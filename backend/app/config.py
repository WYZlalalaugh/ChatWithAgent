"""
应用配置管理模块
"""

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # 基础配置
    APP_NAME: str = "ChatBot Platform"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 服务配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False
    
    # 安全配置
    SECRET_KEY: str = Field(..., description="JWT 密钥")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # 数据库配置
    DATABASE_URL: str = Field(..., description="数据库连接 URL")
    REDIS_URL: str = Field(..., description="Redis 连接 URL")
    
    # AI 模型配置
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_VERSION: str = "2023-12-01-preview"
    
    # 向量数据库配置
    VECTOR_STORE_TYPE: str = "chroma"  # chroma, qdrant, faiss, pinecone
    VECTOR_STORE_PATH: str = "./data/vector_store"
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    
    # 文件存储配置
    UPLOAD_PATH: str = "./data/uploads"
    MAX_UPLOAD_SIZE: int = 100  # MB
    ALLOWED_EXTENSIONS: List[str] = [
        "jpg", "jpeg", "png", "gif", "pdf", "docx", "txt", "md"
    ]
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"
    
    # 跨域配置
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ]
    
    # 限流配置
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10
    
    # 平台配置
    QQ_BOT_TOKEN: Optional[str] = None
    QQ_BOT_SECRET: Optional[str] = None
    WECHAT_BOT_CONFIG: Optional[str] = None
    FEISHU_APP_ID: Optional[str] = None
    FEISHU_APP_SECRET: Optional[str] = None
    DINGTALK_APP_KEY: Optional[str] = None
    DINGTALK_APP_SECRET: Optional[str] = None
    
    # 插件配置
    PLUGIN_PATH: str = "./plugins"
    PLUGIN_AUTO_LOAD: bool = True
    
    # MCP 配置
    MCP_SERVER_PORT: int = 8001
    MCP_TOOLS_PATH: str = "./tools"
    
    # 向量数据库配置
    DEFAULT_VECTOR_STORE: str = "chroma"  # chroma, faiss, qdrant, pinecone
    EMBEDDING_DIMENSION: int = 1536  # OpenAI text-embedding-ada-002 维度
    
    # Chroma 配置
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    
    # FAISS 配置
    FAISS_INDEX_TYPE: str = "IVFFlat"
    FAISS_NLIST: int = 100
    FAISS_PERSIST_DIRECTORY: str = "./data/faiss"
    FAISS_METRIC_TYPE: str = "IP"  # IP or L2
    
    # Qdrant 配置
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_URL: Optional[str] = None  # 云端服务URL
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_DISTANCE_METRIC: str = "Cosine"
    
    # Pinecone 配置
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: str = "us-west1-gcp"
    PINECONE_METRIC: str = "cosine"
    PINECONE_CLOUD: str = "gcp"
    PINECONE_REGION: str = "us-west1"
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    MASTER_KEY: Optional[str] = None  # 加密主密钥
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 1
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # 密码策略
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    # 会话管理
    MAX_CONCURRENT_SESSIONS: int = 5
    SESSION_TIMEOUT_MINUTES: int = 30
    
    # 审计日志
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_LEVEL: str = "INFO"
    AUDIT_LOG_RETENTION_DAYS: int = 30
    
    # 内容过滤
    CONTENT_FILTER_ENABLED: bool = True
    SENSITIVE_WORD_FILTER_ENABLED: bool = True
    AUTO_BLOCK_HIGH_RISK_CONTENT: bool = True
    CONTENT_RISK_THRESHOLD: int = 80
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取应用配置（单例模式）"""
    return Settings()


# 全局配置实例
settings = get_settings()