"""
插件系统框架
"""

from .base import BasePlugin, PluginInfo
from .manager import PluginManager
from .loader import PluginLoader
from .events import EventBus, Event
from .registry import PluginRegistry
from .sandbox import PluginSandbox

__all__ = [
    'BasePlugin',
    'PluginInfo',
    'PluginManager', 
    'PluginLoader',
    'EventBus',
    'Event',
    'PluginRegistry',
    'PluginSandbox'
]