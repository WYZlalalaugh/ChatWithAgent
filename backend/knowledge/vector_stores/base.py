"""
向量数据库基础抽象类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class VectorDocument:
    """向量文档数据类"""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass 
class SearchResult:
    """搜索结果数据类"""
    document: VectorDocument
    score: float
    

class BaseVectorStore(ABC):
    """向量数据库基础抽象类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.collection_name = config.get('collection_name', 'default')
        self.dimension = config.get('dimension', 1536)
        
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化向量数据库连接"""
        pass
        
    @abstractmethod  
    async def create_collection(self, collection_name: str, dimension: int) -> bool:
        """创建向量集合"""
        pass
        
    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """删除向量集合"""
        pass
        
    @abstractmethod
    async def list_collections(self) -> List[str]:
        """列出所有向量集合"""
        pass
        
    @abstractmethod
    async def add_documents(self, documents: List[VectorDocument]) -> bool:
        """添加文档到向量数据库"""
        pass
        
    @abstractmethod
    async def update_document(self, document: VectorDocument) -> bool:
        """更新文档"""
        pass
        
    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        pass
        
    @abstractmethod
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """批量删除文档"""
        pass
        
    @abstractmethod
    async def search_similar(
        self, 
        query_embedding: List[float], 
        top_k: int = 10,
        score_threshold: float = 0.0,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """相似性搜索"""
        pass
        
    @abstractmethod
    async def search_by_ids(self, document_ids: List[str]) -> List[VectorDocument]:
        """根据ID搜索文档"""
        pass
        
    @abstractmethod
    async def get_document_count(self) -> int:
        """获取文档总数"""
        pass
        
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
        
    @abstractmethod
    async def close(self):
        """关闭连接"""
        pass
        
    async def batch_add_documents(
        self, 
        documents: List[VectorDocument], 
        batch_size: int = 100
    ) -> bool:
        """批量添加文档"""
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            success = await self.add_documents(batch)
            if not success:
                return False
        return True
        
    def _validate_embedding_dimension(self, embedding: List[float]) -> bool:
        """验证向量维度"""
        return len(embedding) == self.dimension