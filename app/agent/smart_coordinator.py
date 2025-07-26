"""
Smart Coordinator for Multi-Agent System
智能协调器 - 作为用户交互的主入口，智能分析用户输入并协调agent工作
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from .unified_config import get_config_manager, AgentRole
from .input_analyzer import InputAnalyzer, InputType, InputAnalysisResult
from .preference_manager import PreferenceManager, UserPreferences
from .agent_orchestrator import AgentOrchestrator, WorkflowType, WorkflowResult
from .bounty_recommendation_agent import BountyRecommendationAgent, get_recommendation_agent
from .models import TaskInfo
from .exceptions import ConfigurationError, ModelAPIError, MultiAgentError
from .error_handler import get_error_handler, with_error_handling
from .error_messages import generate_user_friendly_error, MessageLanguage
from .structured_logging import get_logger
from .monitoring import performance_monitor, get_metrics_collector
from .debugging_tools import debug_trace, debug_context
from .concurrent_processor import get_concurrent_processor, TaskPriority
from ..core.performance import get_cache_manager, get_memory_optimizer, cache_result

logger = get_logger(__name__)


class UserIntent(str, Enum):
    """用户意图类型"""
    CREATE_TASK = "create_task"
    ANALYZE_CONTENT = "analyze_content"
    SET_PREFERENCES = "set_preferences"
    GET_STATUS = "get_status"
    GET_RECOMMENDATIONS = "get_recommendations"
    CHAT = "chat"
    HELP = "help"


@dataclass
class UserInput:
    """用户输入数据"""
    content: str
    input_type: InputType
    user_id: str
    metadata: Dict[str, Any]
    timestamp: datetime
    
    @classmethod
    def create(cls, content: str, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> 'UserInput':
        """创建用户输入实例"""
        return cls(
            content=content,
            input_type=InputType.TEXT,  # 默认为文本，后续会被分析器更新
            user_id=user_id,
            metadata=metadata or {},
            timestamp=datetime.utcnow()
        )


@dataclass
class ProcessContext:
    """处理上下文"""
    user_id: str
    preferences: UserPreferences
    conversation_history: List[Dict[str, Any]]
    workflow_type: WorkflowType
    metadata: Dict[str, Any]


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChatResponse:
    """聊天响应"""
    message: str
    task_info: Optional[TaskInfo] = None
    suggestions: List[str] = None
    requires_action: bool = False
    action_type: Optional[str] = None
    processing_time: float = 0.0


@dataclass
class ProcessResult:
    """处理结果"""
    success: bool
    task_info: Optional[TaskInfo] = None
    response_message: str = ""
    user_intent: Optional[UserIntent] = None
    suggestions: List[str] = None
    processing_time: float = 0.0
    error_message: Optional[str] = None


class SmartCoordinator:
    """智能协调器 - 多Agent系统的核心协调组件"""
    
    def __init__(self, db_session: Optional[Any] = None):
        self.config_manager = get_config_manager()
        self.input_analyzer = InputAnalyzer()
        self.preference_manager = PreferenceManager()
        self.agent_orchestrator = AgentOrchestrator()
        self.db_session = db_session
        self.recommendation_agent: Optional[BountyRecommendationAgent] = None
        
        # 对话历史管理
        self.conversation_histories: Dict[str, List[ChatMessage]] = {}
        
        # 性能优化组件
        self.cache_manager = get_cache_manager()
        self.memory_optimizer = get_memory_optimizer()
        self.concurrent_processor = None
        
        # 性能监控
        self.processing_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_processing_time": 0.0
        }
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化协调器"""
        try:
            # 初始化各个组件
            await self.preference_manager.initialize()
            await self.agent_orchestrator.initialize()
            
            # 初始化并发处理器
            self.concurrent_processor = await get_concurrent_processor()
            
            # 初始化推荐Agent（如果有数据库会话）
            if self.db_session:
                self.recommendation_agent = await get_recommendation_agent(self.db_session)
            
            self._initialized = True
            logger.info("智能协调器初始化完成")
            
        except Exception as e:
            logger.error(f"智能协调器初始化失败: {e}")
            raise ConfigurationError(f"Smart coordinator initialization failed: {str(e)}")
    
    @debug_trace(component="smart_coordinator", event_type="user_input_processing")
    @performance_monitor("smart_coordinator.process_user_input")
    @with_error_handling("process_user_input")
    async def process_user_input(
        self, 
        user_input: UserInput,
        context: Optional[Dict[str, Any]] = None
    ) -> ProcessResult:
        """
        处理用户输入的主要方法
        
        Args:
            user_input: 用户输入数据
            context: 额外的上下文信息
            
        Returns:
            ProcessResult: 处理结果
        """
        start_time = time.time()
        
        try:
            with debug_context("smart_coordinator", "process_user_input", 
                              user_id=user_input.user_id, 
                              content_length=len(user_input.content)):
                
                # 记录指标
                get_metrics_collector().increment_counter("user_input.requests", 
                                                        labels={"user_id": user_input.user_id})
                
                logger.info(f"处理用户输入: {user_input.user_id} - {user_input.content[:100]}...")
                
                # 1. 分析用户输入
                analysis_result = await self.input_analyzer.analyze_input(user_input.content)
                user_input.input_type = analysis_result.input_type
                
                # 记录输入类型指标
                get_metrics_collector().increment_counter("user_input.by_type", 
                                                        labels={"input_type": analysis_result.input_type.value})
                
                # 2. 获取用户偏好（使用缓存）
                user_preferences = await self._get_cached_user_preferences(user_input.user_id)
                
                # 3. 创建处理上下文
                process_context = ProcessContext(
                    user_id=user_input.user_id,
                    preferences=user_preferences,
                    conversation_history=self._get_conversation_history(user_input.user_id),
                    workflow_type=self._determine_workflow_type(analysis_result),
                    metadata=context or {}
                )
                
                # 4. 根据输入类型和意图选择处理策略
                if analysis_result.user_intent == UserIntent.CREATE_TASK:
                    # 优先使用并发处理
                    if self.concurrent_processor:
                        result = await self._handle_task_creation_concurrent(user_input, analysis_result, process_context)
                    else:
                        result = await self._handle_task_creation(user_input, analysis_result, process_context)
                elif analysis_result.user_intent == UserIntent.ANALYZE_CONTENT:
                    result = await self._handle_content_analysis(user_input, analysis_result, process_context)
                elif analysis_result.user_intent == UserIntent.SET_PREFERENCES:
                    result = await self._handle_preference_setting(user_input, analysis_result, process_context)
                elif analysis_result.user_intent == UserIntent.GET_RECOMMENDATIONS:
                    result = await self._handle_recommendation_request(user_input, analysis_result, process_context)
                elif analysis_result.user_intent == UserIntent.CHAT:
                    result = await self._handle_chat(user_input, analysis_result, process_context)
                else:
                    result = await self._handle_general_query(user_input, analysis_result, process_context)
                
                # 5. 更新对话历史
                self._update_conversation_history(user_input.user_id, user_input.content, result.response_message)
                
                # 6. 学习用户偏好
                await self.preference_manager.learn_from_interaction(
                    user_input.user_id, 
                    user_input, 
                    result
                )
                
                # 7. 更新统计信息
                processing_time = time.time() - start_time
                result.processing_time = processing_time
                self._update_stats(True, processing_time)
                
                logger.info(f"用户输入处理完成: {user_input.user_id} - 耗时 {processing_time:.2f}s")
                return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_stats(False, processing_time)
            
            logger.error(f"用户输入处理失败: {e}")
            return ProcessResult(
                success=False,
                response_message=f"处理失败: {str(e)}",
                processing_time=processing_time,
                error_message=str(e)
            )
    
    async def chat_with_user(
        self,
        message: str,
        user_id: str,
        conversation_history: Optional[List[ChatMessage]] = None
    ) -> ChatResponse:
        """
        与用户进行对话式交互
        
        Args:
            message: 用户消息
            user_id: 用户ID
            conversation_history: 对话历史
            
        Returns:
            ChatResponse: 聊天响应
        """
        start_time = time.time()
        
        try:
            # 创建用户输入
            user_input = UserInput.create(message, user_id)
            
            # 处理输入
            result = await self.process_user_input(user_input)
            
            # 生成聊天响应
            response = ChatResponse(
                message=result.response_message,
                task_info=result.task_info,
                suggestions=result.suggestions or [],
                requires_action=result.task_info is not None,
                action_type="task_created" if result.task_info else None,
                processing_time=time.time() - start_time
            )
            
            return response
            
        except Exception as e:
            logger.error(f"聊天处理失败: {e}")
            return ChatResponse(
                message=f"抱歉，处理您的消息时出现了问题: {str(e)}",
                processing_time=time.time() - start_time
            )
    
    async def _handle_task_creation(
        self, 
        user_input: UserInput, 
        analysis_result: InputAnalysisResult,
        context: ProcessContext
    ) -> ProcessResult:
        """处理任务创建请求"""
        try:
            # 根据输入类型选择工作流
            if analysis_result.input_type == InputType.URL:
                workflow_result = await self.agent_orchestrator.execute_workflow(
                    WorkflowType.URL_PROCESSING,
                    analysis_result.extracted_data,
                    context.preferences
                )
            elif analysis_result.input_type == InputType.IMAGE:
                workflow_result = await self.agent_orchestrator.execute_workflow(
                    WorkflowType.IMAGE_PROCESSING,
                    analysis_result.extracted_data,
                    context.preferences
                )
            elif analysis_result.input_type == InputType.MIXED:
                workflow_result = await self.agent_orchestrator.execute_workflow(
                    WorkflowType.MIXED_PROCESSING,
                    analysis_result.extracted_data,
                    context.preferences
                )
            else:
                # 纯文本内容
                workflow_result = await self.agent_orchestrator.execute_workflow(
                    WorkflowType.TEXT_PROCESSING,
                    user_input.content,
                    context.preferences
                )
            
            if workflow_result.success:
                return ProcessResult(
                    success=True,
                    task_info=workflow_result.task_info,
                    response_message=f"任务创建成功！标题: {workflow_result.task_info.title}",
                    user_intent=UserIntent.CREATE_TASK,
                    suggestions=self._generate_task_suggestions(workflow_result.task_info)
                )
            else:
                return ProcessResult(
                    success=False,
                    response_message=f"任务创建失败: {workflow_result.error_message}",
                    error_message=workflow_result.error_message
                )
                
        except Exception as e:
            logger.error(f"任务创建处理失败: {e}")
            return ProcessResult(
                success=False,
                response_message=f"任务创建失败: {str(e)}",
                error_message=str(e)
            )
    
    async def _handle_content_analysis(
        self, 
        user_input: UserInput, 
        analysis_result: InputAnalysisResult,
        context: ProcessContext
    ) -> ProcessResult:
        """处理内容分析请求"""
        try:
            # 执行内容分析工作流（不创建任务）
            workflow_result = await self.agent_orchestrator.execute_workflow(
                self._determine_workflow_type(analysis_result),
                analysis_result.extracted_data or user_input.content,
                context.preferences,
                create_task=False  # 只分析，不创建任务
            )
            
            if workflow_result.success:
                return ProcessResult(
                    success=True,
                    task_info=workflow_result.task_info,
                    response_message=self._format_analysis_response(workflow_result.task_info),
                    user_intent=UserIntent.ANALYZE_CONTENT,
                    suggestions=["创建任务", "修改分析重点", "保存分析结果"]
                )
            else:
                return ProcessResult(
                    success=False,
                    response_message=f"内容分析失败: {workflow_result.error_message}",
                    error_message=workflow_result.error_message
                )
                
        except Exception as e:
            logger.error(f"内容分析处理失败: {e}")
            return ProcessResult(
                success=False,
                response_message=f"内容分析失败: {str(e)}",
                error_message=str(e)
            )
    
    async def _handle_preference_setting(
        self, 
        user_input: UserInput, 
        analysis_result: InputAnalysisResult,
        context: ProcessContext
    ) -> ProcessResult:
        """处理偏好设置请求"""
        try:
            # 从输入中提取偏好设置
            preferences_update = analysis_result.extracted_preferences
            
            if preferences_update:
                # 更新用户偏好
                await self.preference_manager.update_user_preferences(
                    user_input.user_id, 
                    preferences_update
                )
                
                return ProcessResult(
                    success=True,
                    response_message="偏好设置已更新！",
                    user_intent=UserIntent.SET_PREFERENCES,
                    suggestions=["查看当前偏好", "重置偏好", "测试新偏好"]
                )
            else:
                return ProcessResult(
                    success=False,
                    response_message="无法识别偏好设置，请提供更具体的信息。",
                    suggestions=["设置输出格式", "设置分析重点", "设置语言偏好"]
                )
                
        except Exception as e:
            logger.error(f"偏好设置处理失败: {e}")
            return ProcessResult(
                success=False,
                response_message=f"偏好设置失败: {str(e)}",
                error_message=str(e)
            )
    
    async def _handle_chat(
        self, 
        user_input: UserInput, 
        analysis_result: InputAnalysisResult,
        context: ProcessContext
    ) -> ProcessResult:
        """处理一般聊天请求"""
        try:
            # 生成友好的回复
            response_message = self._generate_chat_response(user_input.content, context)
            
            return ProcessResult(
                success=True,
                response_message=response_message,
                user_intent=UserIntent.CHAT,
                suggestions=self._generate_chat_suggestions(context)
            )
            
        except Exception as e:
            logger.error(f"聊天处理失败: {e}")
            return ProcessResult(
                success=False,
                response_message="抱歉，我现在无法很好地回应您的消息。",
                error_message=str(e)
            )
    
    async def _handle_general_query(
        self, 
        user_input: UserInput, 
        analysis_result: InputAnalysisResult,
        context: ProcessContext
    ) -> ProcessResult:
        """处理一般查询请求"""
        try:
            if analysis_result.user_intent == UserIntent.GET_STATUS:
                # 返回系统状态
                status_info = await self._get_system_status()
                return ProcessResult(
                    success=True,
                    response_message=status_info,
                    user_intent=UserIntent.GET_STATUS
                )
            elif analysis_result.user_intent == UserIntent.HELP:
                # 返回帮助信息
                help_info = self._get_help_info()
                return ProcessResult(
                    success=True,
                    response_message=help_info,
                    user_intent=UserIntent.HELP,
                    suggestions=["创建任务", "分析内容", "设置偏好"]
                )
            else:
                # 默认处理
                return ProcessResult(
                    success=True,
                    response_message="我理解了您的请求，但需要更多信息来帮助您。",
                    suggestions=["提供URL链接", "上传图片", "描述具体需求"]
                )
                
        except Exception as e:
            logger.error(f"一般查询处理失败: {e}")
            return ProcessResult(
                success=False,
                response_message=f"查询处理失败: {str(e)}",
                error_message=str(e)
            )
    
    async def _handle_recommendation_request(
        self, 
        user_input: UserInput, 
        analysis_result: InputAnalysisResult,
        context: ProcessContext
    ) -> ProcessResult:
        """处理bounty推荐请求"""
        try:
            if not self.recommendation_agent:
                return ProcessResult(
                    success=False,
                    response_message="推荐功能暂时不可用，请稍后再试。",
                    error_message="Recommendation agent not initialized"
                )
            
            # 获取推荐
            recommendations = await self.recommendation_agent.get_recommendations(
                user_id=user_input.user_id,
                limit=5  # 默认推荐5个任务
            )
            
            if not recommendations:
                return ProcessResult(
                    success=True,
                    response_message="暂时没有找到适合您的bounty任务，请稍后再试或更新您的偏好设置。",
                    suggestions=["更新技能偏好", "设置兴趣领域", "查看所有任务"]
                )
            
            # 格式化推荐结果
            response_message = self._format_recommendations(recommendations, context.preferences)
            
            return ProcessResult(
                success=True,
                response_message=response_message,
                user_intent=UserIntent.GET_RECOMMENDATIONS,
                suggestions=["查看任务详情", "申请任务", "更新偏好", "获取更多推荐"]
            )
            
        except Exception as e:
            logger.error(f"推荐请求处理失败: {e}")
            return ProcessResult(
                success=False,
                response_message=f"获取推荐失败: {str(e)}",
                error_message=str(e)
            )
    
    def _format_recommendations(
        self, 
        recommendations: List[Any], 
        preferences: UserPreferences
    ) -> str:
        """格式化推荐结果"""
        if preferences.output_format.value == "JSON":
            import json
            recommendations_data = [
                {
                    "task_id": rec.task_id,
                    "title": rec.title,
                    "description": rec.description[:200] + "..." if len(rec.description) > 200 else rec.description,
                    "reward": rec.reward,
                    "reward_currency": rec.reward_currency,
                    "tags": rec.tags,
                    "difficulty_level": rec.difficulty_level,
                    "match_score": rec.match_score,
                    "match_reasons": rec.match_reasons
                }
                for rec in recommendations
            ]
            return f"为您推荐的bounty任务:\n```json\n{json.dumps(recommendations_data, indent=2, ensure_ascii=False)}\n```"
        
        elif preferences.output_format.value == "STRUCTURED":
            response = "🎯 为您推荐的bounty任务:\n\n"
            for i, rec in enumerate(recommendations, 1):
                response += f"**{i}. {rec.title}**\n"
                response += f"   💰 奖励: {rec.reward} {rec.reward_currency}\n"
                response += f"   🏷️ 标签: {', '.join(rec.tags)}\n"
                response += f"   📊 匹配度: {rec.match_score:.1%}\n"
                response += f"   ✨ 匹配原因: {', '.join(rec.match_reasons)}\n"
                if rec.deadline:
                    response += f"   ⏰ 截止时间: {rec.deadline.strftime('%Y-%m-%d')}\n"
                response += f"   📝 描述: {rec.description[:150]}...\n\n"
            return response
        
        else:  # MARKDOWN (default)
            response = "## 🎯 为您推荐的bounty任务\n\n"
            for i, rec in enumerate(recommendations, 1):
                response += f"### {i}. {rec.title}\n\n"
                response += f"**奖励:** {rec.reward} {rec.reward_currency}  \n"
                response += f"**标签:** {', '.join(rec.tags)}  \n"
                response += f"**匹配度:** {rec.match_score:.1%}  \n"
                response += f"**匹配原因:** {', '.join(rec.match_reasons)}  \n"
                if rec.deadline:
                    response += f"**截止时间:** {rec.deadline.strftime('%Y-%m-%d')}  \n"
                response += f"**描述:** {rec.description[:200]}{'...' if len(rec.description) > 200 else ''}\n\n"
                response += "---\n\n"
            return response
    
    def _determine_workflow_type(self, analysis_result: InputAnalysisResult) -> WorkflowType:
        """根据分析结果确定工作流类型"""
        if analysis_result.input_type == InputType.URL:
            return WorkflowType.URL_PROCESSING
        elif analysis_result.input_type == InputType.IMAGE:
            return WorkflowType.IMAGE_PROCESSING
        elif analysis_result.input_type == InputType.MIXED:
            return WorkflowType.MIXED_PROCESSING
        else:
            return WorkflowType.TEXT_PROCESSING
    
    def _get_conversation_history(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的对话历史"""
        if user_id not in self.conversation_histories:
            self.conversation_histories[user_id] = []
        
        # 转换为字典格式
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            }
            for msg in self.conversation_histories[user_id][-10:]  # 只保留最近10条
        ]
    
    def _update_conversation_history(self, user_id: str, user_message: str, assistant_response: str) -> None:
        """更新对话历史"""
        if user_id not in self.conversation_histories:
            self.conversation_histories[user_id] = []
        
        history = self.conversation_histories[user_id]
        
        # 添加用户消息
        history.append(ChatMessage(
            role="user",
            content=user_message,
            timestamp=datetime.utcnow()
        ))
        
        # 添加助手回复
        history.append(ChatMessage(
            role="assistant",
            content=assistant_response,
            timestamp=datetime.utcnow()
        ))
        
        # 保持历史记录在合理长度内
        if len(history) > 20:
            self.conversation_histories[user_id] = history[-20:]
    
    def _generate_task_suggestions(self, task_info: TaskInfo) -> List[str]:
        """根据任务信息生成建议"""
        suggestions = []
        
        if not task_info.deadline:
            suggestions.append("设置截止日期")
        
        if not task_info.reward:
            suggestions.append("设置奖励金额")
        
        if not task_info.tags:
            suggestions.append("添加相关标签")
        
        if not task_info.difficulty_level:
            suggestions.append("设置难度等级")
        
        suggestions.extend(["编辑任务", "发布任务", "保存草稿"])
        
        return suggestions
    
    def _format_analysis_response(self, task_info: TaskInfo) -> str:
        """格式化分析响应"""
        response = f"内容分析完成！\n\n"
        response += f"标题: {task_info.title}\n"
        response += f"描述: {task_info.description[:200]}...\n"
        
        if task_info.reward:
            response += f"奖励: {task_info.reward} {task_info.reward_currency}\n"
        
        if task_info.deadline:
            response += f"截止日期: {task_info.deadline}\n"
        
        if task_info.tags:
            response += f"标签: {', '.join(task_info.tags)}\n"
        
        if task_info.difficulty_level:
            response += f"难度: {task_info.difficulty_level}\n"
        
        return response
    
    def _generate_chat_response(self, message: str, context: ProcessContext) -> str:
        """生成聊天回复"""
        # 简单的聊天回复逻辑
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["你好", "hello", "hi"]):
            return f"您好！我是BountyGo的智能助手，可以帮您分析任务内容、创建任务或设置偏好。有什么可以帮您的吗？"
        
        elif any(word in message_lower for word in ["谢谢", "thank"]):
            return "不客气！如果还有其他需要帮助的地方，随时告诉我。"
        
        elif any(word in message_lower for word in ["帮助", "help"]):
            return self._get_help_info()
        
        else:
            return "我理解了您的消息。您可以发送URL链接、上传图片或描述任务需求，我会帮您分析和处理。"
    
    def _generate_chat_suggestions(self, context: ProcessContext) -> List[str]:
        """生成聊天建议"""
        return [
            "分析URL内容",
            "上传图片分析",
            "设置我的偏好",
            "查看系统状态",
            "获取帮助"
        ]
    
    async def _get_system_status(self) -> str:
        """获取系统状态信息"""
        try:
            orchestrator_status = await self.agent_orchestrator.get_status()
            
            status_info = "系统状态报告:\n\n"
            status_info += f"智能协调器: {'正常' if self._initialized else '未初始化'}\n"
            status_info += f"Agent编排器: {'正常' if orchestrator_status.get('initialized') else '未初始化'}\n"
            status_info += f"可用Agent数量: {orchestrator_status.get('agent_count', 0)}\n"
            status_info += f"处理请求总数: {self.processing_stats['total_requests']}\n"
            status_info += f"成功率: {self.processing_stats['successful_requests'] / max(self.processing_stats['total_requests'], 1) * 100:.1f}%\n"
            status_info += f"平均处理时间: {self.processing_stats['avg_processing_time']:.2f}秒\n"
            
            return status_info
            
        except Exception as e:
            return f"获取系统状态失败: {str(e)}"
    
    def _get_help_info(self) -> str:
        """获取帮助信息"""
        return """
BountyGo智能助手使用指南:

🔗 URL分析: 发送网页链接，我会分析其中的任务信息
🖼️ 图片分析: 上传图片，我会识别其中的任务内容
📝 文本分析: 直接描述任务需求，我会帮您结构化
⚙️ 偏好设置: 告诉我您的偏好，如输出格式、分析重点等
📊 系统状态: 查看当前系统运行状态
❓ 获取帮助: 随时询问使用方法

示例:
- "分析这个URL: https://example.com/task"
- "我希望输出格式为JSON"
- "重点关注技术要求"
- "系统状态如何？"
        """
    
    @cache_result(key_prefix="user_preferences", ttl_seconds=300)
    async def _get_cached_user_preferences(self, user_id: str) -> UserPreferences:
        """获取缓存的用户偏好"""
        return await self.preference_manager.get_user_preferences(user_id)
    
    async def _handle_task_creation_concurrent(
        self, 
        user_input: UserInput, 
        analysis_result: InputAnalysisResult,
        context: ProcessContext
    ) -> ProcessResult:
        """并发处理任务创建请求"""
        try:
            # 使用并发处理器执行工作流
            workflow_func = None
            workflow_data = None
            
            if analysis_result.input_type == InputType.URL:
                workflow_func = self.agent_orchestrator.execute_workflow
                workflow_data = (WorkflowType.URL_PROCESSING, analysis_result.extracted_data, context.preferences)
            elif analysis_result.input_type == InputType.IMAGE:
                workflow_func = self.agent_orchestrator.execute_workflow
                workflow_data = (WorkflowType.IMAGE_PROCESSING, analysis_result.extracted_data, context.preferences)
            elif analysis_result.input_type == InputType.MIXED:
                workflow_func = self.agent_orchestrator.execute_workflow
                workflow_data = (WorkflowType.MIXED_PROCESSING, analysis_result.extracted_data, context.preferences)
            else:
                workflow_func = self.agent_orchestrator.execute_workflow
                workflow_data = (WorkflowType.TEXT_PROCESSING, user_input.content, context.preferences)
            
            if self.concurrent_processor and workflow_func:
                # 使用并发处理器执行
                task_id = await self.concurrent_processor.submit_agent_task(
                    "orchestrator",
                    workflow_func,
                    *workflow_data,
                    priority=TaskPriority.HIGH,
                    timeout=60
                )
                
                task_result = await self.concurrent_processor.worker_pool.get_task_result(task_id, timeout=60)
                
                if task_result.status.value == "completed":
                    workflow_result = task_result.result
                else:
                    raise Exception(f"工作流执行失败: {task_result.error}")
            else:
                # 直接执行
                workflow_result = await workflow_func(*workflow_data)
            
            if workflow_result.success:
                return ProcessResult(
                    success=True,
                    task_info=workflow_result.task_info,
                    response_message=f"任务创建成功！标题: {workflow_result.task_info.title}",
                    user_intent=UserIntent.CREATE_TASK,
                    suggestions=self._generate_task_suggestions(workflow_result.task_info)
                )
            else:
                return ProcessResult(
                    success=False,
                    response_message=f"任务创建失败: {workflow_result.error_message}",
                    error_message=workflow_result.error_message
                )
                
        except Exception as e:
            logger.error(f"并发任务创建处理失败: {e}")
            return ProcessResult(
                success=False,
                response_message=f"任务创建失败: {str(e)}",
                error_message=str(e)
            )
    
    def _update_stats(self, success: bool, processing_time: float) -> None:
        """更新处理统计信息"""
        self.processing_stats["total_requests"] += 1
        
        if success:
            self.processing_stats["successful_requests"] += 1
        else:
            self.processing_stats["failed_requests"] += 1
        
        # 更新平均处理时间
        total = self.processing_stats["total_requests"]
        current_avg = self.processing_stats["avg_processing_time"]
        self.processing_stats["avg_processing_time"] = (
            (current_avg * (total - 1) + processing_time) / total
        )
        
        # 定期进行内存优化
        if total % 50 == 0:  # 每50个请求检查一次
            optimization_result = self.memory_optimizer.check_and_optimize()
            if optimization_result.get("optimized"):
                logger.info(f"内存优化完成: {optimization_result}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return self.processing_stats.copy()
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 全局智能协调器实例
_smart_coordinator: Optional[SmartCoordinator] = None


async def get_smart_coordinator() -> SmartCoordinator:
    """获取全局智能协调器实例"""
    global _smart_coordinator
    
    if _smart_coordinator is None:
        _smart_coordinator = SmartCoordinator()
        await _smart_coordinator.initialize()
    
    return _smart_coordinator