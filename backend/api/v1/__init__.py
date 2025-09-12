"""
API v1版本模块
"""

from .auth import router as auth_router
from .users import router as users_router
from .bots import router as bots_router
from .conversations import router as conversations_router
from .messages import router as messages_router
from .knowledge import router as knowledge_router
from .plugins import router as plugins_router
from .system import router as system_router

__all__ = [
    'auth_router',
    'users_router', 
    'bots_router',
    'conversations_router',
    'messages_router',
    'knowledge_router',
    'plugins_router',
    'system_router'
]