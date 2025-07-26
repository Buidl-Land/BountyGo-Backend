"""
Monitoring and Metrics System for Multi-Agent System
多代理系统监控和指标收集系统
"""
import asyncio
import logging
import time
import psutil
import threading
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import json
import os

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """指标类型"""
    COUNTER = "counter"         # 计数器
    GAUGE = "gauge"            # 仪表盘
    HISTOGRAM = "histogram"     # 直方图
    TIMER = "timer"            # 计时器


@dataclass
class Metric:
    """指标数据"""
    name: str
    type: MetricType
    value: Union[int, float]
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    description: Optional[str] = None


@dataclass
class PerformanceStats:
    """性能统计"""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, success: bool = True, error_message: Optional[str] = None):
        """完成性能统计"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error_message = error_message


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """增加计数器"""
        with self._lock:
            key = self._make_key(name, labels)
            self.counters[key] += value
            self._add_metric(Metric(
                name=name,
                type=MetricType.COUNTER,
                value=self.counters[key],
                timestamp=datetime.now(),
                labels=labels or {}
            ))
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表盘值"""
        with self._lock:
            key = self._make_key(name, labels)
            self.gauges[key] = value
            self._add_metric(Metric(
                name=name,
                type=MetricType.GAUGE,
                value=value,
                timestamp=datetime.now(),
                labels=labels or {}
            ))
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录直方图值"""
        with self._lock:
            key = self._make_key(name, labels)
            self.histograms[key].append(value)
            # 保持最近1000个值
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
            
            self._add_metric(Metric(
                name=name,
                type=MetricType.HISTOGRAM,
                value=value,
                timestamp=datetime.now(),
                labels=labels or {}
            ))
    
    def record_timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """记录计时器值"""
        with self._lock:
            key = self._make_key(name, labels)
            self.timers[key].append(duration)
            # 保持最近1000个值
            if len(self.timers[key]) > 1000:
                self.timers[key] = self.timers[key][-1000:]
            
            self._add_metric(Metric(
                name=name,
                type=MetricType.TIMER,
                value=duration,
                timestamp=datetime.now(),
                labels=labels or {}
            ))
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """生成指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}[{label_str}]"
    
    def _add_metric(self, metric: Metric):
        """添加指标"""
        self.metrics.append(metric)
    
    def get_metrics(self, name_filter: Optional[str] = None) -> List[Metric]:
        """获取指标"""
        with self._lock:
            if name_filter:
                return [m for m in self.metrics if name_filter in m.name]
            return list(self.metrics)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        with self._lock:
            summary = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {},
                "timers": {}
            }
            
            # 计算直方图统计
            for key, values in self.histograms.items():
                if values:
                    summary["histograms"][key] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "p50": self._percentile(values, 50),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99)
                    }
            
            # 计算计时器统计
            for key, values in self.timers.items():
                if values:
                    summary["timers"][key] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "p50": self._percentile(values, 50),
                        "p95": self._percentile(values, 95),
                        "p99": self._percentile(values, 99)
                    }
            
            return summary
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self, interval: float = 30.0):
        """开始系统监控"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("System monitoring started")
    
    async def stop_monitoring(self):
        """停止系统监控"""
        self.monitoring_active = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("System monitoring stopped")
    
    async def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring_active:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics_collector.set_gauge("system.cpu.usage", cpu_percent)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            self.metrics_collector.set_gauge("system.memory.usage", memory.percent)
            self.metrics_collector.set_gauge("system.memory.available", memory.available)
            self.metrics_collector.set_gauge("system.memory.used", memory.used)
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            self.metrics_collector.set_gauge("system.disk.usage", disk.percent)
            self.metrics_collector.set_gauge("system.disk.free", disk.free)
            
            # 网络统计
            network = psutil.net_io_counters()
            self.metrics_collector.set_gauge("system.network.bytes_sent", network.bytes_sent)
            self.metrics_collector.set_gauge("system.network.bytes_recv", network.bytes_recv)
            
            # 进程信息
            process = psutil.Process()
            self.metrics_collector.set_gauge("process.memory.rss", process.memory_info().rss)
            self.metrics_collector.set_gauge("process.memory.vms", process.memory_info().vms)
            self.metrics_collector.set_gauge("process.cpu.percent", process.cpu_percent())
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.active_operations: Dict[str, PerformanceStats] = {}
        self._lock = threading.Lock()
    
    def start_operation(self, operation_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """开始操作监控"""
        operation_id = f"{operation_name}_{int(time.time() * 1000000)}"
        
        with self._lock:
            self.active_operations[operation_id] = PerformanceStats(
                operation_name=operation_name,
                start_time=time.time(),
                context=context or {}
            )
        
        self.metrics_collector.increment_counter(
            "operations.started",
            labels={"operation": operation_name}
        )
        
        return operation_id
    
    def finish_operation(
        self,
        operation_id: str,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """完成操作监控"""
        with self._lock:
            if operation_id not in self.active_operations:
                logger.warning(f"Operation {operation_id} not found in active operations")
                return
            
            stats = self.active_operations.pop(operation_id)
            stats.finish(success, error_message)
        
        # 记录指标
        self.metrics_collector.record_timer(
            "operations.duration",
            stats.duration,
            labels={"operation": stats.operation_name}
        )
        
        if success:
            self.metrics_collector.increment_counter(
                "operations.success",
                labels={"operation": stats.operation_name}
            )
        else:
            self.metrics_collector.increment_counter(
                "operations.error",
                labels={"operation": stats.operation_name}
            )
        
        # 记录性能日志
        logger.info(
            f"Operation completed: {stats.operation_name}",
            extra={
                "operation_id": operation_id,
                "duration": stats.duration,
                "success": success,
                "error_message": error_message,
                "context": stats.context
            }
        )
    
    def get_active_operations(self) -> Dict[str, PerformanceStats]:
        """获取活跃操作"""
        with self._lock:
            return self.active_operations.copy()


def performance_monitor(operation_name: str, context_extractor: Optional[Callable] = None):
    """性能监控装饰器"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                monitor = get_performance_monitor()
                context = {}
                if context_extractor:
                    try:
                        context = context_extractor(*args, **kwargs)
                    except Exception:
                        pass
                
                operation_id = monitor.start_operation(operation_name, context)
                
                try:
                    result = await func(*args, **kwargs)
                    monitor.finish_operation(operation_id, success=True)
                    return result
                except Exception as e:
                    monitor.finish_operation(operation_id, success=False, error_message=str(e))
                    raise
            
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                monitor = get_performance_monitor()
                context = {}
                if context_extractor:
                    try:
                        context = context_extractor(*args, **kwargs)
                    except Exception:
                        pass
                
                operation_id = monitor.start_operation(operation_name, context)
                
                try:
                    result = func(*args, **kwargs)
                    monitor.finish_operation(operation_id, success=True)
                    return result
                except Exception as e:
                    monitor.finish_operation(operation_id, success=False, error_message=str(e))
                    raise
            
            return sync_wrapper
    
    return decorator


