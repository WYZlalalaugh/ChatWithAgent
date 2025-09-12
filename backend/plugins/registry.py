"""
插件注册表
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from .base import PluginInfo, PluginType


class PluginRegistry:
    """插件注册表"""
    
    def __init__(self, registry_file: str = "./data/plugin_registry.json"):
        self.logger = logging.getLogger("plugins.registry")
        self.registry_file = Path(registry_file)
        
        # 确保目录存在
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 插件信息存储
        self._plugins: Dict[str, PluginInfo] = {}
        
        # 插件索引
        self._by_type: Dict[PluginType, Set[str]] = {}
        self._by_author: Dict[str, Set[str]] = {}
        self._by_tags: Dict[str, Set[str]] = {}
        
        # 加载注册表
        asyncio.create_task(self._load_registry())
    
    async def register(self, plugin_info: PluginInfo) -> bool:
        """注册插件"""
        try:
            # 检查插件是否已存在
            if plugin_info.name in self._plugins:
                existing = self._plugins[plugin_info.name]
                if existing.version == plugin_info.version:
                    self.logger.warning(f"Plugin {plugin_info.name} v{plugin_info.version} already registered")
                    return True
                else:
                    self.logger.info(f"Updating plugin {plugin_info.name} from v{existing.version} to v{plugin_info.version}")
            
            # 注册插件
            self._plugins[plugin_info.name] = plugin_info
            
            # 更新索引
            self._update_indexes(plugin_info)
            
            # 保存注册表
            await self._save_registry()
            
            self.logger.info(f"Registered plugin: {plugin_info.name} v{plugin_info.version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register plugin {plugin_info.name}: {e}")
            return False
    
    async def unregister(self, plugin_name: str) -> bool:
        """注销插件"""
        try:
            if plugin_name not in self._plugins:
                self.logger.warning(f"Plugin {plugin_name} not found in registry")
                return True
            
            plugin_info = self._plugins[plugin_name]
            
            # 移除插件
            del self._plugins[plugin_name]
            
            # 更新索引
            self._remove_from_indexes(plugin_info)
            
            # 保存注册表
            await self._save_registry()
            
            self.logger.info(f"Unregistered plugin: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister plugin {plugin_name}: {e}")
            return False
    
    async def get(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self._plugins.get(plugin_name)
    
    async def list_all(self) -> List[PluginInfo]:
        """列出所有插件"""
        return list(self._plugins.values())
    
    async def list_by_type(self, plugin_type: PluginType) -> List[PluginInfo]:
        """按类型列出插件"""
        plugin_names = self._by_type.get(plugin_type, set())
        return [self._plugins[name] for name in plugin_names if name in self._plugins]
    
    async def list_by_author(self, author: str) -> List[PluginInfo]:
        """按作者列出插件"""
        plugin_names = self._by_author.get(author, set())
        return [self._plugins[name] for name in plugin_names if name in self._plugins]
    
    async def list_by_tag(self, tag: str) -> List[PluginInfo]:
        """按标签列出插件"""
        plugin_names = self._by_tags.get(tag, set())
        return [self._plugins[name] for name in plugin_names if name in self._plugins]
    
    async def search(
        self,
        query: str = "",
        plugin_type: Optional[PluginType] = None,
        author: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[PluginInfo]:
        """搜索插件"""
        results = []
        
        for plugin_info in self._plugins.values():
            # 类型过滤
            if plugin_type and plugin_info.plugin_type != plugin_type:
                continue
            
            # 作者过滤
            if author and plugin_info.author.lower() != author.lower():
                continue
            
            # 标签过滤
            if tags:
                if not any(tag in plugin_info.tags for tag in tags):
                    continue
            
            # 文本搜索
            if query:
                query_lower = query.lower()
                if (query_lower not in plugin_info.name.lower() and
                    query_lower not in plugin_info.description.lower() and
                    not any(query_lower in tag.lower() for tag in plugin_info.tags)):
                    continue
            
            results.append(plugin_info)
        
        return results
    
    def _update_indexes(self, plugin_info: PluginInfo):
        """更新索引"""
        # 类型索引
        if plugin_info.plugin_type not in self._by_type:
            self._by_type[plugin_info.plugin_type] = set()
        self._by_type[plugin_info.plugin_type].add(plugin_info.name)
        
        # 作者索引
        if plugin_info.author not in self._by_author:
            self._by_author[plugin_info.author] = set()
        self._by_author[plugin_info.author].add(plugin_info.name)
        
        # 标签索引
        for tag in plugin_info.tags:
            if tag not in self._by_tags:
                self._by_tags[tag] = set()
            self._by_tags[tag].add(plugin_info.name)
    
    def _remove_from_indexes(self, plugin_info: PluginInfo):
        """从索引中移除"""
        # 类型索引
        if plugin_info.plugin_type in self._by_type:
            self._by_type[plugin_info.plugin_type].discard(plugin_info.name)
        
        # 作者索引
        if plugin_info.author in self._by_author:
            self._by_author[plugin_info.author].discard(plugin_info.name)
        
        # 标签索引
        for tag in plugin_info.tags:
            if tag in self._by_tags:
                self._by_tags[tag].discard(plugin_info.name)
    
    async def _load_registry(self):
        """加载注册表"""
        try:
            if not self.registry_file.exists():
                return
            
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 恢复插件信息
            for plugin_data in data.get('plugins', []):
                try:
                    plugin_info = self._dict_to_plugin_info(plugin_data)
                    self._plugins[plugin_info.name] = plugin_info
                    self._update_indexes(plugin_info)
                except Exception as e:
                    self.logger.error(f"Error loading plugin info: {e}")
            
            self.logger.info(f"Loaded {len(self._plugins)} plugins from registry")
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin registry: {e}")
    
    async def _save_registry(self):
        """保存注册表"""
        try:
            data = {
                'version': '1.0',
                'updated_at': datetime.utcnow().isoformat(),
                'plugins': [
                    self._plugin_info_to_dict(plugin_info)
                    for plugin_info in self._plugins.values()
                ]
            }
            
            # 原子写入
            temp_file = self.registry_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            temp_file.replace(self.registry_file)
            
        except Exception as e:
            self.logger.error(f"Failed to save plugin registry: {e}")
    
    def _plugin_info_to_dict(self, plugin_info: PluginInfo) -> Dict[str, Any]:
        """插件信息转字典"""
        return {
            'name': plugin_info.name,
            'version': plugin_info.version,
            'description': plugin_info.description,
            'author': plugin_info.author,
            'plugin_type': plugin_info.plugin_type.value,
            'entry_point': plugin_info.entry_point,
            'dependencies': plugin_info.dependencies,
            'permissions': plugin_info.permissions,
            'config_schema': plugin_info.config_schema,
            'min_system_version': plugin_info.min_system_version,
            'max_system_version': plugin_info.max_system_version,
            'tags': plugin_info.tags,
            'homepage': plugin_info.homepage,
            'repository': plugin_info.repository,
            'license': plugin_info.license
        }
    
    def _dict_to_plugin_info(self, data: Dict[str, Any]) -> PluginInfo:
        """字典转插件信息"""
        return PluginInfo(
            name=data['name'],
            version=data['version'],
            description=data['description'],
            author=data['author'],
            plugin_type=PluginType(data['plugin_type']),
            entry_point=data['entry_point'],
            dependencies=data.get('dependencies', []),
            permissions=data.get('permissions', []),
            config_schema=data.get('config_schema'),
            min_system_version=data.get('min_system_version'),
            max_system_version=data.get('max_system_version'),
            tags=data.get('tags', []),
            homepage=data.get('homepage'),
            repository=data.get('repository'),
            license=data.get('license')
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        type_counts = {}
        for plugin_type, plugin_names in self._by_type.items():
            type_counts[plugin_type.value] = len(plugin_names)
        
        author_counts = {
            author: len(plugin_names)
            for author, plugin_names in self._by_author.items()
        }
        
        tag_counts = {
            tag: len(plugin_names)
            for tag, plugin_names in self._by_tags.items()
        }
        
        return {
            'total_plugins': len(self._plugins),
            'by_type': type_counts,
            'by_author': author_counts,
            'by_tags': tag_counts,
            'top_authors': sorted(
                author_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            'popular_tags': sorted(
                tag_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }