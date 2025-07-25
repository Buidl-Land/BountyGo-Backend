"""
标签管理API端点
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.tag import Tag, UserTagProfile
from app.schemas.tag import (
    Tag as TagSchema,
    TagCreate,
    TagUpdate,
    TagCategory,
    UserTagProfile as UserTagProfileSchema,
    UserTagProfileCreate,
    UserTagProfileUpdate,
    TagSearchResponse,
    TagAnalytics,
    BulkTagCreate,
    BulkTagResponse
)
from app.schemas.base import SuccessResponse

router = APIRouter()


@router.get("/", response_model=List[TagSchema], summary="获取标签列表")
async def get_tags(
    category: Optional[TagCategory] = Query(None, description="标签分类筛选"),
    is_active: bool = Query(True, description="是否只显示激活的标签"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取系统标签列表
    
    - **category**: 标签分类 (industry, skill, media)
    - **is_active**: 是否只显示激活的标签
    - **limit**: 返回数量限制，最大500
    """
    query = select(Tag)
    
    # 分类筛选
    if category:
        query = query.where(Tag.category == category.value)
    
    # 激活状态筛选
    if is_active:
        query = query.where(Tag.is_active == True)
    
    # 按使用次数排序
    query = query.order_by(Tag.usage_count.desc(), Tag.name).limit(limit)
    
    result = await db.execute(query)
    tags = result.scalars().all()
    
    return tags


@router.post("/", response_model=TagSchema, summary="创建新标签")
async def create_tag(
    tag_data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新的系统标签
    
    - **name**: 标签名称
    - **category**: 标签分类 (industry, skill, media)
    - **description**: 标签描述
    """
    # 检查标签名是否已存在
    result = await db.execute(
        select(Tag).where(Tag.name == tag_data.name)
    )
    existing_tag = result.scalar_one_or_none()
    
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="标签名称已存在"
        )
    
    # 创建新标签
    new_tag = Tag(**tag_data.model_dump())
    db.add(new_tag)
    await db.commit()
    await db.refresh(new_tag)
    
    return new_tag


# 将这个路由移到文件末尾，在所有具体路径之后


@router.put("/{tag_id}", response_model=TagSchema, summary="更新标签")
async def update_tag(
    tag_id: int,
    tag_update: TagUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新指定标签的信息
    
    - **tag_id**: 标签ID
    - **name**: 标签名称
    - **category**: 标签分类
    - **description**: 标签描述
    - **is_active**: 是否激活
    """
    # 查询标签
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签不存在"
        )
    
    # 如果更新名称，检查是否重复
    if tag_update.name and tag_update.name != tag.name:
        result = await db.execute(
            select(Tag).where(Tag.name == tag_update.name)
        )
        existing_tag = result.scalar_one_or_none()
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="标签名称已存在"
            )
    
    # 更新标签信息
    for field, value in tag_update.model_dump(exclude_unset=True).items():
        setattr(tag, field, value)
    
    await db.commit()
    await db.refresh(tag)
    
    return tag


@router.delete("/{tag_id}", response_model=SuccessResponse, summary="删除标签")
async def delete_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除指定标签
    
    - **tag_id**: 标签ID
    """
    # 查询标签
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签不存在"
        )
    
    # 检查是否有关联数据
    from app.models.task import TaskTag
    result = await db.execute(
        select(func.count(TaskTag.id)).where(TaskTag.tag_id == tag_id)
    )
    task_count = result.scalar()
    
    result = await db.execute(
        select(func.count(UserTagProfile.id)).where(UserTagProfile.tag_id == tag_id)
    )
    profile_count = result.scalar()
    
    if task_count > 0 or profile_count > 0:
        # 不直接删除，而是设为不激活
        tag.is_active = False
        await db.commit()
        return SuccessResponse(message="标签已设为不激活状态")
    else:
        # 可以安全删除
        await db.delete(tag)
        await db.commit()
        return SuccessResponse(message="标签删除成功")


@router.get("/search", response_model=TagSearchResponse, summary="搜索标签")
async def search_tags(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    category: Optional[TagCategory] = Query(None, description="标签分类筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    db: AsyncSession = Depends(get_db)
):
    """
    根据关键词搜索标签
    
    - **q**: 搜索关键词
    - **category**: 标签分类筛选
    - **limit**: 返回数量限制
    """
    query = select(Tag).where(Tag.is_active == True)
    
    # 关键词搜索
    search_term = f"%{q}%"
    query = query.where(
        or_(
            Tag.name.ilike(search_term),
            Tag.description.ilike(search_term)
        )
    )
    
    # 分类筛选
    if category:
        query = query.where(Tag.category == category.value)
    
    # 按相关性排序（使用次数和名称匹配度）
    query = query.order_by(Tag.usage_count.desc(), Tag.name).limit(limit)
    
    result = await db.execute(query)
    tags = result.scalars().all()
    
    # 计算总数
    count_query = select(func.count(Tag.id)).where(Tag.is_active == True)
    count_query = count_query.where(
        or_(
            Tag.name.ilike(search_term),
            Tag.description.ilike(search_term)
        )
    )
    if category:
        count_query = count_query.where(Tag.category == category.value)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    return TagSearchResponse(
        tags=tags,
        total=total,
        query=q,
        category=category
    )


@router.get("/categories", response_model=List[str], summary="获取标签分类列表")
async def get_tag_categories():
    """
    获取所有可用的标签分类
    
    - **返回**: 标签分类列表
    """
    return [category.value for category in TagCategory]


@router.get("/analytics", response_model=TagAnalytics, summary="获取标签统计")
async def get_tag_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取标签使用统计信息
    
    - **返回**: 标签统计数据
    """
    # 总标签数
    total_result = await db.execute(
        select(func.count(Tag.id)).where(Tag.is_active == True)
    )
    total_tags = total_result.scalar()
    
    # 按分类统计
    category_result = await db.execute(
        select(Tag.category, func.count(Tag.id))
        .where(Tag.is_active == True)
        .group_by(Tag.category)
    )
    tags_by_category = {category: count for category, count in category_result.all()}
    
    # 最常用标签
    most_used_result = await db.execute(
        select(Tag.name, Tag.usage_count)
        .where(Tag.is_active == True)
        .order_by(Tag.usage_count.desc())
        .limit(10)
    )
    most_used_tags = [
        {"name": name, "usage_count": count}
        for name, count in most_used_result.all()
    ]
    
    # 最新标签
    recent_result = await db.execute(
        select(Tag)
        .where(Tag.is_active == True)
        .order_by(Tag.created_at.desc())
        .limit(5)
    )
    recent_tags = recent_result.scalars().all()
    
    return TagAnalytics(
        total_tags=total_tags,
        tags_by_category=tags_by_category,
        most_used_tags=most_used_tags,
        recent_tags=recent_tags
    )


