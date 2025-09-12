"""
对话引擎
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime, timedelta
import json
import uuid

from llm_service.client import LLMServiceManager
from knowledge.retriever import KnowledgeRetriever
from agents.react_agent import ReactAgent
from managers.conversation_manager import conversation_manager
from managers.message_manager import message_manager
from security.content_filter import ContentFilter
from app.config import settings


class ConversationEngine:
    """对话引擎"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_manager = LLMServiceManager()
        self.knowledge_retriever = KnowledgeRetriever()
        self.content_filter = ContentFilter()
        
        # 对话上下文缓存
        self.context_cache: Dict[str, Dict[str, Any]] = {}
        
        # 对话配置
        self.max_context_length = settings.conversation.max_context_length
        self.context_window_size = settings.conversation.context_window_size
        self.enable_memory_compression = settings.conversation.enable_memory_compression
    
    async def process_message(
        self,
        conversation_id: str,
        user_message: str,
        bot_config: Dict[str, Any],
        stream: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理用户消息并生成回复"""
        try:
            # 获取对话上下文
            context = await self._get_conversation_context(conversation_id)
            
            # 内容过滤
            filtered_message = await self.content_filter.filter_content(user_message)
            
            # 添加用户消息到上下文
            context['messages'].append({
                'role': 'user',
                'content': filtered_message,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # 管理上下文长度
            context = await self._manage_context_length(context)
            
            # 知识库检索（如果启用）
            knowledge_context = ""
            if bot_config.get('enable_knowledge', False):
                knowledge_context = await self._retrieve_knowledge(
                    query=filtered_message,
                    knowledge_base_ids=bot_config.get('knowledge_base_ids', [])
                )
            
            # 构建系统提示词
            system_prompt = await self._build_system_prompt(
                bot_config=bot_config,
                knowledge_context=knowledge_context,
                conversation_context=context
            )
            
            # 准备消息历史
            messages = [
                {'role': 'system', 'content': system_prompt}
            ] + context['messages'][-self.context_window_size:]
            
            # 获取LLM客户端
            llm_client = await self.llm_manager.get_client(
                provider=bot_config.get('llm_provider', 'openai'),
                config=bot_config.get('llm_config', {})
            )
            
            # 生成回复
            if stream:
                async for chunk in self._generate_stream_response(
                    llm_client, messages, bot_config
                ):
                    yield chunk
            else:
                response = await self._generate_response(
                    llm_client, messages, bot_config
                )
                yield response
            
        except Exception as e:
            self.logger.error(f"Failed to process message: {e}")
            yield {
                'type': 'error',
                'content': '抱歉，处理您的消息时发生了错误，请稍后重试。'
            }
    
    async def _get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """获取对话上下文"""
        try:
            # 从缓存中获取
            if conversation_id in self.context_cache:
                return self.context_cache[conversation_id]
            
            # 从数据库加载
            conversation = await conversation_manager.get_conversation_by_id(conversation_id)
            if not conversation:
                # 创建新的上下文
                context = {
                    'conversation_id': conversation_id,
                    'messages': [],
                    'metadata': {},
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
            else:
                # 加载最近的消息
                messages, _ = await message_manager.get_messages(
                    filters={'conversation_id': conversation_id},
                    limit=self.context_window_size * 2,
                    order_by=['created_at']
                )
                
                context = {
                    'conversation_id': conversation_id,
                    'messages': [
                        {
                            'role': 'user' if msg.sender_type == 'user' else 'assistant',
                            'content': msg.content,
                            'timestamp': msg.created_at.isoformat()
                        }
                        for msg in messages
                    ],
                    'metadata': conversation.context,
                    'created_at': conversation.created_at.isoformat(),
                    'updated_at': conversation.updated_at.isoformat()
                }
            
            # 缓存上下文
            self.context_cache[conversation_id] = context
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation context: {e}")
            return {
                'conversation_id': conversation_id,
                'messages': [],
                'metadata': {},
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
    
    async def _manage_context_length(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """管理上下文长度"""
        try:
            messages = context['messages']
            
            if len(messages) <= self.max_context_length:
                return context
            
            if self.enable_memory_compression:
                # 压缩早期对话
                compressed_messages = await self._compress_early_messages(
                    messages[:-self.context_window_size]
                )
                context['messages'] = compressed_messages + messages[-self.context_window_size:]
            else:
                # 简单截断
                context['messages'] = messages[-self.max_context_length:]
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to manage context length: {e}")
            return context
    
    async def _compress_early_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """压缩早期消息"""
        try:
            if not messages:
                return []
            
            # 构建对话文本
            conversation_text = []
            for msg in messages:
                role = "用户" if msg['role'] == 'user' else "助手"
                conversation_text.append(f"{role}: {msg['content']}")
            
            text = "\n".join(conversation_text)
            
            # 使用LLM生成摘要
            llm_client = await self.llm_manager.get_client('openai')
            
            summary_prompt = f"""
请将以下对话内容压缩成简洁的摘要，保留关键信息和上下文：

{text}

要求：
1. 保持对话的核心内容和关键信息
2. 用第三人称描述
3. 控制在200字以内
"""
            
            response = await llm_client.chat_completion(
                messages=[
                    {'role': 'system', 'content': '你是一个专业的对话摘要助手。'},
                    {'role': 'user', 'content': summary_prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            summary = response.get('content', '对话摘要生成失败')
            
            return [{
                'role': 'system',
                'content': f"对话历史摘要：{summary}",
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'summary'
            }]
            
        except Exception as e:
            self.logger.error(f"Failed to compress early messages: {e}")
            return []
    
    async def _retrieve_knowledge(
        self,
        query: str,
        knowledge_base_ids: List[str]
    ) -> str:
        """检索知识库"""
        try:
            if not knowledge_base_ids:
                return ""
            
            # 从知识库检索相关信息
            results = await self.knowledge_retriever.search(
                query=query,
                knowledge_base_ids=knowledge_base_ids,
                top_k=5,
                score_threshold=0.7
            )
            
            if not results:
                return ""
            
            # 构建知识上下文
            knowledge_pieces = []
            for result in results:
                knowledge_pieces.append(f"- {result.content}")
            
            return "相关知识：\n" + "\n".join(knowledge_pieces)
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve knowledge: {e}")
            return ""
    
    async def _build_system_prompt(
        self,
        bot_config: Dict[str, Any],
        knowledge_context: str,
        conversation_context: Dict[str, Any]
    ) -> str:
        """构建系统提示词"""
        try:
            base_prompt = bot_config.get('system_prompt', '你是一个有用的AI助手。')
            
            # 添加知识上下文
            if knowledge_context:
                base_prompt += f"\n\n{knowledge_context}"
            
            # 添加对话上下文信息
            if conversation_context.get('metadata'):
                metadata = conversation_context['metadata']
                if metadata.get('user_preferences'):
                    base_prompt += f"\n\n用户偏好：{metadata['user_preferences']}"
                
                if metadata.get('conversation_topic'):
                    base_prompt += f"\n\n当前话题：{metadata['conversation_topic']}"
            
            # 添加时间信息
            current_time = datetime.now().strftime('%Y年%m月%d日 %H:%M')
            base_prompt += f"\n\n当前时间：{current_time}"
            
            return base_prompt
            
        except Exception as e:
            self.logger.error(f"Failed to build system prompt: {e}")
            return bot_config.get('system_prompt', '你是一个有用的AI助手。')
    
    async def _generate_response(
        self,
        llm_client: Any,
        messages: List[Dict[str, Any]],
        bot_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成回复"""
        try:
            response = await llm_client.chat_completion(
                messages=messages,
                temperature=bot_config.get('temperature', 0.7),
                max_tokens=bot_config.get('max_tokens', 2000),
                top_p=bot_config.get('top_p', 1.0),
                frequency_penalty=bot_config.get('frequency_penalty', 0.0),
                presence_penalty=bot_config.get('presence_penalty', 0.0)
            )
            
            content = response.get('content', '')
            
            # 内容后处理
            processed_content = await self._post_process_content(content, bot_config)
            
            return {
                'type': 'message',
                'content': processed_content,
                'metadata': {
                    'model': response.get('model'),
                    'usage': response.get('usage', {}),
                    'finish_reason': response.get('finish_reason')
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate response: {e}")
            return {
                'type': 'error',
                'content': '生成回复时发生错误，请稍后重试。'
            }
    
    async def _generate_stream_response(
        self,
        llm_client: Any,
        messages: List[Dict[str, Any]],
        bot_config: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """生成流式回复"""
        try:
            content_buffer = ""
            
            async for chunk in llm_client.chat_completion_stream(
                messages=messages,
                temperature=bot_config.get('temperature', 0.7),
                max_tokens=bot_config.get('max_tokens', 2000),
                top_p=bot_config.get('top_p', 1.0),
                frequency_penalty=bot_config.get('frequency_penalty', 0.0),
                presence_penalty=bot_config.get('presence_penalty', 0.0)
            ):
                if chunk.get('type') == 'content':
                    delta = chunk.get('content', '')
                    content_buffer += delta
                    
                    yield {
                        'type': 'stream',
                        'content': delta,
                        'is_complete': False
                    }
                
                elif chunk.get('type') == 'done':
                    # 最终处理内容
                    processed_content = await self._post_process_content(
                        content_buffer, bot_config
                    )
                    
                    yield {
                        'type': 'stream',
                        'content': '',
                        'is_complete': True,
                        'final_content': processed_content,
                        'metadata': chunk.get('metadata', {})
                    }
                    break
            
        except Exception as e:
            self.logger.error(f"Failed to generate stream response: {e}")
            yield {
                'type': 'error',
                'content': '生成流式回复时发生错误。'
            }
    
    async def _post_process_content(self, content: str, bot_config: Dict[str, Any]) -> str:
        """内容后处理"""
        try:
            # 内容过滤
            filtered_content = await self.content_filter.filter_content(content)
            
            # 格式化处理
            if bot_config.get('enable_markdown', True):
                # 保持Markdown格式
                pass
            
            # 长度限制
            max_length = bot_config.get('max_response_length', 4000)
            if len(filtered_content) > max_length:
                filtered_content = filtered_content[:max_length] + "..."
            
            return filtered_content
            
        except Exception as e:
            self.logger.error(f"Failed to post process content: {e}")
            return content
    
    async def save_response(
        self,
        conversation_id: str,
        response_content: str,
        metadata: Dict[str, Any]
    ):
        """保存机器人回复"""
        try:
            # 保存到数据库
            await message_manager.create_message(
                conversation_id=conversation_id,
                content=response_content,
                message_type='text',
                sender_type='bot',
                sender_id='system',
                metadata=metadata
            )
            
            # 更新缓存中的上下文
            if conversation_id in self.context_cache:
                self.context_cache[conversation_id]['messages'].append({
                    'role': 'assistant',
                    'content': response_content,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                self.context_cache[conversation_id]['updated_at'] = datetime.utcnow().isoformat()
            
        except Exception as e:
            self.logger.error(f"Failed to save response: {e}")
    
    async def clear_conversation_context(self, conversation_id: str):
        """清除对话上下文"""
        try:
            # 从缓存中移除
            if conversation_id in self.context_cache:
                del self.context_cache[conversation_id]
            
            # 清除数据库中的上下文
            await conversation_manager.clear_conversation_messages(conversation_id)
            
        except Exception as e:
            self.logger.error(f"Failed to clear conversation context: {e}")
    
    async def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """获取对话摘要"""
        try:
            return await conversation_manager.generate_conversation_summary(conversation_id)
        except Exception as e:
            self.logger.error(f"Failed to get conversation summary: {e}")
            return {}
    
    async def update_conversation_metadata(
        self,
        conversation_id: str,
        metadata: Dict[str, Any]
    ):
        """更新对话元数据"""
        try:
            # 更新数据库
            await conversation_manager.update_conversation(
                conversation_id, {'context': metadata}
            )
            
            # 更新缓存
            if conversation_id in self.context_cache:
                self.context_cache[conversation_id]['metadata'].update(metadata)
            
        except Exception as e:
            self.logger.error(f"Failed to update conversation metadata: {e}")
    
    def get_engine_statistics(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        return {
            'cached_conversations': len(self.context_cache),
            'max_context_length': self.max_context_length,
            'context_window_size': self.context_window_size,
            'memory_compression_enabled': self.enable_memory_compression
        }


# 全局对话引擎实例
conversation_engine = ConversationEngine()