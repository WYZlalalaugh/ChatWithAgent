"""
对话管理器
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json

from sqlalchemy import select, and_, or_, desc, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db_session
from app.models.database import Conversation, Message, Bot, User
from llm_service.client import LLMServiceManager


class ConversationManager:
    """对话管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_manager = LLMServiceManager()
    
    async def create_conversation(
        self,
        user_id: str,
        bot_id: str,
        platform_type: str,
        platform_user_id: str,
        title: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """创建对话"""
        try:
            async with get_db_session() as session:
                conversation = Conversation(
                    title=title or f"新对话 - {datetime.now().strftime('%m-%d %H:%M')}",
                    bot_id=bot_id,
                    user_id=user_id,
                    platform_type=platform_type,
                    platform_user_id=platform_user_id,
                    context=context or {},
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                session.add(conversation)
                await session.commit()
                await session.refresh(conversation)
                
                self.logger.info(f"Created conversation {conversation.id}")
                return conversation
                
        except Exception as e:
            self.logger.error(f"Failed to create conversation: {e}")
            raise
    
    async def get_conversation_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """根据ID获取对话"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Conversation)
                    .options(selectinload(Conversation.bot))
                    .where(Conversation.id == conversation_id)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Failed to get conversation {conversation_id}: {e}")
            return None
    
    async def get_conversations(
        self,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 20,
        order_by: List[str] = None
    ) -> Tuple[List[Conversation], int]:
        """获取对话列表"""
        try:
            async with get_db_session() as session:
                # 构建查询
                query = select(Conversation).options(selectinload(Conversation.bot))
                count_query = select(func.count(Conversation.id))
                
                # 应用过滤条件
                if filters:
                    conditions = []
                    
                    if filters.get('user_id'):
                        conditions.append(Conversation.user_id == filters['user_id'])
                    
                    if filters.get('bot_id'):
                        conditions.append(Conversation.bot_id == filters['bot_id'])
                    
                    if filters.get('platform_type'):
                        conditions.append(Conversation.platform_type == filters['platform_type'])
                    
                    if filters.get('is_active') is not None:
                        conditions.append(Conversation.is_active == filters['is_active'])
                    
                    if filters.get('search'):
                        search_term = f"%{filters['search']}%"
                        conditions.append(Conversation.title.ilike(search_term))
                    
                    if conditions:
                        condition = and_(*conditions)
                        query = query.where(condition)
                        count_query = count_query.where(condition)
                
                # 应用排序
                if order_by:
                    for order in order_by:
                        if order.startswith('-'):
                            field = order[1:]
                            query = query.order_by(desc(getattr(Conversation, field)))
                        else:
                            query = query.order_by(getattr(Conversation, order))
                else:
                    query = query.order_by(desc(Conversation.updated_at))
                
                # 应用分页
                query = query.offset(offset).limit(limit)
                
                # 执行查询
                result = await session.execute(query)
                conversations = result.scalars().all()
                
                count_result = await session.execute(count_query)
                total = count_result.scalar()
                
                return list(conversations), total
                
        except Exception as e:
            self.logger.error(f"Failed to get conversations: {e}")
            return [], 0
    
    async def update_conversation(
        self,
        conversation_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Conversation]:
        """更新对话"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Conversation).where(Conversation.id == conversation_id)
                )
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    return None
                
                # 更新字段
                for field, value in update_data.items():
                    if hasattr(conversation, field):
                        setattr(conversation, field, value)
                
                conversation.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(conversation)
                
                self.logger.info(f"Updated conversation {conversation_id}")
                return conversation
                
        except Exception as e:
            self.logger.error(f"Failed to update conversation {conversation_id}: {e}")
            return None
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        try:
            async with get_db_session() as session:
                # 先删除相关消息
                await session.execute(
                    update(Message)
                    .where(Message.conversation_id == conversation_id)
                    .values(deleted_at=datetime.utcnow())
                )
                
                # 删除对话
                result = await session.execute(
                    select(Conversation).where(Conversation.id == conversation_id)
                )
                conversation = result.scalar_one_or_none()
                
                if conversation:
                    await session.delete(conversation)
                    await session.commit()
                    
                    self.logger.info(f"Deleted conversation {conversation_id}")
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            return False
    
    async def clear_conversation_messages(self, conversation_id: str) -> bool:
        """清空对话消息"""
        try:
            async with get_db_session() as session:
                await session.execute(
                    update(Message)
                    .where(Message.conversation_id == conversation_id)
                    .values(deleted_at=datetime.utcnow())
                )
                
                # 重置对话上下文
                await session.execute(
                    update(Conversation)
                    .where(Conversation.id == conversation_id)
                    .values(
                        context={},
                        updated_at=datetime.utcnow()
                    )
                )
                
                await session.commit()
                
                self.logger.info(f"Cleared messages for conversation {conversation_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to clear conversation messages {conversation_id}: {e}")
            return False
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False
    ) -> Tuple[List[Message], int]:
        """获取对话消息"""
        try:
            async with get_db_session() as session:
                # 构建查询
                query = select(Message).where(Message.conversation_id == conversation_id)
                count_query = select(func.count(Message.id)).where(
                    Message.conversation_id == conversation_id
                )
                
                # 是否包含已删除消息
                if not include_deleted:
                    query = query.where(Message.deleted_at.is_(None))
                    count_query = count_query.where(Message.deleted_at.is_(None))
                
                # 应用排序和分页
                query = query.order_by(Message.created_at).offset(offset).limit(limit)
                
                # 执行查询
                result = await session.execute(query)
                messages = result.scalars().all()
                
                count_result = await session.execute(count_query)
                total = count_result.scalar()
                
                return list(messages), total
                
        except Exception as e:
            self.logger.error(f"Failed to get conversation messages {conversation_id}: {e}")
            return [], 0
    
    async def get_conversation_statistics(self, conversation_id: str) -> Dict[str, Any]:
        """获取对话统计信息"""
        try:
            async with get_db_session() as session:
                # 获取消息统计
                message_stats = await session.execute(
                    select(
                        func.count(Message.id).label('total_messages'),
                        func.count(Message.id).filter(Message.sender_type == 'user').label('user_messages'),
                        func.count(Message.id).filter(Message.sender_type == 'bot').label('bot_messages'),
                        func.min(Message.created_at).label('first_message_time'),
                        func.max(Message.created_at).label('last_message_time')
                    )
                    .where(
                        and_(
                            Message.conversation_id == conversation_id,
                            Message.deleted_at.is_(None)
                        )
                    )
                )
                
                stats = message_stats.first()
                
                # 计算平均响应时间
                avg_response_time = await self._calculate_avg_response_time(conversation_id)
                
                # 获取消息类型分布
                message_types = await session.execute(
                    select(
                        Message.message_type,
                        func.count(Message.id).label('count')
                    )
                    .where(
                        and_(
                            Message.conversation_id == conversation_id,
                            Message.deleted_at.is_(None)
                        )
                    )
                    .group_by(Message.message_type)
                )
                
                type_distribution = {row.message_type: row.count for row in message_types}
                
                return {
                    'total_messages': stats.total_messages or 0,
                    'user_messages': stats.user_messages or 0,
                    'bot_messages': stats.bot_messages or 0,
                    'first_message_time': stats.first_message_time.isoformat() if stats.first_message_time else None,
                    'last_message_time': stats.last_message_time.isoformat() if stats.last_message_time else None,
                    'avg_response_time': avg_response_time,
                    'message_types': type_distribution
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get conversation statistics {conversation_id}: {e}")
            return {}
    
    async def generate_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """生成对话摘要"""
        try:
            # 获取对话消息
            messages, _ = await self.get_conversation_messages(conversation_id, limit=100)
            
            if not messages:
                return {'summary': '暂无对话内容', 'key_points': []}
            
            # 构建对话文本
            conversation_text = []
            for msg in messages[-50:]:  # 只取最近50条消息
                sender = "用户" if msg.sender_type == "user" else "机器人"
                conversation_text.append(f"{sender}: {msg.content}")
            
            text = "\n".join(conversation_text)
            
            # 使用LLM生成摘要
            llm_client = await self.llm_manager.get_client('openai')
            
            summary_prompt = f"""
请为以下对话生成一个简洁的摘要，并提取关键要点：

{text}

请返回JSON格式：
{{
    "summary": "对话摘要",
    "key_points": ["要点1", "要点2", "要点3"],
    "topics": ["主题1", "主题2"],
    "sentiment": "positive/neutral/negative"
}}
"""
            
            response = await llm_client.chat_completion(
                messages=[
                    {'role': 'system', 'content': '你是一个专业的对话分析助手，擅长总结对话内容和提取关键信息。'},
                    {'role': 'user', 'content': summary_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            try:
                summary_data = json.loads(response.get('content', '{}'))
            except json.JSONDecodeError:
                summary_data = {
                    'summary': response.get('content', '无法生成摘要'),
                    'key_points': [],
                    'topics': [],
                    'sentiment': 'neutral'
                }
            
            # 添加统计信息
            stats = await self.get_conversation_statistics(conversation_id)
            summary_data.update({
                'message_count': stats.get('total_messages', 0),
                'time_span': self._calculate_time_span(
                    stats.get('first_message_time'),
                    stats.get('last_message_time')
                ),
                'generated_at': datetime.utcnow().isoformat()
            })
            
            return summary_data
            
        except Exception as e:
            self.logger.error(f"Failed to generate conversation summary {conversation_id}: {e}")
            return {
                'summary': '摘要生成失败',
                'key_points': [],
                'error': str(e)
            }
    
    async def search_conversations(
        self,
        user_id: str,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索对话"""
        try:
            async with get_db_session() as session:
                # 搜索对话标题
                title_results = await session.execute(
                    select(Conversation)
                    .where(
                        and_(
                            Conversation.user_id == user_id,
                            Conversation.title.ilike(f"%{query}%"),
                            Conversation.is_active == True
                        )
                    )
                    .order_by(desc(Conversation.updated_at))
                    .limit(limit)
                )
                
                conversations = []
                for conv in title_results.scalars():
                    conversations.append({
                        'id': conv.id,
                        'title': conv.title,
                        'match_type': 'title',
                        'updated_at': conv.updated_at.isoformat()
                    })
                
                # 搜索消息内容
                if len(conversations) < limit:
                    content_results = await session.execute(
                        select(Message.conversation_id, func.max(Message.created_at))
                        .join(Conversation)
                        .where(
                            and_(
                                Conversation.user_id == user_id,
                                Message.content.ilike(f"%{query}%"),
                                Message.deleted_at.is_(None),
                                Conversation.is_active == True
                            )
                        )
                        .group_by(Message.conversation_id)
                        .order_by(desc(func.max(Message.created_at)))
                        .limit(limit - len(conversations))
                    )
                    
                    for conv_id, last_msg_time in content_results:
                        conv = await self.get_conversation_by_id(conv_id)
                        if conv and conv.id not in [c['id'] for c in conversations]:
                            conversations.append({
                                'id': conv.id,
                                'title': conv.title,
                                'match_type': 'content',
                                'updated_at': conv.updated_at.isoformat()
                            })
                
                return conversations
                
        except Exception as e:
            self.logger.error(f"Failed to search conversations: {e}")
            return []
    
    async def _calculate_avg_response_time(self, conversation_id: str) -> float:
        """计算平均响应时间"""
        try:
            async with get_db_session() as session:
                messages = await session.execute(
                    select(Message)
                    .where(
                        and_(
                            Message.conversation_id == conversation_id,
                            Message.deleted_at.is_(None)
                        )
                    )
                    .order_by(Message.created_at)
                )
                
                message_list = list(messages.scalars())
                response_times = []
                
                for i in range(len(message_list) - 1):
                    current_msg = message_list[i]
                    next_msg = message_list[i + 1]
                    
                    # 用户消息后跟机器人回复
                    if (current_msg.sender_type == 'user' and 
                        next_msg.sender_type == 'bot'):
                        time_diff = (next_msg.created_at - current_msg.created_at).total_seconds()
                        response_times.append(time_diff)
                
                return sum(response_times) / len(response_times) if response_times else 0.0
                
        except Exception as e:
            self.logger.error(f"Failed to calculate avg response time: {e}")
            return 0.0
    
    def _calculate_time_span(self, start_time: str, end_time: str) -> str:
        """计算时间跨度"""
        try:
            if not start_time or not end_time:
                return ''
            
            start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            delta = end - start
            
            if delta.days > 0:
                return f"{delta.days}天"
            elif delta.seconds > 3600:
                hours = delta.seconds // 3600
                return f"{hours}小时"
            elif delta.seconds > 60:
                minutes = delta.seconds // 60
                return f"{minutes}分钟"
            else:
                return f"{delta.seconds}秒"
                
        except Exception:
            return ''


# 全局对话管理器实例
conversation_manager = ConversationManager()