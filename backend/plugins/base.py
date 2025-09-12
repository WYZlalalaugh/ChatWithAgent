"""
插件基类和基本定义
"""

import abc
import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PluginState(str, Enum):
    """插件状态"""
    UNKNOWN = "unknown"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"
    DISABLED = "disabled"


class PluginType(str, Enum):
    """插件类型"""
    MESSAGE_HANDLER = "message_handler"
    COMMAND = "command"
    MIDDLEWARE = "middleware"
    TOOL = "tool"
    ADAPTER = "adapter"
    EXTENSION = "extension"
    SERVICE = "service"


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    entry_point: str
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    min_system_version: Optional[str] = None
    max_system_version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    
    def __post_init__(self):
        # 验证必需字段
        if not self.name:
            raise ValueError("Plugin name is required")
        if not self.version:
            raise ValueError("Plugin version is required")
        if not self.entry_point:
            raise ValueError("Plugin entry point is required")


@dataclass
class PluginContext:
    """插件上下文"""
    plugin_info: PluginInfo
    config: Dict[str, Any]
    data_dir: str
    temp_dir: str
    log_level: str = "INFO"
    permissions: Set[str] = field(default_factory=set)
    
    def get_logger(self) -> logging.Logger:
        """获取插件专用日志器"""
        logger = logging.getLogger(f"plugin.{self.plugin_info.name}")
        logger.setLevel(getattr(logging, self.log_level))
        return logger


class BasePlugin(abc.ABC):
    """插件基类"""
    
    def __init__(self, context: PluginContext):
        self.context = context
        self.logger = context.get_logger()
        self.state = PluginState.LOADED
        self.started_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        
        # 插件内部状态
        self._event_handlers: Dict[str, List[callable]] = {}
        self._config = context.config.copy()
        
    @abc.abstractmethod
    async def initialize(self) -> bool:
        """初始化插件"""
        pass
    
    @abc.abstractmethod
    async def start(self) -> bool:
        """启动插件"""
        pass
    
    @abc.abstractmethod
    async def stop(self) -> bool:
        """停止插件"""
        pass
    
    async def cleanup(self) -> bool:
        """清理插件资源"""
        try:
            # 清理事件处理器
            self._event_handlers.clear()
            
            # 子类可以重写这个方法来清理特定资源
            return await self._cleanup_resources()
            
        except Exception as e:
            self.logger.error(f"Plugin cleanup failed: {e}")
            return False
    
    async def _cleanup_resources(self) -> bool:
        """清理插件特定资源（子类重写）"""
        return True
    
    async def reload_config(self, new_config: Dict[str, Any]) -> bool:
        """重新加载配置"""
        try:
            old_config = self._config.copy()
            self._config.update(new_config)
            
            # 调用配置更新处理
            success = await self._on_config_changed(old_config, self._config)
            
            if not success:
                # 回滚配置
                self._config = old_config
                
            return success
            
        except Exception as e:
            self.logger.error(f"Config reload failed: {e}")
            return False
    
    async def _on_config_changed(
        self,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any]
    ) -> bool:
        """配置变更处理（子类重写）"""
        return True
    
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return self.context.plugin_info
    
    def get_state(self) -> PluginState:
        """获取插件状态"""
        return self.state
    
    def get_config(self, key: Optional[str] = None, default: Any = None) -> Any:
        """获取配置"""
        if key is None:
            return self._config.copy()
        return self._config.get(key, default)
    
    def set_config(self, key: str, value: Any):
        """设置配置"""
        self._config[key] = value
    
    def has_permission(self, permission: str) -> bool:
        """检查权限"""
        return permission in self.context.permissions
    
    def require_permission(self, permission: str):
        """要求权限"""
        if not self.has_permission(permission):
            raise PermissionError(f"Plugin requires permission: {permission}")
    
    def register_event_handler(self, event_type: str, handler: callable):
        """注册事件处理器"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def unregister_event_handler(self, event_type: str, handler: callable):
        """注销事件处理器"""
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    async def handle_event(self, event_type: str, event_data: Any) -> List[Any]:
        """处理事件"""
        results = []
        
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(event_data)
                    else:
                        result = handler(event_data)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Event handler error: {e}")
                    results.append(None)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取插件统计信息"""
        return {
            "name": self.context.plugin_info.name,
            "version": self.context.plugin_info.version,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "error_message": self.error_message,
            "event_handlers": {
                event_type: len(handlers)
                for event_type, handlers in self._event_handlers.items()
            },
            "config_keys": list(self._config.keys()),
            "permissions": list(self.context.permissions)
        }


class MessageHandlerPlugin(BasePlugin):
    """消息处理插件基类"""
    
    @abc.abstractmethod
    async def handle_message(self, message: Any) -> Optional[Any]:
        """处理消息"""
        pass
    
    async def can_handle_message(self, message: Any) -> bool:
        """检查是否可以处理消息"""
        return True


class CommandPlugin(BasePlugin):
    """命令插件基类"""
    
    def __init__(self, context: PluginContext):
        super().__init__(context)
        self.commands: Dict[str, callable] = {}
    
    @abc.abstractmethod
    def get_commands(self) -> Dict[str, str]:
        """获取命令列表 {command: description}"""
        pass
    
    @abc.abstractmethod
    async def execute_command(
        self,
        command: str,
        args: List[str],
        context: Dict[str, Any]
    ) -> Any:
        """执行命令"""
        pass
    
    def register_command(self, command: str, handler: callable, description: str = ""):
        """注册命令"""
        self.commands[command] = {
            "handler": handler,
            "description": description
        }


class ToolPlugin(BasePlugin):
    """工具插件基类"""
    
    @abc.abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        pass
    
    @abc.abstractmethod
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行工具"""
        pass


class ServicePlugin(BasePlugin):
    """服务插件基类"""
    
    def __init__(self, context: PluginContext):
        super().__init__(context)
        self.service_name = context.plugin_info.name
        self.is_running = False
    
    @abc.abstractmethod
    async def start_service(self) -> bool:
        """启动服务"""
        pass
    
    @abc.abstractmethod
    async def stop_service(self) -> bool:
        """停止服务"""
        pass
    
    @abc.abstractmethod
    async def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        pass


# 插件工厂
class PluginFactory:
    """插件工厂"""
    
    _plugin_classes = {
        PluginType.MESSAGE_HANDLER: MessageHandlerPlugin,
        PluginType.COMMAND: CommandPlugin,
        PluginType.TOOL: ToolPlugin,
        PluginType.SERVICE: ServicePlugin,
        PluginType.EXTENSION: BasePlugin,
        PluginType.MIDDLEWARE: BasePlugin,
        PluginType.ADAPTER: BasePlugin,
    }
    
    @classmethod
    def create_plugin(
        self,
        plugin_class: type,
        context: PluginContext
    ) -> BasePlugin:
        """创建插件实例"""
        if not issubclass(plugin_class, BasePlugin):
            raise TypeError("Plugin class must inherit from BasePlugin")
        
        return plugin_class(context)
    
    @classmethod
    def register_plugin_type(cls, plugin_type: PluginType, plugin_class: type):
        """注册插件类型"""
        cls._plugin_classes[plugin_type] = plugin_class
    
    @classmethod
    def get_base_class(cls, plugin_type: PluginType) -> type:
        """获取插件类型的基类"""
        return cls._plugin_classes.get(plugin_type, BasePlugin)