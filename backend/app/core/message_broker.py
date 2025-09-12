"""
消息代理系统
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger

from app.core.messages import (
    UnifiedMessage, MessageEvent, MessageResponse, 
    PlatformType, MessageStatus
)
from app.core.events import EventBus, create_event
from app.core.redis import RedisClient


class MessageQueue:
    """消息队列"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self._running = False
    
    async def start(self):
        """启动消息队列"""
        self._running = True
        logger.info("消息队列已启动")
    
    async def stop(self):
        """停止消息队列"""
        self._running = False
        logger.info("消息队列已停止")
    
    async def enqueue(self, queue_name: str, message: UnifiedMessage):
        """将消息加入队列"""
        try:
            message_data = message.json()
            await self.redis.redis.lpush(f"queue:{queue_name}", message_data)
            logger.debug(f"消息已加入队列 {queue_name}: {message.message_id}")
        except Exception as e:
            logger.error(f"消息入队失败: {e}")
            raise
    
    async def dequeue(self, queue_name: str, timeout: int = 10) -> Optional[UnifiedMessage]:
        """从队列中取出消息"""
        try:
            result = await self.redis.redis.brpop(f"queue:{queue_name}", timeout=timeout)
            if result:
                queue, message_data = result
                return UnifiedMessage.parse_raw(message_data)
            return None
        except Exception as e:
            logger.error(f"消息出队失败: {e}")
            return None
    
    async def get_queue_size(self, queue_name: str) -> int:
        """获取队列大小"""
        return await self.redis.redis.llen(f"queue:{queue_name}")


class MessageRouter:
    """消息路由器"""
    
    def __init__(self):
        self._routes: Dict[str, List[callable]] = {}
        self._platform_routes: Dict[PlatformType, str] = {}
    
    def register_route(self, pattern: str, handler: callable):
        """注册路由"""
        if pattern not in self._routes:
            self._routes[pattern] = []
        self._routes[pattern].append(handler)
        logger.info(f"注册消息路由: {pattern} -> {handler.__name__}")
    
    def register_platform_route(self, platform: PlatformType, queue_name: str):
        """注册平台路由"""
        self._platform_routes[platform] = queue_name
        logger.info(f"注册平台路由: {platform} -> {queue_name}")
    
    async def route_message(self, message: UnifiedMessage) -> List[str]:
        """路由消息"""
        routes = []
        
        # 平台路由
        if message.platform in self._platform_routes:
            routes.append(self._platform_routes[message.platform])
        
        # 模式匹配路由
        for pattern, handlers in self._routes.items():
            if self._match_pattern(message, pattern):
                routes.extend([f"handler:{handler.__name__}" for handler in handlers])
        
        return routes
    
    def _match_pattern(self, message: UnifiedMessage, pattern: str) -> bool:
        """匹配路由模式"""
        # 简单的模式匹配，可以扩展为更复杂的规则
        if pattern == "*":
            return True
        
        if pattern.startswith("platform:"):
            platform = pattern.split(":", 1)[1]
            return message.platform.value == platform
        
        if pattern.startswith("type:"):
            msg_type = pattern.split(":", 1)[1]
            return message.message_type.value == msg_type
        
        if pattern.startswith("text:"):
            text_pattern = pattern.split(":", 1)[1]
            return message.content.text and text_pattern in message.content.text
        
        return False


