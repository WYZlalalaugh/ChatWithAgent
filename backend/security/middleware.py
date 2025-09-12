"""
安全中间件
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import get_auth_service, get_authz_service
from .rate_limiter import get_rate_limiter, RateLimitConfig
from .content_filter import get_content_filter
from .audit import get_audit_logger, AuditLevel, AuditCategory
from .permissions import get_permission_manager
from app.config import settings


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.logger = logging.getLogger("security.middleware")
        
        # 安全组件
        self.auth_service = get_auth_service()
        self.authz_service = get_authz_service()
        self.permission_manager = get_permission_manager()
        
        # 配置
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        
        # 豁免路径（不需要认证的路径）
        self.exempt_paths = {
            "/docs", "/openapi.json", "/redoc",
            "/health", "/metrics", "/favicon.ico",
            "/auth/login", "/auth/register"
        }
        
        # 公开API路径（不需要认证但需要限流）
        self.public_api_paths = {
            "/api/v1/public"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        start_time = time.time()
        request_id = f"req_{int(start_time * 1000)}"
        
        # 设置请求ID
        request.state.request_id = request_id
        
        try:
            # 安全检查
            security_result = await self._security_check(request)
            if security_result:
                return security_result
            
            # 执行请求
            response = await call_next(request)
            
            # 添加安全响应头
            self._add_security_headers(response)
            
            # 记录审计日志
            await self._log_request(request, response, start_time)
            
            return response
            
        except HTTPException as e:
            # 记录HTTP异常
            await self._log_security_event(
                request, "http_exception", 
                {"status_code": e.status_code, "detail": e.detail}
            )
            raise
        except Exception as e:
            # 记录未处理异常
            await self._log_security_event(
                request, "unhandled_exception",
                {"error": str(e)}
            )
            raise
    
    async def _security_check(self, request: Request) -> Optional[Response]:
        """安全检查"""
        try:
            path = request.url.path
            method = request.method
            
            # 检查是否为豁免路径
            if any(path.startswith(exempt) for exempt in self.exempt_paths):
                return None
            
            # IP封锁检查
            client_ip = self._get_client_ip(request)
            if await self._is_ip_blocked(client_ip):
                await self._log_security_event(
                    request, "ip_blocked", {"ip": client_ip}
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="IP address is blocked"
                )
            
            # 限流检查
            rate_limit_result = await self._check_rate_limit(request)
            if not rate_limit_result.allowed:
                await self._log_security_event(
                    request, "rate_limit_exceeded", 
                    {"ip": client_ip, "retry_after": rate_limit_result.retry_after}
                )
                
                response = Response(
                    content="Rate limit exceeded",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS
                )
                response.headers["Retry-After"] = str(rate_limit_result.retry_after or 60)
                response.headers["X-RateLimit-Limit"] = str(rate_limit_result.limit)
                response.headers["X-RateLimit-Remaining"] = str(rate_limit_result.remaining)
                response.headers["X-RateLimit-Reset"] = str(rate_limit_result.reset_time)
                return response
            
            # 认证检查
            if not any(path.startswith(public) for public in self.public_api_paths):
                auth_result = await self._authenticate_request(request)
                if not auth_result:
                    await self._log_security_event(
                        request, "authentication_failed", {"path": path}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
                
                # 设置用户信息
                request.state.user = auth_result
                
                # 权限检查
                if not await self._authorize_request(request, auth_result):
                    await self._log_security_event(
                        request, "authorization_failed",
                        {"user_id": auth_result.user_id, "path": path}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions"
                    )
            
            return None
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Security check error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Security check failed"
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _is_ip_blocked(self, ip: str) -> bool:
        """检查IP是否被封锁"""
        # 这里可以实现IP黑名单检查
        # 暂时返回False
        return False
    
    async def _check_rate_limit(self, request: Request):
        """检查限流"""
        try:
            rate_limiter = await get_rate_limiter()
            
            # 生成限流键
            client_ip = self._get_client_ip(request)
            path = request.url.path
            method = request.method
            
            # 不同路径使用不同的限流配置
            if path.startswith("/api/"):
                config = RateLimitConfig(limit=1000, window=3600)  # API: 每小时1000次
                key = f"api_rate_limit:{client_ip}"
            elif path.startswith("/auth/"):
                config = RateLimitConfig(limit=10, window=300)  # 认证: 5分钟10次
                key = f"auth_rate_limit:{client_ip}"
            else:
                config = RateLimitConfig(limit=500, window=3600)  # 默认: 每小时500次
                key = f"general_rate_limit:{client_ip}"
            
            return await rate_limiter.check_rate_limit(key, config)
            
        except Exception as e:
            self.logger.error(f"Rate limit check error: {e}")
            # 出错时允许通过
            return type('RateLimitResult', (), {
                'allowed': True,
                'limit': 1000,
                'remaining': 1000,
                'reset_time': int(time.time() + 3600)
            })()
    
    async def _authenticate_request(self, request: Request):
        """认证请求"""
        try:
            # 从Authorization头获取令牌
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return None
            
            token = authorization[7:]  # 移除"Bearer "前缀
            
            # 验证令牌
            auth_token = await self.auth_service.verify_token(token)
            if not auth_token:
                return None
            
            return auth_token
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return None
    
    async def _authorize_request(self, request: Request, auth_token) -> bool:
        """授权请求"""
        try:
            path = request.url.path
            method = request.method
            
            # 生成所需权限
            required_permission = self._get_required_permission(path, method)
            if not required_permission:
                return True  # 不需要特定权限
            
            # 检查权限
            return await self.authz_service.check_permission(
                auth_token.permissions,
                required_permission
            )
            
        except Exception as e:
            self.logger.error(f"Authorization error: {e}")
            return False
    
    def _get_required_permission(self, path: str, method: str) -> Optional[str]:
        """获取所需权限"""
        # 简化的权限映射
        if path.startswith("/api/v1/users"):
            if method == "GET":
                return "user.read"
            elif method in ("POST", "PUT", "PATCH"):
                return "user.write"
            elif method == "DELETE":
                return "user.delete"
        elif path.startswith("/api/v1/bots"):
            if method == "GET":
                return "bot.read"
            elif method in ("POST", "PUT", "PATCH"):
                return "bot.write"
            elif method == "DELETE":
                return "bot.delete"
        elif path.startswith("/api/v1/admin"):
            return "system.admin"
        
        # 默认需要读权限
        return "api.read"
    
    def _add_security_headers(self, response: Response):
        """添加安全响应头"""
        for header, value in self.security_headers.items():
            response.headers[header] = value
    
    async def _log_request(self, request: Request, response: Response, start_time: float):
        """记录请求审计日志"""
        try:
            audit_logger = await get_audit_logger()
            
            user_id = getattr(request.state, 'user', None)
            if user_id and hasattr(user_id, 'user_id'):
                user_id = user_id.user_id
            else:
                user_id = None
            
            duration = time.time() - start_time
            
            await audit_logger.log_event(
                level=AuditLevel.INFO,
                category=AuditCategory.API_CALL,
                action=f"{request.method} {request.url.path}",
                user_id=user_id,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent"),
                request_id=getattr(request.state, 'request_id', None),
                details={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "status_code": response.status_code,
                    "duration": duration
                },
                result="success" if 200 <= response.status_code < 400 else "error"
            )
            
        except Exception as e:
            self.logger.error(f"Audit logging error: {e}")
    
    async def _log_security_event(
        self,
        request: Request,
        event_type: str,
        details: Dict[str, Any]
    ):
        """记录安全事件"""
        try:
            audit_logger = await get_audit_logger()
            
            await audit_logger.log_event(
                level=AuditLevel.WARNING,
                category=AuditCategory.SECURITY_VIOLATION,
                action=event_type,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent"),
                request_id=getattr(request.state, 'request_id', None),
                details=details,
                result="violation"
            )
            
        except Exception as e:
            self.logger.error(f"Security event logging error: {e}")


class ContentFilterMiddleware(BaseHTTPMiddleware):
    """内容过滤中间件"""
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.logger = logging.getLogger("security.content_filter")
        self.content_filter = get_content_filter()
        
        # 需要过滤的路径
        self.filter_paths = {
            "/api/v1/messages", "/api/v1/conversations",
            "/api/v1/knowledge", "/api/v1/chat"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        try:
            # 检查是否需要内容过滤
            if not settings.CONTENT_FILTER_ENABLED:
                return await call_next(request)
            
            path = request.url.path
            method = request.method
            
            # 只对POST/PUT请求进行内容过滤
            if method not in ("POST", "PUT", "PATCH"):
                return await call_next(request)
            
            # 检查路径
            if not any(path.startswith(filter_path) for filter_path in self.filter_paths):
                return await call_next(request)
            
            # 读取请求体
            body = await request.body()
            if not body:
                return await call_next(request)
            
            # 解析JSON内容
            try:
                import json
                content_data = json.loads(body.decode())
            except:
                # 非JSON内容，跳过过滤
                return await call_next(request)
            
            # 过滤内容
            filtered_data = await self._filter_content(content_data, request)
            
            # 重新构建请求
            if filtered_data != content_data:
                filtered_body = json.dumps(filtered_data).encode()
                
                # 创建新的请求对象
                scope = request.scope.copy()
                scope["body"] = filtered_body
                
                # 更新Content-Length
                scope["headers"] = [
                    (name, value) for name, value in scope["headers"]
                    if name != b"content-length"
                ]
                scope["headers"].append((b"content-length", str(len(filtered_body)).encode()))
                
                # 创建新请求
                from starlette.requests import Request as StarletteRequest
                new_request = StarletteRequest(scope)
                return await call_next(new_request)
            
            return await call_next(request)
            
        except Exception as e:
            self.logger.error(f"Content filter error: {e}")
            return await call_next(request)
    
    async def _filter_content(self, data: Dict[str, Any], request: Request) -> Dict[str, Any]:
        """过滤内容"""
        try:
            filtered_data = data.copy()
            
            # 需要过滤的字段
            filter_fields = ["content", "message", "text", "body", "description"]
            
            for field in filter_fields:
                if field in filtered_data and isinstance(filtered_data[field], str):
                    text = filtered_data[field]
                    
                    # 分析内容
                    analysis = await self.content_filter.analyze_content(text, {
                        "user_id": getattr(request.state, 'user', {}).get('user_id'),
                        "timestamp": time.time(),
                        "ip_address": self._get_client_ip(request)
                    })
                    
                    filter_result = analysis["filter_result"]
                    
                    # 检查是否需要阻止
                    if filter_result.is_blocked or analysis["final_risk_score"] >= settings.CONTENT_RISK_THRESHOLD:
                        await self._log_content_violation(request, text, analysis)
                        
                        if settings.AUTO_BLOCK_HIGH_RISK_CONTENT:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Content violates community guidelines"
                            )
                    
                    # 使用过滤后的文本
                    filtered_data[field] = filter_result.filtered_text
            
            return filtered_data
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Content filtering error: {e}")
            return data
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _log_content_violation(
        self,
        request: Request,
        content: str,
        analysis: Dict[str, Any]
    ):
        """记录内容违规"""
        try:
            audit_logger = await get_audit_logger()
            
            user_id = getattr(request.state, 'user', None)
            if user_id and hasattr(user_id, 'user_id'):
                user_id = user_id.user_id
            else:
                user_id = None
            
            await audit_logger.log_event(
                level=AuditLevel.WARNING,
                category=AuditCategory.SECURITY_VIOLATION,
                action="content_violation",
                user_id=user_id,
                ip_address=self._get_client_ip(request),
                details={
                    "content_length": len(content),
                    "risk_score": analysis["final_risk_score"],
                    "violations": analysis["filter_result"].violations,
                    "path": request.url.path
                },
                result="violation"
            )
            
        except Exception as e:
            self.logger.error(f"Content violation logging error: {e}")


# JWT Bearer认证方案
class JWTBearer(HTTPBearer):
    """JWT Bearer认证"""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.auth_service = get_auth_service()
    
    async def __call__(self, request: Request) -> Optional[str]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if credentials:
            if not credentials.scheme == "Bearer":
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid authentication scheme"
                    )
                return None
            
            if not await self._verify_jwt(credentials.credentials):
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid token or expired token"
                    )
                return None
            
            return credentials.credentials
        
        if self.auto_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        return None
    
    async def _verify_jwt(self, token: str) -> bool:
        """验证JWT令牌"""
        try:
            auth_token = await self.auth_service.verify_token(token)
            return auth_token is not None
        except:
            return False


# 全局JWT认证实例
jwt_bearer = JWTBearer()


def get_jwt_bearer() -> JWTBearer:
    """获取JWT认证实例"""
    return jwt_bearer