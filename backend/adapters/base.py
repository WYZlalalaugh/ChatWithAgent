"""
平台适配器基础框架
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from loguru import logger

from app.core.messages import (
    UnifiedMessage, MessageEvent, PlatformType, ChatType, 
    MessageType, UserInfo, ChatInfo, MessageContent
)
from app.core.events import EventBus, create_event


class AdapterConfig:
    """适配器配置基类"""
    
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.__dict__.copy()


class BaseAdapter(ABC):
    """平台适配器基类"""
    
    def __init__(
        self, 
        platform_type: PlatformType,
        config: AdapterConfig,
        event_bus: EventBus
    ):
        self.platform_type = platform_type
        self.config = config
        self.event_bus = event_bus
        self.is_connected = False
        self.bot_id: Optional[str] = None
        self._running = False
        self._receive_task: Optional[asyncio.Task] = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """连接到平台"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """断开平台连接"""
        pass
    
    @abstractmethod
    async def send_message(self, message: UnifiedMessage) -> bool:
        """发送消息到平台"""
        pass
    
    @abstractmethod
    async def receive_messages(self):
        """接收平台消息（生成器）"""
        pass
    
    @abstractmethod
    def parse_platform_message(self, platform_message: Any) -> UnifiedMessage:
        """解析平台原始消息为统一格式"""
        pass
    
    @abstractmethod
    def format_outgoing_message(self, message: UnifiedMessage) -> Any:
        """格式化outgoing消息为平台格式"""
        pass
    
    async def start(self, bot_id: str) -> bool:
        """启动适配器"""
        try:
            self.bot_id = bot_id
            
            # 连接到平台
            if not await self.connect():
                logger.error(f"平台连接失败: {self.platform_type}")
                return False
            
            # 启动消息接收
            self._running = True
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            # 发布启动事件
            event = create_event(
                event_type="adapter.started",
                platform=self.platform_type.value,
                bot_id=bot_id,
                data={"adapter_type": self.__class__.__name__}
            )
            await self.event_bus.publish(event)
            
            logger.info(f"适配器已启动: {self.platform_type}")
            return True
            
        except Exception as e:
            logger.error(f"适配器启动失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """停止适配器"""
        try:
            self._running = False
            
            # 停止消息接收
            if self._receive_task:
                self._receive_task.cancel()
                try:
                    await self._receive_task
                except asyncio.CancelledError:
                    pass
            
            # 断开连接
            await self.disconnect()
            
            # 发布停止事件
            event = create_event(
                event_type="adapter.stopped",
                platform=self.platform_type.value,
                bot_id=self.bot_id,
                data={"adapter_type": self.__class__.__name__}
            )
            await self.event_bus.publish(event)
            
            logger.info(f"适配器已停止: {self.platform_type}")
            return True
            
        except Exception as e:
            logger.error(f"适配器停止失败: {e}")
            return False
    
    async def _receive_loop(self):
        """消息接收循环"""
        logger.info(f"开始接收消息: {self.platform_type}")
        
        try:
            async for platform_message in self.receive_messages():
                if not self._running:
                    break
                
                try:
                    # 解析平台消息
                    unified_message = self.parse_platform_message(platform_message)
                    
                    # 发布消息接收事件
                    event = create_event(
                        event_type="message.received",
                        platform=self.platform_type.value,
                        bot_id=self.bot_id,
                        message=unified_message
                    )
                    await self.event_bus.publish(event)
                    
                except Exception as e:
                    logger.error(f"消息解析失败: {e}")
                    
                    # 发布错误事件
                    event = create_event(
                        event_type="message.parse_error",
                        platform=self.platform_type.value,
                        bot_id=self.bot_id,
                        data={"error": str(e), "raw_message": str(platform_message)}
                    )
                    await self.event_bus.publish(event)
        
        except Exception as e:
            logger.error(f"消息接收循环异常: {e}")
            
            # 发布适配器错误事件
            event = create_event(
                event_type="adapter.error",
                platform=self.platform_type.value,
                bot_id=self.bot_id,
                data={"error": str(e)}
            )
            await self.event_bus.publish(event)
        
        logger.info(f"消息接收循环结束: {self.platform_type}")
    
    async def handle_outgoing_message(self, message: UnifiedMessage) -> bool:
        """处理outgoing消息"""
        try:
            # 发送消息
            success = await self.send_message(message)
            
            if success:
                # 发布消息发送成功事件
                event = create_event(
                    event_type="message.sent",
                    platform=self.platform_type.value,
                    bot_id=self.bot_id,
                    message=message
                )
                await self.event_bus.publish(event)
            else:
                # 发布消息发送失败事件
                event = create_event(
                    event_type="message.send_failed",
                    platform=self.platform_type.value,
                    bot_id=self.bot_id,
                    message=message
                )
                await self.event_bus.publish(event)
            
            return success
            
        except Exception as e:
            logger.error(f"消息发送异常: {e}")
            
            # 发布消息发送异常事件
            event = create_event(
                event_type="message.send_error",
                platform=self.platform_type.value,
                bot_id=self.bot_id,
                message=message,
                data={"error": str(e)}
            )
            await self.event_bus.publish(event)
            
            return False
    
    def create_unified_message(
        self,
        message_id: str,
        sender_id: str,
        sender_name: str,
        chat_id: str,
        chat_type: ChatType,
        message_type: MessageType,
        content: Union[str, Dict[str, Any]],
        platform_message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UnifiedMessage:
        """创建统一消息对象"""
        
        # 处理内容
        if isinstance(content, str):
            message_content = MessageContent(text=content)
        elif isinstance(content, dict):
            message_content = MessageContent(**content)
        else:
            message_content = MessageContent(text=str(content))
        
        # 创建用户信息
        sender = UserInfo(
            user_id=sender_id,
            username=sender_name
        )
        
        # 创建聊天信息
        chat = ChatInfo(
            chat_id=chat_id,
            chat_type=chat_type
        )
        
        return UnifiedMessage(
            message_id=message_id,
            platform=self.platform_type,
            platform_message_id=platform_message_id,
            sender=sender,
            chat=chat,
            message_type=message_type,
            content=message_content,
            timestamp=timestamp or datetime.utcnow(),
            metadata=metadata
        )


class AdapterManager:
    """适配器管理器"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._adapters: Dict[str, BaseAdapter] = {}
        self._bot_adapters: Dict[str, BaseAdapter] = {}
    
    def register_adapter(self, adapter_name: str, adapter: BaseAdapter):
        """注册适配器"""
        self._adapters[adapter_name] = adapter
        logger.info(f"适配器已注册: {adapter_name}")
    
    async def start_adapter(self, adapter_name: str, bot_id: str) -> bool:
        """启动适配器"""
        if adapter_name not in self._adapters:
            logger.error(f"适配器不存在: {adapter_name}")
            return False
        
        adapter = self._adapters[adapter_name]
        success = await adapter.start(bot_id)
        
        if success:
            self._bot_adapters[bot_id] = adapter
        
        return success
    
    async def stop_adapter(self, bot_id: str) -> bool:
        """停止适配器"""
        if bot_id not in self._bot_adapters:
            logger.warning(f"机器人适配器不存在: {bot_id}")
            return True
        
        adapter = self._bot_adapters[bot_id]
        success = await adapter.stop()
        
        if success:
            del self._bot_adapters[bot_id]
        
        return success
    
    async def send_message(self, bot_id: str, message: UnifiedMessage) -> bool:
        """通过适配器发送消息"""
        if bot_id not in self._bot_adapters:
            logger.error(f"机器人适配器不存在: {bot_id}")
            return False
        
        adapter = self._bot_adapters[bot_id]
        return await adapter.handle_outgoing_message(message)
    
    def get_adapter(self, bot_id: str) -> Optional[BaseAdapter]:
        """获取机器人适配器"""
        return self._bot_adapters.get(bot_id)
    
    def list_adapters(self) -> List[str]:
        """列出所有注册的适配器"""
        return list(self._adapters.keys())
    
    def list_active_adapters(self) -> List[str]:
        """列出所有活跃的适配器"""
        return list(self._bot_adapters.keys())


# 全局适配器管理器实例
adapter_manager: Optional[AdapterManager] = None


async def get_adapter_manager() -> AdapterManager:
    """获取适配器管理器"""
    global adapter_manager
    if not adapter_manager:
        from app.core.events import get_event_bus
        event_bus = await get_event_bus()
        adapter_manager = AdapterManager(event_bus)
    
    return adapter_manager