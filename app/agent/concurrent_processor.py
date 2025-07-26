"""
Concurrent processing module for multi-agent system
并发处理模块 - 提供并发执行和任务调度功能
"""
import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable, TypeVar, Generic, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
from collections import defaultdict, deque
import weakref
from functools import wraps

from .exceptions import MultiAgentError, ConfigurationError
from .structured_logging import get_logger
from .monitoring import get_metrics_collector

# 临时定义 performance_monitor 装饰器，直到监控模块完善
def performance_monitor(operation_name: str):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                logger.debug(f"操作 {operation_name} 耗时: {duration:.3f}s")
        return wrapper
    return decorator

logger = get_logger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class ConcurrentTask(Generic[T]):
    """并发任务"""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[T] = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task_{int(time.time() * 1000000)}"
    
    @property
    def execution_time(self) -> Optional[float]:
        """获取执行时间"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def wait_time(self) -> Optional[float]:
        """获取等待时间"""
        if self.started_at:
            return (self.started_at - self.created_at).total_seconds()
        return None


class TaskQueue:
    """任务队列"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queues: Dict[TaskPriority, deque] = {
            priority: deque() for priority in TaskPriority
        }
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)
        self._not_full = asyncio.Condition(self._lock)
        self._size = 0
        
        self._stats = {
            "enqueued": 0,
            "dequeued": 0,
            "dropped": 0,
            "current_size": 0
        }
    
    async def put(self, task: ConcurrentTask, block: bool = True) -> bool:
        """添加任务到队列"""
        async with self._not_full:
            # 检查队列是否已满
            while self._size >= self.max_size:
                if not block:
                    self._stats["dropped"] += 1
                    return False
                await self._not_full.wait()
            
            # 添加任务到对应优先级队列
            self._queues[task.priority].append(task)
            self._size += 1
            self._stats["enqueued"] += 1
            self._stats["current_size"] = self._size
            
            # 通知等待的消费者
            async with self._not_empty:
                self._not_empty.notify()
            
            return True
    
    async def get(self, block: bool = True) -> Optional[ConcurrentTask]:
        """从队列获取任务"""
        async with self._not_empty:
            # 等待任务可用
            while self._size == 0:
                if not block:
                    return None
                await self._not_empty.wait()
            
            # 按优先级获取任务
            task = None
            for priority in sorted(TaskPriority, key=lambda x: x.value, reverse=True):
                if self._queues[priority]:
                    task = self._queues[priority].popleft()
                    break
            
            if task:
                self._size -= 1
                self._stats["dequeued"] += 1
                self._stats["current_size"] = self._size
                
                # 通知等待的生产者
                async with self._not_full:
                    self._not_full.notify()
            
            return task
    
    def qsize(self) -> int:
        """获取队列大小"""
        return self._size
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        return self._size == 0
    
    def full(self) -> bool:
        """检查队列是否已满"""
        return self._size >= self.max_size
    
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        priority_stats = {
            priority.name: len(queue) 
            for priority, queue in self._queues.items()
        }
        
        return {
            **self._stats,
            "max_size": self.max_size,
            "priority_distribution": priority_stats
        }


