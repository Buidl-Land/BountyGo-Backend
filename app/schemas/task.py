"""
Task-related Pydantic schemas
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

from .tag import Tag
from .user import User
from .organizer import OrganizerSummary


class TaskStatus(str, Enum):
    """Task status options"""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskBase(BaseModel):
    """Base task schema"""
    title: str = Field(..., min_length=1, max_length=255)
    summary: Optional[str] = Field(None, max_length=500, description="任务简介")
    description: Optional[str] = None
    category: Optional[str] = Field(None, description="任务分类")
    deadline: Optional[int] = Field(None, description="截止日期时间戳")
    external_link: Optional[str] = Field(None, description="活动原始链接")


class TaskCreate(TaskBase):
    """Schema for creating a task"""
    tag_ids: List[int] = Field(default=[], max_items=20)


class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    summary: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    category: Optional[str] = None
    deadline: Optional[int] = Field(None, description="截止日期时间戳")
    external_link: Optional[str] = None
    status: Optional[TaskStatus] = None
    tag_ids: Optional[List[int]] = Field(None, max_items=20)
    organizer_name: Optional[str] = Field(None, description="主办方名称")


class Task(TaskBase):
    """Schema for task response"""
    id: int
    sponsor_id: int
    organizer_id: Optional[int] = None
    status: TaskStatus
    view_count: int
    join_count: int
    created_at: datetime
    updated_at: datetime
    tags: List[Tag] = []
    sponsor: Optional[User] = None
    organizer: Optional[OrganizerSummary] = None

    model_config = ConfigDict(from_attributes=True)


class TaskSummary(BaseModel):
    """Summary task schema for lists"""
    id: int
    title: str
    summary: Optional[str] = None
    category: Optional[str] = None
    deadline: Optional[int] = Field(None, description="截止日期时间戳")
    sponsor_id: int
    organizer_id: Optional[int] = None
    status: TaskStatus
    view_count: int
    join_count: int
    created_at: datetime
    tags: List[Tag] = []
    organizer: Optional[OrganizerSummary] = None

    model_config = ConfigDict(from_attributes=True)


class TaskFilters(BaseModel):
    """Task filtering options"""
    status: Optional[TaskStatus] = None
    sponsor_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None
    min_reward: Optional[Decimal] = None
    max_reward: Optional[Decimal] = None
    currency: Optional[str] = None
    has_deadline: Optional[bool] = None
    search: Optional[str] = None


class TaskList(BaseModel):
    """Task list response"""
    tasks: List[TaskSummary]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


class Pagination(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# Todo schemas
class TodoBase(BaseModel):
    """Base todo schema"""
    title: Optional[str] = Field(None, max_length=255, description="自定义todo标题")
    description: Optional[str] = Field(None, description="自定义todo描述")
    deadline: Optional[int] = Field(None, description="自定义截止时间戳")
    remind_flags: Optional[Dict[str, bool]] = Field(
        default={"t_3d": True, "t_1d": True, "ddl_2h": True}
    )
    is_active: bool = True


class TodoCreate(TodoBase):
    """Schema for creating a todo"""
    task_id: Optional[int] = Field(None, description="关联的任务ID，为空则为私人todo")


class TodoUpdate(BaseModel):
    """Schema for updating a todo"""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    deadline: Optional[int] = None
    remind_flags: Optional[Dict[str, bool]] = None
    is_active: Optional[bool] = None
    is_completed: Optional[bool] = None


class Todo(TodoBase):
    """Schema for todo response"""
    id: int
    user_id: int
    task_id: Optional[int] = None
    added_at: datetime
    is_completed: bool
    created_at: datetime
    updated_at: datetime
    task: Optional[TaskSummary] = None

    model_config = ConfigDict(from_attributes=True)


# Message schemas
class MessageBase(BaseModel):
    """Base message schema"""
    content: str = Field(..., min_length=1, max_length=10000)


class MessageCreate(MessageBase):
    """Schema for creating a message"""
    task_id: int


class MessageUpdate(BaseModel):
    """Schema for updating a message"""
    content: str = Field(..., min_length=1, max_length=10000)


class Message(MessageBase):
    """Schema for message response"""
    id: int
    task_id: int
    user_id: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    user: Optional[User] = None

    model_config = ConfigDict(from_attributes=True)


class MessageList(BaseModel):
    """Message list response"""
    messages: List[Message]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


# Analytics schemas
class TaskAnalytics(BaseModel):
    """Task analytics response"""
    task_id: int
    view_count: int
    join_count: int
    message_count: int
    unique_viewers: int
    daily_views: List[Dict[str, Any]]
    top_countries: List[Dict[str, Any]]
    engagement_rate: float


class SponsorDashboard(BaseModel):
    """Sponsor dashboard response"""
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    total_views: int
    total_joins: int
    total_messages: int
    recent_tasks: List[TaskSummary]
    top_performing_tasks: List[Dict[str, Any]]


class TaskView(BaseModel):
    """Task view tracking"""
    id: int
    task_id: int
    user_id: Optional[int] = None
    viewed_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ExportData(BaseModel):
    """Data export response"""
    format: str
    data: Dict[str, Any]
    generated_at: datetime
    total_records: int