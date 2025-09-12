"""
机器人数据模型
"""

from sqlalchemy import Column, String, Text, JSON, Enum, Index
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Bot(BaseModel):
    """机器人模型"""
    
    __tablename__ = "bots"
    
    # 机器人名称
    name = Column(String(255), nullable=False)
    
    # 机器人描述
    description = Column(Text, nullable=True)
    
    # 平台类型（qq, wechat, feishu, dingtalk 等）
    platform_type = Column(String(50), nullable=False)
    
    # 平台配置（JSON 格式，存储平台特定配置）
    platform_config = Column(JSON, nullable=True)
    
    # LLM 配置（大语言模型配置）
    llm_config = Column(JSON, nullable=True)
    
    # Agent 配置（智能体配置）
    agent_config = Column(JSON, nullable=True)
    
    # 关联的知识库 ID 列表
    knowledge_base_ids = Column(JSON, nullable=True)
    
    # 插件配置
    plugin_configs = Column(JSON, nullable=True)
    
    # 机器人状态
    status = Column(
        Enum('active', 'inactive', 'error', name='bot_status'),
        default='inactive',
        nullable=False
    )
    
    # 关系
    conversations = relationship("Conversation", back_populates="bot")
    plugins = relationship("BotPlugin", back_populates="bot")
    usage_logs = relationship("ModelUsageLog", back_populates="bot")
    
    # 索引
    __table_args__ = (
        Index('idx_platform_type', 'platform_type'),
        Index('idx_status', 'status'),
    )
    
    def __repr__(self):
        return f"<Bot(id={self.id}, name={self.name}, platform={self.platform_type}, status={self.status})>"


class BotPlugin(BaseModel):
    """机器人插件关联模型"""
    
    __tablename__ = "bot_plugins"
    
    # 机器人 ID
    bot_id = Column(String(36), nullable=False)
    
    # 插件 ID
    plugin_id = Column(String(36), nullable=False)
    
    # 插件配置
    config = Column(JSON, nullable=True)
    
    # 是否启用
    is_enabled = Column(String(10), default='true', nullable=False)
    
    # 关系
    bot = relationship("Bot", back_populates="plugins")
    plugin = relationship("Plugin", back_populates="bot_plugins")
    
    # 索引
    __table_args__ = (
        Index('idx_bot_plugin', 'bot_id', 'plugin_id', unique=True),
    )
    
    def __repr__(self):
        return f"<BotPlugin(bot_id={self.bot_id}, plugin_id={self.plugin_id}, enabled={self.is_enabled})>"