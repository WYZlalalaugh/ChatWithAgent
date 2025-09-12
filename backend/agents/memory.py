"""
智能体记忆模块
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from loguru import logger

from app.core.redis import RedisClient


class MemoryType(str, Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working"
    EPISODIC = "episodic"


class MemoryEntry:
    """记忆条目"""
    
    def __init__(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.id = f"mem_{int(datetime.utcnow().timestamp() * 1000000)}"
        self.content = content
        self.memory_type = memory_type
        self.importance = importance
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.utcnow()
        self.access_count = 0
        self.last_accessed = self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "importance": self.importance,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """从字典创建"""
        entry = cls(
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            importance=data["importance"],
            metadata=data["metadata"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )
        entry.id = data["id"]
        entry.access_count = data["access_count"]
        entry.last_accessed = datetime.fromisoformat(data["last_accessed"])
        return entry
    
    def access(self):
        """访问记忆（更新访问统计）"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


class ConversationMemory:
    """对话记忆"""
    
    def __init__(
        self,
        conversation_id: str,
        max_short_term: int = 20,
        max_working: int = 10,
        redis_client: Optional[RedisClient] = None
    ):
        self.conversation_id = conversation_id
        self.max_short_term = max_short_term
        self.max_working = max_working
        self.redis_client = redis_client
        
        # 内存存储
        self.short_term_memory: List[MemoryEntry] = []
        self.working_memory: List[MemoryEntry] = []
        self.long_term_memory: List[MemoryEntry] = []
        
        # 从 Redis 加载记忆
        if self.redis_client:
            asyncio.create_task(self._load_from_redis())
    
    async def add_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """添加记忆"""
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata
        )
        
        if memory_type == MemoryType.SHORT_TERM:
            self.short_term_memory.append(entry)
            # 保持短期记忆大小限制
            if len(self.short_term_memory) > self.max_short_term:
                # 移除最老的记忆
                removed = self.short_term_memory.pop(0)
                # 如果重要性高，转移到长期记忆
                if removed.importance > 0.7:
                    removed.memory_type = MemoryType.LONG_TERM
                    self.long_term_memory.append(removed)
        
        elif memory_type == MemoryType.WORKING:
            self.working_memory.append(entry)
            # 保持工作记忆大小限制
            if len(self.working_memory) > self.max_working:
                self.working_memory.pop(0)
        
        elif memory_type == MemoryType.LONG_TERM:
            self.long_term_memory.append(entry)
        
        # 保存到 Redis
        if self.redis_client:
            await self._save_to_redis()
        
        logger.debug(f"添加记忆: {memory_type.value} - {content[:50]}...")
        return entry
    
    def get_recent_memories(
        self,
        count: int = 10,
        memory_types: Optional[List[MemoryType]] = None
    ) -> List[MemoryEntry]:
        """获取最近的记忆"""
        if memory_types is None:
            memory_types = [MemoryType.SHORT_TERM, MemoryType.WORKING]
        
        memories = []
        
        if MemoryType.SHORT_TERM in memory_types:
            memories.extend(self.short_term_memory)
        if MemoryType.WORKING in memory_types:
            memories.extend(self.working_memory)
        if MemoryType.LONG_TERM in memory_types:
            memories.extend(self.long_term_memory)
        
        # 按时间戳排序
        memories.sort(key=lambda x: x.timestamp, reverse=True)
        
        # 返回最近的记忆并更新访问统计
        recent = memories[:count]
        for memory in recent:
            memory.access()
        
        return recent
    
    def search_memories(
        self,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 5
    ) -> List[MemoryEntry]:
        """搜索记忆"""
        if memory_types is None:
            memory_types = [MemoryType.SHORT_TERM, MemoryType.WORKING, MemoryType.LONG_TERM]
        
        memories = []
        
        if MemoryType.SHORT_TERM in memory_types:
            memories.extend(self.short_term_memory)
        if MemoryType.WORKING in memory_types:
            memories.extend(self.working_memory)
        if MemoryType.LONG_TERM in memory_types:
            memories.extend(self.long_term_memory)
        
        # 简单的文本匹配搜索
        query_lower = query.lower()
        matching_memories = []
        
        for memory in memories:
            if query_lower in memory.content.lower():
                matching_memories.append((memory, 1.0))  # 完全匹配得分为1
            elif any(word in memory.content.lower() for word in query_lower.split()):
                matching_memories.append((memory, 0.5))  # 部分匹配得分为0.5
        
        # 按相关性和重要性排序
        matching_memories.sort(
            key=lambda x: (x[1], x[0].importance, x[0].timestamp),
            reverse=True
        )
        
        # 返回结果并更新访问统计
        results = [memory for memory, score in matching_memories[:limit]]
        for memory in results:
            memory.access()
        
        return results
    
    def get_context_summary(self, max_length: int = 500) -> str:
        """获取上下文摘要"""
        # 获取最重要和最近的记忆
        recent_memories = self.get_recent_memories(count=10)
        
        if not recent_memories:
            return "暂无对话记忆。"
        
        # 构建摘要
        context_parts = []
        current_length = 0
        
        for memory in recent_memories:
            content = memory.content
            if current_length + len(content) > max_length:
                # 截断内容
                remaining = max_length - current_length
                if remaining > 50:  # 保留最少50个字符
                    content = content[:remaining] + "..."
                    context_parts.append(content)
                break
            
            context_parts.append(content)
            current_length += len(content)
        
        return "\n".join(context_parts)
    
    def clear_working_memory(self):
        """清除工作记忆"""
        self.working_memory.clear()
        logger.info(f"清除工作记忆: {self.conversation_id}")
    
    def consolidate_memory(self):
        """整理记忆（将重要的短期记忆转为长期记忆）"""
        consolidated = []
        remaining = []
        
        for memory in self.short_term_memory:
            # 根据重要性、访问次数等判断是否转为长期记忆
            score = memory.importance + (memory.access_count * 0.1)
            if score > 0.8:
                memory.memory_type = MemoryType.LONG_TERM
                self.long_term_memory.append(memory)
                consolidated.append(memory)
            else:
                remaining.append(memory)
        
        self.short_term_memory = remaining
        logger.info(f"记忆整理完成: {len(consolidated)} 条记忆转为长期记忆")
        
        return len(consolidated)
    
    async def _save_to_redis(self):
        """保存记忆到 Redis"""
        if not self.redis_client:
            return
        
        try:
            memory_data = {
                "short_term": [entry.to_dict() for entry in self.short_term_memory],
                "working": [entry.to_dict() for entry in self.working_memory],
                "long_term": [entry.to_dict() for entry in self.long_term_memory]
            }
            
            key = f"memory:{self.conversation_id}"
            await self.redis_client.set(key, memory_data, expire=86400)  # 24小时过期
            
        except Exception as e:
            logger.error(f"保存记忆到 Redis 失败: {e}")
    
    async def _load_from_redis(self):
        """从 Redis 加载记忆"""
        if not self.redis_client:
            return
        
        try:
            key = f"memory:{self.conversation_id}"
            data = await self.redis_client.get(key)
            
            if data:
                memory_data = json.loads(data)
                
                self.short_term_memory = [
                    MemoryEntry.from_dict(entry_data)
                    for entry_data in memory_data.get("short_term", [])
                ]
                
                self.working_memory = [
                    MemoryEntry.from_dict(entry_data)
                    for entry_data in memory_data.get("working", [])
                ]
                
                self.long_term_memory = [
                    MemoryEntry.from_dict(entry_data)
                    for entry_data in memory_data.get("long_term", [])
                ]
                
                logger.info(f"从 Redis 加载记忆: {self.conversation_id}")
                
        except Exception as e:
            logger.error(f"从 Redis 加载记忆失败: {e}")


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis_client = redis_client
        self.conversation_memories: Dict[str, ConversationMemory] = {}
    
    def get_conversation_memory(
        self,
        conversation_id: str,
        max_short_term: int = 20,
        max_working: int = 10
    ) -> ConversationMemory:
        """获取对话记忆"""
        if conversation_id not in self.conversation_memories:
            self.conversation_memories[conversation_id] = ConversationMemory(
                conversation_id=conversation_id,
                max_short_term=max_short_term,
                max_working=max_working,
                redis_client=self.redis_client
            )
        
        return self.conversation_memories[conversation_id]
    
    def remove_conversation_memory(self, conversation_id: str):
        """移除对话记忆"""
        if conversation_id in self.conversation_memories:
            del self.conversation_memories[conversation_id]
            logger.info(f"移除对话记忆: {conversation_id}")
    
    async def cleanup_expired_memories(self, days: int = 7):
        """清理过期记忆"""
        if not self.redis_client:
            return
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            for conversation_id, memory in self.conversation_memories.items():
                # 清理长期记忆中的过期记忆
                memory.long_term_memory = [
                    entry for entry in memory.long_term_memory
                    if entry.timestamp > cutoff_time or entry.importance > 0.9
                ]
                
                # 保存更新
                await memory._save_to_redis()
            
            logger.info(f"清理过期记忆完成，阈值: {days} 天")
            
        except Exception as e:
            logger.error(f"清理过期记忆失败: {e}")


# 全局记忆管理器实例
memory_manager: Optional[MemoryManager] = None


async def get_memory_manager() -> MemoryManager:
    """获取记忆管理器"""
    global memory_manager
    if not memory_manager:
        from app.core.redis import get_redis
        redis_client = await get_redis()
        memory_manager = MemoryManager(redis_client)
    
    return memory_manager