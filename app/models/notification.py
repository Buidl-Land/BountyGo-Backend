"""
Notification-related database models
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from .base import Base, TimestampMixin


class NotificationType(str, Enum):
    """Notification type enumeration"""
    TASK_REMINDER_3D = "task_reminder_3d"  # 3 days before deadline
    TASK_REMINDER_1D = "task_reminder_1d"  # 1 day before deadline
    TASK_REMINDER_2H = "task_reminder_2h"  # 2 hours before deadline
    TASK_COMPLETED = "task_completed"
    TASK_CANCELLED = "task_cancelled"
    NEW_MESSAGE = "new_message"


class NotificationStatus(str, Enum):
    """Notification status enumeration"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationChannel(str, Enum):
    """Notification delivery channel"""
    TELEGRAM = "telegram"
    WEBSOCKET = "websocket"
    EMAIL = "email"


class Notification(Base, TimestampMixin):
    """Notification model for tracking all notifications"""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)

    # Notification details
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Scheduling
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Delivery details
    delivery_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # External delivery ID (e.g., Telegram message ID)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    task: Mapped[Optional["Task"]] = relationship("Task", back_populates="notifications")


class NotificationTemplate(Base, TimestampMixin):
    """Notification template for different types and channels"""
    __tablename__ = "notification_templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)

    # Template content
    title_template: Mapped[str] = mapped_column(String(255), nullable=False)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)

    # Template variables (JSON format)
    variables: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string of available variables

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Unique constraint on type and channel
    __table_args__ = (
        {"extend_existing": True}
    )


class UserNotificationPreference(Base, TimestampMixin):
    """User notification preferences"""
    __tablename__ = "user_notification_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Notification type preferences
    task_reminder_3d_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    task_reminder_1d_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    task_reminder_2h_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    task_completed_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    task_cancelled_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    new_message_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Channel preferences
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    websocket_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Quiet hours (24-hour format)
    quiet_hours_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-23
    quiet_hours_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)    # 0-23

    # Timezone
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notification_preferences")
