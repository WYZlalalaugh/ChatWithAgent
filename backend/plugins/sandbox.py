"""
插件沙箱
"""

import asyncio
import signal
import sys
import logging
import resource
import threading
import time
from typing import Any, Callable, Dict, Optional
from contextlib import contextmanager
import traceback


class PluginSandbox:
    """插件沙箱"""
    
    def __init__(self):
        self.logger = logging.getLogger("plugins.sandbox")
        
        # 资源限制配置
        self.resource_limits = {
            'max_memory': 100 * 1024 * 1024,  # 100MB
            'max_cpu_time': 30,  # 30秒
            'max_execution_time': 60,  # 60秒
            'max_file_size': 10 * 1024 * 1024,  # 10MB
            'max_open_files': 100
        }
        
        # 权限配置
        self.allowed_modules = {
            'json', 'datetime', 'time', 'math', 'random',
            'urllib.parse', 'base64', 'hashlib', 'uuid',
            'typing', 'dataclasses', 'enum', 'abc',
            'asyncio', 'concurrent.futures'
        }
        
        self.forbidden_modules = {
            'os', 'sys', 'subprocess', 'threading',
            'multiprocessing', 'socket', 'http.server',
            'ftplib', 'telnetlib', 'poplib', 'imaplib',
            'smtplib', '__builtin__', 'builtins'
        }
        
        # 执行统计
        self._execution_stats: Dict[str, Dict[str, Any]] = {}
    
    async def run_in_sandbox(
        self,
        func: Callable,
        plugin_name: str,
        *args,
        **kwargs
    ) -> Any:
        """在沙箱中运行函数"""
        try:
            self.logger.debug(f"Running function in sandbox for plugin: {plugin_name}")
            
            # 记录开始时间
            start_time = time.time()
            
            # 设置资源限制
            with self._resource_limits():
                # 设置执行超时
                result = await asyncio.wait_for(
                    self._execute_with_monitoring(func, plugin_name, *args, **kwargs),
                    timeout=self.resource_limits['max_execution_time']
                )
            
            # 记录统计信息
            execution_time = time.time() - start_time
            self._record_execution(plugin_name, execution_time, True)
            
            return result
            
        except asyncio.TimeoutError:
            self.logger.error(f"Plugin {plugin_name} execution timeout")
            self._record_execution(plugin_name, self.resource_limits['max_execution_time'], False, "timeout")
            return False
            
        except Exception as e:
            self.logger.error(f"Plugin {plugin_name} execution error: {e}")
            self._record_execution(plugin_name, time.time() - start_time, False, str(e))
            return False
    
    async def _execute_with_monitoring(
        self,
        func: Callable,
        plugin_name: str,
        *args,
        **kwargs
    ) -> Any:
        """带监控的执行"""
        try:
            # 检查函数安全性
            self._check_function_safety(func)
            
            # 执行函数
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # 在线程池中执行同步函数
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, *args, **kwargs)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Function execution error: {e}")
            traceback.print_exc()
            raise
    
    def _check_function_safety(self, func: Callable):
        """检查函数安全性"""
        try:
            # 检查函数模块
            module_name = getattr(func, '__module__', None)
            if module_name:
                # 检查是否为禁止的模块
                for forbidden in self.forbidden_modules:
                    if module_name.startswith(forbidden):
                        raise SecurityError(f"Access to forbidden module: {module_name}")
            
            # 检查函数代码（简单检查）
            if hasattr(func, '__code__'):
                code = func.__code__
                
                # 检查是否使用了危险的内置函数
                dangerous_names = {'exec', 'eval', 'compile', '__import__', 'open', 'file'}
                for name in code.co_names:
                    if name in dangerous_names:
                        raise SecurityError(f"Use of dangerous function: {name}")
        
        except SecurityError:
            raise
        except Exception as e:
            self.logger.warning(f"Function safety check error: {e}")
    
    @contextmanager
    def _resource_limits(self):
        """设置资源限制"""
        # 保存原始限制
        original_limits = {}
        
        try:
            # 设置内存限制
            if hasattr(resource, 'RLIMIT_AS'):
                original_limits['memory'] = resource.getrlimit(resource.RLIMIT_AS)
                resource.setrlimit(
                    resource.RLIMIT_AS,
                    (self.resource_limits['max_memory'], self.resource_limits['max_memory'])
                )
            
            # 设置CPU时间限制
            if hasattr(resource, 'RLIMIT_CPU'):
                original_limits['cpu'] = resource.getrlimit(resource.RLIMIT_CPU)
                resource.setrlimit(
                    resource.RLIMIT_CPU,
                    (self.resource_limits['max_cpu_time'], self.resource_limits['max_cpu_time'])
                )
            
            # 设置文件大小限制
            if hasattr(resource, 'RLIMIT_FSIZE'):
                original_limits['fsize'] = resource.getrlimit(resource.RLIMIT_FSIZE)
                resource.setrlimit(
                    resource.RLIMIT_FSIZE,
                    (self.resource_limits['max_file_size'], self.resource_limits['max_file_size'])
                )
            
            # 设置打开文件数限制
            if hasattr(resource, 'RLIMIT_NOFILE'):
                original_limits['nofile'] = resource.getrlimit(resource.RLIMIT_NOFILE)
                resource.setrlimit(
                    resource.RLIMIT_NOFILE,
                    (self.resource_limits['max_open_files'], self.resource_limits['max_open_files'])
                )
            
            yield
            
        finally:
            # 恢复原始限制
            try:
                if 'memory' in original_limits and hasattr(resource, 'RLIMIT_AS'):
                    resource.setrlimit(resource.RLIMIT_AS, original_limits['memory'])
                
                if 'cpu' in original_limits and hasattr(resource, 'RLIMIT_CPU'):
                    resource.setrlimit(resource.RLIMIT_CPU, original_limits['cpu'])
                
                if 'fsize' in original_limits and hasattr(resource, 'RLIMIT_FSIZE'):
                    resource.setrlimit(resource.RLIMIT_FSIZE, original_limits['fsize'])
                
                if 'nofile' in original_limits and hasattr(resource, 'RLIMIT_NOFILE'):
                    resource.setrlimit(resource.RLIMIT_NOFILE, original_limits['nofile'])
                    
            except Exception as e:
                self.logger.error(f"Error restoring resource limits: {e}")
    
    def _record_execution(
        self,
        plugin_name: str,
        execution_time: float,
        success: bool,
        error: Optional[str] = None
    ):
        """记录执行统计"""
        if plugin_name not in self._execution_stats:
            self._execution_stats[plugin_name] = {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'total_time': 0.0,
                'average_time': 0.0,
                'max_time': 0.0,
                'min_time': float('inf'),
                'last_error': None,
                'error_count': 0
            }
        
        stats = self._execution_stats[plugin_name]
        stats['total_executions'] += 1
        stats['total_time'] += execution_time
        
        if success:
            stats['successful_executions'] += 1
        else:
            stats['failed_executions'] += 1
            stats['last_error'] = error
            stats['error_count'] += 1
        
        # 更新时间统计
        stats['average_time'] = stats['total_time'] / stats['total_executions']
        stats['max_time'] = max(stats['max_time'], execution_time)
        stats['min_time'] = min(stats['min_time'], execution_time)
    
    def get_execution_stats(self, plugin_name: Optional[str] = None) -> Dict[str, Any]:
        """获取执行统计"""
        if plugin_name:
            return self._execution_stats.get(plugin_name, {})
        else:
            return self._execution_stats.copy()
    
    def clear_stats(self, plugin_name: Optional[str] = None):
        """清除统计信息"""
        if plugin_name:
            self._execution_stats.pop(plugin_name, None)
        else:
            self._execution_stats.clear()
    
    def set_resource_limit(self, resource_name: str, limit: int):
        """设置资源限制"""
        if resource_name in self.resource_limits:
            self.resource_limits[resource_name] = limit
            self.logger.info(f"Set resource limit {resource_name} to {limit}")
    
    def add_allowed_module(self, module_name: str):
        """添加允许的模块"""
        self.allowed_modules.add(module_name)
        self.logger.info(f"Added allowed module: {module_name}")
    
    def remove_allowed_module(self, module_name: str):
        """移除允许的模块"""
        self.allowed_modules.discard(module_name)
        self.logger.info(f"Removed allowed module: {module_name}")
    
    def add_forbidden_module(self, module_name: str):
        """添加禁止的模块"""
        self.forbidden_modules.add(module_name)
        self.logger.info(f"Added forbidden module: {module_name}")
    
    def remove_forbidden_module(self, module_name: str):
        """移除禁止的模块"""
        self.forbidden_modules.discard(module_name)
        self.logger.info(f"Removed forbidden module: {module_name}")
    
    def get_sandbox_config(self) -> Dict[str, Any]:
        """获取沙箱配置"""
        return {
            'resource_limits': self.resource_limits.copy(),
            'allowed_modules': list(self.allowed_modules),
            'forbidden_modules': list(self.forbidden_modules)
        }


class SecurityError(Exception):
    """安全错误"""
    pass


# 简化的权限检查装饰器
def sandbox_required(plugin_name: str = None):
    """沙箱执行装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            sandbox = PluginSandbox()
            name = plugin_name or func.__name__
            return await sandbox.run_in_sandbox(func, name, *args, **kwargs)
        
        return wrapper
    return decorator