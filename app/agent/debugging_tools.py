"""
Debugging and Troubleshooting Tools for Multi-Agent System
多代理系统调试和故障排查工具
"""
import asyncio
import inspect
import json
import time
import traceback
import sys
from typing import Dict, List, Optional, Any, Callable, Union, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import contextmanager
import threading
import functools

from .structured_logging import get_logger, LogContext
from .monitoring import get_metrics_collector, get_performance_monitor
from .exceptions import MultiAgentError, ErrorCategory, ErrorSeverity

logger = get_logger(__name__)


@dataclass
class DebugEvent:
    """调试事件"""
    timestamp: datetime
    event_type: str
    component: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    thread_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "component": self.component,
            "message": self.message,
            "data": self.data,
            "stack_trace": self.stack_trace,
            "thread_id": self.thread_id
        }


@dataclass
class FunctionCall:
    """函数调用记录"""
    function_name: str
    module: str
    args: tuple
    kwargs: dict
    start_time: float
    end_time: Optional[float] = None
    result: Any = None
    exception: Optional[Exception] = None
    duration: Optional[float] = None
    
    def finish(self, result: Any = None, exception: Optional[Exception] = None):
        """完成函数调用记录"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.result = result
        self.exception = exception
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "function_name": self.function_name,
            "module": self.module,
            "args": str(self.args),
            "kwargs": str(self.kwargs),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "result": str(self.result) if self.result is not None else None,
            "exception": str(self.exception) if self.exception else None,
            "success": self.exception is None
        }


class DebugTracer:
    """调试跟踪器"""
    
    def __init__(self, max_events: int = 1000, max_calls: int = 500):
        self.max_events = max_events
        self.max_calls = max_calls
        self.events: deque = deque(maxlen=max_events)
        self.function_calls: deque = deque(maxlen=max_calls)
        self.active_calls: Dict[int, FunctionCall] = {}
        self.enabled = False
        self._lock = threading.Lock()
    
    def enable(self):
        """启用调试跟踪"""
        self.enabled = True
        logger.info("Debug tracing enabled")
    
    def disable(self):
        """禁用调试跟踪"""
        self.enabled = False
        logger.info("Debug tracing disabled")
    
    def add_event(
        self,
        event_type: str,
        component: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        include_stack: bool = False
    ):
        """添加调试事件"""
        if not self.enabled:
            return
        
        with self._lock:
            event = DebugEvent(
                timestamp=datetime.now(),
                event_type=event_type,
                component=component,
                message=message,
                data=data or {},
                stack_trace=traceback.format_stack() if include_stack else None,
                thread_id=threading.get_ident()
            )
            self.events.append(event)
    
    def start_function_call(
        self,
        function_name: str,
        module: str,
        args: tuple,
        kwargs: dict
    ) -> int:
        """开始函数调用跟踪"""
        if not self.enabled:
            return -1
        
        call_id = id((function_name, time.time()))
        
        with self._lock:
            call = FunctionCall(
                function_name=function_name,
                module=module,
                args=args,
                kwargs=kwargs,
                start_time=time.time()
            )
            self.active_calls[call_id] = call
        
        return call_id
    
    def finish_function_call(
        self,
        call_id: int,
        result: Any = None,
        exception: Optional[Exception] = None
    ):
        """完成函数调用跟踪"""
        if not self.enabled or call_id == -1:
            return
        
        with self._lock:
            if call_id in self.active_calls:
                call = self.active_calls.pop(call_id)
                call.finish(result, exception)
                self.function_calls.append(call)
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        component: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[DebugEvent]:
        """获取调试事件"""
        with self._lock:
            events = list(self.events)
        
        # 过滤事件
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if component:
            events = [e for e in events if e.component == component]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        return events
    
    def get_function_calls(
        self,
        function_name: Optional[str] = None,
        module: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[FunctionCall]:
        """获取函数调用记录"""
        with self._lock:
            calls = list(self.function_calls)
        
        # 过滤调用
        if function_name:
            calls = [c for c in calls if c.function_name == function_name]
        
        if module:
            calls = [c for c in calls if c.module == module]
        
        if since:
            calls = [c for c in calls if datetime.fromtimestamp(c.start_time) >= since]
        
        return calls
    
    def get_active_calls(self) -> List[FunctionCall]:
        """获取活跃的函数调用"""
        with self._lock:
            return list(self.active_calls.values())
    
    def clear(self):
        """清除所有跟踪数据"""
        with self._lock:
            self.events.clear()
            self.function_calls.clear()
            self.active_calls.clear()
        logger.info("Debug trace data cleared")


class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self):
        self.profiles: Dict[str, List[float]] = defaultdict(list)
        self.enabled = False
        self._lock = threading.Lock()
    
    def enable(self):
        """启用性能分析"""
        self.enabled = True
        logger.info("Performance profiling enabled")
    
    def disable(self):
        """禁用性能分析"""
        self.enabled = False
        logger.info("Performance profiling disabled")
    
    def record(self, operation: str, duration: float):
        """记录性能数据"""
        if not self.enabled:
            return
        
        with self._lock:
            self.profiles[operation].append(duration)
            # 保持最近1000个记录
            if len(self.profiles[operation]) > 1000:
                self.profiles[operation] = self.profiles[operation][-1000:]
    
    def get_stats(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """获取性能统计"""
        with self._lock:
            if operation:
                if operation not in self.profiles:
                    return {}
                durations = self.profiles[operation]
                return self._calculate_stats(operation, durations)
            else:
                stats = {}
                for op, durations in self.profiles.items():
                    stats[op] = self._calculate_stats(op, durations)
                return stats
    
    def _calculate_stats(self, operation: str, durations: List[float]) -> Dict[str, Any]:
        """计算统计数据"""
        if not durations:
            return {"operation": operation, "count": 0}
        
        sorted_durations = sorted(durations)
        count = len(durations)
        
        return {
            "operation": operation,
            "count": count,
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / count,
            "median": sorted_durations[count // 2],
            "p95": sorted_durations[int(count * 0.95)],
            "p99": sorted_durations[int(count * 0.99)]
        }
    
    def clear(self):
        """清除性能数据"""
        with self._lock:
            self.profiles.clear()
        logger.info("Performance profile data cleared")


class SystemDiagnostics:
    """系统诊断工具"""
    
    def __init__(self):
        self.tracer = DebugTracer()
        self.profiler = PerformanceProfiler()
    
    def run_health_check(self) -> Dict[str, Any]:
        """运行系统健康检查"""
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }
        
        # 检查内存使用
        try:
            import psutil
            memory = psutil.virtual_memory()
            health_status["checks"]["memory"] = {
                "status": "healthy" if memory.percent < 80 else "warning",
                "usage_percent": memory.percent,
                "available_gb": memory.available / (1024**3)
            }
        except Exception as e:
            health_status["checks"]["memory"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 检查磁盘空间
        try:
            import psutil
            disk = psutil.disk_usage('/')
            health_status["checks"]["disk"] = {
                "status": "healthy" if disk.percent < 90 else "warning",
                "usage_percent": disk.percent,
                "free_gb": disk.free / (1024**3)
            }
        except Exception as e:
            health_status["checks"]["disk"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 检查活跃线程数
        try:
            thread_count = threading.active_count()
            health_status["checks"]["threads"] = {
                "status": "healthy" if thread_count < 100 else "warning",
                "active_count": thread_count
            }
        except Exception as e:
            health_status["checks"]["threads"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 检查错误率
        try:
            metrics = get_metrics_collector()
            summary = metrics.get_summary()
            error_count = sum(summary.get("counters", {}).get(k, 0) 
                            for k in summary.get("counters", {}) 
                            if "error" in k.lower())
            total_operations = sum(summary.get("counters", {}).values())
            
            error_rate = error_count / total_operations if total_operations > 0 else 0
            health_status["checks"]["error_rate"] = {
                "status": "healthy" if error_rate < 0.05 else "warning",
                "error_rate": error_rate,
                "error_count": error_count,
                "total_operations": total_operations
            }
        except Exception as e:
            health_status["checks"]["error_rate"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 确定整体状态
        check_statuses = [check.get("status", "error") for check in health_status["checks"].values()]
        if "error" in check_statuses:
            health_status["overall_status"] = "error"
        elif "warning" in check_statuses:
            health_status["overall_status"] = "warning"
        
        return health_status
    
    def generate_debug_report(self) -> Dict[str, Any]:
        """生成调试报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self._get_system_info(),
            "health_check": self.run_health_check(),
            "recent_events": [e.to_dict() for e in self.tracer.get_events(since=datetime.now() - timedelta(hours=1))],
            "recent_function_calls": [c.to_dict() for c in self.tracer.get_function_calls(since=datetime.now() - timedelta(hours=1))],
            "active_calls": [c.to_dict() for c in self.tracer.get_active_calls()],
            "performance_stats": self.profiler.get_stats(),
            "metrics_summary": get_metrics_collector().get_summary()
        }
        
        return report
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "thread_count": threading.active_count()
        }
        
        try:
            import psutil
            info.update({
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
                "disk_total_gb": psutil.disk_usage('/').total / (1024**3)
            })
        except ImportError:
            pass
        
        return info
    
    def export_debug_data(self, filepath: str, format: str = "json"):
        """导出调试数据"""
        report = self.generate_debug_report()
        
        if format == "json":
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Debug data exported to {filepath}")


