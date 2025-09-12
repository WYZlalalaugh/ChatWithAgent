"""
对话管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, AsyncGenerator
import logging
import json

from ...security.auth import AuthManager
from ...models.database import User
from ...managers.conversation_manager import conversation_manager
from ...managers.bot_manager import bot_manager
from ...engines.conversation_engine import conversation_engine
from ...engines.stream_processor import stream_processor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/conversations", tags=["conversations"])
security = HTTPBearer()


class ConversationResponse(BaseModel):
    """对话响应模型"""
    id: str
    user_id: str
    bot_id: str
    title: str
    platform: str
    platform_chat_id: str
    status: str
    context: Dict[str, Any]
    created_at: str
    updated_at: str
    last_message_at: Optional[str] = None


class ConversationCreateRequest(BaseModel):
    """创建对话请求模型"""
    bot_id: str
    title: Optional[str] = None
    platform: str = "web"
    platform_chat_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ConversationListResponse(BaseModel):
    """对话列表响应模型"""
    conversations: List[ConversationResponse]
    total: int
    page: int
    page_size: int


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    stream: bool = False
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    message_id: str
    response: str
    conversation_id: str
    timestamp: str


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """获取当前用户依赖"""
    auth_manager = AuthManager()
    token = credentials.credentials
    user = await auth_manager.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return user


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    bot_id: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """获取对话列表"""
    try:
        # 构建过滤条件
        filters = {}
        if current_user.role != "admin":
            filters['user_id'] = current_user.id
        
        if bot_id:
            filters['bot_id'] = bot_id
        if platform:
            filters['platform'] = platform
        if status:
            filters['status'] = status
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 获取对话列表
        conversations, total = await conversation_manager.get_conversations(
            filters=filters,
            offset=offset,
            limit=page_size,
            order_by=['-updated_at']  # 按更新时间倒序
        )
        
        # 转换为响应模型
        conversation_responses = []
        for conv in conversations:
            conversation_responses.append(ConversationResponse(
                id=conv.id,
                user_id=conv.user_id,
                bot_id=conv.bot_id,
                title=conv.title,
                platform=conv.platform,
                platform_chat_id=conv.platform_chat_id,
                status=conv.status,
                context=conv.context,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat(),
                last_message_at=conv.last_message_at.isoformat() if conv.last_message_at else None
            ))
        
        return ConversationListResponse(
            conversations=conversation_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"List conversations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取对话详情"""
    try:
        conversation = await conversation_manager.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # 权限检查
        if current_user.role != "admin" and conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        return ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            bot_id=conversation.bot_id,
            title=conversation.title,
            platform=conversation.platform,
            platform_chat_id=conversation.platform_chat_id,
            status=conversation.status,
            context=conversation.context,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            last_message_at=conversation.last_message_at.isoformat() if conversation.last_message_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """创建新对话"""
    try:
        # 验证机器人存在且有权限
        bot = await bot_manager.get_bot(request.bot_id)
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        if current_user.role != "admin" and bot.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        # 生成默认标题
        title = request.title or f"与 {bot.name} 的对话"
        
        # 创建对话
        conversation = await conversation_manager.create_conversation(
            user_id=current_user.id,
            bot_id=request.bot_id,
            title=title,
            platform=request.platform,
            platform_chat_id=request.platform_chat_id,
            context=request.context or {}
        )
        
        return ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            bot_id=conversation.bot_id,
            title=conversation.title,
            platform=conversation.platform,
            platform_chat_id=conversation.platform_chat_id,
            status=conversation.status,
            context=conversation.context,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            last_message_at=conversation.last_message_at.isoformat() if conversation.last_message_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{conversation_id}/chat", response_model=ChatResponse)
