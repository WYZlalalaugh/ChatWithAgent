"""
权限管理系统
"""

import logging
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PermissionType(str, Enum):
    """权限类型"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class ResourceType(str, Enum):
    """资源类型"""
    USER = "user"
    BOT = "bot"
    CONVERSATION = "conversation"
    MESSAGE = "message"
    KNOWLEDGE_BASE = "knowledge_base"
    PLUGIN = "plugin"
    SYSTEM = "system"
    API = "api"


@dataclass
class Permission:
    """权限定义"""
    name: str
    resource_type: ResourceType
    permission_type: PermissionType
    description: str
    is_system: bool = False  # 是否为系统权限
    
    def __str__(self) -> str:
        return f"{self.resource_type.value}.{self.permission_type.value}"
    
    def __hash__(self) -> int:
        return hash(self.name)


@dataclass
class Role:
    """角色定义"""
    name: str
    description: str
    permissions: Set[Permission] = field(default_factory=set)
    is_system: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_permission(self, permission: Permission):
        """添加权限"""
        self.permissions.add(permission)
    
    def remove_permission(self, permission: Permission):
        """移除权限"""
        self.permissions.discard(permission)
    
    def has_permission(self, permission: Permission) -> bool:
        """检查是否有权限"""
        return permission in self.permissions
    
    def get_permission_names(self) -> Set[str]:
        """获取权限名称集合"""
        return {perm.name for perm in self.permissions}


@dataclass
class UserPermission:
    """用户权限"""
    user_id: str
    roles: Set[Role] = field(default_factory=set)
    direct_permissions: Set[Permission] = field(default_factory=set)
    denied_permissions: Set[Permission] = field(default_factory=set)
    
    def get_effective_permissions(self) -> Set[Permission]:
        """获取有效权限"""
        # 从角色获取权限
        role_permissions = set()
        for role in self.roles:
            role_permissions.update(role.permissions)
        
        # 合并直接权限
        all_permissions = role_permissions | self.direct_permissions
        
        # 移除被拒绝的权限
        effective_permissions = all_permissions - self.denied_permissions
        
        return effective_permissions
    
    def has_permission(self, permission: Permission) -> bool:
        """检查是否有权限"""
        return permission in self.get_effective_permissions()
    
    def has_permission_by_name(self, permission_name: str) -> bool:
        """通过权限名检查是否有权限"""
        effective_perms = self.get_effective_permissions()
        return permission_name in {perm.name for perm in effective_perms}


class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger("security.permissions")
        
        # 权限注册表
        self.permissions: Dict[str, Permission] = {}
        
        # 角色注册表
        self.roles: Dict[str, Role] = {}
        
        # 用户权限缓存
        self.user_permissions: Dict[str, UserPermission] = {}
        
        # 初始化系统权限和角色
        self._initialize_system_permissions()
        self._initialize_system_roles()
    
    def _initialize_system_permissions(self):
        """初始化系统权限"""
        # 用户相关权限
        self.register_permission(Permission(
            "user.read", ResourceType.USER, PermissionType.READ,
            "读取用户信息", is_system=True
        ))
        self.register_permission(Permission(
            "user.write", ResourceType.USER, PermissionType.WRITE,
            "修改用户信息", is_system=True
        ))
        self.register_permission(Permission(
            "user.delete", ResourceType.USER, PermissionType.DELETE,
            "删除用户", is_system=True
        ))
        self.register_permission(Permission(
            "user.admin", ResourceType.USER, PermissionType.ADMIN,
            "用户管理", is_system=True
        ))
        
        # 机器人相关权限
        self.register_permission(Permission(
            "bot.read", ResourceType.BOT, PermissionType.READ,
            "查看机器人", is_system=True
        ))
        self.register_permission(Permission(
            "bot.write", ResourceType.BOT, PermissionType.WRITE,
            "修改机器人", is_system=True
        ))
        self.register_permission(Permission(
            "bot.delete", ResourceType.BOT, PermissionType.DELETE,
            "删除机器人", is_system=True
        ))
        self.register_permission(Permission(
            "bot.execute", ResourceType.BOT, PermissionType.EXECUTE,
            "执行机器人", is_system=True
        ))
        
        # 对话相关权限
        self.register_permission(Permission(
            "conversation.read", ResourceType.CONVERSATION, PermissionType.READ,
            "查看对话", is_system=True
        ))
        self.register_permission(Permission(
            "conversation.write", ResourceType.CONVERSATION, PermissionType.WRITE,
            "修改对话", is_system=True
        ))
        self.register_permission(Permission(
            "conversation.delete", ResourceType.CONVERSATION, PermissionType.DELETE,
            "删除对话", is_system=True
        ))
        
        # 消息相关权限
        self.register_permission(Permission(
            "message.read", ResourceType.MESSAGE, PermissionType.READ,
            "查看消息", is_system=True
        ))
        self.register_permission(Permission(
            "message.write", ResourceType.MESSAGE, PermissionType.WRITE,
            "发送消息", is_system=True
        ))
        self.register_permission(Permission(
            "message.delete", ResourceType.MESSAGE, PermissionType.DELETE,
            "删除消息", is_system=True
        ))
        
        # 知识库相关权限
        self.register_permission(Permission(
            "knowledge.read", ResourceType.KNOWLEDGE_BASE, PermissionType.READ,
            "查看知识库", is_system=True
        ))
        self.register_permission(Permission(
            "knowledge.write", ResourceType.KNOWLEDGE_BASE, PermissionType.WRITE,
            "修改知识库", is_system=True
        ))
        self.register_permission(Permission(
            "knowledge.delete", ResourceType.KNOWLEDGE_BASE, PermissionType.DELETE,
            "删除知识库", is_system=True
        ))
        
        # 插件相关权限
        self.register_permission(Permission(
            "plugin.read", ResourceType.PLUGIN, PermissionType.READ,
            "查看插件", is_system=True
        ))
        self.register_permission(Permission(
            "plugin.write", ResourceType.PLUGIN, PermissionType.WRITE,
            "修改插件", is_system=True
        ))
        self.register_permission(Permission(
            "plugin.delete", ResourceType.PLUGIN, PermissionType.DELETE,
            "删除插件", is_system=True
        ))
        self.register_permission(Permission(
            "plugin.execute", ResourceType.PLUGIN, PermissionType.EXECUTE,
            "执行插件", is_system=True
        ))
        
        # 系统相关权限
        self.register_permission(Permission(
            "system.read", ResourceType.SYSTEM, PermissionType.READ,
            "查看系统信息", is_system=True
        ))
        self.register_permission(Permission(
            "system.admin", ResourceType.SYSTEM, PermissionType.ADMIN,
            "系统管理", is_system=True
        ))
        
        # API相关权限
        self.register_permission(Permission(
            "api.read", ResourceType.API, PermissionType.READ,
            "调用只读API", is_system=True
        ))
        self.register_permission(Permission(
            "api.write", ResourceType.API, PermissionType.WRITE,
            "调用写入API", is_system=True
        ))
        self.register_permission(Permission(
            "api.admin", ResourceType.API, PermissionType.ADMIN,
            "调用管理API", is_system=True
        ))
    
    def _initialize_system_roles(self):
        """初始化系统角色"""
        # 超级管理员角色
        admin_role = Role(
            name="admin",
            description="系统管理员，拥有所有权限",
            is_system=True
        )
        # 添加所有权限
        for permission in self.permissions.values():
            admin_role.add_permission(permission)
        self.register_role(admin_role)
        
        # 用户角色
        user_role = Role(
            name="user",
            description="普通用户",
            is_system=True
        )
        user_permissions = [
            "user.read", "message.read", "message.write",
            "conversation.read", "conversation.write",
            "bot.read", "bot.execute", "api.read"
        ]
        for perm_name in user_permissions:
            if perm_name in self.permissions:
                user_role.add_permission(self.permissions[perm_name])
        self.register_role(user_role)
        
        # 机器人管理员角色
        bot_admin_role = Role(
            name="bot_admin",
            description="机器人管理员",
            is_system=True
        )
        bot_admin_permissions = [
            "bot.read", "bot.write", "bot.delete", "bot.execute",
            "conversation.read", "conversation.write", "conversation.delete",
            "message.read", "message.write", "message.delete",
            "plugin.read", "plugin.write", "plugin.execute",
            "api.read", "api.write"
        ]
        for perm_name in bot_admin_permissions:
            if perm_name in self.permissions:
                bot_admin_role.add_permission(self.permissions[perm_name])
        self.register_role(bot_admin_role)
        
        # 知识库管理员角色
        kb_admin_role = Role(
            name="knowledge_admin",
            description="知识库管理员",
            is_system=True
        )
        kb_admin_permissions = [
            "knowledge.read", "knowledge.write", "knowledge.delete",
            "api.read", "api.write"
        ]
        for perm_name in kb_admin_permissions:
            if perm_name in self.permissions:
                kb_admin_role.add_permission(self.permissions[perm_name])
        self.register_role(kb_admin_role)
        
        # 只读用户角色
        readonly_role = Role(
            name="readonly",
            description="只读用户",
            is_system=True
        )
        readonly_permissions = [
            "user.read", "bot.read", "conversation.read",
            "message.read", "knowledge.read", "api.read"
        ]
        for perm_name in readonly_permissions:
            if perm_name in self.permissions:
                readonly_role.add_permission(self.permissions[perm_name])
        self.register_role(readonly_role)
    
    def register_permission(self, permission: Permission):
        """注册权限"""
        self.permissions[permission.name] = permission
        self.logger.info(f"Registered permission: {permission.name}")
    
    def register_role(self, role: Role):
        """注册角色"""
        self.roles[role.name] = role
        self.logger.info(f"Registered role: {role.name}")
    
    def get_permission(self, name: str) -> Optional[Permission]:
        """获取权限"""
        return self.permissions.get(name)
    
    def get_role(self, name: str) -> Optional[Role]:
        """获取角色"""
        return self.roles.get(name)
    
    def assign_role_to_user(self, user_id: str, role_name: str) -> bool:
        """为用户分配角色"""
        try:
            role = self.roles.get(role_name)
            if not role:
                self.logger.error(f"Role not found: {role_name}")
                return False
            
            if user_id not in self.user_permissions:
                self.user_permissions[user_id] = UserPermission(user_id=user_id)
            
            self.user_permissions[user_id].roles.add(role)
            self.logger.info(f"Assigned role {role_name} to user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error assigning role: {e}")
            return False
    
    def remove_role_from_user(self, user_id: str, role_name: str) -> bool:
        """从用户移除角色"""
        try:
            role = self.roles.get(role_name)
            if not role:
                self.logger.error(f"Role not found: {role_name}")
                return False
            
            if user_id in self.user_permissions:
                self.user_permissions[user_id].roles.discard(role)
                self.logger.info(f"Removed role {role_name} from user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error removing role: {e}")
            return False
    
    def grant_permission_to_user(self, user_id: str, permission_name: str) -> bool:
        """为用户直接授予权限"""
        try:
            permission = self.permissions.get(permission_name)
            if not permission:
                self.logger.error(f"Permission not found: {permission_name}")
                return False
            
            if user_id not in self.user_permissions:
                self.user_permissions[user_id] = UserPermission(user_id=user_id)
            
            self.user_permissions[user_id].direct_permissions.add(permission)
            self.logger.info(f"Granted permission {permission_name} to user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error granting permission: {e}")
            return False
    
    def deny_permission_to_user(self, user_id: str, permission_name: str) -> bool:
        """拒绝用户权限"""
        try:
            permission = self.permissions.get(permission_name)
            if not permission:
                self.logger.error(f"Permission not found: {permission_name}")
                return False
            
            if user_id not in self.user_permissions:
                self.user_permissions[user_id] = UserPermission(user_id=user_id)
            
            self.user_permissions[user_id].denied_permissions.add(permission)
            self.logger.info(f"Denied permission {permission_name} to user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error denying permission: {e}")
            return False
    
    def check_user_permission(self, user_id: str, permission_name: str) -> bool:
        """检查用户权限"""
        try:
            if user_id not in self.user_permissions:
                # 用户不存在，默认分配user角色
                self.assign_role_to_user(user_id, "user")
            
            user_perm = self.user_permissions[user_id]
            return user_perm.has_permission_by_name(permission_name)
            
        except Exception as e:
            self.logger.error(f"Error checking permission: {e}")
            return False
    
    def get_user_permissions(self, user_id: str) -> Set[str]:
        """获取用户所有权限"""
        if user_id not in self.user_permissions:
            self.assign_role_to_user(user_id, "user")
        
        user_perm = self.user_permissions[user_id]
        effective_perms = user_perm.get_effective_permissions()
        return {perm.name for perm in effective_perms}
    
    def get_user_roles(self, user_id: str) -> Set[str]:
        """获取用户角色"""
        if user_id not in self.user_permissions:
            return set()
        
        user_perm = self.user_permissions[user_id]
        return {role.name for role in user_perm.roles}
    
    def list_permissions(self) -> List[Dict[str, Any]]:
        """列出所有权限"""
        return [
            {
                "name": perm.name,
                "resource_type": perm.resource_type.value,
                "permission_type": perm.permission_type.value,
                "description": perm.description,
                "is_system": perm.is_system
            }
            for perm in self.permissions.values()
        ]
    
    def list_roles(self) -> List[Dict[str, Any]]:
        """列出所有角色"""
        return [
            {
                "name": role.name,
                "description": role.description,
                "permissions": list(role.get_permission_names()),
                "is_system": role.is_system
            }
            for role in self.roles.values()
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取权限统计信息"""
        return {
            "total_permissions": len(self.permissions),
            "total_roles": len(self.roles),
            "total_users": len(self.user_permissions),
            "system_permissions": sum(1 for p in self.permissions.values() if p.is_system),
            "system_roles": sum(1 for r in self.roles.values() if r.is_system)
        }


# 全局权限管理器实例
permission_manager = PermissionManager()


def get_permission_manager() -> PermissionManager:
    """获取权限管理器实例"""
    return permission_manager


# 权限检查装饰器
def require_permission(permission_name: str):
    """权限检查装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里需要从请求上下文获取用户ID
            # 暂时使用简单实现
            user_id = kwargs.get('user_id') or getattr(args[0], 'user_id', None)
            
            if not user_id:
                raise Exception("User ID not found")
            
            if not permission_manager.check_user_permission(user_id, permission_name):
                raise Exception(f"Permission denied: {permission_name}")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator