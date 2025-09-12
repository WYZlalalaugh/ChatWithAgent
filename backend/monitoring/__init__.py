"""
监控与日志系统初始化
"""

import asyncio
import logging
from .metrics import metric_collector, alert_manager, AlertLevel
from .logging import log_manager


logger = logging.getLogger(__name__)


async def initialize_monitoring():
    """初始化监控系统"""
    try:
        logger.info("Initializing monitoring system...")
        
        # 添加默认告警规则
        _add_default_alert_rules()
        
        # 启动系统监控
        await metric_collector.start_system_monitoring()
        
        # 启动告警监控
        await alert_manager.start_monitoring()
        
        logger.info("Monitoring system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize monitoring system: {e}")
        raise


def _add_default_alert_rules():
    """添加默认告警规则"""
    # CPU使用率告警
    alert_manager.add_rule(
        name="High CPU Usage",
        metric_name="system_cpu_percent",
        condition="gt",
        threshold=80.0,
        level=AlertLevel.WARNING,
        description="System CPU usage is high"
    )
    
    alert_manager.add_rule(
        name="Critical CPU Usage",
        metric_name="system_cpu_percent",
        condition="gt",
        threshold=95.0,
        level=AlertLevel.CRITICAL,
        description="System CPU usage is critical"
    )
    
    # 内存使用率告警
    alert_manager.add_rule(
        name="High Memory Usage",
        metric_name="system_memory_percent",
        condition="gt",
        threshold=85.0,
        level=AlertLevel.WARNING,
        description="System memory usage is high"
    )
    
    alert_manager.add_rule(
        name="Critical Memory Usage",
        metric_name="system_memory_percent",
        condition="gt",
        threshold=95.0,
        level=AlertLevel.CRITICAL,
        description="System memory usage is critical"
    )
    
    # 磁盘使用率告警
    alert_manager.add_rule(
        name="High Disk Usage",
        metric_name="system_disk_percent",
        condition="gt",
        threshold=85.0,
        level=AlertLevel.WARNING,
        description="System disk usage is high"
    )
    
    alert_manager.add_rule(
        name="Critical Disk Usage",
        metric_name="system_disk_percent",
        condition="gt",
        threshold=95.0,
        level=AlertLevel.CRITICAL,
        description="System disk usage is critical"
    )
    
    # 进程CPU使用率告警
    alert_manager.add_rule(
        name="High Process CPU",
        metric_name="process_cpu_percent",
        condition="gt",
        threshold=50.0,
        level=AlertLevel.WARNING,
        description="Process CPU usage is high"
    )
    
    # 进程内存使用率告警
    alert_manager.add_rule(
        name="High Process Memory",
        metric_name="process_memory_percent",
        condition="gt",
        threshold=70.0,
        level=AlertLevel.WARNING,
        description="Process memory usage is high"
    )


async def cleanup_monitoring():
    """清理监控系统"""
    try:
        logger.info("Cleaning up monitoring system...")
        
        # 停止监控
        await metric_collector.stop_system_monitoring()
        await alert_manager.stop_monitoring()
        
        # 停止日志管理器
        log_manager.stop()
        
        logger.info("Monitoring system cleaned up")
        
    except Exception as e:
        logger.error(f"Failed to cleanup monitoring system: {e}")


# 便捷的监控装饰器
def monitor_endpoint(endpoint_name: str):
    """监控API端点的装饰器"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # 增加请求计数
                metric_collector.increment("http_requests_total", labels={"endpoint": endpoint_name})
                
                # 计时
                start_time = asyncio.get_event_loop().time()
                try:
                    result = await func(*args, **kwargs)
                    # 成功计数
                    metric_collector.increment("http_requests_success", labels={"endpoint": endpoint_name})
                    return result
                except Exception as e:
                    # 错误计数
                    metric_collector.increment("http_requests_error", labels={"endpoint": endpoint_name})
                    raise
                finally:
                    # 记录响应时间
                    duration = asyncio.get_event_loop().time() - start_time
                    metric_collector.record_timer("http_request_duration", duration, labels={"endpoint": endpoint_name})
            
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # 增加请求计数
                metric_collector.increment("http_requests_total", labels={"endpoint": endpoint_name})
                
                # 计时
                import time
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    # 成功计数
                    metric_collector.increment("http_requests_success", labels={"endpoint": endpoint_name})
                    return result
                except Exception as e:
                    # 错误计数
                    metric_collector.increment("http_requests_error", labels={"endpoint": endpoint_name})
                    raise
                finally:
                    # 记录响应时间
                    duration = time.time() - start_time
                    metric_collector.record_timer("http_request_duration", duration, labels={"endpoint": endpoint_name})
            
            return sync_wrapper
    
    return decorator


def monitor_database_operation(operation_name: str):
    """监控数据库操作的装饰器"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # 增加操作计数
                metric_collector.increment("database_operations_total", labels={"operation": operation_name})
                
                # 计时
                start_time = asyncio.get_event_loop().time()
                try:
                    result = await func(*args, **kwargs)
                    # 成功计数
                    metric_collector.increment("database_operations_success", labels={"operation": operation_name})
                    return result
                except Exception as e:
                    # 错误计数
                    metric_collector.increment("database_operations_error", labels={"operation": operation_name})
                    raise
                finally:
                    # 记录执行时间
                    duration = asyncio.get_event_loop().time() - start_time
                    metric_collector.record_timer("database_operation_duration", duration, labels={"operation": operation_name})
            
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # 增加操作计数
                metric_collector.increment("database_operations_total", labels={"operation": operation_name})
                
                # 计时
                import time
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    # 成功计数
                    metric_collector.increment("database_operations_success", labels={"operation": operation_name})
                    return result
                except Exception as e:
                    # 错误计数
                    metric_collector.increment("database_operations_error", labels={"operation": operation_name})
                    raise
                finally:
                    # 记录执行时间
                    duration = time.time() - start_time
                    metric_collector.record_timer("database_operation_duration", duration, labels={"operation": operation_name})
            
            return sync_wrapper
    
    return decorator


def monitor_llm_request(model_name: str):
    """监控LLM请求的装饰器"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # 增加请求计数
                metric_collector.increment("llm_requests_total", labels={"model": model_name})
                
                # 计时
                start_time = asyncio.get_event_loop().time()
                try:
                    result = await func(*args, **kwargs)
                    # 成功计数
                    metric_collector.increment("llm_requests_success", labels={"model": model_name})
                    
                    # 记录token使用量
                    if isinstance(result, dict) and 'usage' in result:
                        usage = result['usage']
                        if 'total_tokens' in usage:
                            metric_collector.observe_histogram("llm_tokens_used", usage['total_tokens'], labels={"model": model_name})
                    
                    return result
                except Exception as e:
                    # 错误计数
                    metric_collector.increment("llm_requests_error", labels={"model": model_name})
                    raise
                finally:
                    # 记录响应时间
                    duration = asyncio.get_event_loop().time() - start_time
                    metric_collector.record_timer("llm_request_duration", duration, labels={"model": model_name})
            
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # 增加请求计数
                metric_collector.increment("llm_requests_total", labels={"model": model_name})
                
                # 计时
                import time
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    # 成功计数
                    metric_collector.increment("llm_requests_success", labels={"model": model_name})
                    
                    # 记录token使用量
                    if isinstance(result, dict) and 'usage' in result:
                        usage = result['usage']
                        if 'total_tokens' in usage:
                            metric_collector.observe_histogram("llm_tokens_used", usage['total_tokens'], labels={"model": model_name})
                    
                    return result
                except Exception as e:
                    # 错误计数
                    metric_collector.increment("llm_requests_error", labels={"model": model_name})
                    raise
                finally:
                    # 记录响应时间
                    duration = time.time() - start_time
                    metric_collector.record_timer("llm_request_duration", duration, labels={"model": model_name})
            
            return sync_wrapper
    
    return decorator


# 模块导出
__all__ = [
    'initialize_monitoring',
    'cleanup_monitoring',
    'monitor_endpoint',
    'monitor_database_operation',
    'monitor_llm_request',
    'metric_collector',
    'alert_manager',
    'log_manager'
]