"""
Todo管理API端点
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.task import Todo, Task
from app.schemas.task import (
    Todo as TodoSchema,
    TodoCreate,
    TodoUpdate
)
from app.schemas.base import SuccessResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[TodoSchema], summary="获取用户的Todo列表")
async def get_todos(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    is_completed: Optional[bool] = Query(None, description="筛选完成状态"),
    is_active: Optional[bool] = Query(True, description="筛选激活状态"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的Todo列表，包括任务相关的todo和私人todo
    """
    # 构建查询
    query = select(Todo).options(
        selectinload(Todo.task)
    ).where(Todo.user_id == current_user.id)

    # 筛选条件
    if is_completed is not None:
        query = query.where(Todo.is_completed == is_completed)

    if is_active is not None:
        query = query.where(Todo.is_active == is_active)

    # 排序：未完成的在前，按创建时间倒序
    query = query.order_by(Todo.is_completed.asc(), Todo.created_at.desc())

    # 分页
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    # 执行查询
    result = await db.execute(query)
    todos = result.scalars().all()

    return todos


@router.post("/", response_model=TodoSchema, summary="创建Todo")
async def create_todo(
    todo_data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新的Todo项目

    - 如果提供task_id，则创建任务相关的todo
    - 如果不提供task_id，则创建私人todo（需要提供title）
    """
    # 验证数据
    if todo_data.task_id is None and not todo_data.title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="私人todo必须提供标题"
        )

    # 如果是任务相关的todo，验证任务是否存在
    if todo_data.task_id:
        result = await db.execute(
            select(Task).where(Task.id == todo_data.task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="任务不存在"
            )

    # 创建todo
    todo_dict = todo_data.model_dump()

    # 将remind_flags转换为JSON字符串
    if todo_dict.get("remind_flags"):
        import json
        todo_dict["remind_flags"] = json.dumps(todo_dict["remind_flags"])

    new_todo = Todo(
        user_id=current_user.id,
        **todo_dict
    )

    db.add(new_todo)
    await db.commit()
    await db.refresh(new_todo)

    # 重新查询以获取关联数据
    result = await db.execute(
        select(Todo).options(
            selectinload(Todo.task)
        ).where(Todo.id == new_todo.id)
    )
    todo_with_task = result.scalar_one()

    return todo_with_task


@router.put("/{todo_id}", response_model=TodoSchema, summary="更新Todo")
async def update_todo(
    todo_id: int,
    todo_data: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新Todo项目
    """
    # 查询todo
    result = await db.execute(
        select(Todo).options(
            selectinload(Todo.task)
        ).where(
            and_(
                Todo.id == todo_id,
                Todo.user_id == current_user.id
            )
        )
    )
    todo = result.scalar_one_or_none()

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo不存在或无权限访问"
        )

    # 更新字段
    update_data = todo_data.model_dump(exclude_unset=True)

    # 将remind_flags转换为JSON字符串
    if "remind_flags" in update_data and update_data["remind_flags"] is not None:
        import json
        update_data["remind_flags"] = json.dumps(update_data["remind_flags"])

    for field, value in update_data.items():
        setattr(todo, field, value)

    await db.commit()
    await db.refresh(todo)

    return todo


@router.delete("/{todo_id}", response_model=SuccessResponse, summary="删除Todo")
async def delete_todo(
    todo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除Todo项目
    """
    # 查询todo
    result = await db.execute(
        select(Todo).where(
            and_(
                Todo.id == todo_id,
                Todo.user_id == current_user.id
            )
        )
    )
    todo = result.scalar_one_or_none()

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo不存在或无权限访问"
        )

    await db.delete(todo)
    await db.commit()

    return SuccessResponse(message="Todo删除成功")


@router.patch("/{todo_id}/complete", response_model=TodoSchema, summary="标记Todo为完成")
async def complete_todo(
    todo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    标记Todo为完成状态
    """
    # 查询todo
    result = await db.execute(
        select(Todo).options(
            selectinload(Todo.task)
        ).where(
            and_(
                Todo.id == todo_id,
                Todo.user_id == current_user.id
            )
        )
    )
    todo = result.scalar_one_or_none()

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo不存在或无权限访问"
        )

    todo.is_completed = True
    await db.commit()
    await db.refresh(todo)

    return todo


@router.patch("/{todo_id}/uncomplete", response_model=TodoSchema, summary="标记Todo为未完成")
async def uncomplete_todo(
    todo_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    标记Todo为未完成状态
    """
    # 查询todo
    result = await db.execute(
        select(Todo).options(
            selectinload(Todo.task)
        ).where(
            and_(
                Todo.id == todo_id,
                Todo.user_id == current_user.id
            )
        )
    )
    todo = result.scalar_one_or_none()

    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo不存在或无权限访问"
        )

    todo.is_completed = False
    await db.commit()
    await db.refresh(todo)

    return todo