class MonitoringSystem:
    """监控系统"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.system_monitor = SystemMonitor(self.metrics_collector)
        self.performance_monitor = PerformanceMonitor(self.metrics_collector)
        self.started = False
    
    async def start(self, system_monitor_interval: float = 30.0):
        """启动监控系统"""
        if self.started:
            return
        
        await self.system_monitor.start_monitoring(system_monitor_interval)
        self.started = True
        logger.info("Monitoring system started")
    
    async def stop(self):
        """停止监控系统"""
        if not self.started:
            return
        
        await self.system_monitor.stop_monitoring()
        self.started = False
        logger.info("Monitoring system stopped")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return self.metrics_collector.get_summary()
    
    def export_metrics(self, format: str = "json") -> str:
        """导出指标"""
        summary = self.get_metrics_summary()
        
        if format == "json":
            return json.dumps(summary, indent=2, default=str)
        elif format == "prometheus":
            return self._export_prometheus_format(summary)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_prometheus_format(self, summary: Dict[str, Any]) -> str:
        """导出Prometheus格式"""
        lines = []
        
        # 计数器
        for name, value in summary.get("counters", {}).items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # 仪表盘
        for name, value in summary.get("gauges", {}).items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        # 直方图
        for name, stats in summary.get("histograms", {}).items():
            lines.append(f"# TYPE {name} histogram")
            lines.append(f"{name}_count {stats['count']}")
            lines.append(f"{name}_sum {stats['avg'] * stats['count']}")
            for percentile in [50, 95, 99]:
                lines.append(f"{name}_bucket{{le=\"{percentile}\"}} {stats[f'p{percentile}']}")
        
        return "\n".join(lines)


# 全局监控系统实例
_global_monitoring_system: Optional[MonitoringSystem] = None


def get_monitoring_system() -> MonitoringSystem:
    """获取全局监控系统"""
    global _global_monitoring_system
    if _global_monitoring_system is None:
        _global_monitoring_system = MonitoringSystem()
    return _global_monitoring_system


def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器"""
    return get_monitoring_system().metrics_collector


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器"""
    return get_monitoring_system().performance_monitor