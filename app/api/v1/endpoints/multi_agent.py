"""
Multi-Agent System API Endpoints
多Agent系统API端点
"""
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from app.agent.smart_coordinator import (
    get_smart_coordinator, SmartCoordinator, UserInput, 
    ProcessResult, ChatResponse
)
from app.agent.preference_manager import UserPreferences, OutputFormat, AnalysisFocus
from app.agent.bounty_recommendation_agent import get_recommendation_agent, BountyRecommendation
from app.agent.unified_config import get_config_manager
from app.core.auth import get_current_user
from app.models.user import User
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


# Request/Response Models
class ProcessInputRequest(BaseModel):
    """处理输入请求"""
    content: str = Field(..., description="用户输入内容")
    context: Optional[Dict[str, Any]] = Field(None, description="额外上下文")


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")


class PreferenceUpdateRequest(BaseModel):
    """偏好更新请求"""
    output_format: Optional[str] = Field(None, description="输出格式")
    language: Optional[str] = Field(None, description="语言偏好")
    analysis_focus: Optional[List[str]] = Field(None, description="分析重点")
    quality_threshold: Optional[float] = Field(None, description="质量阈值")
    auto_create_tasks: Optional[bool] = Field(None, description="自动创建任务")


class ProcessInputResponse(BaseModel):
    """处理输入响应"""
    success: bool
    task_info: Optional[Dict[str, Any]] = None
    response_message: str
    user_intent: Optional[str] = None
    suggestions: List[str] = []
    processing_time: float
    error_message: Optional[str] = None


class ChatResponseModel(BaseModel):
    """聊天响应"""
    message: str
    task_info: Optional[Dict[str, Any]] = None
    suggestions: List[str] = []
    requires_action: bool = False
    action_type: Optional[str] = None
    processing_time: float


class PreferenceResponse(BaseModel):
    """偏好响应"""
    user_id: str
    output_format: str
    language: str
    analysis_focus: List[str]
    quality_threshold: float
    auto_create_tasks: bool
    updated_at: str


class SystemStatusResponse(BaseModel):
    """系统状态响应"""
    coordinator_status: Dict[str, Any]
    config_summary: Dict[str, Any]
    performance_stats: Dict[str, Any]


class RecommendationResponse(BaseModel):
    """推荐响应"""
    task_id: int
    title: str
    description: str
    reward: Optional[float]
    reward_currency: str
    tags: List[str]
    difficulty_level: Optional[str]
    estimated_hours: Optional[int]
    deadline: Optional[str]
    match_score: float
    match_reasons: List[str]


class RecommendationsResponse(BaseModel):
    """推荐列表响应"""
    recommendations: List[RecommendationResponse]
    total_count: int
    user_profile: Dict[str, Any]


