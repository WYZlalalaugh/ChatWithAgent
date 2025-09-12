"""
钉钉平台适配器
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


class DingTalkConfig(AdapterConfig):
    """钉钉适配器配置"""
    
    def __init__(
        self,
        app_key: str,
        app_secret: str,
        robot_webhook: str = "",
        robot_secret: str = "",
        **kwargs
    ):
        self.app_key = app_key
        self.app_secret = app_secret
        self.robot_webhook = robot_webhook
        self.robot_secret = robot_secret
        super().__init__(**kwargs)


class DingTalkAdapter(BaseAdapter):
    """钉钉平台适配器"""
    
    def __init__(self, config: DingTalkConfig, event_bus):
        super().__init__(PlatformType.DINGTALK, config, event_bus)
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.api_base_url = "https://oapi.dingtalk.com"
    
    async def connect(self) -> bool:
        """连接到钉钉平台"""
        try:
            # 获取访问令牌
            success = await self._get_access_token()
            if success:
                self.is_connected = True
                logger.info("钉钉平台连接成功")
                return True
            else:
                logger.error("钉钉平台连接失败")
                return False
                
        except Exception as e:
            logger.error(f"钉钉平台连接异常: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """断开钉钉平台连接"""
        try:
            self.is_connected = False
            self.access_token = None
            self.token_expires_at = None
            logger.info("钉钉平台连接已断开")
            return True
            
        except Exception as e:
            logger.error(f"钉钉平台断开连接失败: {e}")
            return False
    
    async def send_message(self, message: UnifiedMessage) -> bool:
        """发送消息到钉钉平台"""
        try:
            if not self.is_connected:
                logger.error("钉钉平台未连接")
                return False
            
            # 检查并刷新访问令牌
            if not await self._ensure_valid_token():
                return False
            
            # 格式化消息
            payload = self.format_outgoing_message(message)
            
            # 发送消息
            if self.config.robot_webhook:
                # 机器人 webhook 模式
                success = await self._send_robot_message(payload)
            else:
                # 应用消息模式
                success = await self._send_app_message(payload)
            
            if success:
                logger.info(f"钉钉消息发送成功: {message.message_id}")
            else:
                logger.error(f"钉钉消息发送失败: {message.message_id}")
            
            return success
                        
        except Exception as e:
            logger.error(f"钉钉消息发送异常: {e}")
            return False
    
    async def receive_messages(self) -> AsyncGenerator[Dict[str, Any], None]:
        """接收钉钉平台消息"""
        # 钉钉使用回调模式，这里实现为空生成器
        # 实际消息接收通过 webhook 处理
        while self._running:
            await asyncio.sleep(1)
            # 在实际实现中，这里会从消息队列中获取回调消息
            yield
    
    def parse_platform_message(self, platform_message: Dict[str, Any]) -> UnifiedMessage:
        """解析钉钉平台消息为统一格式"""
        try:
            # 钉钉回调消息格式
            msg_type = platform_message.get("msgtype", "text")
            sender_staff_id = platform_message.get("senderStaffId", "")
            sender_nick = platform_message.get("senderNick", "")
            chat_bot_corp_id = platform_message.get("chatbotCorpId", "")
            chat_bot_user_id = platform_message.get("chatbotUserId", "")
            msg_id = platform_message.get("msgId", str(uuid.uuid4()))
            create_at = platform_message.get("createAt", int(datetime.utcnow().timestamp() * 1000))
            
            # 解析时间
            timestamp = datetime.fromtimestamp(create_at / 1000)
            
            # 创建用户信息
            sender = UserInfo(
                user_id=sender_staff_id,
                username=sender_nick
            )
            
            # 创建聊天信息
            chat = ChatInfo(
                chat_id=chat_bot_corp_id or chat_bot_user_id,
                chat_type=ChatType.PRIVATE  # 钉钉机器人主要是私聊
            )
            
            # 解析消息内容
            if msg_type == "text":
                text_content = platform_message.get("text", {})
                message_content = MessageContent(text=text_content.get("content", ""))
                message_type = MessageType.TEXT
            elif msg_type == "image":
                message_content = MessageContent(
                    media_url=platform_message.get("downloadCode", ""),
                    metadata=platform_message
                )
                message_type = MessageType.IMAGE
            elif msg_type == "file":
                message_content = MessageContent(
                    file_name=platform_message.get("fileName", ""),
                    metadata=platform_message
                )
                message_type = MessageType.FILE
            else:
                message_content = MessageContent(text=str(platform_message))
                message_type = MessageType.SYSTEM
            
            return UnifiedMessage(
                message_id=str(msg_id),
                platform=self.platform_type,
                platform_message_id=str(msg_id),
                sender=sender,
                chat=chat,
                message_type=message_type,
                content=message_content,
                timestamp=timestamp,
                metadata={"raw": platform_message}
            )
            
        except Exception as e:
            logger.error(f"钉钉消息解析失败: {e}")
            raise
    
    def format_outgoing_message(self, message: UnifiedMessage) -> Dict[str, Any]:
        """格式化outgoing消息为钉钉平台格式"""
        if message.message_type == MessageType.TEXT:
            return {
                "msgtype": "text",
                "text": {
                    "content": message.content.text
                }
            }
        elif message.message_type == MessageType.CARD:
            # 钉钉 ActionCard 格式
            return {
                "msgtype": "actionCard",
                "actionCard": {
                    "title": message.content.metadata.get("title", ""),
                    "text": message.content.text,
                    "singleTitle": message.content.metadata.get("button_text", "查看详情"),
                    "singleURL": message.content.metadata.get("url", "")
                }
            }
        elif message.message_type == MessageType.IMAGE:
            return {
                "msgtype": "image",
                "image": {
                    "mediaId": message.content.metadata.get("media_id", "")
                }
            }
        else:
            return {
                "msgtype": "text",
                "text": {
                    "content": str(message.content.text or "")
                }
            }
    
    async def _get_access_token(self) -> bool:
        """获取访问令牌"""
        try:
            url = f"{self.api_base_url}/gettoken"
            params = {
                "appkey": self.config.app_key,
                "appsecret": self.config.app_secret
            }
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("errcode") == 0:
                            self.access_token = result["access_token"]
                            expires_in = result.get("expires_in", 7200)
                            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)  # 提前5分钟过期
                            logger.info("钉钉访问令牌获取成功")
                            return True
                        else:
                            logger.error(f"钉钉访问令牌获取失败: {result}")
                            return False
                    else:
                        logger.error(f"钉钉访问令牌请求失败: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"钉钉访问令牌获取异常: {e}")
            return False
    
    async def _ensure_valid_token(self) -> bool:
        """确保访问令牌有效"""
        if not self.access_token or not self.token_expires_at:
            return await self._get_access_token()
        
        if datetime.utcnow() >= self.token_expires_at:
            return await self._get_access_token()
        
        return True
    
    async def _send_robot_message(self, payload: Dict[str, Any]) -> bool:
        """发送机器人消息"""
        try:
            # 计算签名
            timestamp = str(int(datetime.utcnow().timestamp() * 1000))
            secret = self.config.robot_secret
            
            if secret:
                string_to_sign = f"{timestamp}\n{secret}"
                hmac_code = hmac.new(
                    secret.encode("utf-8"), 
                    string_to_sign.encode("utf-8"), 
                    digestmod=hashlib.sha256
                ).digest()
                sign = base64.b64encode(hmac_code).decode("utf-8")
                
                webhook_url = f"{self.config.robot_webhook}&timestamp={timestamp}&sign={sign}"
            else:
                webhook_url = self.config.robot_webhook
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("errcode") == 0
                    else:
                        return False
                        
        except Exception as e:
            logger.error(f"钉钉机器人消息发送异常: {e}")
            return False
    
    async def _send_app_message(self, payload: Dict[str, Any]) -> bool:
        """发送应用消息"""
        try:
            url = f"{self.api_base_url}/robot/send?access_token={self.access_token}"
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("errcode") == 0
                    else:
                        return False
                        
        except Exception as e:
            logger.error(f"钉钉应用消息发送异常: {e}")
            return False