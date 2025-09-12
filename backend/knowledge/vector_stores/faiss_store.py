"""
FAISS向量数据库适配器
"""

import asyncio
import logging
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
import faiss

from .base import BaseVectorStore, VectorDocument, SearchResult


class FAISSVectorStore(BaseVectorStore):
    """FAISS向量数据库实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # FAISS配置
        self.index_type = config.get('index_type', 'IVFFlat')
        self.nlist = config.get('nlist', 100)  # IVF参数
        self.persist_directory = config.get('persist_directory', './faiss_index')
        self.metric_type = config.get('metric_type', 'IP')  # IP或L2
        
        # 内部状态
        self.index = None
        self.documents: Dict[str, VectorDocument] = {}
        self.id_to_idx: Dict[str, int] = {}
        self.idx_to_id: Dict[int, str] = {}
        self.next_idx = 0
        
        # 确保持久化目录存在
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
    async def initialize(self) -> bool:
        """初始化FAISS索引"""
        try:
            # 尝试加载现有索引
            if await self._load_index():
                self.logger.info("Loaded existing FAISS index")
            else:
                # 创建新索引
                await self._create_index()
                self.logger.info("Created new FAISS index")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize FAISS: {str(e)}")
            return False
            
    async def _create_index(self):
        """创建FAISS索引"""
        if self.index_type == 'IVFFlat':
            # 创建IVFFlat索引
            quantizer = faiss.IndexFlatIP(self.dimension) if self.metric_type == 'IP' else faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)
        elif self.index_type == 'Flat':
            # 创建Flat索引
            self.index = faiss.IndexFlatIP(self.dimension) if self.metric_type == 'IP' else faiss.IndexFlatL2(self.dimension)
        elif self.index_type == 'HNSW':
            # 创建HNSW索引
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)
            self.index.hnsw.efConstruction = 200
            self.index.hnsw.efSearch = 100
        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")
            
    async def _load_index(self) -> bool:
        """加载现有索引"""
        try:
            index_path = Path(self.persist_directory) / f"{self.collection_name}.index"
            metadata_path = Path(self.persist_directory) / f"{self.collection_name}.pkl"
            
            if not index_path.exists() or not metadata_path.exists():
                return False
                
            # 加载索引
            self.index = faiss.read_index(str(index_path))
            
            # 加载元数据
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
                self.documents = metadata['documents']
                self.id_to_idx = metadata['id_to_idx']
                self.idx_to_id = metadata['idx_to_id']
                self.next_idx = metadata['next_idx']
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load FAISS index: {str(e)}")
            return False
            
    async def _save_index(self) -> bool:
        """保存索引"""
        try:
            index_path = Path(self.persist_directory) / f"{self.collection_name}.index"
            metadata_path = Path(self.persist_directory) / f"{self.collection_name}.pkl"
            
            # 保存索引
            faiss.write_index(self.index, str(index_path))
            
            # 保存元数据
            metadata = {
                'documents': self.documents,
                'id_to_idx': self.id_to_idx,
                'idx_to_id': self.idx_to_id,
                'next_idx': self.next_idx
            }
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save FAISS index: {str(e)}")
            return False
            
    async def create_collection(self, collection_name: str, dimension: int) -> bool:
        """创建向量集合"""
        try:
            old_collection = self.collection_name
            self.collection_name = collection_name
            self.dimension = dimension
            
            # 创建新索引
            await self._create_index()
            
            # 重置状态
            self.documents.clear()
            self.id_to_idx.clear()
            self.idx_to_id.clear()
            self.next_idx = 0
            
            # 保存新索引
            await self._save_index()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create collection {collection_name}: {str(e)}")
            self.collection_name = old_collection
            return False
            
    async def delete_collection(self, collection_name: str) -> bool:
        """删除向量集合"""
        try:
            index_path = Path(self.persist_directory) / f"{collection_name}.index"
            metadata_path = Path(self.persist_directory) / f"{collection_name}.pkl"
            
            # 删除文件
            if index_path.exists():
                index_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
                
            # 如果删除的是当前集合，重置状态
            if collection_name == self.collection_name:
                self.index = None
                self.documents.clear()
                self.id_to_idx.clear()
                self.idx_to_id.clear()
                self.next_idx = 0
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete collection {collection_name}: {str(e)}")
            return False
            
    async def list_collections(self) -> List[str]:
        """列出所有向量集合"""
        try:
            directory = Path(self.persist_directory)
            collections = []
            
            for file_path in directory.glob("*.index"):
                collection_name = file_path.stem
                collections.append(collection_name)
                
            return collections
            
        except Exception as e:
            self.logger.error(f"Failed to list collections: {str(e)}")
            return []
            
    async def add_documents(self, documents: List[VectorDocument]) -> bool:
        """添加文档到向量数据库"""
        try:
            if self.index is None:
                await self._create_index()
            
            # 准备向量数据
            embeddings = []
            for doc in documents:
                if not self._validate_embedding_dimension(doc.embedding):
                    self.logger.error(f"Invalid embedding dimension: {len(doc.embedding)}")
                    return False
                embeddings.append(doc.embedding)
                
            # 转换为numpy数组
            vectors = np.array(embeddings, dtype=np.float32)
            
            # 如果是训练型索引且未训练，先训练
            if hasattr(self.index, 'is_trained') and not self.index.is_trained:
                if len(vectors) < self.nlist:
                    # 数据量不足以训练，创建临时数据
                    temp_vectors = np.random.random((self.nlist, self.dimension)).astype(np.float32)
                    self.index.train(temp_vectors)
                else:
                    self.index.train(vectors)
                    
            # 添加向量到索引
            start_idx = self.next_idx
            self.index.add(vectors)
            
            # 更新映射关系和文档存储
            for i, doc in enumerate(documents):
                idx = start_idx + i
                self.documents[doc.id] = doc
                self.id_to_idx[doc.id] = idx
                self.idx_to_id[idx] = doc.id
                
            self.next_idx += len(documents)
            
            # 保存索引
            await self._save_index()
            
            self.logger.info(f"Added {len(documents)} documents to FAISS")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add documents: {str(e)}")
            return False
            
    async def update_document(self, document: VectorDocument) -> bool:
        """更新文档"""
        try:
            # FAISS不支持直接更新，需要删除后重新添加
            if document.id in self.id_to_idx:
                # 删除旧文档
                await self.delete_document(document.id)
                
            # 添加新文档
            return await self.add_documents([document])
            
        except Exception as e:
            self.logger.error(f"Failed to update document {document.id}: {str(e)}")
            return False
            
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        try:
            if document_id not in self.id_to_idx:
                self.logger.warning(f"Document {document_id} not found")
                return True
                
            # FAISS不支持直接删除，我们只从映射中移除
            # 在实际应用中，可能需要重建索引来真正删除
            idx = self.id_to_idx[document_id]
            
            del self.documents[document_id]
            del self.id_to_idx[document_id]
            del self.idx_to_id[idx]
            
            # 保存更新后的元数据
            await self._save_index()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete document {document_id}: {str(e)}")
            return False
            
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """批量删除文档"""
        try:
            for doc_id in document_ids:
                if not await self.delete_document(doc_id):
                    return False
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
            if self.index is None or self.index.ntotal == 0:
                return []
                
            if not self._validate_embedding_dimension(query_embedding):
                self.logger.error(f"Invalid query embedding dimension: {len(query_embedding)}")
                return []
            
            # 准备查询向量
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # 执行搜索
            scores, indices = self.index.search(query_vector, top_k)
            
            # 处理结果
            search_results = []
            for i in range(len(indices[0])):
                idx = indices[0][i]
                score = float(scores[0][i])
                
                # 检查索引是否有效
                if idx == -1:  # FAISS返回-1表示未找到
                    continue
                    
                # 获取文档ID
                doc_id = self.idx_to_id.get(idx)
                if not doc_id:
                    continue
                    
                # 获取文档
                doc = self.documents.get(doc_id)
                if not doc:
                    continue
                    
                # 应用过滤器
                if filter_dict:
                    if not self._apply_filter(doc.metadata, filter_dict):
                        continue
                        
                # 转换分数（FAISS返回距离，需要根据metric_type转换）
                if self.metric_type == 'IP':
                    # 内积，分数越高越相似
                    similarity_score = score
                else:
                    # L2距离，距离越小越相似
                    similarity_score = 1.0 / (1.0 + score)
                    
                if similarity_score >= score_threshold:
                    search_results.append(SearchResult(
                        document=doc,
                        score=similarity_score
                    ))
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Failed to search similar documents: {str(e)}")
            return []
            
    def _apply_filter(self, metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """应用过滤器"""
        for key, value in filter_dict.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
        
    async def search_by_ids(self, document_ids: List[str]) -> List[VectorDocument]:
        """根据ID搜索文档"""
        try:
            documents = []
            for doc_id in document_ids:
                doc = self.documents.get(doc_id)
                if doc:
                    documents.append(doc)
            return documents
        except Exception as e:
            self.logger.error(f"Failed to search documents by IDs: {str(e)}")
            return []
            
    async def get_document_count(self) -> int:
        """获取文档总数"""
        try:
            return len(self.documents)
        except Exception as e:
            self.logger.error(f"Failed to get document count: {str(e)}")
            return 0
            
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            return self.index is not None
        except Exception as e:
            self.logger.error(f"FAISS health check failed: {str(e)}")
            return False
            
    async def close(self):
        """关闭连接"""
        try:
            # 保存最新状态
            if self.index is not None:
                await self._save_index()
            
            # 清理内存
            self.index = None
            self.documents.clear()
            self.id_to_idx.clear()
            self.idx_to_id.clear()
            
            self.logger.info("FAISS connection closed")
        except Exception as e:
            self.logger.error(f"Error closing FAISS connection: {str(e)}")