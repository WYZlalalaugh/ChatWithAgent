"""
MCP客户端实现
"""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from .types import (
    MCPRequest, MCPResponse, MCPNotification, MCPMessage,
    MCPMethod, MCPError, MCPTool, MCPProgress, MCPLogEntry
)


class MCPClient:
    """MCP协议客户端"""
    
    def __init__(
        self,
        name: str = "ChatAgent MCP Client",
        version: str = "1.0.0"
    ):
        self.name = name
        self.version = version
        self.logger = logging.getLogger("mcp.client")
        
        # 连接状态
        self.is_connected = False
        self.is_initialized = False
        self.server_info: Optional[Dict[str, Any]] = None
        self.server_capabilities: Optional[Dict[str, Any]] = None
        
        # 请求管理
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.request_counter = 0
        
        # 工具缓存
        self.available_tools: List[MCPTool] = []
        
        # 回调函数
        self.progress_handler: Optional[Callable[[MCPProgress], None]] = None
        self.log_handler: Optional[Callable[[MCPLogEntry], None]] = None
        
        # 传输层接口（需要子类实现）
        self.send_message: Optional[Callable[[str], asyncio.Future]] = None
        
    async def initialize(
        self,
        capabilities: Optional[Dict[str, Any]] = None
    ) -> bool:
        """初始化连接"""
        try:
            if not self.is_connected:
                self.logger.error("Not connected to server")
                return False
            
            # 准备初始化参数
            init_params = {
                "protocolVersion": self.version,
                "clientInfo": {
                    "name": self.name,
                    "version": self.version
                },
                "capabilities": capabilities or {
                    "tools": True,
                    "resources": False,
                    "prompts": False
                }
            }
            
            # 发送初始化请求
            response = await self._send_request(
                MCPMethod.INITIALIZE,
                init_params
            )
            
            if response and not response.error:
                result = response.result
                self.server_info = result.get("serverInfo", {})
                self.server_capabilities = result.get("capabilities", {})
                self.is_initialized = True
                
                self.logger.info(f"Initialized with server: {self.server_info}")
                return True
            else:
                error_msg = response.error.get("message", "Unknown error") if response.error else "No response"
                self.logger.error(f"Initialization failed: {error_msg}")
                return False
                
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            return False
    
    async def list_tools(self) -> List[MCPTool]:
        """获取可用工具列表"""
        try:
            if not self.is_initialized:
                self.logger.error("Client not initialized")
                return []
            
            if not self.server_capabilities.get("tools"):
                self.logger.warning("Server does not support tools")
                return []
            
            response = await self._send_request(MCPMethod.LIST_TOOLS)
            
            if response and not response.error:
                tools_data = response.result.get("tools", [])
                self.available_tools = []
                
                for tool_data in tools_data:
                    # 解析工具定义
                    tool = MCPTool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        parameters=[]  # 简化处理，实际应解析inputSchema
                    )
                    self.available_tools.append(tool)
                
                self.logger.info(f"Retrieved {len(self.available_tools)} tools")
                return self.available_tools
            else:
                error_msg = response.error.get("message", "Unknown error") if response.error else "No response"
                self.logger.error(f"List tools failed: {error_msg}")
                return []
                
        except Exception as e:
            self.logger.error(f"List tools error: {e}")
            return []
    
    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """调用工具"""
        try:
            if not self.is_initialized:
                return {
                    "success": False,
                    "error": "Client not initialized"
                }
            
            if not self.server_capabilities.get("tools"):
                return {
                    "success": False,
                    "error": "Server does not support tools"
                }
            
            # 准备调用参数
            call_params = {
                "name": tool_name,
                "arguments": arguments or {}
            }
            
            response = await self._send_request(
                MCPMethod.CALL_TOOL,
                call_params
            )
            
            if response and not response.error:
                result = response.result
                content = result.get("content", [])
                is_error = result.get("isError", False)
                
                # 提取文本内容
                text_content = ""
                for item in content:
                    if item.get("type") == "text":
                        text_content += item.get("text", "")
                
                return {
                    "success": not is_error,
                    "result": text_content,
                    "content": content,
                    "tool_name": tool_name
                }
            else:
                error_msg = response.error.get("message", "Unknown error") if response.error else "No response"
                return {
                    "success": False,
                    "error": error_msg,
                    "tool_name": tool_name
                }
                
        except Exception as e:
            self.logger.error(f"Tool call error: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }
    
    async def ping(self) -> bool:
        """发送ping请求"""
        try:
            response = await self._send_request(MCPMethod.PING)
            
            if response and not response.error:
                result = response.result
                return result.get("pong", False)
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Ping error: {e}")
            return False
    
    async def _send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Optional[MCPResponse]:
        """发送请求"""
        try:
            if not self.send_message:
                raise RuntimeError("Transport layer not configured")
            
            # 生成请求ID
            self.request_counter += 1
            request_id = f"req_{self.request_counter}_{uuid.uuid4().hex[:8]}"
            
            # 创建请求
            request = MCPRequest(
                id=request_id,
                method=method,
                params=params
            )
            
            # 创建Future等待响应
            response_future = asyncio.Future()
            self.pending_requests[request_id] = response_future
            
            try:
                # 发送请求
                await self.send_message(request.to_json())
                
                # 等待响应
                response = await asyncio.wait_for(response_future, timeout=timeout)
                return response
                
            finally:
                # 清理待处理请求
                self.pending_requests.pop(request_id, None)
                
        except asyncio.TimeoutError:
            self.logger.error(f"Request timeout: {method}")
            return None
        except Exception as e:
            self.logger.error(f"Send request error: {e}")
            return None
    
    async def handle_message(self, message_data: str):
        """处理收到的消息"""
        try:
            message_dict = json.loads(message_data)
            
            # 检查是否为响应
            if "id" in message_dict and message_dict["id"] in self.pending_requests:
                # 处理响应
                response = MCPResponse.from_dict(message_dict)
                future = self.pending_requests.get(response.id)
                if future and not future.done():
                    future.set_result(response)
                return
            
            # 检查是否为通知
            if "method" in message_dict and "id" not in message_dict:
                notification = MCPNotification.from_dict(message_dict)
                await self._handle_notification(notification)
                return
            
            self.logger.warning(f"Unknown message type: {message_dict}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
        except Exception as e:
            self.logger.error(f"Message handling error: {e}")
    
    async def _handle_notification(self, notification: MCPNotification):
        """处理通知"""
        try:
            if notification.method == MCPMethod.PROGRESS:
                # 处理进度通知
                if self.progress_handler and notification.params:
                    progress = MCPProgress(**notification.params)
                    self.progress_handler(progress)
                    
            elif notification.method == MCPMethod.LOG:
                # 处理日志通知
                if self.log_handler and notification.params:
                    log_entry = MCPLogEntry(**notification.params)
                    self.log_handler(log_entry)
                    
            else:
                self.logger.info(f"Received notification: {notification.method}")
                
        except Exception as e:
            self.logger.error(f"Notification handling error: {e}")
    
    def set_transport(self, send_func: Callable[[str], asyncio.Future]):
        """设置传输层"""
        self.send_message = send_func
    
    def set_connection_state(self, connected: bool):
        """设置连接状态"""
        self.is_connected = connected
        if not connected:
            self.is_initialized = False
            # 取消所有待处理请求
            for future in self.pending_requests.values():
                if not future.done():
                    future.cancel()
            self.pending_requests.clear()
    
    def set_progress_handler(self, handler: Callable[[MCPProgress], None]):
        """设置进度处理器"""
        self.progress_handler = handler
    
    def set_log_handler(self, handler: Callable[[MCPLogEntry], None]):
        """设置日志处理器"""
        self.log_handler = handler
    
    def get_status(self) -> Dict[str, Any]:
        """获取客户端状态"""
        return {
            "name": self.name,
            "version": self.version,
            "is_connected": self.is_connected,
            "is_initialized": self.is_initialized,
            "server_info": self.server_info,
            "server_capabilities": self.server_capabilities,
            "available_tools": [tool.name for tool in self.available_tools],
            "pending_requests": len(self.pending_requests)
        }