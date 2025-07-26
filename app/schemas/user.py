"""
User-related Pydantic schemas
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    nickname: str = Field(..., min_length=1, max_length=100)
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a user"""
    google_id: Optional[str] = None
    clerk_id: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    nickname: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar_url: Optional[str] = None
    telegram_notifications_enabled: Optional[bool] = None


class UserWalletBase(BaseModel):
    """Base wallet schema"""
    wallet_address: str = Field(..., min_length=42, max_length=42)
    wallet_type: str = Field(default="ethereum", max_length=20)
    is_primary: bool = False


class UserWalletCreate(UserWalletBase):
    """Schema for creating a wallet"""
    pass


class UserWallet(UserWalletBase):
    """Schema for wallet response"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RefreshTokenBase(BaseModel):
    """Base refresh token schema"""
    expires_at: datetime
    is_revoked: bool = False


class RefreshTokenCreate(RefreshTokenBase):
    """Schema for creating a refresh token"""
    user_id: int
    token_hash: str


class RefreshToken(RefreshTokenBase):
    """Schema for refresh token response"""
    id: int
    user_id: int
    token_hash: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class User(UserBase):
    """Schema for user response"""
    id: int
    is_active: bool
    telegram_chat_id: Optional[str] = None
    telegram_username: Optional[str] = None
    telegram_notifications_enabled: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserWithWallets(User):
    """User schema with wallets included"""
    wallets: List[UserWallet] = []


class UserProfile(User):
    """Extended user profile with relationships"""
    tag_profile: Optional["UserTagProfile"] = None


class UserInDB(User):
    """User schema for database operations"""
    google_id: Optional[str] = None
    clerk_id: Optional[str] = None


# Authentication schemas
class TokenResponse(BaseModel):
    """Token response schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class GoogleAuthRequest(BaseModel):
    """Google OAuth authentication request"""
    google_token: str = Field(..., min_length=1, description="Google OAuth ID token")


class WalletAuthRequest(BaseModel):
    """Wallet authentication request"""
    wallet_address: str = Field(..., min_length=42, max_length=42)
    signature: str
    message: str


class ClerkAuthRequest(BaseModel):
    """Clerk authentication request"""
    clerk_token: str = Field(..., min_length=1, description="Clerk JWT token")


class ClerkLinkRequest(BaseModel):
    """Request to link Clerk account to existing user"""
    clerk_token: str = Field(..., min_length=1, description="Clerk JWT token")
    user_id: Optional[int] = None  # If not provided, use current authenticated user


class GoogleUserInfo(BaseModel):
    """Google user information"""
    google_id: str
    email: EmailStr
    nickname: str
    avatar_url: Optional[str] = None
    verified_email: bool = True


# Forward reference resolution
from .tag import UserTagProfile
UserProfile.model_rebuild()