"""
机器人管理器
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db_session
from app.models.database import Bot, User, Conversation, Message
from adapters.base import BaseAdapter, get_adapter
from llm_service.client import LLMServiceManager
from security.encryption import encrypt_config, decrypt_config
from engines.conversation_engine import conversation_engine
from managers.conversation_manager import conversation_manager
from managers.message_manager import message_manager
from app.config import settings


class BotManager:
    """机器人管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.running_bots: Dict[str, Dict[str, Any]] = {}
        self.llm_manager = LLMServiceManager()
        
    async def create_bot(
        self,
        user_id: str,
        name: str,
        platform_type: str,
        platform_config: Dict[str, Any],
        llm_config: Dict[str, Any],
        description: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> Bot:
        """创建机器人"""
        try:
            async with get_db_session() as session:
                # 验证平台配置
                if not await self._validate_platform_config(platform_type, platform_config):
                    raise ValueError("Invalid platform configuration")
                
                # 验证LLM配置
                if not await self._validate_llm_config(llm_config):
                    raise ValueError("Invalid LLM configuration")
                
                # 加密敏感配置
                encrypted_platform_config = encrypt_config(platform_config)
                encrypted_llm_config = encrypt_config(llm_config)
                
                # 创建机器人记录
                bot = Bot(
                    name=name,
                    description=description,
                    avatar_url=avatar_url,
                    user_id=user_id,
                    platform_type=platform_type,
                    platform_config=encrypted_platform_config,
                    llm_config=encrypted_llm_config,
                    is_active=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                session.add(bot)
                await session.commit()
                await session.refresh(bot)
                
                self.logger.info(f"Created bot {bot.id} for user {user_id}")
                return bot
                
        except Exception as e:
            self.logger.error(f"Failed to create bot: {e}")
            raise
    
    async def get_bot_by_id(self, bot_id: str) -> Optional[Bot]:
        """根据ID获取机器人"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Bot).where(Bot.id == bot_id)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Failed to get bot {bot_id}: {e}")
            return None
    
    async def get_bot(self, bot_id: str) -> Optional[Bot]:
        """获取机器人（便捷方法）"""
        return await self.get_bot_by_id(bot_id)
    
    async def get_bots(
        self,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 20,
        order_by: List[str] = None
    ) -> Tuple[List[Bot], int]:
        """获取机器人列表"""
        try:
            async with get_db_session() as session:
                # 构建查询
                query = select(Bot)
                count_query = select(func.count(Bot.id))
                
                # 应用过滤条件
                if filters:
                    conditions = []
                    
                    if filters.get('user_id'):
                        conditions.append(Bot.user_id == filters['user_id'])
                    
                    if filters.get('platform_type'):
                        conditions.append(Bot.platform_type == filters['platform_type'])
                    
                    if filters.get('is_active') is not None:
                        conditions.append(Bot.is_active == filters['is_active'])
                    
                    if filters.get('search'):
                        search_term = f"%{filters['search']}%"
                        conditions.append(
                            or_(
                                Bot.name.ilike(search_term),
                                Bot.description.ilike(search_term)
                            )
                        )
                    
                    if conditions:
                        condition = and_(*conditions)
                        query = query.where(condition)
                        count_query = count_query.where(condition)
                
                # 应用排序
                if order_by:
                    for order in order_by:
                        if order.startswith('-'):
                            field = order[1:]
                            query = query.order_by(desc(getattr(Bot, field)))
                        else:
                            query = query.order_by(getattr(Bot, order))
                else:
                    query = query.order_by(desc(Bot.created_at))
                
                # 应用分页
                query = query.offset(offset).limit(limit)
                
                # 执行查询
                result = await session.execute(query)
                bots = result.scalars().all()
                
                count_result = await session.execute(count_query)
                total = count_result.scalar()
                
                return list(bots), total
                
        except Exception as e:
            self.logger.error(f"Failed to get bots: {e}")
            return [], 0
    
    async def update_bot(self, bot_id: str, update_data: Dict[str, Any]) -> Optional[Bot]:
        """更新机器人"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(Bot).where(Bot.id == bot_id)
                )
                bot = result.scalar_one_or_none()
                
                if not bot:
                    return None
                
                # 更新字段
                for field, value in update_data.items():
                    if hasattr(bot, field):
                        if field == 'platform_config' and value:
                            # 验证并加密平台配置
                            if await self._validate_platform_config(bot.platform_type, value):
                                setattr(bot, field, encrypt_config(value))
                        elif field == 'llm_config' and value:
                            # 验证并加密LLM配置
                            if await self._validate_llm_config(value):
                                setattr(bot, field, encrypt_config(value))
                        else:
                            setattr(bot, field, value)
                
                bot.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(bot)
                
                self.logger.info(f"Updated bot {bot_id}")
                return bot
                
        except Exception as e:
            self.logger.error(f"Failed to update bot {bot_id}: {e}")
            return None
    
    async def delete_bot(self, bot_id: str) -> bool:
        """删除机器人"""
        try:
            # 先停止机器人
            await self.stop_bot(bot_id)
            
            async with get_db_session() as session:
                result = await session.execute(
                    select(Bot).where(Bot.id == bot_id)
                )
                bot = result.scalar_one_or_none()
                
                if not bot:
                    return False
                
                # 删除相关数据（对话、消息等）
                await self._cleanup_bot_data(session, bot_id)
                
                # 删除机器人记录
                await session.delete(bot)
                await session.commit()
                
                self.logger.info(f"Deleted bot {bot_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to delete bot {bot_id}: {e}")
            return False
    
    async def start_bot(self, bot_id: str) -> bool:
        """启动机器人"""
        try:
            bot = await self.get_bot_by_id(bot_id)
            if not bot:
                raise ValueError(f"Bot {bot_id} not found")
            
            if bot_id in self.running_bots:
                self.logger.warning(f"Bot {bot_id} is already running")
                return True
            
            # 解密配置
            platform_config = decrypt_config(bot.platform_config)
            llm_config = decrypt_config(bot.llm_config)
            
            # 创建平台适配器
            adapter = get_adapter(bot.platform_type)
            if not adapter:
                raise ValueError(f"Unsupported platform: {bot.platform_type}")
            
            # 初始化适配器
            await adapter.initialize(platform_config)
            
            # 创建LLM客户端
            llm_client = await self.llm_manager.get_client(
                provider=llm_config.get('provider', 'openai'),
                config=llm_config
            )
            
            # 注册机器人
            self.running_bots[bot_id] = {
                'bot': bot,
                'adapter': adapter,
                'llm_client': llm_client,
                'start_time': datetime.utcnow(),
                'message_count': 0,
                'error_count': 0,
                'last_activity': datetime.utcnow()
            }
            
            # 设置消息处理器
            await adapter.set_message_handler(
                lambda msg: self._handle_message(bot_id, msg)
            )
            
            # 启动适配器
            await adapter.start()
            
            # 更新数据库状态
            await self.update_bot(bot_id, {'is_active': True})
            
            self.logger.info(f"Started bot {bot_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start bot {bot_id}: {e}")
            # 清理失败的启动
            if bot_id in self.running_bots:
                del self.running_bots[bot_id]
            return False
    
    async def stop_bot(self, bot_id: str) -> bool:
        """停止机器人"""
        try:
            if bot_id not in self.running_bots:
                self.logger.warning(f"Bot {bot_id} is not running")
                return True
            
            bot_info = self.running_bots[bot_id]
            adapter = bot_info['adapter']
            
            # 停止适配器
            await adapter.stop()
            
            # 移除运行记录
            del self.running_bots[bot_id]
            
            # 更新数据库状态
            await self.update_bot(bot_id, {'is_active': False})
            
            self.logger.info(f"Stopped bot {bot_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop bot {bot_id}: {e}")
            return False
    
    async def get_bot_status(self, bot_id: str) -> Dict[str, Any]:
        """获取机器人状态"""
        try:
            is_running = bot_id in self.running_bots
            
            status = {
                'bot_id': bot_id,
                'is_running': is_running,
                'is_online': False,
                'start_time': None,
                'message_count': 0,
                'error_count': 0,
                'last_activity': None
            }
            
            if is_running:
                bot_info = self.running_bots[bot_id]
                adapter = bot_info['adapter']
                
                status.update({
                    'is_online': await adapter.is_connected(),
                    'start_time': bot_info['start_time'].isoformat(),
                    'message_count': bot_info['message_count'],
                    'error_count': bot_info['error_count'],
                    'last_activity': bot_info['last_activity'].isoformat()
                })
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get bot status {bot_id}: {e}")
            return {'bot_id': bot_id, 'is_running': False, 'error': str(e)}
    
    async def restart_bot(self, bot_id: str) -> bool:
        """重启机器人"""
        try:
            await self.stop_bot(bot_id)
            await asyncio.sleep(1)  # 等待完全停止
            return await self.start_bot(bot_id)
        except Exception as e:
            self.logger.error(f"Failed to restart bot {bot_id}: {e}")
            return False
    
    async def get_running_bots(self) -> List[str]:
        """获取正在运行的机器人列表"""
        return list(self.running_bots.keys())
    
    async def _handle_message(self, bot_id: str, message: Dict[str, Any]):
        """处理接收到的消息"""
        try:
            if bot_id not in self.running_bots:
                return
            
            bot_info = self.running_bots[bot_id]
            bot = bot_info['bot']
            adapter = bot_info['adapter']
            
            # 更新统计信息
            bot_info['message_count'] += 1
            bot_info['last_activity'] = datetime.utcnow()
            
            # 获取或创建对话
            conversation = await self._get_or_create_conversation(
                bot_id=bot_id,
                platform_user_id=message.get('user_id'),
                platform_type=bot.platform_type
            )
            
            # 构建机器人配置
            llm_config = decrypt_config(bot.llm_config)
            bot_config = {
                'llm_config': llm_config,
                'system_prompt': bot.description or llm_config.get('system_prompt', ''),
                'knowledge_base_ids': getattr(bot, 'knowledge_base_ids', []),
                'plugins': getattr(bot, 'plugins', [])
            }
            
            # 使用对话引擎处理消息
            response_content = ""
            async for chunk in conversation_engine.process_message(
                conversation_id=conversation.id,
                user_message=message.get('content', ''),
                bot_config=bot_config,
                stream=False
            ):
                if chunk.get("type") == "content":
                    response_content += chunk.get("content", "")
                elif chunk.get("type") == "response_complete":
                    break
            
            # 发送回复
            if response_content:
                await adapter.send_message(
                    user_id=message.get('user_id'),
                    content=response_content,
                    message_type='text'
                )
            
        except Exception as e:
            self.logger.error(f"Failed to handle message for bot {bot_id}: {e}")
            
            # 更新错误计数
            if bot_id in self.running_bots:
                self.running_bots[bot_id]['error_count'] += 1
    
    async def _get_or_create_conversation(
        self,
        bot_id: str,
        platform_user_id: str,
        platform_type: str
    ) -> Conversation:
        """获取或创建对话"""
        try:
            # 查找现有对话
            conversations, _ = await conversation_manager.get_conversations(
                filters={
                    'bot_id': bot_id,
                    'platform_chat_id': platform_user_id,
                    'platform': platform_type,
                    'status': 'active'
                },
                limit=1
            )
            
            if conversations:
                return conversations[0]
            
            # 创建新对话
            bot = await self.get_bot_by_id(bot_id)
            conversation = await conversation_manager.create_conversation(
                user_id=bot.user_id,
                bot_id=bot_id,
                title=f"与{bot.name}的对话",
                platform=platform_type,
                platform_chat_id=platform_user_id,
                context={}
            )
            
            return conversation
            
        except Exception as e:
            self.logger.error(f"Failed to get or create conversation: {e}")
            raise
    
    async def _save_message(
        self,
        conversation_id: str,
        content: str,
        message_type: str,
        sender_type: str,
        sender_id: str,
        metadata: Dict[str, Any]
    ) -> Any:
        """保存消息"""
        try:
            message = await message_manager.create_message(
                conversation_id=conversation_id,
                content=content,
                message_type=message_type,
                sender_type=sender_type,
                sender_id=sender_id,
                metadata=metadata
            )
            return message
        except Exception as e:
            self.logger.error(f"Failed to save message: {e}")
            raise
    
    async def _validate_platform_config(
        self,
        platform_type: str,
        config: Dict[str, Any]
    ) -> bool:
        """验证平台配置"""
        try:
            # 获取适配器并验证配置
            adapter = get_adapter(platform_type)
            if not adapter:
                return False
            
            return await adapter.validate_config(config)
        except Exception as e:
            self.logger.error(f"Platform config validation failed: {e}")
            return False
    
    async def _validate_llm_config(self, config: Dict[str, Any]) -> bool:
        """验证LLM配置"""
        try:
            required_fields = ['provider', 'model']
            return all(field in config for field in required_fields)
        except Exception as e:
            self.logger.error(f"LLM config validation failed: {e}")
            return False
    
    async def _cleanup_bot_data(self, session: AsyncSession, bot_id: str):
        """清理机器人相关数据"""
        try:
            # 删除消息
            await session.execute(
                select(Message).join(Conversation).where(Conversation.bot_id == bot_id)
            )
            
            # 删除对话
            await session.execute(
                select(Conversation).where(Conversation.bot_id == bot_id)
            )
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup bot data: {e}")


# 全局机器人管理器实例
bot_manager = BotManager()