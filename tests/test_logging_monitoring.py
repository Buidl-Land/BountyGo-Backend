"""
Tests for logging and monitoring system
日志记录和监控系统测试
"""
import asyncio
import json
import tempfile
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import pytest

from app.agent.structured_logging import (
    StructuredLogger, LoggingConfig, LogLevel, LogFormat,
    LogContext, get_logger, configure_logging
)
from app.agent.monitoring import (
    MetricsCollector, SystemMonitor, PerformanceMonitor,
    MonitoringSystem, performance_monitor, get_monitoring_system
)
from app.agent.debugging_tools import (
    DebugTracer, PerformanceProfiler, SystemDiagnostics,
    debug_trace, debug_context, get_debug_tracer
)
from app.agent.exceptions import MultiAgentError, ErrorCategory, ErrorSeverity


class TestStructuredLogging:
    """结构化日志测试"""
    
    def test_logger_creation(self):
        """测试日志记录器创建"""
        logger = get_logger("test_logger")
        assert logger.name == "test_logger"
        assert isinstance(logger, StructuredLogger)
    
    def test_log_levels(self):
        """测试日志级别"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LoggingConfig(
                level=LogLevel.DEBUG,
                log_dir=temp_dir,
                console_output=False
            )
            logger = StructuredLogger("test_levels", config)
            
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")
            
            # 检查日志文件是否创建
            log_file = Path(temp_dir) / "test_levels.log"
            assert log_file.exists()
    
    def test_json_format(self):
        """测试JSON格式"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LoggingConfig(
                format_type=LogFormat.JSON,
                log_dir=temp_dir,
                console_output=False
            )
            logger = StructuredLogger("test_json", config)
            
            logger.info("Test message", extra_field="extra_value")
            
            # 读取日志文件并验证JSON格式
            log_file = Path(temp_dir) / "test_json.log"
            with open(log_file, 'r') as f:
                log_line = f.readline().strip()
                log_data = json.loads(log_line)
                
                assert log_data["message"] == "Test message"
                assert log_data["level"] == "INFO"
                assert log_data["extra_field"] == "extra_value"
    
    def test_context_logging(self):
        """测试上下文日志"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LoggingConfig(
                format_type=LogFormat.JSON,
                log_dir=temp_dir,
                console_output=False
            )
            logger = StructuredLogger("test_context", config)
            
            with logger.context(request_id="req_123", user_id="user_456"):
                logger.info("Message with context")
            
            # 验证上下文信息
            log_file = Path(temp_dir) / "test_context.log"
            with open(log_file, 'r') as f:
                log_line = f.readline().strip()
                log_data = json.loads(log_line)
                
                assert log_data["context"]["request_id"] == "req_123"
                assert log_data["context"]["user_id"] == "user_456"
    
    def test_error_logging(self):
        """测试错误日志"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = LoggingConfig(
                format_type=LogFormat.JSON,
                log_dir=temp_dir,
                console_output=False
            )
            logger = StructuredLogger("test_error", config)
            
            try:
                raise ValueError("Test error")
            except Exception as e:
                logger.log_error(e, "Error occurred during test")
            
            # 验证错误日志
            error_log_file = Path(temp_dir) / "test_error_error.log"
            assert error_log_file.exists()
            
            with open(error_log_file, 'r') as f:
                log_line = f.readline().strip()
                log_data = json.loads(log_line)
                
                assert "Error occurred during test" in log_data["message"]
                assert log_data["level"] == "ERROR"
                assert "exception" in log_data


class TestMetricsCollector:
    """指标收集器测试"""
    
    def test_counter_metrics(self):
        """测试计数器指标"""
        collector = MetricsCollector()
        
        collector.increment_counter("test_counter", 1)
        collector.increment_counter("test_counter", 2)
        
        summary = collector.get_summary()
        assert summary["counters"]["test_counter"] == 3
    
    def test_gauge_metrics(self):
        """测试仪表盘指标"""
        collector = MetricsCollector()
        
        collector.set_gauge("test_gauge", 10.5)
        collector.set_gauge("test_gauge", 20.3)
        
        summary = collector.get_summary()
        assert summary["gauges"]["test_gauge"] == 20.3
    
    def test_histogram_metrics(self):
        """测试直方图指标"""
        collector = MetricsCollector()
        
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            collector.record_histogram("test_histogram", value)
        
        summary = collector.get_summary()
        hist_stats = summary["histograms"]["test_histogram"]
        
        assert hist_stats["count"] == 5
        assert hist_stats["min"] == 1.0
        assert hist_stats["max"] == 5.0
        assert hist_stats["avg"] == 3.0
    
    def test_timer_metrics(self):
        """测试计时器指标"""
        collector = MetricsCollector()
        
        durations = [0.1, 0.2, 0.3, 0.4, 0.5]
        for duration in durations:
            collector.record_timer("test_timer", duration)
        
        summary = collector.get_summary()
        timer_stats = summary["timers"]["test_timer"]
        
        assert timer_stats["count"] == 5
        assert timer_stats["min"] == 0.1
        assert timer_stats["max"] == 0.5
        assert timer_stats["avg"] == 0.3
    
    def test_labels(self):
        """测试标签功能"""
        collector = MetricsCollector()
        
        collector.increment_counter("requests", 1, {"method": "GET"})
        collector.increment_counter("requests", 2, {"method": "POST"})
        
        summary = collector.get_summary()
        assert summary["counters"]["requests[method=GET]"] == 1
        assert summary["counters"]["requests[method=POST]"] == 2


