"""
User-related database models
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, String, Text, DECIMAL, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User model for authentication and profile management"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Telegram integration
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telegram_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    wallets: Mapped[List["UserWallet"]] = relationship(
        "UserWallet", back_populates="user", cascade="all, delete-orphan"
    )
    tag_profiles: Mapped[List["UserTagProfile"]] = relationship(
        "UserTagProfile", back_populates="user", cascade="all, delete-orphan"
    )
    sponsored_tasks: Mapped[List["Task"]] = relationship(
        "Task", back_populates="sponsor", cascade="all, delete-orphan"
    )
    todos: Mapped[List["Todo"]] = relationship(
        "Todo", back_populates="user", cascade="all, delete-orphan"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="user", cascade="all, delete-orphan"
    )
    task_views: Mapped[List["TaskView"]] = relationship(
        "TaskView", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    notification_preferences: Mapped[List["UserNotificationPreference"]] = relationship(
        "UserNotificationPreference", back_populates="user", cascade="all, delete-orphan"
    )


class UserWallet(Base, TimestampMixin):
    """User wallet addresses for Web3 authentication"""
    __tablename__ = "user_wallets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    wallet_address: Mapped[str] = mapped_column(String(42), unique=True, nullable=False)
    wallet_type: Mapped[str] = mapped_column(String(20), default="ethereum", nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wallets")


class RefreshToken(Base, TimestampMixin):
    """Refresh tokens for JWT authentication"""
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")