"""
ReAct 智能体框架
Reasoning (推理) + Acting (行动) 循环框架
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
from loguru import logger

from app.services.llm_service import LLMService, ModelResponse


class ActionStatus(str, Enum):
    """行动状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class StepType(str, Enum):
    """步骤类型枚举"""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL = "final"


class AgentStep:
    """智能体执行步骤"""
    
    def __init__(
        self,
        step_type: StepType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.step_id = str(uuid.uuid4())
        self.step_type = step_type
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.utcnow()


class AgentAction:
    """智能体行动"""
    
    def __init__(
        self,
        tool_name: str,
        tool_input: Union[str, Dict[str, Any]],
        thought: str = "",
        action_id: Optional[str] = None
    ):
        self.action_id = action_id or str(uuid.uuid4())
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.thought = thought
        self.status = ActionStatus.PENDING
        self.result: Optional[str] = None
        self.error: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None


class AgentFinish:
    """智能体完成"""
    
    def __init__(self, return_values: Dict[str, Any], log: str = ""):
        self.return_values = return_values
        self.log = log


class BaseTool(ABC):
    """工具基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """执行工具"""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具模式"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_parameters_schema()
        }
    
    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """获取参数模式"""
        pass


class SearchTool(BaseTool):
    """搜索工具"""
    
    def __init__(self):
        super().__init__(
            name="search",
            description="搜索相关信息。输入搜索查询，返回搜索结果。"
        )
    
    async def execute(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """执行搜索"""
        try:
            if isinstance(input_data, dict):
                query = input_data.get("query", "")
            else:
                query = str(input_data)
            
            # 这里可以集成真实的搜索API
            # 暂时返回模拟结果
            result = f"搜索结果：关于'{query}'的相关信息..."
            logger.info(f"搜索工具执行: {query}")
            return result
            
        except Exception as e:
            logger.error(f"搜索工具执行失败: {e}")
            return f"搜索失败: {str(e)}"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询"
                }
            },
            "required": ["query"]
        }


class CalculatorTool(BaseTool):
    """计算器工具"""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="执行数学计算。输入数学表达式，返回计算结果。"
        )
    
    async def execute(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """执行计算"""
        try:
            if isinstance(input_data, dict):
                expression = input_data.get("expression", "")
            else:
                expression = str(input_data)
            
            # 安全的数学计算
            # 注意：在生产环境中需要更严格的安全检查
            allowed_chars = set("0123456789+-*/().,")
            if not all(c in allowed_chars for c in expression.replace(" ", "")):
                return "计算表达式包含非法字符"
            
            result = eval(expression)
            logger.info(f"计算器工具执行: {expression} = {result}")
            return str(result)
            
        except Exception as e:
            logger.error(f"计算器工具执行失败: {e}")
            return f"计算失败: {str(e)}"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式"
                }
            },
            "required": ["expression"]
        }


class KnowledgeSearchTool(BaseTool):
    """知识库搜索工具"""
    
    def __init__(self, knowledge_service=None):
        super().__init__(
            name="knowledge_search",
            description="在知识库中搜索相关信息。输入查询内容，返回知识库中的相关信息。"
        )
        self.knowledge_service = knowledge_service
    
    async def execute(self, input_data: Union[str, Dict[str, Any]]) -> str:
        """执行知识库搜索"""
        try:
            if isinstance(input_data, dict):
                query = input_data.get("query", "")
                knowledge_base_id = input_data.get("knowledge_base_id")
            else:
                query = str(input_data)
                knowledge_base_id = None
            
            if self.knowledge_service:
                # 调用知识库服务
                results = await self.knowledge_service.search(query, knowledge_base_id)
                return f"知识库搜索结果: {results}"
            else:
                # 模拟结果
                result = f"知识库中关于'{query}'的信息..."
                logger.info(f"知识库搜索工具执行: {query}")
                return result
                
        except Exception as e:
            logger.error(f"知识库搜索工具执行失败: {e}")
            return f"知识库搜索失败: {str(e)}"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询"
                },
                "knowledge_base_id": {
                    "type": "string",
                    "description": "知识库ID（可选）"
                }
            },
            "required": ["query"]
        }


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """注册默认工具"""
        self.register_tool(SearchTool())
        self.register_tool(CalculatorTool())
        self.register_tool(KnowledgeSearchTool())
    
    def register_tool(self, tool: BaseTool):
        """注册工具"""
        self._tools[tool.name] = tool
        logger.info(f"工具已注册: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[BaseTool]:
        """列出所有工具"""
        return list(self._tools.values())
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取所有工具的模式"""
        return [tool.get_schema() for tool in self._tools.values()]


class AgentMemory:
    """智能体记忆"""
    
    def __init__(self, max_steps: int = 100):
        self.max_steps = max_steps
        self.steps: List[AgentStep] = []
        self.context: Dict[str, Any] = {}
    
    def add_step(self, step: AgentStep):
        """添加步骤"""
        self.steps.append(step)
        
        # 保持记忆大小限制
        if len(self.steps) > self.max_steps:
            self.steps = self.steps[-self.max_steps:]
    
    def get_recent_steps(self, count: int = 10) -> List[AgentStep]:
        """获取最近的步骤"""
        return self.steps[-count:]
    
    def get_context(self, key: str) -> Any:
        """获取上下文"""
        return self.context.get(key)
    
    def set_context(self, key: str, value: Any):
        """设置上下文"""
        self.context[key] = value
    
    def clear(self):
        """清除记忆"""
        self.steps.clear()
        self.context.clear()


class ReActAgent:
    """ReAct 智能体"""
    
    def __init__(
        self,
        llm_service: LLMService,
        model_id: str,
        tool_registry: ToolRegistry,
        memory: Optional[AgentMemory] = None,
        max_iterations: int = 10,
        max_execution_time: int = 300  # 5分钟
    ):
        self.llm_service = llm_service
        self.model_id = model_id
        self.tool_registry = tool_registry
        self.memory = memory or AgentMemory()
        self.max_iterations = max_iterations
        self.max_execution_time = max_execution_time
        
        # ReAct 提示词模板
        self.react_prompt = self._get_react_prompt()
    
    def _get_react_prompt(self) -> str:
        """获取 ReAct 提示词模板"""
        tools_desc = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tool_registry.list_tools()
        ])
        
        return f"""你是一个智能助手，可以使用以下工具来回答问题：

{tools_desc}

请使用以下格式回答问题：

Thought: 我需要思考这个问题...
Action: tool_name
Action Input: tool_input
Observation: 工具返回的结果
... (这个 Thought/Action/Action Input/Observation 可以重复)
Thought: 我现在知道最终答案了
Final Answer: 最终答案

开始吧！

Question: {{question}}
{{agent_scratchpad}}"""
    
    async def run(self, question: str) -> Dict[str, Any]:
        """运行智能体"""
        logger.info(f"ReAct 智能体开始处理问题: {question}")
        
        start_time = datetime.utcnow()
        iterations = 0
        agent_scratchpad = ""
        
        # 添加初始问题到记忆
        self.memory.add_step(AgentStep(
            step_type=StepType.THOUGHT,
            content=f"用户问题: {question}"
        ))
        
        try:
            while iterations < self.max_iterations:
                # 检查执行时间
                if (datetime.utcnow() - start_time).total_seconds() > self.max_execution_time:
                    logger.warning("智能体执行超时")
                    break
                
                iterations += 1
                logger.debug(f"ReAct 迭代 {iterations}")
                
                # 构建提示词
                prompt = self.react_prompt.format(
                    question=question,
                    agent_scratchpad=agent_scratchpad
                )
                
                # 调用 LLM
                messages = [{"role": "user", "content": prompt}]
                response = await self.llm_service.chat(
                    model_id=self.model_id,
                    messages=messages,
                    temperature=0.1
                )
                
                if not isinstance(response, ModelResponse):
                    logger.error("LLM 返回类型错误")
                    break
                
                llm_output = response.content
                logger.debug(f"LLM 输出: {llm_output}")
                
                # 解析 LLM 输出
                parsed_output = self._parse_llm_output(llm_output)
                
                if isinstance(parsed_output, AgentFinish):
                    # 智能体完成
                    self.memory.add_step(AgentStep(
                        step_type=StepType.FINAL,
                        content=parsed_output.return_values.get("output", ""),
                        metadata={"log": parsed_output.log}
                    ))
                    
                    return {
                        "success": True,
                        "result": parsed_output.return_values.get("output", ""),
                        "iterations": iterations,
                        "steps": [step.__dict__ for step in self.memory.steps],
                        "execution_time": (datetime.utcnow() - start_time).total_seconds()
                    }
                
                elif isinstance(parsed_output, AgentAction):
                    # 执行行动
                    action_result = await self._execute_action(parsed_output)
                    
                    # 更新记忆
                    self.memory.add_step(AgentStep(
                        step_type=StepType.THOUGHT,
                        content=parsed_output.thought
                    ))
                    
                    self.memory.add_step(AgentStep(
                        step_type=StepType.ACTION,
                        content=f"{parsed_output.tool_name}: {parsed_output.tool_input}",
                        metadata={"action_id": parsed_output.action_id}
                    ))
                    
                    self.memory.add_step(AgentStep(
                        step_type=StepType.OBSERVATION,
                        content=action_result,
                        metadata={"action_id": parsed_output.action_id}
                    ))
                    
                    # 更新 scratchpad
                    agent_scratchpad += f"\nThought: {parsed_output.thought}"
                    agent_scratchpad += f"\nAction: {parsed_output.tool_name}"
                    agent_scratchpad += f"\nAction Input: {parsed_output.tool_input}"
                    agent_scratchpad += f"\nObservation: {action_result}"
                
                else:
                    logger.error(f"无法解析 LLM 输出: {llm_output}")
                    break
            
            # 达到最大迭代次数
            logger.warning(f"达到最大迭代次数: {self.max_iterations}")
            return {
                "success": False,
                "result": "达到最大迭代次数，未能完成任务",
                "iterations": iterations,
                "steps": [step.__dict__ for step in self.memory.steps],
                "execution_time": (datetime.utcnow() - start_time).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"ReAct 智能体执行失败: {e}")
            return {
                "success": False,
                "result": f"执行失败: {str(e)}",
                "iterations": iterations,
                "steps": [step.__dict__ for step in self.memory.steps],
                "execution_time": (datetime.utcnow() - start_time).total_seconds()
            }
    
    def _parse_llm_output(self, text: str) -> Union[AgentAction, AgentFinish]:
        """解析 LLM 输出"""
        try:
            # 查找最终答案
            if "Final Answer:" in text:
                final_answer_start = text.rfind("Final Answer:")
                final_answer = text[final_answer_start + len("Final Answer:"):].strip()
                return AgentFinish(
                    return_values={"output": final_answer},
                    log=text
                )
            
            # 解析思考、行动和输入
            thought = ""
            action = ""
            action_input = ""
            
            lines = text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("Thought:"):
                    current_section = "thought"
                    thought = line[len("Thought:"):].strip()
                elif line.startswith("Action:"):
                    current_section = "action"
                    action = line[len("Action:"):].strip()
                elif line.startswith("Action Input:"):
                    current_section = "action_input"
                    action_input = line[len("Action Input:"):].strip()
                elif current_section == "thought" and line:
                    thought += " " + line
                elif current_section == "action" and line:
                    action += " " + line
                elif current_section == "action_input" and line:
                    action_input += " " + line
            
            if action and action_input:
                return AgentAction(
                    tool_name=action,
                    tool_input=action_input,
                    thought=thought
                )
            
            # 如果无法解析，返回默认完成
            return AgentFinish(
                return_values={"output": "无法解析响应"},
                log=text
            )
            
        except Exception as e:
            logger.error(f"解析 LLM 输出失败: {e}")
            return AgentFinish(
                return_values={"output": f"解析失败: {str(e)}"},
                log=text
            )
    
    async def _execute_action(self, action: AgentAction) -> str:
        """执行行动"""
        try:
            action.status = ActionStatus.RUNNING
            action.start_time = datetime.utcnow()
            
            # 获取工具
            tool = self.tool_registry.get_tool(action.tool_name)
            if not tool:
                action.status = ActionStatus.FAILED
                action.error = f"工具不存在: {action.tool_name}"
                action.end_time = datetime.utcnow()
                return action.error
            
            # 执行工具
            result = await tool.execute(action.tool_input)
            
            action.status = ActionStatus.SUCCESS
            action.result = result
            action.end_time = datetime.utcnow()
            
            logger.info(f"工具执行成功: {action.tool_name}")
            return result
            
        except Exception as e:
            action.status = ActionStatus.FAILED
            action.error = str(e)
            action.end_time = datetime.utcnow()
            
            logger.error(f"工具执行失败: {action.tool_name} - {e}")
            return f"工具执行失败: {str(e)}"


