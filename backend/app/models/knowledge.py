"""
知识库数据模型
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON, Enum, Integer, Index, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class KnowledgeBase(BaseModel):
    """知识库模型"""
    
    __tablename__ = "knowledge_bases"
    
    # 知识库名称
    name = Column(String(255), nullable=False)
    
    # 知识库描述
    description = Column(Text, nullable=True)
    
    # 嵌入模型
    embedding_model = Column(String(255), default='text-embedding-ada-002', nullable=False)
    
    # 向量存储类型
    vector_store_type = Column(String(50), default='chroma', nullable=False)
    
    # 向量存储配置
    vector_store_config = Column(JSON, nullable=True)
    
    # 其他配置
    config = Column(JSON, nullable=True)
    
    # 关系
    documents = relationship("Document", back_populates="knowledge_base")
    chat_records = relationship("ChatRecord", back_populates="knowledge_base")
    multimodal_contents = relationship("MultimodalContent", back_populates="knowledge_base")
    
    # 索引
    __table_args__ = (
        Index('idx_name', 'name'),
    )
    
    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, name={self.name}, type={self.vector_store_type})>"


class Document(BaseModel):
    """文档模型"""
    
    __tablename__ = "documents"
    
    # 知识库 ID
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    
    # 文档标题
    title = Column(String(500), nullable=False)
    
    # 文件路径
    file_path = Column(String(1000), nullable=True)
    
    # 内容类型
    content_type = Column(String(100), nullable=True)
    
    # 来源类型
    source_type = Column(
        Enum('upload', 'url', 'api', 'chat', name='source_type'),
        default='upload',
        nullable=False
    )
    
    # 文档内容
    content = Column(Text, nullable=True)
    
    # 元数据
    metadata = Column(JSON, nullable=True)
    
    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")
    
    # 索引
    __table_args__ = (
        Index('idx_knowledge_base', 'knowledge_base_id'),
        Index('idx_source_type', 'source_type'),
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title}, source={self.source_type})>"


class DocumentChunk(BaseModel):
    """文档分块模型"""
    
    __tablename__ = "document_chunks"
    
    # 文档 ID
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # 分块内容
    content = Column(Text, nullable=False)
    
    # 嵌入向量
    embedding = Column(JSON, nullable=True)
    
    # 元数据
    metadata = Column(JSON, nullable=True)
    
    # 分块索引
    chunk_index = Column(Integer, nullable=False)
    
    # 分块类型
    chunk_type = Column(String(50), default='text', nullable=False)
    
    # 关系
    document = relationship("Document", back_populates="chunks")
    
    # 索引
    __table_args__ = (
        Index('idx_document', 'document_id'),
        Index('idx_chunk_index', 'chunk_index'),
    )
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index})>"


class ChatRecord(BaseModel):
    """聊天记录模型（用于导入历史聊天记录到知识库）"""
    
    __tablename__ = "chat_records"
    
    # 对话 ID（可为空，用于关联现有对话）
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    
    # 知识库 ID
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    
    # 聊天内容
    chat_content = Column(Text, nullable=False)
    
    # 聊天元数据
    chat_metadata = Column(JSON, nullable=True)
    
    # 聊天时间
    chat_time = Column(DateTime, nullable=True)
    
    # 关系
    conversation = relationship("Conversation", back_populates="chat_records")
    knowledge_base = relationship("KnowledgeBase", back_populates="chat_records")
    
    # 索引
    __table_args__ = (
        Index('idx_knowledge_base', 'knowledge_base_id'),
        Index('idx_chat_time', 'chat_time'),
    )
    
    def __repr__(self):
        return f"<ChatRecord(id={self.id}, knowledge_base_id={self.knowledge_base_id})>"


class MultimodalContent(BaseModel):
    """多模态内容模型"""
    
    __tablename__ = "multimodal_contents"
    
    # 知识库 ID
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    
    # 内容类型
    content_type = Column(
        Enum('image', 'audio', 'video', name='content_type'),
        nullable=False
    )
    
    # 文件路径
    file_path = Column(String(1000), nullable=False)
    
    # 原始文件名
    original_filename = Column(String(500), nullable=True)
    
    # 提取的文本内容
    extracted_text = Column(Text, nullable=True)
    
    # 内容元数据
    content_metadata = Column(JSON, nullable=True)
    
    # 嵌入向量
    embedding = Column(JSON, nullable=True)
    
    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="multimodal_contents")
    
    # 索引
    __table_args__ = (
        Index('idx_knowledge_base', 'knowledge_base_id'),
        Index('idx_content_type', 'content_type'),
    )
    
    def __repr__(self):
        return f"<MultimodalContent(id={self.id}, type={self.content_type}, filename={self.original_filename})>"