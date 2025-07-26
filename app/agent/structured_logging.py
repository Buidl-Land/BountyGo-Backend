"""
Structured Logging System for Multi-Agent System
多代理系统结构化日志记录系统
"""
import logging
import logging.handlers
import json
import sys
import os
import traceback
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
import time
import asyncio
from contextlib import contextmanager

from .exceptions import MultiAgentError, ErrorCategory, ErrorSeverity


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """日志格式"""
    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


@dataclass
class LogContext:
    """日志上下文"""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: Optional[str] = None
    agent_type: Optional[str] = None
    component: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def __init__(self, format_type: LogFormat = LogFormat.JSON, include_context: bool = True):
        super().__init__()
        self.format_type = format_type
        self.include_context = include_context
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 基础日志数据
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加上下文信息
        if self.include_context and hasattr(record, 'context'):
            log_data["context"] = record.context
        
        # 添加额外字段
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info', 'context']:
                log_data[key] = value
        
        # 处理异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # 处理MultiAgentError
        if hasattr(record, 'agent_error') and isinstance(record.agent_error, MultiAgentError):
            log_data["agent_error"] = record.agent_error.to_dict()
        
        # 根据格式类型返回
        if self.format_type == LogFormat.JSON:
            return json.dumps(log_data, ensure_ascii=False, default=str)
        elif self.format_type == LogFormat.STRUCTURED:
            return self._format_structured(log_data)
        else:  # TEXT
            return self._format_text(log_data)
    
    def _format_structured(self, log_data: Dict[str, Any]) -> str:
        """格式化为结构化文本"""
        parts = [
            f"[{log_data['timestamp']}]",
            f"[{log_data['level']}]",
            f"[{log_data['logger']}]",
            log_data['message']
        ]
        
        if 'context' in log_data:
            context_str = " ".join(f"{k}={v}" for k, v in log_data['context'].items())
            parts.append(f"context=({context_str})")
        
        if 'exception' in log_data:
            parts.append(f"exception={log_data['exception']['type']}: {log_data['exception']['message']}")
        
        return " ".join(parts)
    
    def _format_text(self, log_data: Dict[str, Any]) -> str:
        """格式化为普通文本"""
        return f"{log_data['timestamp']} - {log_data['level']} - {log_data['logger']} - {log_data['message']}"


class ContextFilter(logging.Filter):
    """上下文过滤器"""
    
    def __init__(self):
        super().__init__()
        self.local = threading.local()
    
    def filter(self, record: logging.LogRecord) -> bool:
        """添加上下文信息到日志记录"""
        context = getattr(self.local, 'context', None)
        if context:
            record.context = context.to_dict()
        return True
    
    def set_context(self, context: LogContext):
        """设置当前线程的日志上下文"""
        self.local.context = context
    
    def clear_context(self):
        """清除当前线程的日志上下文"""
        if hasattr(self.local, 'context'):
            delattr(self.local, 'context')
    
    def get_context(self) -> Optional[LogContext]:
        """获取当前线程的日志上下文"""
        return getattr(self.local, 'context', None)


