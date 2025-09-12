"""
Pinecone向量数据库适配器
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
import pinecone
from pinecone import Pinecone, ServerlessSpec

from .base import BaseVectorStore, VectorDocument, SearchResult


class PineconeVectorStore(BaseVectorStore):
    """Pinecone向量数据库实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Pinecone配置
        self.api_key = config.get('api_key')
        self.environment = config.get('environment', 'us-west1-gcp')
        self.index_name = config.get('index_name', self.collection_name)
        self.metric = config.get('metric', 'cosine')
        self.cloud = config.get('cloud', 'gcp')
        self.region = config.get('region', 'us-west1')
        
        # 客户端和索引
        self.pc = None
        self.index = None
        
    async def initialize(self) -> bool:
        """初始化Pinecone客户端"""
        try:
            if not self.api_key:
                self.logger.error("Pinecone API key is required")
                return False
            
            # 初始化Pinecone客户端
            self.pc = Pinecone(api_key=self.api_key)
            
            # 获取或创建索引
            await self._get_or_create_index()
            
            self.logger.info("Pinecone vector store initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Pinecone: {str(e)}")
            return False
            
    async def _get_or_create_index(self):
        """获取或创建索引"""
        try:
            # 检查索引是否存在
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                # 创建索引
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric,
                    spec=ServerlessSpec(
                        cloud=self.cloud,
                        region=self.region
                    )
                )
                
                # 等待索引就绪
                while not self.pc.describe_index(self.index_name).status['ready']:
                    await asyncio.sleep(1)
                    
                self.logger.info(f"Created Pinecone index: {self.index_name}")
            
            # 连接到索引
            self.index = self.pc.Index(self.index_name)
            
        except Exception as e:
            self.logger.error(f"Failed to get or create index: {str(e)}")
            raise
            
    async def create_collection(self, collection_name: str, dimension: int) -> bool:
        """创建向量集合（Pinecone中对应索引）"""
        try:
            self.pc.create_index(
                name=collection_name,
                dimension=dimension,
                metric=self.metric,
                spec=ServerlessSpec(
                    cloud=self.cloud,
                    region=self.region
                )
            )
            
            # 等待索引就绪
            while not self.pc.describe_index(collection_name).status['ready']:
                await asyncio.sleep(1)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create index {collection_name}: {str(e)}")
            return False
            
    async def delete_collection(self, collection_name: str) -> bool:
        """删除向量集合（删除索引）"""
        try:
            self.pc.delete_index(collection_name)
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete index {collection_name}: {str(e)}")
            return False
            
    async def list_collections(self) -> List[str]:
        """列出所有向量集合（索引）"""
        try:
            indexes = self.pc.list_indexes()
            return [idx.name for idx in indexes]
        except Exception as e:
            self.logger.error(f"Failed to list indexes: {str(e)}")
            return []
            
    async def add_documents(self, documents: List[VectorDocument]) -> bool:
        """添加文档到向量数据库"""
        try:
            if not self.index:
                self.logger.error("Index not initialized")
                return False
            
            # 准备向量数据
            vectors = []
            for doc in documents:
                if not self._validate_embedding_dimension(doc.embedding):
                    self.logger.error(f"Invalid embedding dimension: {len(doc.embedding)}")
                    return False
                
                # 准备元数据（包含内容）
                metadata = {
                    'content': doc.content,
                    **doc.metadata
                }
                
                vectors.append({
                    'id': doc.id,
                    'values': doc.embedding,
                    'metadata': metadata
                })
            
            # 批量上传（Pinecone建议批次大小为100）
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
                
            self.logger.info(f"Added {len(documents)} documents to Pinecone")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add documents: {str(e)}")
            return False
            
    async def update_document(self, document: VectorDocument) -> bool:
        """更新文档"""
        try:
            if not self.index:
                self.logger.error("Index not initialized")
                return False
                
            if not self._validate_embedding_dimension(document.embedding):
                self.logger.error(f"Invalid embedding dimension: {len(document.embedding)}")
                return False
            
            metadata = {
                'content': document.content,
                **document.metadata
            }
            
            self.index.upsert(vectors=[{
                'id': document.id,
                'values': document.embedding,
                'metadata': metadata
            }])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update document {document.id}: {str(e)}")
            return False
            
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        try:
            if not self.index:
                self.logger.error("Index not initialized")
                return False
                
            self.index.delete(ids=[document_id])
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete document {document_id}: {str(e)}")
            return False
            
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """批量删除文档"""
        try:
            if not self.index:
                self.logger.error("Index not initialized")
                return False
            
            # Pinecone批量删除限制为1000个ID
            batch_size = 1000
            for i in range(0, len(document_ids), batch_size):
                batch = document_ids[i:i + batch_size]
                self.index.delete(ids=batch)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete documents: {str(e)}")
            return False
            
    async def search_similar(
        self, 
        query_embedding: List[float], 
        top_k: int = 10,
        score_threshold: float = 0.0,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """相似性搜索"""
        try:
            if not self.index:
                self.logger.error("Index not initialized")
                return []
                
            if not self._validate_embedding_dimension(query_embedding):
                self.logger.error(f"Invalid query embedding dimension: {len(query_embedding)}")
                return []
            
            # 执行搜索
            search_results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                filter=filter_dict,
                include_metadata=True,
                include_values=True
            )
            
            # 处理结果
            results = []
            for match in search_results.matches:
                if match.score >= score_threshold:
                    metadata = match.metadata or {}
                    content = metadata.pop('content', '')
                    
                    doc = VectorDocument(
                        id=match.id,
                        content=content,
                        embedding=match.values or [],
                        metadata=metadata
                    )
                    
                    results.append(SearchResult(
                        document=doc,
                        score=match.score
                    ))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search similar documents: {str(e)}")
            return []
            
    async def search_by_ids(self, document_ids: List[str]) -> List[VectorDocument]:
        """根据ID搜索文档"""
        try:
            if not self.index:
                self.logger.error("Index not initialized")
                return []
            
            # Pinecone使用fetch来获取特定ID的向量
            results = self.index.fetch(ids=document_ids)
            
            documents = []
            for doc_id, vector_data in results.vectors.items():
                metadata = vector_data.metadata or {}
                content = metadata.pop('content', '')
                
                doc = VectorDocument(
                    id=doc_id,
                    content=content,
                    embedding=vector_data.values or [],
                    metadata=metadata
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Failed to search documents by IDs: {str(e)}")
            return []
            
    async def get_document_count(self) -> int:
        """获取文档总数"""
        try:
            if not self.index:
                return 0
                
            stats = self.index.describe_index_stats()
            return stats.total_vector_count or 0
            
        except Exception as e:
            self.logger.error(f"Failed to get document count: {str(e)}")
            return 0
            
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.index:
                return False
                
            # 尝试获取索引统计信息
            self.index.describe_index_stats()
            return True
            
        except Exception as e:
            self.logger.error(f"Pinecone health check failed: {str(e)}")
            return False
            
    async def close(self):
        """关闭连接"""
        try:
            # Pinecone客户端通常不需要显式关闭连接
            self.index = None
            self.pc = None
            self.logger.info("Pinecone connection closed")
        except Exception as e:
            self.logger.error(f"Error closing Pinecone connection: {str(e)}")