"""
ChatBot Platform 主应用入口
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.database import init_db
from app.utils.logger import setup_logging

# 设置日志
setup_logging()

# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="开源大语言模型原生即时通信机器人开发平台",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# TODO: 注册 API 路由
# from app.api.v1 import api_router
# app.include_router(api_router, prefix=settings.API_V1_STR)

# TODO: 注册 WebSocket
# from app.api.websocket import websocket_router
# app.include_router(websocket_router, prefix="/ws")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    # 初始化数据库
    await init_db()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功!")
    print(f"📖 API 文档: http://{settings.API_HOST}:{settings.API_PORT}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    print("👋 应用正在关闭...")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": settings.API_V1_STR,
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "version": settings.APP_VERSION}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )