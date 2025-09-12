"""
监控与日志系统基础框架
"""

import asyncio
import logging
import time
import psutil
import json
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from collections import deque, defaultdict

from app.cache import redis_client
from app.config import settings


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """指标数据"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'type': self.metric_type.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels
        }


@dataclass
class Alert:
    """告警数据"""
    id: str
    name: str
    level: AlertLevel
    message: str
    timestamp: datetime
    metric_name: str
    metric_value: float
    threshold: float
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['level'] = self.level.value
        data['timestamp'] = self.timestamp.isoformat()
        if self.resolved_at:
            data['resolved_at'] = self.resolved_at.isoformat()
        return data


class MetricCollector:
    """指标收集器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics: deque = deque(maxlen=10000)  # 保留最近10000个指标
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        
        # 缓存配置
        self.cache_prefix = "metrics:"
        self.cache_ttl = 3600  # 1小时
        
        # 系统监控
        self.system_monitor_interval = 30  # 30秒
        self.system_monitor_running = False
        self._system_monitor_task = None
    
    def increment(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """递增计数器"""
        key = self._make_key(name, labels)
        self.counters[key] += value
        
        metric = Metric(
            name=name,
            value=self.counters[key],
            metric_type=MetricType.COUNTER,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        )
        
        self._add_metric(metric)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """设置计量器值"""
        key = self._make_key(name, labels)
        self.gauges[key] = value
        
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        )
        
        self._add_metric(metric)
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """记录直方图观测值"""
        key = self._make_key(name, labels)
        self.histograms[key].append(value)
        
        # 保持最近1000个值
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]
        
        metric = Metric(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        )
        
        self._add_metric(metric)
    
    def record_timer(self, name: str, duration: float, labels: Dict[str, str] = None):
        """记录计时器值"""
        key = self._make_key(name, labels)
        self.timers[key].append(duration)
        
        # 保持最近1000个值
        if len(self.timers[key]) > 1000:
            self.timers[key] = self.timers[key][-1000:]
        
        metric = Metric(
            name=name,
            value=duration,
            metric_type=MetricType.TIMER,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        )
        
        self._add_metric(metric)
    
    def timer(self, name: str, labels: Dict[str, str] = None):
        """计时器装饰器"""
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    finally:
                        duration = time.time() - start_time
                        self.record_timer(name, duration, labels)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    start_time = time.time()
                    try:
                        result = func(*args, **kwargs)
                        return result
                    finally:
                        duration = time.time() - start_time
                        self.record_timer(name, duration, labels)
                return sync_wrapper
        return decorator
    
    async def get_metrics(
        self,
        name_filter: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取指标数据"""
        try:
            # 过滤指标
            filtered_metrics = []
            
            for metric in reversed(self.metrics):  # 最新的在前
                if len(filtered_metrics) >= limit:
                    break
                
                # 名称过滤
                if name_filter and name_filter not in metric.name:
                    continue
                
                # 时间过滤
                if start_time and metric.timestamp < start_time:
                    continue
                
                if end_time and metric.timestamp > end_time:
                    continue
                
                filtered_metrics.append(metric.to_dict())
            
            return filtered_metrics
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics: {e}")
            return []
    
    async def get_metric_summary(self, name: str, labels: Dict[str, str] = None) -> Dict[str, Any]:
        """获取指标摘要"""
        try:
            key = self._make_key(name, labels)
            summary = {'name': name, 'labels': labels or {}}
            
            # 计数器
            if key in self.counters:
                summary['counter_value'] = self.counters[key]
            
            # 计量器
            if key in self.gauges:
                summary['gauge_value'] = self.gauges[key]
            
            # 直方图统计
            if key in self.histograms and self.histograms[key]:
                values = self.histograms[key]
                summary['histogram'] = {
                    'count': len(values),
                    'sum': sum(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values)
                }
            
            # 计时器统计
            if key in self.timers and self.timers[key]:
                values = self.timers[key]
                sorted_values = sorted(values)
                count = len(values)
                
                summary['timer'] = {
                    'count': count,
                    'sum': sum(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / count,
                    'p50': sorted_values[int(count * 0.5)],
                    'p95': sorted_values[int(count * 0.95)],
                    'p99': sorted_values[int(count * 0.99)]
                }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get metric summary: {e}")
            return {'name': name, 'error': str(e)}
    
    async def start_system_monitoring(self):
        """开始系统监控"""
        if self.system_monitor_running:
            return
        
        self.system_monitor_running = True
        self._system_monitor_task = asyncio.create_task(self._system_monitor_loop())
        self.logger.info("System monitoring started")
    
    async def stop_system_monitoring(self):
        """停止系统监控"""
        self.system_monitor_running = False
        
        if self._system_monitor_task:
            self._system_monitor_task.cancel()
            try:
                await self._system_monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("System monitoring stopped")
    
    async def _system_monitor_loop(self):
        """系统监控循环"""
        try:
            while self.system_monitor_running:
                await self._collect_system_metrics()
                await asyncio.sleep(self.system_monitor_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"System monitor error: {e}")
    
    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            self.set_gauge("system_cpu_percent", cpu_percent)
            
            # 内存使用
            memory = psutil.virtual_memory()
            self.set_gauge("system_memory_percent", memory.percent)
            self.set_gauge("system_memory_available", memory.available)
            self.set_gauge("system_memory_used", memory.used)
            
            # 磁盘使用
            disk = psutil.disk_usage('/')
            self.set_gauge("system_disk_percent", disk.percent)
            self.set_gauge("system_disk_free", disk.free)
            self.set_gauge("system_disk_used", disk.used)
            
            # 网络IO
            net_io = psutil.net_io_counters()
            self.set_gauge("system_network_bytes_sent", net_io.bytes_sent)
            self.set_gauge("system_network_bytes_recv", net_io.bytes_recv)
            
            # 进程信息
            process = psutil.Process()
            self.set_gauge("process_cpu_percent", process.cpu_percent())
            self.set_gauge("process_memory_percent", process.memory_percent())
            self.set_gauge("process_memory_rss", process.memory_info().rss)
            
            # 文件描述符（Unix系统）
            try:
                self.set_gauge("process_open_files", process.num_fds())
            except (AttributeError, psutil.AccessDenied):
                pass
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """生成指标键"""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def _add_metric(self, metric: Metric):
        """添加指标"""
        self.metrics.append(metric)
        
        # 异步缓存到Redis
        asyncio.create_task(self._cache_metric(metric))
    
    async def _cache_metric(self, metric: Metric):
        """缓存指标到Redis"""
        try:
            key = f"{self.cache_prefix}{metric.name}"
            value = json.dumps(metric.to_dict(), ensure_ascii=False)
            
            # 使用有序集合存储时间序列数据
            timestamp = int(metric.timestamp.timestamp())
            await redis_client.zadd(key, {value: timestamp})
            
            # 设置TTL
            await redis_client.expire(key, self.cache_ttl)
            
            # 保持最近1000个数据点
            await redis_client.zremrangebyrank(key, 0, -1001)
            
        except Exception as e:
            self.logger.error(f"Failed to cache metric: {e}")


class AlertManager:
    """告警管理器"""
    
    def __init__(self, metric_collector: MetricCollector):
        self.logger = logging.getLogger(__name__)
        self.metric_collector = metric_collector
        self.rules: List[Dict[str, Any]] = []
        self.alerts: Dict[str, Alert] = {}
        self.alert_handlers: List[Callable] = []
        
        # 检查间隔
        self.check_interval = 60  # 1分钟
        self.check_running = False
        self._check_task = None
    
    def add_rule(
        self,
        name: str,
        metric_name: str,
        condition: str,  # "gt", "lt", "eq", "gte", "lte"
        threshold: float,
        level: AlertLevel = AlertLevel.WARNING,
        description: str = ""
    ):
        """添加告警规则"""
        rule = {
            'name': name,
            'metric_name': metric_name,
            'condition': condition,
            'threshold': threshold,
            'level': level,
            'description': description
        }
        
        self.rules.append(rule)
        self.logger.info(f"Added alert rule: {name}")
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    async def start_monitoring(self):
        """开始告警监控"""
        if self.check_running:
            return
        
        self.check_running = True
        self._check_task = asyncio.create_task(self._check_loop())
        self.logger.info("Alert monitoring started")
    
    async def stop_monitoring(self):
        """停止告警监控"""
        self.check_running = False
        
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Alert monitoring stopped")
    
    async def _check_loop(self):
        """告警检查循环"""
        try:
            while self.check_running:
                await self._check_rules()
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Alert check error: {e}")
    
    async def _check_rules(self):
        """检查告警规则"""
        try:
            for rule in self.rules:
                await self._check_rule(rule)
        except Exception as e:
            self.logger.error(f"Failed to check rules: {e}")
    
    async def _check_rule(self, rule: Dict[str, Any]):
        """检查单个告警规则"""
        try:
            # 获取指标摘要
            summary = await self.metric_collector.get_metric_summary(rule['metric_name'])
            
            # 获取当前值
            current_value = None
            
            if 'gauge_value' in summary:
                current_value = summary['gauge_value']
            elif 'counter_value' in summary:
                current_value = summary['counter_value']
            elif 'timer' in summary:
                current_value = summary['timer']['avg']
            elif 'histogram' in summary:
                current_value = summary['histogram']['avg']
            
            if current_value is None:
                return
            
            # 检查条件
            threshold = rule['threshold']
            condition = rule['condition']
            
            triggered = False
            if condition == 'gt' and current_value > threshold:
                triggered = True
            elif condition == 'gte' and current_value >= threshold:
                triggered = True
            elif condition == 'lt' and current_value < threshold:
                triggered = True
            elif condition == 'lte' and current_value <= threshold:
                triggered = True
            elif condition == 'eq' and current_value == threshold:
                triggered = True
            
            alert_id = f"{rule['name']}_{rule['metric_name']}"
            
            if triggered:
                # 触发告警
                if alert_id not in self.alerts or self.alerts[alert_id].resolved:
                    alert = Alert(
                        id=alert_id,
                        name=rule['name'],
                        level=rule['level'],
                        message=f"{rule['description']} - {rule['metric_name']} {condition} {threshold}, current: {current_value}",
                        timestamp=datetime.utcnow(),
                        metric_name=rule['metric_name'],
                        metric_value=current_value,
                        threshold=threshold
                    )
                    
                    self.alerts[alert_id] = alert
                    await self._fire_alert(alert)
            else:
                # 恢复告警
                if alert_id in self.alerts and not self.alerts[alert_id].resolved:
                    alert = self.alerts[alert_id]
                    alert.resolved = True
                    alert.resolved_at = datetime.utcnow()
                    
                    await self._resolve_alert(alert)
            
        except Exception as e:
            self.logger.error(f"Failed to check rule {rule['name']}: {e}")
    
    async def _fire_alert(self, alert: Alert):
        """触发告警"""
        self.logger.warning(f"ALERT FIRED: {alert.name} - {alert.message}")
        
        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler error: {e}")
    
    async def _resolve_alert(self, alert: Alert):
        """恢复告警"""
        self.logger.info(f"ALERT RESOLVED: {alert.name}")
        
        # 这里可以添加告警恢复的处理逻辑
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        return [
            alert.to_dict()
            for alert in self.alerts.values()
            if not alert.resolved
        ]
    
    def get_all_alerts(self) -> List[Dict[str, Any]]:
        """获取所有告警"""
        return [alert.to_dict() for alert in self.alerts.values()]


# 全局实例
metric_collector = MetricCollector()
alert_manager = AlertManager(metric_collector)


# 便捷函数
def increment(name: str, value: float = 1.0, labels: Dict[str, str] = None):
    """递增计数器"""
    metric_collector.increment(name, value, labels)


def set_gauge(name: str, value: float, labels: Dict[str, str] = None):
    """设置计量器"""
    metric_collector.set_gauge(name, value, labels)


def observe(name: str, value: float, labels: Dict[str, str] = None):
    """记录观测值"""
    metric_collector.observe_histogram(name, value, labels)


def timer(name: str, labels: Dict[str, str] = None):
    """计时器装饰器"""
    return metric_collector.timer(name, labels)


async def start_monitoring():
    """启动监控"""
    await metric_collector.start_system_monitoring()
    await alert_manager.start_monitoring()


async def stop_monitoring():
    """停止监控"""
    await metric_collector.stop_system_monitoring()
    await alert_manager.stop_monitoring()