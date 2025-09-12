"""
微信平台适配器
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncGenerator
from loguru import logger

from app.core.messages import (
    UnifiedMessage, PlatformType, ChatType, MessageType, 
    UserInfo, ChatInfo, MessageContent
)
from adapters.base import BaseAdapter, AdapterConfig


class WeChatConfig(AdapterConfig):
    """微信适配器配置"""
    
    def __init__(
        self,
        corp_id: str,
        corp_secret: str,
        agent_id: str,
        token: str = "",
        encoding_aes_key: str = "",
        **kwargs
    ):
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.agent_id = agent_id
        self.token = token
        self.encoding_aes_key = encoding_aes_key
        super().__init__(**kwargs)


class WeChatAdapter(BaseAdapter):
    """企业微信平台适配器"""
    
    def __init__(self, config: WeChatConfig, event_bus):
        super().__init__(PlatformType.WECHAT, config, event_bus)
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.api_base_url = "https://qyapi.weixin.qq.com"
    
    async def connect(self) -> bool:
        """连接到企业微信平台"""
        try:
            # 获取访问令牌
            success = await self._get_access_token()
            if success:
                self.is_connected = True
                logger.info("企业微信平台连接成功")
                return True
            else:
                logger.error("企业微信平台连接失败")
                return False
                
        except Exception as e:
            logger.error(f"企业微信平台连接异常: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """断开企业微信平台连接"""
        try:
            self.is_connected = False
            self.access_token = None
            self.token_expires_at = None
            logger.info("企业微信平台连接已断开")
            return True
            
        except Exception as e:
            logger.error(f"企业微信平台断开连接失败: {e}")
            return False
    
    async def send_message(self, message: UnifiedMessage) -> bool:
        """发送消息到企业微信平台"""
        try:
            if not self.is_connected:
                logger.error("企业微信平台未连接")
                return False
            
            # 检查并刷新访问令牌
            if not await self._ensure_valid_token():
                return False
            
            # 格式化消息
            payload = self.format_outgoing_message(message)
            
            # 发送消息
            url = f"{self.api_base_url}/cgi-bin/message/send?access_token={self.access_token}"
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("errcode") == 0:
                            logger.info(f"企业微信消息发送成功: {message.message_id}")
                            return True
                        else:
                            logger.error(f"企业微信消息发送失败: {result}")
                            return False
                    else:
                        logger.error(f"企业微信消息发送失败: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"企业微信消息发送异常: {e}")
            return False
    
    async def receive_messages(self) -> AsyncGenerator[Dict[str, Any], None]:
        """接收企业微信平台消息"""
        # 企业微信使用回调模式，这里实现为空生成器
        # 实际消息接收通过 webhook 处理
        while self._running:
            await asyncio.sleep(1)
            # 在实际实现中，这里会从消息队列中获取回调消息
            yield
    
    def parse_platform_message(self, platform_message: Dict[str, Any]) -> UnifiedMessage:
        """解析企业微信平台消息为统一格式"""
        try:
            # 企业微信回调消息格式
            msg_type = platform_message.get("MsgType", "text")
            from_user = platform_message.get("FromUserName", "")
            to_user = platform_message.get("ToUserName", "")
            create_time = platform_message.get("CreateTime", int(datetime.utcnow().timestamp()))
            msg_id = platform_message.get("MsgId", str(uuid.uuid4()))
            
            # 解析时间
            timestamp = datetime.fromtimestamp(create_time)
            
            # 创建用户信息
            sender = UserInfo(
                user_id=from_user,
                username=from_user
            )
            
            # 创建聊天信息
            chat = ChatInfo(
                chat_id=to_user,  # 应用ID作为聊天ID
                chat_type=ChatType.PRIVATE
            )
            
            # 根据消息类型解析内容
            if msg_type == "text":
                content = MessageContent(text=platform_message.get("Content", ""))
                message_type = MessageType.TEXT
            elif msg_type == "image":
                content = MessageContent(
                    media_url=platform_message.get("PicUrl", ""),
                    metadata={"media_id": platform_message.get("MediaId", "")}
                )
                message_type = MessageType.IMAGE
            elif msg_type == "voice":
                content = MessageContent(
                    metadata={
                        "media_id": platform_message.get("MediaId", ""),
                        "format": platform_message.get("Format", "")
                    }
                )
                message_type = MessageType.AUDIO
            elif msg_type == "file":
                content = MessageContent(
                    file_name=platform_message.get("Title", ""),
                    metadata={"media_id": platform_message.get("MediaId", "")}
                )
                message_type = MessageType.FILE
            else:
                content = MessageContent(text=str(platform_message))
                message_type = MessageType.SYSTEM
            
            return UnifiedMessage(
                message_id=str(msg_id),
                platform=self.platform_type,
                platform_message_id=str(msg_id),
                sender=sender,
                chat=chat,
                message_type=message_type,
                content=content,
                timestamp=timestamp,
                metadata={"raw": platform_message}
            )
            
        except Exception as e:
            logger.error(f"企业微信消息解析失败: {e}")
            raise
    
    def format_outgoing_message(self, message: UnifiedMessage) -> Dict[str, Any]:
        """格式化outgoing消息为企业微信平台格式"""
        payload = {
            "touser": message.chat.chat_id,
            "agentid": self.config.agent_id,
            "safe": 0
        }
        
        if message.message_type == MessageType.TEXT:
            payload["msgtype"] = "text"
            payload["text"] = {
                "content": message.content.text
            }
        elif message.message_type == MessageType.IMAGE:
            payload["msgtype"] = "image"
            payload["image"] = {
                "media_id": message.content.metadata.get("media_id", "")
            }
        elif message.message_type == MessageType.CARD:
            payload["msgtype"] = "textcard"
            payload["textcard"] = {
                "title": message.content.metadata.get("title", ""),
                "description": message.content.text,
                "url": message.content.metadata.get("url", ""),
                "btntxt": message.content.metadata.get("btntxt", "详情")
            }
        
        return payload
    
    async def _get_access_token(self) -> bool:
        """获取访问令牌"""
        try:
            url = f"{self.api_base_url}/cgi-bin/gettoken"
            params = {
                "corpid": self.config.corp_id,
                "corpsecret": self.config.corp_secret
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
                            logger.info("企业微信访问令牌获取成功")
                            return True
                        else:
                            logger.error(f"企业微信访问令牌获取失败: {result}")
                            return False
                    else:
                        logger.error(f"企业微信访问令牌请求失败: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"企业微信访问令牌获取异常: {e}")
            return False
    
    async def _ensure_valid_token(self) -> bool:
        """确保访问令牌有效"""
        if not self.access_token or not self.token_expires_at:
            return await self._get_access_token()
        
        if datetime.utcnow() >= self.token_expires_at:
            return await self._get_access_token()
        
        return True