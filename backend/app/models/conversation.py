"""
对话数据模型
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, Enum, Index, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Conversation(BaseModel):
    """对话模型"""
    
    __tablename__ = "conversations"
    
    # 机器人 ID
    bot_id = Column(String(36), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False)
    
    # 用户 ID
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # 聊天类型
    chat_type = Column(
        Enum('private', 'group', 'channel', name='chat_type'),
        default='private',
        nullable=False
    )
    
    # 平台聊天 ID（群组 ID、频道 ID 等）
    platform_chat_id = Column(String(255), nullable=True)
    
    # 上下文数据（JSON 格式存储对话上下文）
    context_data = Column(JSON, nullable=True)
    
    # 开始时间
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 最后消息时间
    last_message_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 关系
    bot = relationship("Bot", back_populates="conversations")
    user = relationship("User", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation")
    chat_records = relationship("ChatRecord", back_populates="conversation")
    
    # 索引
    __table_args__ = (
        Index('idx_bot_user', 'bot_id', 'user_id'),
        Index('idx_last_message', 'last_message_at'),
    )
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, bot_id={self.bot_id}, user_id={self.user_id}, type={self.chat_type})>"