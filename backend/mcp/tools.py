"""
MCP工具管理系统
"""

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union
from datetime import datetime

from .types import MCPTool, MCPToolParameter, MCPError, MCPProgress


class BaseTool(ABC):
    """工具基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.parameters: List[MCPToolParameter] = []
        self.logger = logging.getLogger(f"mcp.tool.{name}")
        
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具"""
        pass
    
    def add_parameter(
        self,
        name: str,
        type_name: str,
        description: str,
        required: bool = True,
        default: Any = None,
        enum: Optional[List[Any]] = None
    ):
        """添加参数定义"""
        param = MCPToolParameter(
            name=name,
            type=type_name,
            description=description,
            required=required,
            default=default,
            enum=enum
        )
        self.parameters.append(param)
    
    def to_mcp_tool(self) -> MCPTool:
        """转换为MCP工具格式"""
        return MCPTool(
            name=self.name,
            description=self.description,
            parameters=self.parameters
        )
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        try:
            # 检查必需参数
            for param in self.parameters:
                if param.required and param.name not in params:
                    self.logger.error(f"Missing required parameter: {param.name}")
                    return False
            
            # 检查参数类型（简单验证）
            for param in self.parameters:
                if param.name in params:
                    value = params[param.name]
                    if param.type == "string" and not isinstance(value, str):
                        self.logger.error(f"Parameter {param.name} should be string")
                        return False
                    elif param.type == "number" and not isinstance(value, (int, float)):
                        self.logger.error(f"Parameter {param.name} should be number")
                        return False
                    elif param.type == "boolean" and not isinstance(value, bool):
                        self.logger.error(f"Parameter {param.name} should be boolean")
                        return False
                    elif param.type == "array" and not isinstance(value, list):
                        self.logger.error(f"Parameter {param.name} should be array")
                        return False
                    elif param.type == "object" and not isinstance(value, dict):
                        self.logger.error(f"Parameter {param.name} should be object")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Parameter validation failed: {e}")
            return False


