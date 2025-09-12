"""
RAG检索引擎
"""

import asyncio
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from app.services.llm_service import LLMService
from knowledge.chunking import TextChunk
from knowledge.vector_stores import VectorDocument, SearchResult as VectorSearchResult
from knowledge.vector_stores.factory import get_vector_store_manager


class SearchType(str, Enum):
    """搜索类型枚举"""
    SEMANTIC = "semantic"      # 语义搜索
    KEYWORD = "keyword"        # 关键词搜索
    HYBRID = "hybrid"          # 混合搜索
    FULL_TEXT = "full_text"    # 全文搜索


@dataclass
class SearchResult:
    """搜索结果"""
    content: str
    score: float
    metadata: Dict[str, Any]
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
            "chunk_id": self.chunk_id,
            "document_id": self.document_id
        }


class BaseRetriever(ABC):
    """检索器基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """搜索"""
        pass
    
    @abstractmethod
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        **kwargs
    ) -> bool:
        """添加文档"""
        pass


class SemanticRetriever(BaseRetriever):
    """语义检索器"""
    
    def __init__(
        self,
        llm_service: LLMService,
        embedding_model_id: str,
        vector_store=None
    ):
        super().__init__("semantic")
        self.llm_service = llm_service
        self.embedding_model_id = embedding_model_id
        self.vector_store = vector_store
        self.documents: List[Dict[str, Any]] = []  # 临时存储，实际应使用向量数据库
        self.embeddings: List[List[float]] = []   # 临时存储
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """语义搜索"""
        try:
            # 生成查询向量
            query_embedding = await self._get_embedding(query)
            
            if self.vector_store:
                # 使用向量数据库搜索
                return await self._search_vector_store(query_embedding, top_k, filters)
            else:
                # 使用内存搜索（仅用于测试）
                return await self._search_memory(query_embedding, top_k, filters)
                
        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return []
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        **kwargs
    ) -> bool:
        """添加文档"""
        try:
            # 生成嵌入向量
            texts = [doc.get("content", "") for doc in documents]
            embeddings = await self._get_embeddings(texts)
            
            if self.vector_store:
                # 添加到向量数据库
                return await self._add_to_vector_store(documents, embeddings)
            else:
                # 添加到内存（仅用于测试）
                self.documents.extend(documents)
                self.embeddings.extend(embeddings)
                return True
                
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False
    
    async def _get_embedding(self, text: str) -> List[float]:
        """获取单个文本的嵌入向量"""
        embeddings = await self.llm_service.embedding(
            model_id=self.embedding_model_id,
            texts=[text]
        )
        return embeddings[0] if embeddings else []
    
    async def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取多个文本的嵌入向量"""
        if not texts:
            return []
        
        # 分批处理，避免一次处理过多文本
        batch_size = 10
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = await self.llm_service.embedding(
                model_id=self.embedding_model_id,
                texts=batch_texts
            )
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    async def _search_vector_store(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        """在向量数据库中搜索"""
        try:
            # 获取向量数据库管理器
            vector_manager = get_vector_store_manager()
            
            # 执行向量搜索
            vector_results = await vector_manager.search_similar(
                query_embedding=query_embedding,
                top_k=top_k,
                filter_dict=filters
            )
            
            # 转换结果格式
            search_results = []
            for result in vector_results:
                search_result = SearchResult(
                    content=result.document.content,
                    score=result.score,
                    metadata=result.document.metadata,
                    chunk_id=result.document.metadata.get('chunk_id'),
                    document_id=result.document.metadata.get('document_id')
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"向量数据库搜索失败: {e}")
            return []
    
    async def _search_memory(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[SearchResult]:
        """在内存中搜索"""
        if not self.documents or not self.embeddings:
            return []
        
        # 计算相似度
        similarities = []
        query_vec = np.array(query_embedding)
        
        for i, doc_embedding in enumerate(self.embeddings):
            doc_vec = np.array(doc_embedding)
            
            # 计算余弦相似度
            similarity = np.dot(query_vec, doc_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)
            )
            similarities.append((i, similarity))
        
        # 排序并取前k个
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_results = similarities[:top_k]
        
        # 构建结果
        results = []
        for doc_idx, score in top_results:
            doc = self.documents[doc_idx]
            
            # 应用过滤器
            if filters and not self._apply_filters(doc, filters):
                continue
            
            result = SearchResult(
                content=doc.get("content", ""),
                score=float(score),
                metadata=doc.get("metadata", {}),
                chunk_id=doc.get("chunk_id"),
                document_id=doc.get("document_id")
            )
            results.append(result)
        
        return results
    
    def _apply_filters(self, document: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """应用过滤器"""
        metadata = document.get("metadata", {})
        
        for key, value in filters.items():
            if key not in metadata:
                return False
            
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            else:
                if metadata[key] != value:
                    return False
        
        return True
    
    async def _add_to_vector_store(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> bool:
        """添加到向量数据库"""
        try:
            # 获取向量数据库管理器
            vector_manager = get_vector_store_manager()
            
            # 准备向量文档
            vector_docs = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                vector_doc = VectorDocument(
                    id=doc.get('id', f'doc_{i}_{int(datetime.now().timestamp())}'),
                    content=doc.get('content', ''),
                    embedding=embedding,
                    metadata=doc.get('metadata', {})
                )
                vector_docs.append(vector_doc)
            
            # 批量添加文档
            return await vector_manager.add_documents(vector_docs)
            
        except Exception as e:
            logger.error(f"添加文档到向量数据库失败: {e}")
            return False


class KeywordRetriever(BaseRetriever):
    """关键词检索器"""
    
    def __init__(self):
        super().__init__("keyword")
        self.documents: List[Dict[str, Any]] = []
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """关键词搜索"""
        try:
            # 简单的关键词匹配
            query_words = set(query.lower().split())
            scored_docs = []
            
            for doc in self.documents:
                content = doc.get("content", "").lower()
                
                # 应用过滤器
                if filters and not self._apply_filters(doc, filters):
                    continue
                
                # 计算关键词匹配分数
                content_words = set(content.split())
                matched_words = query_words.intersection(content_words)
                
                if matched_words:
                    # 计算 TF-IDF 风格的分数
                    score = len(matched_words) / len(query_words)
                    
                    # 考虑词频
                    for word in matched_words:
                        word_freq = content.count(word)
                        score += word_freq * 0.1
                    
                    scored_docs.append((doc, score))
            
            # 排序并取前k个
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            top_docs = scored_docs[:top_k]
            
            # 构建结果
            results = []
            for doc, score in top_docs:
                result = SearchResult(
                    content=doc.get("content", ""),
                    score=score,
                    metadata=doc.get("metadata", {}),
                    chunk_id=doc.get("chunk_id"),
                    document_id=doc.get("document_id")
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            return []
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        **kwargs
    ) -> bool:
        """添加文档"""
        try:
            self.documents.extend(documents)
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False
    
    def _apply_filters(self, document: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """应用过滤器"""
        metadata = document.get("metadata", {})
        
        for key, value in filters.items():
            if key not in metadata:
                return False
            
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            else:
                if metadata[key] != value:
                    return False
        
        return True


class HybridRetriever(BaseRetriever):
    """混合检索器"""
    
    def __init__(
        self,
        semantic_retriever: SemanticRetriever,
        keyword_retriever: KeywordRetriever,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        super().__init__("hybrid")
        self.semantic_retriever = semantic_retriever
        self.keyword_retriever = keyword_retriever
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """混合搜索"""
        try:
            # 并行执行语义搜索和关键词搜索
            semantic_task = self.semantic_retriever.search(
                query, top_k * 2, filters, **kwargs
            )
            keyword_task = self.keyword_retriever.search(
                query, top_k * 2, filters, **kwargs
            )
            
            semantic_results, keyword_results = await asyncio.gather(
                semantic_task, keyword_task
            )
            
            # 合并和重新排序结果
            combined_results = self._combine_results(
                semantic_results, keyword_results
            )
            
            return combined_results[:top_k]
            
        except Exception as e:
            logger.error(f"混合搜索失败: {e}")
            return []
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        **kwargs
    ) -> bool:
        """添加文档"""
        try:
            # 同时添加到两个检索器
            semantic_task = self.semantic_retriever.add_documents(documents, **kwargs)
            keyword_task = self.keyword_retriever.add_documents(documents, **kwargs)
            
            semantic_success, keyword_success = await asyncio.gather(
                semantic_task, keyword_task
            )
            
            return semantic_success and keyword_success
            
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False
    
    def _combine_results(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult]
    ) -> List[SearchResult]:
        """合并搜索结果"""
        # 构建结果字典，以内容为键
        result_map: Dict[str, SearchResult] = {}
        
        # 添加语义搜索结果
        for result in semantic_results:
            content_key = result.content[:100]  # 使用前100个字符作为键
            if content_key in result_map:
                # 更新分数
                result_map[content_key].score = (
                    result_map[content_key].score + 
                    result.score * self.semantic_weight
                )
            else:
                result.score *= self.semantic_weight
                result_map[content_key] = result
        
        # 添加关键词搜索结果
        for result in keyword_results:
            content_key = result.content[:100]
            if content_key in result_map:
                # 更新分数
                result_map[content_key].score += result.score * self.keyword_weight
            else:
                result.score *= self.keyword_weight
                result_map[content_key] = result
        
        # 按分数排序
        combined_results = list(result_map.values())
        combined_results.sort(key=lambda x: x.score, reverse=True)
        
        return combined_results


class RetrievalService:
    """检索服务"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.retrievers: Dict[str, BaseRetriever] = {}
    
    def register_retriever(self, retriever: BaseRetriever):
        """注册检索器"""
        self.retrievers[retriever.name] = retriever
        logger.info(f"检索器已注册: {retriever.name}")
    
    async def search(
        self,
        query: str,
        search_type: SearchType = SearchType.HYBRID,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        knowledge_base_id: Optional[str] = None,
        **kwargs
    ) -> List[SearchResult]:
        """搜索"""
        try:
            # 添加知识库过滤器
            if knowledge_base_id and filters is None:
                filters = {"knowledge_base_id": knowledge_base_id}
            elif knowledge_base_id and filters:
                filters["knowledge_base_id"] = knowledge_base_id
            
            # 选择检索器
            retriever_name = search_type.value
            if retriever_name not in self.retrievers:
                logger.warning(f"检索器不存在: {retriever_name}，使用默认检索器")
                retriever_name = "semantic"
            
            retriever = self.retrievers[retriever_name]
            
            # 执行搜索
            results = await retriever.search(query, top_k, filters, **kwargs)
            
            logger.info(f"检索完成: {len(results)} 个结果，类型: {search_type}")
            return results
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        search_types: Optional[List[SearchType]] = None,
        **kwargs
    ) -> Dict[str, bool]:
        """添加文档到检索器"""
        if search_types is None:
            search_types = [SearchType.SEMANTIC, SearchType.KEYWORD]
        
        results = {}
        
        for search_type in search_types:
            retriever_name = search_type.value
            if retriever_name in self.retrievers:
                retriever = self.retrievers[retriever_name]
                success = await retriever.add_documents(documents, **kwargs)
                results[retriever_name] = success
            else:
                results[retriever_name] = False
        
        return results
    
    def list_retrievers(self) -> List[str]:
        """列出可用检索器"""
        return list(self.retrievers.keys())


# 初始化检索服务的函数
async def create_retrieval_service(
    llm_service: LLMService,
    embedding_model_id: str,
    vector_store=None
) -> RetrievalService:
    """创建检索服务"""
    service = RetrievalService(llm_service)
    
    # 创建检索器
    semantic_retriever = SemanticRetriever(
        llm_service=llm_service,
        embedding_model_id=embedding_model_id,
        vector_store=vector_store
    )
    
    keyword_retriever = KeywordRetriever()
    
    hybrid_retriever = HybridRetriever(
        semantic_retriever=semantic_retriever,
        keyword_retriever=keyword_retriever
    )
    
    # 注册检索器
    service.register_retriever(semantic_retriever)
    service.register_retriever(keyword_retriever)
    service.register_retriever(hybrid_retriever)
    
    return service