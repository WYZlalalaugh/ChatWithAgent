"""
用户数据模型
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, JSON, Index
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class User(BaseModel):
    """用户模型"""
    
    __tablename__ = "users"
    
    # 平台用户 ID（各平台的用户标识）
    platform_user_id = Column(String(255), nullable=False)
    
    # 平台类型（qq, wechat, feishu, dingtalk 等）
    platform_type = Column(String(50), nullable=False)
    
    # 用户名
    username = Column(String(255), nullable=True)
    
    # 头像 URL
    avatar_url = Column(Text, nullable=True)
    
    # 用户档案数据（JSON 格式存储平台特定信息）
    profile_data = Column(JSON, nullable=True)
    
    # 最后活跃时间
    last_active = Column(DateTime, nullable=True)
    
    # 关系
    conversations = relationship("Conversation", back_populates="user")
    messages = relationship("ChatMessage", back_populates="user")
    permissions = relationship("UserPermission", back_populates="user")
    
    # 索引
    __table_args__ = (
        Index('idx_platform_user', 'platform_type', 'platform_user_id', unique=True),
        Index('idx_platform_type', 'platform_type'),
        Index('idx_last_active', 'last_active'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, platform={self.platform_type})>"


class UserPermission(BaseModel):
    """用户权限模型"""
    
    __tablename__ = "user_permissions"
    
    # 用户 ID
    user_id = Column(String(36), nullable=False, index=True)
    
    # 资源类型（bot, knowledge_base, plugin 等）
    resource_type = Column(String(100), nullable=False)
    
    # 资源 ID（具体资源的 ID）
    resource_id = Column(String(36), nullable=True)
    
    # 权限级别（read, write, admin）
    permission_level = Column(String(20), nullable=False, default="read")
    
    # 授权时间
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 授权人
    granted_by = Column(String(36), nullable=True)
    
    # 关系
    user = relationship("User", back_populates="permissions")
    
    # 索引
    __table_args__ = (
        Index('idx_user_resource', 'user_id', 'resource_type'),
    )
    
    def __repr__(self):
        return f"<UserPermission(user_id={self.user_id}, resource={self.resource_type}, level={self.permission_level})>"