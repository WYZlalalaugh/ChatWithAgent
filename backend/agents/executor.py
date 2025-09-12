"""
智能体执行器
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from loguru import logger

from agents.react import ReActAgent, AgentManager
from agents.memory import MemoryManager, MemoryType
from app.services.llm_service import LLMService
from app.core.messages import UnifiedMessage


class ExecutionMode(str, Enum):
    """执行模式枚举"""
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"     # 并行执行
    PIPELINE = "pipeline"     # 流水线执行


class AgentTask:
    """智能体任务"""
    
    def __init__(
        self,
        task_id: str,
        query: str,
        agent_id: str,
        priority: int = 5,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 300
    ):
        self.task_id = task_id
        self.query = query
        self.agent_id = agent_id
        self.priority = priority
        self.context = context or {}
        self.timeout = timeout
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.status = "pending"


class TaskQueue:
    """任务队列"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.tasks: List[AgentTask] = []
        self.running_tasks: Dict[str, AgentTask] = {}
        self._lock = asyncio.Lock()
    
    async def add_task(self, task: AgentTask) -> bool:
        """添加任务"""
        async with self._lock:
            if len(self.tasks) >= self.max_size:
                logger.warning(f"任务队列已满: {self.max_size}")
                return False
            
            # 按优先级插入
            inserted = False
            for i, existing_task in enumerate(self.tasks):
                if task.priority > existing_task.priority:
                    self.tasks.insert(i, task)
                    inserted = True
                    break
            
            if not inserted:
                self.tasks.append(task)
            
            logger.info(f"任务已添加到队列: {task.task_id}")
            return True
    
    async def get_next_task(self) -> Optional[AgentTask]:
        """获取下一个任务"""
        async with self._lock:
            if self.tasks:
                task = self.tasks.pop(0)
                self.running_tasks[task.task_id] = task
                task.status = "running"
                task.started_at = datetime.utcnow()
                return task
            return None
    
    async def complete_task(self, task_id: str, result: Dict[str, Any]):
        """完成任务"""
        async with self._lock:
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                task.result = result
                del self.running_tasks[task_id]
                logger.info(f"任务完成: {task_id}")
    
    async def fail_task(self, task_id: str, error: str):
        """任务失败"""
        async with self._lock:
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.status = "failed"
                task.completed_at = datetime.utcnow()
                task.error = error
                del self.running_tasks[task_id]
                logger.error(f"任务失败: {task_id} - {error}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            "pending_tasks": len(self.tasks),
            "running_tasks": len(self.running_tasks),
            "queue_size": self.max_size
        }


