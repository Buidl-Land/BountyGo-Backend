"""
Custom exceptions for multi-agent system functionality.
多代理系统自定义异常
"""
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class ErrorSeverity(str, Enum):
    """错误严重程度"""
    LOW = "low"           # 轻微错误，不影响主要功能
    MEDIUM = "medium"     # 中等错误，影响部分功能
    HIGH = "high"         # 严重错误，影响核心功能
    CRITICAL = "critical" # 致命错误，系统无法正常运行


class ErrorCategory(str, Enum):
    """错误分类"""
    CONFIGURATION = "configuration"     # 配置错误
    NETWORK = "network"                # 网络错误
    MODEL_API = "model_api"            # 模型API错误
    VALIDATION = "validation"          # 验证错误
    PROCESSING = "processing"          # 处理错误
    STORAGE = "storage"                # 存储错误
    AUTHENTICATION = "authentication"   # 认证错误
    RATE_LIMIT = "rate_limit"          # 限流错误
    TIMEOUT = "timeout"                # 超时错误
    RESOURCE = "resource"              # 资源错误


class MultiAgentError(Exception):
    """多代理系统基础异常"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.PROCESSING,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        retry_after: Optional[int] = None,
        user_message: Optional[str] = None
    ):
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details
        self.context = context or {}
        self.recoverable = recoverable
        self.retry_after = retry_after
        self.user_message = user_message or self._generate_user_message()
        self.timestamp = datetime.now()
        super().__init__(self.message)
    
    def _generate_user_message(self) -> str:
        """生成用户友好的错误消息"""
        if self.category == ErrorCategory.NETWORK:
            return "网络连接出现问题，请检查网络连接后重试"
        elif self.category == ErrorCategory.MODEL_API:
            return "AI模型服务暂时不可用，请稍后重试"
        elif self.category == ErrorCategory.CONFIGURATION:
            return "系统配置有误，请联系管理员"
        elif self.category == ErrorCategory.RATE_LIMIT:
            return "请求过于频繁，请稍后重试"
        elif self.category == ErrorCategory.TIMEOUT:
            return "处理超时，请重试或简化请求"
        else:
            return "处理过程中出现错误，请重试"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "context": self.context,
            "recoverable": self.recoverable,
            "retry_after": self.retry_after,
            "user_message": self.user_message,
            "timestamp": self.timestamp.isoformat()
        }


# 配置相关错误
class ConfigurationError(MultiAgentError):
    """配置错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


class ValidationError(MultiAgentError):
    """验证错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


# 网络和API相关错误
class NetworkError(MultiAgentError):
    """网络错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            retry_after=30,
            **kwargs
        )


class ModelAPIError(MultiAgentError):
    """模型API调用错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.MODEL_API,
            severity=ErrorSeverity.MEDIUM,
            retry_after=10,
            **kwargs
        )


class RateLimitError(MultiAgentError):
    """限流错误"""
    def __init__(self, message: str, retry_after: int = 60, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            retry_after=retry_after,
            **kwargs
        )


class TimeoutError(MultiAgentError):
    """超时错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            retry_after=5,
            **kwargs
        )


# 处理相关错误
class ProcessingError(MultiAgentError):
    """处理错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ContentExtractionError(ProcessingError):
    """内容提取错误"""
    pass


class TaskCreationError(ProcessingError):
    """任务创建错误"""
    pass


class URLValidationError(ValidationError):
    """URL验证错误"""
    pass


# 存储相关错误
class StorageError(MultiAgentError):
    """存储错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.STORAGE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


# 认证相关错误
class AuthenticationError(MultiAgentError):
    """认证错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


# 资源相关错误
class ResourceError(MultiAgentError):
    """资源错误"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


# 向后兼容的别名
URLAgentError = MultiAgentError