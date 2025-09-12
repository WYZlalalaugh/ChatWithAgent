"""
API路由管理器
"""

import logging
from typing import Any, Dict, List, Optional, Callable
from fastapi import APIRouter as FastAPIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from security.middleware import get_jwt_bearer
from security.permissions import get_permission_manager


class APIRouter:
    """API路由管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger("api.router")
        
        # 版本路由
        self._version_routers: Dict[str, FastAPIRouter] = {}
        
        # 权限管理
        self.permission_manager = get_permission_manager()
        self.jwt_bearer = get_jwt_bearer()
    
    def create_version_router(self, version: str) -> FastAPIRouter:
        """创建版本路由"""
        if version not in self._version_routers:
            router = FastAPIRouter()
            self._version_routers[version] = router
            self.logger.info(f"Created API router for version: {version}")
        
        return self._version_routers[version]
    
    def get_version_router(self, version: str) -> Optional[FastAPIRouter]:
        """获取版本路由"""
        return self._version_routers.get(version)
    
    def create_protected_route(
        self,
        router: FastAPIRouter,
        path: str,
        methods: List[str],
        handler: Callable,
        permission: Optional[str] = None,
        **kwargs
    ):
        """创建受保护的路由"""
        async def protected_handler(*args, **handler_kwargs):
            # 从依赖注入中获取认证信息
            token = handler_kwargs.get('token')
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # 检查权限
            if permission:
                # 这里需要从token中提取用户信息并检查权限
                # 简化实现
                pass
            
            # 执行原始处理器
            return await handler(*args, **handler_kwargs)
        
        # 添加JWT依赖
        dependencies = kwargs.get('dependencies', [])
        dependencies.append(Depends(self.jwt_bearer))
        kwargs['dependencies'] = dependencies
        
        # 注册路由
        for method in methods:
            if method.upper() == "GET":
                router.get(path, **kwargs)(protected_handler)
            elif method.upper() == "POST":
                router.post(path, **kwargs)(protected_handler)
            elif method.upper() == "PUT":
                router.put(path, **kwargs)(protected_handler)
            elif method.upper() == "DELETE":
                router.delete(path, **kwargs)(protected_handler)
            elif method.upper() == "PATCH":
                router.patch(path, **kwargs)(protected_handler)
    
    def create_public_route(
        self,
        router: FastAPIRouter,
        path: str,
        methods: List[str],
        handler: Callable,
        **kwargs
    ):
        """创建公开路由"""
        for method in methods:
            if method.upper() == "GET":
                router.get(path, **kwargs)(handler)
            elif method.upper() == "POST":
                router.post(path, **kwargs)(handler)
            elif method.upper() == "PUT":
                router.put(path, **kwargs)(handler)
            elif method.upper() == "DELETE":
                router.delete(path, **kwargs)(handler)
            elif method.upper() == "PATCH":
                router.patch(path, **kwargs)(handler)
    
    def get_route_statistics(self) -> Dict[str, Any]:
        """获取路由统计"""
        stats = {}
        
        for version, router in self._version_routers.items():
            route_count = len(router.routes)
            stats[version] = {
                "route_count": route_count,
                "routes": [
                    {
                        "path": route.path,
                        "methods": list(route.methods) if hasattr(route, 'methods') else [],
                        "name": route.name if hasattr(route, 'name') else ""
                    }
                    for route in router.routes
                ]
            }
        
        return stats


# 权限验证依赖
async def verify_permission(required_permission: str):
    """权限验证依赖工厂"""
    async def permission_checker(token: str = Depends(get_jwt_bearer())):
        # 这里应该验证token并检查权限
        # 简化实现
        return True
    
    return permission_checker


# 分页参数依赖
class PaginationParams:
    """分页参数"""
    def __init__(self, page: int = 1, size: int = 20, max_size: int = 100):
        self.page = max(1, page)
        self.size = max(1, min(size, max_size))
        self.offset = (self.page - 1) * self.size


def get_pagination_params(
    page: int = 1,
    size: int = 20
) -> PaginationParams:
    """获取分页参数"""
    return PaginationParams(page, size)


# 响应模型
class APIResponse:
    """API响应基类"""
    
    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """成功响应"""
        return {
            "success": True,
            "message": message,
            "data": data
        }
    
    @staticmethod
    def error(message: str = "Error", code: int = 500, data: Any = None) -> Dict[str, Any]:
        """错误响应"""
        return {
            "success": False,
            "message": message,
            "code": code,
            "data": data
        }
    
    @staticmethod
    def paginated(
        items: List[Any],
        total: int,
        page: int,
        size: int,
        message: str = "Success"
    ) -> Dict[str, Any]:
        """分页响应"""
        return {
            "success": True,
            "message": message,
            "data": {
                "items": items,
                "pagination": {
                    "total": total,
                    "page": page,
                    "size": size,
                    "pages": (total + size - 1) // size
                }
            }
        }