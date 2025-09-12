"""
插件管理器
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from .base import BasePlugin, PluginInfo, PluginState, PluginType
from .loader import PluginLoader, PluginLoadError
from .events import EventBus, get_event_bus, Event
from .registry import PluginRegistry
from .sandbox import PluginSandbox
from app.config import settings


class PluginManager:
    """插件管理器"""
    
    def __init__(
        self,
        plugin_directories: Optional[List[str]] = None,
        data_directory: str = "./data/plugins",
        temp_directory: str = "./temp/plugins"
    ):
        self.logger = logging.getLogger("plugins.manager")
        
        # 目录配置
        self.data_directory = Path(data_directory)
        self.temp_directory = Path(temp_directory)
        
        # 创建目录
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.temp_directory.mkdir(parents=True, exist_ok=True)
        
        # 核心组件
        self.loader = PluginLoader(plugin_directories)
        self.registry = PluginRegistry()
        self.event_bus = get_event_bus()
        self.sandbox = PluginSandbox()
        
        # 插件实例存储
        self._plugins: Dict[str, BasePlugin] = {}
        
        # 插件配置
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        
        # 插件依赖图
        self._dependency_graph: Dict[str, Set[str]] = {}
        
        # 启动顺序
        self._startup_order: List[str] = []
        
        # 状态
        self._is_started = False
        
        # 统计信息
        self._stats = {
            "loaded_count": 0,
            "active_count": 0,
            "error_count": 0,
            "total_events_handled": 0
        }
    
    async def initialize(self):
        """初始化插件管理器"""
        try:
            self.logger.info("Initializing plugin manager...")
            
            # 启动事件总线
            await self.event_bus.start()
            
            # 发现插件
            await self.discover_plugins()
            
            # 加载配置
            await self._load_plugin_configs()
            
            self.logger.info("Plugin manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Plugin manager initialization failed: {e}")
            raise
    
    async def discover_plugins(self) -> List[PluginInfo]:
        """发现插件"""
        try:
            self.logger.info("Discovering plugins...")
            
            plugins = await self.loader.discover_plugins()
            
            # 注册到插件注册表
            for plugin_info in plugins:
                await self.registry.register(plugin_info)
            
            self.logger.info(f"Discovered {len(plugins)} plugins")
            return plugins
            
        except Exception as e:
            self.logger.error(f"Plugin discovery failed: {e}")
            return []
    
    async def load_plugin(
        self,
        plugin_name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """加载插件"""
        try:
            # 检查插件是否已加载
            if plugin_name in self._plugins:
                self.logger.warning(f"Plugin {plugin_name} is already loaded")
                return True
            
            # 获取插件信息
            plugin_info = await self.registry.get(plugin_name)
            if not plugin_info:
                self.logger.error(f"Plugin {plugin_name} not found in registry")
                return False
            
            # 检查依赖
            if not await self._check_dependencies(plugin_info):
                self.logger.error(f"Dependency check failed for plugin {plugin_name}")
                return False
            
            # 获取配置
            plugin_config = config or self._plugin_configs.get(plugin_name, {})
            
            # 创建插件数据目录
            plugin_data_dir = self.data_directory / plugin_name
            plugin_temp_dir = self.temp_directory / plugin_name
            
            plugin_data_dir.mkdir(exist_ok=True)
            plugin_temp_dir.mkdir(exist_ok=True)
            
            # 加载插件
            plugin_instance = await self.loader.load_plugin(
                plugin_info=plugin_info,
                config=plugin_config,
                data_dir=str(plugin_data_dir),
                temp_dir=str(plugin_temp_dir)
            )
            
            # 在沙箱中运行插件初始化
            success = await self.sandbox.run_in_sandbox(
                plugin_instance.initialize,
                plugin_name
            )
            
            if not success:
                self.logger.error(f"Plugin {plugin_name} initialization failed")
                return False
            
            # 存储插件实例
            self._plugins[plugin_name] = plugin_instance
            plugin_instance.state = PluginState.INITIALIZED
            
            # 注册到事件总线
            self.event_bus.register_plugin(plugin_name, plugin_instance)
            
            # 自动注册事件处理器
            await self._register_event_handlers(plugin_instance)
            
            # 更新统计
            self._stats["loaded_count"] += 1
            
            # 发出插件加载事件
            await self.event_bus.emit(
                "plugin.loaded",
                {"plugin_name": plugin_name, "plugin_info": plugin_info},
                source="plugin_manager"
            )
            
            self.logger.info(f"Plugin {plugin_name} loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_name}: {e}")
            
            # 清理
            if plugin_name in self._plugins:
                del self._plugins[plugin_name]
            
            self._stats["error_count"] += 1
            return False
    
    async def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        try:
            if plugin_name not in self._plugins:
                self.logger.warning(f"Plugin {plugin_name} is not loaded")
                return True
            
            plugin_instance = self._plugins[plugin_name]
            
            # 停止插件
            if plugin_instance.state == PluginState.STARTED:
                await self.stop_plugin(plugin_name)
            
            # 清理插件资源
            await plugin_instance.cleanup()
            
            # 从事件总线注销
            self.event_bus.unregister_plugin(plugin_name)
            
            # 卸载模块
            await self.loader.unload_plugin(plugin_name)
            
            # 移除插件实例
            del self._plugins[plugin_name]
            
            # 更新统计
            self._stats["loaded_count"] -= 1
            if plugin_instance.state == PluginState.STARTED:
                self._stats["active_count"] -= 1
            
            # 发出插件卸载事件
            await self.event_bus.emit(
                "plugin.unloaded",
                {"plugin_name": plugin_name},
                source="plugin_manager"
            )
            
            self.logger.info(f"Plugin {plugin_name} unloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False
    
    async def start_plugin(self, plugin_name: str) -> bool:
        """启动插件"""
        try:
            if plugin_name not in self._plugins:
                self.logger.error(f"Plugin {plugin_name} is not loaded")
                return False
            
            plugin_instance = self._plugins[plugin_name]
            
            if plugin_instance.state == PluginState.STARTED:
                self.logger.warning(f"Plugin {plugin_name} is already started")
                return True
            
            # 在沙箱中启动插件
            success = await self.sandbox.run_in_sandbox(
                plugin_instance.start,
                plugin_name
            )
            
            if success:
                plugin_instance.state = PluginState.STARTED
                plugin_instance.started_at = datetime.utcnow()
                
                # 更新统计
                self._stats["active_count"] += 1
                
                # 发出插件启动事件
                await self.event_bus.emit(
                    "plugin.started",
                    {"plugin_name": plugin_name},
                    source="plugin_manager"
                )
                
                self.logger.info(f"Plugin {plugin_name} started successfully")
                return True
            else:
                plugin_instance.state = PluginState.ERROR
                plugin_instance.error_message = "Start failed"
                self._stats["error_count"] += 1
                
                self.logger.error(f"Failed to start plugin {plugin_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting plugin {plugin_name}: {e}")
            
            if plugin_name in self._plugins:
                self._plugins[plugin_name].state = PluginState.ERROR
                self._plugins[plugin_name].error_message = str(e)
                self._stats["error_count"] += 1
            
            return False
    
    async def stop_plugin(self, plugin_name: str) -> bool:
        """停止插件"""
        try:
            if plugin_name not in self._plugins:
                self.logger.error(f"Plugin {plugin_name} is not loaded")
                return False
            
            plugin_instance = self._plugins[plugin_name]
            
            if plugin_instance.state != PluginState.STARTED:
                self.logger.warning(f"Plugin {plugin_name} is not running")
                return True
            
            # 在沙箱中停止插件
            success = await self.sandbox.run_in_sandbox(
                plugin_instance.stop,
                plugin_name
            )
            
            if success:
                plugin_instance.state = PluginState.STOPPED
                
                # 更新统计
                self._stats["active_count"] -= 1
                
                # 发出插件停止事件
                await self.event_bus.emit(
                    "plugin.stopped",
                    {"plugin_name": plugin_name},
                    source="plugin_manager"
                )
                
                self.logger.info(f"Plugin {plugin_name} stopped successfully")
                return True
            else:
                self.logger.error(f"Failed to stop plugin {plugin_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error stopping plugin {plugin_name}: {e}")
            return False
    
    async def restart_plugin(self, plugin_name: str) -> bool:
        """重启插件"""
        try:
            await self.stop_plugin(plugin_name)
            return await self.start_plugin(plugin_name)
        except Exception as e:
            self.logger.error(f"Error restarting plugin {plugin_name}: {e}")
            return False
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        try:
            # 保存配置
            config = self._plugin_configs.get(plugin_name)
            
            # 卸载插件
            await self.unload_plugin(plugin_name)
            
            # 重新加载插件
            return await self.load_plugin(plugin_name, config)
            
        except Exception as e:
            self.logger.error(f"Error reloading plugin {plugin_name}: {e}")
            return False
    
    async def start_all(self) -> bool:
        """启动所有插件"""
        try:
            self.logger.info("Starting all plugins...")
            
            # 计算启动顺序
            startup_order = self._calculate_startup_order()
            
            success_count = 0
            
            for plugin_name in startup_order:
                if await self.start_plugin(plugin_name):
                    success_count += 1
            
            self._is_started = True
            
            self.logger.info(f"Started {success_count}/{len(startup_order)} plugins")
            return success_count == len(startup_order)
            
        except Exception as e:
            self.logger.error(f"Error starting all plugins: {e}")
            return False
    
    async def stop_all(self) -> bool:
        """停止所有插件"""
        try:
            self.logger.info("Stopping all plugins...")
            
            # 按相反顺序停止
            stop_order = list(reversed(self._startup_order))
            
            success_count = 0
            
            for plugin_name in stop_order:
                if await self.stop_plugin(plugin_name):
                    success_count += 1
            
            self._is_started = False
            
            self.logger.info(f"Stopped {success_count}/{len(stop_order)} plugins")
            return success_count == len(stop_order)
            
        except Exception as e:
            self.logger.error(f"Error stopping all plugins: {e}")
            return False
    
    async def shutdown(self):
        """关闭插件管理器"""
        try:
            self.logger.info("Shutting down plugin manager...")
            
            # 停止所有插件
            await self.stop_all()
            
            # 卸载所有插件
            for plugin_name in list(self._plugins.keys()):
                await self.unload_plugin(plugin_name)
            
            # 停止事件总线
            await self.event_bus.stop()
            
            # 清理临时目录
            if self.temp_directory.exists():
                shutil.rmtree(self.temp_directory)
            
            self.logger.info("Plugin manager shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during plugin manager shutdown: {e}")
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """获取插件实例"""
        return self._plugins.get(plugin_name)
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        plugin = self.get_plugin(plugin_name)
        return plugin.get_info() if plugin else None
    
    def list_plugins(self) -> List[str]:
        """列出所有插件"""
        return list(self._plugins.keys())
    
    def list_plugins_by_type(self, plugin_type: PluginType) -> List[str]:
        """按类型列出插件"""
        return [
            name for name, plugin in self._plugins.items()
            if plugin.get_info().plugin_type == plugin_type
        ]
    
    def get_plugin_states(self) -> Dict[str, PluginState]:
        """获取所有插件状态"""
        return {
            name: plugin.get_state()
            for name, plugin in self._plugins.items()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        active_by_type = {}
        error_plugins = []
        
        for name, plugin in self._plugins.items():
            plugin_type = plugin.get_info().plugin_type.value
            
            if plugin.get_state() == PluginState.STARTED:
                active_by_type[plugin_type] = active_by_type.get(plugin_type, 0) + 1
            elif plugin.get_state() == PluginState.ERROR:
                error_plugins.append({
                    "name": name,
                    "error": plugin.error_message
                })
        
        return {
            **self._stats,
            "active_by_type": active_by_type,
            "error_plugins": error_plugins,
            "event_bus_stats": self.event_bus.get_event_stats()
        }
    
    async def _check_dependencies(self, plugin_info: PluginInfo) -> bool:
        """检查插件依赖"""
        for dependency in plugin_info.dependencies:
            if dependency not in self._plugins:
                # 尝试加载依赖
                if not await self.load_plugin(dependency):
                    return False
        return True
    
    def _calculate_startup_order(self) -> List[str]:
        """计算插件启动顺序"""
        if self._startup_order:
            return self._startup_order
        
        # 拓扑排序
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(plugin_name: str):
            if plugin_name in temp_visited:
                raise Exception(f"Circular dependency detected: {plugin_name}")
            
            if plugin_name not in visited:
                temp_visited.add(plugin_name)
                
                # 访问依赖
                plugin = self._plugins.get(plugin_name)
                if plugin:
                    for dependency in plugin.get_info().dependencies:
                        if dependency in self._plugins:
                            visit(dependency)
                
                temp_visited.remove(plugin_name)
                visited.add(plugin_name)
                order.append(plugin_name)
        
        # 访问所有插件
        for plugin_name in self._plugins.keys():
            if plugin_name not in visited:
                visit(plugin_name)
        
        self._startup_order = order
        return order
    
    async def _register_event_handlers(self, plugin_instance: BasePlugin):
        """注册插件的事件处理器"""
        try:
            # 查找带有事件处理器装饰器的方法
            for attr_name in dir(plugin_instance):
                attr = getattr(plugin_instance, attr_name)
                
                if hasattr(attr, "_event_name"):
                    self.event_bus.subscribe(
                        event_name=attr._event_name,
                        handler=attr,
                        priority=getattr(attr, "_event_priority", 20),
                        once=getattr(attr, "_event_once", False),
                        conditions=getattr(attr, "_event_conditions", None),
                        plugin_name=plugin_instance.get_info().name
                    )
                    
                    self.logger.debug(
                        f"Registered event handler: {attr_name} for event: {attr._event_name}"
                    )
        
        except Exception as e:
            self.logger.error(f"Error registering event handlers: {e}")
    
    async def _load_plugin_configs(self):
        """加载插件配置"""
        config_file = self.data_directory / "configs.json"
        
        if config_file.exists():
            try:
                import json
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._plugin_configs = json.load(f)
                
                self.logger.info("Plugin configurations loaded")
            except Exception as e:
                self.logger.error(f"Error loading plugin configurations: {e}")
    
    async def save_plugin_configs(self):
        """保存插件配置"""
        config_file = self.data_directory / "configs.json"
        
        try:
            import json
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self._plugin_configs, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Plugin configurations saved")
        except Exception as e:
            self.logger.error(f"Error saving plugin configurations: {e}")
    
    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]):
        """设置插件配置"""
        self._plugin_configs[plugin_name] = config
    
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """获取插件配置"""
        return self._plugin_configs.get(plugin_name, {})


# 全局插件管理器实例
global_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器实例"""
    global global_plugin_manager
    if global_plugin_manager is None:
        plugin_dirs = getattr(settings, 'PLUGIN_DIRECTORIES', ["./plugins"])
        global_plugin_manager = PluginManager(plugin_directories=plugin_dirs)
    return global_plugin_manager