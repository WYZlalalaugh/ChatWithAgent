"""
MCP协议数据类型定义
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import json


class MCPMessageType(str, Enum):
    """MCP消息类型"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class MCPMethod(str, Enum):
    """MCP方法枚举"""
    # 工具相关
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    
    # 资源相关
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"
    
    # 提示相关
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"
    
    # 连接管理
    INITIALIZE = "initialize"
    PING = "ping"
    
    # 通知
    PROGRESS = "notifications/progress"
    LOG = "notifications/log"


@dataclass
class MCPMessage:
    """MCP消息基类"""
    jsonrpc: str = "2.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            k: v for k, v in self.__dict__.items() 
            if v is not None
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        return cls(**{
            k: v for k, v in data.items() 
            if k in cls.__dataclass_fields__
        })


@dataclass
class MCPRequest(MCPMessage):
    """MCP请求消息"""
    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]] = None


@dataclass 
class MCPResponse(MCPMessage):
    """MCP响应消息"""
    id: Union[str, int]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


@dataclass
class MCPNotification(MCPMessage):
    """MCP通知消息"""
    method: str
    params: Optional[Dict[str, Any]] = None


@dataclass
class MCPError:
    """MCP错误信息"""
    code: int
    message: str
    data: Optional[Any] = None
    
    # 标准错误代码
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP特定错误代码
    TOOL_NOT_FOUND = -32000
    TOOL_EXECUTION_ERROR = -32001
    RESOURCE_NOT_FOUND = -32002
    PERMISSION_DENIED = -32003


@dataclass
class MCPToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None


@dataclass
class MCPTool:
    """MCP工具定义"""
    name: str
    description: str
    parameters: List[MCPToolParameter] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": param.type,
                        "description": param.description,
                        **({"enum": param.enum} if param.enum else {}),
                        **({"default": param.default} if param.default is not None else {})
                    }
                    for param in self.parameters
                },
                "required": [param.name for param in self.parameters if param.required]
            }
        }


@dataclass
class MCPResource:
    """MCP资源定义"""
    uri: str
    name: str
    description: str
    mimeType: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "uri": self.uri,
            "name": self.name,
            "description": self.description
        }
        if self.mimeType:
            result["mimeType"] = self.mimeType
        return result


@dataclass
class MCPPrompt:
    """MCP提示定义"""
    name: str
    description: str
    arguments: Optional[List[MCPToolParameter]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "name": self.name,
            "description": self.description
        }
        if self.arguments:
            result["arguments"] = [arg.__dict__ for arg in self.arguments]
        return result


@dataclass
class MCPProgress:
    """进度通知"""
    progress: int  # 0-100
    total: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {"progress": self.progress}
        if self.total is not None:
            result["total"] = self.total
        return result


@dataclass
class MCPLogEntry:
    """日志条目"""
    level: str  # debug, info, warning, error
    message: str
    data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "level": self.level,
            "message": self.message
        }
        if self.data:
            result["data"] = self.data
        return result


# 标准错误响应模板
def create_error_response(
    request_id: Union[str, int],
    error_code: int,
    error_message: str,
    error_data: Optional[Any] = None
) -> MCPResponse:
    """创建错误响应"""
    error = {
        "code": error_code,
        "message": error_message
    }
    if error_data is not None:
        error["data"] = error_data
        
    return MCPResponse(
        id=request_id,
        error=error
    )


def create_success_response(
    request_id: Union[str, int],
    result: Any
) -> MCPResponse:
    """创建成功响应"""
    return MCPResponse(
        id=request_id,
        result=result
    )