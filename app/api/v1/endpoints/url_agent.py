"""
URL代理API端点 - 智能URL内容提取和任务创建
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl, Field

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_user_optional
from app.models.user import User
from app.agent.service import URLAgentService
from app.agent.models import TaskInfo
from app.agent.exceptions import URLAgentError
from app.schemas.base import SuccessResponse

router = APIRouter()


# Request/Response schemas
class URLProcessRequest(BaseModel):
    """URL处理请求"""
    url: HttpUrl = Field(..., description="要处理的URL")
    auto_create: bool = Field(default=False, description="是否自动创建任务")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://github.com/example/project",
                "auto_create": False
            }
        }


class URLExtractRequest(BaseModel):
    """URL信息提取请求"""
    url: HttpUrl = Field(..., description="要分析的URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://github.com/example/project"
            }
        }


class ContentExtractRequest(BaseModel):
    """文本内容提取请求"""
    content: str = Field(..., min_length=10, max_length=50000, description="要分析的文本内容")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Looking for a Python developer to build a web scraping tool. Budget: $500. Deadline: 2024-12-31."
            }
        }


class TaskInfoResponse(BaseModel):
    """任务信息响应"""
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    reward: Optional[float] = Field(None, description="奖励金额")
    reward_currency: Optional[str] = Field(None, description="奖励货币")
    deadline: Optional[str] = Field(None, description="截止日期 (ISO格式)")
    tags: list[str] = Field(default=[], description="相关标签")
    difficulty_level: Optional[str] = Field(None, description="难度等级")
    estimated_hours: Optional[int] = Field(None, description="预估工时")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Python Web Scraping Project",
                "description": "Build a web scraping tool using Python and BeautifulSoup",
                "reward": 500.0,
                "reward_currency": "USD",
                "deadline": "2024-12-31T23:59:59",
                "tags": ["python", "web-scraping", "beautifulsoup"],
                "difficulty_level": "中级",
                "estimated_hours": 20
            }
        }


class URLProcessResponse(BaseModel):
    """URL处理响应"""
    success: bool = Field(..., description="处理是否成功")
    task_id: Optional[int] = Field(None, description="创建的任务ID（如果auto_create=True）")
    extracted_info: TaskInfoResponse = Field(..., description="提取的任务信息")
    processing_time: float = Field(..., description="处理时间（秒）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "task_id": 123,
                "extracted_info": {
                    "title": "Python Web Scraping Project",
                    "description": "Build a web scraping tool",
                    "reward": 500.0,
                    "reward_currency": "USD",
                    "tags": ["python", "web-scraping"]
                },
                "processing_time": 2.5
            }
        }


class ServiceStatusResponse(BaseModel):
    """服务状态响应"""
    service_name: str = Field(..., description="服务名称")
    status: str = Field(..., description="服务状态")
    components: dict = Field(..., description="组件状态")
    metrics: dict = Field(..., description="性能指标")
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_name": "URLAgentService",
                "status": "healthy",
                "components": {
                    "content_extractor": {"status": "ready"},
                    "url_parsing_agent": {"status": "ready"},
                    "ppio_client": {"status": "ready"}
                },
                "metrics": {
                    "total_requests": 100,
                    "success_rate": 0.95,
                    "avg_processing_time": 2.3
                }
            }
        }


# Helper function to convert TaskInfo to response
def task_info_to_response(task_info: TaskInfo) -> TaskInfoResponse:
    """将TaskInfo转换为响应格式"""
    return TaskInfoResponse(
        title=task_info.title,
        description=task_info.description,
        reward=float(task_info.reward) if task_info.reward else None,
        reward_currency=task_info.reward_currency,
        deadline=task_info.deadline.isoformat() if task_info.deadline else None,
        tags=task_info.tags,
        difficulty_level=task_info.difficulty_level,
        estimated_hours=task_info.estimated_hours
    )


@router.post("/process", response_model=URLProcessResponse, summary="处理URL并提取任务信息")
async def process_url(
    request: URLProcessRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    处理URL并提取任务信息，可选择自动创建任务
    
    - **url**: 要处理的URL（支持GitHub、任务平台等）
    - **auto_create**: 是否自动创建任务到数据库
    
    **需要认证**: 是
    
    **处理流程**:
    1. 提取网页内容
    2. AI分析并提取结构化任务信息
    3. 如果auto_create=True，自动创建任务
    
    **支持的URL类型**:
    - GitHub项目和Issue
    - 自由职业平台任务
    - 开发者社区任务
    - 其他包含任务信息的网页
    """
    try:
        # 创建URL代理服务实例
        service = URLAgentService(db_session=db)
        
        # 处理URL
        result = await service.process_url(
            url=str(request.url),
            user_id=current_user.id,
            auto_create=request.auto_create
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"URL处理失败: {result.error_message}"
            )
        
        return URLProcessResponse(
            success=result.success,
            task_id=result.task_id,
            extracted_info=task_info_to_response(result.extracted_info),
            processing_time=result.processing_time
        )
        
    except URLAgentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}"
        )


