"""
API网关主入口
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import uvicorn

from .router import APIRouter
from .handlers import APIHandler
from .middleware import GatewayMiddleware
from .docs import APIDocGenerator
from security.middleware import SecurityMiddleware, ContentFilterMiddleware
from app.config import settings


class APIGateway:
    """API网关"""
    
    def __init__(
        self,
        title: str = "ChatAgent API Gateway",
        version: str = "1.0.0",
        description: str = "开源大语言模型原生即时通信机器人开发平台 API",
        host: str = "0.0.0.0",
        port: int = 8000
    ):
        self.logger = logging.getLogger("api.gateway")
        
        # 基本配置
        self.title = title
        self.version = version
        self.description = description
        self.host = host
        self.port = port
        
        # 创建FastAPI应用
        self.app = FastAPI(
            title=self.title,
            version=self.version,
            description=self.description,
            docs_url=None,  # 禁用默认文档，使用自定义文档
            redoc_url=None,
            openapi_url="/api/v1/openapi.json"
        )
        
        # 核心组件
        self.router = APIRouter()
        self.middleware = GatewayMiddleware()
        self.doc_generator = APIDocGenerator()
        
        # API处理器
        self.handlers: Dict[str, APIHandler] = {}
        
        # WebSocket连接管理
        self.websocket_connections: Dict[str, List[Any]] = {}
        
        # 初始化网关
        self._setup_middleware()
        self._setup_routes()
        self._setup_exception_handlers()
        
    def _setup_middleware(self):
        """设置中间件"""
        # CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境应该限制具体域名
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 安全中间件
        self.app.add_middleware(SecurityMiddleware)
        
        # 内容过滤中间件
        self.app.add_middleware(ContentFilterMiddleware)
        
        # 自定义网关中间件
        self.app.add_middleware(GatewayMiddleware)
    
    def _setup_routes(self):
        """设置路由"""
        # 健康检查
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "version": self.version}
        
        # API文档
        @self.app.get("/docs", include_in_schema=False)
        async def custom_swagger_ui_html():
            return get_swagger_ui_html(
                openapi_url="/api/v1/openapi.json",
                title=f"{self.title} - API文档",
                swagger_favicon_url="/static/favicon.ico"
            )
        
        # 自定义OpenAPI规范
        @self.app.get("/api/v1/openapi.json", include_in_schema=False)
        async def get_openapi_endpoint():
            return get_openapi(
                title=self.title,
                version=self.version,
                description=self.description,
                routes=self.app.routes,
            )
        
        # 注册API路由
        self._register_api_routes()
    
    def _register_api_routes(self):
        """注册API路由"""
        # v1 API路由
        v1_router = self.router.create_version_router("v1")
        
        # 认证相关路由
        from .v1.auth import router as auth_router
        v1_router.include_router(auth_router, prefix="/auth", tags=["认证"])
        
        # 用户管理路由
        from .v1.users import router as users_router
        v1_router.include_router(users_router, prefix="/users", tags=["用户管理"])
        
        # 机器人管理路由
        from .v1.bots import router as bots_router
        v1_router.include_router(bots_router, prefix="/bots", tags=["机器人管理"])
        
        # 对话管理路由
        from .v1.conversations import router as conversations_router
        v1_router.include_router(conversations_router, prefix="/conversations", tags=["对话管理"])
        
        # 消息管理路由
        from .v1.messages import router as messages_router
        v1_router.include_router(messages_router, prefix="/messages", tags=["消息管理"])
        
        # 知识库管理路由
        from .v1.knowledge import router as knowledge_router
        v1_router.include_router(knowledge_router, prefix="/knowledge", tags=["知识库管理"])
        
        # 插件管理路由
        from .v1.plugins import router as plugins_router
        v1_router.include_router(plugins_router, prefix="/plugins", tags=["插件管理"])
        
        # 系统管理路由
        from .v1.system import router as system_router
        v1_router.include_router(system_router, prefix="/system", tags=["系统管理"])
        
        # 多模态处理路由
        from .v1.multimodal import router as multimodal_router
        v1_router.include_router(multimodal_router, prefix="/multimodal", tags=["多模态处理"])
        
        # 监控与日志路由
        from .v1.monitoring import router as monitoring_router
        v1_router.include_router(monitoring_router, prefix="/monitoring", tags=["监控与日志"])
        
        # WebSocket路由
        from .v1.ws import router as websocket_router
        v1_router.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
        
        # 将v1路由添加到主应用
        self.app.include_router(v1_router, prefix="/api/v1")
    
    def _setup_exception_handlers(self):
        """设置异常处理器"""
        @self.app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            self.logger.error(f"Unhandled exception: {exc}", exc_info=True)
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred",
                    "request_id": getattr(request.state, 'request_id', None)
                }
            )
        
        @self.app.exception_handler(404)
        async def not_found_handler(request: Request, exc):
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Not found",
                    "message": f"The requested resource '{request.url.path}' was not found",
                    "request_id": getattr(request.state, 'request_id', None)
                }
            )
    
    def register_handler(self, name: str, handler: APIHandler):
        """注册API处理器"""
        self.handlers[name] = handler
        self.logger.info(f"Registered API handler: {name}")
    
    def unregister_handler(self, name: str):
        """注销API处理器"""
        if name in self.handlers:
            del self.handlers[name]
            self.logger.info(f"Unregistered API handler: {name}")
    
    def get_handler(self, name: str) -> Optional[APIHandler]:
        """获取API处理器"""
        return self.handlers.get(name)
    
    async def start(self):
        """启动API网关"""
        try:
            self.logger.info(f"Starting API Gateway on {self.host}:{self.port}")
            
            # 配置uvicorn
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=True,
                reload=False,  # 生产环境应设为False
                workers=1  # 多进程可能会有问题，建议使用异步
            )
            
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            self.logger.error(f"Failed to start API Gateway: {e}")
            raise
    
    async def stop(self):
        """停止API网关"""
        try:
            self.logger.info("Stopping API Gateway...")
            
            # 关闭所有WebSocket连接
            for connection_list in self.websocket_connections.values():
                for websocket in connection_list:
                    try:
                        await websocket.close()
                    except:
                        pass
            
            self.websocket_connections.clear()
            
            self.logger.info("API Gateway stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping API Gateway: {e}")
    
    def get_openapi_schema(self) -> Dict[str, Any]:
        """获取OpenAPI规范"""
        return get_openapi(
            title=self.title,
            version=self.version,
            description=self.description,
            routes=self.app.routes,
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取网关统计信息"""
        return {
            "title": self.title,
            "version": self.version,
            "handlers_count": len(self.handlers),
            "websocket_connections": {
                endpoint: len(connections)
                for endpoint, connections in self.websocket_connections.items()
            },
            "total_websocket_connections": sum(
                len(connections) for connections in self.websocket_connections.values()
            ),
            "routes_count": len(self.app.routes)
        }


# 全局API网关实例
global_api_gateway = None


def get_api_gateway() -> APIGateway:
    """获取全局API网关实例"""
    global global_api_gateway
    if global_api_gateway is None:
        global_api_gateway = APIGateway()
    return global_api_gateway


# 便捷函数
async def start_api_gateway(
    host: str = "0.0.0.0",
    port: int = 8000
):
    """启动API网关"""
    gateway = get_api_gateway()
    gateway.host = host
    gateway.port = port
    await gateway.start()


async def stop_api_gateway():
    """停止API网关"""
    gateway = get_api_gateway()
    await gateway.stop()