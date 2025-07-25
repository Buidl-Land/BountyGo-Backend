# 开发环境认证指南

## 概述

为了方便开发和测试，BountyGo后端提供了开发环境测试token功能，可以绕过Google OAuth流程直接进行API测试。

## 配置步骤

### 1. 设置环境变量

在 `.env` 文件中添加以下配置：

```bash
# 开发环境设置
ENVIRONMENT=development
DEBUG=true

# 开发测试token配置
DEV_TEST_TOKEN=your-custom-test-token
DEV_TEST_USER_EMAIL=dev@bountygo.com
DEV_TEST_USER_NICKNAME=开发测试用户
```

### 2. 使用示例配置

可以直接复制 `.env.dev` 文件的内容到 `.env` 文件：

```bash
cp .env.dev .env
```

## 使用方法

### 1. 检查配置状态

访问API信息端点查看开发环境配置：

```bash
curl http://localhost:8000/api/v1/
```

响应示例：
```json
{
  "message": "BountyGo API v1",
  "development": {
    "environment": "development",
    "test_token": "your-custom-test-token",
    "test_user": "dev@bountygo.com",
    "note": "在开发环境下，可以使用 'your-custom-test-token' 作为Bearer token进行测试"
  }
}
```

### 2. 获取详细认证信息

访问开发认证信息端点：

```bash
curl http://localhost:8000/api/v1/dev-auth
```

响应示例：
```json
{
  "message": "开发环境认证说明",
  "status": "已配置",
  "test_token": "your-custom-test-token",
  "usage": {
    "header": "Authorization: Bearer your-custom-test-token",
    "curl_example": "curl -H 'Authorization: Bearer your-custom-test-token' http://localhost:8000/api/v1/users/me",
    "test_user": {
      "email": "dev@bountygo.com",
      "nickname": "开发测试用户",
      "note": "测试用户会自动创建"
    }
  },
  "protected_endpoints": [
    "/api/v1/users/me",
    "/api/v1/users/me/wallets",
    "/api/v1/analytics/me",
    "/api/v1/analytics/sponsor-dashboard",
    "/api/v1/tags/me/profile"
  ]
}
```

### 3. 使用测试token访问API

使用测试token访问需要认证的端点：

```bash
# 获取当前用户信息
curl -H "Authorization: Bearer your-custom-test-token" \
     http://localhost:8000/api/v1/users/me

# 获取用户钱包列表
curl -H "Authorization: Bearer your-custom-test-token" \
     http://localhost:8000/api/v1/users/me/wallets

# 获取个人统计数据
curl -H "Authorization: Bearer your-custom-test-token" \
     http://localhost:8000/api/v1/analytics/me
```

## 错误提示改进

系统现在提供更精确的错误提示：

### 1. 缺少认证头
```json
{
  "detail": "缺少身份认证令牌。请在请求头中添加 'Authorization: Bearer <token>'。 开发环境可使用测试token: your-custom-test-token"
}
```

### 2. 空token
```json
{
  "detail": "访问令牌为空。请提供有效的Bearer token。"
}
```

### 3. 格式错误的token
```json
{
  "detail": "访问令牌格式错误。请检查前端是否正确传递token。"
}
```

### 4. 无效JWT格式
```json
{
  "detail": "访问令牌格式无效。请检查token是否完整且未被篡改。"
}
```

### 5. 过期token
```json
{
  "detail": "访问令牌已过期。请使用refresh token刷新令牌或重新登录。"
}
```

## 测试脚本

运行测试脚本验证认证系统：

```bash
# 运行认证系统测试
python scripts/test_auth_improvements.py

# 指定不同的API地址
python scripts/test_auth_improvements.py --url http://localhost:8000
```

## 安全注意事项

1. **仅限开发环境**: 测试token功能仅在 `ENVIRONMENT=development` 时启用
2. **生产环境禁用**: 生产环境会自动禁用此功能
3. **token安全**: 开发测试token应该定期更换，不要使用简单的值
4. **用户隔离**: 测试用户与真实用户完全隔离

## 故障排除

### 测试token不工作

1. 检查环境变量是否正确设置
2. 确认 `ENVIRONMENT=development`
3. 重启应用程序
4. 检查 `/api/v1/dev-auth` 端点的响应

### 无法访问开发端点

如果 `/api/v1/dev-auth` 返回404，说明：
- 应用程序不在开发环境运行
- `ENVIRONMENT` 变量未设置为 `development`

### 测试用户创建失败

检查数据库连接和权限，确保应用程序可以创建用户记录。

## 公开端点

以下端点无需认证即可访问：

- `GET /api/v1/tasks` - 任务列表
- `GET /api/v1/tasks/{id}` - 任务详情
- `GET /api/v1/tags` - 标签列表
- `GET /api/v1/tags/search` - 标签搜索
- `GET /api/v1/analytics/system` - 系统统计
- `GET /api/v1/analytics/popular-tags` - 热门标签
- `GET /api/v1/analytics/recent-activity` - 最近活动

## 需要认证的端点

以下端点需要提供有效的Bearer token：

- `GET /api/v1/users/me` - 当前用户信息
- `GET /api/v1/users/me/wallets` - 用户钱包列表
- `POST /api/v1/tasks` - 创建任务
- `PUT /api/v1/tasks/{id}` - 更新任务
- `GET /api/v1/analytics/me` - 个人统计
- `GET /api/v1/analytics/sponsor-dashboard` - 发布者仪表板
- `GET /api/v1/tags/me/profile` - 个人标签配置