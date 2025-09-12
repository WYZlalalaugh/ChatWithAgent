"""
API处理器基类
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
import json


class APIHandler(ABC):
    """API处理器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"api.handler.{name}")
    
    @abstractmethod
    async def handle(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理API请求"""
        pass
    
    async def validate_request(self, request_data: Dict[str, Any]) -> bool:
        """验证请求数据"""
        return True
    
    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求的完整流程"""
        try:
            # 验证请求
            if not await self.validate_request(request_data):
                return {
                    "success": False,
                    "error": "Invalid request data"
                }
            
            # 处理请求
            result = await self.handle(request_data)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger("api.websocket_manager")
        self.connections: Dict[str, List[WebSocket]] = {}
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str, metadata: Optional[Dict[str, Any]] = None):
        """建立WebSocket连接"""
        try:
            await websocket.accept()
            
            if client_id not in self.connections:
                self.connections[client_id] = []
            
            self.connections[client_id].append(websocket)
            self.connection_metadata[websocket] = metadata or {}
            
            self.logger.info(f"WebSocket connected: {client_id}")
            
        except Exception as e:
            self.logger.error(f"Error connecting WebSocket: {e}")
    
    async def disconnect(self, websocket: WebSocket, client_id: str):
        """断开WebSocket连接"""
        try:
            if client_id in self.connections:
                if websocket in self.connections[client_id]:
                    self.connections[client_id].remove(websocket)
                
                if not self.connections[client_id]:
                    del self.connections[client_id]
            
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]
            
            self.logger.info(f"WebSocket disconnected: {client_id}")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting WebSocket: {e}")
    
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        """发送消息给特定客户端"""
        if client_id in self.connections:
            disconnected = []
            
            for websocket in self.connections[client_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(websocket)
            
            # 清理断开的连接
            for websocket in disconnected:
                await self.disconnect(websocket, client_id)
    
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[List[str]] = None):
        """广播消息给所有客户端"""
        exclude = exclude or []
        
        for client_id in list(self.connections.keys()):
            if client_id not in exclude:
                await self.send_message(client_id, message)
    
    def get_connected_clients(self) -> List[str]:
        """获取已连接的客户端列表"""
        return list(self.connections.keys())
    
    def get_connection_count(self) -> int:
        """获取连接总数"""
        return sum(len(connections) for connections in self.connections.values())


class WebSocketHandler:
    """WebSocket处理器"""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.logger = logging.getLogger(f"api.websocket.{endpoint}")
        self.manager = WebSocketManager()
        self.message_handlers: Dict[str, callable] = {}
    
    def register_message_handler(self, message_type: str, handler: callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        self.logger.info(f"Registered message handler for type: {message_type}")
    
    async def handle_connection(self, websocket: WebSocket, client_id: str):
        """处理WebSocket连接"""
        try:
            await self.manager.connect(websocket, client_id)
            
            # 发送连接确认
            await self.manager.send_message(client_id, {
                "type": "connection_confirmed",
                "client_id": client_id,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # 监听消息
            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    await self._handle_message(client_id, message)
                    
                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await self.manager.send_message(client_id, {
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")
                    await self.manager.send_message(client_id, {
                        "type": "error",
                        "message": "Internal server error"
                    })
        
        except Exception as e:
            self.logger.error(f"Error in WebSocket connection: {e}")
        
        finally:
            await self.manager.disconnect(websocket, client_id)
    
    async def _handle_message(self, client_id: str, message: Dict[str, Any]):
        """处理接收到的消息"""
        try:
            message_type = message.get("type")
            
            if not message_type:
                await self.manager.send_message(client_id, {
                    "type": "error",
                    "message": "Message type is required"
                })
                return
            
            # 查找对应的处理器
            handler = self.message_handlers.get(message_type)
            
            if handler:
                # 调用处理器
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(client_id, message)
                else:
                    result = handler(client_id, message)
                
                # 发送响应
                if result:
                    await self.manager.send_message(client_id, result)
            else:
                await self.manager.send_message(client_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
        
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
            await self.manager.send_message(client_id, {
                "type": "error",
                "message": "Failed to process message"
            })
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """发送消息给特定客户端"""
        await self.manager.send_message(client_id, message)
    
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[List[str]] = None):
        """广播消息"""
        await self.manager.broadcast(message, exclude)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "endpoint": self.endpoint,
            "connected_clients": self.manager.get_connected_clients(),
            "connection_count": self.manager.get_connection_count(),
            "message_handlers": list(self.message_handlers.keys())
        }


# 全局WebSocket管理器
global_websocket_managers: Dict[str, WebSocketHandler] = {}


def get_websocket_handler(endpoint: str) -> WebSocketHandler:
    """获取WebSocket处理器"""
    if endpoint not in global_websocket_managers:
        global_websocket_managers[endpoint] = WebSocketHandler(endpoint)
    
    return global_websocket_managers[endpoint]


def register_websocket_endpoint(endpoint: str) -> WebSocketHandler:
    """注册WebSocket端点"""
    return get_websocket_handler(endpoint)