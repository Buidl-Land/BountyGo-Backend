"""
WebSocket API端点
"""
from fastapi import APIRouter, WebSocket, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import authenticate_user_by_token
from app.models.user import User
from app.services.websocket import websocket_service

router = APIRouter()
security = HTTPBearer()


async def get_user_from_websocket_token(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db)
) -> User:
    """从WebSocket连接中获取用户信息"""
    try:
        # 从查询参数中获取token
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=4001, reason="Missing authentication token")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

        # 使用现有的认证函数验证token并获取用户
        user = await authenticate_user_by_token(token, db)

        if not user or not user.is_active:
            await websocket.close(code=4001, reason="User not found or inactive")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return user

    except Exception as e:
        await websocket.close(code=4000, reason=f"Authentication error: {str(e)}")
        raise


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket端点用于实时通知

    连接URL: ws://localhost:8000/api/v1/ws/notifications?token=<access_token>

    客户端可以发送以下消息类型:
    - {"type": "ping"} - 心跳检测
    - {"type": "mark_read", "notification_id": 123} - 标记通知为已读

    服务器会发送以下消息类型:
    - {"type": "pong"} - 心跳响应
    - {"type": "task_reminder", ...} - 任务提醒
    - {"type": "task_completed", ...} - 任务完成通知
    - {"type": "new_message", ...} - 新消息通知
    - {"type": "connection_established"} - 连接确认
    - {"type": "error", "message": "..."} - 错误消息
    """
    # 验证用户身份
    user = await get_user_from_websocket_token(websocket, db)

    # 处理WebSocket连接
    await websocket_service.handle_websocket(websocket, user)


@router.websocket("/test")
async def websocket_test(websocket: WebSocket):
    """
    WebSocket测试端点（无需认证）

    用于测试WebSocket连接是否正常工作
    """
    await websocket.accept()

    try:
        await websocket.send_text("WebSocket connection established successfully!")

        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")

    except Exception as e:
        print(f"WebSocket test error: {e}")
    finally:
        await websocket.close()
