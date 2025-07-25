"""
Telegram Bot service for sending notifications with complete binding functionality
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.services.notification import notification_service

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Telegram Bot service for notifications"""

    def __init__(self):
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Telegram Bot"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.warning("Telegram Bot token not configured")
            return False

        try:
            # Create bot instance
            self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

            # Create application
            self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("bind", self.bind_command))
            self.application.add_handler(CommandHandler("unbind", self.unbind_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("help", self.help_command))

            # Add message handler for unknown commands
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.unknown_message))

            # Start the bot
            await self.application.initialize()
            await self.application.start()

            self._initialized = True
            logger.info("✅ Telegram Bot initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Telegram Bot: {e}")
            return False

    async def shutdown(self):
        """Shutdown Telegram Bot"""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
        self._initialized = False
        logger.info("Telegram Bot shutdown")

    async def send_notification(self, chat_id: str, title: str, message: str) -> Optional[str]:
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
            "🎯 Welcome to BountyGo Notification Bot!\n\n"
            "This bot will send you task reminders and updates.\n\n"
            "Available commands:\n"
            "/bind <user_id> - Bind your account\n"
            "/unbind - Unbind your account\n"
            "/status - Check binding status\n"
            "/help - Show this help message\n\n"
            "To get started, use /bind command with your user ID from the BountyGo app."
        )

        await update.message.reply_text(welcome_message)

    async def bind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /bind command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide your user ID.\n"
                "Usage: /bind <user_id>\n\n"
                "You can find your user ID in the BountyGo app profile."
            )
            return

        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid user ID format.\n"
                "Please provide a valid numeric user ID.\n\n"
                "Example: /bind 123"
            )
            return
        chat_id = str(update.effective_chat.id)
        username = update.effective_user.username

        # 验证token并绑定账号
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            try:
                # 查找用户
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    await update.message.reply_text(
                        "❌ User ID not found.\n\n"
                        "Please check your user ID and try again.\n"
                        "You can find your user ID in the BountyGo app profile."
                    )
                    return

                # 检查是否已经绑定了其他账号
                if user.telegram_chat_id and user.telegram_chat_id != chat_id:
                    await update.message.reply_text(
                        "⚠️ This account is already bound to another Telegram account.\n\n"
                        "Please unbind the previous account first or contact support."
                    )
                    return

                # 绑定账号
                await db.execute(
                    update(User)
                    .where(User.id == user.id)
                    .values(
                        telegram_chat_id=chat_id,
                        telegram_username=username,
                        telegram_notifications_enabled=True
                    )
                )
                await db.commit()

                await update.message.reply_text(
                    f"✅ Account bound successfully!\n\n"
                    f"👤 User: {user.username}\n"
                    f"🆔 User ID: {user_id}\n"
                    f"📱 Chat ID: {chat_id}\n"
                    f"🔔 Notifications: Enabled\n\n"
                    "You will now receive task reminders and updates from BountyGo!"
                )

            except Exception as e:
                logger.error(f"Error binding Telegram account: {e}")
                await update.message.reply_text(
                    "❌ An error occurred while binding your account.\n\n"
                    "Please try again later or contact support."
                )
                await db.rollback()

    async def unbind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unbind command"""
        chat_id = str(update.effective_chat.id)

        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            try:
                # 查找绑定的用户
                result = await db.execute(
                    select(User).where(User.telegram_chat_id == chat_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    await update.message.reply_text(
                        "❌ No account is bound to this Telegram chat.\n\n"
                        "Use /bind <user_token> to bind your account."
                    )
                    return

                # 解绑账号
                await db.execute(
                    update(User)
                    .where(User.id == user.id)
                    .values(
                        telegram_chat_id=None,
                        telegram_username=None,
                        telegram_notifications_enabled=False
                    )
                )
                await db.commit()

                await update.message.reply_text(
                    f"🔓 Account unbound successfully!\n\n"
                    f"👤 User: {user.username}\n"
                    f"🔔 Notifications: Disabled\n\n"
                    "You will no longer receive notifications from BountyGo.\n"
                    "Use /bind to reconnect your account anytime."
                )

            except Exception as e:
                logger.error(f"Error unbinding Telegram account: {e}")
                await update.message.reply_text(
                    "❌ An error occurred while unbinding your account.\n\n"
                    "Please try again later or contact support."
                )
                await db.rollback()

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        chat_id = str(update.effective_chat.id)

        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            try:
                # 查找绑定的用户
                result = await db.execute(
                    select(User).where(User.telegram_chat_id == chat_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    await update.message.reply_text(
                        "❌ No account is bound to this Telegram chat.\n\n"
                        "📱 Chat ID: {chat_id}\n"
                        "🔗 Status: Not bound\n\n"
                        "Use /bind <user_token> to bind your account."
                    )
                    return

                await update.message.reply_text(
                    f"✅ Account Status\n\n"
                    f"👤 User: {user.username}\n"
                    f"📱 Chat ID: {chat_id}\n"
                    f"🔗 Status: Bound\n"
                    f"🔔 Notifications: {'Enabled' if user.telegram_notifications_enabled else 'Disabled'}\n\n"
                    "Use /unbind to disconnect your account."
                )

            except Exception as e:
                logger.error(f"Error checking Telegram account status: {e}")
                await update.message.reply_text(
                    "❌ An error occurred while checking your account status.\n\n"
                    "Please try again later or contact support."
                )
                await db.rollback()

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "🎯 BountyGo Notification Bot Help\n\n"
            "Available commands:\n\n"
            "🔗 /bind <user_id>\n"
            "   Bind your BountyGo account to receive notifications\n\n"
            "🔓 /unbind\n"
            "   Unbind your account and stop notifications\n\n"
            "📊 /status\n"
            "   Check your account binding status\n\n"
            "❓ /help\n"
            "   Show this help message\n\n"
            "💡 To get your user ID:\n"
            "1. Open BountyGo app\n"
            "2. Go to Profile or Settings\n"
            "3. Copy your user ID (numeric)\n"
            "4. Use /bind <your_user_id> here\n\n"
            "Need help? Contact support in the BountyGo app."
        )

        await update.message.reply_text(help_message)

    async def unknown_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown messages"""
        await update.message.reply_text(
            "❓ I don't understand that command.\n\n"
            "Use /help to see available commands."
        )


# Global instance
telegram_bot_service = TelegramBotService()
