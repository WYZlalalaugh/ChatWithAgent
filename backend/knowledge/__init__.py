"""
知识库系统模块
"""

from .processors.text import TextDocumentProcessor
from .chunking import ChunkingService
from .retrieval import RetrievalService
from .vector_stores import (
    VectorStoreManager,
    VectorStoreType,
    BaseVectorStore,
    VectorDocument,
    SearchResult
)
from .vector_stores.factory import (
    VectorStoreFactory,
    VectorStoreConfigManager,
    get_vector_store_manager,
    initialize_default_vector_store
)

__all__ = [
    'TextDocumentProcessor',
    'ChunkingService', 
    'RetrievalService',
    'VectorStoreManager',
    'VectorStoreType',
    'BaseVectorStore',
    'VectorDocument',
    'SearchResult',
    'VectorStoreFactory',
    'VectorStoreConfigManager',
    'get_vector_store_manager',
    'initialize_default_vector_store'
]