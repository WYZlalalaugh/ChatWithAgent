"""
消息管理器
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json

from sqlalchemy import select, and_, or_, desc, func, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.database import Message, Conversation, Bot
from managers.bot_manager import bot_manager
from security.content_filter import ContentFilter


class MessageManager:
    """消息管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.content_filter = ContentFilter()
    
    async def create_message(
        self,
        conversation_id: str,
        content: str,
        message_type: str,
        sender_type: str,
        sender_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """创建消息"""
        try:
            # 内容过滤
            filtered_content = await self.content_filter.filter_content(content)
            
            async with get_db_session() as session:
                message = Message(
                    conversation_id=conversation_id,
                    content=filtered_content,
                    message_type=message_type,
                    sender_type=sender_type,
                    sender_id=sender_id,
                    metadata=metadata or {},
                    created_at=datetime.utcnow()
                )
                
                session.add(message)
                await session.commit()
                await session.refresh(message)
                
                # 更新对话的最后活动时间
                await session.execute(
                    update(Conversation)
                    .where(Conversation.id == conversation_id)
                    .values(updated_at=datetime.utcnow())
                )
                await session.commit()
                
                self.logger.info(f"Created message {message.id}")
                return message
                
        except Exception as e:
            self.logger.error(f"Failed to create message: {e}")
            raise
    
    async def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """根据ID获取消息"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Message).where(Message.id == message_id)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Failed to get message {message_id}: {e}")
            return None
    
    async def get_messages(
        self,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 50,
        order_by: List[str] = None
    ) -> Tuple[List[Message], int]:
        """获取消息列表"""
        try:
            async with get_db_session() as session:
                # 构建查询
                query = select(Message)
                count_query = select(func.count(Message.id))
                
                # 应用过滤条件
                if filters:
                    conditions = []
                    
                    if filters.get('conversation_id'):
                        conditions.append(Message.conversation_id == filters['conversation_id'])
                    
                    if filters.get('conversation_id__in'):
                        conditions.append(Message.conversation_id.in_(filters['conversation_id__in']))
                    
                    if filters.get('sender_type'):
                        conditions.append(Message.sender_type == filters['sender_type'])
                    
                    if filters.get('message_type'):
                        conditions.append(Message.message_type == filters['message_type'])
                    
                    if filters.get('start_time'):
                        conditions.append(Message.created_at >= filters['start_time'])
                    
                    if filters.get('end_time'):
                        conditions.append(Message.created_at <= filters['end_time'])
                    
                    if filters.get('search'):
                        search_term = f"%{filters['search']}%"
                        conditions.append(Message.content.ilike(search_term))
                    
                    # 默认不包含已删除消息
                    conditions.append(Message.deleted_at.is_(None))
                    
                    if conditions:
                        condition = and_(*conditions)
                        query = query.where(condition)
                        count_query = count_query.where(condition)
                
                # 应用排序
                if order_by:
                    for order in order_by:
                        if order.startswith('-'):
                            field = order[1:]
                            query = query.order_by(desc(getattr(Message, field)))
                        else:
                            query = query.order_by(getattr(Message, order))
                else:
                    query = query.order_by(desc(Message.created_at))
                
                # 应用分页
                query = query.offset(offset).limit(limit)
                
                # 执行查询
                result = await session.execute(query)
                messages = result.scalars().all()
                
                count_result = await session.execute(count_query)
                total = count_result.scalar()
                
                return list(messages), total
                
        except Exception as e:
            self.logger.error(f"Failed to get messages: {e}")
            return [], 0
    
    async def update_message(
        self,
        message_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Message]:
        """更新消息"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Message).where(Message.id == message_id)
                )
                message = result.scalar_one_or_none()
                
                if not message:
                    return None
                
                # 更新字段
                for field, value in update_data.items():
                    if hasattr(message, field):
                        if field == 'content':
                            # 对内容进行过滤
                            value = await self.content_filter.filter_content(value)
                        setattr(message, field, value)
                
                await session.commit()
                await session.refresh(message)
                
                self.logger.info(f"Updated message {message_id}")
                return message
                
        except Exception as e:
            self.logger.error(f"Failed to update message {message_id}: {e}")
            return None
    
    async def delete_message(self, message_id: str) -> bool:
        """删除消息（软删除）"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    update(Message)
                    .where(Message.id == message_id)
                    .values(deleted_at=datetime.utcnow())
                )
                
                await session.commit()
                
                self.logger.info(f"Deleted message {message_id}")
                return result.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Failed to delete message {message_id}: {e}")
            return False
    
    async def send_message(
        self,
        conversation_id: str,
        content: str,
        message_type: str = 'text',
        sender_type: str = 'user',
        sender_id: str = '',
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """发送消息并触发机器人响应"""
        try:
            # 创建用户消息
            message = await self.create_message(
                conversation_id=conversation_id,
                content=content,
                message_type=message_type,
                sender_type=sender_type,
                sender_id=sender_id,
                metadata=metadata
            )
            
            # 异步触发机器人响应
            asyncio.create_task(self.trigger_bot_response(message.id))
            
            return message
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            raise
    
    async def trigger_bot_response(self, message_id: str):
        """触发机器人响应"""
        try:
            message = await self.get_message_by_id(message_id)
            if not message:
                return
            
            # 获取对话信息
            async with get_db_session() as session:
                result = await session.execute(
                    select(Conversation).where(Conversation.id == message.conversation_id)
                )
                conversation = result.scalar_one_or_none()
                
                if not conversation:
                    return
                
                # 检查机器人是否在运行
                if conversation.bot_id not in await bot_manager.get_running_bots():
                    self.logger.warning(f"Bot {conversation.bot_id} is not running")
                    return
                
                # 构建消息数据
                message_data = {
                    'user_id': conversation.platform_user_id,
                    'content': message.content,
                    'type': message.message_type,
                    'metadata': message.metadata,
                    'conversation_id': conversation.id
                }
                
                # 触发机器人处理
                await bot_manager._handle_message(conversation.bot_id, message_data)
                
        except Exception as e:
            self.logger.error(f"Failed to trigger bot response: {e}")
    
    async def search_messages(
        self,
        search_filters: Dict[str, Any],
        offset: int = 0,
        limit: int = 50
    ) -> Tuple[List[Message], int]:
        """搜索消息"""
        try:
            async with get_db_session() as session:
                # 构建搜索查询
                query = select(Message)
                count_query = select(func.count(Message.id))
                
                conditions = [Message.deleted_at.is_(None)]
                
                # 用户权限过滤
                if search_filters.get('user_id'):
                    # 只搜索用户有权限的对话
                    query = query.join(Conversation)
                    count_query = count_query.join(Conversation)
                    conditions.append(Conversation.user_id == search_filters['user_id'])
                
                # 搜索查询
                if search_filters.get('query'):
                    search_term = f"%{search_filters['query']}%"
                    conditions.append(Message.content.ilike(search_term))
                
                # 对话ID过滤
                if search_filters.get('conversation_ids'):
                    conditions.append(Message.conversation_id.in_(search_filters['conversation_ids']))
                
                # 消息类型过滤
                if search_filters.get('message_types'):
                    conditions.append(Message.message_type.in_(search_filters['message_types']))
                
                # 时间范围过滤
                if search_filters.get('start_date'):
                    conditions.append(Message.created_at >= search_filters['start_date'])
                
                if search_filters.get('end_date'):
                    conditions.append(Message.created_at <= search_filters['end_date'])
                
                # 应用条件
                if conditions:
                    condition = and_(*conditions)
                    query = query.where(condition)
                    count_query = count_query.where(condition)
                
                # 排序和分页
                query = query.order_by(desc(Message.created_at)).offset(offset).limit(limit)
                
                # 执行查询
                result = await session.execute(query)
                messages = result.scalars().all()
                
                count_result = await session.execute(count_query)
                total = count_result.scalar()
                
                return list(messages), total
                
        except Exception as e:
            self.logger.error(f"Failed to search messages: {e}")
            return [], 0
    
    async def get_conversation_statistics(self, conversation_id: str) -> Dict[str, Any]:
        """获取对话消息统计"""
        try:
            async with get_db_session() as session:
                # 基础统计
                stats_result = await session.execute(
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
                
                stats = stats_result.first()
                
                # 消息类型分布
                type_result = await session.execute(
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
                
                message_types = {row.message_type: row.count for row in type_result}
                
                # 计算平均响应时间
                avg_response_time = await self._calculate_avg_response_time(conversation_id)
                
                return {
                    'conversation_id': conversation_id,
                    'total_messages': stats.total_messages or 0,
                    'user_messages': stats.user_messages or 0,
                    'bot_messages': stats.bot_messages or 0,
                    'message_types': message_types,
                    'avg_response_time': avg_response_time,
                    'last_message_time': stats.last_message_time.isoformat() if stats.last_message_time else None,
                    'first_message_time': stats.first_message_time.isoformat() if stats.first_message_time else None
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get conversation statistics: {e}")
            return {}
    
    async def get_daily_message_stats(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取每日消息统计"""
        try:
            async with get_db_session() as session:
                query = select(
                    func.date(Message.created_at).label('date'),
                    func.count(Message.id).label('total_messages'),
                    func.count(Message.id).filter(Message.sender_type == 'user').label('user_messages'),
                    func.count(Message.id).filter(Message.sender_type == 'bot').label('bot_messages')
                ).where(
                    and_(
                        Message.created_at >= start_date,
                        Message.created_at <= end_date,
                        Message.deleted_at.is_(None)
                    )
                )
                
                if user_id:
                    query = query.join(Conversation).where(Conversation.user_id == user_id)
                
                query = query.group_by(func.date(Message.created_at)).order_by(func.date(Message.created_at))
                
                result = await session.execute(query)
                
                stats = []
                for row in result:
                    stats.append({
                        'date': row.date.isoformat(),
                        'total_messages': row.total_messages,
                        'user_messages': row.user_messages,
                        'bot_messages': row.bot_messages
                    })
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get daily message stats: {e}")
            return []
    
    async def get_popular_messages(
        self,
        conversation_id: Optional[str] = None,
        message_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取热门消息（基于长度或复杂度）"""
        try:
            async with get_db_session() as session:
                query = select(
                    Message.id,
                    Message.content,
                    Message.message_type,
                    Message.created_at,
                    func.length(Message.content).label('content_length')
                ).where(Message.deleted_at.is_(None))
                
                if conversation_id:
                    query = query.where(Message.conversation_id == conversation_id)
                
                if message_type:
                    query = query.where(Message.message_type == message_type)
                
                query = query.order_by(desc(func.length(Message.content))).limit(limit)
                
                result = await session.execute(query)
                
                messages = []
                for row in result:
                    messages.append({
                        'id': row.id,
                        'content': row.content[:200] + '...' if len(row.content) > 200 else row.content,
                        'message_type': row.message_type,
                        'created_at': row.created_at.isoformat(),
                        'content_length': row.content_length
                    })
                
                return messages
                
        except Exception as e:
            self.logger.error(f"Failed to get popular messages: {e}")
            return []
    
    async def _calculate_avg_response_time(self, conversation_id: str) -> float:
        """计算平均响应时间"""
        try:
            async with get_db_session() as session:
                # 获取对话中的所有消息，按时间排序
                result = await session.execute(
                    select(Message)
                    .where(
                        and_(
                            Message.conversation_id == conversation_id,
                            Message.deleted_at.is_(None)
                        )
                    )
                    .order_by(Message.created_at)
                )
                
                messages = list(result.scalars())
                response_times = []
                
                for i in range(len(messages) - 1):
                    current_msg = messages[i]
                    next_msg = messages[i + 1]
                    
                    # 用户消息后跟机器人回复
                    if (current_msg.sender_type == 'user' and 
                        next_msg.sender_type == 'bot'):
                        time_diff = (next_msg.created_at - current_msg.created_at).total_seconds()
                        response_times.append(time_diff)
                
                return sum(response_times) / len(response_times) if response_times else 0.0
                
        except Exception as e:
            self.logger.error(f"Failed to calculate avg response time: {e}")
            return 0.0
    
    async def export_messages(
        self,
        conversation_id: str,
        format_type: str = 'json'
    ) -> Dict[str, Any]:
        """导出消息"""
        try:
            messages, _ = await self.get_messages(
                filters={'conversation_id': conversation_id},
                limit=10000  # 大量导出
            )
            
            if format_type == 'json':
                return {
                    'conversation_id': conversation_id,
                    'export_time': datetime.utcnow().isoformat(),
                    'messages': [
                        {
                            'id': msg.id,
                            'content': msg.content,
                            'message_type': msg.message_type,
                            'sender_type': msg.sender_type,
                            'sender_id': msg.sender_id,
                            'metadata': msg.metadata,
                            'created_at': msg.created_at.isoformat()
                        }
                        for msg in messages
                    ]
                }
            elif format_type == 'text':
                lines = []
                for msg in messages:
                    sender = "用户" if msg.sender_type == "user" else "机器人"
                    timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    lines.append(f"[{timestamp}] {sender}: {msg.content}")
                
                return {
                    'conversation_id': conversation_id,
                    'export_time': datetime.utcnow().isoformat(),
                    'content': '\n'.join(lines)
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to export messages: {e}")
            return {}


# 全局消息管理器实例
message_manager = MessageManager()