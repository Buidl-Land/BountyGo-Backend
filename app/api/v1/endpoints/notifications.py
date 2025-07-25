"""
通知管理API端点
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.notification import (
    Notification as NotificationSchema,
    NotificationList,
    UserNotificationPreference as UserNotificationPreferenceSchema,
    UserNotificationPreferenceUpdate,
    TelegramBindRequest,
    TelegramBindResponse,
    TelegramUnbindResponse
)
from app.schemas.base import SuccessResponse
from app.services.notification import (
    notification_service,
    user_notification_preference_service
)

router = APIRouter()


@router.get("/", response_model=NotificationList, summary="获取我的通知列表")
async def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="通知状态筛选")
):
    """
    获取当前用户的通知列表

    - **page**: 页码，从1开始
    - **size**: 每页数量，最大100
    - **status**: 通知状态 (pending, sent, failed, cancelled)
    """
    from app.models.notification import NotificationStatus

    notification_status = None
    if status:
        try:
            notification_status = NotificationStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的通知状态"
            )

    notifications, total = await notification_service.get_user_notifications(
        db, current_user.id, page, size, notification_status
    )

    return NotificationList(
        notifications=notifications,
        total=total,
        page=page,
        size=size,
        has_next=(page * size) < total,
        has_prev=page > 1
    )


@router.get("/preferences", response_model=UserNotificationPreferenceSchema, summary="获取通知偏好设置")
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的通知偏好设置
    """
    preferences = await user_notification_preference_service.get_user_preferences(
        db, current_user.id
    )
    return preferences


@router.put("/preferences", response_model=UserNotificationPreferenceSchema, summary="更新通知偏好设置")
async def update_notification_preferences(
    preferences_update: UserNotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新当前用户的通知偏好设置

    - **task_reminder_3d_enabled**: 是否启用3天前提醒
    - **task_reminder_1d_enabled**: 是否启用1天前提醒
    - **task_reminder_2h_enabled**: 是否启用2小时前提醒
    - **telegram_enabled**: 是否启用Telegram通知
    - **websocket_enabled**: 是否启用WebSocket通知
    - **email_enabled**: 是否启用邮件通知
    - **quiet_hours_start**: 免打扰开始时间 (0-23)
    - **quiet_hours_end**: 免打扰结束时间 (0-23)
    - **timezone**: 时区设置
    """
    preferences = await user_notification_preference_service.update_user_preferences(
        db, current_user.id, preferences_update
    )
    return preferences


@router.post("/telegram/bind", response_model=TelegramBindResponse, summary="绑定Telegram账号")
async def bind_telegram(
    bind_request: TelegramBindRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    绑定Telegram账号以接收通知

    - **telegram_chat_id**: Telegram聊天ID
    - **telegram_username**: Telegram用户名（可选）
    """
    try:
        # 更新用户的Telegram信息
        current_user.telegram_chat_id = bind_request.telegram_chat_id
        current_user.telegram_username = bind_request.telegram_username
        current_user.telegram_notifications_enabled = True

        await db.commit()
        await db.refresh(current_user)

        # 同时启用Telegram通知偏好
        preferences = await user_notification_preference_service.get_user_preferences(
            db, current_user.id
        )
        preferences.telegram_enabled = True
        await db.commit()

        return TelegramBindResponse(
            success=True,
            message="Telegram账号绑定成功",
            telegram_chat_id=current_user.telegram_chat_id,
            telegram_username=current_user.telegram_username
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"绑定失败: {str(e)}"
        )


@router.delete("/telegram/unbind", response_model=TelegramUnbindResponse, summary="解绑Telegram账号")
async def unbind_telegram(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    解绑Telegram账号
    """
    try:
        # 清除用户的Telegram信息
        current_user.telegram_chat_id = None
        current_user.telegram_username = None
        current_user.telegram_notifications_enabled = False

        await db.commit()

        # 同时禁用Telegram通知偏好
        preferences = await user_notification_preference_service.get_user_preferences(
            db, current_user.id
        )
        preferences.telegram_enabled = False
        await db.commit()

        return TelegramUnbindResponse(
            success=True,
            message="Telegram账号解绑成功"
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解绑失败: {str(e)}"
        )


@router.get("/telegram/status", response_model=dict, summary="获取Telegram绑定状态")
async def get_telegram_status(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的Telegram绑定状态
    """
    return {
        "is_bound": bool(current_user.telegram_chat_id),
        "telegram_chat_id": current_user.telegram_chat_id,
        "telegram_username": current_user.telegram_username,
        "notifications_enabled": current_user.telegram_notifications_enabled
    }


@router.post("/test", response_model=SuccessResponse, summary="发送测试通知")
async def send_test_notification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    发送测试通知以验证设置
    """
    from datetime import datetime
    from app.models.notification import NotificationType, NotificationChannel
    from app.schemas.notification import NotificationCreate

    try:
        # 直接创建通知对象
        from app.models.notification import Notification
        test_notification = Notification(
            user_id=current_user.id,
            type="new_message",
            channel="websocket",
            status="pending",
            title="测试通知",
            message="这是一条测试通知，用于验证您的通知设置是否正常工作。",
            scheduled_at=datetime.utcnow()
        )

        db.add(test_notification)
        await db.commit()
        await db.refresh(test_notification)

        return SuccessResponse(message="测试通知已发送")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送测试通知失败: {str(e)}"
        )
