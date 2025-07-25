"""
分析统计API端点
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.task import Task, TaskView, Message, Todo
from app.models.tag import Tag, UserTagProfile
from app.schemas.task import SponsorDashboard, TaskAnalytics
from app.schemas.base import BaseSchema

router = APIRouter()


class SystemStats(BaseSchema):
    """系统统计数据"""
    total_users: int
    total_tasks: int
    total_tags: int
    active_tasks: int
    completed_tasks: int
    total_messages: int
    total_views: int


class UserStats(BaseSchema):
    """用户统计数据"""
    joined_tasks: int
    created_tasks: int
    messages_sent: int
    profile_completion: float


class PopularTag(BaseSchema):
    """热门标签"""
    tag_name: str
    task_count: int
    user_count: int


class RecentActivity(BaseSchema):
    """最近活动"""
    type: str  # task_created, task_joined, message_sent
    title: str
    user_name: str
    created_at: datetime


@router.get("/system", response_model=SystemStats, summary="获取系统统计")
async def get_system_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    获取系统整体统计数据
    
    - **返回**: 系统各项统计指标
    """
    # 用户总数
    users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    total_users = users_result.scalar()
    
    # 任务总数
    tasks_result = await db.execute(select(func.count(Task.id)))
    total_tasks = tasks_result.scalar()
    
    # 标签总数
    tags_result = await db.execute(
        select(func.count(Tag.id)).where(Tag.is_active == True)
    )
    total_tags = tags_result.scalar()
    
    # 活跃任务数
    active_tasks_result = await db.execute(
        select(func.count(Task.id)).where(Task.status == "active")
    )
    active_tasks = active_tasks_result.scalar()
    
    # 已完成任务数
    completed_tasks_result = await db.execute(
        select(func.count(Task.id)).where(Task.status == "completed")
    )
    completed_tasks = completed_tasks_result.scalar()
    
    # 消息总数
    messages_result = await db.execute(
        select(func.count(Message.id)).where(Message.is_deleted == False)
    )
    total_messages = messages_result.scalar()
    
    # 浏览总数
    views_result = await db.execute(select(func.count(TaskView.id)))
    total_views = views_result.scalar()
    
    return SystemStats(
        total_users=total_users,
        total_tasks=total_tasks,
        total_tags=total_tags,
        active_tasks=active_tasks,
        completed_tasks=completed_tasks,
        total_messages=total_messages,
        total_views=total_views
    )


@router.get("/me", response_model=UserStats, summary="获取我的统计")
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的个人统计数据
    
    - **返回**: 用户个人统计指标
    """
    # 加入的任务数
    joined_result = await db.execute(
        select(func.count(Todo.id))
        .where(Todo.user_id == current_user.id)
        .where(Todo.is_active == True)
    )
    joined_tasks = joined_result.scalar()
    
    # 创建的任务数
    created_result = await db.execute(
        select(func.count(Task.id)).where(Task.sponsor_id == current_user.id)
    )
    created_tasks = created_result.scalar()
    
    # 发送的消息数
    messages_result = await db.execute(
        select(func.count(Message.id))
        .where(Message.user_id == current_user.id)
        .where(Message.is_deleted == False)
    )
    messages_sent = messages_result.scalar()
    
    # 计算资料完整度
    profile_completion = 0.0
    if current_user.nickname:
        profile_completion += 25.0
    if current_user.avatar_url:
        profile_completion += 25.0
    if current_user.google_id:
        profile_completion += 25.0
    
    # 检查是否有标签配置
    tags_result = await db.execute(
        select(func.count(UserTagProfile.id))
        .where(UserTagProfile.user_id == current_user.id)
    )
    if tags_result.scalar() > 0:
        profile_completion += 25.0
    
    return UserStats(
        joined_tasks=joined_tasks,
        created_tasks=created_tasks,
        messages_sent=messages_sent,
        profile_completion=profile_completion
    )


@router.get("/popular-tags", response_model=List[PopularTag], summary="获取热门标签")
async def get_popular_tags(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取最热门的标签列表
    
    - **limit**: 返回数量限制
    - **返回**: 热门标签列表，按使用频率排序
    """
    from app.models.task import TaskTag
    
    # 查询标签使用统计
    result = await db.execute(
        select(
            Tag.name,
            func.count(TaskTag.id).label('task_count'),
            func.count(UserTagProfile.id).label('user_count')
        )
        .select_from(Tag)
        .outerjoin(TaskTag, Tag.id == TaskTag.tag_id)
        .outerjoin(UserTagProfile, Tag.id == UserTagProfile.tag_id)
        .where(Tag.is_active == True)
        .group_by(Tag.id, Tag.name)
        .order_by(desc('task_count'), desc('user_count'))
        .limit(limit)
    )
    
    popular_tags = []
    for name, task_count, user_count in result.all():
        popular_tags.append(PopularTag(
            tag_name=name,
            task_count=task_count or 0,
            user_count=user_count or 0
        ))
    
    return popular_tags