class WorkerPool:
    """工作线程池"""
    
    def __init__(
        self,
        max_workers: int = 5,
        worker_timeout: int = 300,
        queue_size: int = 1000
    ):
        self.max_workers = max_workers
        self.worker_timeout = worker_timeout
        self.task_queue = TaskQueue(queue_size)
        
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        self._stats = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "tasks_timeout": 0,
            "workers_created": 0,
            "workers_destroyed": 0,
            "active_workers": 0
        }
        
        # 任务结果存储
        self._task_results: Dict[str, ConcurrentTask] = {}
        self._result_callbacks: Dict[str, List[Callable]] = defaultdict(list)
    
    async def start(self) -> None:
        """启动工作池"""
        if self._running:
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        # 创建工作协程
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._workers.append(worker)
            self._stats["workers_created"] += 1
        
        self._stats["active_workers"] = len(self._workers)
        logger.info(f"工作池启动，工作协程数: {self.max_workers}")
    
    async def stop(self, timeout: int = 30) -> None:
        """停止工作池"""
        if not self._running:
            return
        
        logger.info("正在停止工作池...")
        self._running = False
        self._shutdown_event.set()
        
        # 等待所有工作协程完成
        if self._workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._workers, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning("工作协程停止超时，强制取消")
                for worker in self._workers:
                    worker.cancel()
        
        self._workers.clear()
        self._stats["active_workers"] = 0
        logger.info("工作池已停止")
    
    async def submit_task(
        self,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[int] = None,
        max_retries: int = 3,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """提交任务"""
        task = ConcurrentTask(
            task_id=task_id or f"task_{int(time.time() * 1000000)}",
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
            metadata=metadata or {}
        )
        
        success = await self.task_queue.put(task)
        if not success:
            raise MultiAgentError("任务队列已满，无法提交任务")
        
        logger.debug(f"任务已提交: {task.task_id}")
        return task.task_id
    
    async def get_task_result(
        self,
        task_id: str,
        timeout: Optional[int] = None
    ) -> ConcurrentTask:
        """获取任务结果"""
        start_time = time.time()
        
        while True:
            # 检查结果是否已准备好
            if task_id in self._task_results:
                return self._task_results[task_id]
            
            # 检查超时
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"等待任务结果超时: {task_id}")
            
            # 短暂等待
            await asyncio.sleep(0.1)
    
    def add_result_callback(self, task_id: str, callback: Callable) -> None:
        """添加结果回调"""
        self._result_callbacks[task_id].append(callback)
    
    async def _worker_loop(self, worker_name: str) -> None:
        """工作协程主循环"""
        logger.info(f"工作协程启动: {worker_name}")
        
        try:
            while self._running:
                try:
                    # 获取任务
                    task = await asyncio.wait_for(
                        self.task_queue.get(block=True),
                        timeout=1.0
                    )
                    
                    if task is None:
                        continue
                    
                    # 执行任务
                    await self._execute_task(task, worker_name)
                    
                except asyncio.TimeoutError:
                    # 正常的超时，继续循环
                    continue
                except Exception as e:
                    logger.error(f"工作协程异常 {worker_name}: {e}")
                    await asyncio.sleep(1)  # 避免快速失败循环
        
        except asyncio.CancelledError:
            logger.info(f"工作协程被取消: {worker_name}")
        
        finally:
            self._stats["workers_destroyed"] += 1
            logger.info(f"工作协程结束: {worker_name}")
    
    async def _execute_task(self, task: ConcurrentTask, worker_name: str) -> None:
        """执行任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        
        logger.debug(f"开始执行任务: {task.task_id} (worker: {worker_name})")
        
        try:
            # 设置超时
            timeout = task.timeout or self.worker_timeout
            
            # 执行任务函数
            if asyncio.iscoroutinefunction(task.func):
                result = await asyncio.wait_for(
                    task.func(*task.args, **task.kwargs),
                    timeout=timeout
                )
            else:
                # 在线程池中执行同步函数
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: task.func(*task.args, **task.kwargs)
                    ),
                    timeout=timeout
                )
            
            # 任务成功完成
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            self._stats["tasks_processed"] += 1
            logger.debug(f"任务执行成功: {task.task_id}")
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error = TimeoutError(f"任务执行超时: {timeout}s")
            task.completed_at = datetime.utcnow()
            
            self._stats["tasks_timeout"] += 1
            logger.warning(f"任务执行超时: {task.task_id}")
            
        except Exception as e:
            task.error = e
            task.completed_at = datetime.utcnow()
            
            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.started_at = None
                task.completed_at = None
                
                # 重新加入队列
                await self.task_queue.put(task, block=False)
                logger.info(f"任务重试: {task.task_id} (第{task.retry_count}次)")
                return
            else:
                task.status = TaskStatus.FAILED
                self._stats["tasks_failed"] += 1
                logger.error(f"任务执行失败: {task.task_id}, 错误: {e}")
        
        # 存储结果
        self._task_results[task.task_id] = task
        
        # 调用回调函数
        for callback in self._result_callbacks.get(task.task_id, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"任务回调执行失败: {e}")
        
        # 清理回调
        self._result_callbacks.pop(task.task_id, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取工作池统计"""
        return {
            **self._stats,
            "max_workers": self.max_workers,
            "running": self._running,
            "queue_stats": self.task_queue.get_stats(),
            "pending_results": len(self._task_results)
        }
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        if task_id in self._task_results:
            return self._task_results[task_id].status
        
        # 检查是否在队列中
        for priority_queue in self.task_queue._queues.values():
            for task in priority_queue:
                if task.task_id == task_id:
                    return task.status
        
        return None