async def chat_with_bot(
    conversation_id: str,
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """与机器人对话（非流式）"""
    try:
        # 验证对话存在且有权限
        conversation = await conversation_manager.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        if current_user.role != "admin" and conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        # 获取机器人配置
        bot = await bot_manager.get_bot(conversation.bot_id)
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # 构建机器人配置
        bot_config = {
            "llm_config": bot.llm_config,
            "system_prompt": bot.description,
            "knowledge_base_ids": getattr(bot, 'knowledge_base_ids', []),
            "plugins": getattr(bot, 'plugins', [])
        }
        
        # 处理消息
        response_content = ""
        message_id = None
        
        async for chunk in conversation_engine.process_message(
            conversation_id=conversation_id,
            user_message=request.message,
            bot_config=bot_config,
            stream=False
        ):
            if chunk.get("type") == "message_saved":
                message_id = chunk.get("message_id")
            elif chunk.get("type") == "content":
                response_content += chunk.get("content", "")
            elif chunk.get("type") == "response_complete":
                break
        
        return ChatResponse(
            message_id=message_id or "",
            response=response_content,
            conversation_id=conversation_id,
            timestamp=conversation_engine._get_current_time()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat with bot error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/{conversation_id}/chat/stream")
async def chat_with_bot_stream(
    conversation_id: str,
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """与机器人对话（流式）"""
    try:
        # 验证对话存在且有权限
        conversation = await conversation_manager.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        if current_user.role != "admin" and conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        # 获取机器人配置
        bot = await bot_manager.get_bot(conversation.bot_id)
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bot not found"
            )
        
        # 构建机器人配置
        bot_config = {
            "llm_config": bot.llm_config,
            "system_prompt": bot.description,
            "knowledge_base_ids": getattr(bot, 'knowledge_base_ids', []),
            "plugins": getattr(bot, 'plugins', [])
        }
        
        async def generate_stream():
            """生成流式响应"""
            try:
                async for chunk in conversation_engine.process_message(
                    conversation_id=conversation_id,
                    user_message=request.message,
                    bot_config=bot_config,
                    stream=True
                ):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                
                # 发送结束标记
                yield f"data: {json.dumps({'type': 'stream_end'}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                logger.error(f"Stream generation error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Stream error'}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat stream error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    title: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user)
):
    """更新对话"""
    try:
        # 验证对话存在且有权限
        conversation = await conversation_manager.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        if current_user.role != "admin" and conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        # 准备更新数据
        update_data = {}
        if title is not None:
            update_data['title'] = title
        if context is not None:
            update_data['context'] = context
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # 更新对话
        updated_conversation = await conversation_manager.update_conversation(
            conversation_id, update_data
        )
        
        return ConversationResponse(
            id=updated_conversation.id,
            user_id=updated_conversation.user_id,
            bot_id=updated_conversation.bot_id,
            title=updated_conversation.title,
            platform=updated_conversation.platform,
            platform_chat_id=updated_conversation.platform_chat_id,
            status=updated_conversation.status,
            context=updated_conversation.context,
            created_at=updated_conversation.created_at.isoformat(),
            updated_at=updated_conversation.updated_at.isoformat(),
            last_message_at=updated_conversation.last_message_at.isoformat() if updated_conversation.last_message_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除对话"""
    try:
        # 验证对话存在且有权限
        conversation = await conversation_manager.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        if current_user.role != "admin" and conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        # 删除对话
        await conversation_manager.delete_conversation(conversation_id)
        
        return {"success": True, "message": "Conversation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{conversation_id}/statistics")
async def get_conversation_statistics(
    conversation_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取对话统计信息"""
    try:
        # 验证对话存在且有权限
        conversation = await conversation_manager.get_conversation_by_id(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        if current_user.role != "admin" and conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )
        
        # 获取统计信息
        stats = await conversation_manager.get_conversation_statistics(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "total_messages": stats.get('total_messages', 0),
            "user_messages": stats.get('user_messages', 0),
            "bot_messages": stats.get('bot_messages', 0),
            "avg_response_time": stats.get('avg_response_time', 0),
            "first_message_time": stats.get('first_message_time'),
            "last_message_time": stats.get('last_message_time'),
            "conversation_duration": stats.get('conversation_duration', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )