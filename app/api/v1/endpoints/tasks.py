"""
任务管理API端点
"""
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.task import Task, TaskTag, Todo, Message, TaskView
from app.models.tag import Tag
from app.schemas.task import (
    Task as TaskSchema,
    TaskCreate,
    TaskUpdate,
    TaskSummary,
    TaskList,
    Todo as TodoSchema,
    TodoCreate,
    TodoUpdate,
    Message as MessageSchema,
    MessageCreate,
    MessageList
)
from app.schemas.organizer import OrganizerSummary
from app.schemas.base import SuccessResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=TaskList, summary="获取任务列表")
async def get_tasks(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="任务状态筛选"),
    sponsor_id: Optional[int] = Query(None, description="发布者ID筛选"),
    tag_ids: Optional[str] = Query(None, description="标签ID列表，逗号分隔"),
    category: Optional[str] = Query(None, description="任务分类筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    获取任务列表，支持分页和多种筛选条件

    - **page**: 页码，从1开始
    - **size**: 每页数量，最大100
    - **status**: 任务状态 (active, completed, cancelled, paused)
    - **sponsor_id**: 发布者用户ID
    - **tag_ids**: 标签ID列表，用逗号分隔，如 "1,2,3"
    - **category**: 任务分类 (黑客松, 征文, Meme创作, Web3交互, 推特抽奖, 开发实战)
    - **search**: 在标题和描述中搜索关键词
    """
    # 构建查询条件
    query = select(Task).options(
        selectinload(Task.sponsor),
        selectinload(Task.organizer),
        selectinload(Task.task_tags).selectinload(TaskTag.tag)
    )

    # 状态筛选
    if status:
        query = query.where(Task.status == status)

    # 发布者筛选
    if sponsor_id:
        query = query.where(Task.sponsor_id == sponsor_id)

    # 分类筛选
    if category:
        query = query.where(Task.category == category)

    # 关键词搜索
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term)
            )
        )

    # 标签筛选
    if tag_ids:
        try:
            tag_id_list = [int(tid.strip()) for tid in tag_ids.split(",")]
            query = query.join(TaskTag).where(TaskTag.tag_id.in_(tag_id_list))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="标签ID格式错误"
            )

    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    offset = (page - 1) * size
    query = query.offset(offset).limit(size).order_by(Task.created_at.desc())

    # 执行查询
    result = await db.execute(query)
    tasks = result.scalars().all()

    # 如果用户已登录，查询用户的todo状态
    user_todos = {}
    if current_user:
        task_ids = [task.id for task in tasks]
        if task_ids:
            todos_query = select(Todo).where(
                and_(
                    Todo.user_id == current_user.id,
                    Todo.task_id.in_(task_ids)
                )
            )
            todos_result = await db.execute(todos_query)
            todos = todos_result.scalars().all()

            for todo in todos:
                user_todos[todo.task_id] = {
                    "todo_id": todo.id,
                    "is_joined": True,
                    "is_completed": todo.is_completed,
                    "is_active": todo.is_active,
                    "added_at": todo.added_at.isoformat() if todo.added_at else None
                }

    # 转换为TaskSummary
    task_summaries = []
    for task in tasks:
        # 获取用户todo状态
        user_todo_status = None
        if current_user:
            if task.id in user_todos:
                user_todo_status = user_todos[task.id]
            else:
                user_todo_status = {
                    "todo_id": None,
                    "is_joined": False,
                    "is_completed": False,
                    "is_active": False,
                    "added_at": None
                }

        task_summary = TaskSummary(
            id=task.id,
            title=task.title,
            summary=task.summary,
            category=task.category,
            reward_details=task.reward_details,
            reward_type=task.reward_type,
            deadline=task.deadline,
            external_link=task.external_link,
            sponsor_id=task.sponsor_id,
            organizer_id=task.organizer_id,
            status=task.status,
            view_count=task.view_count,
            join_count=task.join_count,
            created_at=task.created_at,
            tags=[tt.tag for tt in task.task_tags],
            organizer=OrganizerSummary(
                id=task.organizer.id,
                name=task.organizer.name,
                is_verified=task.organizer.is_verified
            ) if task.organizer else None,
            user_todo_status=user_todo_status
        )
        task_summaries.append(task_summary)

    return TaskList(
        tasks=task_summaries,
        total=total,
        page=page,
        size=size,
        has_next=offset + size < total,
        has_prev=page > 1
    )


@router.post("/", response_model=TaskSchema, summary="创建新任务")
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新任务

    - **title**: 任务标题
    - **summary**: 任务简介
    - **description**: 任务描述
    - **category**: 任务分类
    - **reward_details**: 奖励详情
    - **reward_type**: 奖励分类 (每人、瓜分、抽奖、积分、权益)
    - **deadline**: 截止时间
    - **external_link**: 外部链接
    - **tag_ids**: 关联的标签ID列表
    - **organizer_name**: 主办方名称
    """
    # 创建任务
    task_dict = task_data.model_dump(exclude={"tag_ids"})
    new_task = Task(
        sponsor_id=current_user.id,
        **task_dict
    )

    db.add(new_task)
    await db.flush()  # 获取任务ID

    # 添加标签关联
    if task_data.tag_ids:
        for tag_id in task_data.tag_ids:
            # 验证标签存在
            tag_result = await db.execute(select(Tag).where(Tag.id == tag_id))
            if not tag_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"标签ID {tag_id} 不存在"
                )

            task_tag = TaskTag(task_id=new_task.id, tag_id=tag_id)
            db.add(task_tag)

    await db.commit()
    await db.refresh(new_task)

    # 重新加载完整信息
    result = await db.execute(
        select(Task)
        .options(
            selectinload(Task.sponsor),
            selectinload(Task.task_tags).selectinload(TaskTag.tag)
        )
        .where(Task.id == new_task.id)
    )
    task = result.scalar_one()

    return task


# ==================== My Todos Routes ====================
# 这些路由必须在 /{task_id} 路由之前定义，避免路由冲突

@router.get("/my-todos", response_model=List[TodoSchema], summary="获取我的任务列表")
async def get_my_todos(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    is_active: Optional[bool] = Query(None, description="筛选活跃状态"),
    task_status: Optional[str] = Query(None, description="筛选任务状态")
):
    """
    获取当前用户的任务待办列表

    - **is_active**: 筛选待办事项的活跃状态
    - **task_status**: 筛选任务状态 (active, completed, cancelled, paused)
    """
    # 构建基础查询
    query = select(Todo).where(Todo.user_id == current_user.id)

    # 筛选条件
    if is_active is not None:
        query = query.where(Todo.is_active == is_active)

    if task_status:
        query = query.join(Task).where(Task.status == task_status)

    # 按添加时间倒序排列
    query = query.order_by(Todo.added_at.desc())

    # 执行查询
    result = await db.execute(query)
    todos = result.scalars().all()

    # 如果有todos，重新查询以确保正确预加载关联数据
    if todos:
        todo_ids = [todo.id for todo in todos]
        # 重新查询并预加载所有关联数据
        preload_query = select(Todo).options(
            selectinload(Todo.task).selectinload(Task.sponsor),
            selectinload(Todo.task).selectinload(Task.organizer),
            selectinload(Todo.task).selectinload(Task.task_tags).selectinload(TaskTag.tag)
        ).where(Todo.id.in_(todo_ids)).order_by(Todo.added_at.desc())

        preload_result = await db.execute(preload_query)
        todos = preload_result.scalars().all()

    return todos


