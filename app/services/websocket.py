"""
WebSocket service for real-time notifications
"""
import json
import asyncio
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationChannel
from app.models.user import User
from app.services.notification import notification_service
from app.schemas.notification import (
    WebSocketMessage,
    TaskReminderMessage,
    TaskCompletedMessage,
    NewMessageNotification
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        # Store active connections: user_id -> set of websockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Store websocket to user mapping for cleanup
        self.websocket_users: Dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a new WebSocket connection"""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()

        self.active_connections[user_id].add(websocket)
        self.websocket_users[websocket] = user_id

        logger.info(f"User {user_id} connected via WebSocket")

        # Send connection confirmation
        await self.send_personal_message(
            user_id,
            {
                "type": "connection_established",
                "message": "Connected to BoutyGo notifications",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        user_id = self.websocket_users.get(websocket)
        if user_id:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            del self.websocket_users[websocket]
            logger.info(f"User {user_id} disconnected from WebSocket")

    async def send_personal_message(self, user_id: int, message: Dict[str, Any]):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            disconnected_websockets = []

            for websocket in self.active_connections[user_id].copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected_websockets.append(websocket)

            # Clean up disconnected websockets
            for websocket in disconnected_websockets:
                self.disconnect(websocket)

    async def send_broadcast(self, message: Dict[str, Any]):
        """Send message to all connected users"""
        disconnected_websockets = []

        for user_id, websockets in self.active_connections.items():
            for websocket in websockets.copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    disconnected_websockets.append(websocket)

        # Clean up disconnected websockets
        for websocket in disconnected_websockets:
            self.disconnect(websocket)

    def get_connected_users(self) -> Set[int]:
        """Get set of currently connected user IDs"""
        return set(self.active_connections.keys())

    def is_user_connected(self, user_id: int) -> bool:
        """Check if user is currently connected"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


class WebSocketNotificationSender:
    """Service for sending notifications via WebSocket"""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def send_pending_notifications(self, db: AsyncSession):
        """Send all pending WebSocket notifications"""
        # Get pending WebSocket notifications
        notifications = await notification_service.get_pending_notifications(
            db, channel="websocket"
        )

        # 只在有通知时才记录日志
        if notifications:
            logger.info(f"Found {len(notifications)} pending WebSocket notifications")

        for notification in notifications:
            await self._send_notification(db, notification)

    async def _send_notification(self, db: AsyncSession, notification: Notification):
        """Send a single notification via WebSocket"""
        try:
            # Check if user is connected
            if not self.connection_manager.is_user_connected(notification.user_id):
                logger.info(f"User {notification.user_id} not connected, skipping WebSocket notification")
                # Mark as failed but don't retry (user not online)
                await notification_service.mark_notification_failed(
                    db, notification.id, "User not connected"
                )
                return

            # Create WebSocket message based on notification type
            message = self._create_websocket_message(notification)

            # Send message
            await self.connection_manager.send_personal_message(
                notification.user_id, message
            )

            # Mark as sent
            await notification_service.mark_notification_sent(
                db, notification.id, "websocket_sent"
            )

            logger.info(f"WebSocket notification {notification.id} sent to user {notification.user_id}")

        except Exception as e:
            logger.error(f"Error sending WebSocket notification {notification.id}: {e}")
            await notification_service.mark_notification_failed(
                db, notification.id, str(e)
            )

    def _create_websocket_message(self, notification: Notification) -> Dict[str, Any]:
        """Create WebSocket message from notification"""
        base_message = {
            "id": notification.id,
            "type": notification.type.value,
            "title": notification.title,
            "message": notification.message,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Add task-specific data if available
        if notification.task:
            base_message.update({
                "task_id": notification.task.id,
                "task_title": notification.task.title,
                "task_deadline": notification.task.deadline.isoformat() if notification.task.deadline else None
            })

        return base_message

    async def send_task_reminder(
        self,
        user_id: int,
        task_id: int,
        task_title: str,
        deadline: int,
        reminder_type: str,
        message: str
    ):
        """Send task reminder via WebSocket"""
        if self.connection_manager.is_user_connected(user_id):
            reminder_message = TaskReminderMessage(
                task_id=task_id,
                task_title=task_title,
                deadline=deadline,
                reminder_type=reminder_type,
                message=message,
                timestamp=datetime.utcnow()
            )

            await self.connection_manager.send_personal_message(
                user_id, reminder_message.model_dump()
            )

    async def send_task_completed(
        self,
        user_id: int,
        task_id: int,
        task_title: str,
        message: str
    ):
        """Send task completed notification via WebSocket"""
        if self.connection_manager.is_user_connected(user_id):
            completed_message = TaskCompletedMessage(
                task_id=task_id,
                task_title=task_title,
                message=message,
                timestamp=datetime.utcnow()
            )

            await self.connection_manager.send_personal_message(
                user_id, completed_message.model_dump()
            )

    async def send_new_message_notification(
        self,
        user_id: int,
        task_id: int,
        task_title: str,
        message_id: int,
        sender_name: str,
        message_preview: str
    ):
        """Send new message notification via WebSocket"""
        if self.connection_manager.is_user_connected(user_id):
            new_message = NewMessageNotification(
                task_id=task_id,
                task_title=task_title,
                message_id=message_id,
                sender_name=sender_name,
                message_preview=message_preview,
                timestamp=datetime.utcnow()
            )

            await self.connection_manager.send_personal_message(
                user_id, new_message.model_dump()
            )


class WebSocketService:
    """Main WebSocket service"""

    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.notification_sender = WebSocketNotificationSender(self.connection_manager)

    async def handle_websocket(self, websocket: WebSocket, user: User):
        """Handle WebSocket connection lifecycle"""
        await self.connection_manager.connect(websocket, user.id)

        try:
            while True:
                # Keep connection alive and handle incoming messages
                data = await websocket.receive_text()

                # Parse incoming message
                try:
                    message = json.loads(data)
                    await self._handle_incoming_message(websocket, user, message)
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.utcnow().isoformat()
                    }))

        except WebSocketDisconnect:
            logger.info(f"User {user.id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error for user {user.id}: {e}")
        finally:
            self.connection_manager.disconnect(websocket)

    async def _handle_incoming_message(self, websocket: WebSocket, user: User, message: Dict[str, Any]):
        """Handle incoming WebSocket messages from client"""
        message_type = message.get("type")

        if message_type == "ping":
            # Respond to ping with pong
            await websocket.send_text(json.dumps({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            }))

        elif message_type == "mark_read":
            # Mark notification as read
            notification_id = message.get("notification_id")
            if notification_id:
                # Here you could implement marking notifications as read
                await websocket.send_text(json.dumps({
                    "type": "notification_marked_read",
                    "notification_id": notification_id,
                    "timestamp": datetime.utcnow().isoformat()
                }))

        else:
            # Unknown message type
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "timestamp": datetime.utcnow().isoformat()
            }))


# Global instances
websocket_service = WebSocketService()
connection_manager = websocket_service.connection_manager
websocket_notification_sender = websocket_service.notification_sender