@router.post("/bulk", response_model=BulkTagResponse, summary="批量创建标签")
async def bulk_create_tags(
    bulk_data: BulkTagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    批量创建标签
    
    - **tags**: 标签列表，最多100个
    """
    created_tags = []
    skipped_tags = []
    errors = []
    
    for tag_data in bulk_data.tags:
        try:
            # 检查是否已存在
            result = await db.execute(
                select(Tag).where(Tag.name == tag_data.name)
            )
            existing_tag = result.scalar_one_or_none()
            
            if existing_tag:
                skipped_tags.append(tag_data.name)
                continue
            
            # 创建新标签
            new_tag = Tag(**tag_data.model_dump())
            db.add(new_tag)
            await db.flush()  # 获取ID但不提交
            created_tags.append(new_tag)
            
        except Exception as e:
            errors.append(f"创建标签 '{tag_data.name}' 失败: {str(e)}")
    
    if created_tags:
        await db.commit()
        # 刷新所有创建的标签
        for tag in created_tags:
            await db.refresh(tag)
    
    return BulkTagResponse(
        created=created_tags,
        skipped=skipped_tags,
        errors=errors
    )


# 用户标签配置相关端点
@router.get("/me/profile", response_model=List[UserTagProfileSchema], summary="获取我的标签配置")
async def get_my_tag_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的标签兴趣配置
    
    - **返回**: 用户标签配置列表，包含权重信息
    """
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(UserTagProfile)
        .options(selectinload(UserTagProfile.tag))
        .where(UserTagProfile.user_id == current_user.id)
        .order_by(UserTagProfile.weight.desc())
    )
    profiles = result.scalars().all()
    
    return profiles


@router.post("/me/profile", response_model=UserTagProfileSchema, summary="添加标签兴趣")
async def add_tag_to_profile(
    profile_data: UserTagProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    为当前用户添加标签兴趣配置
    
    - **tag_id**: 标签ID
    - **weight**: 兴趣权重 (0.0-10.0)
    """
    # 检查标签是否存在
    result = await db.execute(select(Tag).where(Tag.id == profile_data.tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签不存在"
        )
    
    # 检查是否已存在配置
    result = await db.execute(
        select(UserTagProfile)
        .where(UserTagProfile.user_id == current_user.id)
        .where(UserTagProfile.tag_id == profile_data.tag_id)
    )
    existing_profile = result.scalar_one_or_none()
    
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该标签已在兴趣配置中"
        )
    
    # 创建新配置
    new_profile = UserTagProfile(
        user_id=current_user.id,
        tag_id=profile_data.tag_id,
        weight=profile_data.weight
    )
    
    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)
    
    # 重新加载完整信息
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(UserTagProfile)
        .options(selectinload(UserTagProfile.tag))
        .where(UserTagProfile.id == new_profile.id)
    )
    profile = result.scalar_one()
    
    return profile


@router.put("/me/profile/{tag_id}", response_model=UserTagProfileSchema, summary="更新标签兴趣权重")
async def update_tag_profile(
    tag_id: int,
    profile_update: UserTagProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新指定标签的兴趣权重
    
    - **tag_id**: 标签ID
    - **weight**: 新的兴趣权重
    """
    # 查询配置
    result = await db.execute(
        select(UserTagProfile)
        .where(UserTagProfile.user_id == current_user.id)
        .where(UserTagProfile.tag_id == tag_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签配置不存在"
        )
    
    # 更新权重
    if profile_update.weight is not None:
        profile.weight = profile_update.weight
    
    await db.commit()
    await db.refresh(profile)
    
    # 重新加载完整信息
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(UserTagProfile)
        .options(selectinload(UserTagProfile.tag))
        .where(UserTagProfile.id == profile.id)
    )
    updated_profile = result.scalar_one()
    
    return updated_profile


@router.delete("/me/profile/{tag_id}", response_model=SuccessResponse, summary="删除标签兴趣")
async def remove_tag_from_profile(
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    从当前用户的兴趣配置中删除指定标签
    
    - **tag_id**: 标签ID
    """
    # 查询配置
    result = await db.execute(
        select(UserTagProfile)
        .where(UserTagProfile.user_id == current_user.id)
        .where(UserTagProfile.tag_id == tag_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签配置不存在"
        )
    
    await db.delete(profile)
    await db.commit()
    
    return SuccessResponse(message="标签兴趣删除成功")


# 参数化路由放在最后，避免与具体路径冲突
@router.get("/{tag_id}", response_model=TagSchema, summary="获取标签详情")
async def get_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定标签的详细信息
    
    - **tag_id**: 标签ID
    """
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标签不存在"
        )
    
    return tag