class LoggingConfig:
    """日志配置"""
    
    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
        format_type: LogFormat = LogFormat.JSON,
        log_dir: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console_output: bool = True,
        file_output: bool = True,
        include_context: bool = True
    ):
        self.level = level
        self.format_type = format_type
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.console_output = console_output
        self.file_output = file_output
        self.include_context = include_context


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str, config: Optional[LoggingConfig] = None):
        self.name = name
        self.config = config or LoggingConfig()
        self.logger = logging.getLogger(name)
        self.context_filter = ContextFilter()
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志记录器"""
        # 清除现有处理器
        self.logger.handlers.clear()
        
        # 设置日志级别
        self.logger.setLevel(getattr(logging, self.config.level.value))
        
        # 创建格式化器
        formatter = StructuredFormatter(
            format_type=self.config.format_type,
            include_context=self.config.include_context
        )
        
        # 添加上下文过滤器
        self.logger.addFilter(self.context_filter)
        
        # 控制台输出
        if self.config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 文件输出
        if self.config.file_output:
            self._setup_file_handlers(formatter)
    
    def _setup_file_handlers(self, formatter: StructuredFormatter):
        """设置文件处理器"""
        # 确保日志目录存在
        self.config.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 主日志文件
        main_log_file = self.config.log_dir / f"{self.name}.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        main_handler.setFormatter(formatter)
        self.logger.addHandler(main_handler)
        
        # 错误日志文件
        error_log_file = self.config.log_dir / f"{self.name}_error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
    
    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """记录信息日志"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """记录错误日志"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """记录严重错误日志"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """内部日志记录方法"""
        extra = {}
        
        # 处理额外参数
        for key, value in kwargs.items():
            if key not in ['exc_info', 'stack_info', 'stacklevel']:
                extra[key] = value
        
        # 记录日志
        self.logger.log(
            level,
            message,
            extra=extra,
            exc_info=kwargs.get('exc_info'),
            stack_info=kwargs.get('stack_info'),
            stacklevel=kwargs.get('stacklevel', 1) + 1
        )
    
    def log_error(self, error: Exception, message: Optional[str] = None, **kwargs):
        """记录错误"""
        error_message = message or f"Error occurred: {str(error)}"
        
        extra = kwargs.copy()
        if isinstance(error, MultiAgentError):
            extra['agent_error'] = error
        
        self.error(
            error_message,
            exc_info=True,
            **extra
        )
    
    def log_performance(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        **kwargs
    ):
        """记录性能日志"""
        self.info(
            f"Performance: {operation}",
            operation=operation,
            duration=duration,
            success=success,
            **kwargs
        )
    
    @contextmanager
    def context(self, **context_kwargs):
        """日志上下文管理器"""
        # 获取当前上下文
        current_context = self.context_filter.get_context()
        
        # 创建新上下文
        if current_context:
            new_context_data = current_context.to_dict()
            new_context_data.update(context_kwargs)
        else:
            new_context_data = context_kwargs
        
        new_context = LogContext(**new_context_data)
        
        # 设置新上下文
        self.context_filter.set_context(new_context)
        
        try:
            yield
        finally:
            # 恢复原上下文
            if current_context:
                self.context_filter.set_context(current_context)
            else:
                self.context_filter.clear_context()


class LoggingManager:
    """日志管理器"""
    
    def __init__(self, config: Optional[LoggingConfig] = None):
        self.config = config or LoggingConfig()
        self.loggers: Dict[str, StructuredLogger] = {}
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """设置根日志记录器"""
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.level.value))
        
        # 防止重复日志
        root_logger.propagate = False
    
    def get_logger(self, name: str) -> StructuredLogger:
        """获取日志记录器"""
        if name not in self.loggers:
            self.loggers[name] = StructuredLogger(name, self.config)
        return self.loggers[name]
    
    def configure_logger(self, name: str, config: LoggingConfig) -> StructuredLogger:
        """配置特定的日志记录器"""
        logger = StructuredLogger(name, config)
        self.loggers[name] = logger
        return logger
    
    def set_global_context(self, **context_kwargs):
        """设置全局日志上下文"""
        context = LogContext(**context_kwargs)
        for logger in self.loggers.values():
            logger.context_filter.set_context(context)
    
    def clear_global_context(self):
        """清除全局日志上下文"""
        for logger in self.loggers.values():
            logger.context_filter.clear_context()


# 全局日志管理器
_global_logging_manager: Optional[LoggingManager] = None


def get_logging_manager() -> LoggingManager:
    """获取全局日志管理器"""
    global _global_logging_manager
    if _global_logging_manager is None:
        _global_logging_manager = LoggingManager()
    return _global_logging_manager


def get_logger(name: str) -> StructuredLogger:
    """获取日志记录器（便捷函数）"""
    return get_logging_manager().get_logger(name)


def configure_logging(
    level: LogLevel = LogLevel.INFO,
    format_type: LogFormat = LogFormat.JSON,
    log_dir: Optional[str] = None,
    **kwargs
):
    """配置全局日志设置"""
    global _global_logging_manager
    config = LoggingConfig(
        level=level,
        format_type=format_type,
        log_dir=log_dir,
        **kwargs
    )
    _global_logging_manager = LoggingManager(config)


# 便捷的日志装饰器
def log_function_call(logger_name: str = None, include_args: bool = False, include_result: bool = False):
    """函数调用日志装饰器"""
    def decorator(func):
        logger = get_logger(logger_name or func.__module__)
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                with logger.context(function=func.__name__):
                    start_time = time.time()
                    
                    log_data = {"function": func.__name__}
                    if include_args:
                        log_data["args"] = str(args)
                        log_data["kwargs"] = str(kwargs)
                    
                    logger.debug(f"Function call started: {func.__name__}", **log_data)
                    
                    try:
                        result = await func(*args, **kwargs)
                        duration = time.time() - start_time
                        
                        result_log_data = {
                            "function": func.__name__,
                            "duration": duration,
                            "success": True
                        }
                        if include_result:
                            result_log_data["result"] = str(result)
                        
                        logger.debug(f"Function call completed: {func.__name__}", **result_log_data)
                        return result
                    
                    except Exception as e:
                        duration = time.time() - start_time
                        logger.error(
                            f"Function call failed: {func.__name__}",
                            function=func.__name__,
                            duration=duration,
                            success=False,
                            exc_info=True
                        )
                        raise
            
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with logger.context(function=func.__name__):
                    start_time = time.time()
                    
                    log_data = {"function": func.__name__}
                    if include_args:
                        log_data["args"] = str(args)
                        log_data["kwargs"] = str(kwargs)
                    
                    logger.debug(f"Function call started: {func.__name__}", **log_data)
                    
                    try:
                        result = func(*args, **kwargs)
                        duration = time.time() - start_time
                        
                        result_log_data = {
                            "function": func.__name__,
                            "duration": duration,
                            "success": True
                        }
                        if include_result:
                            result_log_data["result"] = str(result)
                        
                        logger.debug(f"Function call completed: {func.__name__}", **result_log_data)
                        return result
                    
                    except Exception as e:
                        duration = time.time() - start_time
                        logger.error(
                            f"Function call failed: {func.__name__}",
                            function=func.__name__,
                            duration=duration,
                            success=False,
                            exc_info=True
                        )
                        raise
            
            return sync_wrapper
    
    return decorator