class AgentExecutor:
    """智能体执行器"""
    
    def __init__(
        self,
        agent_manager: AgentManager,
        memory_manager: MemoryManager,
        max_concurrent_tasks: int = 10
    ):
        self.agent_manager = agent_manager
        self.memory_manager = memory_manager
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_queue = TaskQueue()
        self.running = False
        self.workers: List[asyncio.Task] = []
        self.execution_stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "average_execution_time": 0.0
        }
    
    async def start(self):
        """启动执行器"""
        if self.running:
            logger.warning("执行器已在运行")
            return
        
        self.running = True
        
        # 启动工作协程
        for i in range(self.max_concurrent_tasks):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
        
        logger.info(f"智能体执行器已启动，工作线程数: {self.max_concurrent_tasks}")
    
    async def stop(self):
        """停止执行器"""
        if not self.running:
            return
        
        self.running = False
        
        # 停止所有工作协程
        for worker in self.workers:
            worker.cancel()
        
        # 等待所有工作协程结束
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        logger.info("智能体执行器已停止")
    
    async def execute_query(
        self,
        query: str,
        agent_id: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 5,
        sync: bool = False
    ) -> Union[Dict[str, Any], str]:
        """执行查询"""
        task_id = str(uuid.uuid4())
        
        # 创建任务
        task = AgentTask(
            task_id=task_id,
            query=query,
            agent_id=agent_id,
            priority=priority,
            context=context or {}
        )
        
        # 添加对话ID到上下文
        if conversation_id:
            task.context["conversation_id"] = conversation_id
        
        # 添加到队列
        success = await self.task_queue.add_task(task)
        if not success:
            return {"success": False, "error": "任务队列已满"}
        
        if sync:
            # 同步等待结果
            return await self._wait_for_task_completion(task_id)
        else:
            # 异步执行，返回任务ID
            return {"success": True, "task_id": task_id}
    
    async def execute_conversation(
        self,
        message: UnifiedMessage,
        agent_id: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """执行对话"""
        try:
            # 获取对话记忆
            memory = self.memory_manager.get_conversation_memory(conversation_id)
            
            # 添加用户消息到记忆
            await memory.add_memory(
                content=f"用户: {message.content.text}",
                memory_type=MemoryType.SHORT_TERM,
                importance=0.6
            )
            
            # 获取上下文摘要
            context_summary = memory.get_context_summary()
            
            # 构建查询上下文
            context = {
                "conversation_id": conversation_id,
                "user_message": message.content.text,
                "context_summary": context_summary,
                "platform": message.platform.value,
                "sender": message.sender.dict()
            }
            
            # 执行查询
            result = await self.execute_query(
                query=message.content.text,
                agent_id=agent_id,
                conversation_id=conversation_id,
                context=context,
                priority=7,  # 对话优先级较高
                sync=True
            )
            
            if result.get("success"):
                # 添加助手回复到记忆
                assistant_reply = result.get("result", "")
                await memory.add_memory(
                    content=f"助手: {assistant_reply}",
                    memory_type=MemoryType.SHORT_TERM,
                    importance=0.7
                )
            
            return result
            
        except Exception as e:
            logger.error(f"执行对话失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _worker(self, worker_name: str):
        """工作协程"""
        logger.info(f"工作协程已启动: {worker_name}")
        
        while self.running:
            try:
                # 获取任务
                task = await self.task_queue.get_next_task()
                if not task:
                    await asyncio.sleep(0.1)
                    continue
                
                logger.info(f"{worker_name} 开始执行任务: {task.task_id}")
                
                # 执行任务
                result = await self._execute_task(task)
                
                # 更新统计
                self.execution_stats["total_tasks"] += 1
                
                if result.get("success"):
                    await self.task_queue.complete_task(task.task_id, result)
                    self.execution_stats["completed_tasks"] += 1
                else:
                    await self.task_queue.fail_task(task.task_id, result.get("error", "未知错误"))
                    self.execution_stats["failed_tasks"] += 1
                
                # 更新平均执行时间
                if task.completed_at and task.started_at:
                    execution_time = (task.completed_at - task.started_at).total_seconds()
                    total_time = self.execution_stats["average_execution_time"] * (self.execution_stats["total_tasks"] - 1)
                    self.execution_stats["average_execution_time"] = (total_time + execution_time) / self.execution_stats["total_tasks"]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"工作协程异常 {worker_name}: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"工作协程已停止: {worker_name}")
    
    async def _execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """执行任务"""
        try:
            # 获取智能体
            agent = self.agent_manager.get_agent(task.agent_id)
            if not agent:
                return {
                    "success": False,
                    "error": f"智能体不存在: {task.agent_id}"
                }
            
            # 设置上下文到智能体记忆
            if task.context:
                conversation_id = task.context.get("conversation_id")
                if conversation_id:
                    memory = self.memory_manager.get_conversation_memory(conversation_id)
                    
                    # 添加上下文信息到工作记忆
                    context_summary = task.context.get("context_summary", "")
                    if context_summary:
                        await memory.add_memory(
                            content=f"上下文: {context_summary}",
                            memory_type=MemoryType.WORKING,
                            importance=0.5
                        )
            
            # 执行智能体
            start_time = datetime.utcnow()
            result = await asyncio.wait_for(
                agent.run(task.query),
                timeout=task.timeout
            )
            end_time = datetime.utcnow()
            
            # 添加执行时间
            result["execution_time"] = (end_time - start_time).total_seconds()
            result["task_id"] = task.task_id
            
            return result
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"任务执行超时: {task.timeout}秒",
                "task_id": task.task_id
            }
        except Exception as e:
            logger.error(f"任务执行异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id
            }
    
    async def _wait_for_task_completion(
        self,
        task_id: str,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            # 检查任务是否在运行队列中
            if task_id in self.task_queue.running_tasks:
                await asyncio.sleep(0.5)
                continue
            
            # 查找已完成的任务（这里应该从持久存储或缓存中查找）
            # 暂时返回超时
            break
        
        return {
            "success": False,
            "error": "等待任务完成超时"
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取执行器状态"""
        return {
            "running": self.running,
            "workers": len(self.workers),
            "queue_status": self.task_queue.get_queue_status(),
            "stats": self.execution_stats
        }


# 全局执行器实例
agent_executor: Optional[AgentExecutor] = None


async def get_agent_executor() -> AgentExecutor:
    """获取智能体执行器"""
    global agent_executor
    if not agent_executor:
        from agents.react import get_agent_manager
        from agents.memory import get_memory_manager
        
        agent_manager = await get_agent_manager()
        memory_manager = await get_memory_manager()
        agent_executor = AgentExecutor(agent_manager, memory_manager)
        
        # 启动执行器
        await agent_executor.start()
    
    return agent_executor