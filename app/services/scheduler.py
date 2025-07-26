"""
后台任务调度器
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.notification import notification_service, task_reminder_scheduler
from app.services.telegram_bot import telegram_notification_sender
from app.services.websocket import websocket_notification_sender

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """通知调度器"""

    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("Notification scheduler is already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("Notification scheduler started")

    async def stop(self):
        """停止调度器"""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("Notification scheduler stopped")

    async def _run_scheduler(self):
        """运行调度器主循环"""
        while self.running:
            try:
                await self._process_notifications()
                # 每30秒检查一次
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification scheduler: {e}")
                await asyncio.sleep(60)  # 出错时等待更长时间

    async def _process_notifications(self):
        """处理待发送的通知"""
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            try:
                # 发送Telegram通知
                await telegram_notification_sender.send_pending_notifications(db)

                # 发送WebSocket通知
                await websocket_notification_sender.send_pending_notifications(db)

                # logger.debug("Processed pending notifications")  # 减少日志输出

            except Exception as e:
                logger.error(f"Error processing notifications: {e}")
                await db.rollback()


class TaskReminderSchedulerService:
    """任务提醒调度服务"""

    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """启动任务提醒调度器"""
        if self.running:
            logger.warning("Task reminder scheduler is already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("Task reminder scheduler started")

    async def stop(self):
        """停止任务提醒调度器"""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("Task reminder scheduler stopped")

    async def _run_scheduler(self):
        """运行调度器主循环"""
        while self.running:
            try:
                await self._schedule_upcoming_reminders()
                # 每小时检查一次
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in task reminder scheduler: {e}")
                await asyncio.sleep(1800)  # 出错时等待30分钟

    async def _schedule_upcoming_reminders(self):
        """为即将到期的任务安排提醒"""
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models.task import Task

        async with AsyncSessionLocal() as db:
            try:
                # 查找未来7天内到期的任务
                future_timestamp = int(datetime.utcnow().timestamp()) + (7 * 24 * 3600)  # 7 days in seconds

                result = await db.execute(
                    select(Task).where(
                        Task.deadline.isnot(None),
                        Task.deadline <= future_timestamp,
                        Task.status == "active"
                    )
                )
                tasks = result.scalars().all()

                for task in tasks:
                    await task_reminder_scheduler.schedule_task_reminders(db, task.id)

                # 只在有任务时才记录日志
                if tasks:
                    logger.info(f"Scheduled reminders for {len(tasks)} upcoming tasks")

            except Exception as e:
                logger.error(f"Error scheduling task reminders: {e}")
                await db.rollback()


class SchedulerManager:
    """调度器管理器"""

    def __init__(self):
        self.notification_scheduler = NotificationScheduler()
        self.task_reminder_scheduler = TaskReminderSchedulerService()

    async def start_all(self):
        """启动所有调度器"""
        await self.notification_scheduler.start()
        await self.task_reminder_scheduler.start()
        logger.info("All schedulers started")

    async def stop_all(self):
        """停止所有调度器"""
        await self.notification_scheduler.stop()
        await self.task_reminder_scheduler.stop()
        logger.info("All schedulers stopped")


# 全局调度器实例
scheduler_manager = SchedulerManager()