@router.put("/my-todos/{todo_id}", response_model=TodoSchema, summary="更新我的任务设置")
async def update_my_todo(
    todo_id: int,
    todo_update: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新个人待办事项的设置

    - **todo_id**: 待办事项ID
    - **remind_flags**: 提醒设置
    - **is_active**: 是否活跃
    """
    # 查询待办事项
    result = await db.execute(
        select(Todo)
        .where(Todo.id == todo_id)
        .where(Todo.user_id == current_user.id)
    )
    todo = result.scalar_one_or_none()

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="待办事项不存在或无权限访问"
        )

    # 更新待办事项
    update_data = todo_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "remind_flags" and value is not None:
            # 将字典转换为JSON字符串
            setattr(todo, field, json.dumps(value))
        else:
            setattr(todo, field, value)

    await db.commit()
    await db.refresh(todo)

    # 重新查询以预加载task关系，避免序列化时的异步会话问题
    result = await db.execute(
        select(Todo)
        .options(
            selectinload(Todo.task).selectinload(Task.sponsor),
            selectinload(Todo.task).selectinload(Task.organizer),
            selectinload(Todo.task).selectinload(Task.task_tags).selectinload(TaskTag.tag)
        )
        .where(Todo.id == todo.id)
    )
    todo_with_task = result.scalar_one()

    # TODO: 重新调度提醒
    # 这里可以调用提醒调度服务重新安排提醒

    return todo_with_task


@router.delete("/my-todos/{todo_id}", response_model=SuccessResponse, summary="移除我的任务")
async def remove_my_todo(
    todo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    从个人待办列表中移除任务

    - **todo_id**: 待办事项ID
    """
    # 查询待办事项
    result = await db.execute(
        select(Todo)
        .where(Todo.id == todo_id)
        .where(Todo.user_id == current_user.id)
    )
    todo = result.scalar_one_or_none()

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="待办事项不存在或无权限访问"
        )

    # 删除待办事项
    await db.delete(todo)

    # 更新任务的加入计数
    task_result = await db.execute(select(Task).where(Task.id == todo.task_id))
    task = task_result.scalar_one_or_none()
    if task and task.join_count > 0:
        task.join_count -= 1

    await db.commit()

    return SuccessResponse(message="已从待办列表中移除任务")


# ==================== Task Detail Routes ====================

@router.get("/{task_id}", response_model=TaskSchema, summary="获取任务详情")
async def get_task(
    task_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定任务的详细信息

    - **task_id**: 任务ID
    - **返回**: 任务完整信息，包括发布者和标签
    """
    # 查询任务
    result = await db.execute(
        select(Task)
        .options(
            selectinload(Task.sponsor),
            selectinload(Task.task_tags).selectinload(TaskTag.tag)
        )
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 记录浏览
    if current_user:
        task_view = TaskView(
            task_id=task_id,
            user_id=current_user.id
        )
        db.add(task_view)

        # 更新浏览计数
        task.view_count += 1
        await db.commit()

    return task


@router.put("/{task_id}", response_model=TaskSchema, summary="更新任务")
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新指定任务的信息（仅任务发布者可操作）

    - **task_id**: 任务ID
    - **返回**: 更新后的任务信息
    """
    # 查询任务
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 检查权限
    if task.sponsor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有任务发布者可以修改任务"
        )

    # 更新任务信息
    update_data = task_update.model_dump(exclude_unset=True, exclude={"tag_ids"})
    for field, value in update_data.items():
        setattr(task, field, value)

    # 更新标签关联
    if task_update.tag_ids is not None:
        # 删除现有标签关联
        await db.execute(
            select(TaskTag).where(TaskTag.task_id == task_id)
        )
        existing_tags = await db.execute(
            select(TaskTag).where(TaskTag.task_id == task_id)
        )
        for tag_relation in existing_tags.scalars():
            await db.delete(tag_relation)

        # 添加新的标签关联
        for tag_id in task_update.tag_ids:
            task_tag = TaskTag(task_id=task_id, tag_id=tag_id)
            db.add(task_tag)

    await db.commit()
    await db.refresh(task)

    # 重新加载完整信息
    result = await db.execute(
        select(Task)
        .options(
            selectinload(Task.sponsor),
            selectinload(Task.task_tags).selectinload(TaskTag.tag)
        )
        .where(Task.id == task_id)
    )
    updated_task = result.scalar_one()

    return updated_task


