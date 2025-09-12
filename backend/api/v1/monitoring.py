"""
监控与日志API路由
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from ...security.auth import AuthManager
from ...models.database import User
from ...monitoring.metrics import metric_collector, alert_manager, AlertLevel
from ...monitoring.logging import log_manager, LogLevel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"])
security = HTTPBearer()


class MetricResponse(BaseModel):
    """指标响应模型"""
    name: str
    value: float
    type: str
    timestamp: str
    labels: Dict[str, str]


class MetricSummaryResponse(BaseModel):
    """指标摘要响应模型"""
    name: str
    labels: Dict[str, str]
    counter_value: Optional[float] = None
    gauge_value: Optional[float] = None
    histogram: Optional[Dict[str, float]] = None
    timer: Optional[Dict[str, float]] = None


class AlertResponse(BaseModel):
    """告警响应模型"""
    id: str
    name: str
    level: str
    message: str
    timestamp: str
    metric_name: str
    metric_value: float
    threshold: float
    resolved: bool
    resolved_at: Optional[str] = None


class LogEntryResponse(BaseModel):
    """日志条目响应模型"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: str
    function: str
    line_number: int
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    exception_info: Optional[str] = None


class AlertRuleRequest(BaseModel):
    """告警规则请求模型"""
    name: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    level: str = "WARNING"
    description: str = ""


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """获取当前用户依赖"""
    auth_manager = AuthManager()
    token = credentials.credentials
    user = await auth_manager.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """获取管理员用户依赖"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/metrics", response_model=List[MetricResponse])
async def get_metrics(
    name_filter: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user)
):
    """获取指标数据"""
    try:
        # 解析时间参数
        start_dt = None
        end_dt = None
        
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_time format. Use ISO format."
                )
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_time format. Use ISO format."
                )
        
        # 获取指标
        metrics = await metric_collector.get_metrics(
            name_filter=name_filter,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit
        )
        
        return [MetricResponse(**metric) for metric in metrics]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get metrics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics"
        )


@router.get("/metrics/{metric_name}/summary", response_model=MetricSummaryResponse)
async def get_metric_summary(
    metric_name: str,
    current_user: User = Depends(get_current_user)
):
    """获取指标摘要"""
    try:
        summary = await metric_collector.get_metric_summary(metric_name)
        return MetricSummaryResponse(**summary)
        
    except Exception as e:
        logger.error(f"Get metric summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metric summary"
        )


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user)
):
    """获取告警列表"""
    try:
        if active_only:
            alerts = alert_manager.get_active_alerts()
        else:
            alerts = alert_manager.get_all_alerts()
        
        return [AlertResponse(**alert) for alert in alerts]
        
    except Exception as e:
        logger.error(f"Get alerts error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get alerts"
        )


@router.post("/alert-rules")
async def create_alert_rule(
    rule: AlertRuleRequest,
    current_user: User = Depends(get_admin_user)
):
    """创建告警规则"""
    try:
        # 验证告警级别
        try:
            level = AlertLevel(rule.level.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid alert level: {rule.level}"
            )
        
        # 验证条件
        valid_conditions = ["gt", "lt", "eq", "gte", "lte"]
        if rule.condition not in valid_conditions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid condition: {rule.condition}. Must be one of {valid_conditions}"
            )
        
        # 添加告警规则
        alert_manager.add_rule(
            name=rule.name,
            metric_name=rule.metric_name,
            condition=rule.condition,
            threshold=rule.threshold,
            level=level,
            description=rule.description
        )
        
        return {"success": True, "message": "Alert rule created successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create alert rule error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create alert rule"
        )


@router.get("/logs", response_model=List[LogEntryResponse])
async def search_logs(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    logger_name: Optional[str] = Query(None),
    message_contains: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    request_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user)
):
    """搜索日志"""
    try:
        # 解析时间参数
        start_dt = None
        end_dt = None
        
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_time format. Use ISO format."
                )
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_time format. Use ISO format."
                )
        
        # 解析日志级别
        log_level = None
        if level:
            try:
                log_level = LogLevel(level.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid log level: {level}"
                )
        
        # 权限检查：非管理员只能查看自己的日志
        search_user_id = user_id
        if current_user.role != "admin":
            search_user_id = current_user.id
        
        # 搜索日志
        logs = await log_manager.search_logs(
            start_time=start_dt,
            end_time=end_dt,
            level=log_level,
            logger_name=logger_name,
            message_contains=message_contains,
            user_id=search_user_id,
            request_id=request_id,
            limit=limit
        )
        
        return [LogEntryResponse(**log) for log in logs]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search logs error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search logs"
        )


@router.get("/system")
async def get_system_metrics(
    current_user: User = Depends(get_current_user)
):
    """获取系统指标"""
    try:
        # 获取系统相关的指标摘要
        system_metrics = {}
        
        system_metric_names = [
            "system_cpu_percent",
            "system_memory_percent",
            "system_disk_percent",
            "process_cpu_percent",
            "process_memory_percent"
        ]
        
        for metric_name in system_metric_names:
            summary = await metric_collector.get_metric_summary(metric_name)
            if 'gauge_value' in summary:
                system_metrics[metric_name] = summary['gauge_value']
        
        # 获取应用指标
        app_metrics = {}
        app_metric_names = [
            "http_requests_total",
            "http_request_duration",
            "websocket_connections",
            "database_connections",
            "cache_hits",
            "cache_misses"
        ]
        
        for metric_name in app_metric_names:
            summary = await metric_collector.get_metric_summary(metric_name)
            if summary:
                app_metrics[metric_name] = summary
        
        return {
            "system_metrics": system_metrics,
            "app_metrics": app_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get system metrics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system metrics"
        )


@router.get("/statistics")
async def get_monitoring_statistics(
    current_user: User = Depends(get_admin_user)
):
    """获取监控统计信息"""
    try:
        # 指标统计
        metric_stats = metric_collector.get_statistics()
        
        # 日志统计
        log_stats = await log_manager.get_log_statistics()
        
        # 告警统计
        all_alerts = alert_manager.get_all_alerts()
        active_alerts = alert_manager.get_active_alerts()
        
        alert_stats = {
            "total_alerts": len(all_alerts),
            "active_alerts": len(active_alerts),
            "alert_levels": {}
        }
        
        for alert in all_alerts:
            level = alert['level']
            alert_stats['alert_levels'][level] = alert_stats['alert_levels'].get(level, 0) + 1
        
        return {
            "metrics": metric_stats,
            "logs": log_stats,
            "alerts": alert_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get monitoring statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get monitoring statistics"
        )


@router.post("/start")
async def start_monitoring(
    current_user: User = Depends(get_admin_user)
):
    """启动监控"""
    try:
        from ...monitoring.metrics import start_monitoring
        await start_monitoring()
        
        return {"success": True, "message": "Monitoring started successfully"}
        
    except Exception as e:
        logger.error(f"Start monitoring error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start monitoring"
        )


@router.post("/stop")
async def stop_monitoring(
    current_user: User = Depends(get_admin_user)
):
    """停止监控"""
    try:
        from ...monitoring.metrics import stop_monitoring
        await stop_monitoring()
        
        return {"success": True, "message": "Monitoring stopped successfully"}
        
    except Exception as e:
        logger.error(f"Stop monitoring error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop monitoring"
        )


@router.get("/health")
async def monitoring_health_check():
    """监控系统健康检查"""
    try:
        # 检查指标收集器状态
        metric_status = {
            "system_monitor_running": metric_collector.system_monitor_running,
            "metrics_count": len(metric_collector.metrics)
        }
        
        # 检查告警管理器状态
        alert_status = {
            "alert_check_running": alert_manager.check_running,
            "rules_count": len(alert_manager.rules),
            "active_alerts": len(alert_manager.get_active_alerts())
        }
        
        # 检查日志管理器状态
        log_status = {
            "log_processing_running": log_manager.running,
            "queue_size": log_manager.log_queue.qsize()
        }
        
        return {
            "status": "healthy",
            "metrics": metric_status,
            "alerts": alert_status,
            "logs": log_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Monitoring health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }