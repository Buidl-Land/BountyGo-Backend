"""
Data models for URL agent functionality.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class URLProcessRequest(BaseModel):
    """URL处理请求模型"""
    url: HttpUrl = Field(..., description="要处理的URL")
    user_id: int = Field(..., description="用户ID")
    auto_create: bool = Field(default=False, description="是否自动创建任务")


class WebContent(BaseModel):
    """网页内容模型"""
    url: str = Field(..., description="网页URL")
    title: str = Field(..., description="网页标题")
    content: str = Field(..., description="网页内容")
    meta_description: Optional[str] = Field(None, description="Meta描述")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="提取时间")


class OrganizerInfo(BaseModel):
    """AI提取的主办方信息模型"""
    name: str = Field(..., description="主办方名称")


class TaskInfo(BaseModel):
    """AI提取的任务信息模型"""
    title: str = Field(..., description="任务标题")
    summary: Optional[str] = Field(None, description="任务简介")
    description: Optional[str] = Field(None, description="任务描述")
    deadline: Optional[int] = Field(None, description="截止日期时间戳")
    category: Optional[str] = Field(None, description="任务分类：黑客松、征文、Meme创作、Web3交互、推特抽奖、开发实战")
    reward_details: Optional[str] = Field(None, description="奖励详情")
    reward_type: Optional[str] = Field(None, description="奖励分类：每人、瓜分、抽奖、积分、权益")
    reward: Optional[Decimal] = Field(None, description="奖励金额")
    reward_currency: Optional[str] = Field(None, description="奖励货币")
    tags: Optional[List[str]] = Field(None, description="任务标签列表")
    difficulty_level: Optional[str] = Field(None, description="难度等级")
    estimated_hours: Optional[int] = Field(None, description="预估工时")
    organizer_name: Optional[str] = Field(None, description="主办方名称")
    external_link: Optional[str] = Field(None, description="活动原始链接")


class TaskProcessResult(BaseModel):
    """任务处理结果模型"""
    success: bool = Field(..., description="处理是否成功")
    task_id: Optional[int] = Field(None, description="创建的任务ID")
    extracted_info: Optional[TaskInfo] = Field(None, description="提取的任务信息")
    error_message: Optional[str] = Field(None, description="错误信息")
    processing_time: float = Field(..., description="处理时间(秒)")


class TaskCreationResponse(BaseModel):
    """任务创建响应模型"""
    task_id: int = Field(..., description="任务ID")
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务描述")
    reward: Optional[Decimal] = Field(None, description="奖励金额")
    tags: List[str] = Field(default=[], description="标签列表")
    created_at: datetime = Field(..., description="创建时间")
    needs_review: bool = Field(default=True, description="是否需要人工审核")