@router.delete("/{task_id}", response_model=SuccessResponse, summary="删除任务")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除指定任务（仅任务发布者可操作）

    - **task_id**: 任务ID
    """
    # 查询任务
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 检查权限
    if task.sponsor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有任务发布者可以删除任务"
        )

    await db.delete(task)
    await db.commit()

    return SuccessResponse(message="任务删除成功")


@router.post("/{task_id}/join", response_model=TodoSchema, summary="加入任务")
async def join_task(
    task_id: int,
    todo_data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    加入指定任务，添加到个人待办列表

    - **task_id**: 任务ID
    - **remind_flags**: 提醒设置
    """
    # 检查任务是否存在
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 检查是否已加入
    result = await db.execute(
        select(Todo)
        .where(Todo.user_id == current_user.id)
        .where(Todo.task_id == task_id)
    )
    existing_todo = result.scalar_one_or_none()

    if existing_todo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已经加入该任务"
        )

    # 创建待办事项
    todo_dict = todo_data.model_dump()

    # 设置task_id（覆盖可能存在的值）
    todo_dict["task_id"] = task_id

    # 将remind_flags转换为JSON字符串
    if todo_dict.get("remind_flags"):
        todo_dict["remind_flags"] = json.dumps(todo_dict["remind_flags"])

    new_todo = Todo(
        user_id=current_user.id,
        **todo_dict
    )

    db.add(new_todo)

    # 更新任务加入计数
    task.join_count += 1

    await db.commit()
    await db.refresh(new_todo)

    # 预加载task关系以避免序列化时的异步会话问题
    result = await db.execute(
        select(Todo)
        .options(
            selectinload(Todo.task).selectinload(Task.sponsor),
            selectinload(Todo.task).selectinload(Task.organizer),
            selectinload(Todo.task).selectinload(Task.task_tags).selectinload(TaskTag.tag)
        )
        .where(Todo.id == new_todo.id)
    )
    new_todo_with_task = result.scalar_one()

    # 调度任务提醒 - 暂时禁用以避免数据库问题
    # try:
    #     from app.services.notification import task_reminder_scheduler
    #     await task_reminder_scheduler.schedule_task_reminders(db, task_id)
    # except Exception as e:
    #     # 提醒调度失败不应该影响加入任务的操作
    #     logger.warning(f"Failed to schedule reminders for task {task_id}: {e}")

    return new_todo_with_task


@router.get("/{task_id}/messages", response_model=MessageList, summary="获取任务讨论")
async def get_task_messages(
    task_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定任务的讨论消息

    - **task_id**: 任务ID
    - **page**: 页码
    - **size**: 每页数量
    """
    # 检查任务是否存在
    result = await db.execute(select(Task).where(Task.id == task_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 计算总数
    count_result = await db.execute(
        select(func.count(Message.id))
        .where(Message.task_id == task_id)
        .where(Message.is_deleted == False)
    )
    total = count_result.scalar()

    # 查询消息
    offset = (page - 1) * size
    result = await db.execute(
        select(Message)
        .options(selectinload(Message.user))
        .where(Message.task_id == task_id)
        .where(Message.is_deleted == False)
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    messages = result.scalars().all()

    return MessageList(
        messages=messages,
        total=total,
        page=page,
        size=size,
        has_next=offset + size < total,
        has_prev=page > 1
    )


@router.post("/{task_id}/messages", response_model=MessageSchema, summary="发送讨论消息")
async def create_task_message(
    task_id: int,
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    在指定任务下发送讨论消息

    - **task_id**: 任务ID
    - **content**: 消息内容
    """
    # 检查任务是否存在
    result = await db.execute(select(Task).where(Task.id == task_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 创建消息
    new_message = Message(
        task_id=task_id,
        user_id=current_user.id,
        content=message_data.content
    )

    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)

    # 重新加载完整信息
    result = await db.execute(
        select(Message)
        .options(selectinload(Message.user))
        .where(Message.id == new_message.id)
    )
    message = result.scalar_one()

    return message


@router.put("/{task_id}/complete", response_model=SuccessResponse, summary="完成任务确认")
async def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    标记任务为已完成（仅任务发布者可操作）

    - **task_id**: 任务ID
    """
    # 查询任务
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 检查权限
    if task.sponsor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有任务发布者可以标记任务完成"
        )

    # 更新任务状态
    task.status = "completed"
    await db.commit()

    # TODO: 发送任务完成通知给所有参与者
    # 这里可以调用通知服务发送完成通知

    return SuccessResponse(message="任务已标记为完成")








