# BountyGo 通知系统文档

## 概述

BountyGo 通知系统提供了完整的任务提醒和通知功能，支持多种通知渠道和个性化设置。

## 功能特性

### 1. 任务提醒
- **3天前提醒**: 任务截止日期前3天发送提醒
- **1天前提醒**: 任务截止日期前1天发送提醒
- **2小时前提醒**: 任务截止日期前2小时发送最后提醒
- **自动调度**: 用户加入任务时自动安排提醒

### 2. 通知渠道
- **WebSocket**: 实时推送到前端/客户端
- **Telegram Bot**: 通过Telegram机器人发送消息
- **邮件通知**: 通过邮件发送（可扩展）

### 3. Telegram Bot 绑定流程
用户通过Telegram Bot的指令来绑定账号：

1. **启动Bot对话**
   ```
   /start - 显示欢迎消息和可用命令
   ```

2. **绑定账号**
   ```
   /bind <user_id> - 绑定BountyGo账号
   ```
   - 用户需要从BountyGo应用获取user_id（数字ID）
   - Bot验证用户ID有效性
   - 将Telegram chat_id与用户账号关联
   - 自动启用Telegram通知

3. **查看绑定状态**
   ```
   /status - 查看当前绑定状态
   ```

4. **解绑账号**
   ```
   /unbind - 解绑当前账号
   ```

5. **获取帮助**
   ```
   /help - 显示所有可用命令和使用说明
   ```

### 4. 个性化设置
- **提醒类型开关**: 可单独控制每种提醒类型
- **渠道偏好**: 可选择接收通知的渠道
- **免打扰时间**: 设置免打扰时间段
- **时区设置**: 支持不同时区

## API 端点

### 通知管理

#### 获取通知列表
```http
GET /api/v1/notifications/
```

查询参数:
- `page`: 页码 (默认: 1)
- `size`: 每页数量 (默认: 20)
- `status`: 通知状态筛选 (pending, sent, failed, cancelled)

#### 获取通知偏好设置
```http
GET /api/v1/notifications/preferences
```

#### 更新通知偏好设置
```http
PUT /api/v1/notifications/preferences
```

请求体示例:
```json
{
  "task_reminder_3d_enabled": true,
  "task_reminder_1d_enabled": true,
  "task_reminder_2h_enabled": true,
  "telegram_enabled": true,
  "websocket_enabled": true,
  "quiet_hours_start": 22,
  "quiet_hours_end": 8,
  "timezone": "Asia/Shanghai"
}
```

### Telegram 集成

#### 绑定 Telegram 账号
```http
POST /api/v1/notifications/telegram/bind
```

请求体:
```json
{
  "telegram_chat_id": "123456789",
  "telegram_username": "username"
}
```

#### 解绑 Telegram 账号
```http
DELETE /api/v1/notifications/telegram/unbind
```

#### 获取 Telegram 绑定状态
```http
GET /api/v1/notifications/telegram/status
```

### 任务管理

#### 获取我的任务列表
```http
GET /api/v1/tasks/my-todos
```

查询参数:
- `is_active`: 筛选活跃状态
- `task_status`: 筛选任务状态

#### 更新任务设置
```http
PUT /api/v1/tasks/my-todos/{todo_id}
```

请求体:
```json
{
  "remind_flags": {
    "t_3d": true,
    "t_1d": true,
    "ddl_2h": true
  },
  "is_active": true
}
```

#### 完成任务确认
```http
PUT /api/v1/tasks/{task_id}/complete
```

### WebSocket 连接

#### 连接 WebSocket
```
ws://localhost:8000/api/v1/ws/notifications?token=<access_token>
```

#### 消息格式

客户端发送:
```json
{
  "type": "ping"
}
```

服务器响应:
```json
{
  "type": "pong",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

任务提醒消息:
```json
{
  "type": "task_reminder",
  "task_id": 123,
  "task_title": "完成项目文档",
  "deadline": "2024-01-01T18:00:00Z",
  "reminder_type": "task_reminder_2h",
  "message": "任务即将在2小时后到期",
  "timestamp": "2024-01-01T16:00:00Z"
}
```

## Telegram Bot 设置

### 1. 创建 Bot
1. 在 Telegram 中找到 @BotFather
2. 发送 `/newbot` 命令
3. 按提示设置 Bot 名称和用户名
4. 获取 Bot Token

### 2. 配置环境变量
```bash
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

