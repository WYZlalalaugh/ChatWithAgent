"""
认证相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import jwt
import logging

from ...security.auth import AuthManager
from ...models.database import User
from ...config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
settings = get_settings()


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    token_type: str
    expires_in: int
    user_info: dict


class RegisterRequest(BaseModel):
    """注册请求模型"""
    username: str
    password: str
    email: str
    nickname: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """修改密码请求模型"""
    old_password: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录"""
    try:
        auth_manager = AuthManager()
        
        # 验证用户凭证
        user = await auth_manager.authenticate_user(request.username, request.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # 检查用户状态
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        # 生成访问令牌
        access_token = await auth_manager.create_access_token(user.id)
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.security.access_token_expire_minutes * 60,
            user_info={
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "email": user.email,
                "role": user.role,
                "avatar_url": user.avatar_url
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/register", response_model=dict)
async def register(request: RegisterRequest):
    """用户注册"""
    try:
        auth_manager = AuthManager()
        
        # 检查用户名是否已存在
        existing_user = await auth_manager.get_user_by_username(request.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # 检查邮箱是否已存在
        existing_email = await auth_manager.get_user_by_email(request.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        
        # 创建用户
        user = await auth_manager.create_user(
            username=request.username,
            password=request.password,
            email=request.email,
            nickname=request.nickname or request.username
        )
        
        return {
            "success": True,
            "message": "User registered successfully",
            "user_id": user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """用户登出"""
    try:
        auth_manager = AuthManager()
        token = credentials.credentials
        
        # 将令牌加入黑名单
        await auth_manager.revoke_token(token)
        
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(request: TokenRefreshRequest):
    """刷新访问令牌"""
    try:
        auth_manager = AuthManager()
        
        # 验证刷新令牌
        user_id = await auth_manager.verify_refresh_token(request.refresh_token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # 获取用户信息
        user = await auth_manager.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or disabled"
            )
        
        # 生成新的访问令牌
        access_token = await auth_manager.create_access_token(user.id)
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.security.access_token_expire_minutes * 60,
            user_info={
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "email": user.email,
                "role": user.role,
                "avatar_url": user.avatar_url
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户信息"""
    try:
        auth_manager = AuthManager()
        token = credentials.credentials
        
        # 验证令牌并获取用户
        user = await auth_manager.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "email": user.email,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """修改密码"""
    try:
        auth_manager = AuthManager()
        token = credentials.credentials
        
        # 获取当前用户
        user = await auth_manager.get_current_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # 验证旧密码
        if not await auth_manager.verify_password(request.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid old password"
            )
        
        # 更新密码
        await auth_manager.update_user_password(user.id, request.new_password)
        
        return {"success": True, "message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/verify-token")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证令牌有效性"""
    try:
        auth_manager = AuthManager()
        token = credentials.credentials
        
        # 验证令牌
        user = await auth_manager.get_current_user(token)
        if not user:
            return {"valid": False, "message": "Invalid token"}
        
        return {
            "valid": True,
            "user_id": user.id,
            "username": user.username,
            "expires_in": await auth_manager.get_token_remaining_time(token)
        }
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return {"valid": False, "message": "Token verification failed"}