@router.get("/recent-activity", response_model=List[RecentActivity], summary="获取最近活动")
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取系统最近活动列表
    
    - **limit**: 返回数量限制
    - **返回**: 最近活动列表
    """
    activities = []
    
    # 最近创建的任务
    tasks_result = await db.execute(
        select(Task.title, User.nickname, Task.created_at)
        .join(User, Task.sponsor_id == User.id)
        .order_by(Task.created_at.desc())
        .limit(limit // 2)
    )
    
    for title, user_name, created_at in tasks_result.all():
        activities.append(RecentActivity(
            type="task_created",
            title=f"创建了任务: {title}",
            user_name=user_name,
            created_at=created_at
        ))
    
    # 最近的消息
    messages_result = await db.execute(
        select(Task.title, User.nickname, Message.created_at)
        .select_from(Message)
        .join(Task, Message.task_id == Task.id)
        .join(User, Message.user_id == User.id)
        .where(Message.is_deleted == False)
        .order_by(Message.created_at.desc())
        .limit(limit // 2)
    )
    
    for title, user_name, created_at in messages_result.all():
        activities.append(RecentActivity(
            type="message_sent",
            title=f"在任务 '{title}' 中发送了消息",
            user_name=user_name,
            created_at=created_at
        ))
    
    # 按时间排序
    activities.sort(key=lambda x: x.created_at, reverse=True)
    
    return activities[:limit]


@router.get("/sponsor-dashboard", response_model=SponsorDashboard, summary="获取发布者仪表板")
async def get_sponsor_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户作为任务发布者的仪表板数据
    
    - **返回**: 发布者统计数据和任务列表
    """
    # 任务统计
    total_tasks_result = await db.execute(
        select(func.count(Task.id)).where(Task.sponsor_id == current_user.id)
    )
    total_tasks = total_tasks_result.scalar()
    
    active_tasks_result = await db.execute(
        select(func.count(Task.id))
        .where(Task.sponsor_id == current_user.id)
        .where(Task.status == "active")
    )
    active_tasks = active_tasks_result.scalar()
    
    completed_tasks_result = await db.execute(
        select(func.count(Task.id))
        .where(Task.sponsor_id == current_user.id)
        .where(Task.status == "completed")
    )
    completed_tasks = completed_tasks_result.scalar()
    
    # 浏览和参与统计
    views_result = await db.execute(
        select(func.sum(Task.view_count))
        .where(Task.sponsor_id == current_user.id)
    )
    total_views = views_result.scalar() or 0
    
    joins_result = await db.execute(
        select(func.sum(Task.join_count))
        .where(Task.sponsor_id == current_user.id)
    )
    total_joins = joins_result.scalar() or 0
    
    # 消息统计
    messages_result = await db.execute(
        select(func.count(Message.id))
        .select_from(Message)
        .join(Task, Message.task_id == Task.id)
        .where(Task.sponsor_id == current_user.id)
        .where(Message.is_deleted == False)
    )
    total_messages = messages_result.scalar()
    
    # 最近任务
    from sqlalchemy.orm import selectinload
    recent_tasks_result = await db.execute(
        select(Task)
        .options(selectinload(Task.task_tags).selectinload(TaskTag.tag))
        .where(Task.sponsor_id == current_user.id)
        .order_by(Task.created_at.desc())
        .limit(5)
    )
    recent_tasks = recent_tasks_result.scalars().all()
    
    # 转换为TaskSummary
    from app.schemas.task import TaskSummary
    from app.models.task import TaskTag
    recent_task_summaries = []
    for task in recent_tasks:
        task_summary = TaskSummary(
            id=task.id,
            title=task.title,
            reward=task.reward,
            reward_currency=task.reward_currency,
            deadline=task.deadline,
            sponsor_id=task.sponsor_id,
            status=task.status,
            view_count=task.view_count,
            join_count=task.join_count,
            created_at=task.created_at,
            tags=[tt.tag for tt in task.task_tags]
        )
        recent_task_summaries.append(task_summary)
    
    # 表现最好的任务
    top_tasks_result = await db.execute(
        select(Task.title, Task.view_count, Task.join_count)
        .where(Task.sponsor_id == current_user.id)
        .order_by((Task.view_count + Task.join_count * 2).desc())
        .limit(5)
    )
    
    top_performing_tasks = []
    for title, views, joins in top_tasks_result.all():
        top_performing_tasks.append({
            "title": title,
            "views": views,
            "joins": joins,
            "engagement_score": views + joins * 2
        })
    
    return SponsorDashboard(
        total_tasks=total_tasks,
        active_tasks=active_tasks,
        completed_tasks=completed_tasks,
        total_views=total_views,
        total_joins=total_joins,
        total_messages=total_messages,
        recent_tasks=recent_task_summaries,
        top_performing_tasks=top_performing_tasks
    )


