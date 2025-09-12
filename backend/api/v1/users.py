"""
用户管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
import logging

from ...security.auth import AuthManager
from ...security.permissions import require_permission
from ...models.database import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])
security = HTTPBearer()


class UserResponse(BaseModel):
    """用户响应模型"""
    id: str
    username: str
    nickname: str
    email: str
    role: str
    avatar_url: Optional[str]
    is_active: bool
    created_at: str
    last_login: Optional[str]


class UserUpdateRequest(BaseModel):
    """用户更新请求模型"""
    nickname: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCreateRequest(BaseModel):
    """创建用户请求模型"""
    username: str
    password: str
    email: str
    nickname: Optional[str] = None
    role: str = "user"


class UserListResponse(BaseModel):
    """用户列表响应模型"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """获取当前用户依赖"""
    auth_manager = AuthManager()
    token = credentials.credentials
    user = await auth_manager.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return user


@router.get("/", response_model=UserListResponse)
@require_permission("user:read")
async def list_users(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None)
):
    """获取用户列表"""
    try:
        auth_manager = AuthManager()
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 获取用户列表
        users, total = await auth_manager.get_users(
            offset=offset,
            limit=page_size,
            search=search
        )
        
        # 转换为响应模型
        user_responses = []
        for user in users:
            user_responses.append(UserResponse(
                id=user.id,
                username=user.username,
                nickname=user.nickname,
                email=user.email,
                role=user.role,
                avatar_url=user.avatar_url,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                last_login=user.last_login.isoformat() if user.last_login else None
            ))
        
        return UserListResponse(
            users=user_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{user_id}", response_model=UserResponse)
@require_permission("user:read")
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取用户详情"""
    try:
        auth_manager = AuthManager()
        
        # 检查权限（用户只能查看自己的信息，管理员可以查看所有）
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        user = await auth_manager.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            role=user.role,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/", response_model=UserResponse)
@require_permission("user:create")
async def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """创建用户"""
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
            nickname=request.nickname or request.username,
            role=request.role
        )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            role=user.role,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{user_id}", response_model=UserResponse)
@require_permission("user:update")
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """更新用户信息"""
    try:
        auth_manager = AuthManager()
        
        # 检查权限（用户只能更新自己的信息，管理员可以更新所有）
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        # 获取用户
        user = await auth_manager.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 准备更新数据
        update_data = {}
        if request.nickname is not None:
            update_data['nickname'] = request.nickname
        if request.email is not None:
            # 检查邮箱是否已被其他用户使用
            existing_email = await auth_manager.get_user_by_email(request.email)
            if existing_email and existing_email.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists"
                )
            update_data['email'] = request.email
        if request.avatar_url is not None:
            update_data['avatar_url'] = request.avatar_url
        
        # 更新用户
        updated_user = await auth_manager.update_user(user_id, update_data)
        
        return UserResponse(
            id=updated_user.id,
            username=updated_user.username,
            nickname=updated_user.nickname,
            email=updated_user.email,
            role=updated_user.role,
            avatar_url=updated_user.avatar_url,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at.isoformat(),
            last_login=updated_user.last_login.isoformat() if updated_user.last_login else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{user_id}")
@require_permission("user:delete")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除用户"""
    try:
        auth_manager = AuthManager()
        
        # 不能删除自己
        if current_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete yourself"
            )
        
        # 获取用户
        user = await auth_manager.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 删除用户
        await auth_manager.delete_user(user_id)
        
        return {"success": True, "message": "User deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{user_id}/activate")
@require_permission("user:update")
async def activate_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """激活用户"""
    try:
        auth_manager = AuthManager()
        
        user = await auth_manager.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        await auth_manager.update_user(user_id, {"is_active": True})
        
        return {"success": True, "message": "User activated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Activate user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{user_id}/deactivate")
@require_permission("user:update")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """停用用户"""
    try:
        auth_manager = AuthManager()
        
        # 不能停用自己
        if current_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate yourself"
            )
        
        user = await auth_manager.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        await auth_manager.update_user(user_id, {"is_active": False})
        
        return {"success": True, "message": "User deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deactivate user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )