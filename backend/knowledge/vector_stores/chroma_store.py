"""
Chroma向量数据库适配器
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.api.models.Collection import Collection

from .base import BaseVectorStore, VectorDocument, SearchResult


class ChromaVectorStore(BaseVectorStore):
    """Chroma向量数据库实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.collection = None
        
        # Chroma配置
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 8000)
        self.persist_directory = config.get('persist_directory')
        self.is_persistent = self.persist_directory is not None
        
    async def initialize(self) -> bool:
        """初始化Chroma客户端"""
        try:
            if self.is_persistent:
                # 持久化模式
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory
                )
            else:
                # 内存模式或服务器模式
                try:
                    self.client = chromadb.HttpClient(
                        host=self.host,
                        port=self.port
                    )
                except Exception:
                    # 如果连接服务器失败，退回到内存模式
                    self.client = chromadb.Client()
                    self.logger.warning("Failed to connect to Chroma server, using in-memory client")
            
            # 测试连接
            await self._run_in_executor(self.client.heartbeat)
            
            # 获取或创建集合
            await self._get_or_create_collection()
            
            self.logger.info("Chroma vector store initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Chroma: {str(e)}")
            return False
            
    async def _run_in_executor(self, func, *args, **kwargs):
        """在线程池中运行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
        
    async def _get_or_create_collection(self) -> Collection:
        """获取或创建集合"""
        if self.collection is None:
            self.collection = await self._run_in_executor(
                self.client.get_or_create_collection,
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        return self.collection
        
    async def create_collection(self, collection_name: str, dimension: int) -> bool:
        """创建向量集合"""
        try:
            await self._run_in_executor(
                self.client.create_collection,
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to create collection {collection_name}: {str(e)}")
            return False
            
    async def delete_collection(self, collection_name: str) -> bool:
        """删除向量集合"""
        try:
            await self._run_in_executor(
                self.client.delete_collection,
                name=collection_name
            )
            if collection_name == self.collection_name:
                self.collection = None
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete collection {collection_name}: {str(e)}")
            return False
            
    async def list_collections(self) -> List[str]:
        """列出所有向量集合"""
        try:
            collections = await self._run_in_executor(self.client.list_collections)
            return [col.name for col in collections]
        except Exception as e:
            self.logger.error(f"Failed to list collections: {str(e)}")
            return []
            
    async def add_documents(self, documents: List[VectorDocument]) -> bool:
        """添加文档到向量数据库"""
        try:
            collection = await self._get_or_create_collection()
            
            # 准备数据
            ids = [doc.id for doc in documents]
            embeddings = [doc.embedding for doc in documents]
            documents_text = [doc.content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            
            # 验证向量维度
            for embedding in embeddings:
                if not self._validate_embedding_dimension(embedding):
                    self.logger.error(f"Invalid embedding dimension: {len(embedding)}")
                    return False
            
            await self._run_in_executor(
                collection.add,
                ids=ids,
                embeddings=embeddings,
                documents=documents_text,
                metadatas=metadatas
            )
            
            self.logger.info(f"Added {len(documents)} documents to Chroma")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add documents: {str(e)}")
            return False
            
    async def update_document(self, document: VectorDocument) -> bool:
        """更新文档"""
        try:
            collection = await self._get_or_create_collection()
            
            if not self._validate_embedding_dimension(document.embedding):
                self.logger.error(f"Invalid embedding dimension: {len(document.embedding)}")
                return False
            
            await self._run_in_executor(
                collection.update,
                ids=[document.id],
                embeddings=[document.embedding],
                documents=[document.content],
                metadatas=[document.metadata]
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update document {document.id}: {str(e)}")
            return False
            
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        try:
            collection = await self._get_or_create_collection()
            
            await self._run_in_executor(
                collection.delete,
                ids=[document_id]
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete document {document_id}: {str(e)}")
            return False
            
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """批量删除文档"""
        try:
            collection = await self._get_or_create_collection()
            
            await self._run_in_executor(
                collection.delete,
                ids=document_ids
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
            collection = await self._get_or_create_collection()
            
            if not self._validate_embedding_dimension(query_embedding):
                self.logger.error(f"Invalid query embedding dimension: {len(query_embedding)}")
                return []
            
            # 构建where条件
            where_clause = filter_dict if filter_dict else None
            
            results = await self._run_in_executor(
                collection.query,
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
                include=['documents', 'metadatas', 'distances']
            )
            
            # 处理结果
            search_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    # Chroma返回距离，需要转换为相似度分数
                    distance = results['distances'][0][i]
                    score = 1.0 / (1.0 + distance)  # 简单的距离到相似度转换
                    
                    if score >= score_threshold:
                        doc = VectorDocument(
                            id=results['ids'][0][i],
                            content=results['documents'][0][i],
                            embedding=query_embedding,  # Chroma不返回原始embedding
                            metadata=results['metadatas'][0][i] or {}
                        )
                        
                        search_results.append(SearchResult(
                            document=doc,
                            score=score
                        ))
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Failed to search similar documents: {str(e)}")
            return []
            
    async def search_by_ids(self, document_ids: List[str]) -> List[VectorDocument]:
        """根据ID搜索文档"""
        try:
            collection = await self._get_or_create_collection()
            
            results = await self._run_in_executor(
                collection.get,
                ids=document_ids,
                include=['documents', 'metadatas']
            )
            
            documents = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    doc = VectorDocument(
                        id=results['ids'][i],
                        content=results['documents'][i],
                        embedding=[],  # Chroma不返回embedding
                        metadata=results['metadatas'][i] or {}
                    )
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Failed to search documents by IDs: {str(e)}")
            return []
            
    async def get_document_count(self) -> int:
        """获取文档总数"""
        try:
            collection = await self._get_or_create_collection()
            count = await self._run_in_executor(collection.count)
            return count
        except Exception as e:
            self.logger.error(f"Failed to get document count: {str(e)}")
            return 0
            
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if self.client is None:
                return False
            await self._run_in_executor(self.client.heartbeat)
            return True
        except Exception as e:
            self.logger.error(f"Chroma health check failed: {str(e)}")
            return False
            
    async def close(self):
        """关闭连接"""
        try:
            # Chroma客户端通常不需要显式关闭
            self.client = None
            self.collection = None
            self.logger.info("Chroma connection closed")
        except Exception as e:
            self.logger.error(f"Error closing Chroma connection: {str(e)}")