class AgentManager:
    """智能体管理器"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.tool_registry = ToolRegistry()
        self.agents: Dict[str, ReActAgent] = {}
    
    def create_agent(
        self,
        agent_id: str,
        model_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ReActAgent:
        """创建智能体"""
        config = config or {}
        
        agent = ReActAgent(
            llm_service=self.llm_service,
            model_id=model_id,
            tool_registry=self.tool_registry,
            memory=AgentMemory(max_steps=config.get("max_memory_steps", 100)),
            max_iterations=config.get("max_iterations", 10),
            max_execution_time=config.get("max_execution_time", 300)
        )
        
        self.agents[agent_id] = agent
        logger.info(f"智能体已创建: {agent_id}")
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[ReActAgent]:
        """获取智能体"""
        return self.agents.get(agent_id)
    
    def remove_agent(self, agent_id: str) -> bool:
        """移除智能体"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"智能体已移除: {agent_id}")
            return True
        return False
    
    def register_tool(self, tool: BaseTool):
        """注册工具"""
        self.tool_registry.register_tool(tool)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具"""
        return self.tool_registry.get_tools_schema()


# 全局智能体管理器实例
agent_manager: Optional[AgentManager] = None


async def get_agent_manager() -> AgentManager:
    """获取智能体管理器"""
    global agent_manager
    if not agent_manager:
        from app.services.llm_service import get_llm_service
        llm_service = await get_llm_service()
        agent_manager = AgentManager(llm_service)
    
    return agent_manager