### 3. Bot 命令
- `/start` - 欢迎消息和设置说明
- `/bind <user_token>` - 绑定 BountyGo 账号
- `/unbind` - 解绑账号
- `/status` - 查看绑定状态
- `/help` - 帮助信息

### 4. 绑定流程
1. 用户在 BountyGo 应用中获取绑定 token
2. 在 Telegram 中向 Bot 发送 `/bind <token>`
3. 系统验证 token 并绑定账号
4. 开始接收任务提醒

## 部署配置

### 环境变量
```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# 通知设置
NOTIFICATION_BATCH_SIZE=100
NOTIFICATION_RETRY_DELAY=300
NOTIFICATION_MAX_RETRIES=3

# WebSocket 设置
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_MAX_CONNECTIONS_PER_USER=5

# 任务提醒设置
REMINDER_CHECK_INTERVAL=1800
REMINDER_ADVANCE_DAYS=7
```

### 后台服务
系统会自动启动以下后台服务:
- **通知调度器**: 每30秒检查并发送待发送的通知
- **任务提醒调度器**: 每小时检查并安排即将到期的任务提醒
- **Telegram Bot**: 处理 Telegram 消息和命令

## 数据库结构

### 通知表 (notifications)
- `id`: 通知ID
- `user_id`: 用户ID
- `task_id`: 任务ID (可选)
- `type`: 通知类型
- `channel`: 通知渠道
- `status`: 通知状态
- `title`: 通知标题
- `message`: 通知内容
- `scheduled_at`: 计划发送时间
- `sent_at`: 实际发送时间

### 用户通知偏好表 (user_notification_preferences)
- `user_id`: 用户ID
- `task_reminder_*_enabled`: 各种提醒开关
- `*_enabled`: 各渠道开关
- `quiet_hours_start/end`: 免打扰时间
- `timezone`: 时区设置

### 用户表扩展字段
- `telegram_chat_id`: Telegram 聊天ID
- `telegram_username`: Telegram 用户名
- `telegram_notifications_enabled`: Telegram 通知开关

## 使用示例

### 1. 用户加入任务
```python
# 用户加入任务时自动调度提醒
POST /api/v1/tasks/123/join
{
  "remind_flags": {
    "t_3d": true,
    "t_1d": true,
    "ddl_2h": true
  }
}
```

### 2. 设置通知偏好
```python
# 启用 Telegram 通知，设置免打扰时间
PUT /api/v1/notifications/preferences
{
  "telegram_enabled": true,
  "websocket_enabled": true,
  "quiet_hours_start": 22,
  "quiet_hours_end": 8,
  "timezone": "Asia/Shanghai"
}
```

### 3. 绑定 Telegram
```python
# 绑定 Telegram 账号
POST /api/v1/notifications/telegram/bind
{
  "telegram_chat_id": "123456789",
  "telegram_username": "myusername"
}
```

### 4. WebSocket 连接
```javascript
// 前端连接 WebSocket
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/notifications?token=' + accessToken);

ws.onmessage = function(event) {
  const notification = JSON.parse(event.data);
  if (notification.type === 'task_reminder') {
    showNotification(notification.title, notification.message);
  }
};
```

## 故障排除

### 常见问题
1. **Telegram Bot 无响应**: 检查 Bot Token 是否正确配置
2. **WebSocket 连接失败**: 确认 access token 有效且用户已认证
3. **提醒未发送**: 检查任务是否有截止时间，用户是否启用了相应提醒
4. **通知重复**: 检查后台调度器是否重复启动

### 日志查看
```bash
# 查看通知相关日志
grep "notification" /var/log/bountygo/app.log

# 查看 Telegram Bot 日志
grep "telegram" /var/log/bountygo/app.log

# 查看 WebSocket 日志
grep "websocket" /var/log/bountygo/app.log
```
