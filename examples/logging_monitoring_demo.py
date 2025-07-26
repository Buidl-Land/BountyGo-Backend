#!/usr/bin/env python3
"""
Logging and Monitoring System Demo
日志记录和监控系统演示
"""
import asyncio
import time
from app.agent.structured_logging import (
    get_logger, configure_logging, LogLevel, LogFormat
)
from app.agent.monitoring import (
    get_monitoring_system, performance_monitor
)
from app.agent.debugging_tools import (
    debug_trace, debug_context, get_debug_tracer
)


# 配置日志系统
configure_logging(
    level=LogLevel.INFO,
    format_type=LogFormat.JSON,
    log_dir="logs"
)

logger = get_logger("demo")


@performance_monitor("demo_operation")
@debug_trace("demo_component")
async def demo_async_operation(duration: float = 1.0):
    """演示异步操作的监控和调试"""
    logger.info(f"开始异步操作，预计耗时 {duration} 秒")
    
    with debug_context("demo_component", "async_work", duration=duration):
        await asyncio.sleep(duration)
        
        # 模拟一些工作
        result = f"异步操作完成，耗时 {duration} 秒"
        logger.info(result)
        
        return result


@performance_monitor("sync_demo_operation")
@debug_trace("demo_component")
def demo_sync_operation(iterations: int = 5):
    """演示同步操作的监控和调试"""
    logger.info(f"开始同步操作，迭代 {iterations} 次")
    
    results = []
    for i in range(iterations):
        with debug_context("demo_component", "sync_iteration", iteration=i):
            time.sleep(0.1)  # 模拟工作
            result = f"迭代 {i+1} 完成"
            results.append(result)
            logger.debug(result)
    
    logger.info(f"同步操作完成，共 {len(results)} 次迭代")
    return results


async def demo_error_handling():
    """演示错误处理和日志记录"""
    logger.info("演示错误处理")
    
    try:
        # 模拟一个错误
        raise ValueError("这是一个演示错误")
    except Exception as e:
        logger.log_error(e, "演示错误处理")


async def main():
    """主演示函数"""
    print("=== 日志记录和监控系统演示 ===\n")
    
    # 启动监控系统
    monitoring = get_monitoring_system()
    await monitoring.start(system_monitor_interval=5.0)
    
    # 启用调试跟踪
    tracer = get_debug_tracer()
    tracer.enable()
    
    try:
        # 使用日志上下文
        with logger.context(user_id="demo_user", operation="demo_session"):
            logger.info("演示开始")
            
            # 演示异步操作
            print("1. 演示异步操作监控...")
            await demo_async_operation(0.5)
            await demo_async_operation(1.0)
            
            # 演示同步操作
            print("2. 演示同步操作监控...")
            demo_sync_operation(3)
            
            # 演示错误处理
            print("3. 演示错误处理...")
            await demo_error_handling()
            
            # 等待一些系统指标收集
            print("4. 等待系统指标收集...")
            await asyncio.sleep(2)
            
            logger.info("演示完成")
        
        # 显示收集的指标
        print("\n=== 指标摘要 ===")
        metrics_summary = monitoring.get_metrics_summary()
        
        print("计数器指标:")
        for name, value in metrics_summary.get("counters", {}).items():
            print(f"  {name}: {value}")
        
        print("\n计时器指标:")
        for name, stats in metrics_summary.get("timers", {}).items():
            print(f"  {name}:")
            print(f"    计数: {stats['count']}")
            print(f"    平均: {stats['avg']:.3f}s")
            print(f"    最小: {stats['min']:.3f}s")
            print(f"    最大: {stats['max']:.3f}s")
        
        print("\n系统指标:")
        for name, value in metrics_summary.get("gauges", {}).items():
            if name.startswith("system."):
                print(f"  {name}: {value}")
        
        # 显示调试事件
        print("\n=== 调试事件 ===")
        events = tracer.get_events()
        for event in events[-10:]:  # 显示最后10个事件
            print(f"  [{event.timestamp.strftime('%H:%M:%S')}] {event.event_type} - {event.component}: {event.message}")
        
        # 显示函数调用
        print("\n=== 函数调用统计 ===")
        calls = tracer.get_function_calls()
        for call in calls[-5:]:  # 显示最后5个调用
            status = "成功" if call.exception is None else "失败"
            print(f"  {call.function_name} ({call.module}): {call.duration:.3f}s - {status}")
        
        # 导出指标
        print("\n=== 导出指标 ===")
        json_export = monitoring.export_metrics("json")
        print("JSON格式指标已生成")
        
        prometheus_export = monitoring.export_metrics("prometheus")
        print("Prometheus格式指标已生成")
        
        # 保存到文件
        with open("logs/metrics_export.json", "w") as f:
            f.write(json_export)
        
        with open("logs/metrics_export.prom", "w") as f:
            f.write(prometheus_export)
        
        print("指标已保存到 logs/ 目录")
        
    finally:
        # 停止监控系统
        await monitoring.stop()
        print("\n演示结束")


if __name__ == "__main__":
    asyncio.run(main())