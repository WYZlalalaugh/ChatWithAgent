"""
插件和模型数据模型
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, Enum, Boolean, Integer, Numeric, Index, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Plugin(BaseModel):
    """插件模型"""
    
    __tablename__ = "plugins"
    
    # 插件名称（唯一）
    name = Column(String(255), nullable=False, unique=True)
    
    # 插件版本
    version = Column(String(50), nullable=False)
    
    # 插件描述
    description = Column(Text, nullable=True)
    
    # 插件作者
    author = Column(String(255), nullable=True)
    
    # 插件清单（JSON 格式，包含入口点、权限等信息）
    manifest = Column(JSON, nullable=True)
    
    # 插件状态
    status = Column(
        Enum('active', 'inactive', 'error', name='plugin_status'),
        default='inactive',
        nullable=False
    )
    
    # 关系
    bot_plugins = relationship("BotPlugin", back_populates="plugin")
    
    # 索引
    __table_args__ = (
        Index('idx_name', 'name'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Plugin(id={self.id}, name={self.name}, version={self.version}, status={self.status})>"


class Model(BaseModel):
    """AI 模型配置模型"""
    
    __tablename__ = "models"
    
    # 模型名称
    name = Column(String(255), nullable=False)
    
    # 提供商（openai, anthropic, azure, 等）
    provider = Column(String(100), nullable=False)
    
    # 模型类型
    model_type = Column(
        Enum('chat', 'embedding', 'image', 'audio', name='model_type'),
        default='chat',
        nullable=False
    )
    
    # API 配置
    api_config = Column(JSON, nullable=True)
    
    # 模型参数
    parameters = Column(JSON, nullable=True)
    
    # 是否激活
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 关系
    usage_logs = relationship("ModelUsageLog", back_populates="model")
    
    # 索引
    __table_args__ = (
        Index('idx_provider', 'provider'),
        Index('idx_model_type', 'model_type'),
        Index('idx_is_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Model(id={self.id}, name={self.name}, provider={self.provider}, type={self.model_type})>"


class ModelUsageLog(BaseModel):
    """模型使用日志模型"""
    
    __tablename__ = "model_usage_logs"
    
    # 模型 ID
    model_id = Column(String(36), ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    
    # 机器人 ID
    bot_id = Column(String(36), ForeignKey("bots.id", ondelete="SET NULL"), nullable=True)
    
    # 对话 ID
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    
    # 请求 Token 数
    request_tokens = Column(Integer, default=0, nullable=False)
    
    # 响应 Token 数
    response_tokens = Column(Integer, default=0, nullable=False)
    
    # 总 Token 数
    total_tokens = Column(Integer, default=0, nullable=False)
    
    # 成本
    cost = Column(Numeric(10, 6), default=0, nullable=False)
    
    # 响应时间（毫秒）
    response_time = Column(Integer, nullable=True)
    
    # 状态
    status = Column(
        Enum('success', 'error', 'timeout', name='usage_status'),
        default='success',
        nullable=False
    )
    
    # 错误信息
    error_message = Column(Text, nullable=True)
    
    # 关系
    model = relationship("Model", back_populates="usage_logs")
    bot = relationship("Bot", back_populates="usage_logs")
    
    # 索引
    __table_args__ = (
        Index('idx_model', 'model_id'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ModelUsageLog(id={self.id}, model_id={self.model_id}, tokens={self.total_tokens}, status={self.status})>"