class MessageBroker:
    """消息代理"""
    
    def __init__(self, redis_client: RedisClient, event_bus: EventBus):
        self.redis = redis_client
        self.event_bus = event_bus
        self.queue = MessageQueue(redis_client)
        self.router = MessageRouter()
        self._workers: Dict[str, asyncio.Task] = {}
        self._running = False
    
    async def start(self):
        """启动消息代理"""
        self._running = True
        await self.queue.start()
        
        # 启动默认工作者
        await self.start_worker("default", self._default_message_handler)
        
        logger.info("消息代理已启动")
    
    async def stop(self):
        """停止消息代理"""
        self._running = False
        
        # 停止所有工作者
        for worker_name, task in self._workers.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        await self.queue.stop()
        logger.info("消息代理已停止")
    
    async def publish_message(self, message: UnifiedMessage) -> str:
        """发布消息"""
        try:
            # 设置消息ID
            if not message.message_id:
                message.message_id = str(uuid.uuid4())
            
            # 路由消息
            routes = await self.router.route_message(message)
            
            # 将消息加入相应队列
            for route in routes:
                await self.queue.enqueue(route, message)
            
            # 发布消息接收事件
            event = create_event(
                event_type="message.published",
                platform=message.platform.value,
                message=message
            )
            await self.event_bus.publish(event)
            
            logger.info(f"消息已发布: {message.message_id}, 路由: {routes}")
            return message.message_id
            
        except Exception as e:
            logger.error(f"消息发布失败: {e}")
            
            # 发布消息失败事件
            event = create_event(
                event_type="message.publish_failed",
                platform=message.platform.value,
                message=message,
                data={"error": str(e)}
            )
            await self.event_bus.publish(event)
            raise
    
    async def start_worker(self, queue_name: str, handler: callable):
        """启动工作者"""
        if queue_name in self._workers:
            logger.warning(f"工作者 {queue_name} 已存在")
            return
        
        task = asyncio.create_task(self._worker_loop(queue_name, handler))
        self._workers[queue_name] = task
        logger.info(f"工作者已启动: {queue_name}")
    
    async def stop_worker(self, queue_name: str):
        """停止工作者"""
        if queue_name in self._workers:
            task = self._workers[queue_name]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._workers[queue_name]
            logger.info(f"工作者已停止: {queue_name}")
    
    async def _worker_loop(self, queue_name: str, handler: callable):
        """工作者循环"""
        logger.info(f"工作者循环开始: {queue_name}")
        
        while self._running:
            try:
                # 从队列中获取消息
                message = await self.queue.dequeue(queue_name, timeout=1)
                if message:
                    # 处理消息
                    await self._handle_message(message, handler)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"工作者 {queue_name} 处理消息失败: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"工作者循环结束: {queue_name}")
    
    async def _handle_message(self, message: UnifiedMessage, handler: callable):
        """处理消息"""
        try:
            # 更新消息状态
            message.status = MessageStatus.SENT
            
            # 调用处理器
            if asyncio.iscoroutinefunction(handler):
                response = await handler(message)
            else:
                response = handler(message)
            
            # 发布消息处理完成事件
            event = create_event(
                event_type="message.processed",
                platform=message.platform.value,
                message=message,
                data={"response": response}
            )
            await self.event_bus.publish(event)
            
        except Exception as e:
            logger.error(f"消息处理失败: {e}")
            
            # 更新消息状态
            message.status = MessageStatus.FAILED
            
            # 发布消息处理失败事件
            event = create_event(
                event_type="message.process_failed",
                platform=message.platform.value,
                message=message,
                data={"error": str(e)}
            )
            await self.event_bus.publish(event)
    
    async def _default_message_handler(self, message: UnifiedMessage) -> MessageResponse:
        """默认消息处理器"""
        logger.info(f"默认处理器处理消息: {message.message_id}")
        
        # 这里可以实现默认的消息处理逻辑
        # 例如：转发到AI服务、记录日志等
        
        return MessageResponse(
            response_id=str(uuid.uuid4()),
            original_message_id=message.message_id,
            responses=[],
            success=True
        )
    
    def register_platform_handler(self, platform: PlatformType, handler: callable):
        """注册平台处理器"""
        queue_name = f"platform:{platform.value}"
        self.router.register_platform_route(platform, queue_name)
        asyncio.create_task(self.start_worker(queue_name, handler))
    
    def register_message_handler(self, pattern: str, handler: callable):
        """注册消息处理器"""
        self.router.register_route(pattern, handler)


# 全局消息代理实例（稍后初始化）
message_broker: Optional[MessageBroker] = None


async def get_message_broker() -> MessageBroker:
    """获取消息代理实例"""
    global message_broker
    if not message_broker:
        from app.core.redis import get_redis
        from app.core.events import get_event_bus
        
        redis_client = await get_redis()
        event_bus = await get_event_bus()
        message_broker = MessageBroker(redis_client, event_bus)
    
    return message_broker