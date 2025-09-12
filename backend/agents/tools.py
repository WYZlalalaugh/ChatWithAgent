"""
智能体工具集
"""

import asyncio
import aiohttp
import json
import os
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from loguru import logger

from agents.react import BaseTool


class WebSearchTool(BaseTool):
    """网络搜索工具"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="web_search",
            description="在互联网上搜索信息。输入搜索查询，返回搜索结果。"
        )
        self.api_key = api_key
    
    async def execute(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """执行网络搜索"""
        try:
            if isinstance(input_data, dict):
                query = input_data.get("query", "")
                num_results = input_data.get("num_results", 5)
            else:
                query = str(input_data)
                num_results = 5
            
            if not query:
                return "搜索查询不能为空"
            
            # 这里可以集成真实的搜索API（如 Bing Search API、Google Custom Search 等）
            # 暂时返回模拟结果
            results = [
                f"搜索结果 {i+1}: 关于'{query}'的相关信息...",
                f"标题: {query} 相关资料",
                f"内容: 这是关于 {query} 的详细信息...",
                f"来源: https://example.com/{query.replace(' ', '-')}"
            ]
            
            logger.info(f"网络搜索工具执行: {query}")
            return "\n".join(results[:num_results])
            
        except Exception as e:
            logger.error(f"网络搜索工具执行失败: {e}")
            return f"搜索失败: {str(e)}"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询"
                },
                "num_results": {
                    "type": "integer",
                    "description": "返回结果数量（默认5）",
                    "default": 5
                }
            },
            "required": ["query"]
        }


class WebScrapingTool(BaseTool):
    """网页抓取工具"""
    
    def __init__(self):
        super().__init__(
            name="web_scraping",
            description="抓取指定网页的内容。输入网页URL，返回网页文本内容。"
        )
    
    async def execute(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """执行网页抓取"""
        try:
            if isinstance(input_data, dict):
                url = input_data.get("url", "")
                max_length = input_data.get("max_length", 2000)
            else:
                url = str(input_data)
                max_length = 2000
            
            if not url:
                return "URL不能为空"
            
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            # 抓取网页内容
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # 简单的文本提取（在实际应用中可以使用 BeautifulSoup 等库）
                        # 移除HTML标签
                        import re
                        text = re.sub(r'<[^>]+>', '', content)
                        text = re.sub(r'\s+', ' ', text).strip()
                        
                        # 限制长度
                        if len(text) > max_length:
                            text = text[:max_length] + "..."
                        
                        logger.info(f"网页抓取工具执行: {url}")
                        return f"网页内容:\n{text}"
                    else:
                        return f"无法访问网页: HTTP {response.status}"
            
        except Exception as e:
            logger.error(f"网页抓取工具执行失败: {e}")
            return f"抓取失败: {str(e)}"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要抓取的网页URL"
                },
                "max_length": {
                    "type": "integer",
                    "description": "返回内容的最大长度（默认2000）",
                    "default": 2000
                }
            },
            "required": ["url"]
        }


class FileOperationTool(BaseTool):
    """文件操作工具"""
    
    def __init__(self, allowed_paths: Optional[List[str]] = None):
        super().__init__(
            name="file_operation",
            description="执行文件操作，如读取、写入、列出目录等。"
        )
        self.allowed_paths = allowed_paths or ["./data", "./temp"]
    
    async def execute(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """执行文件操作"""
        try:
            if isinstance(input_data, dict):
                operation = input_data.get("operation", "")
                path = input_data.get("path", "")
                content = input_data.get("content", "")
            else:
                # 简单解析字符串输入
                parts = str(input_data).split(" ", 2)
                operation = parts[0] if len(parts) > 0 else ""
                path = parts[1] if len(parts) > 1 else ""
                content = parts[2] if len(parts) > 2 else ""
            
            if not operation or not path:
                return "操作类型和路径不能为空"
            
            # 安全检查：确保路径在允许的目录中
            if not any(os.path.abspath(path).startswith(os.path.abspath(allowed)) 
                      for allowed in self.allowed_paths):
                return f"路径不在允许的目录中: {self.allowed_paths}"
            
            if operation == "read":
                if os.path.exists(path) and os.path.isfile(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    logger.info(f"文件读取: {path}")
                    return f"文件内容:\n{content}"
                else:
                    return f"文件不存在: {path}"
            
            elif operation == "write":
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"文件写入: {path}")
                return f"文件写入成功: {path}"
            
            elif operation == "list":
                if os.path.exists(path) and os.path.isdir(path):
                    files = os.listdir(path)
                    logger.info(f"目录列表: {path}")
                    return f"目录内容:\n" + "\n".join(files)
                else:
                    return f"目录不存在: {path}"
            
            elif operation == "delete":
                if os.path.exists(path):
                    if os.path.isfile(path):
                        os.remove(path)
                        logger.info(f"文件删除: {path}")
                        return f"文件删除成功: {path}"
                    else:
                        return f"不能删除目录: {path}"
                else:
                    return f"文件不存在: {path}"
            
            else:
                return f"不支持的操作: {operation}"
            
        except Exception as e:
            logger.error(f"文件操作工具执行失败: {e}")
            return f"文件操作失败: {str(e)}"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "操作类型: read, write, list, delete",
                    "enum": ["read", "write", "list", "delete"]
                },
                "path": {
                    "type": "string",
                    "description": "文件或目录路径"
                },
                "content": {
                    "type": "string",
                    "description": "写入的内容（仅用于write操作）"
                }
            },
            "required": ["operation", "path"]
        }


class CodeExecutionTool(BaseTool):
    """代码执行工具"""
    
    def __init__(self, allowed_languages: Optional[List[str]] = None):
        super().__init__(
            name="code_execution",
            description="执行代码片段。支持Python、JavaScript等语言。"
        )
        self.allowed_languages = allowed_languages or ["python", "javascript"]
    
    async def execute(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """执行代码"""
        try:
            if isinstance(input_data, dict):
                language = input_data.get("language", "python").lower()
                code = input_data.get("code", "")
                timeout = input_data.get("timeout", 10)
            else:
                language = "python"
                code = str(input_data)
                timeout = 10
            
            if not code:
                return "代码不能为空"
            
            if language not in self.allowed_languages:
                return f"不支持的语言: {language}"
            
            # 安全检查：禁止危险操作
            dangerous_keywords = [
                "import os", "import subprocess", "import sys",
                "exec(", "eval(", "__import__",
                "open(", "file(", "input(", "raw_input("
            ]
            
            if any(keyword in code for keyword in dangerous_keywords):
                return "代码包含潜在危险操作，执行被拒绝"
            
            if language == "python":
                result = await self._execute_python(code, timeout)
            elif language == "javascript":
                result = await self._execute_javascript(code, timeout)
            else:
                return f"暂不支持语言: {language}"
            
            logger.info(f"代码执行工具执行: {language}")
            return result
            
        except Exception as e:
            logger.error(f"代码执行工具执行失败: {e}")
            return f"代码执行失败: {str(e)}"
    
    async def _execute_python(self, code: str, timeout: int) -> str:
        """执行Python代码"""
        try:
            # 创建临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # 执行代码
            process = await asyncio.create_subprocess_exec(
                'python', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                
                output = stdout.decode('utf-8')
                error = stderr.decode('utf-8')
                
                if error:
                    return f"执行错误:\n{error}"
                else:
                    return f"执行结果:\n{output}"
                    
            except asyncio.TimeoutError:
                process.kill()
                return "代码执行超时"
            finally:
                # 清理临时文件
                os.unlink(temp_file)
                
        except Exception as e:
            return f"Python执行失败: {str(e)}"
    
    async def _execute_javascript(self, code: str, timeout: int) -> str:
        """执行JavaScript代码"""
        try:
            # 创建临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # 执行代码
            process = await asyncio.create_subprocess_exec(
                'node', temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
                
                output = stdout.decode('utf-8')
                error = stderr.decode('utf-8')
                
                if error:
                    return f"执行错误:\n{error}"
                else:
                    return f"执行结果:\n{output}"
                    
            except asyncio.TimeoutError:
                process.kill()
                return "代码执行超时"
            finally:
                # 清理临时文件
                os.unlink(temp_file)
                
        except Exception as e:
            return f"JavaScript执行失败: {str(e)}"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "description": "编程语言",
                    "enum": self.allowed_languages,
                    "default": "python"
                },
                "code": {
                    "type": "string",
                    "description": "要执行的代码"
                },
                "timeout": {
                    "type": "integer",
                    "description": "执行超时时间（秒），默认10秒",
                    "default": 10
                }
            },
            "required": ["code"]
        }


class APICallTool(BaseTool):
    """API调用工具"""
    
    def __init__(self):
        super().__init__(
            name="api_call",
            description="调用外部API接口。支持GET、POST等HTTP方法。"
        )
    
    async def execute(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """执行API调用"""
        try:
            if isinstance(input_data, dict):
                url = input_data.get("url", "")
                method = input_data.get("method", "GET").upper()
                headers = input_data.get("headers", {})
                params = input_data.get("params", {})
                data = input_data.get("data", {})
                timeout = input_data.get("timeout", 10)
            else:
                url = str(input_data)
                method = "GET"
                headers = {}
                params = {}
                data = {}
                timeout = 10
            
            if not url:
                return "URL不能为空"
            
            # 设置默认headers
            if "User-Agent" not in headers:
                headers["User-Agent"] = "ChatBot-Agent/1.0"
            
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(
                        url, headers=headers, params=params, timeout=timeout
                    ) as response:
                        result = await response.text()
                        status = response.status
                elif method == "POST":
                    async with session.post(
                        url, headers=headers, params=params, json=data, timeout=timeout
                    ) as response:
                        result = await response.text()
                        status = response.status
                else:
                    return f"不支持的HTTP方法: {method}"
                
                logger.info(f"API调用工具执行: {method} {url}")
                return f"HTTP {status}\n响应内容:\n{result}"
            
        except Exception as e:
            logger.error(f"API调用工具执行失败: {e}")
            return f"API调用失败: {str(e)}"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "API接口URL"
                },
                "method": {
                    "type": "string",
                    "description": "HTTP方法",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                    "default": "GET"
                },
                "headers": {
                    "type": "object",
                    "description": "请求头"
                },
                "params": {
                    "type": "object",
                    "description": "查询参数"
                },
                "data": {
                    "type": "object",
                    "description": "请求数据（用于POST/PUT）"
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认10秒",
                    "default": 10
                }
            },
            "required": ["url"]
        }


class DateTimeTool(BaseTool):
    """日期时间工具"""
    
    def __init__(self):
        super().__init__(
            name="datetime",
            description="获取当前日期时间信息或进行日期计算。"
        )
    
    async def execute(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """执行日期时间操作"""
        try:
            if isinstance(input_data, dict):
                operation = input_data.get("operation", "current")
                format_str = input_data.get("format", "%Y-%m-%d %H:%M:%S")
            else:
                operation = str(input_data) if input_data else "current"
                format_str = "%Y-%m-%d %H:%M:%S"
            
            now = datetime.utcnow()
            
            if operation == "current":
                result = now.strftime(format_str)
            elif operation == "date":
                result = now.strftime("%Y-%m-%d")
            elif operation == "time":
                result = now.strftime("%H:%M:%S")
            elif operation == "timestamp":
                result = str(int(now.timestamp()))
            elif operation == "iso":
                result = now.isoformat()
            else:
                result = now.strftime(format_str)
            
            logger.info(f"日期时间工具执行: {operation}")
            return f"当前时间: {result}"
            
        except Exception as e:
            logger.error(f"日期时间工具执行失败: {e}")
            return f"日期时间操作失败: {str(e)}"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["current", "date", "time", "timestamp", "iso"],
                    "default": "current"
                },
                "format": {
                    "type": "string",
                    "description": "日期格式字符串",
                    "default": "%Y-%m-%d %H:%M:%S"
                }
            }
        }


# 高级工具注册函数
def register_advanced_tools(tool_registry):
    """注册高级工具"""
    tool_registry.register_tool(WebSearchTool())
    tool_registry.register_tool(WebScrapingTool())
    tool_registry.register_tool(FileOperationTool())
    tool_registry.register_tool(CodeExecutionTool())
    tool_registry.register_tool(APICallTool())
    tool_registry.register_tool(DateTimeTool())
    
    logger.info("高级工具注册完成")
