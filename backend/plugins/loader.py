"""
插件加载器
"""

import asyncio
import importlib
import importlib.util
import inspect
import json
import logging
import os
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type
import toml
import yaml

from .base import BasePlugin, PluginInfo, PluginContext, PluginType, PluginFactory


class PluginLoadError(Exception):
    """插件加载错误"""
    pass


class PluginLoader:
    """插件加载器"""
    
    def __init__(self, plugin_directories: List[str] = None):
        self.logger = logging.getLogger("plugins.loader")
        
        # 插件目录
        self.plugin_directories = plugin_directories or ["./plugins"]
        
        # 已加载的插件模块
        self._loaded_modules: Dict[str, Any] = {}
        
        # 插件信息缓存
        self._plugin_info_cache: Dict[str, PluginInfo] = {}
        
        # 支持的配置文件格式
        self.config_parsers = {
            ".json": json.load,
            ".yaml": yaml.safe_load,
            ".yml": yaml.safe_load,
            ".toml": toml.load
        }
        
        # 支持的插件包格式
        self.supported_formats = {".py", ".zip", ".pyz"}
    
    async def discover_plugins(self) -> List[PluginInfo]:
        """发现插件"""
        discovered_plugins = []
        
        for plugin_dir in self.plugin_directories:
            plugin_path = Path(plugin_dir)
            
            if not plugin_path.exists():
                self.logger.warning(f"Plugin directory not found: {plugin_dir}")
                continue
            
            # 扫描目录中的插件
            for item in plugin_path.iterdir():
                try:
                    plugin_info = await self._discover_plugin(item)
                    if plugin_info:
                        discovered_plugins.append(plugin_info)
                        self._plugin_info_cache[plugin_info.name] = plugin_info
                except Exception as e:
                    self.logger.error(f"Error discovering plugin in {item}: {e}")
        
        self.logger.info(f"Discovered {len(discovered_plugins)} plugins")
        return discovered_plugins
    
    async def _discover_plugin(self, plugin_path: Path) -> Optional[PluginInfo]:
        """发现单个插件"""
        if plugin_path.is_file():
            # 单文件插件
            if plugin_path.suffix in self.supported_formats:
                return await self._load_plugin_info_from_file(plugin_path)
        elif plugin_path.is_dir():
            # 目录插件
            return await self._load_plugin_info_from_directory(plugin_path)
        
        return None
    
    async def _load_plugin_info_from_file(self, file_path: Path) -> Optional[PluginInfo]:
        """从文件加载插件信息"""
        try:
            if file_path.suffix == ".py":
                # Python文件插件
                return await self._load_info_from_python_file(file_path)
            elif file_path.suffix in (".zip", ".pyz"):
                # 压缩包插件
                return await self._load_info_from_zip_file(file_path)
        except Exception as e:
            self.logger.error(f"Error loading plugin info from {file_path}: {e}")
        
        return None
    
    async def _load_plugin_info_from_directory(self, dir_path: Path) -> Optional[PluginInfo]:
        """从目录加载插件信息"""
        try:
            # 查找配置文件
            config_file = self._find_config_file(dir_path)
            if config_file:
                return await self._load_info_from_config_file(config_file, dir_path)
            
            # 查找主模块文件
            main_file = self._find_main_file(dir_path)
            if main_file:
                return await self._load_info_from_python_file(main_file)
            
        except Exception as e:
            self.logger.error(f"Error loading plugin info from directory {dir_path}: {e}")
        
        return None
    
    def _find_config_file(self, dir_path: Path) -> Optional[Path]:
        """查找配置文件"""
        config_names = ["plugin", "manifest"]
        
        for name in config_names:
            for ext in self.config_parsers.keys():
                config_file = dir_path / f"{name}{ext}"
                if config_file.exists():
                    return config_file
        
        return None
    
    def _find_main_file(self, dir_path: Path) -> Optional[Path]:
        """查找主模块文件"""
        main_files = ["__init__.py", "main.py", f"{dir_path.name}.py"]
        
        for main_file in main_files:
            file_path = dir_path / main_file
            if file_path.exists():
                return file_path
        
        return None
    
    async def _load_info_from_config_file(
        self,
        config_file: Path,
        plugin_dir: Path
    ) -> Optional[PluginInfo]:
        """从配置文件加载插件信息"""
        try:
            # 解析配置文件
            with open(config_file, 'r', encoding='utf-8') as f:
                parser = self.config_parsers[config_file.suffix]
                config_data = parser(f)
            
            # 构建插件信息
            plugin_info = self._build_plugin_info_from_config(config_data, plugin_dir)
            return plugin_info
            
        except Exception as e:
            self.logger.error(f"Error parsing config file {config_file}: {e}")
            return None
    
    async def _load_info_from_python_file(self, python_file: Path) -> Optional[PluginInfo]:
        """从Python文件加载插件信息"""
        try:
            # 临时加载模块以获取元数据
            spec = importlib.util.spec_from_file_location("temp_plugin", python_file)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找插件类
            plugin_class = self._find_plugin_class(module)
            if not plugin_class:
                return None
            
            # 从类或模块属性构建插件信息
            return self._build_plugin_info_from_class(plugin_class, python_file)
            
        except Exception as e:
            self.logger.error(f"Error loading info from Python file {python_file}: {e}")
            return None
    
    async def _load_info_from_zip_file(self, zip_file: Path) -> Optional[PluginInfo]:
        """从ZIP文件加载插件信息"""
        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                # 查找配置文件
                config_file = None
                for name in zf.namelist():
                    if any(name.endswith(f"plugin{ext}") or name.endswith(f"manifest{ext}")
                           for ext in self.config_parsers.keys()):
                        config_file = name
                        break
                
                if config_file:
                    # 从配置文件加载
                    with zf.open(config_file) as f:
                        ext = Path(config_file).suffix
                        parser = self.config_parsers[ext]
                        config_data = parser(f)
                    
                    return self._build_plugin_info_from_config(config_data, zip_file)
                
                # 查找主模块
                main_file = None
                for name in ["__init__.py", "main.py"]:
                    if name in zf.namelist():
                        main_file = name
                        break
                
                if main_file:
                    # 从Python代码加载
                    with zf.open(main_file) as f:
                        code = f.read().decode('utf-8')
                    
                    # 临时编译和执行代码
                    module = self._create_module_from_code(code, main_file)
                    plugin_class = self._find_plugin_class(module)
                    
                    if plugin_class:
                        return self._build_plugin_info_from_class(plugin_class, zip_file)
            
        except Exception as e:
            self.logger.error(f"Error loading info from ZIP file {zip_file}: {e}")
        
        return None
    
    def _build_plugin_info_from_config(
        self,
        config_data: Dict[str, Any],
        plugin_path: Path
    ) -> PluginInfo:
        """从配置数据构建插件信息"""
        # 必需字段
        name = config_data.get("name")
        version = config_data.get("version")
        description = config_data.get("description", "")
        author = config_data.get("author", "Unknown")
        entry_point = config_data.get("entry_point", "main.py")
        
        if not name or not version:
            raise PluginLoadError("Plugin name and version are required")
        
        # 插件类型
        plugin_type_str = config_data.get("type", "extension")
        try:
            plugin_type = PluginType(plugin_type_str)
        except ValueError:
            plugin_type = PluginType.EXTENSION
        
        # 可选字段
        dependencies = config_data.get("dependencies", [])
        permissions = config_data.get("permissions", [])
        config_schema = config_data.get("config_schema")
        min_system_version = config_data.get("min_system_version")
        max_system_version = config_data.get("max_system_version")
        tags = config_data.get("tags", [])
        homepage = config_data.get("homepage")
        repository = config_data.get("repository")
        license_info = config_data.get("license")
        
        return PluginInfo(
            name=name,
            version=version,
            description=description,
            author=author,
            plugin_type=plugin_type,
            entry_point=str(plugin_path / entry_point) if plugin_path.is_dir() else str(plugin_path),
            dependencies=dependencies,
            permissions=permissions,
            config_schema=config_schema,
            min_system_version=min_system_version,
            max_system_version=max_system_version,
            tags=tags,
            homepage=homepage,
            repository=repository,
            license=license_info
        )
    
    def _build_plugin_info_from_class(
        self,
        plugin_class: Type[BasePlugin],
        plugin_path: Path
    ) -> PluginInfo:
        """从插件类构建插件信息"""
        # 从类属性获取信息
        name = getattr(plugin_class, "PLUGIN_NAME", plugin_path.stem)
        version = getattr(plugin_class, "PLUGIN_VERSION", "1.0.0")
        description = getattr(plugin_class, "PLUGIN_DESCRIPTION", plugin_class.__doc__ or "")
        author = getattr(plugin_class, "PLUGIN_AUTHOR", "Unknown")
        plugin_type_str = getattr(plugin_class, "PLUGIN_TYPE", "extension")
        
        try:
            plugin_type = PluginType(plugin_type_str)
        except ValueError:
            plugin_type = PluginType.EXTENSION
        
        dependencies = getattr(plugin_class, "PLUGIN_DEPENDENCIES", [])
        permissions = getattr(plugin_class, "PLUGIN_PERMISSIONS", [])
        
        return PluginInfo(
            name=name,
            version=version,
            description=description,
            author=author,
            plugin_type=plugin_type,
            entry_point=str(plugin_path),
            dependencies=dependencies,
            permissions=permissions
        )
    
    def _find_plugin_class(self, module: Any) -> Optional[Type[BasePlugin]]:
        """在模块中查找插件类"""
        for name in dir(module):
            obj = getattr(module, name)
            
            if (inspect.isclass(obj) and
                issubclass(obj, BasePlugin) and
                obj != BasePlugin):
                return obj
        
        return None
    
    def _create_module_from_code(self, code: str, filename: str) -> Any:
        """从代码创建模块"""
        import types
        
        module = types.ModuleType("temp_plugin")
        module.__file__ = filename
        
        exec(code, module.__dict__)
        
        return module
    
    async def load_plugin(
        self,
        plugin_info: PluginInfo,
        config: Dict[str, Any],
        data_dir: str,
        temp_dir: str
    ) -> BasePlugin:
        """加载插件"""
        try:
            self.logger.info(f"Loading plugin: {plugin_info.name} v{plugin_info.version}")
            
            # 检查依赖
            await self._check_dependencies(plugin_info)
            
            # 加载插件模块
            plugin_module = await self._load_plugin_module(plugin_info)
            
            # 查找插件类
            plugin_class = self._find_plugin_class(plugin_module)
            if not plugin_class:
                raise PluginLoadError(f"No plugin class found in {plugin_info.entry_point}")
            
            # 创建插件上下文
            context = PluginContext(
                plugin_info=plugin_info,
                config=config,
                data_dir=data_dir,
                temp_dir=temp_dir,
                permissions=set(plugin_info.permissions)
            )
            
            # 创建插件实例
            plugin_instance = PluginFactory.create_plugin(plugin_class, context)
            
            # 存储模块引用
            self._loaded_modules[plugin_info.name] = plugin_module
            
            self.logger.info(f"Successfully loaded plugin: {plugin_info.name}")
            return plugin_instance
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_info.name}: {e}")
            raise PluginLoadError(f"Failed to load plugin {plugin_info.name}: {e}")
    
    async def _check_dependencies(self, plugin_info: PluginInfo):
        """检查插件依赖"""
        for dependency in plugin_info.dependencies:
            if dependency not in self._plugin_info_cache:
                raise PluginLoadError(f"Missing dependency: {dependency}")
            
            # 这里可以添加版本检查逻辑
    
    async def _load_plugin_module(self, plugin_info: PluginInfo) -> Any:
        """加载插件模块"""
        entry_point = Path(plugin_info.entry_point)
        
        if entry_point.suffix == ".py":
            # Python文件
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_info.name}",
                entry_point
            )
            if not spec or not spec.loader:
                raise PluginLoadError(f"Cannot load spec for {entry_point}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            return module
            
        elif entry_point.suffix in (".zip", ".pyz"):
            # ZIP包
            sys.path.insert(0, str(entry_point))
            try:
                module = importlib.import_module("__main__")
                return module
            finally:
                sys.path.remove(str(entry_point))
                
        elif entry_point.is_dir():
            # 目录包
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_info.name}",
                entry_point / "__init__.py"
            )
            if not spec or not spec.loader:
                raise PluginLoadError(f"Cannot load spec for {entry_point}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            return module
        
        else:
            raise PluginLoadError(f"Unsupported plugin format: {entry_point}")
    
    async def unload_plugin(self, plugin_name: str):
        """卸载插件"""
        try:
            if plugin_name in self._loaded_modules:
                # 从sys.modules中移除
                module = self._loaded_modules[plugin_name]
                module_name = getattr(module, "__name__", None)
                
                if module_name and module_name in sys.modules:
                    del sys.modules[module_name]
                
                # 从缓存中移除
                del self._loaded_modules[plugin_name]
                
                self.logger.info(f"Unloaded plugin: {plugin_name}")
            
        except Exception as e:
            self.logger.error(f"Error unloading plugin {plugin_name}: {e}")
    
    def get_loaded_modules(self) -> Dict[str, Any]:
        """获取已加载的模块"""
        return self._loaded_modules.copy()
    
    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """检查插件是否已加载"""
        return plugin_name in self._loaded_modules
    
    def add_plugin_directory(self, directory: str):
        """添加插件目录"""
        if directory not in self.plugin_directories:
            self.plugin_directories.append(directory)
    
    def remove_plugin_directory(self, directory: str):
        """移除插件目录"""
        if directory in self.plugin_directories:
            self.plugin_directories.remove(directory)