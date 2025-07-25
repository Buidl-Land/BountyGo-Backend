#!/usr/bin/env python3
"""
BountyGo 通知系统测试脚本
"""
import asyncio
import json
import sys
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目路径
sys.path.append('.')

from app.core.database import get_db
from app.models.user import User
from app.models.task import Task, Todo
from app.models.notification import Notification, NotificationType, NotificationChannel
from app.services.notification import (
    notification_service,
    user_notification_preference_service,
    task_reminder_scheduler
)
from app.schemas.notification import (
    NotificationCreate,
    UserNotificationPreferenceCreate
)


async def create_test_data(db: AsyncSession):
    """创建测试数据"""
    print("🔧 创建测试数据...")

    # 创建测试用户
    test_user = User(
        email="test@example.com",
        nickname="测试用户",
        is_active=True
    )
    db.add(test_user)
    await db.flush()

    # 创建测试任务
    test_task = Task(
        title="测试任务",
        description="这是一个用于测试通知系统的任务",
        deadline=datetime.utcnow() + timedelta(hours=25),  # 25小时后到期
        sponsor_id=test_user.id,
        status="active"
    )
    db.add(test_task)
    await db.flush()

    # 创建待办事项
    test_todo = Todo(
        user_id=test_user.id,
        task_id=test_task.id,
        remind_flags='{"t_3d": true, "t_1d": true, "ddl_2h": true}',
        is_active=True
    )
    db.add(test_todo)

    await db.commit()

    print(f"✅ 创建测试用户: {test_user.id}")
    print(f"✅ 创建测试任务: {test_task.id}")
    print(f"✅ 创建待办事项: {test_todo.id}")

    return test_user, test_task, test_todo


async def test_notification_preferences(db: AsyncSession, user_id: int):
    """测试通知偏好设置"""
    print("\n📋 测试通知偏好设置...")

    # 获取用户偏好（会自动创建默认偏好）
    preferences = await user_notification_preference_service.get_user_preferences(db, user_id)
    print(f"✅ 获取用户偏好: {preferences.id}")

    # 更新偏好设置
    from app.schemas.notification import UserNotificationPreferenceUpdate
    update_data = UserNotificationPreferenceUpdate(
        telegram_enabled=True,
        websocket_enabled=True,
        quiet_hours_start=22,
        quiet_hours_end=8,
        timezone="Asia/Shanghai"
    )

    updated_preferences = await user_notification_preference_service.update_user_preferences(
        db, user_id, update_data
    )
    print(f"✅ 更新用户偏好: Telegram={updated_preferences.telegram_enabled}")

    return updated_preferences


async def test_task_reminder_scheduling(db: AsyncSession, task_id: int):
    """测试任务提醒调度"""
    print("\n⏰ 测试任务提醒调度...")

    # 调度任务提醒
    await task_reminder_scheduler.schedule_task_reminders(db, task_id)
    print(f"✅ 为任务 {task_id} 调度提醒")

    # 查询生成的通知
    from sqlalchemy import select
    result = await db.execute(
        select(Notification).where(Notification.task_id == task_id)
    )
    notifications = result.scalars().all()

    print(f"✅ 生成了 {len(notifications)} 个通知:")
    for notification in notifications:
        print(f"   - {notification.type.value} ({notification.channel.value}) - {notification.scheduled_at}")

    return notifications


async def test_manual_notification(db: AsyncSession, user_id: int, task_id: int):
    """测试手动创建通知"""
    print("\n📨 测试手动创建通知...")

    # 创建测试通知
    notification_data = NotificationCreate(
        user_id=user_id,
        task_id=task_id,
        type=NotificationType.NEW_MESSAGE,
        channel="websocket",
        title="测试通知",
        message="这是一条测试通知消息",
        scheduled_at=datetime.utcnow()
    )

    notification = await notification_service.create(db, notification_data)
    print(f"✅ 创建测试通知: {notification.id}")

    return notification


async def test_pending_notifications(db: AsyncSession):
    """测试获取待发送通知"""
    print("\n📤 测试获取待发送通知...")

    # 获取待发送的 WebSocket 通知
    pending_notifications = await notification_service.get_pending_notifications(
        db, channel="websocket", limit=10
    )

    print(f"✅ 找到 {len(pending_notifications)} 个待发送的 WebSocket 通知")

    for notification in pending_notifications:
        print(f"   - {notification.title} (计划时间: {notification.scheduled_at})")

        # 模拟发送成功
        await notification_service.mark_notification_sent(
            db, notification.id, "test_delivery_id"
        )
        print(f"   ✅ 标记通知 {notification.id} 为已发送")

    return pending_notifications


async def test_user_notifications(db: AsyncSession, user_id: int):
    """测试获取用户通知列表"""
    print("\n📋 测试获取用户通知列表...")

    notifications, total = await notification_service.get_user_notifications(
        db, user_id, page=1, size=10
    )

    print(f"✅ 用户有 {total} 个通知，当前页显示 {len(notifications)} 个")

    for notification in notifications:
        print(f"   - {notification.title} ({notification.status.value})")

    return notifications


async def cleanup_test_data(db: AsyncSession, user_id: int):
    """清理测试数据"""
    print("\n🧹 清理测试数据...")

    from sqlalchemy import delete

    # 删除通知
    await db.execute(delete(Notification).where(Notification.user_id == user_id))

    # 删除待办事项
    await db.execute(delete(Todo).where(Todo.user_id == user_id))

    # 删除任务
    await db.execute(delete(Task).where(Task.sponsor_id == user_id))

    # 删除用户偏好
    from app.models.notification import UserNotificationPreference
    await db.execute(delete(UserNotificationPreference).where(UserNotificationPreference.user_id == user_id))

    # 删除用户
    await db.execute(delete(User).where(User.id == user_id))

    await db.commit()
    print("✅ 测试数据清理完成")


async def main():
    """主测试函数"""
    print("🚀 开始测试 BountyGo 通知系统")
    print("=" * 50)

    async for db in get_db():
        try:
            # 1. 创建测试数据
            test_user, test_task, test_todo = await create_test_data(db)

            # 2. 测试通知偏好设置
            preferences = await test_notification_preferences(db, test_user.id)

            # 3. 测试任务提醒调度
            notifications = await test_task_reminder_scheduling(db, test_task.id)

            # 4. 测试手动创建通知
            manual_notification = await test_manual_notification(db, test_user.id, test_task.id)

            # 5. 测试获取待发送通知
            pending_notifications = await test_pending_notifications(db)

            # 6. 测试获取用户通知列表
            user_notifications = await test_user_notifications(db, test_user.id)

            print("\n" + "=" * 50)
            print("🎉 所有测试完成!")
            print(f"📊 测试结果:")
            print(f"   - 创建用户: 1")
            print(f"   - 创建任务: 1")
            print(f"   - 调度提醒: {len(notifications)}")
            print(f"   - 手动通知: 1")
            print(f"   - 待发送通知: {len(pending_notifications)}")
            print(f"   - 用户通知总数: {len(user_notifications)}")

            # 7. 清理测试数据
            await cleanup_test_data(db, test_user.id)

        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(main())
