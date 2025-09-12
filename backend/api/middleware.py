"""
API网关中间件
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class GatewayMiddleware(BaseHTTPMiddleware):
    """网关中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("api.middleware")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 记录开始时间
        start_time = time.time()
        
        # 添加请求头
        response = await call_next(request)
        
        # 计算处理时间
        process_time = time.time() - start_time
        
        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-API-Version"] = "1.0.0"
        
        # 记录请求日志
        self._log_request(request, response, process_time)
        
        return response
    
    def _log_request(self, request: Request, response: Response, process_time: float):
        """记录请求日志"""
        try:
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("User-Agent", "Unknown")
            
            log_data = {
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "method": request.method,
                "url": str(request.url),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "status_code": response.status_code,
                "process_time": process_time
            }
            
            if response.status_code >= 400:
                self.logger.warning(f"Request failed: {log_data}")
            else:
                self.logger.info(f"Request completed: {log_data}")
                
        except Exception as e:
            self.logger.error(f"Error logging request: {e}")
    
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


class APIVersionMiddleware(BaseHTTPMiddleware):
    """API版本中间件"""
    
    def __init__(self, app, default_version: str = "v1"):
        super().__init__(app)
        self.default_version = default_version
        self.logger = logging.getLogger("api.version")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理API版本"""
        # 从URL路径提取版本
        path_parts = request.url.path.strip("/").split("/")
        
        if len(path_parts) >= 2 and path_parts[0] == "api":
            version = path_parts[1]
            request.state.api_version = version
        else:
            # 从请求头获取版本
            version = request.headers.get("API-Version", self.default_version)
            request.state.api_version = version
        
        # 验证版本
        if not self._is_valid_version(version):
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid API version",
                    "message": f"API version '{version}' is not supported",
                    "supported_versions": ["v1"]
                }
            )
        
        response = await call_next(request)
        response.headers["API-Version"] = version
        
        return response
    
    def _is_valid_version(self, version: str) -> bool:
        """验证API版本"""
        supported_versions = {"v1"}
        return version in supported_versions


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    def __init__(self, app, log_body: bool = False):
        super().__init__(app)
        self.log_body = log_body
        self.logger = logging.getLogger("api.request_logger")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """记录详细请求信息"""
        start_time = time.time()
        
        # 记录请求
        await self._log_request(request)
        
        # 处理请求
        response = await call_next(request)
        
        # 记录响应
        process_time = time.time() - start_time
        await self._log_response(request, response, process_time)
        
        return response
    
    async def _log_request(self, request: Request):
        """记录请求详情"""
        try:
            log_data = {
                "timestamp": time.time(),
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client": request.client.host if request.client else None,
                "query_params": dict(request.query_params)
            }
            
            # 记录请求体（如果启用）
            if self.log_body and request.method in ("POST", "PUT", "PATCH"):
                try:
                    body = await request.body()
                    if body:
                        log_data["body_size"] = len(body)
                        # 不记录实际内容，只记录大小（安全考虑）
                except:
                    pass
            
            self.logger.debug(f"Request: {log_data}")
            
        except Exception as e:
            self.logger.error(f"Error logging request: {e}")
    
    async def _log_response(self, request: Request, response: Response, process_time: float):
        """记录响应详情"""
        try:
            log_data = {
                "timestamp": time.time(),
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "process_time": process_time
            }
            
            self.logger.debug(f"Response: {log_data}")
            
        except Exception as e:
            self.logger.error(f"Error logging response: {e}")


class MetricsMiddleware(BaseHTTPMiddleware):
    """指标收集中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.metrics = {
            "request_count": 0,
            "error_count": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "status_codes": {},
            "endpoints": {}
        }
        self.logger = logging.getLogger("api.metrics")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """收集指标"""
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # 更新指标
        self._update_metrics(request, response, process_time)
        
        return response
    
    def _update_metrics(self, request: Request, response: Response, process_time: float):
        """更新指标数据"""
        try:
            # 基本计数
            self.metrics["request_count"] += 1
            
            if response.status_code >= 400:
                self.metrics["error_count"] += 1
            
            # 时间统计
            self.metrics["total_time"] += process_time
            self.metrics["avg_time"] = self.metrics["total_time"] / self.metrics["request_count"]
            
            # 状态码统计
            status_code = str(response.status_code)
            self.metrics["status_codes"][status_code] = self.metrics["status_codes"].get(status_code, 0) + 1
            
            # 端点统计
            endpoint = f"{request.method} {request.url.path}"
            if endpoint not in self.metrics["endpoints"]:
                self.metrics["endpoints"][endpoint] = {
                    "count": 0,
                    "total_time": 0.0,
                    "avg_time": 0.0,
                    "error_count": 0
                }
            
            endpoint_metrics = self.metrics["endpoints"][endpoint]
            endpoint_metrics["count"] += 1
            endpoint_metrics["total_time"] += process_time
            endpoint_metrics["avg_time"] = endpoint_metrics["total_time"] / endpoint_metrics["count"]
            
            if response.status_code >= 400:
                endpoint_metrics["error_count"] += 1
            
        except Exception as e:
            self.logger.error(f"Error updating metrics: {e}")
    
    def get_metrics(self) -> dict:
        """获取指标数据"""
        return self.metrics.copy()
    
    def reset_metrics(self):
        """重置指标数据"""
        self.metrics = {
            "request_count": 0,
            "error_count": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "status_codes": {},
            "endpoints": {}
        }