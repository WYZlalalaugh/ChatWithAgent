"""
审计日志服务
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as redis

from app.config import settings


class AuditLevel(str, Enum):
    """审计级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditCategory(str, Enum):
    """审计类别"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_OPERATION = "system_operation"
    SECURITY_VIOLATION = "security_violation"
    API_CALL = "api_call"
    USER_ACTION = "user_action"


@dataclass
class AuditEvent:
    """审计事件"""
    timestamp: datetime
    level: AuditLevel
    category: AuditCategory
    action: str
    user_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    result: Optional[str] = None  # success, failure, error
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.logger = logging.getLogger("security.audit")
        self.redis_client = redis_client
        
        # 内存缓存（当Redis不可用时）
        self.memory_cache: List[AuditEvent] = []
        self.max_memory_cache = 1000
        
        # 审计配置
        self.enabled_categories = set(AuditCategory)
        self.min_level = AuditLevel.INFO
        
        # 敏感字段（记录时需要脱敏）
        self.sensitive_fields = {
            'password', 'token', 'secret', 'key', 'api_key',
            'access_token', 'refresh_token', 'private_key'
        }
    
    async def log_event(
        self,
        level: AuditLevel,
        category: AuditCategory,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
        **kwargs
    ):
        """记录审计事件"""
        try:
            # 检查是否启用该类别
            if category not in self.enabled_categories:
                return
            
            # 检查日志级别
            if not self._should_log_level(level):
                return
            
            # 创建审计事件
            event = AuditEvent(
                timestamp=datetime.utcnow(),
                level=level,
                category=category,
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                details=self._sanitize_details(details or {}),
                result=result,
                error_message=error_message,
                **kwargs
            )
            
            # 记录到存储
            await self._store_event(event)
            
            # 记录到日志文件
            self._log_to_file(event)
            
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
    
    def _should_log_level(self, level: AuditLevel) -> bool:
        """检查是否应该记录该级别"""
        level_order = {
            AuditLevel.DEBUG: 0,
            AuditLevel.INFO: 1,
            AuditLevel.WARNING: 2,
            AuditLevel.ERROR: 3,
            AuditLevel.CRITICAL: 4
        }
        return level_order[level] >= level_order[self.min_level]
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏详细信息"""
        sanitized = {}
        
        for key, value in details.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                # 脱敏敏感字段
                if isinstance(value, str) and len(value) > 4:
                    sanitized[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
                else:
                    sanitized[key] = "***"
            else:
                sanitized[key] = value
        
        return sanitized
    
    async def _store_event(self, event: AuditEvent):
        """存储事件"""
        try:
            if self.redis_client:
                await self._store_to_redis(event)
            else:
                await self._store_to_memory(event)
        except Exception as e:
            self.logger.error(f"Failed to store audit event: {e}")
            # 降级到内存存储
            await self._store_to_memory(event)
    
    async def _store_to_redis(self, event: AuditEvent):
        """存储到Redis"""
        try:
            # 按日期分区存储
            date_key = event.timestamp.strftime("%Y-%m-%d")
            redis_key = f"audit_log:{date_key}"
            
            # 存储事件
            await self.redis_client.lpush(redis_key, event.to_json())
            
            # 设置过期时间（保留30天）
            await self.redis_client.expire(redis_key, 30 * 24 * 3600)
            
            # 存储索引（用于快速查询）
            await self._store_indexes(event)
            
        except Exception as e:
            self.logger.error(f"Redis storage failed: {e}")
            raise
    
    async def _store_indexes(self, event: AuditEvent):
        """存储索引"""
        try:
            timestamp = event.timestamp.timestamp()
            
            # 用户索引
            if event.user_id:
                user_key = f"audit_user:{event.user_id}"
                await self.redis_client.zadd(user_key, {event.to_json(): timestamp})
                await self.redis_client.expire(user_key, 30 * 24 * 3600)
            
            # 类别索引
            category_key = f"audit_category:{event.category.value}"
            await self.redis_client.zadd(category_key, {event.to_json(): timestamp})
            await self.redis_client.expire(category_key, 30 * 24 * 3600)
            
            # 资源索引
            if event.resource_type and event.resource_id:
                resource_key = f"audit_resource:{event.resource_type}:{event.resource_id}"
                await self.redis_client.zadd(resource_key, {event.to_json(): timestamp})
                await self.redis_client.expire(resource_key, 30 * 24 * 3600)
                
        except Exception as e:
            self.logger.error(f"Index storage failed: {e}")
    
    async def _store_to_memory(self, event: AuditEvent):
        """存储到内存"""
        self.memory_cache.append(event)
        
        # 限制内存缓存大小
        if len(self.memory_cache) > self.max_memory_cache:
            self.memory_cache.pop(0)
    
    def _log_to_file(self, event: AuditEvent):
        """记录到日志文件"""
        try:
            log_message = (
                f"AUDIT - {event.level.value.upper()} - "
                f"{event.category.value} - {event.action} - "
                f"User: {event.user_id or 'N/A'} - "
                f"Resource: {event.resource_type or 'N/A'}:{event.resource_id or 'N/A'} - "
                f"Result: {event.result or 'N/A'}"
            )
            
            if event.error_message:
                log_message += f" - Error: {event.error_message}"
            
            # 根据级别选择日志方法
            if event.level == AuditLevel.DEBUG:
                self.logger.debug(log_message)
            elif event.level == AuditLevel.INFO:
                self.logger.info(log_message)
            elif event.level == AuditLevel.WARNING:
                self.logger.warning(log_message)
            elif event.level == AuditLevel.ERROR:
                self.logger.error(log_message)
            elif event.level == AuditLevel.CRITICAL:
                self.logger.critical(log_message)
                
        except Exception as e:
            self.logger.error(f"File logging failed: {e}")
    
    async def query_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        category: Optional[AuditCategory] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """查询审计事件"""
        try:
            if self.redis_client:
                return await self._query_from_redis(
                    start_time, end_time, user_id, category,
                    resource_type, resource_id, limit
                )
            else:
                return await self._query_from_memory(
                    start_time, end_time, user_id, category,
                    resource_type, resource_id, limit
                )
        except Exception as e:
            self.logger.error(f"Query events failed: {e}")
            return []
    
    async def _query_from_redis(
        self,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        user_id: Optional[str],
        category: Optional[AuditCategory],
        resource_type: Optional[str],
        resource_id: Optional[str],
        limit: int
    ) -> List[AuditEvent]:
        """从Redis查询"""
        try:
            events = []
            
            if user_id:
                # 从用户索引查询
                key = f"audit_user:{user_id}"
                start_score = start_time.timestamp() if start_time else 0
                end_score = end_time.timestamp() if end_time else float('inf')
                
                results = await self.redis_client.zrangebyscore(
                    key, start_score, end_score, withscores=False
                )
                
                for result in results[:limit]:
                    try:
                        event_data = json.loads(result)
                        event_data['timestamp'] = datetime.fromisoformat(event_data['timestamp'])
                        events.append(AuditEvent(**event_data))
                    except:
                        continue
            
            elif category:
                # 从类别索引查询
                key = f"audit_category:{category.value}"
                start_score = start_time.timestamp() if start_time else 0
                end_score = end_time.timestamp() if end_time else float('inf')
                
                results = await self.redis_client.zrangebyscore(
                    key, start_score, end_score, withscores=False
                )
                
                for result in results[:limit]:
                    try:
                        event_data = json.loads(result)
                        event_data['timestamp'] = datetime.fromisoformat(event_data['timestamp'])
                        events.append(AuditEvent(**event_data))
                    except:
                        continue
            
            else:
                # 从日期分区查询
                if not start_time:
                    start_time = datetime.utcnow().replace(hour=0, minute=0, second=0)
                if not end_time:
                    end_time = datetime.utcnow()
                
                current_date = start_time.date()
                end_date = end_time.date()
                
                while current_date <= end_date and len(events) < limit:
                    date_key = current_date.strftime("%Y-%m-%d")
                    redis_key = f"audit_log:{date_key}"
                    
                    results = await self.redis_client.lrange(redis_key, 0, limit - len(events))
                    
                    for result in results:
                        try:
                            event_data = json.loads(result)
                            event_data['timestamp'] = datetime.fromisoformat(event_data['timestamp'])
                            event = AuditEvent(**event_data)
                            
                            # 时间过滤
                            if start_time <= event.timestamp <= end_time:
                                events.append(event)
                        except:
                            continue
                    
                    current_date = current_date.replace(day=current_date.day + 1)
            
            return sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]
            
        except Exception as e:
            self.logger.error(f"Redis query failed: {e}")
            return []
    
    async def _query_from_memory(
        self,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        user_id: Optional[str],
        category: Optional[AuditCategory],
        resource_type: Optional[str],
        resource_id: Optional[str],
        limit: int
    ) -> List[AuditEvent]:
        """从内存查询"""
        filtered_events = []
        
        for event in self.memory_cache:
            # 时间过滤
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            
            # 用户过滤
            if user_id and event.user_id != user_id:
                continue
            
            # 类别过滤
            if category and event.category != category:
                continue
            
            # 资源过滤
            if resource_type and event.resource_type != resource_type:
                continue
            if resource_id and event.resource_id != resource_id:
                continue
            
            filtered_events.append(event)
        
        # 按时间排序并限制数量
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_events[:limit]
    
    async def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取审计统计"""
        try:
            if not start_time:
                start_time = datetime.utcnow().replace(hour=0, minute=0, second=0)
            if not end_time:
                end_time = datetime.utcnow()
            
            events = await self.query_events(
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
            
            stats = {
                "total_events": len(events),
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "by_level": {},
                "by_category": {},
                "by_result": {},
                "top_users": {},
                "top_actions": {}
            }
            
            # 按级别统计
            for event in events:
                level = event.level.value
                stats["by_level"][level] = stats["by_level"].get(level, 0) + 1
            
            # 按类别统计
            for event in events:
                category = event.category.value
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            
            # 按结果统计
            for event in events:
                result = event.result or "unknown"
                stats["by_result"][result] = stats["by_result"].get(result, 0) + 1
            
            # 用户统计
            for event in events:
                if event.user_id:
                    stats["top_users"][event.user_id] = stats["top_users"].get(event.user_id, 0) + 1
            
            # 动作统计
            for event in events:
                action = event.action
                stats["top_actions"][action] = stats["top_actions"].get(action, 0) + 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Statistics generation failed: {e}")
            return {}
    
    def set_enabled_categories(self, categories: List[AuditCategory]):
        """设置启用的审计类别"""
        self.enabled_categories = set(categories)
    
    def set_min_level(self, level: AuditLevel):
        """设置最小日志级别"""
        self.min_level = level
    
    # 便捷方法
    async def log_authentication(self, action: str, user_id: str, result: str, **kwargs):
        """记录认证事件"""
        await self.log_event(
            level=AuditLevel.INFO,
            category=AuditCategory.AUTHENTICATION,
            action=action,
            user_id=user_id,
            result=result,
            **kwargs
        )
    
    async def log_authorization(self, action: str, user_id: str, resource_type: str, result: str, **kwargs):
        """记录授权事件"""
        await self.log_event(
            level=AuditLevel.INFO,
            category=AuditCategory.AUTHORIZATION,
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            result=result,
            **kwargs
        )
    
    async def log_data_access(self, action: str, user_id: str, resource_type: str, resource_id: str, **kwargs):
        """记录数据访问事件"""
        await self.log_event(
            level=AuditLevel.INFO,
            category=AuditCategory.DATA_ACCESS,
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            result="success",
            **kwargs
        )
    
    async def log_security_violation(self, action: str, details: Dict[str, Any], **kwargs):
        """记录安全违规事件"""
        await self.log_event(
            level=AuditLevel.WARNING,
            category=AuditCategory.SECURITY_VIOLATION,
            action=action,
            details=details,
            result="violation",
            **kwargs
        )


# 全局审计日志器实例
audit_logger = None


async def get_audit_logger() -> AuditLogger:
    """获取审计日志器实例"""
    global audit_logger
    if audit_logger is None:
        try:
            # 尝试连接Redis
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=2,  # 使用专门的数据库
                decode_responses=False
            )
            await redis_client.ping()
            audit_logger = AuditLogger(redis_client)
        except:
            # Redis不可用时使用内存存储
            audit_logger = AuditLogger()
    
    return audit_logger