class TestPerformanceMonitor:
    """性能监控器测试"""
    
    def test_operation_monitoring(self):
        """测试操作监控"""
        collector = MetricsCollector()
        monitor = PerformanceMonitor(collector)
        
        # 开始操作
        op_id = monitor.start_operation("test_operation", {"param": "value"})
        time.sleep(0.1)  # 模拟操作时间
        monitor.finish_operation(op_id, success=True)
        
        # 检查指标
        summary = collector.get_summary()
        assert "operations.started[operation=test_operation]" in summary["counters"]
        assert "operations.success[operation=test_operation]" in summary["counters"]
        assert "operations.duration[operation=test_operation]" in summary["timers"]
    
    def test_failed_operation(self):
        """测试失败操作监控"""
        collector = MetricsCollector()
        monitor = PerformanceMonitor(collector)
        
        op_id = monitor.start_operation("failed_operation")
        monitor.finish_operation(op_id, success=False, error_message="Test error")
        
        summary = collector.get_summary()
        assert "operations.error[operation=failed_operation]" in summary["counters"]
    
    def test_active_operations(self):
        """测试活跃操作跟踪"""
        collector = MetricsCollector()
        monitor = PerformanceMonitor(collector)
        
        op_id = monitor.start_operation("long_operation")
        active_ops = monitor.get_active_operations()
        
        assert len(active_ops) == 1
        assert active_ops[op_id].operation_name == "long_operation"
        
        monitor.finish_operation(op_id)
        active_ops = monitor.get_active_operations()
        assert len(active_ops) == 0


class TestDebugTracer:
    """调试跟踪器测试"""
    
    def test_event_tracking(self):
        """测试事件跟踪"""
        tracer = DebugTracer()
        tracer.enable()
        
        tracer.add_event("test_event", "test_component", "Test message", {"key": "value"})
        
        events = tracer.get_events()
        assert len(events) == 1
        assert events[0].event_type == "test_event"
        assert events[0].component == "test_component"
        assert events[0].message == "Test message"
        assert events[0].data["key"] == "value"
    
    def test_function_call_tracking(self):
        """测试函数调用跟踪"""
        tracer = DebugTracer()
        tracer.enable()
        
        call_id = tracer.start_function_call("test_func", "test_module", (1, 2), {"key": "value"})
        tracer.finish_function_call(call_id, result="success")
        
        calls = tracer.get_function_calls()
        assert len(calls) == 1
        assert calls[0].function_name == "test_func"
        assert calls[0].result == "success"
        assert calls[0].exception is None
    
    def test_event_filtering(self):
        """测试事件过滤"""
        tracer = DebugTracer()
        tracer.enable()
        
        tracer.add_event("type1", "comp1", "Message 1")
        tracer.add_event("type2", "comp1", "Message 2")
        tracer.add_event("type1", "comp2", "Message 3")
        
        # 按事件类型过滤
        type1_events = tracer.get_events(event_type="type1")
        assert len(type1_events) == 2
        
        # 按组件过滤
        comp1_events = tracer.get_events(component="comp1")
        assert len(comp1_events) == 2


class TestPerformanceProfiler:
    """性能分析器测试"""
    
    def test_performance_recording(self):
        """测试性能记录"""
        profiler = PerformanceProfiler()
        profiler.enable()
        
        profiler.record("test_operation", 0.1)
        profiler.record("test_operation", 0.2)
        profiler.record("test_operation", 0.3)
        
        stats = profiler.get_stats("test_operation")
        assert stats["count"] == 3
        assert stats["min"] == 0.1
        assert stats["max"] == 0.3
        assert abs(stats["avg"] - 0.2) < 0.001
    
    def test_multiple_operations(self):
        """测试多个操作的性能记录"""
        profiler = PerformanceProfiler()
        profiler.enable()
        
        profiler.record("op1", 0.1)
        profiler.record("op2", 0.2)
        
        all_stats = profiler.get_stats()
        assert "op1" in all_stats
        assert "op2" in all_stats
        assert all_stats["op1"]["count"] == 1
        assert all_stats["op2"]["count"] == 1


