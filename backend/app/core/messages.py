"""
统一消息格式定义
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    """平台类型枚举"""
    QQ = "qq"
    QQ_CHANNEL = "qq_channel"
    WECHAT = "wechat"
    WECHAT_PERSONAL = "wechat_personal"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"


class ChatType(str, Enum):
    """聊天类型枚举"""
    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    SYSTEM = "system"
    CARD = "card"
    LOCATION = "location"


class MessageStatus(str, Enum):
    """消息状态枚举"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class UserInfo(BaseModel):
    """用户信息"""
    user_id: str
    username: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    platform_data: Optional[Dict[str, Any]] = None


class ChatInfo(BaseModel):
    """聊天信息"""
    chat_id: str
    chat_type: ChatType
    chat_name: Optional[str] = None
    member_count: Optional[int] = None
    platform_data: Optional[Dict[str, Any]] = None


class MessageContent(BaseModel):
    """消息内容"""
    text: Optional[str] = None
    media_url: Optional[str] = None
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    duration: Optional[int] = None  # 音频/视频时长（秒）
    width: Optional[int] = None     # 图片/视频宽度
    height: Optional[int] = None    # 图片/视频高度
    thumbnail_url: Optional[str] = None  # 缩略图
    metadata: Optional[Dict[str, Any]] = None


class UnifiedMessage(BaseModel):
    """统一消息格式"""
    # 基础信息
    message_id: str = Field(..., description="消息唯一标识")
    conversation_id: Optional[str] = Field(None, description="对话唯一标识")
    
    # 平台信息
    platform: PlatformType = Field(..., description="平台类型")
    platform_message_id: Optional[str] = Field(None, description="平台原始消息ID")
    
    # 发送者信息
    sender: UserInfo = Field(..., description="发送者信息")
    
    # 聊天信息
    chat: ChatInfo = Field(..., description="聊天信息")
    
    # 消息内容
    message_type: MessageType = Field(..., description="消息类型")
    content: MessageContent = Field(..., description="消息内容")
    
    # 回复信息
    reply_to: Optional[str] = Field(None, description="回复的消息ID")
    
    # 时间信息
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="消息时间")
    
    # 状态信息
    status: MessageStatus = Field(default=MessageStatus.PENDING, description="消息状态")
    
    # 额外信息
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MessageEvent(BaseModel):
    """消息事件"""
    event_type: str = Field(..., description="事件类型")
    event_id: str = Field(..., description="事件唯一标识")
    platform: PlatformType = Field(..., description="平台类型")
    bot_id: Optional[str] = Field(None, description="机器人ID")
    message: Optional[UnifiedMessage] = Field(None, description="消息内容")
    data: Optional[Dict[str, Any]] = Field(None, description="事件数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="事件时间")


class MessageResponse(BaseModel):
    """消息响应"""
    response_id: str = Field(..., description="响应唯一标识")
    original_message_id: str = Field(..., description="原始消息ID")
    responses: List[UnifiedMessage] = Field(default_factory=list, description="响应消息列表")
    success: bool = Field(True, description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="响应元数据")