"""
用户管理API端点
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User, UserWallet
from app.schemas.user import (
    User as UserSchema,
    UserUpdate,
    UserWallet as UserWalletSchema,
    UserWalletCreate
)
from app.schemas.base import SuccessResponse

router = APIRouter()


@router.get("/me", response_model=UserSchema, summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前登录用户的详细信息
    
    - **返回**: 用户完整信息，包括钱包地址
    """
    # 加载用户的钱包信息
    result = await db.execute(
        select(User)
        .options(selectinload(User.wallets))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user


@router.put("/me", response_model=UserSchema, summary="更新用户信息")
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新当前登录用户的信息
    
    - **nickname**: 用户昵称
    - **avatar_url**: 头像URL
    """
    # 更新用户信息
    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.get("/me/wallets", response_model=List[UserWalletSchema], summary="获取用户钱包列表")
async def get_user_wallets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的所有钱包地址
    
    - **返回**: 钱包地址列表
    """
    result = await db.execute(
        select(UserWallet)
        .where(UserWallet.user_id == current_user.id)
        .order_by(UserWallet.is_primary.desc(), UserWallet.created_at.desc())
    )
    wallets = result.scalars().all()
    
    return wallets


@router.post("/me/wallets", response_model=UserWalletSchema, summary="添加钱包地址")
async def add_user_wallet(
    wallet_data: UserWalletCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    为当前用户添加新的钱包地址
    
    - **wallet_address**: 钱包地址 (42字符)
    - **wallet_type**: 钱包类型 (默认: ethereum)
    - **is_primary**: 是否设为主钱包
    """
    # 检查钱包地址是否已存在
    result = await db.execute(
        select(UserWallet)
        .where(UserWallet.wallet_address == wallet_data.wallet_address)
    )
    existing_wallet = result.scalar_one_or_none()
    
    if existing_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="钱包地址已存在"
        )
    
    # 如果设为主钱包，先取消其他主钱包
    if wallet_data.is_primary:
        await db.execute(
            select(UserWallet)
            .where(UserWallet.user_id == current_user.id)
            .where(UserWallet.is_primary == True)
        )
        # 更新现有主钱包
        result = await db.execute(
            select(UserWallet)
            .where(UserWallet.user_id == current_user.id)
            .where(UserWallet.is_primary == True)
        )
        existing_primary = result.scalars().all()
        for wallet in existing_primary:
            wallet.is_primary = False
    
    # 创建新钱包
    new_wallet = UserWallet(
        user_id=current_user.id,
        **wallet_data.model_dump()
    )
    
    db.add(new_wallet)
    await db.commit()
    await db.refresh(new_wallet)
    
    return new_wallet


@router.delete("/me/wallets/{wallet_id}", response_model=SuccessResponse, summary="删除钱包地址")
async def delete_user_wallet(
    wallet_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除指定的钱包地址
    
    - **wallet_id**: 钱包ID
    """
    # 查找钱包
    result = await db.execute(
        select(UserWallet)
        .where(UserWallet.id == wallet_id)
        .where(UserWallet.user_id == current_user.id)
    )
    wallet = result.scalar_one_or_none()
    
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="钱包不存在"
        )
    
    await db.delete(wallet)
    await db.commit()
    
    return SuccessResponse(message="钱包地址删除成功")


@router.get("/profile", response_model=UserSchema, summary="获取用户公开资料")
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定用户的公开资料信息
    
    - **user_id**: 用户ID
    - **返回**: 用户公开信息（不包含敏感数据）
    """
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .where(User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user