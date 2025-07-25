"""
Custom exceptions for URL agent functionality.
"""


class URLAgentError(Exception):
    """URL代理基础异常"""
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class URLValidationError(URLAgentError):
    """URL验证错误"""
    pass


class ContentExtractionError(URLAgentError):
    """内容提取错误"""
    pass


class ModelAPIError(URLAgentError):
    """模型API调用错误"""
    pass


class TaskCreationError(URLAgentError):
    """任务创建错误"""
    pass


class ConfigurationError(URLAgentError):
    """配置错误"""
    pass