class TestDecorators:
    """装饰器测试"""
    
    @pytest.mark.asyncio
    async def test_performance_monitor_decorator(self):
        """测试性能监控装饰器"""
        @performance_monitor("test_decorated_function")
        async def test_function():
            await asyncio.sleep(0.1)
            return "success"
        
        result = await test_function()
        assert result == "success"
        
        # 检查指标是否记录
        collector = get_monitoring_system().metrics_collector
        summary = collector.get_summary()
        
        # 应该有计时器记录
        timer_keys = [k for k in summary["timers"].keys() if "test_decorated_function" in k]
        assert len(timer_keys) > 0
    
    def test_debug_trace_decorator(self):
        """测试调试跟踪装饰器"""
        tracer = get_debug_tracer()
        tracer.enable()
        
        @debug_trace(component="test_component")
        def test_function(x, y):
            return x + y
        
        result = test_function(1, 2)
        assert result == 3
        
        # 检查跟踪记录
        events = tracer.get_events(component="test_component")
        assert len(events) >= 2  # 开始和结束事件
        
        calls = tracer.get_function_calls(function_name="test_function")
        assert len(calls) == 1
        assert calls[0].result == 3
    
    def test_debug_context_manager(self):
        """测试调试上下文管理器"""
        tracer = get_debug_tracer()
        tracer.enable()
        
        with debug_context("test_component", "test_operation", param="value"):
            time.sleep(0.01)  # 模拟操作
        
        events = tracer.get_events(component="test_component")
        start_events = [e for e in events if e.event_type == "context_start"]
        end_events = [e for e in events if e.event_type == "context_end"]
        
        assert len(start_events) == 1
        assert len(end_events) == 1
        assert start_events[0].data["param"] == "value"


class TestSystemDiagnostics:
    """系统诊断测试"""
    
    def test_health_check(self):
        """测试健康检查"""
        diagnostics = SystemDiagnostics()
        health_status = diagnostics.run_health_check()
        
        assert "overall_status" in health_status
        assert "checks" in health_status
        assert "timestamp" in health_status
        
        # 检查基本的健康检查项
        checks = health_status["checks"]
        assert "memory" in checks
        assert "disk" in checks
        assert "threads" in checks
    
    def test_debug_report_generation(self):
        """测试调试报告生成"""
        diagnostics = SystemDiagnostics()
        
        # 添加一些测试数据
        diagnostics.tracer.enable()
        diagnostics.tracer.add_event("test", "component", "Test event")
        
        report = diagnostics.generate_debug_report()
        
        assert "timestamp" in report
        assert "system_info" in report
        assert "health_check" in report
        assert "recent_events" in report
        assert "performance_stats" in report
        assert "metrics_summary" in report
    
    def test_debug_data_export(self):
        """测试调试数据导出"""
        diagnostics = SystemDiagnostics()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            diagnostics.export_debug_data(temp_file, format="json")
            
            # 验证文件是否创建并包含有效JSON
            with open(temp_file, 'r') as f:
                data = json.load(f)
                assert "timestamp" in data
                assert "system_info" in data
        finally:
            Path(temp_file).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_monitoring_system_integration():
    """测试监控系统集成"""
    monitoring = get_monitoring_system()
    
    # 启动监控
    await monitoring.start(system_monitor_interval=0.1)
    
    # 等待一些系统指标收集
    await asyncio.sleep(0.2)
    
    # 获取指标摘要
    summary = monitoring.get_metrics_summary()
    
    # 应该有系统指标
    gauges = summary.get("gauges", {})
    system_metrics = [k for k in gauges.keys() if k.startswith("system.")]
    assert len(system_metrics) > 0
    
    # 停止监控
    await monitoring.stop()


def test_metrics_export():
    """测试指标导出"""
    monitoring = get_monitoring_system()
    
    # 添加一些测试指标
    monitoring.metrics_collector.increment_counter("test_counter", 5)
    monitoring.metrics_collector.set_gauge("test_gauge", 10.5)
    
    # 导出JSON格式
    json_export = monitoring.export_metrics("json")
    data = json.loads(json_export)
    
    assert "counters" in data
    assert "gauges" in data
    assert data["counters"]["test_counter"] == 5
    assert data["gauges"]["test_gauge"] == 10.5
    
    # 导出Prometheus格式
    prometheus_export = monitoring.export_metrics("prometheus")
    assert "test_counter 5" in prometheus_export
    assert "test_gauge 10.5" in prometheus_export


if __name__ == "__main__":
    pytest.main([__file__])