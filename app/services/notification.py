"""
Notification service for managing notifications and reminders
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update, delete
from sqlalchemy.orm import selectinload

from app.models.notification import (
    Notification,
    NotificationTemplate,
    UserNotificationPreference,
    NotificationType,
    NotificationStatus,
    NotificationChannel
)
from app.models.user import User
from app.models.task import Task, Todo
from app.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
    UserNotificationPreferenceCreate,
    UserNotificationPreferenceUpdate
)
from app.services.base import BaseService
from app.core.exceptions import NotFoundError, ValidationError


class NotificationService(BaseService[Notification, NotificationCreate, NotificationUpdate]):
    """Service for managing notifications"""

    def __init__(self):
        super().__init__(Notification)

    async def create_task_reminder(
        self,
        db: AsyncSession,
        user_id: int,
        task_id: int,
        reminder_type: NotificationType,
        scheduled_at: datetime,
        channel: str = "websocket"
    ) -> Notification:
        """Create a task reminder notification"""

        # Get task details
        task_result = await db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            raise NotFoundError("Task not found")

        # Get notification template
        template = await self.get_notification_template(db, reminder_type, channel)

        # Generate notification content
        title, message = self._generate_notification_content(
            template, task, reminder_type
        )

        # Create notification
        notification_data = NotificationCreate(
            user_id=user_id,
            task_id=task_id,
            type=reminder_type,
            channel=channel,
            title=title,
            message=message,
            scheduled_at=scheduled_at
        )

        return await self.create(db, notification_data)

    async def get_notification_template(
        self,
        db: AsyncSession,
        notification_type: NotificationType,
        channel: str
    ) -> NotificationTemplate:
        """Get notification template for type and channel"""

        result = await db.execute(
            select(NotificationTemplate)
            .where(
                and_(
                    NotificationTemplate.type == notification_type,
                    NotificationTemplate.channel == channel,
                    NotificationTemplate.is_active == True
                )
            )
        )
        template = result.scalar_one_or_none()

        if not template:
            # Create default template if not exists
            template = await self._create_default_template(db, notification_type, channel)

        return template

    async def _create_default_template(
        self,
        db: AsyncSession,
        notification_type: NotificationType,
        channel: str
    ) -> NotificationTemplate:
        """Create default notification template"""

        templates = {
            NotificationType.TASK_REMINDER_3D: {
                "title": "Task Reminder - 3 Days Left",
                "message": "Task '{task_title}' is due in 3 days (Deadline: {deadline}). Don't forget to complete it!"
            },
            NotificationType.TASK_REMINDER_1D: {
                "title": "Task Reminder - 1 Day Left",
                "message": "Task '{task_title}' is due tomorrow (Deadline: {deadline}). Time to finish up!"
            },
            NotificationType.TASK_REMINDER_2H: {
                "title": "Task Reminder - 2 Hours Left",
                "message": "Task '{task_title}' is due in 2 hours (Deadline: {deadline}). Final reminder!"
            },
            NotificationType.TASK_COMPLETED: {
                "title": "Task Completed",
                "message": "Task '{task_title}' has been marked as completed. Great job!"
            },
            NotificationType.TASK_CANCELLED: {
                "title": "Task Cancelled",
                "message": "Task '{task_title}' has been cancelled by the sponsor."
            },
            NotificationType.NEW_MESSAGE: {
                "title": "New Message",
                "message": "New message in task '{task_title}' from {sender_name}: {message_preview}"
            }
        }

        template_data = templates.get(notification_type)
        if not template_data:
            raise ValidationError(f"No default template for {notification_type}")

        template = NotificationTemplate(
            type=notification_type,
            channel=channel,
            title_template=template_data["title"],
            message_template=template_data["message"],
            variables=json.dumps(["task_title", "deadline", "sender_name", "message_preview"]),
            is_active=True
        )

        db.add(template)
        await db.commit()
        await db.refresh(template)

        return template

    def _generate_notification_content(
        self,
        template: NotificationTemplate,
        task: Task,
        notification_type: NotificationType,
        **kwargs
    ) -> tuple[str, str]:
        """Generate notification title and message from template"""

        # Prepare template variables
        variables = {
            "task_title": task.title,
            "deadline": task.deadline.strftime("%Y-%m-%d %H:%M") if task.deadline else "No deadline",
            "task_id": task.id,
            **kwargs
        }

        # Format title and message
        title = template.title_template.format(**variables)
        message = template.message_template.format(**variables)

        return title, message

    async def get_pending_notifications(
        self,
        db: AsyncSession,
        channel: Optional[str] = None,
        limit: int = 100
    ) -> List[Notification]:
        """Get pending notifications ready to be sent"""

        query = select(Notification).options(
            selectinload(Notification.user),
            selectinload(Notification.task)
        ).where(
            and_(
                Notification.status == "pending",
                Notification.scheduled_at <= datetime.utcnow(),
                Notification.retry_count < Notification.max_retries
            )
        )

        if channel:
            query = query.where(Notification.channel == channel)

        query = query.limit(limit).order_by(Notification.scheduled_at)

        result = await db.execute(query)
        return result.scalars().all()

    async def mark_notification_sent(
        self,
        db: AsyncSession,
        notification_id: int,
        delivery_id: Optional[str] = None
    ) -> bool:
        """Mark notification as sent"""

        update_data = {
            "status": "sent",
            "sent_at": datetime.utcnow()
        }

        if delivery_id:
            update_data["delivery_id"] = delivery_id

        result = await db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(**update_data)
        )

        await db.commit()
        return result.rowcount > 0

    async def mark_notification_failed(
        self,
        db: AsyncSession,
        notification_id: int,
        error_message: str
    ) -> bool:
        """Mark notification as failed and increment retry count"""

        result = await db.execute(
            update(Notification)
            .where(Notification.id == notification_id)
            .values(
                status="failed",
                error_message=error_message,
                retry_count=Notification.retry_count + 1
            )
        )

        await db.commit()
        return result.rowcount > 0

    async def get_user_notifications(
        self,
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        size: int = 20,
        status: Optional[NotificationStatus] = None
    ) -> tuple[List[Notification], int]:
        """Get user notifications with pagination"""

        query = select(Notification).options(
            selectinload(Notification.task)
        ).where(Notification.user_id == user_id)

        if status:
            # Convert enum to string value if needed
            status_value = status.value if hasattr(status, 'value') else status
            query = query.where(Notification.status == status_value)

        # Count total
        count_result = await db.execute(
            select(Notification).where(Notification.user_id == user_id)
        )
        total = len(count_result.scalars().all())

        # Get paginated results
        offset = (page - 1) * size
        query = query.offset(offset).limit(size).order_by(Notification.created_at.desc())

        result = await db.execute(query)
        notifications = result.scalars().all()

        return notifications, total


class UserNotificationPreferenceService(BaseService[UserNotificationPreference, UserNotificationPreferenceCreate, UserNotificationPreferenceUpdate]):
    """Service for managing user notification preferences"""

    def __init__(self):
        super().__init__(UserNotificationPreference)

    async def get_user_preferences(
        self,
        db: AsyncSession,
        user_id: int
    ) -> UserNotificationPreference:
        """Get user notification preferences, create default if not exists"""

        result = await db.execute(
            select(UserNotificationPreference)
            .where(UserNotificationPreference.user_id == user_id)
        )
        preferences = result.scalar_one_or_none()

        if not preferences:
            # Create default preferences
            preferences_data = UserNotificationPreferenceCreate(user_id=user_id)
            preferences = await self.create(db, preferences_data)

        return preferences

    async def update_user_preferences(
        self,
        db: AsyncSession,
        user_id: int,
        preferences_update: UserNotificationPreferenceUpdate
    ) -> UserNotificationPreference:
        """Update user notification preferences"""

        preferences = await self.get_user_preferences(db, user_id)

        update_data = preferences_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(preferences, field, value)

        await db.commit()
        await db.refresh(preferences)

        return preferences


class TaskReminderScheduler:
    """Service for scheduling task reminders"""

    async def schedule_task_reminders(self, db: AsyncSession, task_id: int):
        """Schedule all reminders for a task"""
        # Get task with todos
        task_result = await db.execute(
            select(Task).options(
                selectinload(Task.todos).selectinload(Todo.user)
            ).where(Task.id == task_id)
        )
        task = task_result.scalar_one_or_none()

        if not task or not task.deadline:
            return

        # Schedule reminders for each user who joined the task
        for todo in task.todos:
            if not todo.is_active:
                continue

            await self._schedule_user_task_reminders(db, todo.user, task, todo)

    async def _schedule_user_task_reminders(
        self,
        db: AsyncSession,
        user: User,
        task: Task,
        todo: Todo
    ):
        """Schedule reminders for a specific user and task"""
        if not task.deadline:
            return

        # Get user preferences
        preferences = await user_notification_preference_service.get_user_preferences(db, user.id)

        # Parse remind_flags from todo
        remind_flags = json.loads(todo.remind_flags) if todo.remind_flags else {}

        # Schedule 3-day reminder
        if (remind_flags.get("t_3d", True) and
            preferences.task_reminder_3d_enabled):

            reminder_time = task.deadline - timedelta(days=3)
            if reminder_time > datetime.utcnow():
                await self._create_reminder(
                    db, user.id, task.id,
                    NotificationType.TASK_REMINDER_3D,
                    reminder_time, preferences
                )

        # Schedule 1-day reminder
        if (remind_flags.get("t_1d", True) and
            preferences.task_reminder_1d_enabled):

            reminder_time = task.deadline - timedelta(days=1)
            if reminder_time > datetime.utcnow():
                await self._create_reminder(
                    db, user.id, task.id,
                    NotificationType.TASK_REMINDER_1D,
                    reminder_time, preferences
                )

        # Schedule 2-hour reminder
        if (remind_flags.get("ddl_2h", True) and
            preferences.task_reminder_2h_enabled):

            reminder_time = task.deadline - timedelta(hours=2)
            if reminder_time > datetime.utcnow():
                await self._create_reminder(
                    db, user.id, task.id,
                    NotificationType.TASK_REMINDER_2H,
                    reminder_time, preferences
                )

    async def _create_reminder(
        self,
        db: AsyncSession,
        user_id: int,
        task_id: int,
        reminder_type: NotificationType,
        scheduled_at: datetime,
        preferences: UserNotificationPreference
    ):
        """Create reminder notifications for enabled channels"""

        # Create Telegram reminder if enabled
        if preferences.telegram_enabled:
            await notification_service.create_task_reminder(
                db, user_id, task_id, reminder_type, scheduled_at,
                "telegram"
            )

        # Create WebSocket reminder if enabled
        if preferences.websocket_enabled:
            await notification_service.create_task_reminder(
                db, user_id, task_id, reminder_type, scheduled_at,
                "websocket"
            )

        # Create Email reminder if enabled
        if preferences.email_enabled:
            await notification_service.create_task_reminder(
                db, user_id, task_id, reminder_type, scheduled_at,
                "email"
            )


# Service instances
notification_service = NotificationService()
user_notification_preference_service = UserNotificationPreferenceService()
task_reminder_scheduler = TaskReminderScheduler()
