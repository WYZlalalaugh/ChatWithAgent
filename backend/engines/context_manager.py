"""
对话上下文管理器
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import hashlib

from app.cache import redis_client
from managers.conversation_manager import conversation_manager
from managers.message_manager import message_manager


class ContextManager:
    """对话上下文管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cache_prefix = "context:"
        self.cache_ttl = 3600  # 1小时缓存
        
        # 上下文配置
        self.max_context_messages = 50
        self.context_summary_threshold = 30
        self.memory_decay_factor = 0.95
    
    async def get_context(
        self,
        conversation_id: str,
        max_messages: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取对话上下文"""
        try:
            cache_key = f"{self.cache_prefix}{conversation_id}"
            
            # 尝试从缓存获取
            cached_context = await redis_client.get(cache_key)
            if cached_context:
                try:
                    context = json.loads(cached_context)
                    # 检查缓存时效性
                    if self._is_context_valid(context):
                        return context
                except (json.JSONDecodeError, KeyError):
                    pass
            
            # 从数据库重建上下文
            context = await self._build_context_from_db(
                conversation_id, max_messages or self.max_context_messages
            )
            
            # 缓存上下文
            await self._cache_context(conversation_id, context)
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get context for {conversation_id}: {e}")
            return self._create_empty_context(conversation_id)
    
    async def update_context(
        self,
        conversation_id: str,
        new_message: Dict[str, Any],
        response_message: Optional[Dict[str, Any]] = None
    ):
        """更新对话上下文"""
        try:
            # 获取当前上下文
            context = await self.get_context(conversation_id)
            
            # 添加新消息
            context['messages'].append(new_message)
            
            if response_message:
                context['messages'].append(response_message)
            
            # 更新元数据
            context['last_updated'] = datetime.utcnow().isoformat()
            context['message_count'] = len(context['messages'])
            
            # 管理上下文长度
            context = await self._manage_context_length(context)
            
            # 更新记忆权重
            context = self._update_memory_weights(context)
            
            # 缓存更新后的上下文
            await self._cache_context(conversation_id, context)
            
        except Exception as e:
            self.logger.error(f"Failed to update context for {conversation_id}: {e}")
    
    async def _build_context_from_db(
        self,
        conversation_id: str,
        max_messages: int
    ) -> Dict[str, Any]:
        """从数据库构建上下文"""
        try:
            # 获取对话信息
            conversation = await conversation_manager.get_conversation_by_id(conversation_id)
            
            # 获取最近的消息
            messages, _ = await message_manager.get_messages(
                filters={'conversation_id': conversation_id},
                limit=max_messages,
                order_by=['created_at']
            )
            
            # 构建上下文
            context = {
                'conversation_id': conversation_id,
                'messages': [
                    {
                        'id': msg.id,
                        'role': 'user' if msg.sender_type == 'user' else 'assistant',
                        'content': msg.content,
                        'timestamp': msg.created_at.isoformat(),
                        'metadata': msg.metadata,
                        'weight': 1.0  # 初始权重
                    }
                    for msg in messages
                ],
                'metadata': conversation.context if conversation else {},
                'created_at': conversation.created_at.isoformat() if conversation else datetime.utcnow().isoformat(),
                'last_updated': datetime.utcnow().isoformat(),
                'message_count': len(messages),
                'summary': None,
                'topics': [],
                'entities': {},
                'sentiment': 'neutral'
            }
            
            # 分析上下文
            context = await self._analyze_context(context)
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to build context from DB: {e}")
            return self._create_empty_context(conversation_id)
    
    def _create_empty_context(self, conversation_id: str) -> Dict[str, Any]:
        """创建空上下文"""
        return {
            'conversation_id': conversation_id,
            'messages': [],
            'metadata': {},
            'created_at': datetime.utcnow().isoformat(),
            'last_updated': datetime.utcnow().isoformat(),
            'message_count': 0,
            'summary': None,
            'topics': [],
            'entities': {},
            'sentiment': 'neutral'
        }
    
    async def _manage_context_length(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """管理上下文长度"""
        try:
            messages = context['messages']
            
            if len(messages) <= self.max_context_messages:
                return context
            
            # 需要压缩或截断
            if len(messages) > self.context_summary_threshold:
                # 生成摘要并保留最近的消息
                old_messages = messages[:-self.max_context_messages//2]
                recent_messages = messages[-self.max_context_messages//2:]
                
                # 生成摘要
                summary = await self._generate_context_summary(old_messages)
                context['summary'] = summary
                
                # 保留最近的消息
                context['messages'] = recent_messages
            else:
                # 简单截断
                context['messages'] = messages[-self.max_context_messages:]
            
            context['message_count'] = len(context['messages'])
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to manage context length: {e}")
            return context
    
    async def _generate_context_summary(self, messages: List[Dict[str, Any]]) -> str:
        """生成上下文摘要"""
        try:
            if not messages:
                return ""
            
            # 构建对话文本
            conversation_text = []
            for msg in messages:
                role = "用户" if msg['role'] == 'user' else "助手"
                conversation_text.append(f"{role}: {msg['content']}")
            
            text = "\n".join(conversation_text)
            
            # 这里可以接入LLM生成摘要，现在先用简化版本
            # TODO: 集成LLM摘要功能
            
            # 简化的摘要生成
            summary_points = []
            
            # 提取关键词
            keywords = self._extract_keywords(text)
            if keywords:
                summary_points.append(f"主要关键词: {', '.join(keywords[:5])}")
            
            # 消息数量统计
            user_messages = len([m for m in messages if m['role'] == 'user'])
            bot_messages = len([m for m in messages if m['role'] == 'assistant'])
            summary_points.append(f"包含 {user_messages} 条用户消息和 {bot_messages} 条助手回复")
            
            # 时间跨度
            if len(messages) >= 2:
                start_time = messages[0]['timestamp']
                end_time = messages[-1]['timestamp']
                summary_points.append(f"对话时间从 {start_time} 到 {end_time}")
            
            return "对话摘要: " + "; ".join(summary_points)
            
        except Exception as e:
            self.logger.error(f"Failed to generate context summary: {e}")
            return "对话摘要生成失败"
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """提取关键词（简化版本）"""
        try:
            # 简单的关键词提取
            import re
            
            # 移除标点符号，转换为小写
            words = re.findall(r'\b\w+\b', text.lower())
            
            # 过滤停用词
            stop_words = {
                '的', '了', '是', '我', '你', '他', '她', '它', '们',
                '在', '有', '和', '对', '但', '从', '这', '那', '个',
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
                'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about'
            }
            
            filtered_words = [w for w in words if w not in stop_words and len(w) > 1]
            
            # 统计词频
            word_count = {}
            for word in filtered_words:
                word_count[word] = word_count.get(word, 0) + 1
            
            # 按词频排序
            sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
            
            return [word for word, count in sorted_words[:max_keywords]]
            
        except Exception as e:
            self.logger.error(f"Failed to extract keywords: {e}")
            return []
    
    def _update_memory_weights(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """更新记忆权重"""
        try:
            messages = context['messages']
            current_time = datetime.utcnow()
            
            for msg in messages:
                try:
                    msg_time = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                    time_diff = (current_time - msg_time).total_seconds() / 3600  # 小时差
                    
                    # 时间衰减
                    time_weight = self.memory_decay_factor ** time_diff
                    
                    # 消息重要性（可以根据内容长度、关键词等调整）
                    content_weight = min(len(msg['content']) / 100, 2.0)
                    
                    # 角色权重（用户消息可能更重要）
                    role_weight = 1.2 if msg['role'] == 'user' else 1.0
                    
                    # 综合权重
                    msg['weight'] = time_weight * content_weight * role_weight
                    
                except (ValueError, TypeError, KeyError):
                    msg['weight'] = 1.0
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to update memory weights: {e}")
            return context
    
    async def _analyze_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析上下文"""
        try:
            messages = context['messages']
            if not messages:
                return context
            
            # 提取主题
            all_content = " ".join([msg['content'] for msg in messages])
            topics = self._extract_keywords(all_content, max_keywords=5)
            context['topics'] = topics
            
            # 简单的情感分析
            sentiment = self._analyze_sentiment(all_content)
            context['sentiment'] = sentiment
            
            # 实体提取（简化版本）
            entities = self._extract_entities(all_content)
            context['entities'] = entities
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to analyze context: {e}")
            return context
    
    def _analyze_sentiment(self, text: str) -> str:
        """简单的情感分析"""
        try:
            positive_words = ['好', '棒', '优秀', '满意', '喜欢', '开心', '高兴', 'good', 'great', 'excellent', 'happy']
            negative_words = ['坏', '差', '糟糕', '不满', '讨厌', '生气', '难过', 'bad', 'terrible', 'angry', 'sad']
            
            text_lower = text.lower()
            
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            
            if positive_count > negative_count:
                return 'positive'
            elif negative_count > positive_count:
                return 'negative'
            else:
                return 'neutral'
                
        except Exception:
            return 'neutral'
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """简单的实体提取"""
        try:
            import re
            
            entities = {
                'emails': re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text),
                'phones': re.findall(r'\b\d{3}-?\d{3,4}-?\d{4}\b', text),
                'urls': re.findall(r'https?://[^\s]+', text),
                'numbers': re.findall(r'\b\d+\b', text)
            }
            
            # 过滤空值
            return {k: v for k, v in entities.items() if v}
            
        except Exception as e:
            self.logger.error(f"Failed to extract entities: {e}")
            return {}
    
    async def _cache_context(self, conversation_id: str, context: Dict[str, Any]):
        """缓存上下文"""
        try:
            cache_key = f"{self.cache_prefix}{conversation_id}"
            context_json = json.dumps(context, ensure_ascii=False)
            
            await redis_client.setex(cache_key, self.cache_ttl, context_json)
            
        except Exception as e:
            self.logger.error(f"Failed to cache context: {e}")
    
    def _is_context_valid(self, context: Dict[str, Any]) -> bool:
        """检查缓存的上下文是否有效"""
        try:
            last_updated = context.get('last_updated')
            if not last_updated:
                return False
            
            update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            now = datetime.utcnow()
            
            # 检查是否在缓存期内
            return (now - update_time).total_seconds() < self.cache_ttl
            
        except Exception:
            return False
    
    async def clear_context_cache(self, conversation_id: str):
        """清除上下文缓存"""
        try:
            cache_key = f"{self.cache_prefix}{conversation_id}"
            await redis_client.delete(cache_key)
            
        except Exception as e:
            self.logger.error(f"Failed to clear context cache: {e}")
    
    async def get_context_statistics(self) -> Dict[str, Any]:
        """获取上下文统计信息"""
        try:
            # 获取缓存中的上下文数量
            pattern = f"{self.cache_prefix}*"
            cached_contexts = await redis_client.keys(pattern)
            
            return {
                'cached_contexts': len(cached_contexts),
                'cache_ttl': self.cache_ttl,
                'max_context_messages': self.max_context_messages,
                'summary_threshold': self.context_summary_threshold
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get context statistics: {e}")
            return {}


# 全局上下文管理器实例
context_manager = ContextManager()