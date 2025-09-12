"""
插件事件总线系统
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
import weakref


class EventPriority(int, Enum):
    """事件优先级"""
    LOWEST = 0
    LOW = 10
    NORMAL = 20
    HIGH = 30
    HIGHEST = 40


@dataclass
class Event:
    """事件对象"""
    name: str
    data: Any
    source: Optional[str] = None
    timestamp: float = None
    metadata: Optional[Dict[str, Any]] = None
    cancelled: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.metadata is None:
            self.metadata = {}
    
    def cancel(self):
        """取消事件"""
        self.cancelled = True
    
    def is_cancelled(self) -> bool:
        """检查事件是否被取消"""
        return self.cancelled


@dataclass
class EventHandler:
    """事件处理器"""
    handler: Callable
    priority: EventPriority
    once: bool = False  # 是否只执行一次
    conditions: Optional[Dict[str, Any]] = None  # 执行条件
    
    async def __call__(self, event: Event) -> Any:
        """调用处理器"""
        # 检查执行条件
        if self.conditions and not self._check_conditions(event):
            return None
        
        try:
            if asyncio.iscoroutinefunction(self.handler):
                return await self.handler(event)
            else:
                return self.handler(event)
        except Exception as e:
            logging.error(f"Event handler error: {e}")
            return None
    
    def _check_conditions(self, event: Event) -> bool:
        """检查执行条件"""
        for key, expected_value in self.conditions.items():
            if key == "source":
                if event.source != expected_value:
                    return False
            elif key in event.metadata:
                if event.metadata[key] != expected_value:
                    return False
            else:
                return False
        return True


class EventBus:
    """事件总线"""
    
    def __init__(self):
        self.logger = logging.getLogger("plugins.event_bus")
        
        # 事件处理器存储 {event_name: [EventHandler]}
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        
        # 通配符处理器
        self._wildcard_handlers: List[EventHandler] = []
        
        # 事件统计
        self._event_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "emitted": 0,
            "handled": 0,
            "errors": 0
        })
        
        # 事件历史（用于调试）
        self._event_history: List[Event] = []
        self._max_history_size = 1000
        
        # 异步任务队列
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # 插件引用（弱引用，避免循环引用）
        self._plugin_refs: Dict[str, weakref.ref] = {}
    
    async def start(self):
        """启动事件总线"""
        if self._is_running:
            return
        
        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_events())
        self.logger.info("Event bus started")
    
    async def stop(self):
        """停止事件总线"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        # 清空队列
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        self.logger.info("Event bus stopped")
    
    async def _process_events(self):
        """处理事件队列"""
        while self._is_running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._handle_event_internal(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Event processing error: {e}")
    
    def subscribe(
        self,
        event_name: str,
        handler: Callable,
        priority: EventPriority = EventPriority.NORMAL,
        once: bool = False,
        conditions: Optional[Dict[str, Any]] = None,
        plugin_name: Optional[str] = None
    ):
        """订阅事件"""
        event_handler = EventHandler(
            handler=handler,
            priority=priority,
            once=once,
            conditions=conditions
        )
        
        if event_name == "*":
            # 通配符处理器
            self._wildcard_handlers.append(event_handler)
            self._wildcard_handlers.sort(key=lambda h: h.priority, reverse=True)
        else:
            # 普通事件处理器
            self._handlers[event_name].append(event_handler)
            self._handlers[event_name].sort(key=lambda h: h.priority, reverse=True)
        
        self.logger.debug(f"Subscribed to event: {event_name} (plugin: {plugin_name})")
    
    def unsubscribe(self, event_name: str, handler: Callable):
        """取消订阅事件"""
        if event_name == "*":
            self._wildcard_handlers = [
                h for h in self._wildcard_handlers
                if h.handler != handler
            ]
        else:
            self._handlers[event_name] = [
                h for h in self._handlers[event_name]
                if h.handler != handler
            ]
        
        self.logger.debug(f"Unsubscribed from event: {event_name}")
    
    def unsubscribe_all(self, plugin_name: str):
        """取消插件的所有订阅"""
        # 这里需要更复杂的实现来跟踪插件的处理器
        # 暂时通过插件引用来实现
        if plugin_name in self._plugin_refs:
            plugin_ref = self._plugin_refs[plugin_name]
            plugin = plugin_ref()
            
            if plugin:
                # 移除该插件的所有处理器
                for event_name in list(self._handlers.keys()):
                    self._handlers[event_name] = [
                        h for h in self._handlers[event_name]
                        if getattr(h.handler, '__self__', None) != plugin
                    ]
                
                # 移除通配符处理器
                self._wildcard_handlers = [
                    h for h in self._wildcard_handlers
                    if getattr(h.handler, '__self__', None) != plugin
                ]
            
            del self._plugin_refs[plugin_name]
    
    async def emit(
        self,
        event_name: str,
        data: Any = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        wait: bool = False
    ) -> Optional[List[Any]]:
        """发出事件"""
        event = Event(
            name=event_name,
            data=data,
            source=source,
            metadata=metadata or {}
        )
        
        # 更新统计
        self._event_stats[event_name]["emitted"] += 1
        
        # 添加到历史记录
        self._add_to_history(event)
        
        if wait:
            # 同步处理
            return await self._handle_event_internal(event)
        else:
            # 异步处理
            if self._is_running:
                await self._event_queue.put(event)
            else:
                # 如果事件总线未运行，直接处理
                return await self._handle_event_internal(event)
            
            return None
    
    async def _handle_event_internal(self, event: Event) -> List[Any]:
        """内部事件处理"""
        results = []
        
        try:
            # 获取事件处理器
            handlers = self._handlers.get(event.name, []) + self._wildcard_handlers
            
            # 按优先级执行处理器
            handlers_to_remove = []
            
            for handler in handlers:
                if event.is_cancelled():
                    break
                
                try:
                    result = await handler(event)
                    results.append(result)
                    
                    # 标记一次性处理器用于移除
                    if handler.once:
                        handlers_to_remove.append((event.name, handler))
                    
                    self._event_stats[event.name]["handled"] += 1
                    
                except Exception as e:
                    self.logger.error(f"Handler error for event {event.name}: {e}")
                    self._event_stats[event.name]["errors"] += 1
                    results.append(None)
            
            # 移除一次性处理器
            for event_name, handler in handlers_to_remove:
                if event_name in self._handlers:
                    try:
                        self._handlers[event_name].remove(handler)
                    except ValueError:
                        pass
                else:
                    try:
                        self._wildcard_handlers.remove(handler)
                    except ValueError:
                        pass
            
            return results
            
        except Exception as e:
            self.logger.error(f"Event handling error for {event.name}: {e}")
            self._event_stats[event.name]["errors"] += 1
            return []
    
    def _add_to_history(self, event: Event):
        """添加到事件历史"""
        self._event_history.append(event)
        
        # 限制历史记录大小
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
    
    def register_plugin(self, plugin_name: str, plugin_instance):
        """注册插件"""
        self._plugin_refs[plugin_name] = weakref.ref(plugin_instance)
    
    def unregister_plugin(self, plugin_name: str):
        """注销插件"""
        self.unsubscribe_all(plugin_name)
    
    def get_subscribers(self, event_name: str) -> List[str]:
        """获取事件订阅者"""
        handlers = self._handlers.get(event_name, [])
        subscribers = []
        
        for handler in handlers:
            handler_name = getattr(handler.handler, '__name__', 'unknown')
            subscribers.append(handler_name)
        
        return subscribers
    
    def get_event_stats(self) -> Dict[str, Dict[str, int]]:
        """获取事件统计"""
        return dict(self._event_stats)
    
    def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取事件历史"""
        recent_events = self._event_history[-limit:]
        
        return [
            {
                "name": event.name,
                "source": event.source,
                "timestamp": event.timestamp,
                "cancelled": event.cancelled,
                "metadata": event.metadata
            }
            for event in recent_events
        ]
    
    def clear_history(self):
        """清空事件历史"""
        self._event_history.clear()
    
    def get_handler_count(self) -> Dict[str, int]:
        """获取处理器数量统计"""
        stats = {}
        
        for event_name, handlers in self._handlers.items():
            stats[event_name] = len(handlers)
        
        stats["*"] = len(self._wildcard_handlers)
        
        return stats


# 事件装饰器
def event_handler(
    event_name: str,
    priority: EventPriority = EventPriority.NORMAL,
    once: bool = False,
    conditions: Optional[Dict[str, Any]] = None
):
    """事件处理器装饰器"""
    def decorator(func):
        func._event_name = event_name
        func._event_priority = priority
        func._event_once = once
        func._event_conditions = conditions
        return func
    
    return decorator


# 全局事件总线实例
global_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """获取全局事件总线"""
    return global_event_bus


# 便捷函数
async def emit_event(
    event_name: str,
    data: Any = None,
    source: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    wait: bool = False
):
    """发出事件（便捷函数）"""
    return await global_event_bus.emit(event_name, data, source, metadata, wait)


def subscribe_event(
    event_name: str,
    handler: Callable,
    priority: EventPriority = EventPriority.NORMAL,
    once: bool = False,
    conditions: Optional[Dict[str, Any]] = None,
    plugin_name: Optional[str] = None
):
    """订阅事件（便捷函数）"""
    global_event_bus.subscribe(event_name, handler, priority, once, conditions, plugin_name)


def unsubscribe_event(event_name: str, handler: Callable):
    """取消订阅事件（便捷函数）"""
    global_event_bus.unsubscribe(event_name, handler)