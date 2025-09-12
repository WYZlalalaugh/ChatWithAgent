"""
飞书平台适配器
"""

import json
import uuid
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, AsyncGenerator
from loguru import logger

from app.core.messages import (
    UnifiedMessage, PlatformType, ChatType, MessageType, 
    UserInfo, ChatInfo, MessageContent
)
from adapters.base import BaseAdapter, AdapterConfig


class FeishuConfig(AdapterConfig):
    """飞书适配器配置"""
    
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        verification_token: str = "",
        encrypt_key: str = "",
        is_lark: bool = False,  # 是否为国际版 Lark
        **kwargs
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key
        self.is_lark = is_lark
        super().__init__(**kwargs)


class FeishuAdapter(BaseAdapter):
    """飞书平台适配器"""
    
    def __init__(self, config: FeishuConfig, event_bus):
        super().__init__(PlatformType.FEISHU, config, event_bus)
        self.tenant_access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        if config.is_lark:
            self.api_base_url = "https://open.larksuite.com"
        else:
            self.api_base_url = "https://open.feishu.cn"
    
    async def connect(self) -> bool:
        """连接到飞书平台"""
        try:
            # 获取租户访问令牌
            success = await self._get_tenant_access_token()
            if success:
                self.is_connected = True
                logger.info("飞书平台连接成功")
                return True
            else:
                logger.error("飞书平台连接失败")
                return False
                
        except Exception as e:
            logger.error(f"飞书平台连接异常: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """断开飞书平台连接"""
        try:
            self.is_connected = False
            self.tenant_access_token = None
            self.token_expires_at = None
            logger.info("飞书平台连接已断开")
            return True
            
        except Exception as e:
            logger.error(f"飞书平台断开连接失败: {e}")
            return False
    
    async def send_message(self, message: UnifiedMessage) -> bool:
        """发送消息到飞书平台"""
        try:
            if not self.is_connected:
                logger.error("飞书平台未连接")
                return False
            
            # 检查并刷新访问令牌
            if not await self._ensure_valid_token():
                return False
            
            # 格式化消息
            payload = self.format_outgoing_message(message)
            
            # 发送消息
            url = f"{self.api_base_url}/open-apis/im/v1/messages"
            headers = {
                "Authorization": f"Bearer {self.tenant_access_token}",
                "Content-Type": "application/json"
            }
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("code") == 0:
                            logger.info(f"飞书消息发送成功: {message.message_id}")
                            return True
                        else:
                            logger.error(f"飞书消息发送失败: {result}")
                            return False
                    else:
                        logger.error(f"飞书消息发送失败: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"飞书消息发送异常: {e}")
            return False
    
    async def receive_messages(self) -> AsyncGenerator[Dict[str, Any], None]:
        """接收飞书平台消息"""
        # 飞书使用回调模式，这里实现为空生成器
        # 实际消息接收通过 webhook 处理
        while self._running:
            await asyncio.sleep(1)
            # 在实际实现中，这里会从消息队列中获取回调消息
            yield
    
    def parse_platform_message(self, platform_message: Dict[str, Any]) -> UnifiedMessage:
        """解析飞书平台消息为统一格式"""
        try:
            # 飞书回调消息格式
            event = platform_message.get("event", {})
            message_data = event.get("message", {})
            sender_data = event.get("sender", {})
            
            # 提取基本信息
            message_id = message_data.get("message_id", str(uuid.uuid4()))
            chat_id = message_data.get("chat_id", "")
            chat_type = message_data.get("chat_type", "p2p")
            create_time = message_data.get("create_time", "")
            message_type_str = message_data.get("message_type", "text")
            content = message_data.get("content", "")
            
            # 解析时间
            if create_time:
                timestamp = datetime.fromtimestamp(int(create_time) / 1000)
            else:
                timestamp = datetime.utcnow()
            
            # 创建用户信息
            sender = UserInfo(
                user_id=sender_data.get("sender_id", {}).get("open_id", ""),
                username=sender_data.get("sender_id", {}).get("user_id", "")
            )
            
            # 创建聊天信息
            if chat_type == "p2p":
                chat_type_enum = ChatType.PRIVATE
            elif chat_type == "group":
                chat_type_enum = ChatType.GROUP
            else:
                chat_type_enum = ChatType.CHANNEL
            
            chat = ChatInfo(
                chat_id=chat_id,
                chat_type=chat_type_enum
            )
            
            # 解析消息内容
            try:
                content_data = json.loads(content) if isinstance(content, str) else content
            except:
                content_data = {"text": str(content)}
            
            if message_type_str == "text":
                message_content = MessageContent(text=content_data.get("text", ""))
                message_type = MessageType.TEXT
            elif message_type_str == "image":
                message_content = MessageContent(
                    media_url=content_data.get("image_key", ""),
                    metadata=content_data
                )
                message_type = MessageType.IMAGE
            elif message_type_str == "audio":
                message_content = MessageContent(
                    metadata=content_data
                )
                message_type = MessageType.AUDIO
            elif message_type_str == "file":
                message_content = MessageContent(
                    file_name=content_data.get("file_name", ""),
                    metadata=content_data
                )
                message_type = MessageType.FILE
            elif message_type_str == "interactive":
                # 互动卡片消息
                message_content = MessageContent(
                    text=content_data.get("template", ""),
                    metadata=content_data
                )
                message_type = MessageType.CARD
            else:
                message_content = MessageContent(text=str(content_data))
                message_type = MessageType.SYSTEM
            
            return UnifiedMessage(
                message_id=message_id,
                platform=self.platform_type,
                platform_message_id=message_id,
                sender=sender,
                chat=chat,
                message_type=message_type,
                content=message_content,
                timestamp=timestamp,
                metadata={"raw": platform_message}
            )
            
        except Exception as e:
            logger.error(f"飞书消息解析失败: {e}")
            raise
    
    def format_outgoing_message(self, message: UnifiedMessage) -> Dict[str, Any]:
        """格式化outgoing消息为飞书平台格式"""
        payload = {
            "receive_id": message.chat.chat_id,
            "receive_id_type": "chat_id"
        }
        
        if message.message_type == MessageType.TEXT:
            payload["msg_type"] = "text"
            payload["content"] = json.dumps({
                "text": message.content.text
            }, ensure_ascii=False)
        elif message.message_type == MessageType.IMAGE:
            payload["msg_type"] = "image"
            payload["content"] = json.dumps({
                "image_key": message.content.metadata.get("image_key", "")
            }, ensure_ascii=False)
        elif message.message_type == MessageType.CARD:
            payload["msg_type"] = "interactive"
            # 飞书卡片消息格式
            card_content = {
                "config": {
                    "wide_screen_mode": True
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": message.content.text
                    }
                ]
            }
            payload["content"] = json.dumps(card_content, ensure_ascii=False)
        
        return payload
    
    async def _get_tenant_access_token(self) -> bool:
        """获取租户访问令牌"""
        try:
            url = f"{self.api_base_url}/open-apis/auth/v3/tenant_access_token/internal"
            payload = {
                "app_id": self.config.app_id,
                "app_secret": self.config.app_secret
            }
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("code") == 0:
                            self.tenant_access_token = result["tenant_access_token"]
                            expires_in = result.get("expire", 7200)
                            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)  # 提前5分钟过期
                            logger.info("飞书租户访问令牌获取成功")
                            return True
                        else:
                            logger.error(f"飞书租户访问令牌获取失败: {result}")
                            return False
                    else:
                        logger.error(f"飞书租户访问令牌请求失败: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"飞书租户访问令牌获取异常: {e}")
            return False
    
    async def _ensure_valid_token(self) -> bool:
        """确保访问令牌有效"""
        if not self.tenant_access_token or not self.token_expires_at:
            return await self._get_tenant_access_token()
        
        if datetime.utcnow() >= self.token_expires_at:
            return await self._get_tenant_access_token()
        
        return True
    
    def verify_webhook_signature(self, timestamp: str, nonce: str, body: str, signature: str) -> bool:
        """验证 webhook 签名"""
        if not self.config.encrypt_key:
            return True  # 如果没有配置加密密钥，跳过验证
        
        # 拼接字符串
        string_to_sign = f"{timestamp}{nonce}{self.config.encrypt_key}{body}"
        
        # 计算签名
        hash_obj = hashlib.sha256(string_to_sign.encode("utf-8"))
        calculated_signature = base64.b64encode(hash_obj.digest()).decode("utf-8")
        
        return calculated_signature == signature