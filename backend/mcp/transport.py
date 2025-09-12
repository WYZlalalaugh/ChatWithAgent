"""
MCP WebSocket传输层实现
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from .server import MCPServer
from .client import MCPClient


class MCPWebSocketServer:
    """MCP WebSocket服务器"""
    
    def __init__(
        self,
        mcp_server: MCPServer,
        host: str = "localhost",
        port: int = 8001
    ):
        self.mcp_server = mcp_server
        self.host = host
        self.port = port
        self.logger = logging.getLogger("mcp.websocket.server")
        
        # 客户端连接管理
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.server: Optional[websockets.WebSocketServer] = None
        
    async def start(self):
        """启动WebSocket服务器"""
        try:
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port
            )
            self.logger.info(f"MCP WebSocket server started on {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop(self):
        """停止WebSocket服务器"""
        try:
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                self.logger.info("MCP WebSocket server stopped")
                
            # 关闭所有客户端连接
            for client_id, websocket in self.clients.items():
                await websocket.close()
                
            self.clients.clear()
            
        except Exception as e:
            self.logger.error(f"Error stopping WebSocket server: {e}")
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """处理客户端连接"""
        client_id = f"ws_{id(websocket)}"
        self.clients[client_id] = websocket
        
        self.logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        
        try:
            async for message in websocket:
                try:
                    # 处理MCP请求
                    response = await self.mcp_server.handle_request(message, client_id)
                    
                    # 发送响应（如果有）
                    if response:
                        await websocket.send(response)
                        
                except Exception as e:
                    self.logger.error(f"Error handling message from {client_id}: {e}")
                    # 发送错误响应
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32603,
                            "message": "Internal error"
                        }
                    }
                    await websocket.send(json.dumps(error_response))
                    
        except ConnectionClosed:
            self.logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            self.logger.error(f"Error in client handler {client_id}: {e}")
        finally:
            # 清理客户端连接
            self.clients.pop(client_id, None)
            self.mcp_server.disconnect_client(client_id)
    
    async def send_notification(self, client_id: str, notification: str) -> bool:
        """向特定客户端发送通知"""
        try:
            websocket = self.clients.get(client_id)
            if websocket:
                await websocket.send(notification)
                return True
            else:
                self.logger.warning(f"Client {client_id} not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending notification to {client_id}: {e}")
            return False
    
    async def broadcast_notification(self, notification: str):
        """向所有客户端广播通知"""
        if not self.clients:
            return
        
        # 并发发送给所有客户端
        tasks = []
        for client_id, websocket in self.clients.items():
            task = self._send_to_client(websocket, notification, client_id)
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_to_client(
        self,
        websocket: WebSocketServerProtocol,
        message: str,
        client_id: str
    ):
        """向单个客户端发送消息"""
        try:
            await websocket.send(message)
        except Exception as e:
            self.logger.error(f"Error sending to client {client_id}: {e}")
    
    def get_connected_clients(self) -> List[str]:
        """获取已连接的客户端列表"""
        return list(self.clients.keys())


class MCPWebSocketClient:
    """MCP WebSocket客户端"""
    
    def __init__(
        self,
        mcp_client: MCPClient,
        server_uri: str = "ws://localhost:8001"
    ):
        self.mcp_client = mcp_client
        self.server_uri = server_uri
        self.logger = logging.getLogger("mcp.websocket.client")
        
        # 连接状态
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False
        
        # 设置传输层
        self.mcp_client.set_transport(self._send_message)
    
    async def connect(self) -> bool:
        """连接到MCP服务器"""
        try:
            self.websocket = await websockets.connect(self.server_uri)
            self.mcp_client.set_connection_state(True)
            
            self.logger.info(f"Connected to MCP server: {self.server_uri}")
            
            # 启动消息处理任务
            self.is_running = True
            asyncio.create_task(self._message_handler())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        try:
            self.is_running = False
            
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            self.mcp_client.set_connection_state(False)
            self.logger.info("Disconnected from MCP server")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")
    
    async def _send_message(self, message: str):
        """发送消息"""
        if not self.websocket:
            raise RuntimeError("Not connected to server")
        
        await self.websocket.send(message)
    
    async def _message_handler(self):
        """消息处理器"""
        try:
            if not self.websocket:
                return
            
            async for message in self.websocket:
                if not self.is_running:
                    break
                
                try:
                    await self.mcp_client.handle_message(message)
                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")
                    
        except ConnectionClosed:
            self.logger.info("Server connection closed")
        except Exception as e:
            self.logger.error(f"Message handler error: {e}")
        finally:
            self.mcp_client.set_connection_state(False)
    
    async def initialize_and_connect(
        self,
        capabilities: Optional[Dict[str, Any]] = None
    ) -> bool:
        """连接并初始化"""
        try:
            # 先连接
            if not await self.connect():
                return False
            
            # 等待连接稳定
            await asyncio.sleep(0.1)
            
            # 初始化
            if not await self.mcp_client.initialize(capabilities):
                await self.disconnect()
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Initialize and connect error: {e}")
            await self.disconnect()
            return False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.mcp_client.is_connected and self.websocket is not None


# 便捷函数
async def create_mcp_websocket_server(
    host: str = "localhost",
    port: int = 8001,
    auto_start: bool = True
) -> MCPWebSocketServer:
    """创建MCP WebSocket服务器"""
    from .server import get_mcp_server
    from .tools import register_builtin_tools
    
    # 注册内置工具
    register_builtin_tools()
    
    # 创建服务器
    mcp_server = get_mcp_server()
    ws_server = MCPWebSocketServer(mcp_server, host, port)
    
    if auto_start:
        await ws_server.start()
    
    return ws_server


async def create_mcp_websocket_client(
    server_uri: str = "ws://localhost:8001",
    auto_connect: bool = True
) -> MCPWebSocketClient:
    """创建MCP WebSocket客户端"""
    mcp_client = MCPClient()
    ws_client = MCPWebSocketClient(mcp_client, server_uri)
    
    if auto_connect:
        await ws_client.initialize_and_connect()
    
    return ws_client