def debug_trace(component: str = None, event_type: str = "function_call"):
    """调试跟踪装饰器"""
    def decorator(func):
        comp = component or func.__module__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_debug_tracer()
            profiler = get_performance_profiler()
            
            # 开始跟踪
            call_id = tracer.start_function_call(
                func.__name__,
                func.__module__,
                args,
                kwargs
            )
            
            tracer.add_event(
                event_type,
                comp,
                f"Function {func.__name__} started",
                {"args_count": len(args), "kwargs_count": len(kwargs)}
            )
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 记录成功
                tracer.finish_function_call(call_id, result=result)
                profiler.record(f"{comp}.{func.__name__}", duration)
                
                tracer.add_event(
                    event_type,
                    comp,
                    f"Function {func.__name__} completed successfully",
                    {"duration": duration}
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # 记录异常
                tracer.finish_function_call(call_id, exception=e)
                profiler.record(f"{comp}.{func.__name__}", duration)
                
                tracer.add_event(
                    "error",
                    comp,
                    f"Function {func.__name__} failed",
                    {"duration": duration, "error": str(e)},
                    include_stack=True
                )
                
                raise
        
        return wrapper
    
    return decorator


@contextmanager
def debug_context(component: str, operation: str, **context_data):
    """调试上下文管理器"""
    tracer = get_debug_tracer()
    
    tracer.add_event(
        "context_start",
        component,
        f"Started {operation}",
        context_data
    )
    
    start_time = time.time()
    
    try:
        yield
        duration = time.time() - start_time
        
        tracer.add_event(
            "context_end",
            component,
            f"Completed {operation}",
            {**context_data, "duration": duration}
        )
        
    except Exception as e:
        duration = time.time() - start_time
        
        tracer.add_event(
            "context_error",
            component,
            f"Failed {operation}",
            {**context_data, "duration": duration, "error": str(e)},
            include_stack=True
        )
        
        raise


# 全局实例
_global_debug_tracer: Optional[DebugTracer] = None
_global_performance_profiler: Optional[PerformanceProfiler] = None
_global_system_diagnostics: Optional[SystemDiagnostics] = None


def get_debug_tracer() -> DebugTracer:
    """获取全局调试跟踪器"""
    global _global_debug_tracer
    if _global_debug_tracer is None:
        _global_debug_tracer = DebugTracer()
    return _global_debug_tracer


def get_performance_profiler() -> PerformanceProfiler:
    """获取全局性能分析器"""
    global _global_performance_profiler
    if _global_performance_profiler is None:
        _global_performance_profiler = PerformanceProfiler()
    return _global_performance_profiler


def get_system_diagnostics() -> SystemDiagnostics:
    """获取全局系统诊断工具"""
    global _global_system_diagnostics
    if _global_system_diagnostics is None:
        _global_system_diagnostics = SystemDiagnostics()
    return _global_system_diagnostics