"""
Notification-related Pydantic schemas
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

from .user import User
from .task import TaskSummary


class NotificationType(str, Enum):
    """Notification type enumeration"""
    TASK_REMINDER_3D = "task_reminder_3d"
    TASK_REMINDER_1D = "task_reminder_1d"
    TASK_REMINDER_2H = "task_reminder_2h"
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


class NotificationBase(BaseModel):
    """Base notification schema"""
    type: str
    channel: str
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    scheduled_at: datetime


class NotificationCreate(NotificationBase):
    """Schema for creating a notification"""
    user_id: int
    task_id: Optional[int] = None


class NotificationUpdate(BaseModel):
    """Schema for updating a notification"""
    status: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivery_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None


class Notification(NotificationBase):
    """Schema for notification response"""
    id: int
    user_id: int
    task_id: Optional[int] = None
    status: str
    sent_at: Optional[datetime] = None
    delivery_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
    user: Optional[User] = None
    task: Optional[TaskSummary] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationList(BaseModel):
    """Notification list response"""
    notifications: List[Notification]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


# Notification Template schemas
class NotificationTemplateBase(BaseModel):
    """Base notification template schema"""
    type: NotificationType
    channel: NotificationChannel
    title_template: str = Field(..., min_length=1, max_length=255)
    message_template: str = Field(..., min_length=1)
    variables: Optional[str] = None
    is_active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    """Schema for creating a notification template"""
    pass


class NotificationTemplateUpdate(BaseModel):
    """Schema for updating a notification template"""
    title_template: Optional[str] = Field(None, min_length=1, max_length=255)
    message_template: Optional[str] = Field(None, min_length=1)
    variables: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationTemplate(NotificationTemplateBase):
    """Schema for notification template response"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# User Notification Preference schemas
class UserNotificationPreferenceBase(BaseModel):
    """Base user notification preference schema"""
    task_reminder_3d_enabled: bool = True
    task_reminder_1d_enabled: bool = True
    task_reminder_2h_enabled: bool = True
    task_completed_enabled: bool = True
    task_cancelled_enabled: bool = True
    new_message_enabled: bool = True
    telegram_enabled: bool = False
    websocket_enabled: bool = True
    email_enabled: bool = False
    quiet_hours_start: Optional[int] = Field(None, ge=0, le=23)
    quiet_hours_end: Optional[int] = Field(None, ge=0, le=23)
    timezone: str = "UTC"


class UserNotificationPreferenceCreate(UserNotificationPreferenceBase):
    """Schema for creating user notification preferences"""
    user_id: int


class UserNotificationPreferenceUpdate(BaseModel):
    """Schema for updating user notification preferences"""
    task_reminder_3d_enabled: Optional[bool] = None
    task_reminder_1d_enabled: Optional[bool] = None
    task_reminder_2h_enabled: Optional[bool] = None
    task_completed_enabled: Optional[bool] = None
    task_cancelled_enabled: Optional[bool] = None
    new_message_enabled: Optional[bool] = None
    telegram_enabled: Optional[bool] = None
    websocket_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    quiet_hours_start: Optional[int] = Field(None, ge=0, le=23)
    quiet_hours_end: Optional[int] = Field(None, ge=0, le=23)
    timezone: Optional[str] = None


class UserNotificationPreference(UserNotificationPreferenceBase):
    """Schema for user notification preference response"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    user: Optional[User] = None

    model_config = ConfigDict(from_attributes=True)


# Telegram integration schemas
class TelegramBindRequest(BaseModel):
    """Schema for Telegram binding request"""
    telegram_chat_id: str
    telegram_username: Optional[str] = None


class TelegramBindResponse(BaseModel):
    """Schema for Telegram binding response"""
    success: bool
    message: str
    telegram_chat_id: Optional[str] = None
    telegram_username: Optional[str] = None


class TelegramUnbindResponse(BaseModel):
    """Schema for Telegram unbinding response"""
    success: bool
    message: str


# WebSocket message schemas
class WebSocketMessage(BaseModel):
    """Schema for WebSocket messages"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime


class TaskReminderMessage(BaseModel):
    """Schema for task reminder WebSocket messages"""
    type: str = "task_reminder"
    task_id: int
    task_title: str
    deadline: int
    reminder_type: NotificationType
    message: str
    timestamp: datetime


class TaskCompletedMessage(BaseModel):
    """Schema for task completed WebSocket messages"""
    type: str = "task_completed"
    task_id: int
    task_title: str
    message: str
    timestamp: datetime


class NewMessageNotification(BaseModel):
    """Schema for new message WebSocket notifications"""
    type: str = "new_message"
    task_id: int
    task_title: str
    message_id: int
    sender_name: str
    message_preview: str
    timestamp: datetime
