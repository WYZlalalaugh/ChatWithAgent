"""
API文档生成器
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html


class APIDocGenerator:
    """API文档生成器"""
    
    def __init__(self):
        self.logger = logging.getLogger("api.docs")
        
        # 自定义OpenAPI配置
        self.openapi_config = {
            "info": {
                "title": "ChatAgent API",
                "version": "1.0.0",
                "description": "开源大语言模型原生即时通信机器人开发平台 API 文档",
                "contact": {
                    "name": "ChatAgent Team",
                    "url": "https://github.com/chatagent/chatagent",
                    "email": "support@chatagent.com"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:8000",
                    "description": "本地开发环境"
                },
                {
                    "url": "https://api.chatagent.com",
                    "description": "生产环境"
                }
            ],
            "tags": [
                {
                    "name": "认证",
                    "description": "用户认证和授权相关接口"
                },
                {
                    "name": "用户管理",
                    "description": "用户信息管理接口"
                },
                {
                    "name": "机器人管理",
                    "description": "机器人创建、配置和管理接口"
                },
                {
                    "name": "对话管理",
                    "description": "对话会话管理接口"
                },
                {
                    "name": "消息管理",
                    "description": "消息发送和接收接口"
                },
                {
                    "name": "知识库管理",
                    "description": "知识库和文档管理接口"
                },
                {
                    "name": "插件管理",
                    "description": "插件安装、配置和管理接口"
                },
                {
                    "name": "系统管理",
                    "description": "系统配置和监控接口"
                },
                {
                    "name": "WebSocket",
                    "description": "实时通信WebSocket接口"
                }
            ]
        }
        
        # 通用响应示例
        self.common_responses = {
            "400": {
                "description": "请求参数错误",
                "content": {
                    "application/json": {
                        "example": {
                            "success": False,
                            "message": "Invalid request parameters",
                            "code": 400
                        }
                    }
                }
            },
            "401": {
                "description": "未授权访问",
                "content": {
                    "application/json": {
                        "example": {
                            "success": False,
                            "message": "Authentication required",
                            "code": 401
                        }
                    }
                }
            },
            "403": {
                "description": "权限不足",
                "content": {
                    "application/json": {
                        "example": {
                            "success": False,
                            "message": "Insufficient permissions",
                            "code": 403
                        }
                    }
                }
            },
            "404": {
                "description": "资源不存在",
                "content": {
                    "application/json": {
                        "example": {
                            "success": False,
                            "message": "Resource not found",
                            "code": 404
                        }
                    }
                }
            },
            "500": {
                "description": "服务器内部错误",
                "content": {
                    "application/json": {
                        "example": {
                            "success": False,
                            "message": "Internal server error",
                            "code": 500
                        }
                    }
                }
            }
        }
    
    def generate_openapi_schema(self, app: FastAPI) -> Dict[str, Any]:
        """生成OpenAPI规范"""
        try:
            # 获取基础OpenAPI规范
            openapi_schema = get_openapi(
                title=self.openapi_config["info"]["title"],
                version=self.openapi_config["info"]["version"],
                description=self.openapi_config["info"]["description"],
                routes=app.routes,
            )
            
            # 合并自定义配置
            openapi_schema.update(self.openapi_config)
            
            # 添加安全模式
            openapi_schema["components"] = openapi_schema.get("components", {})
            openapi_schema["components"]["securitySchemes"] = {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
            
            # 为需要认证的端点添加安全要求
            self._add_security_requirements(openapi_schema)
            
            # 添加通用响应
            self._add_common_responses(openapi_schema)
            
            return openapi_schema
            
        except Exception as e:
            self.logger.error(f"Error generating OpenAPI schema: {e}")
            return {}
    
    def _add_security_requirements(self, openapi_schema: Dict[str, Any]):
        """添加安全要求"""
        paths = openapi_schema.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    # 跳过公开端点
                    if (path.startswith("/auth/") or 
                        path in ["/health", "/docs", "/openapi.json"]):
                        continue
                    
                    # 添加安全要求
                    operation["security"] = [{"bearerAuth": []}]
    
    def _add_common_responses(self, openapi_schema: Dict[str, Any]):
        """添加通用响应"""
        paths = openapi_schema.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    responses = operation.get("responses", {})
                    
                    # 添加通用错误响应
                    for status_code, response in self.common_responses.items():
                        if status_code not in responses:
                            responses[status_code] = response
                    
                    operation["responses"] = responses
    
    def generate_swagger_ui(self, openapi_url: str) -> str:
        """生成Swagger UI HTML"""
        return get_swagger_ui_html(
            openapi_url=openapi_url,
            title="ChatAgent API 文档",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css",
            swagger_favicon_url="/static/favicon.ico"
        )
    
    def generate_redoc_ui(self, openapi_url: str) -> str:
        """生成ReDoc UI HTML"""
        return get_redoc_html(
            openapi_url=openapi_url,
            title="ChatAgent API 文档",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js",
            redoc_favicon_url="/static/favicon.ico"
        )
    
    def add_custom_tag(self, name: str, description: str, external_docs: Optional[Dict[str, str]] = None):
        """添加自定义标签"""
        tag = {
            "name": name,
            "description": description
        }
        
        if external_docs:
            tag["externalDocs"] = external_docs
        
        self.openapi_config["tags"].append(tag)
    
    def set_server(self, url: str, description: str):
        """设置服务器地址"""
        server = {
            "url": url,
            "description": description
        }
        
        # 检查是否已存在
        for i, existing_server in enumerate(self.openapi_config["servers"]):
            if existing_server["url"] == url:
                self.openapi_config["servers"][i] = server
                return
        
        # 添加新服务器
        self.openapi_config["servers"].append(server)
    
    def generate_api_examples(self) -> Dict[str, Any]:
        """生成API使用示例"""
        examples = {
            "authentication": {
                "title": "用户认证",
                "description": "获取访问令牌",
                "request": {
                    "method": "POST",
                    "url": "/api/v1/auth/login",
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": {
                        "username": "admin",
                        "password": "password123"
                    }
                },
                "response": {
                    "status": 200,
                    "body": {
                        "success": True,
                        "message": "Login successful",
                        "data": {
                            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                            "token_type": "bearer",
                            "expires_in": 3600
                        }
                    }
                }
            },
            "create_bot": {
                "title": "创建机器人",
                "description": "创建一个新的机器人",
                "request": {
                    "method": "POST",
                    "url": "/api/v1/bots",
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer your_access_token"
                    },
                    "body": {
                        "name": "客服机器人",
                        "description": "智能客服机器人",
                        "platform_type": "wechat",
                        "llm_config": {
                            "model_name": "gpt-3.5-turbo",
                            "temperature": 0.7,
                            "max_tokens": 1000
                        }
                    }
                },
                "response": {
                    "status": 201,
                    "body": {
                        "success": True,
                        "message": "Bot created successfully",
                        "data": {
                            "id": "bot_123456",
                            "name": "客服机器人",
                            "status": "inactive",
                            "created_at": "2024-01-01T00:00:00Z"
                        }
                    }
                }
            },
            "send_message": {
                "title": "发送消息",
                "description": "向机器人发送消息",
                "request": {
                    "method": "POST",
                    "url": "/api/v1/messages",
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer your_access_token"
                    },
                    "body": {
                        "bot_id": "bot_123456",
                        "conversation_id": "conv_789012",
                        "content": "你好，请问有什么可以帮助您的吗？",
                        "message_type": "text"
                    }
                },
                "response": {
                    "status": 201,
                    "body": {
                        "success": True,
                        "message": "Message sent successfully",
                        "data": {
                            "id": "msg_345678",
                            "content": "你好，请问有什么可以帮助您的吗？",
                            "timestamp": "2024-01-01T00:00:00Z"
                        }
                    }
                }
            }
        }
        
        return examples
    
    def export_postman_collection(self, openapi_schema: Dict[str, Any]) -> Dict[str, Any]:
        """导出Postman集合"""
        try:
            collection = {
                "info": {
                    "name": openapi_schema.get("info", {}).get("title", "API Collection"),
                    "description": openapi_schema.get("info", {}).get("description", ""),
                    "version": openapi_schema.get("info", {}).get("version", "1.0.0"),
                    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
                },
                "auth": {
                    "type": "bearer",
                    "bearer": [
                        {
                            "key": "token",
                            "value": "{{access_token}}",
                            "type": "string"
                        }
                    ]
                },
                "variable": [
                    {
                        "key": "base_url",
                        "value": "http://localhost:8000",
                        "type": "string"
                    },
                    {
                        "key": "access_token",
                        "value": "your_access_token_here",
                        "type": "string"
                    }
                ],
                "item": []
            }
            
            # 转换OpenAPI路径为Postman请求
            paths = openapi_schema.get("paths", {})
            
            for path, path_item in paths.items():
                for method, operation in path_item.items():
                    if method.lower() in ["get", "post", "put", "delete", "patch"]:
                        item = self._create_postman_item(path, method, operation)
                        collection["item"].append(item)
            
            return collection
            
        except Exception as e:
            self.logger.error(f"Error exporting Postman collection: {e}")
            return {}
    
    def _create_postman_item(self, path: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """创建Postman请求项"""
        item = {
            "name": operation.get("summary", f"{method.upper()} {path}"),
            "request": {
                "method": method.upper(),
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json",
                        "type": "text"
                    }
                ],
                "url": {
                    "raw": "{{base_url}}" + path,
                    "host": ["{{base_url}}"],
                    "path": path.strip("/").split("/")
                }
            },
            "response": []
        }
        
        # 添加请求体示例
        if method.lower() in ["post", "put", "patch"]:
            request_body = operation.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                json_content = content.get("application/json", {})
                example = json_content.get("example", {})
                
                if example:
                    item["request"]["body"] = {
                        "mode": "raw",
                        "raw": example,
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    }
        
        return item