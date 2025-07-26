"""
Unified Error Handler for Multi-Agent System
统一错误处理器 - 提供重试、降级和恢复机制
"""
import asyncio
import logging
import time
import traceback
from typing import Dict, List, Optional, Any, Callable, Union, Type
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .exceptions import (
    MultiAgentError, ErrorCategory, ErrorSeverity,
    NetworkError, ModelAPIError, RateLimitError, TimeoutError,
    ConfigurationError, ValidationError, ProcessingError,
    StorageError, AuthenticationError, ResourceError
)

logger = logging.getLogger(__name__)


class RetryStrategy(str, Enum):
    """重试策略"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_INTERVAL = "fixed_interval"
    LINEAR_BACKOFF = "linear_backoff"
    NO_RETRY = "no_retry"


class DegradationLevel(str, Enum):
    """降级级别"""
    NONE = "none"           # 不降级
    PARTIAL = "partial"     # 部分功能降级
    FALLBACK = "fallback"   # 使用备用方案
    MINIMAL = "minimal"     # 最小功能模式


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    
    # 针对不同错误类型的特定配置
    category_configs: Dict[ErrorCategory, 'RetryConfig'] = field(default_factory=dict)
    
    def get_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        if self.strategy == RetryStrategy.NO_RETRY:
            return 0
        elif self.strategy == RetryStrategy.FIXED_INTERVAL:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.base_delay * attempt
        else:  # EXPONENTIAL_BACKOFF
            delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        
        # 应用最大延迟限制
        delay = min(delay, self.max_delay)
        
        # 添加抖动
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay


@dataclass
class DegradationConfig:
    """降级配置"""
    enabled: bool = True
    level: DegradationLevel = DegradationLevel.PARTIAL
    fallback_functions: Dict[str, Callable] = field(default_factory=dict)
    timeout_threshold: float = 30.0
    error_rate_threshold: float = 0.5
    recovery_check_interval: float = 60.0


@dataclass
class ErrorStats:
    """错误统计"""
    total_errors: int = 0
    errors_by_category: Dict[ErrorCategory, int] = field(default_factory=dict)
    errors_by_severity: Dict[ErrorSeverity, int] = field(default_factory=dict)
    recent_errors: List[MultiAgentError] = field(default_factory=list)
    last_error_time: Optional[datetime] = None
    error_rate: float = 0.0
    
    def add_error(self, error: MultiAgentError):
        """添加错误记录"""
        self.total_errors += 1
        self.errors_by_category[error.category] = self.errors_by_category.get(error.category, 0) + 1
        self.errors_by_severity[error.severity] = self.errors_by_severity.get(error.severity, 0) + 1
        self.recent_errors.append(error)
        self.last_error_time = datetime.now()
        
        # 保持最近错误列表大小
        if len(self.recent_errors) > 100:
            self.recent_errors = self.recent_errors[-100:]
        
        # 计算错误率（最近5分钟）
        now = datetime.now()
        recent_errors = [e for e in self.recent_errors if (now - e.timestamp).seconds < 300]
        self.error_rate = len(recent_errors) / 300  # 每秒错误数


class ErrorHandler:
    """统一错误处理器"""
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        degradation_config: Optional[DegradationConfig] = None
    ):
        self.retry_config = retry_config or RetryConfig()
        self.degradation_config = degradation_config or DegradationConfig()
        self.stats = ErrorStats()
        self.degradation_active = False
        self.degradation_start_time: Optional[datetime] = None
        self._setup_default_configs()
    
    def _setup_default_configs(self):
        """设置默认配置"""
        # 为不同错误类型设置特定的重试配置
        self.retry_config.category_configs = {
            ErrorCategory.NETWORK: RetryConfig(
                max_attempts=5,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=2.0,
                max_delay=30.0
            ),
            ErrorCategory.MODEL_API: RetryConfig(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=1.0,
                max_delay=15.0
            ),
            ErrorCategory.RATE_LIMIT: RetryConfig(
                max_attempts=2,
                strategy=RetryStrategy.FIXED_INTERVAL,
                base_delay=60.0
            ),
            ErrorCategory.TIMEOUT: RetryConfig(
                max_attempts=2,
                strategy=RetryStrategy.LINEAR_BACKOFF,
                base_delay=5.0
            ),
            ErrorCategory.CONFIGURATION: RetryConfig(
                max_attempts=1,
                strategy=RetryStrategy.NO_RETRY
            ),
            ErrorCategory.AUTHENTICATION: RetryConfig(
                max_attempts=1,
                strategy=RetryStrategy.NO_RETRY
            )
        }
    
    def should_retry(self, error: MultiAgentError, attempt: int) -> bool:
        """判断是否应该重试"""
        if not error.recoverable:
            return False
        
        config = self.retry_config.category_configs.get(
            error.category, self.retry_config
        )
        
        return attempt < config.max_attempts and config.strategy != RetryStrategy.NO_RETRY
    
    def should_degrade(self) -> bool:
        """判断是否应该降级"""
        if not self.degradation_config.enabled:
            return False
        
        # 基于错误率判断
        if self.stats.error_rate > self.degradation_config.error_rate_threshold:
            return True
        
        # 基于最近错误判断
        if self.stats.recent_errors:
            recent_critical_errors = [
                e for e in self.stats.recent_errors[-10:]
                if e.severity == ErrorSeverity.CRITICAL
            ]
            if len(recent_critical_errors) >= 3:
                return True
        
        return False
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        operation_name: str = "unknown"
    ) -> MultiAgentError:
        """处理错误"""
        # 转换为标准错误格式
        if isinstance(error, MultiAgentError):
            agent_error = error
        else:
            agent_error = self._convert_to_agent_error(error, context)
        
        # 记录错误
        self.stats.add_error(agent_error)
        
        # 记录日志
        logger.error(
            f"Error in {operation_name}: {agent_error.message}",
            extra={
                "category": agent_error.category.value,
                "severity": agent_error.severity.value,
                "context": agent_error.context,
                "traceback": traceback.format_exc() if not isinstance(error, MultiAgentError) else None
            }
        )
        
        # 检查是否需要降级
        if self.should_degrade() and not self.degradation_active:
            await self._activate_degradation()
        
        return agent_error
    
    def _convert_to_agent_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> MultiAgentError:
        """将普通异常转换为MultiAgentError"""
        error_type = type(error).__name__
        error_message = str(error)
        
        # 根据异常类型判断错误类别
        if "timeout" in error_message.lower() or "TimeoutError" in error_type:
            return TimeoutError(f"Operation timeout: {error_message}", context=context)
        elif "network" in error_message.lower() or "ConnectionError" in error_type:
            return NetworkError(f"Network error: {error_message}", context=context)
        elif "rate" in error_message.lower() and "limit" in error_message.lower():
            return RateLimitError(f"Rate limit exceeded: {error_message}", context=context)
        elif "api" in error_message.lower() or "HTTPError" in error_type:
            return ModelAPIError(f"API error: {error_message}", context=context)
        elif "config" in error_message.lower():
            return ConfigurationError(f"Configuration error: {error_message}", context=context)
        elif "auth" in error_message.lower():
            return AuthenticationError(f"Authentication error: {error_message}", context=context)
        else:
            return ProcessingError(f"Processing error: {error_message}", context=context)
    
    async def _activate_degradation(self):
        """激活降级模式"""
        self.degradation_active = True
        self.degradation_start_time = datetime.now()
        logger.warning(f"Activating degradation mode: {self.degradation_config.level.value}")
        
        # 启动恢复检查任务
        asyncio.create_task(self._recovery_check_loop())
    
    async def _recovery_check_loop(self):
        """恢复检查循环"""
        while self.degradation_active:
            await asyncio.sleep(self.degradation_config.recovery_check_interval)
            
            # 检查是否可以恢复
            if await self._can_recover():
                await self._deactivate_degradation()
                break
    
    async def _can_recover(self) -> bool:
        """检查是否可以恢复正常模式"""
        # 检查错误率是否降低
        if self.stats.error_rate > self.degradation_config.error_rate_threshold * 0.5:
            return False
        
        # 检查最近是否有严重错误
        now = datetime.now()
        recent_errors = [
            e for e in self.stats.recent_errors
            if (now - e.timestamp).seconds < 60 and e.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        ]
        
        return len(recent_errors) == 0
    
    async def _deactivate_degradation(self):
        """停用降级模式"""
        self.degradation_active = False
        degradation_duration = datetime.now() - self.degradation_start_time
        logger.info(f"Deactivating degradation mode after {degradation_duration}")
    
    def get_fallback_function(self, function_name: str) -> Optional[Callable]:
        """获取降级备用函数"""
        if not self.degradation_active:
            return None
        
        return self.degradation_config.fallback_functions.get(function_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        return {
            "total_errors": self.stats.total_errors,
            "errors_by_category": {k.value: v for k, v in self.stats.errors_by_category.items()},
            "errors_by_severity": {k.value: v for k, v in self.stats.errors_by_severity.items()},
            "error_rate": self.stats.error_rate,
            "last_error_time": self.stats.last_error_time.isoformat() if self.stats.last_error_time else None,
            "degradation_active": self.degradation_active,
            "degradation_start_time": self.degradation_start_time.isoformat() if self.degradation_start_time else None
        }


def with_error_handling(
    operation_name: str = None,
    retry_config: Optional[RetryConfig] = None,
    context_extractor: Optional[Callable] = None
):
    """错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            handler = ErrorHandler(retry_config=retry_config)
            op_name = operation_name or func.__name__
            
            attempt = 1
            last_error = None
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    context = {}
                    if context_extractor:
                        try:
                            context = context_extractor(*args, **kwargs)
                        except Exception:
                            pass
                    
                    agent_error = await handler.handle_error(e, context, op_name)
                    last_error = agent_error
                    
                    if not handler.should_retry(agent_error, attempt):
                        raise agent_error
                    
                    # 计算重试延迟
                    config = handler.retry_config.category_configs.get(
                        agent_error.category, handler.retry_config
                    )
                    delay = config.get_delay(attempt)
                    
                    logger.info(f"Retrying {op_name} (attempt {attempt + 1}) after {delay:.2f}s")
                    await asyncio.sleep(delay)
                    attempt += 1
            
            # 如果所有重试都失败，抛出最后一个错误
            raise last_error
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 对于同步函数，创建简化的错误处理
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler = ErrorHandler()
                context = {}
                if context_extractor:
                    try:
                        context = context_extractor(*args, **kwargs)
                    except Exception:
                        pass
                
                agent_error = handler._convert_to_agent_error(e, context)
                handler.stats.add_error(agent_error)
                raise agent_error
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# 全局错误处理器实例
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def set_error_handler(handler: ErrorHandler):
    """设置全局错误处理器"""
    global _global_error_handler
    _global_error_handler = handler