"""
Telegram Bot service for sending notifications
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.models.notification import Notification, NotificationChannel
from app.services.notification import notification_service
from app.core.database import get_db

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Service for managing Telegram Bot interactions"""

    def __init__(self):
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self._initialized = False

    async def initialize(self):
        """Initialize Telegram Bot"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram Bot token not configured")
            return

        try:
            self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("bind", self.bind_command))
            self.application.add_handler(CommandHandler("unbind", self.unbind_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))

            # Add message handler for unknown commands
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.unknown_message))

            self._initialized = True
            logger.info("Telegram Bot initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Telegram Bot: {e}")
            raise

    async def start_bot(self):
        """Start the Telegram Bot"""
        if not self._initialized:
            await self.initialize()

        if self.application:
            await self.application.initialize()
            await self.application.start()
            logger.info("Telegram Bot started")

    async def stop_bot(self):
        """Stop the Telegram Bot"""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram Bot stopped")

    async def send_notification(
        self,
        chat_id: str,
        title: str,
        message: str,
        notification_id: Optional[int] = None
    ) -> Optional[str]:
        """Send notification message to Telegram chat"""
        if not self.bot:
            logger.error("Telegram Bot not initialized")
            return None

        try:
            # Format message
            full_message = f"🔔 *{title}*\n\n{message}"

            # Send message
            telegram_message = await self.bot.send_message(
                chat_id=chat_id,
                text=full_message,
                parse_mode='Markdown'
            )

            logger.info(f"Notification sent to chat {chat_id}, message_id: {telegram_message.message_id}")
            return str(telegram_message.message_id)

        except TelegramError as e:
            logger.error(f"Failed to send Telegram notification to {chat_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram notification: {e}")
            return None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = (
            "🎯 Welcome to BoutyGo Notification Bot!\n\n"
            "This bot will send you task reminders and updates.\n\n"
            "Available commands:\n"
            "/bind <user_token> - Bind your account\n"
            "/unbind - Unbind your account\n"
            "/status - Check binding status\n"
            "/help - Show this help message\n\n"
            "To get started, use /bind command with your user token from the BoutyGo app."
        )

        await update.message.reply_text(welcome_message)

    async def bind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /bind command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide your user token.\n"
                "Usage: /bind <user_token>\n\n"
                "You can find your user token in the BoutyGo app settings."
            )
            return

        user_token = context.args[0]
        chat_id = str(update.effective_chat.id)
        username = update.effective_user.username

        # Here you would validate the user token and bind the account
        # For now, we'll just show a placeholder response
        await update.message.reply_text(
            f"🔗 Binding request received!\n\n"
            f"Chat ID: {chat_id}\n"
            f"Username: @{username}\n"
            f"Token: {user_token[:8]}...\n\n"
            "Please complete the binding process in the BoutyGo app."
        )

    async def unbind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unbind command"""
        chat_id = str(update.effective_chat.id)

        # Here you would unbind the account
        # For now, we'll just show a placeholder response
        await update.message.reply_text(
            "🔓 Account unbound successfully!\n\n"
            "You will no longer receive notifications from BoutyGo.\n"
            "Use /bind to reconnect your account anytime."
        )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        chat_id = str(update.effective_chat.id)

        # Here you would check the binding status
        # For now, we'll just show a placeholder response
        await update.message.reply_text(
            f"📊 Status Information\n\n"
            f"Chat ID: {chat_id}\n"
            f"Status: Not bound\n\n"
            "Use /bind <user_token> to connect your account."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "🤖 BoutyGo Notification Bot Help\n\n"
            "Available commands:\n"
            "/start - Welcome message and setup\n"
            "/bind <token> - Bind your BoutyGo account\n"
            "/unbind - Unbind your account\n"
            "/status - Check your binding status\n"
            "/help - Show this help message\n\n"
            "📱 How to use:\n"
            "1. Get your user token from BoutyGo app\n"
            "2. Use /bind <token> to connect\n"
            "3. Start receiving task reminders!\n\n"
            "Need help? Contact support in the BoutyGo app."
        )

        await update.message.reply_text(help_message)

    async def unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown messages"""
        await update.message.reply_text(
            "❓ I don't understand that command.\n"
            "Use /help to see available commands."
        )


class TelegramNotificationSender:
    """Service for sending notifications via Telegram"""

    def __init__(self, bot_service: TelegramBotService):
        self.bot_service = bot_service

    async def send_pending_notifications(self, db: AsyncSession):
        """Send all pending Telegram notifications"""
        if not self.bot_service._initialized:
            # logger.warning("Telegram Bot not initialized, skipping notifications")  # 减少日志输出
            return

        # Get pending Telegram notifications
        notifications = await notification_service.get_pending_notifications(
            db, channel="telegram"
        )

        # 只在有通知时才记录日志
        if notifications:
            logger.info(f"Found {len(notifications)} pending Telegram notifications")

        for notification in notifications:
            await self._send_notification(db, notification)

    async def _send_notification(self, db: AsyncSession, notification: Notification):
        """Send a single notification"""
        try:
            # Check if user has Telegram enabled
            if not notification.user.telegram_chat_id:
                logger.warning(f"User {notification.user_id} has no Telegram chat ID")
                await notification_service.mark_notification_failed(
                    db, notification.id, "User has no Telegram chat ID"
                )
                return

            if not notification.user.telegram_notifications_enabled:
                logger.info(f"User {notification.user_id} has Telegram notifications disabled")
                await notification_service.mark_notification_failed(
                    db, notification.id, "User has Telegram notifications disabled"
                )
                return

            # Send notification
            delivery_id = await self.bot_service.send_notification(
                chat_id=notification.user.telegram_chat_id,
                title=notification.title,
                message=notification.message,
                notification_id=notification.id
            )

            if delivery_id:
                await notification_service.mark_notification_sent(
                    db, notification.id, delivery_id
                )
                logger.info(f"Notification {notification.id} sent successfully")
            else:
                await notification_service.mark_notification_failed(
                    db, notification.id, "Failed to send Telegram message"
                )
                logger.error(f"Failed to send notification {notification.id}")

        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {e}")
            await notification_service.mark_notification_failed(
                db, notification.id, str(e)
            )


# Global instances
telegram_bot_service = TelegramBotService()
telegram_notification_sender = TelegramNotificationSender(telegram_bot_service)
