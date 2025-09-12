"""
日志系统
"""

import asyncio
import logging
import json
import traceback
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import gzip
import os
from pathlib import Path
import threading
from queue import Queue
import time

from app.cache import redis_client
from app.config import settings


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    logger_name: str
    message: str
    module: str
    function: str
    line_number: int
    process_id: int
    thread_id: int
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    exception_info: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['level'] = self.level.value
        return data
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class LogHandler(logging.Handler):
    """自定义日志处理器"""
    
    def __init__(self, log_manager):
        super().__init__()
        self.log_manager = log_manager
    
    def emit(self, record: logging.LogRecord):
        """发送日志记录"""
        try:
            # 获取上下文信息
            user_id = getattr(record, 'user_id', None)
            request_id = getattr(record, 'request_id', None)
            session_id = getattr(record, 'session_id', None)
            extra_data = getattr(record, 'extra_data', None)
            
            # 处理异常信息
            exception_info = None
            if record.exc_info:
                exception_info = ''.join(traceback.format_exception(*record.exc_info))
            
            # 创建日志条目
            log_entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created),
                level=LogLevel(record.levelname),
                logger_name=record.name,
                message=record.getMessage(),
                module=record.module,
                function=record.funcName,
                line_number=record.lineno,
                process_id=record.process,
                thread_id=record.thread,
                user_id=user_id,
                request_id=request_id,
                session_id=session_id,
                extra_data=extra_data,
                exception_info=exception_info
            )
            
            # 异步处理日志
            self.log_manager.add_log_entry(log_entry)
            
        except Exception as e:
            # 避免日志处理器本身的错误导致程序中断
            print(f"Log handler error: {e}")