class ConcurrentProcessor:
    """并发处理器"""
    
    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        worker_timeout: int = 300,
        queue_size: int = 1000
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.worker_pool = WorkerPool(max_concurrent_tasks, worker_timeout, queue_size)
        
        # Agent专用处理池
        self._agent_pools: Dict[str, WorkerPool] = {}
        
        # 批处理支持
        self._batch_tasks: Dict[str, List[ConcurrentTask]] = {}
        self._batch_locks: Dict[str, asyncio.Lock] = {}
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化处理器"""
        if self._initialized:
            return
        
        await self.worker_pool.start()
        self._initialized = True
        logger.info("并发处理器初始化完成")
    
    async def shutdown(self) -> None:
        """关闭处理器"""
        if not self._initialized:
            return
        
        # 停止主工作池
        await self.worker_pool.stop()
        
        # 停止Agent专用池
        for pool in self._agent_pools.values():
            await pool.stop()
        
        self._agent_pools.clear()
        self._initialized = False
        logger.info("并发处理器已关闭")
    
    async def submit_agent_task(
        self,
        agent_name: str,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[int] = None,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """提交Agent任务"""
        if not self._initialized:
            raise ConfigurationError("并发处理器未初始化")
        
        # 为Agent创建专用池（如果不存在）
        if agent_name not in self._agent_pools:
            self._agent_pools[agent_name] = WorkerPool(
                max_workers=2,  # 每个Agent最多2个并发任务
                worker_timeout=timeout or 300,
                queue_size=100
            )
            await self._agent_pools[agent_name].start()
        
        pool = self._agent_pools[agent_name]
        task_id = await pool.submit_task(
            func, *args,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
            metadata={"agent_name": agent_name},
            **kwargs
        )
        
        # 记录指标
        get_metrics_collector().increment_counter(
            "concurrent_processor.agent_tasks",
            labels={"agent": agent_name, "priority": priority.name}
        )
        
        return task_id
    
    async def submit_batch_tasks(
        self,
        batch_id: str,
        tasks: List[Tuple[Callable, tuple, dict]],
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[int] = None,
        max_retries: int = 3
    ) -> List[str]:
        """提交批量任务"""
        if not self._initialized:
            raise ConfigurationError("并发处理器未初始化")
        
        # 创建批处理锁
        if batch_id not in self._batch_locks:
            self._batch_locks[batch_id] = asyncio.Lock()
        
        task_ids = []
        
        async with self._batch_locks[batch_id]:
            self._batch_tasks[batch_id] = []
            
            for func, args, kwargs in tasks:
                task_id = await self.worker_pool.submit_task(
                    func, *args,
                    priority=priority,
                    timeout=timeout,
                    max_retries=max_retries,
                    metadata={"batch_id": batch_id},
                    **kwargs
                )
                task_ids.append(task_id)
        
        logger.info(f"批量任务已提交: {batch_id}, 任务数: {len(task_ids)}")
        return task_ids
    
    async def wait_for_batch(
        self,
        batch_id: str,
        task_ids: List[str],
        timeout: Optional[int] = None
    ) -> List[ConcurrentTask]:
        """等待批量任务完成"""
        results = []
        
        for task_id in task_ids:
            try:
                result = await self.worker_pool.get_task_result(task_id, timeout)
                results.append(result)
            except Exception as e:
                logger.error(f"获取批量任务结果失败 {task_id}: {e}")
                # 创建失败的任务结果
                failed_task = ConcurrentTask(
                    task_id=task_id,
                    func=lambda: None,
                    args=(),
                    kwargs={},
                    status=TaskStatus.FAILED,
                    error=e
                )
                results.append(failed_task)
        
        # 清理批处理数据
        self._batch_tasks.pop(batch_id, None)
        self._batch_locks.pop(batch_id, None)
        
        logger.info(f"批量任务完成: {batch_id}")
        return results
    
    async def execute_parallel_agents(
        self,
        agent_tasks: Dict[str, Tuple[Callable, tuple, dict]],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """并行执行多个Agent任务"""
        if not agent_tasks:
            return {}
        
        # 提交所有Agent任务
        task_futures = {}
        for agent_name, (func, args, kwargs) in agent_tasks.items():
            task_id = await self.submit_agent_task(
                agent_name, func, *args,
                timeout=timeout,
                **kwargs
            )
            task_futures[agent_name] = task_id
        
        # 等待所有任务完成
        results = {}
        for agent_name, task_id in task_futures.items():
            try:
                task_result = await self.worker_pool.get_task_result(task_id, timeout)
                if task_result.status == TaskStatus.COMPLETED:
                    results[agent_name] = task_result.result
                else:
                    results[agent_name] = {
                        "error": str(task_result.error),
                        "status": task_result.status.value
                    }
            except Exception as e:
                results[agent_name] = {
                    "error": str(e),
                    "status": "timeout"
                }
        
        return results
    
    @performance_monitor("concurrent_processor.execute_with_fallback")
    @performance_monitor("concurrent_processor.execute_with_fallback")
    async def execute_with_fallback(
        self,
        primary_func: Callable,
        fallback_func: Callable,
        *args,
        timeout: Optional[int] = None,
        **kwargs
    ) -> Any:
        """执行任务，失败时使用备用方案"""
        try:
            # 尝试执行主要函数
            task_id = await self.worker_pool.submit_task(
                primary_func, *args,
                timeout=timeout,
                max_retries=1,
                **kwargs
            )
            
            result = await self.worker_pool.get_task_result(task_id, timeout)
            
            if result.status == TaskStatus.COMPLETED:
                return result.result
            else:
                logger.warning(f"主要函数执行失败，使用备用方案: {result.error}")
                raise result.error
        
        except Exception as e:
            logger.info(f"执行备用方案: {e}")
            
            # 执行备用函数
            fallback_task_id = await self.worker_pool.submit_task(
                fallback_func, *args,
                timeout=timeout,
                max_retries=2,
                **kwargs
            )
            
            fallback_result = await self.worker_pool.get_task_result(fallback_task_id, timeout)
            
            if fallback_result.status == TaskStatus.COMPLETED:
                return fallback_result.result
            else:
                raise MultiAgentError(f"主要和备用方案都失败了: {fallback_result.error}")
    
    async def execute_with_circuit_breaker(
        self,
        func: Callable,
        *args,
        circuit_breaker_key: str = "default",
        timeout: Optional[int] = None,
        **kwargs
    ) -> Any:
        """使用熔断器执行任务"""
        from ..core.performance import CircuitBreaker
        
        # 获取或创建熔断器
        if not hasattr(self, '_circuit_breakers'):
            self._circuit_breakers = {}
        
        if circuit_breaker_key not in self._circuit_breakers:
            self._circuit_breakers[circuit_breaker_key] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60
            )
        
        circuit_breaker = self._circuit_breakers[circuit_breaker_key]
        
        # 使用熔断器执行任务
        async def wrapped_func():
            task_id = await self.worker_pool.submit_task(
                func, *args,
                timeout=timeout,
                **kwargs
            )
            result = await self.worker_pool.get_task_result(task_id, timeout)
            
            if result.status == TaskStatus.COMPLETED:
                return result.result
            else:
                raise Exception(f"Task failed: {result.error}")
        
        return await circuit_breaker.call(wrapped_func)
    
    async def execute_with_adaptive_timeout(
        self,
        func: Callable,
        *args,
        base_timeout: int = 30,
        max_timeout: int = 300,
        **kwargs
    ) -> Any:
        """使用自适应超时执行任务"""
        from ..core.performance import get_performance_monitor
        
        monitor = get_performance_monitor()
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)
        
        # 获取历史性能数据
        stats = monitor.get_stats(func_name)
        
        # 计算自适应超时
        if stats and stats.get('avg'):
            # 基于平均执行时间的3倍作为超时时间
            adaptive_timeout = min(int(stats['avg'] * 3), max_timeout)
            adaptive_timeout = max(adaptive_timeout, base_timeout)
        else:
            adaptive_timeout = base_timeout
        
        logger.debug(f"使用自适应超时 {adaptive_timeout}s 执行 {func_name}")
        
        task_id = await self.worker_pool.submit_task(
            func, *args,
            timeout=adaptive_timeout,
            **kwargs
        )
        
        result = await self.worker_pool.get_task_result(task_id, adaptive_timeout + 10)
        
        if result.status == TaskStatus.COMPLETED:
            return result.result
        else:
            raise MultiAgentError(f"任务执行失败: {result.error}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取处理器统计"""
        agent_stats = {
            name: pool.get_stats()
            for name, pool in self._agent_pools.items()
        }
        
        return {
            "initialized": self._initialized,
            "main_pool": self.worker_pool.get_stats(),
            "agent_pools": agent_stats,
            "active_batches": len(self._batch_tasks)
        }


# 全局并发处理器实例
_concurrent_processor: Optional[ConcurrentProcessor] = None


async def get_concurrent_processor() -> ConcurrentProcessor:
    """获取全局并发处理器实例"""
    global _concurrent_processor
    
    if _concurrent_processor is None:
        from ..core.config import settings
        
        _concurrent_processor = ConcurrentProcessor(
            max_concurrent_tasks=getattr(settings, 'MAX_CONCURRENT_AGENTS', 10),
            worker_timeout=300,
            queue_size=1000
        )
        await _concurrent_processor.initialize()
    
    return _concurrent_processor


async def cleanup_concurrent_processor() -> None:
    """清理并发处理器"""
    global _concurrent_processor
    
    if _concurrent_processor:
        await _concurrent_processor.shutdown()
        _concurrent_processor = None