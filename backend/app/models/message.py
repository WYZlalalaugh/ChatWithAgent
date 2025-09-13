"""
消息数据模型
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, Enum, Boolean, Index, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ChatMessage(BaseModel):
    """聊天消息模型"""
    
    __tablename__ = "chat_messages"
    
    # 对话 ID
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    
    # 用户 ID（发送者）
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # 消息类型
    message_type = Column(
        Enum('text', 'image', 'audio', 'video', 'file', 'system', name='message_type'),
        default='text',
        nullable=False
    )
    
    # 消息内容
    content = Column(Text, nullable=True)
    
    # 元数据（JSON 格式，存储文件路径、媒体信息等）
    message_metadata = Column(JSON, nullable=True)
    
    # 是否来自机器人
    is_from_bot = Column(Boolean, default=False, nullable=False)
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", back_populates="messages")
    
    # 索引
    __table_args__ = (
        Index('idx_conversation', 'conversation_id'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, conversation_id={self.conversation_id}, type={self.message_type}, from_bot={self.is_from_bot})>"