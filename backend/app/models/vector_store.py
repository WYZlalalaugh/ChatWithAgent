"""
向量数据库配置数据模型
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Index
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class VectorStoreConfig(BaseModel):
    """向量数据库配置模型"""
    
    __tablename__ = "vector_store_configs"
    
    # 配置名称
    name = Column(String(255), nullable=False, unique=True)
    
    # 向量数据库类型（chroma, faiss, qdrant, pinecone）
    store_type = Column(String(50), nullable=False)
    
    # 描述
    description = Column(Text, nullable=True)
    
    # 配置参数（JSON格式存储）
    config = Column(JSON, nullable=False)
    
    # 是否为默认配置
    is_default = Column(Boolean, default=False, nullable=False)
    
    # 是否启用
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    # 索引
    __table_args__ = (
        Index('idx_store_type', 'store_type'),
        Index('idx_is_default', 'is_default'),
        Index('idx_is_enabled', 'is_enabled'),
    )
    
    def __repr__(self):
        return f"<VectorStoreConfig(id={self.id}, name={self.name}, type={self.store_type}, default={self.is_default})>"


class KnowledgeBaseVectorStore(BaseModel):
    """知识库向量数据库关联模型"""
    
    __tablename__ = "knowledge_base_vector_stores"
    
    # 知识库ID
    knowledge_base_id = Column(String(36), nullable=False)
    
    # 向量数据库配置ID
    vector_store_config_id = Column(String(36), nullable=False)
    
    # 向量数据库中的集合名称
    collection_name = Column(String(255), nullable=False)
    
    # 向量维度
    dimension = Column(String(10), default='1536', nullable=False)
    
    # 文档数量
    document_count = Column(String(10), default='0', nullable=False)
    
    # 最后同步时间
    last_sync_time = Column(String(50), nullable=True)
    
    # 是否启用
    is_enabled = Column(Boolean, default=True, nullable=False)
    
    # 额外配置
    extra_config = Column(JSON, nullable=True)
    
    # 索引
    __table_args__ = (
        Index('idx_kb_vector_store', 'knowledge_base_id', 'vector_store_config_id', unique=True),
        Index('idx_collection_name', 'collection_name'),
    )
    
    def __repr__(self):
        return f"<KnowledgeBaseVectorStore(kb_id={self.knowledge_base_id}, config_id={self.vector_store_config_id}, collection={self.collection_name})>"