class LogManager:
    """日志管理器"""
    
    def __init__(
        self,
        log_dir: str = "logs",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        max_files: int = 10,
        compression: bool = True,
        redis_enabled: bool = True,
        redis_ttl: int = 3600 * 24 * 7  # 7天
    ):
        self.log_dir = Path(log_dir)
        self.max_file_size = max_file_size
        self.max_files = max_files
        self.compression = compression
        self.redis_enabled = redis_enabled
        self.redis_ttl = redis_ttl
        
        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志队列和处理线程
        self.log_queue = Queue()
        self.log_thread = None
        self.running = False
        
        # 当前日志文件
        self.current_log_file = None
        self.current_file_size = 0
        
        # Redis缓存前缀
        self.redis_prefix = "logs:"
        
        # 启动日志处理
        self.start()
    
    def start(self):
        """启动日志处理"""
        if self.running:
            return
        
        self.running = True
        self.log_thread = threading.Thread(target=self._process_logs, daemon=True)
        self.log_thread.start()
        
        # 设置日志处理器
        self._setup_logging()
    
    def stop(self):
        """停止日志处理"""
        self.running = False
        
        if self.log_thread:
            self.log_thread.join(timeout=5)
        
        if self.current_log_file:
            self.current_log_file.close()
    
    def add_log_entry(self, log_entry: LogEntry):
        """添加日志条目"""
        try:
            self.log_queue.put(log_entry, block=False)
        except:
            # 队列满了，丢弃日志
            pass
    
    def _setup_logging(self):
        """设置日志配置"""
        # 创建自定义处理器
        handler = LogHandler(self)
        handler.setLevel(logging.DEBUG)
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # 添加到根日志器
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    
    def _process_logs(self):
        """处理日志队列"""
        while self.running:
            try:
                # 获取日志条目（超时1秒）
                try:
                    log_entry = self.log_queue.get(timeout=1)
                except:
                    continue
                
                # 写入文件
                self._write_to_file(log_entry)
                
                # 缓存到Redis
                if self.redis_enabled:
                    asyncio.create_task(self._cache_to_redis(log_entry))
                
                self.log_queue.task_done()
                
            except Exception as e:
                print(f"Log processing error: {e}")
    
    def _write_to_file(self, log_entry: LogEntry):
        """写入日志文件"""
        try:
            # 检查是否需要轮转文件
            if self._should_rotate_file():
                self._rotate_file()
            
            # 确保有当前文件
            if not self.current_log_file:
                self._create_new_file()
            
            # 写入日志
            log_line = log_entry.to_json() + '\n'
            self.current_log_file.write(log_line)
            self.current_log_file.flush()
            
            self.current_file_size += len(log_line.encode('utf-8'))
            
        except Exception as e:
            print(f"Failed to write log to file: {e}")
    
    def _should_rotate_file(self) -> bool:
        """检查是否应该轮转文件"""
        if not self.current_log_file:
            return True
        
        if self.current_file_size >= self.max_file_size:
            return True
        
        return False
    
    def _rotate_file(self):
        """轮转日志文件"""
        try:
            if self.current_log_file:
                self.current_log_file.close()
                
                # 压缩旧文件
                if self.compression:
                    self._compress_file(self.current_log_file.name)
            
            # 清理旧文件
            self._cleanup_old_files()
            
            # 创建新文件
            self._create_new_file()
            
        except Exception as e:
            print(f"Failed to rotate log file: {e}")
    
    def _create_new_file(self):
        """创建新的日志文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"app_{timestamp}.log"
        filepath = self.log_dir / filename
        
        self.current_log_file = open(filepath, 'w', encoding='utf-8')
        self.current_file_size = 0
    
    def _compress_file(self, filepath: str):
        """压缩日志文件"""
        try:
            compressed_path = f"{filepath}.gz"
            
            with open(filepath, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # 删除原文件
            os.remove(filepath)
            
        except Exception as e:
            print(f"Failed to compress log file: {e}")
    
    def _cleanup_old_files(self):
        """清理旧的日志文件"""
        try:
            # 获取所有日志文件
            log_files = []
            for ext in ['*.log', '*.log.gz']:
                log_files.extend(self.log_dir.glob(ext))
            
            # 按修改时间排序
            log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # 删除超出数量限制的文件
            for file_to_delete in log_files[self.max_files:]:
                file_to_delete.unlink()
                
        except Exception as e:
            print(f"Failed to cleanup old log files: {e}")
    
    async def _cache_to_redis(self, log_entry: LogEntry):
        """缓存日志到Redis"""
        try:
            if not self.redis_enabled:
                return
            
            # 按日期和级别分组存储
            date_key = log_entry.timestamp.strftime("%Y%m%d")
            level_key = f"{self.redis_prefix}{date_key}:{log_entry.level.value}"
            
            # 使用有序集合存储，按时间戳排序
            timestamp = int(log_entry.timestamp.timestamp() * 1000)  # 毫秒级时间戳
            log_data = log_entry.to_json()
            
            await redis_client.zadd(level_key, {log_data: timestamp})
            
            # 设置TTL
            await redis_client.expire(level_key, self.redis_ttl)
            
            # 保持最近1万条记录
            await redis_client.zremrangebyrank(level_key, 0, -10001)
            
        except Exception as e:
            print(f"Failed to cache log to Redis: {e}")
    
    async def search_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[LogLevel] = None,
        logger_name: Optional[str] = None,
        message_contains: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """搜索日志"""
        try:
            results = []
            
            # 如果启用了Redis，先从Redis搜索
            if self.redis_enabled:
                redis_results = await self._search_redis_logs(
                    start_time, end_time, level, limit
                )
                results.extend(redis_results)
            
            # 如果Redis结果不足，从文件搜索
            if len(results) < limit:
                file_results = await self._search_file_logs(
                    start_time, end_time, level, logger_name,
                    message_contains, user_id, request_id,
                    limit - len(results)
                )
                results.extend(file_results)
            
            # 过滤和排序
            filtered_results = []
            for log_data in results:
                if self._matches_filters(
                    log_data, logger_name, message_contains, user_id, request_id
                ):
                    filtered_results.append(log_data)
            
            # 按时间排序（最新的在前）
            filtered_results.sort(
                key=lambda x: x.get('timestamp', ''), reverse=True
            )
            
            return filtered_results[:limit]
            
        except Exception as e:
            print(f"Failed to search logs: {e}")
            return []
    
    async def _search_redis_logs(
        self,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        level: Optional[LogLevel],
        limit: int
    ) -> List[Dict[str, Any]]:
        """从Redis搜索日志"""
        try:
            results = []
            
            # 确定搜索的日期范围
            if not start_time:
                start_time = datetime.now() - timedelta(days=1)
            if not end_time:
                end_time = datetime.now()
            
            # 确定搜索的级别
            levels = [level] if level else list(LogLevel)
            
            for search_level in levels:
                # 按日期搜索
                current_date = start_time.date()
                while current_date <= end_time.date():
                    date_key = current_date.strftime("%Y%m%d")
                    level_key = f"{self.redis_prefix}{date_key}:{search_level.value}"
                    
                    # 时间范围过滤
                    min_score = int(start_time.timestamp() * 1000)
                    max_score = int(end_time.timestamp() * 1000)
                    
                    # 从Redis获取数据
                    log_entries = await redis_client.zrangebyscore(
                        level_key, min_score, max_score, withscores=False
                    )
                    
                    for log_data in log_entries:
                        try:
                            log_dict = json.loads(log_data)
                            results.append(log_dict)
                            
                            if len(results) >= limit:
                                return results
                        except json.JSONDecodeError:
                            continue
                    
                    current_date += timedelta(days=1)
            
            return results
            
        except Exception as e:
            print(f"Failed to search Redis logs: {e}")
            return []
    
    async def _search_file_logs(
        self,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        level: Optional[LogLevel],
        logger_name: Optional[str],
        message_contains: Optional[str],
        user_id: Optional[str],
        request_id: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """从文件搜索日志"""
        try:
            results = []
            
            # 获取所有日志文件
            log_files = []
            for ext in ['*.log', '*.log.gz']:
                log_files.extend(self.log_dir.glob(ext))
            
            # 按修改时间排序（最新的在前）
            log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            for log_file in log_files:
                if len(results) >= limit:
                    break
                
                file_results = await self._search_single_file(
                    log_file, start_time, end_time, level,
                    logger_name, message_contains, user_id, request_id,
                    limit - len(results)
                )
                
                results.extend(file_results)
            
            return results
            
        except Exception as e:
            print(f"Failed to search file logs: {e}")
            return []
    
    async def _search_single_file(
        self,
        log_file: Path,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        level: Optional[LogLevel],
        logger_name: Optional[str],
        message_contains: Optional[str],
        user_id: Optional[str],
        request_id: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """搜索单个日志文件"""
        try:
            results = []
            
            # 根据文件扩展名选择打开方式
            if log_file.suffix == '.gz':
                file_opener = gzip.open
                mode = 'rt'
            else:
                file_opener = open
                mode = 'r'
            
            with file_opener(log_file, mode, encoding='utf-8') as f:
                for line in f:
                    if len(results) >= limit:
                        break
                    
                    try:
                        log_data = json.loads(line.strip())
                        
                        # 时间过滤
                        log_time = datetime.fromisoformat(log_data['timestamp'])
                        if start_time and log_time < start_time:
                            continue
                        if end_time and log_time > end_time:
                            continue
                        
                        # 级别过滤
                        if level and log_data['level'] != level.value:
                            continue
                        
                        # 其他过滤
                        if self._matches_filters(
                            log_data, logger_name, message_contains, user_id, request_id
                        ):
                            results.append(log_data)
                            
                    except json.JSONDecodeError:
                        continue
            
            return results
            
        except Exception as e:
            print(f"Failed to search file {log_file}: {e}")
            return []
    
    def _matches_filters(
        self,
        log_data: Dict[str, Any],
        logger_name: Optional[str],
        message_contains: Optional[str],
        user_id: Optional[str],
        request_id: Optional[str]
    ) -> bool:
        """检查日志是否匹配过滤条件"""
        if logger_name and logger_name not in log_data.get('logger_name', ''):
            return False
        
        if message_contains and message_contains not in log_data.get('message', ''):
            return False
        
        if user_id and log_data.get('user_id') != user_id:
            return False
        
        if request_id and log_data.get('request_id') != request_id:
            return False
        
        return True
    
    async def get_log_statistics(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        try:
            stats = {
                'total_files': 0,
                'total_size': 0,
                'levels': {},
                'recent_entries': 0
            }
            
            # 文件统计
            log_files = list(self.log_dir.glob('*.log*'))
            stats['total_files'] = len(log_files)
            stats['total_size'] = sum(f.stat().st_size for f in log_files)
            
            # Redis统计
            if self.redis_enabled:
                today = datetime.now().strftime("%Y%m%d")
                for level in LogLevel:
                    key = f"{self.redis_prefix}{today}:{level.value}"
                    count = await redis_client.zcard(key)
                    stats['levels'][level.value] = count
                    stats['recent_entries'] += count
            
            return stats
            
        except Exception as e:
            print(f"Failed to get log statistics: {e}")
            return {}


# 全局日志管理器实例
log_manager = LogManager()


# 便捷日志函数
def get_logger(name: str) -> logging.Logger:
    """获取日志器"""
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
):
    """带上下文的日志记录"""
    extra = {
        'user_id': user_id,
        'request_id': request_id,
        'session_id': session_id,
        'extra_data': extra_data
    }
    
    logger.log(getattr(logging, level.upper()), message, extra=extra)