"""
主办方管理API端点
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.task import Organizer
from app.schemas.organizer import (
    Organizer as OrganizerSchema,
    OrganizerCreate,
    OrganizerUpdate,
    OrganizerSummary
)
from app.schemas.base import SuccessResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[OrganizerSummary], summary="获取主办方列表")
async def get_organizers(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    verified_only: bool = Query(False, description="仅显示已验证的主办方"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取主办方列表，支持分页和搜索
    """
    # 构建查询
    query = select(Organizer)
    
    # 搜索条件
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Organizer.name.ilike(search_pattern),
                Organizer.description.ilike(search_pattern)
            )
        )
    
    # 验证状态筛选
    if verified_only:
        query = query.where(Organizer.is_verified == True)
    
    # 排序
    query = query.order_by(Organizer.is_verified.desc(), Organizer.name.asc())
    
    # 分页
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)
    
    # 执行查询
    result = await db.execute(query)
    organizers = result.scalars().all()
    
    return organizers


@router.get("/{organizer_id}", response_model=OrganizerSchema, summary="获取主办方详情")
async def get_organizer(
    organizer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定主办方的详细信息
    """
    result = await db.execute(
        select(Organizer).where(Organizer.id == organizer_id)
    )
    organizer = result.scalar_one_or_none()
    
    if not organizer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="主办方不存在"
        )
    
    return organizer


@router.get("/search/{name}", response_model=Optional[OrganizerSummary], summary="根据名称搜索主办方")
async def search_organizer_by_name(
    name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    根据名称精确搜索主办方（用于Agent创建任务时查找已存在的主办方）
    """
    result = await db.execute(
        select(Organizer).where(Organizer.name == name)
    )
    organizer = result.scalar_one_or_none()
    
    return organizer