# API Endpoints
@router.post("/process", response_model=ProcessInputResponse)
async def process_user_input(
    request: ProcessInputRequest,
    current_user: User = Depends(get_current_user)
):
    """
    处理用户输入
    
    支持多种输入类型：
    - 文本内容
    - URL链接
    - 图片数据（base64）
    - 混合内容
    """
    try:
        coordinator = await get_smart_coordinator()
        
        # 创建用户输入
        user_input = UserInput.create(
            content=request.content,
            user_id=str(current_user.id),
            metadata=request.context
        )
        
        # 处理输入
        result = await coordinator.process_user_input(user_input, request.context)
        
        # 转换任务信息
        task_info_dict = None
        if result.task_info:
            task_info_dict = {
                "title": result.task_info.title,
                "description": result.task_info.description,
                "reward": result.task_info.reward,
                "reward_currency": result.task_info.reward_currency,
                "deadline": result.task_info.deadline.isoformat() if result.task_info.deadline else None,
                "tags": result.task_info.tags,
                "difficulty_level": result.task_info.difficulty_level,
                "estimated_hours": result.task_info.estimated_hours
            }
        
        return ProcessInputResponse(
            success=result.success,
            task_info=task_info_dict,
            response_message=result.response_message,
            user_intent=result.user_intent.value if result.user_intent else None,
            suggestions=result.suggestions or [],
            processing_time=result.processing_time,
            error_message=result.error_message
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.post("/chat", response_model=ChatResponseModel)
async def chat_with_agent(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    与智能助手聊天
    
    支持自然语言对话，自动识别用户意图并提供相应服务。
    """
    try:
        coordinator = await get_smart_coordinator()
        
        # 进行聊天
        response = await coordinator.chat_with_user(
            message=request.message,
            user_id=str(current_user.id)
        )
        
        # 转换任务信息
        task_info_dict = None
        if response.task_info:
            task_info_dict = {
                "title": response.task_info.title,
                "description": response.task_info.description,
                "reward": response.task_info.reward,
                "reward_currency": response.task_info.reward_currency,
                "deadline": response.task_info.deadline.isoformat() if response.task_info.deadline else None,
                "tags": response.task_info.tags,
                "difficulty_level": response.task_info.difficulty_level,
                "estimated_hours": response.task_info.estimated_hours
            }
        
        return ChatResponseModel(
            message=response.message,
            task_info=task_info_dict,
            suggestions=response.suggestions or [],
            requires_action=response.requires_action,
            action_type=response.action_type,
            processing_time=response.processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}")


@router.get("/preferences", response_model=PreferenceResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user)
):
    """获取用户偏好设置"""
    try:
        coordinator = await get_smart_coordinator()
        
        preferences = await coordinator.preference_manager.get_user_preferences(
            str(current_user.id)
        )
        
        return PreferenceResponse(
            user_id=preferences.user_id,
            output_format=preferences.output_format.value,
            language=preferences.language,
            analysis_focus=[focus.value for focus in preferences.analysis_focus],
            quality_threshold=preferences.quality_threshold,
            auto_create_tasks=preferences.auto_create_tasks,
            updated_at=preferences.updated_at.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取偏好失败: {str(e)}")


@router.put("/preferences", response_model=PreferenceResponse)
async def update_user_preferences(
    request: PreferenceUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """更新用户偏好设置"""
    try:
        coordinator = await get_smart_coordinator()
        
        # 构建更新数据
        update_data = {}
        
        if request.output_format:
            update_data["output_format"] = request.output_format
        
        if request.language:
            update_data["language"] = request.language
        
        if request.analysis_focus:
            update_data["analysis_focus"] = request.analysis_focus
        
        if request.quality_threshold is not None:
            update_data["quality_threshold"] = request.quality_threshold
        
        if request.auto_create_tasks is not None:
            update_data["auto_create_tasks"] = request.auto_create_tasks
        
        # 更新偏好
        await coordinator.preference_manager.update_user_preferences(
            str(current_user.id),
            update_data
        )
        
        # 返回更新后的偏好
        preferences = await coordinator.preference_manager.get_user_preferences(
            str(current_user.id)
        )
        
        return PreferenceResponse(
            user_id=preferences.user_id,
            output_format=preferences.output_format.value,
            language=preferences.language,
            analysis_focus=[focus.value for focus in preferences.analysis_focus],
            quality_threshold=preferences.quality_threshold,
            auto_create_tasks=preferences.auto_create_tasks,
            updated_at=preferences.updated_at.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新偏好失败: {str(e)}")


@router.get("/preferences/suggestions")
async def get_preference_suggestions(
    current_user: User = Depends(get_current_user)
):
    """获取偏好建议"""
    try:
        coordinator = await get_smart_coordinator()
        
        suggestions = await coordinator.preference_manager.suggest_preferences(
            str(current_user.id)
        )
        
        return {
            "suggestions": [
                {
                    "preference_key": suggestion.preference_key,
                    "suggested_value": suggestion.suggested_value,
                    "reason": suggestion.reason,
                    "confidence": suggestion.confidence
                }
                for suggestion in suggestions
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取建议失败: {str(e)}")


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """获取系统状态"""
    try:
        coordinator = await get_smart_coordinator()
        config_manager = get_config_manager()
        
        # 获取协调器状态
        coordinator_stats = coordinator.get_stats()
        orchestrator_status = await coordinator.agent_orchestrator.get_status()
        
        coordinator_status = {
            "initialized": coordinator.is_initialized(),
            "processing_stats": coordinator_stats,
            "orchestrator": orchestrator_status
        }
        
        # 获取配置摘要
        config_summary = config_manager.get_config_summary()
        
        # 获取性能统计
        performance_stats = {
            "coordinator": coordinator_stats,
            "preference_manager": coordinator.preference_manager.get_stats()
        }
        
        return SystemStatusResponse(
            coordinator_status=coordinator_status,
            config_summary=config_summary,
            performance_stats=performance_stats
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/history")
async def get_interaction_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """获取用户交互历史"""
    try:
        coordinator = await get_smart_coordinator()
        
        history = coordinator.preference_manager.get_user_interaction_history(
            str(current_user.id),
            limit
        )
        
        return {
            "history": [
                {
                    "input_content": interaction.input_content,
                    "input_type": interaction.input_type,
                    "user_intent": interaction.user_intent,
                    "result_success": interaction.result_success,
                    "processing_time": interaction.processing_time,
                    "timestamp": interaction.timestamp.isoformat(),
                    "metadata": interaction.metadata
                }
                for interaction in history
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.post("/analyze-url")
async def analyze_url(
    url: str,
    create_task: bool = False,
    current_user: User = Depends(get_current_user)
):
    """分析URL内容（便捷接口）"""
    try:
        coordinator = await get_smart_coordinator()
        
        # 创建用户输入
        user_input = UserInput.create(
            content=url,
            user_id=str(current_user.id),
            metadata={"create_task": create_task}
        )
        
        # 处理输入
        result = await coordinator.process_user_input(user_input)
        
        return {
            "success": result.success,
            "task_info": result.task_info.__dict__ if result.task_info else None,
            "message": result.response_message,
            "processing_time": result.processing_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL分析失败: {str(e)}")


@router.post("/analyze-image")
async def analyze_image(
    image_data: str,
    create_task: bool = False,
    current_user: User = Depends(get_current_user)
):
    """分析图片内容（便捷接口）"""
    try:
        coordinator = await get_smart_coordinator()
        
        # 创建用户输入
        user_input = UserInput.create(
            content=image_data,
            user_id=str(current_user.id),
            metadata={"create_task": create_task}
        )
        
        # 处理输入
        result = await coordinator.process_user_input(user_input)
        
        return {
            "success": result.success,
            "task_info": result.task_info.__dict__ if result.task_info else None,
            "message": result.response_message,
            "processing_time": result.processing_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片分析失败: {str(e)}")


# 健康检查端点
@router.get("/health")
async def health_check():
    """多Agent系统健康检查"""
    try:
        coordinator = await get_smart_coordinator()
        config_manager = get_config_manager()
        
        health_status = {
            "status": "healthy",
            "components": {
                "smart_coordinator": coordinator.is_initialized(),
                "config_manager": config_manager.is_initialized(),
                "preference_manager": coordinator.preference_manager.is_initialized(),
                "agent_orchestrator": coordinator.agent_orchestrator.is_initialized()
            }
        }
        
        # 检查是否所有组件都健康
        all_healthy = all(health_status["components"].values())
        if not all_healthy:
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/recommendations", response_model=RecommendationsResponse)
async def get_bounty_recommendations(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取个性化bounty推荐
    
    基于用户的技能、兴趣和历史行为，使用RAG技术推荐最适合的bounty任务。
    """
    try:
        # 获取推荐Agent
        recommendation_agent = await get_recommendation_agent(db)
        
        # 获取推荐
        recommendations = await recommendation_agent.get_recommendations(
            user_id=str(current_user.id),
            limit=limit
        )
        
        # 获取用户档案信息
        user_skills, user_interests = await recommendation_agent._extract_user_profile(str(current_user.id))
        user_preferences = await recommendation_agent.preference_manager.get_user_preferences(str(current_user.id))
        
        user_profile = {
            "skills": user_skills,
            "interests": user_interests,
            "preferences": {
                "output_format": user_preferences.output_format.value,
                "language": user_preferences.language,
                "analysis_focus": [focus.value for focus in user_preferences.analysis_focus],
                "task_types": user_preferences.task_types
            }
        }
        
        # 转换推荐结果
        recommendation_responses = [
            RecommendationResponse(
                task_id=rec.task_id,
                title=rec.title,
                description=rec.description,
                reward=rec.reward,
                reward_currency=rec.reward_currency,
                tags=rec.tags,
                difficulty_level=rec.difficulty_level,
                estimated_hours=rec.estimated_hours,
                deadline=rec.deadline.isoformat() if rec.deadline else None,
                match_score=rec.match_score,
                match_reasons=rec.match_reasons
            )
            for rec in recommendations
        ]
        
        return RecommendationsResponse(
            recommendations=recommendation_responses,
            total_count=len(recommendation_responses),
            user_profile=user_profile
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推荐失败: {str(e)}")


@router.post("/ask-recommendations")
async def ask_for_recommendations(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    通过自然语言请求bounty推荐
    
    用户可以用自然语言描述他们想要的任务类型，系统会智能理解并提供相应推荐。
    """
    try:
        # 创建带数据库会话的智能协调器
        coordinator = SmartCoordinator(db_session=db)
        await coordinator.initialize()
        
        # 处理推荐请求
        response = await coordinator.chat_with_user(
            message=request.message,
            user_id=str(current_user.id)
        )
        
        return ChatResponseModel(
            message=response.message,
            task_info=None,  # 推荐不返回单个任务信息
            suggestions=response.suggestions or [],
            requires_action=False,
            action_type=None,
            processing_time=response.processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐请求失败: {str(e)}")


@router.post("/update-user-profile")
async def update_user_profile_for_recommendations(
    skills: List[str] = [],
    interests: List[str] = [],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新用户档案以改善推荐效果
    
    用户可以手动更新技能和兴趣信息，系统会据此调整推荐算法。
    """
    try:
        # 获取推荐Agent
        recommendation_agent = await get_recommendation_agent(db)
        
        # 更新用户嵌入向量
        await recommendation_agent.update_user_embedding(str(current_user.id))
        
        # 获取偏好管理器并更新相关偏好
        preference_manager = recommendation_agent.preference_manager
        
        # 根据技能和兴趣推断任务类型偏好
        task_types = []
        if any(skill in ["python", "javascript", "solidity", "rust"] for skill in skills):
            task_types.append("programming")
        if any(interest in ["web3", "blockchain", "crypto"] for interest in interests):
            task_types.append("web3")
        if any(skill in ["design", "ui", "ux"] for skill in skills):
            task_types.append("design")
        
        # 更新偏好
        if task_types:
            await preference_manager.update_user_preferences(
                str(current_user.id),
                {"task_types": task_types}
            )
        
        return {
            "success": True,
            "message": "用户档案已更新，推荐效果将会改善",
            "updated_skills": skills,
            "updated_interests": interests,
            "inferred_task_types": task_types
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新用户档案失败: {str(e)}")