"""
MCP服务器实现
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from .types import (
    MCPRequest, MCPResponse, MCPNotification, MCPMessage,
    MCPMethod, MCPError, create_error_response, create_success_response,
    MCPProgress, MCPLogEntry
)
from .tools import ToolManager, global_tool_manager


class MCPServer:
    """MCP协议服务器"""
    
    def __init__(self, name: str = "ChatAgent MCP Server", version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.logger = logging.getLogger("mcp.server")
        self.tool_manager = global_tool_manager
        self.is_initialized = False
        
        # 客户端连接管理
        self.clients: Dict[str, Dict[str, Any]] = {}
        
        # 方法处理器映射
        self.method_handlers = {
            MCPMethod.INITIALIZE: self._handle_initialize,
            MCPMethod.LIST_TOOLS: self._handle_list_tools,
            MCPMethod.CALL_TOOL: self._handle_call_tool,
            MCPMethod.PING: self._handle_ping,
        }
        
        # 回调函数
        self.progress_callback: Optional[Callable[[str, MCPProgress], None]] = None
        self.log_callback: Optional[Callable[[MCPLogEntry], None]] = None
        
    async def handle_request(self, request_data: str, client_id: str = "default") -> str:
        """处理MCP请求"""
        try:
            # 解析请求
            request_dict = json.loads(request_data)
            
            # 验证JSON-RPC格式
            if request_dict.get("jsonrpc") != "2.0":
                return self._create_error_response(
                    None, MCPError.INVALID_REQUEST, "Invalid JSON-RPC version"
                ).to_json()
            
            # 检查是否为通知
            if "id" not in request_dict:
                # 处理通知
                notification = MCPNotification.from_dict(request_dict)
                await self._handle_notification(notification, client_id)
                return ""  # 通知不需要响应
            
            # 处理请求
            request = MCPRequest.from_dict(request_dict)
            response = await self._handle_request(request, client_id)
            return response.to_json()
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
            return create_error_response(
                None, MCPError.PARSE_ERROR, "Parse error"
            ).to_json()
        except Exception as e:
            self.logger.error(f"Request handling error: {e}")
            return create_error_response(
                None, MCPError.INTERNAL_ERROR, str(e)
            ).to_json()
    
    async def _handle_request(self, request: MCPRequest, client_id: str) -> MCPResponse:
        """处理具体请求"""
        try:
            # 检查方法是否存在
            if request.method not in self.method_handlers:
                return create_error_response(
                    request.id,
                    MCPError.METHOD_NOT_FOUND,
                    f"Method not found: {request.method}"
                )
            
            # 对于某些方法，检查初始化状态
            if (request.method != MCPMethod.INITIALIZE and 
                request.method != MCPMethod.PING and 
                not self.is_initialized):
                return create_error_response(
                    request.id,
                    MCPError.INVALID_REQUEST,
                    "Server not initialized"
                )
            
            # 执行方法处理器
            handler = self.method_handlers[request.method]
            result = await handler(request.params or {}, client_id)
            
            return create_success_response(request.id, result)
            
        except Exception as e:
            self.logger.error(f"Request handling error: {e}")
            return create_error_response(
                request.id,
                MCPError.INTERNAL_ERROR,
                str(e)
            )
    
    async def _handle_notification(self, notification: MCPNotification, client_id: str):
        """处理通知"""
        self.logger.info(f"Received notification: {notification.method} from {client_id}")
        
        # 这里可以根据需要处理不同类型的通知
        if notification.method == MCPMethod.PROGRESS:
            # 处理进度通知
            pass
        elif notification.method == MCPMethod.LOG:
            # 处理日志通知
            pass
    
    async def _handle_initialize(self, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """处理初始化请求"""
        try:
            client_info = params.get("clientInfo", {})
            protocol_version = params.get("protocolVersion", "1.0.0")
            capabilities = params.get("capabilities", {})
            
            # 记录客户端信息
            self.clients[client_id] = {
                "client_info": client_info,
                "protocol_version": protocol_version,
                "capabilities": capabilities,
                "connected_at": datetime.now().isoformat()
            }
            
            self.is_initialized = True
            
            self.logger.info(f"Client {client_id} initialized: {client_info}")
            
            return {
                "protocolVersion": self.version,
                "capabilities": {
                    "tools": True,
                    "resources": False,  # 暂未实现
                    "prompts": False,    # 暂未实现
                    "logging": True
                },
                "serverInfo": {
                    "name": self.name,
                    "version": self.version
                }
            }
            
        except Exception as e:
            self.logger.error(f"Initialize error: {e}")
            raise
    
    async def _handle_list_tools(self, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """处理列出工具请求"""
        try:
            tools = self.tool_manager.list_tools()
            
            return {
                "tools": [tool.to_dict() for tool in tools]
            }
            
        except Exception as e:
            self.logger.error(f"List tools error: {e}")
            raise
    
    async def _handle_call_tool(self, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """处理工具调用请求"""
        try:
            tool_name = params.get("name")
            if not tool_name:
                raise ValueError("Tool name is required")
            
            arguments = params.get("arguments", {})
            
            # 创建进度回调
            def progress_callback(progress: MCPProgress):
                if self.progress_callback:
                    self.progress_callback(client_id, progress)
            
            # 执行工具
            result = await self.tool_manager.execute_tool(
                tool_name=tool_name,
                parameters=arguments,
                progress_callback=progress_callback
            )
            
            if result["success"]:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": str(result["result"])
                        }
                    ],
                    "isError": False
                }
            else:
                return {
                    "content": [
                        {
                            "type": "text", 
                            "text": f"Tool execution failed: {result['error']}"
                        }
                    ],
                    "isError": True
                }
                
        except Exception as e:
            self.logger.error(f"Call tool error: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Tool execution error: {str(e)}"
                    }
                ],
                "isError": True
            }
    
    async def _handle_ping(self, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """处理ping请求"""
        return {"pong": True, "timestamp": datetime.now().isoformat()}
    
    def _create_error_response(
        self,
        request_id: Optional[Any],
        error_code: int,
        error_message: str
    ) -> MCPResponse:
        """创建错误响应"""
        return create_error_response(request_id, error_code, error_message)
    
    async def send_notification(
        self,
        client_id: str,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """发送通知给客户端"""
        try:
            notification = MCPNotification(
                method=method,
                params=params
            )
            return notification.to_json()
        except Exception as e:
            self.logger.error(f"Send notification error: {e}")
            return ""
    
    async def send_progress_notification(
        self,
        client_id: str,
        progress: MCPProgress
    ) -> str:
        """发送进度通知"""
        return await self.send_notification(
            client_id,
            MCPMethod.PROGRESS,
            progress.to_dict()
        )
    
    async def send_log_notification(
        self,
        client_id: str,
        log_entry: MCPLogEntry
    ) -> str:
        """发送日志通知"""
        return await self.send_notification(
            client_id,
            MCPMethod.LOG,
            log_entry.to_dict()
        )
    
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """获取客户端信息"""
        return self.clients.get(client_id)
    
    def list_clients(self) -> List[str]:
        """列出所有客户端"""
        return list(self.clients.keys())
    
    def disconnect_client(self, client_id: str):
        """断开客户端连接"""
        if client_id in self.clients:
            del self.clients[client_id]
            self.logger.info(f"Client {client_id} disconnected")
    
    def set_progress_callback(self, callback: Callable[[str, MCPProgress], None]):
        """设置进度回调"""
        self.progress_callback = callback
    
    def set_log_callback(self, callback: Callable[[MCPLogEntry], None]):
        """设置日志回调"""
        self.log_callback = callback
    
    def get_server_stats(self) -> Dict[str, Any]:
        """获取服务器统计信息"""
        return {
            "name": self.name,
            "version": self.version,
            "is_initialized": self.is_initialized,
            "client_count": len(self.clients),
            "clients": self.clients,
            "tool_stats": self.tool_manager.get_tool_stats(),
            "uptime": "unknown"  # 可以添加启动时间跟踪
        }


# 全局MCP服务器实例
mcp_server = MCPServer()


def get_mcp_server() -> MCPServer:
    """获取全局MCP服务器实例"""
    return mcp_server