@router.get("/task/{task_id}", response_model=TaskAnalytics, summary="获取任务分析")
async def get_task_analytics(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定任务的详细分析数据
    
    - **task_id**: 任务ID
    - **返回**: 任务分析数据
    """
    # 检查任务是否存在且用户有权限查看
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    if task.sponsor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有任务发布者可以查看分析数据"
        )
    
    # 消息数量
    messages_result = await db.execute(
        select(func.count(Message.id))
        .where(Message.task_id == task_id)
        .where(Message.is_deleted == False)
    )
    message_count = messages_result.scalar()
    
    # 独立浏览者数量
    unique_viewers_result = await db.execute(
        select(func.count(func.distinct(TaskView.user_id)))
        .where(TaskView.task_id == task_id)
        .where(TaskView.user_id.isnot(None))
    )
    unique_viewers = unique_viewers_result.scalar()
    
    # 每日浏览数据（最近7天）
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_views_result = await db.execute(
        select(
            func.date(TaskView.viewed_at).label('date'),
            func.count(TaskView.id).label('views')
        )
        .where(TaskView.task_id == task_id)
        .where(TaskView.viewed_at >= seven_days_ago)
        .group_by(func.date(TaskView.viewed_at))
        .order_by('date')
    )
    
    daily_views = []
    for date, views in daily_views_result.all():
        daily_views.append({
            "date": date.isoformat(),
            "views": views
        })
    
    # 地区分布（模拟数据，实际需要根据IP解析）
    top_countries = [
        {"country": "中国", "views": task.view_count * 0.6},
        {"country": "美国", "views": task.view_count * 0.2},
        {"country": "日本", "views": task.view_count * 0.1},
        {"country": "其他", "views": task.view_count * 0.1}
    ]
    
    # 计算参与率
    engagement_rate = 0.0
    if task.view_count > 0:
        engagement_rate = (task.join_count / task.view_count) * 100
    
    return TaskAnalytics(
        task_id=task_id,
        view_count=task.view_count,
        join_count=task.join_count,
        message_count=message_count,
        unique_viewers=unique_viewers,
        daily_views=daily_views,
        top_countries=top_countries,
        engagement_rate=engagement_rate
    )