class ToolManager:
    """工具管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger("mcp.tool_manager")
        self.tools: Dict[str, BaseTool] = {}
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        
    def register_tool(self, tool: BaseTool) -> bool:
        """注册工具"""
        try:
            if tool.name in self.tools:
                self.logger.warning(f"Tool {tool.name} already exists, replacing...")
            
            self.tools[tool.name] = tool
            self.execution_stats[tool.name] = {
                "call_count": 0,
                "success_count": 0,
                "error_count": 0,
                "last_used": None,
                "average_duration": 0.0
            }
            
            self.logger.info(f"Registered tool: {tool.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register tool {tool.name}: {e}")
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """注销工具"""
        try:
            if tool_name in self.tools:
                del self.tools[tool_name]
                del self.execution_stats[tool_name]
                self.logger.info(f"Unregistered tool: {tool_name}")
                return True
            else:
                self.logger.warning(f"Tool {tool_name} not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to unregister tool {tool_name}: {e}")
            return False
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[MCPTool]:
        """列出所有工具"""
        return [tool.to_mcp_tool() for tool in self.tools.values()]
    
    async def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        progress_callback: Optional[Callable[[MCPProgress], None]] = None
    ) -> Dict[str, Any]:
        """执行工具"""
        start_time = datetime.now()
        
        try:
            # 检查工具是否存在
            tool = self.tools.get(tool_name)
            if not tool:
                raise ValueError(f"Tool {tool_name} not found")
            
            # 验证参数
            if not tool.validate_parameters(parameters):
                raise ValueError(f"Invalid parameters for tool {tool_name}")
            
            # 更新统计信息
            stats = self.execution_stats[tool_name]
            stats["call_count"] += 1
            stats["last_used"] = start_time.isoformat()
            
            # 发送开始进度通知
            if progress_callback:
                progress_callback(MCPProgress(progress=0))
            
            # 执行工具
            self.logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
            result = await tool.execute(**parameters)
            
            # 发送完成进度通知
            if progress_callback:
                progress_callback(MCPProgress(progress=100))
            
            # 更新成功统计
            stats["success_count"] += 1
            
            # 计算执行时间
            duration = (datetime.now() - start_time).total_seconds()
            stats["average_duration"] = (
                (stats["average_duration"] * (stats["success_count"] - 1) + duration) 
                / stats["success_count"]
            )
            
            self.logger.info(f"Tool {tool_name} executed successfully in {duration:.2f}s")
            
            return {
                "success": True,
                "result": result,
                "execution_time": duration,
                "tool_name": tool_name
            }
            
        except Exception as e:
            # 更新错误统计
            if tool_name in self.execution_stats:
                self.execution_stats[tool_name]["error_count"] += 1
            
            error_msg = f"Tool execution failed: {str(e)}"
            self.logger.error(f"Tool {tool_name} execution failed: {e}")
            
            return {
                "success": False,
                "error": error_msg,
                "error_type": type(e).__name__,
                "tool_name": tool_name
            }
    
    def get_tool_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取工具统计信息"""
        if tool_name:
            return self.execution_stats.get(tool_name, {})
        else:
            return self.execution_stats.copy()
    
    def register_function_as_tool(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[List[MCPToolParameter]] = None
    ) -> bool:
        """将函数注册为工具"""
        try:
            # 自动生成名称和描述
            tool_name = name or func.__name__
            tool_description = description or func.__doc__ or f"Tool: {tool_name}"
            
            # 创建函数工具包装器
            class FunctionTool(BaseTool):
                def __init__(self, func, name, desc, params):
                    super().__init__(name, desc)
                    self.func = func
                    if params:
                        self.parameters = params
                    else:
                        self._auto_generate_parameters()
                
                def _auto_generate_parameters(self):
                    """自动生成参数定义"""
                    sig = inspect.signature(self.func)
                    for param_name, param in sig.parameters.items():
                        if param_name == 'self':
                            continue
                        
                        # 尝试推断类型
                        param_type = "string"  # 默认类型
                        if param.annotation != inspect.Parameter.empty:
                            if param.annotation == int:
                                param_type = "number"
                            elif param.annotation == float:
                                param_type = "number"
                            elif param.annotation == bool:
                                param_type = "boolean"
                            elif param.annotation == list:
                                param_type = "array"
                            elif param.annotation == dict:
                                param_type = "object"
                        
                        required = param.default == inspect.Parameter.empty
                        default = None if required else param.default
                        
                        self.add_parameter(
                            name=param_name,
                            type_name=param_type,
                            description=f"Parameter {param_name}",
                            required=required,
                            default=default
                        )
                
                async def execute(self, **kwargs):
                    """执行函数"""
                    if inspect.iscoroutinefunction(self.func):
                        return await self.func(**kwargs)
                    else:
                        return self.func(**kwargs)
            
            # 创建并注册工具
            tool = FunctionTool(func, tool_name, tool_description, parameters)
            return self.register_tool(tool)
            
        except Exception as e:
            self.logger.error(f"Failed to register function as tool: {e}")
            return False
    
    def clear_all_tools(self):
        """清除所有工具"""
        self.tools.clear()
        self.execution_stats.clear()
        self.logger.info("Cleared all tools")


# 创建全局工具管理器实例
global_tool_manager = ToolManager()


def register_tool(tool: BaseTool) -> bool:
    """注册工具到全局管理器"""
    return global_tool_manager.register_tool(tool)


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[List[MCPToolParameter]] = None
):
    """工具装饰器"""
    def decorator(func: Callable) -> Callable:
        global_tool_manager.register_function_as_tool(
            func=func,
            name=name,
            description=description,
            parameters=parameters
        )
        return func
    return decorator


# 内置工具示例
class EchoTool(BaseTool):
    """回声工具"""
    
    def __init__(self):
        super().__init__("echo", "Echo the input text")
        self.add_parameter("text", "string", "Text to echo", required=True)
    
    async def execute(self, text: str) -> str:
        """执行回声"""
        return f"Echo: {text}"


class CalculatorTool(BaseTool):
    """计算器工具"""
    
    def __init__(self):
        super().__init__("calculator", "Perform basic mathematical calculations")
        self.add_parameter("expression", "string", "Mathematical expression to evaluate", required=True)
    
    async def execute(self, expression: str) -> Dict[str, Any]:
        """执行计算"""
        try:
            # 安全的数学表达式求值
            allowed_chars = set("0123456789+-*/().() ")
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Invalid characters in expression")
            
            result = eval(expression)
            return {
                "expression": expression,
                "result": result
            }
        except Exception as e:
            raise ValueError(f"Invalid mathematical expression: {str(e)}")


# 注册内置工具
def register_builtin_tools():
    """注册内置工具"""
    global_tool_manager.register_tool(EchoTool())
    global_tool_manager.register_tool(CalculatorTool())