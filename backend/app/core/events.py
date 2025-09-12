"""
事件处理系统
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from loguru import logger

from app.core.messages import MessageEvent
from app.core.redis import get_redis


class EventBus:
    """事件总线"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._running = False
        self._redis_client = None
    
    async def start(self):
        """启动事件总线"""
        self._running = True
        self._redis_client = await get_redis()
        logger.info("事件总线已启动")
    
    async def stop(self):
        """停止事件总线"""
        self._running = False
        logger.info("事件总线已停止")
    
    def subscribe(self, event_type: str, handler: Callable[[MessageEvent], None]):
        """订阅事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(handler)
        logger.info(f"事件订阅: {event_type} -> {handler.__name__}")
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                logger.info(f"取消事件订阅: {event_type} -> {handler.__name__}")
    
    async def publish(self, event: MessageEvent):
        """发布事件"""
        try:
            # 本地事件处理
            await self._handle_local_event(event)
            
            # Redis 事件分发
            await self._publish_to_redis(event)
            
        except Exception as e:
            logger.error(f"发布事件失败: {e}", exc_info=True)
    
    async def _handle_local_event(self, event: MessageEvent):
        """处理本地事件"""
        event_type = event.event_type
        
        if event_type in self._subscribers:
            handlers = self._subscribers[event_type]
            
            # 并发执行所有处理器
            tasks = []
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        tasks.append(handler(event))
                    else:
                        # 同步函数在线程池中执行
                        loop = asyncio.get_event_loop()
                        tasks.append(loop.run_in_executor(None, handler, event))
                except Exception as e:
                    logger.error(f"事件处理器执行失败 {handler.__name__}: {e}")
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _publish_to_redis(self, event: MessageEvent):
        """发布事件到 Redis"""
        if self._redis_client:
            channel = f"events:{event.event_type}"
            await self._redis_client.publish(channel, event.json())
    
    async def subscribe_redis_events(self, event_types: List[str]):
        """订阅 Redis 事件"""
        if not self._redis_client:
            return
        
        for event_type in event_types:
            channel = f"events:{event_type}"
            pubsub = await self._redis_client.subscribe(channel)
            
            # 在后台任务中处理消息
            asyncio.create_task(self._handle_redis_messages(pubsub, event_type))
    
    async def _handle_redis_messages(self, pubsub, event_type: str):
        """处理 Redis 消息"""
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        event_data = message['data']
                        event = MessageEvent.parse_raw(event_data)
                        await self._handle_local_event(event)
                    except Exception as e:
                        logger.error(f"处理 Redis 事件失败: {e}")
        except Exception as e:
            logger.error(f"Redis 消息监听失败: {e}")
        finally:
            await pubsub.unsubscribe()


class EventHandler:
    """事件处理器基类"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.register_handlers()
    
    def register_handlers(self):
        """注册事件处理器"""
        raise NotImplementedError
    
    async def handle_event(self, event: MessageEvent):
        """处理事件"""
        raise NotImplementedError


class MessageEventHandler(EventHandler):
    """消息事件处理器"""
    
    def register_handlers(self):
        """注册消息相关事件处理器"""
        self.event_bus.subscribe("message.received", self.handle_message_received)
        self.event_bus.subscribe("message.sent", self.handle_message_sent)
        self.event_bus.subscribe("message.failed", self.handle_message_failed)
    
    async def handle_message_received(self, event: MessageEvent):
        """处理接收到的消息"""
        logger.info(f"处理接收消息: {event.message.message_id}")
        # TODO: 实现消息处理逻辑
        pass
    
    async def handle_message_sent(self, event: MessageEvent):
        """处理发送成功的消息"""
        logger.info(f"消息发送成功: {event.message.message_id}")
        # TODO: 更新消息状态
        pass
    
    async def handle_message_failed(self, event: MessageEvent):
        """处理发送失败的消息"""
        logger.error(f"消息发送失败: {event.message.message_id}")
        # TODO: 重试或记录错误
        pass


class BotEventHandler(EventHandler):
    """机器人事件处理器"""
    
    def register_handlers(self):
        """注册机器人相关事件处理器"""
        self.event_bus.subscribe("bot.started", self.handle_bot_started)
        self.event_bus.subscribe("bot.stopped", self.handle_bot_stopped)
        self.event_bus.subscribe("bot.error", self.handle_bot_error)
    
    async def handle_bot_started(self, event: MessageEvent):
        """处理机器人启动事件"""
        logger.info(f"机器人启动: {event.bot_id}")
        # TODO: 更新机器人状态
        pass
    
    async def handle_bot_stopped(self, event: MessageEvent):
        """处理机器人停止事件"""
        logger.info(f"机器人停止: {event.bot_id}")
        # TODO: 更新机器人状态
        pass
    
    async def handle_bot_error(self, event: MessageEvent):
        """处理机器人错误事件"""
        logger.error(f"机器人错误: {event.bot_id}")
        # TODO: 记录错误并处理
        pass


# 全局事件总线实例
event_bus = EventBus()


async def get_event_bus() -> EventBus:
    """获取事件总线实例"""
    return event_bus


def create_event(
    event_type: str,
    platform: str,
    bot_id: Optional[str] = None,
    message=None,
    data: Optional[Dict[str, Any]] = None
) -> MessageEvent:
    """创建事件"""
    return MessageEvent(
        event_type=event_type,
        event_id=str(uuid.uuid4()),
        platform=platform,
        bot_id=bot_id,
        message=message,
        data=data,
        timestamp=datetime.utcnow()
    )