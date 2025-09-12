"""
Qdrant向量数据库适配器
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue
)

from .base import BaseVectorStore, VectorDocument, SearchResult


class QdrantVectorStore(BaseVectorStore):
    """Qdrant向量数据库实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Qdrant配置
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 6333)
        self.api_key = config.get('api_key')
        self.url = config.get('url')  # 云端服务URL
        self.timeout = config.get('timeout', 60)
        self.distance_metric = config.get('distance_metric', 'Cosine')
        
        # 客户端
        self.client = None
        
    async def initialize(self) -> bool:
        """初始化Qdrant客户端"""
        try:
            if self.url:
                # 云端服务
                self.client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=self.timeout
                )
            else:
                # 本地服务
                self.client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    timeout=self.timeout
                )
            
            # 测试连接
            info = self.client.get_collections()
            
            # 获取或创建集合
            await self._get_or_create_collection()
            
            self.logger.info("Qdrant vector store initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Qdrant: {str(e)}")
            return False
            
    async def _get_or_create_collection(self):
        """获取或创建集合"""
        try:
            # 检查集合是否存在
            collections = self.client.get_collections()
            existing_collections = [col.name for col in collections.collections]
            
            if self.collection_name not in existing_collections:
                # 创建集合
                distance_map = {
                    'Cosine': Distance.COSINE,
                    'Euclidean': Distance.EUCLID,
                    'Dot': Distance.DOT
                }
                
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=distance_map.get(self.distance_metric, Distance.COSINE)
                    )
                )
                self.logger.info(f"Created Qdrant collection: {self.collection_name}")
                
        except Exception as e:
            self.logger.error(f"Failed to get or create collection: {str(e)}")
            raise
            
    async def create_collection(self, collection_name: str, dimension: int) -> bool:
        """创建向量集合"""
        try:
            distance_map = {
                'Cosine': Distance.COSINE,
                'Euclidean': Distance.EUCLID,
                'Dot': Distance.DOT
            }
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=distance_map.get(self.distance_metric, Distance.COSINE)
                )
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create collection {collection_name}: {str(e)}")
            return False
            
    async def delete_collection(self, collection_name: str) -> bool:
        """删除向量集合"""
        try:
            self.client.delete_collection(collection_name=collection_name)
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete collection {collection_name}: {str(e)}")
            return False
            
    async def list_collections(self) -> List[str]:
        """列出所有向量集合"""
        try:
            collections = self.client.get_collections()
            return [col.name for col in collections.collections]
        except Exception as e:
            self.logger.error(f"Failed to list collections: {str(e)}")
            return []
            
    async def add_documents(self, documents: List[VectorDocument]) -> bool:
        """添加文档到向量数据库"""
        try:
            # 准备数据点
            points = []
            for doc in documents:
                if not self._validate_embedding_dimension(doc.embedding):
                    self.logger.error(f"Invalid embedding dimension: {len(doc.embedding)}")
                    return False
                
                # 准备payload（包含内容和元数据）
                payload = {
                    'content': doc.content,
                    **doc.metadata
                }
                
                point = PointStruct(
                    id=doc.id,
                    vector=doc.embedding,
                    payload=payload
                )
                points.append(point)
            
            # 批量添加
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            self.logger.info(f"Added {len(documents)} documents to Qdrant")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add documents: {str(e)}")
            return False
            
    async def update_document(self, document: VectorDocument) -> bool:
        """更新文档"""
        try:
            if not self._validate_embedding_dimension(document.embedding):
                self.logger.error(f"Invalid embedding dimension: {len(document.embedding)}")
                return False
            
            payload = {
                'content': document.content,
                **document.metadata
            }
            
            point = PointStruct(
                id=document.id,
                vector=document.embedding,
                payload=payload
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update document {document.id}: {str(e)}")
            return False
            
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[document_id]
                )
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete document {document_id}: {str(e)}")
            return False
            
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """批量删除文档"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=document_ids
                )
            )
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
            if not self._validate_embedding_dimension(query_embedding):
                self.logger.error(f"Invalid query embedding dimension: {len(query_embedding)}")
                return []
            
            # 构建过滤器
            query_filter = None
            if filter_dict:
                conditions = []
                for key, value in filter_dict.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                if conditions:
                    query_filter = Filter(must=conditions)
            
            # 执行搜索
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
                query_filter=query_filter,
                with_payload=True,
                with_vectors=True
            )
            
            # 处理结果
            results = []
            for result in search_results:
                payload = result.payload or {}
                content = payload.pop('content', '')
                
                doc = VectorDocument(
                    id=str(result.id),
                    content=content,
                    embedding=result.vector or [],
                    metadata=payload
                )
                
                results.append(SearchResult(
                    document=doc,
                    score=result.score
                ))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search similar documents: {str(e)}")
            return []
            
    async def search_by_ids(self, document_ids: List[str]) -> List[VectorDocument]:
        """根据ID搜索文档"""
        try:
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=document_ids,
                with_payload=True,
                with_vectors=True
            )
            
            documents = []
            for result in results:
                payload = result.payload or {}
                content = payload.pop('content', '')
                
                doc = VectorDocument(
                    id=str(result.id),
                    content=content,
                    embedding=result.vector or [],
                    metadata=payload
                )
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Failed to search documents by IDs: {str(e)}")
            return []
            
    async def get_document_count(self) -> int:
        """获取文档总数"""
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return info.points_count or 0
        except Exception as e:
            self.logger.error(f"Failed to get document count: {str(e)}")
            return 0
            
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if self.client is None:
                return False
            # 尝试获取集合信息
            self.client.get_collection(collection_name=self.collection_name)
            return True
        except Exception as e:
            self.logger.error(f"Qdrant health check failed: {str(e)}")
            return False
            
    async def close(self):
        """关闭连接"""
        try:
            if self.client:
                self.client.close()
            self.client = None
            self.logger.info("Qdrant connection closed")
        except Exception as e:
            self.logger.error(f"Error closing Qdrant connection: {str(e)}")