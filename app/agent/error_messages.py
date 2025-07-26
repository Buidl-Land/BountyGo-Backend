"""
User-Friendly Error Messages for Multi-Agent System
用户友好的错误消息生成器
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .exceptions import MultiAgentError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class MessageLanguage(str, Enum):
    """消息语言"""
    CHINESE = "zh"
    ENGLISH = "en"


class ErrorMessageGenerator:
    """错误消息生成器"""
    
    def __init__(self, language: MessageLanguage = MessageLanguage.CHINESE):
        self.language = language
        self._setup_message_templates()
    
    def _setup_message_templates(self):
        """设置消息模板"""
        if self.language == MessageLanguage.CHINESE:
            self.templates = {
                ErrorCategory.NETWORK: {
                    "title": "网络连接问题",
                    "message": "无法连接到服务器，请检查网络连接",
                    "suggestions": [
                        "检查网络连接是否正常",
                        "尝试刷新页面或重新发送请求",
                        "如果问题持续，请稍后再试"
                    ],
                    "technical_action": "检查网络配置和防火墙设置"
                },
                ErrorCategory.MODEL_API: {
                    "title": "AI服务暂时不可用",
                    "message": "AI模型服务出现问题，正在尝试恢复",
                    "suggestions": [
                        "请稍等片刻后重试",
                        "如果急需处理，可以尝试简化请求内容",
                        "问题通常会在几分钟内自动恢复"
                    ],
                    "technical_action": "检查API密钥和模型服务状态"
                },
                ErrorCategory.RATE_LIMIT: {
                    "title": "请求过于频繁",
                    "message": "您的请求速度过快，请稍后再试",
                    "suggestions": [
                        "请等待 {retry_after} 秒后重试",
                        "减少同时发送的请求数量",
                        "考虑升级到更高级别的服务计划"
                    ],
                    "technical_action": "实施请求限流和队列机制"
                },
                ErrorCategory.TIMEOUT: {
                    "title": "处理超时",
                    "message": "请求处理时间过长，已自动取消",
                    "suggestions": [
                        "尝试简化您的请求内容",
                        "分批处理大量数据",
                        "检查网络连接稳定性"
                    ],
                    "technical_action": "优化处理逻辑或增加超时时间"
                },
                ErrorCategory.CONFIGURATION: {
                    "title": "系统配置错误",
                    "message": "系统配置存在问题，无法正常处理请求",
                    "suggestions": [
                        "请联系系统管理员",
                        "这通常需要技术人员介入解决",
                        "请提供错误详情以便快速定位问题"
                    ],
                    "technical_action": "检查配置文件和环境变量"
                },
                ErrorCategory.VALIDATION: {
                    "title": "输入验证失败",
                    "message": "您提供的信息格式不正确",
                    "suggestions": [
                        "请检查输入格式是否正确",
                        "确保所有必填字段都已填写",
                        "参考示例格式重新输入"
                    ],
                    "technical_action": "检查输入验证规则"
                },
                ErrorCategory.PROCESSING: {
                    "title": "处理过程出错",
                    "message": "处理您的请求时遇到问题",
                    "suggestions": [
                        "请重试您的操作",
                        "如果问题持续，请简化请求内容",
                        "联系技术支持获取帮助"
                    ],
                    "technical_action": "检查处理逻辑和数据完整性"
                },
                ErrorCategory.STORAGE: {
                    "title": "数据存储问题",
                    "message": "无法保存或读取数据",
                    "suggestions": [
                        "请稍后重试",
                        "检查是否有足够的存储空间",
                        "如果问题持续，请联系管理员"
                    ],
                    "technical_action": "检查存储系统状态和权限"
                },
                ErrorCategory.AUTHENTICATION: {
                    "title": "身份验证失败",
                    "message": "无法验证您的身份信息",
                    "suggestions": [
                        "请检查登录凭据是否正确",
                        "尝试重新登录",
                        "如果忘记密码，请使用密码重置功能"
                    ],
                    "technical_action": "检查认证服务和用户权限"
                },
                ErrorCategory.RESOURCE: {
                    "title": "系统资源不足",
                    "message": "系统资源暂时不足，无法处理请求",
                    "suggestions": [
                        "请稍后重试",
                        "尝试在系统负载较低时使用",
                        "考虑分批处理大量请求"
                    ],
                    "technical_action": "检查系统资源使用情况"
                }
            }
        else:  # English
            self.templates = {
                ErrorCategory.NETWORK: {
                    "title": "Network Connection Issue",
                    "message": "Unable to connect to the server, please check your network connection",
                    "suggestions": [
                        "Check if your network connection is working",
                        "Try refreshing the page or resending the request",
                        "If the problem persists, please try again later"
                    ],
                    "technical_action": "Check network configuration and firewall settings"
                },
                ErrorCategory.MODEL_API: {
                    "title": "AI Service Temporarily Unavailable",
                    "message": "The AI model service is experiencing issues and is being restored",
                    "suggestions": [
                        "Please wait a moment and try again",
                        "If urgent, try simplifying your request",
                        "The issue usually resolves automatically within minutes"
                    ],
                    "technical_action": "Check API keys and model service status"
                },
                # ... 其他英文模板
            }
    
    def generate_user_message(
        self,
        error: MultiAgentError,
        include_suggestions: bool = True,
        include_technical_details: bool = False
    ) -> Dict[str, Any]:
        """生成用户友好的错误消息"""
        template = self.templates.get(error.category, self.templates[ErrorCategory.PROCESSING])
        
        message_data = {
            "title": template["title"],
            "message": template["message"],
            "severity": error.severity.value,
            "timestamp": error.timestamp.isoformat(),
            "error_id": id(error),  # 简单的错误ID
            "recoverable": error.recoverable
        }
        
        # 格式化消息（替换占位符）
        if error.retry_after and "{retry_after}" in template["message"]:
            message_data["message"] = template["message"].format(retry_after=error.retry_after)
        
        # 添加建议
        if include_suggestions:
            suggestions = template["suggestions"].copy()
            if error.retry_after and any("{retry_after}" in s for s in suggestions):
                suggestions = [s.format(retry_after=error.retry_after) for s in suggestions]
            message_data["suggestions"] = suggestions
        
        # 添加技术详情
        if include_technical_details:
            message_data["technical_details"] = {
                "category": error.category.value,
                "original_message": error.message,
                "details": error.details,
                "context": error.context,
                "technical_action": template["technical_action"]
            }
        
        # 添加恢复信息
        if error.recoverable and error.retry_after:
            message_data["retry_info"] = {
                "can_retry": True,
                "retry_after": error.retry_after,
                "retry_message": f"您可以在 {error.retry_after} 秒后重试" if self.language == MessageLanguage.CHINESE 
                                else f"You can retry after {error.retry_after} seconds"
            }
        
        return message_data
    
    def generate_summary_message(
        self,
        errors: List[MultiAgentError],
        time_window_minutes: int = 5
    ) -> Dict[str, Any]:
        """生成错误摘要消息"""
        if not errors:
            return {"message": "无错误记录" if self.language == MessageLanguage.CHINESE else "No errors recorded"}
        
        # 按类别统计错误
        category_counts = {}
        severity_counts = {}
        recent_errors = []
        
        now = datetime.now()
        for error in errors:
            if (now - error.timestamp).total_seconds() <= time_window_minutes * 60:
                recent_errors.append(error)
                category_counts[error.category] = category_counts.get(error.category, 0) + 1
                severity_counts[error.severity] = severity_counts.get(error.severity, 0) + 1
        
        if self.language == MessageLanguage.CHINESE:
            summary = {
                "title": f"最近 {time_window_minutes} 分钟错误摘要",
                "total_errors": len(recent_errors),
                "message": f"检测到 {len(recent_errors)} 个错误",
                "categories": {
                    category.value: {
                        "count": count,
                        "name": self.templates[category]["title"]
                    }
                    for category, count in category_counts.items()
                },
                "severity_distribution": {
                    severity.value: count
                    for severity, count in severity_counts.items()
                },
                "recommendations": self._generate_summary_recommendations(category_counts, severity_counts)
            }
        else:
            summary = {
                "title": f"Error Summary for Last {time_window_minutes} Minutes",
                "total_errors": len(recent_errors),
                "message": f"Detected {len(recent_errors)} errors",
                "categories": {
                    category.value: {
                        "count": count,
                        "name": self.templates.get(category, {}).get("title", category.value)
                    }
                    for category, count in category_counts.items()
                },
                "severity_distribution": {
                    severity.value: count
                    for severity, count in severity_counts.items()
                },
                "recommendations": self._generate_summary_recommendations(category_counts, severity_counts)
            }
        
        return summary
    
    def _generate_summary_recommendations(
        self,
        category_counts: Dict[ErrorCategory, int],
        severity_counts: Dict[ErrorSeverity, int]
    ) -> List[str]:
        """生成摘要建议"""
        recommendations = []
        
        if self.language == MessageLanguage.CHINESE:
            # 基于错误类别的建议
            if ErrorCategory.NETWORK in category_counts and category_counts[ErrorCategory.NETWORK] > 2:
                recommendations.append("检测到多个网络错误，建议检查网络连接稳定性")
            
            if ErrorCategory.MODEL_API in category_counts and category_counts[ErrorCategory.MODEL_API] > 1:
                recommendations.append("AI服务出现多次错误，建议稍后重试或联系技术支持")
            
            if ErrorCategory.RATE_LIMIT in category_counts:
                recommendations.append("触发了速率限制，建议降低请求频率")
            
            # 基于严重程度的建议
            if ErrorSeverity.CRITICAL in severity_counts:
                recommendations.append("检测到严重错误，建议立即联系技术支持")
            elif ErrorSeverity.HIGH in severity_counts and severity_counts[ErrorSeverity.HIGH] > 1:
                recommendations.append("多个高严重性错误，建议检查系统状态")
            
            if not recommendations:
                recommendations.append("大部分错误可以通过重试解决")
        else:
            # English recommendations
            if ErrorCategory.NETWORK in category_counts and category_counts[ErrorCategory.NETWORK] > 2:
                recommendations.append("Multiple network errors detected, check network connection stability")
            
            if ErrorCategory.MODEL_API in category_counts and category_counts[ErrorCategory.MODEL_API] > 1:
                recommendations.append("AI service errors detected, try again later or contact support")
            
            if ErrorCategory.RATE_LIMIT in category_counts:
                recommendations.append("Rate limit triggered, reduce request frequency")
            
            if ErrorSeverity.CRITICAL in severity_counts:
                recommendations.append("Critical errors detected, contact technical support immediately")
            elif ErrorSeverity.HIGH in severity_counts and severity_counts[ErrorSeverity.HIGH] > 1:
                recommendations.append("Multiple high-severity errors, check system status")
            
            if not recommendations:
                recommendations.append("Most errors can be resolved by retrying")
        
        return recommendations


# 全局消息生成器实例
_global_message_generator: Optional[ErrorMessageGenerator] = None


def get_message_generator(language: MessageLanguage = MessageLanguage.CHINESE) -> ErrorMessageGenerator:
    """获取全局消息生成器"""
    global _global_message_generator
    if _global_message_generator is None or _global_message_generator.language != language:
        _global_message_generator = ErrorMessageGenerator(language)
    return _global_message_generator


def generate_user_friendly_error(
    error: MultiAgentError,
    language: MessageLanguage = MessageLanguage.CHINESE,
    include_suggestions: bool = True,
    include_technical_details: bool = False
) -> Dict[str, Any]:
    """生成用户友好的错误消息（便捷函数）"""
    generator = get_message_generator(language)
    return generator.generate_user_message(error, include_suggestions, include_technical_details)