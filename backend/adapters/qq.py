"""
QQ 平台适配器
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncGenerator
import aiohttp
from loguru import logger

from app.core.messages import (
    UnifiedMessage, PlatformType, ChatType, MessageType, 
    UserInfo, ChatInfo, MessageContent
)
from adapters.base import BaseAdapter, AdapterConfig


class QQConfig(AdapterConfig):
    """QQ 适配器配置"""
    
    def __init__(
        self,
        bot_token: str,
        app_id: str = "",
        app_secret: str = "",
        is_sandbox: bool = True,
        api_base_url: str = "https://api.sgroup.qq.com",
        **kwargs
    ):
        self.bot_token = bot_token
        self.app_id = app_id
        self.app_secret = app_secret
        self.is_sandbox = is_sandbox
        self.api_base_url = api_base_url
        super().__init__(**kwargs)


class QQAdapter(BaseAdapter):
    """QQ 平台适配器"""
    
    def __init__(self, config: QQConfig, event_bus):
        super().__init__(PlatformType.QQ, config, event_bus)
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.sequence = 0
        self.session_id = ""
        self.heartbeat_interval = 30
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> bool:
        """连接到 QQ 平台"""
        try:
            # 创建 HTTP 会话
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bot {self.config.app_id}.{self.config.bot_token}",
                    "Content-Type": "application/json"
                }
            )
            
            # 获取 WebSocket 网关
            gateway_url = await self._get_gateway_url()
            if not gateway_url:
                return False
            
            # 建立 WebSocket 连接
            self.websocket = await self.session.ws_connect(gateway_url)
            self.is_connected = True
            
            logger.info("QQ 平台连接成功")
            return True
            
        except Exception as e:
            logger.error(f"QQ 平台连接失败: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """断开 QQ 平台连接"""
        try:
            self.is_connected = False
            
            # 停止心跳
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            
            # 关闭 WebSocket
            if self.websocket:
                await self.websocket.close()
            
            # 关闭 HTTP 会话
            if self.session:
                await self.session.close()
            
            logger.info("QQ 平台连接已断开")
            return True
            
        except Exception as e:
            logger.error(f"QQ 平台断开连接失败: {e}")
            return False
    
    async def send_message(self, message: UnifiedMessage) -> bool:
        """发送消息到 QQ 平台"""
        try:
            if not self.is_connected or not self.session:
                logger.error("QQ 平台未连接")
                return False
            
            # 格式化消息
            payload = self.format_outgoing_message(message)
            
            # 发送消息
            url = f"{self.config.api_base_url}/channels/{message.chat.chat_id}/messages"
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"QQ 消息发送成功: {message.message_id}")
                    return True
                else:
                    logger.error(f"QQ 消息发送失败: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"QQ 消息发送异常: {e}")
            return False
    
    async def receive_messages(self) -> AsyncGenerator[Dict[str, Any], None]:
        """接收 QQ 平台消息"""
        if not self.websocket:
            return
        
        try:
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_websocket_message(data)
                    
                    # 如果是消息事件，yield 给上层处理
                    if data.get("t") == "MESSAGE_CREATE":
                        yield data
                        
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"QQ WebSocket 错误: {self.websocket.exception()}")
                    break
                    
        except Exception as e:
            logger.error(f"QQ 消息接收异常: {e}")
    
    def parse_platform_message(self, platform_message: Dict[str, Any]) -> UnifiedMessage:
        """解析 QQ 平台消息为统一格式"""
        try:
            msg_data = platform_message.get("d", {})
            
            # 提取基本信息
            message_id = msg_data.get("id", str(uuid.uuid4()))
            channel_id = msg_data.get("channel_id", "")
            author = msg_data.get("author", {})
            content = msg_data.get("content", "")
            timestamp_str = msg_data.get("timestamp", "")
            
            # 解析时间
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")) if timestamp_str else datetime.utcnow()
            
            # 创建用户信息
            sender = UserInfo(
                user_id=author.get("id", ""),
                username=author.get("username", ""),
                avatar_url=author.get("avatar", "")
            )
            
            # 创建聊天信息
            chat = ChatInfo(
                chat_id=channel_id,
                chat_type=ChatType.CHANNEL  # QQ 频道默认为频道类型
            )
            
            # 创建消息内容
            message_content = MessageContent(text=content)
            
            # 处理附件
            attachments = msg_data.get("attachments", [])
            if attachments:
                attachment = attachments[0]  # 取第一个附件
                message_content.media_url = attachment.get("url")
                message_content.file_name = attachment.get("filename")
                message_content.file_size = attachment.get("size")
                message_content.mime_type = attachment.get("content_type")
                
                # 根据文件类型设置消息类型
                if attachment.get("content_type", "").startswith("image/"):
                    message_type = MessageType.IMAGE
                elif attachment.get("content_type", "").startswith("audio/"):
                    message_type = MessageType.AUDIO
                elif attachment.get("content_type", "").startswith("video/"):
                    message_type = MessageType.VIDEO
                else:
                    message_type = MessageType.FILE
            else:
                message_type = MessageType.TEXT
            
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
            logger.error(f"QQ 消息解析失败: {e}")
            raise
    
    def format_outgoing_message(self, message: UnifiedMessage) -> Dict[str, Any]:
        """格式化outgoing消息为 QQ 平台格式"""
        payload = {}
        
        if message.message_type == MessageType.TEXT:
            payload["content"] = message.content.text
        elif message.message_type == MessageType.IMAGE:
            payload["image"] = message.content.media_url or message.content.file_path
        elif message.message_type == MessageType.CARD:
            # QQ 频道支持 Markdown 格式
            payload["markdown"] = {
                "custom_template_id": "template_id",
                "params": [
                    {"key": "content", "values": [message.content.text]}
                ]
            }
        
        return payload
    
    async def _get_gateway_url(self) -> Optional[str]:
        """获取 WebSocket 网关 URL"""
        try:
            url = f"{self.config.api_base_url}/gateway"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    gateway_url = data.get("url")
                    logger.info(f"获取 QQ 网关 URL: {gateway_url}")
                    return gateway_url
                else:
                    logger.error(f"获取 QQ 网关失败: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"获取 QQ 网关异常: {e}")
            return None
    
    async def _handle_websocket_message(self, data: Dict[str, Any]):
        """处理 WebSocket 消息"""
        opcode = data.get("op")
        
        if opcode == 10:  # Hello
            # 接收到 Hello，发送 Identify
            await self._send_identify()
            
            # 启动心跳
            heartbeat_interval = data.get("d", {}).get("heartbeat_interval", 30000)
            self.heartbeat_interval = heartbeat_interval / 1000
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
        elif opcode == 11:  # Heartbeat ACK
            logger.debug("QQ 心跳响应")
            
        elif opcode == 0:  # Dispatch
            # 更新序列号
            self.sequence = data.get("s", self.sequence)
            
            # 处理事件
            event_type = data.get("t")
            if event_type == "READY":
                self.session_id = data.get("d", {}).get("session_id", "")
                logger.info(f"QQ 机器人就绪，会话ID: {self.session_id}")
    
    async def _send_identify(self):
        """发送身份验证"""
        identify_payload = {
            "op": 2,
            "d": {
                "token": f"Bot {self.config.app_id}.{self.config.bot_token}",
                "intents": 1 << 30,  # 公域机器人 intents
                "properties": {
                    "os": "linux",
                    "browser": "chatbot-platform",
                    "device": "chatbot-platform"
                }
            }
        }
        
        await self.websocket.send_str(json.dumps(identify_payload))
        logger.info("发送 QQ Identify")
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        try:
            while self.is_connected:
                heartbeat_payload = {
                    "op": 1,
                    "d": self.sequence
                }
                
                await self.websocket.send_str(json.dumps(heartbeat_payload))
                logger.debug("发送 QQ 心跳")
                
                await asyncio.sleep(self.heartbeat_interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"QQ 心跳异常: {e}")