"""
User management service
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.models.user import User, UserWallet
from app.schemas.user import UserCreate, UserUpdate, GoogleUserInfo, UserWalletCreate
from app.services.base import BaseService
from app.core.exceptions import NotFoundError, ValidationError


class UserService(BaseService[User, UserCreate, UserUpdate]):
    """User management service"""
    
    def __init__(self):
        super().__init__(User)
    
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email"""
        stmt = select(User).where(
            User.email == email,
            User.is_active == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_google_id(self, db: AsyncSession, google_id: str) -> Optional[User]:
        """Get user by Google ID"""
        stmt = select(User).where(
            User.google_id == google_id,
            User.is_active == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_with_wallets(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user with wallet relationships"""
        stmt = select(User).options(
            selectinload(User.wallets)
        ).where(
            User.id == user_id,
            User.is_active == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_from_google(
        self, 
        db: AsyncSession, 
        google_user_info: GoogleUserInfo
    ) -> User:
        """Create user from Google OAuth information"""
        user_data = UserCreate(
            google_id=google_user_info.google_id,
            email=google_user_info.email,
            nickname=google_user_info.nickname,
            avatar_url=google_user_info.avatar_url
        )
        
        return await self.create(db, user_data)
    
    async def get_or_create_google_user(
        self, 
        db: AsyncSession, 
        google_user_info: GoogleUserInfo
    ) -> User:
        """Get existing user or create new user from Google OAuth"""
        # First try to find by Google ID
        user = await self.get_by_google_id(db, google_user_info.google_id)
        
        if user:
            # Update existing user with latest Google info
            if user.nickname != google_user_info.nickname or user.avatar_url != google_user_info.avatar_url:
                update_data = UserUpdate(
                    nickname=google_user_info.nickname,
                    avatar_url=google_user_info.avatar_url
                )
                user = await self.update(db, user.id, update_data)
            return user
        
        # Try to find by email (existing user linking Google account)
        user = await self.get_by_email(db, google_user_info.email)
        
        if user:
            # Link Google ID to existing user
            if not user.google_id:
                user.google_id = google_user_info.google_id
                await db.commit()
                await db.refresh(user)
            return user
        
        # Create new user
        return await self.create_from_google(db, google_user_info)
    
    async def add_wallet(
        self, 
        db: AsyncSession, 
        user_id: int, 
        wallet_data: UserWalletCreate
    ) -> UserWallet:
        """Add wallet to user"""
        # Check if user exists
        user = await self.get(db, user_id)
        if not user:
            raise NotFoundError("User not found")
        
        # Check if wallet already exists
        stmt = select(UserWallet).where(
            UserWallet.wallet_address == wallet_data.wallet_address
        )
        result = await db.execute(stmt)
        existing_wallet = result.scalar_one_or_none()
        
        if existing_wallet:
            raise ValidationError("Wallet address already registered")
        
        # Create wallet
        wallet = UserWallet(
            user_id=user_id,
            wallet_address=wallet_data.wallet_address,
            wallet_type=wallet_data.wallet_type,
            is_primary=wallet_data.is_primary
        )
        
        # If this is set as primary, unset other primary wallets
        if wallet_data.is_primary:
            await db.execute(
                update(UserWallet)
                .where(UserWallet.user_id == user_id)
                .values(is_primary=False)
            )
        
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
        
        return wallet
    
    async def get_user_wallets(self, db: AsyncSession, user_id: int) -> List[UserWallet]:
        """Get all wallets for a user"""
        stmt = select(UserWallet).where(
            UserWallet.user_id == user_id
        ).order_by(UserWallet.is_primary.desc(), UserWallet.created_at)
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def remove_wallet(
        self, 
        db: AsyncSession, 
        user_id: int, 
        wallet_id: int
    ) -> bool:
        """Remove wallet from user"""
        stmt = delete(UserWallet).where(
            UserWallet.id == wallet_id,
            UserWallet.user_id == user_id
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        return result.rowcount > 0
    
    async def set_primary_wallet(
        self, 
        db: AsyncSession, 
        user_id: int, 
        wallet_id: int
    ) -> bool:
        """Set a wallet as primary for user"""
        # First unset all primary wallets for user
        await db.execute(
            update(UserWallet)
            .where(UserWallet.user_id == user_id)
            .values(is_primary=False)
        )
        
        # Set the specified wallet as primary
        result = await db.execute(
            update(UserWallet)
            .where(
                UserWallet.id == wallet_id,
                UserWallet.user_id == user_id
            )
            .values(is_primary=True)
        )
        
        await db.commit()
        return result.rowcount > 0
    
    async def deactivate_user(self, db: AsyncSession, user_id: int) -> bool:
        """Deactivate user account"""
        result = await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False)
        )
        
        await db.commit()
        return result.rowcount > 0
    
    async def reactivate_user(self, db: AsyncSession, user_id: int) -> bool:
        """Reactivate user account"""
        result = await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=True)
        )
        
        await db.commit()
        return result.rowcount > 0
    
    async def search_users(
        self, 
        db: AsyncSession, 
        query: str, 
        limit: int = 20, 
        offset: int = 0
    ) -> List[User]:
        """Search users by nickname or email"""
        stmt = select(User).where(
            User.is_active == True,
            (User.nickname.ilike(f"%{query}%") | User.email.ilike(f"%{query}%"))
        ).limit(limit).offset(offset)
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_user_stats(self, db: AsyncSession, user_id: int) -> dict:
        """Get user statistics"""
        # This would typically include task counts, completion rates, etc.
        # For now, return basic info
        user = await self.get(db, user_id)
        if not user:
            raise NotFoundError("User not found")
        
        return {
            "user_id": user_id,
            "created_at": user.created_at,
            "is_active": user.is_active,
            "has_google_auth": bool(user.google_id),
            "wallet_count": len(await self.get_user_wallets(db, user_id))
        }


# Service instance
user_service = UserService()