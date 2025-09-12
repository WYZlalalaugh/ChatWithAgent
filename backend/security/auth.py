"""
身份认证和授权服务
"""

import asyncio
import hashlib
import secrets
import jwt
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from app.config import settings


class TokenType(str, Enum):
    """令牌类型"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


@dataclass
class AuthToken:
    """认证令牌"""
    token: str
    token_type: TokenType
    user_id: str
    expires_at: datetime
    permissions: Set[str]
    metadata: Dict[str, Any]


@dataclass
class AuthUser:
    """认证用户"""
    user_id: str
    username: str
    email: Optional[str]
    roles: Set[str]
    permissions: Set[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]


class AuthenticationService:
    """身份认证服务"""
    
    def __init__(self):
        self.logger = logging.getLogger("security.auth")
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(hours=1)
        self.refresh_token_expire = timedelta(days=30)
        
        # 令牌黑名单（实际应使用Redis）
        self.token_blacklist: Set[str] = set()
        
        # 用户会话管理
        self.active_sessions: Dict[str, Set[str]] = {}  # user_id -> set of token_ids
        
    async def authenticate_user(
        self,
        username: str,
        password: str
    ) -> Optional[AuthUser]:
        """用户身份认证"""
        try:
            # 从数据库获取用户信息（这里需要实际的数据库查询）
            user_data = await self._get_user_by_username(username)
            
            if not user_data:
                self.logger.warning(f"User not found: {username}")
                return None
            
            # 验证密码
            if not self._verify_password(password, user_data["password_hash"]):
                self.logger.warning(f"Invalid password for user: {username}")
                return None
            
            # 检查用户状态
            if not user_data.get("is_active", False):
                self.logger.warning(f"Inactive user attempted login: {username}")
                return None
            
            # 创建认证用户对象
            auth_user = AuthUser(
                user_id=user_data["id"],
                username=user_data["username"],
                email=user_data.get("email"),
                roles=set(user_data.get("roles", [])),
                permissions=set(user_data.get("permissions", [])),
                is_active=user_data["is_active"],
                created_at=user_data["created_at"],
                last_login=user_data.get("last_login")
            )
            
            # 更新最后登录时间
            await self._update_last_login(user_data["id"])
            
            self.logger.info(f"User authenticated successfully: {username}")
            return auth_user
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return None
    
    async def create_access_token(
        self,
        user: AuthUser,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> AuthToken:
        """创建访问令牌"""
        try:
            token_id = secrets.token_urlsafe(32)
            issued_at = datetime.utcnow()
            expires_at = issued_at + self.access_token_expire
            
            # 构建JWT载荷
            payload = {
                "sub": user.user_id,
                "username": user.username,
                "token_type": TokenType.ACCESS.value,
                "token_id": token_id,
                "iat": issued_at,
                "exp": expires_at,
                "roles": list(user.roles),
                "permissions": list(user.permissions)
            }
            
            # 添加额外声明
            if additional_claims:
                payload.update(additional_claims)
            
            # 生成JWT令牌
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # 记录活跃会话
            if user.user_id not in self.active_sessions:
                self.active_sessions[user.user_id] = set()
            self.active_sessions[user.user_id].add(token_id)
            
            return AuthToken(
                token=token,
                token_type=TokenType.ACCESS,
                user_id=user.user_id,
                expires_at=expires_at,
                permissions=user.permissions,
                metadata={"token_id": token_id}
            )
            
        except Exception as e:
            self.logger.error(f"Token creation error: {e}")
            raise
    
    async def create_refresh_token(self, user: AuthUser) -> AuthToken:
        """创建刷新令牌"""
        try:
            token_id = secrets.token_urlsafe(32)
            issued_at = datetime.utcnow()
            expires_at = issued_at + self.refresh_token_expire
            
            payload = {
                "sub": user.user_id,
                "token_type": TokenType.REFRESH.value,
                "token_id": token_id,
                "iat": issued_at,
                "exp": expires_at
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            return AuthToken(
                token=token,
                token_type=TokenType.REFRESH,
                user_id=user.user_id,
                expires_at=expires_at,
                permissions=set(),
                metadata={"token_id": token_id}
            )
            
        except Exception as e:
            self.logger.error(f"Refresh token creation error: {e}")
            raise
    
    async def verify_token(self, token: str) -> Optional[AuthToken]:
        """验证令牌"""
        try:
            # 检查令牌黑名单
            if token in self.token_blacklist:
                self.logger.warning("Token is blacklisted")
                return None
            
            # 解码JWT令牌
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            
            # 验证令牌格式
            required_fields = ["sub", "token_type", "token_id", "exp"]
            if not all(field in payload for field in required_fields):
                self.logger.warning("Invalid token format")
                return None
            
            # 检查令牌是否过期
            exp_timestamp = payload["exp"]
            if datetime.utcnow().timestamp() > exp_timestamp:
                self.logger.warning("Token has expired")
                return None
            
            # 检查用户会话
            user_id = payload["sub"]
            token_id = payload["token_id"]
            
            if (user_id not in self.active_sessions or 
                token_id not in self.active_sessions[user_id]):
                self.logger.warning("Token session not found")
                return None
            
            # 构建认证令牌对象
            auth_token = AuthToken(
                token=token,
                token_type=TokenType(payload["token_type"]),
                user_id=user_id,
                expires_at=datetime.fromtimestamp(exp_timestamp),
                permissions=set(payload.get("permissions", [])),
                metadata={"token_id": token_id}
            )
            
            return auth_token
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Token verification error: {e}")
            return None
    
    async def revoke_token(self, token: str) -> bool:
        """撤销令牌"""
        try:
            # 解码令牌获取信息
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}  # 允许过期令牌
            )
            
            user_id = payload.get("sub")
            token_id = payload.get("token_id")
            
            # 添加到黑名单
            self.token_blacklist.add(token)
            
            # 从活跃会话中移除
            if user_id in self.active_sessions:
                self.active_sessions[user_id].discard(token_id)
                if not self.active_sessions[user_id]:
                    del self.active_sessions[user_id]
            
            self.logger.info(f"Token revoked for user: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Token revocation error: {e}")
            return False
    
    async def revoke_all_user_tokens(self, user_id: str) -> bool:
        """撤销用户的所有令牌"""
        try:
            if user_id in self.active_sessions:
                # 清除用户的所有会话
                del self.active_sessions[user_id]
                
            self.logger.info(f"All tokens revoked for user: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Bulk token revocation error: {e}")
            return False
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return f"{salt}:{password_hash.hex()}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            salt, stored_hash = password_hash.split(':')
            password_hash_check = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return stored_hash == password_hash_check.hex()
        except:
            return False
    
    async def _get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """从数据库获取用户信息"""
        # 这里应该实现实际的数据库查询
        # 暂时返回模拟数据
        if username == "admin":
            return {
                "id": "admin_user_id",
                "username": "admin",
                "email": "admin@example.com",
                "password_hash": self._hash_password("admin123"),
                "roles": ["admin"],
                "permissions": ["*"],
                "is_active": True,
                "created_at": datetime.utcnow(),
                "last_login": None
            }
        return None
    
    async def _update_last_login(self, user_id: str):
        """更新最后登录时间"""
        # 这里应该实现实际的数据库更新
        pass


class AuthorizationService:
    """授权服务"""
    
    def __init__(self):
        self.logger = logging.getLogger("security.authz")
        
        # 权限层次结构
        self.permission_hierarchy = {
            "*": set(),  # 超级权限
            "admin.*": {"user.*", "bot.*", "system.*"},
            "user.*": {"user.read", "user.write"},
            "bot.*": {"bot.read", "bot.write", "bot.execute"},
            "system.*": {"system.read", "system.config"}
        }
    
    async def check_permission(
        self,
        user_permissions: Set[str],
        required_permission: str
    ) -> bool:
        """检查权限"""
        try:
            # 检查超级权限
            if "*" in user_permissions:
                return True
            
            # 直接权限匹配
            if required_permission in user_permissions:
                return True
            
            # 层次权限匹配
            for user_perm in user_permissions:
                if self._is_permission_granted(user_perm, required_permission):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Permission check error: {e}")
            return False
    
    def _is_permission_granted(self, user_permission: str, required_permission: str) -> bool:
        """检查用户权限是否包含所需权限"""
        # 通配符权限
        if user_permission.endswith("*"):
            prefix = user_permission[:-1]
            if required_permission.startswith(prefix):
                return True
        
        # 层次权限
        if user_permission in self.permission_hierarchy:
            granted_permissions = self.permission_hierarchy[user_permission]
            if required_permission in granted_permissions:
                return True
            
            # 递归检查子权限
            for granted_perm in granted_permissions:
                if self._is_permission_granted(granted_perm, required_permission):
                    return True
        
        return False
    
    async def get_user_effective_permissions(
        self,
        user_permissions: Set[str]
    ) -> Set[str]:
        """获取用户的有效权限"""
        effective_permissions = set(user_permissions)
        
        for permission in user_permissions:
            if permission in self.permission_hierarchy:
                effective_permissions.update(self.permission_hierarchy[permission])
        
        return effective_permissions


# 全局服务实例
authentication_service = AuthenticationService()
authorization_service = AuthorizationService()


def get_auth_service() -> AuthenticationService:
    """获取认证服务实例"""
    return authentication_service


def get_authz_service() -> AuthorizationService:
    """获取授权服务实例"""
    return authorization_service