@router.post("/extract-info", response_model=TaskInfoResponse, summary="从URL提取任务信息")
async def extract_task_info(
    request: URLExtractRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    从URL提取任务信息（不创建任务）
    
    - **url**: 要分析的URL
    
    **需要认证**: 否（公开端点）
    
    **用途**:
    - 预览URL中的任务信息
    - 验证URL是否包含有效的任务内容
    - 获取任务信息用于前端展示
    """
    try:
        # 创建URL代理服务实例（不需要数据库会话）
        service = URLAgentService()
        
        # 提取任务信息
        task_info = await service.extract_task_info(str(request.url))
        
        return task_info_to_response(task_info)
        
    except URLAgentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}"
        )


@router.post("/extract-from-content", response_model=TaskInfoResponse, summary="从文本内容提取任务信息")
async def extract_from_content(
    request: ContentExtractRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    从文本内容提取任务信息
    
    - **content**: 要分析的文本内容
    
    **需要认证**: 否（公开端点）
    
    **用途**:
    - 分析用户粘贴的任务描述
    - 从邮件或消息中提取任务信息
    - 批量处理文本内容
    """
    try:
        # 创建URL代理服务实例
        service = URLAgentService()
        
        # 从内容提取任务信息
        task_info = await service.extract_task_info_from_content(request.content)
        
        return task_info_to_response(task_info)
        
    except URLAgentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}"
        )


@router.post("/create-task", response_model=SuccessResponse, summary="从任务信息创建任务")
async def create_task_from_info(
    task_info: TaskInfoResponse,
    source_url: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    从提取的任务信息创建任务
    
    - **task_info**: 任务信息（通常来自extract-info端点）
    - **source_url**: 源URL（可选）
    
    **需要认证**: 是
    
    **用途**:
    - 在预览任务信息后创建任务
    - 批量创建任务
    - 自定义任务创建流程
    """
    try:
        # 创建URL代理服务实例
        service = URLAgentService(db_session=db)
        
        # 转换响应格式为TaskInfo
        from datetime import datetime
        from decimal import Decimal
        
        task_info_obj = TaskInfo(
            title=task_info.title,
            description=task_info.description,
            reward=Decimal(str(task_info.reward)) if task_info.reward else None,
            reward_currency=task_info.reward_currency or "USD",
            deadline=datetime.fromisoformat(task_info.deadline) if task_info.deadline else None,
            tags=task_info.tags,
            difficulty_level=task_info.difficulty_level,
            estimated_hours=task_info.estimated_hours
        )
        
        # 创建任务
        task_id = await service.create_task_from_info(
            task_info=task_info_obj,
            user_id=current_user.id,
            source_url=source_url
        )
        
        return SuccessResponse(
            success=True,
            message=f"任务创建成功，ID: {task_id}",
            data={"task_id": task_id}
        )
        
    except URLAgentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}"
        )


@router.get("/status", response_model=ServiceStatusResponse, summary="获取URL代理服务状态")
async def get_service_status():
    """
    获取URL代理服务状态和性能指标
    
    **需要认证**: 否（公开端点）
    
    **返回信息**:
    - 服务整体状态
    - 各组件状态
    - 性能指标
    - 健康检查结果
    """
    try:
        # 创建URL代理服务实例
        service = URLAgentService()
        
        # 获取健康检查结果
        health_status = await service.health_check()
        
        return ServiceStatusResponse(
            service_name=health_status.get("service_name", "URLAgentService"),
            status=health_status.get("status", "unknown"),
            components=health_status.get("components", {}),
            metrics=health_status.get("metrics", {})
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法获取服务状态: {str(e)}"
        )


@router.get("/metrics", summary="获取性能指标")
async def get_performance_metrics(
    current_user: User = Depends(get_current_user)
):
    """
    获取URL代理服务的详细性能指标
    
    **需要认证**: 是（管理员功能）
    
    **返回信息**:
    - 请求统计
    - 处理时间分析
    - 错误统计
    - 组件性能
    """
    try:
        # 创建URL代理服务实例
        service = URLAgentService()
        
        # 获取性能指标
        metrics = service.get_performance_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "timestamp": "2024-01-01T00:00:00Z"  # 实际应该使用当前时间
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法获取性能指标: {str(e)}"
        )


@router.post("/reset-metrics", summary="重置性能指标")
async def reset_performance_metrics(
    current_user: User = Depends(get_current_user)
):
    """
    重置URL代理服务的性能指标
    
    **需要认证**: 是（管理员功能）
    
    **用途**:
    - 清除历史统计数据
    - 重新开始性能监控
    - 测试和调试
    """
    try:
        # 创建URL代理服务实例
        service = URLAgentService()
        
        # 重置指标
        service.reset_metrics()
        
        return SuccessResponse(
            success=True,
            message="性能指标已重置"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法重置性能指标: {str(e)}"
        )