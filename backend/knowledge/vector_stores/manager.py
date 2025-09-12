"""
向量数据库管理器
统一管理多种向量数据库后端
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Type
from enum import Enum

from .base import BaseVectorStore, VectorDocument, SearchResult
from .chroma_store import ChromaVectorStore
from .faiss_store import FAISSVectorStore
from .qdrant_store import QdrantVectorStore
from .pinecone_store import PineconeVectorStore


class VectorStoreType(Enum):
    """向量数据库类型枚举"""
    CHROMA = "chroma"
    FAISS = "faiss"
    QDRANT = "qdrant"
    PINECONE = "pinecone"


class VectorStoreManager:
    """向量数据库管理器"""
    
    # 向量数据库类型映射
    STORE_CLASSES: Dict[VectorStoreType, Type[BaseVectorStore]] = {
        VectorStoreType.CHROMA: ChromaVectorStore,
        VectorStoreType.FAISS: FAISSVectorStore,
        VectorStoreType.QDRANT: QdrantVectorStore,
        VectorStoreType.PINECONE: PineconeVectorStore,
    }
    
    def __init__(self, default_config: Dict[str, Any] = None):
        self.logger = logging.getLogger(__name__)
        self.stores: Dict[str, BaseVectorStore] = {}
        self.default_config = default_config or {}
        self.default_store_name = None
        
    async def create_store(
        self, 
        store_name: str,
        store_type: VectorStoreType,
        config: Dict[str, Any]
    ) -> bool:
        """创建向量数据库实例"""
        try:
            if store_name in self.stores:
                self.logger.warning(f"Store {store_name} already exists")
                return False
                
            store_class = self.STORE_CLASSES.get(store_type)
            if not store_class:
                self.logger.error(f"Unsupported store type: {store_type}")
                return False
                
            # 合并默认配置
            final_config = {**self.default_config, **config}
            
            # 创建存储实例
            store = store_class(final_config)
            
            # 初始化连接
            if await store.initialize():
                self.stores[store_name] = store
                
                # 设置默认存储
                if self.default_store_name is None:
                    self.default_store_name = store_name
                    
                self.logger.info(f"Created vector store: {store_name} ({store_type.value})")
                return True
            else:
                self.logger.error(f"Failed to initialize store: {store_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating store {store_name}: {str(e)}")
            return False
            
    async def remove_store(self, store_name: str) -> bool:
        """移除向量数据库实例"""
        try:
            if store_name not in self.stores:
                self.logger.warning(f"Store {store_name} not found")
                return False
                
            store = self.stores[store_name]
            await store.close()
            
            del self.stores[store_name]
            
            # 如果删除的是默认存储，重新设置默认存储
            if self.default_store_name == store_name:
                self.default_store_name = next(iter(self.stores.keys()), None)
                
            self.logger.info(f"Removed vector store: {store_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing store {store_name}: {str(e)}")
            return False
            
    def get_store(self, store_name: Optional[str] = None) -> Optional[BaseVectorStore]:
        """获取向量数据库实例"""
        if store_name is None:
            store_name = self.default_store_name
            
        return self.stores.get(store_name)
        
    def list_stores(self) -> List[str]:
        """列出所有向量数据库实例"""
        return list(self.stores.keys())
        
    async def set_default_store(self, store_name: str) -> bool:
        """设置默认向量数据库"""
        if store_name not in self.stores:
            self.logger.error(f"Store {store_name} not found")
            return False
            
        self.default_store_name = store_name
        self.logger.info(f"Set default store to: {store_name}")
        return True
        
    async def add_documents(
        self, 
        documents: List[VectorDocument],
        store_name: Optional[str] = None
    ) -> bool:
        """添加文档到向量数据库"""
        store = self.get_store(store_name)
        if not store:
            self.logger.error(f"Store not found: {store_name or 'default'}")
            return False
            
        return await store.add_documents(documents)
        
    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        score_threshold: float = 0.0,
        filter_dict: Optional[Dict[str, Any]] = None,
        store_name: Optional[str] = None
    ) -> List[SearchResult]:
        """相似性搜索"""
        store = self.get_store(store_name)
        if not store:
            self.logger.error(f"Store not found: {store_name or 'default'}")
            return []
            
        return await store.search_similar(
            query_embedding, top_k, score_threshold, filter_dict
        )
        
    async def delete_document(
        self, 
        document_id: str,
        store_name: Optional[str] = None
    ) -> bool:
        """删除文档"""
        store = self.get_store(store_name)
        if not store:
            self.logger.error(f"Store not found: {store_name or 'default'}")
            return False
            
        return await store.delete_document(document_id)
        
    async def migrate_data(
        self, 
        source_store: str, 
        target_store: str,
        batch_size: int = 100
    ) -> bool:
        """数据迁移"""
        try:
            source = self.get_store(source_store)
            target = self.get_store(target_store)
            
            if not source or not target:
                self.logger.error("Source or target store not found")
                return False
                
            # 获取源数据库中的所有文档
            # 这里需要根据具体实现来获取所有文档
            # 暂时跳过具体实现
            self.logger.info(f"Starting migration from {source_store} to {target_store}")
            
            # TODO: 实现具体的迁移逻辑
            # 1. 从源数据库获取所有文档
            # 2. 批量插入到目标数据库
            # 3. 验证迁移结果
            
            return True
            
        except Exception as e:
            self.logger.error(f"Migration failed: {str(e)}")
            return False
            
    async def health_check_all(self) -> Dict[str, bool]:
        """检查所有向量数据库的健康状态"""
        results = {}
        
        for store_name, store in self.stores.items():
            try:
                results[store_name] = await store.health_check()
            except Exception as e:
                self.logger.error(f"Health check failed for {store_name}: {str(e)}")
                results[store_name] = False
                
        return results
        
    async def get_statistics(self) -> Dict[str, Dict[str, Any]]:
        """获取所有向量数据库的统计信息"""
        stats = {}
        
        for store_name, store in self.stores.items():
            try:
                collections = await store.list_collections()
                doc_count = await store.get_document_count()
                
                stats[store_name] = {
                    'collections': collections,
                    'document_count': doc_count,
                    'is_healthy': await store.health_check()
                }
            except Exception as e:
                self.logger.error(f"Failed to get stats for {store_name}: {str(e)}")
                stats[store_name] = {
                    'error': str(e),
                    'is_healthy': False
                }
                
        return stats
        
    async def close_all(self):
        """关闭所有向量数据库连接"""
        for store_name, store in self.stores.items():
            try:
                await store.close()
                self.logger.info(f"Closed store: {store_name}")
            except Exception as e:
                self.logger.error(f"Error closing store {store_name}: {str(e)}")
                
        self.stores.clear()
        self.default_store_name = None
        
    def export_config(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            'stores': {name: store.config for name, store in self.stores.items()},
            'default_store': self.default_store_name
        }
        
    async def import_config(self, config: Dict[str, Any]) -> bool:
        """导入配置"""
        try:
            # 关闭现有连接
            await self.close_all()
            
            # 重新创建存储
            stores_config = config.get('stores', {})
            for store_name, store_config in stores_config.items():
                store_type_str = store_config.get('type')
                if store_type_str:
                    store_type = VectorStoreType(store_type_str)
                    await self.create_store(store_name, store_type, store_config)
                    
            # 设置默认存储
            default_store = config.get('default_store')
            if default_store and default_store in self.stores:
                await self.set_default_store(default_store)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import config: {str(e)}")
            return False