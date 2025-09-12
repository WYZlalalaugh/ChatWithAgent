"""
WebSocket路由 - 实时对话支持
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.security.utils import get_authorization_scheme_param
import uuid

from ...security.auth import AuthManager
from ...engines.conversation_engine import conversation_engine
from ...engines.stream_processor import stream_processor
from ...managers.bot_manager import bot_manager
from ...managers.conversation_manager import conversation_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, set] = {}
        self.conversation_connections: Dict[str, set] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str):
        """建立连接"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
    
    def disconnect(self, connection_id: str, user_id: str):
        """断开连接"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # 从对话连接中移除
        for conv_id, connections in self.conversation_connections.items():
            connections.discard(connection_id)
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    def join_conversation(self, connection_id: str, conversation_id: str):
        """加入对话"""
        if conversation_id not in self.conversation_connections:
            self.conversation_connections[conversation_id] = set()
        self.conversation_connections[conversation_id].add(connection_id)
    
    def leave_conversation(self, connection_id: str, conversation_id: str):
        """离开对话"""
        if conversation_id in self.conversation_connections:
            self.conversation_connections[conversation_id].discard(connection_id)
            if not self.conversation_connections[conversation_id]:
                del self.conversation_connections[conversation_id]
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """发送个人消息"""
        websocket = self.active_connections.get(connection_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
    
    async def broadcast_to_conversation(self, message: Dict[str, Any], conversation_id: str):
        """向对话中的所有连接广播消息"""
        connections = self.conversation_connections.get(conversation_id, set())
        
        for connection_id in list(connections):  # 使用副本避免迭代时修改
            await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_user(self, message: Dict[str, Any], user_id: str):
        """向用户的所有连接广播消息"""
        connections = self.user_connections.get(user_id, set())
        
        for connection_id in list(connections):
            await self.send_personal_message(message, connection_id)


# 全局连接管理器
connection_manager = ConnectionManager()


async def authenticate_websocket(websocket: WebSocket, token: Optional[str] = None):
    """WebSocket认证"""
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return None
    
    try:
        auth_manager = AuthManager()
        user = await auth_manager.get_current_user(token)
        if not user:
            await websocket.close(code=1008, reason="Invalid token")
            return None
        return user
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return None


@router.websocket("/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    conversation_id: Optional[str] = Query(None),
    bot_id: Optional[str] = Query(None)
):
    """WebSocket聊天端点"""
    connection_id = str(uuid.uuid4())
    user = None
    
    try:
        # 认证用户
        user = await authenticate_websocket(websocket, token)
        if not user:
            return
        
        # 建立连接
        await connection_manager.connect(websocket, connection_id, user.id)
        
        # 如果指定了对话ID，加入对话
        if conversation_id:
            # 验证对话权限
            conversation = await conversation_manager.get_conversation_by_id(conversation_id)
            if not conversation:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Conversation not found"
                }))
                return
            
            if user.role != "admin" and conversation.user_id != user.id:
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "message": "Permission denied"
                }))
                return
            
            connection_manager.join_conversation(connection_id, conversation_id)
        
        # 发送连接成功消息
        await websocket.send_text(json.dumps({
            "type": "connected",
            "connection_id": connection_id,
            "user_id": user.id,
            "conversation_id": conversation_id
        }))
        
        # 消息处理循环
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            await handle_websocket_message(
                websocket, connection_id, user, message_data, conversation_id, bot_id
            )
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Internal server error"
            }))
        except:
            pass
    finally:
        if user:
            connection_manager.disconnect(connection_id, user.id)


async def handle_websocket_message(
    websocket: WebSocket,
    connection_id: str,
    user: Any,
    message_data: Dict[str, Any],
    conversation_id: Optional[str] = None,
    bot_id: Optional[str] = None
):
    """处理WebSocket消息"""
    try:
        message_type = message_data.get("type")
        
        if message_type == "chat":
            await handle_chat_message(
                websocket, connection_id, user, message_data, conversation_id, bot_id
            )
        elif message_type == "join_conversation":
            await handle_join_conversation(connection_id, message_data)
        elif message_type == "leave_conversation":
            await handle_leave_conversation(connection_id, message_data)
        elif message_type == "ping":
            await websocket.send_text(json.dumps({"type": "pong"}))
        else:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            }))
    
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Failed to process message"
        }))


async def handle_chat_message(
    websocket: WebSocket,
    connection_id: str,
    user: Any,
    message_data: Dict[str, Any],
    conversation_id: Optional[str] = None,
    bot_id: Optional[str] = None
):
    """处理聊天消息"""
    try:
        content = message_data.get("content", "").strip()
        if not content:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Message content cannot be empty"
            }))
            return
        
        # 如果没有指定对话ID，创建新对话
        if not conversation_id:
            if not bot_id:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Bot ID is required for new conversation"
                }))
                return
            
            # 验证机器人
            bot = await bot_manager.get_bot(bot_id)
            if not bot:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Bot not found"
                }))
                return
            
            if user.role != "admin" and bot.user_id != user.id:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Permission denied"
                }))
                return
            
            # 创建新对话
            conversation = await conversation_manager.create_conversation(
                user_id=user.id,
                bot_id=bot_id,
                title=content[:50] if len(content) > 50 else content,
                platform="web",
                platform_chat_id=f"web_{connection_id}"
            )
            conversation_id = conversation.id
            
            # 加入对话
            connection_manager.join_conversation(connection_id, conversation_id)
            
            # 通知创建了新对话
            await websocket.send_text(json.dumps({
                "type": "conversation_created",
                "conversation_id": conversation_id,
                "bot_id": bot_id
            }))
        
        # 获取机器人配置
        conversation = await conversation_manager.get_conversation_by_id(conversation_id)
        if not conversation:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Conversation not found"
            }))
            return
        
        bot = await bot_manager.get_bot(conversation.bot_id)
        if not bot:
            await websocket.send_text(json.dumps({
                "type": "error", 
                "message": "Bot not found"
            }))
            return
        
        # 发送用户消息确认
        await websocket.send_text(json.dumps({
            "type": "message_received",
            "conversation_id": conversation_id,
            "content": content,
            "timestamp": conversation_engine._get_current_time()
        }))
        
        # 创建流式对话
        stream_id = await stream_processor.create_stream(
            conversation_id=conversation_id,
            user_message=content,
            bot_config={
                "llm_config": bot.llm_config,
                "system_prompt": bot.description,
                "knowledge_base_ids": getattr(bot, 'knowledge_base_ids', []),
                "plugins": getattr(bot, 'plugins', [])
            },
            websocket=websocket
        )
        
        # 通知开始生成响应
        await websocket.send_text(json.dumps({
            "type": "response_start",
            "stream_id": stream_id,
            "conversation_id": conversation_id
        }))
    
    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Failed to process chat message"
        }))


async def handle_join_conversation(connection_id: str, message_data: Dict[str, Any]):
    """处理加入对话"""
    conversation_id = message_data.get("conversation_id")
    if conversation_id:
        connection_manager.join_conversation(connection_id, conversation_id)


async def handle_leave_conversation(connection_id: str, message_data: Dict[str, Any]):
    """处理离开对话"""
    conversation_id = message_data.get("conversation_id")
    if conversation_id:
        connection_manager.leave_conversation(connection_id, conversation_id)


@router.websocket("/notifications")
async def websocket_notifications_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """WebSocket通知端点"""
    connection_id = str(uuid.uuid4())
    user = None
    
    try:
        # 认证用户
        user = await authenticate_websocket(websocket, token)
        if not user:
            return
        
        # 建立连接
        await connection_manager.connect(websocket, connection_id, user.id)
        
        # 发送连接成功消息
        await websocket.send_text(json.dumps({
            "type": "connected",
            "connection_id": connection_id,
            "user_id": user.id
        }))
        
        # 保持连接活跃
        while True:
            try:
                # 等待ping消息或其他控制消息
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                message_data = json.loads(data)
                
                if message_data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # 发送心跳
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
            except WebSocketDisconnect:
                break
    
    except Exception as e:
        logger.error(f"WebSocket notifications error: {e}")
    finally:
        if user:
            connection_manager.disconnect(connection_id, user.id)


# 导出连接管理器供其他模块使用
__all__ = ["connection_manager", "router"]