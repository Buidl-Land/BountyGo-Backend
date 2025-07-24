# BountyGo Backend

🚀 AI-powered bounty task aggregation and matching platform backend service.

## � 项目概述

BountyGo是一个智能赏金任务聚合和匹配平台，解决Web3赏金生态系统中的碎片化问题。后端采用现代化的异步架构，提供高性能的API服务。

### 核心功能
- 🔐 JWT + Google OAuth 身份认证
- 👤 用户管理和Web3钱包集成
- 📋 赏金任务管理系统
- 🏷️ 智能标签分类系统
- 💬 任务讨论和消息系统
- 📊 用户行为分析和统计
- 🤖 AI驱动的任务推荐（规划中）

## 🛠️ 技术栈

- **框架**: FastAPI 0.104+ (异步Web框架)
- **数据库**: PostgreSQL 17+ (主数据库)
- **ORM**: SQLAlchemy 2.0 (异步ORM)
- **缓存**: Redis (会话和缓存)
- **认证**: JWT + Google OAuth
- **验证**: Pydantic v2 (数据验证)
- **迁移**: Alembic (数据库迁移)
- **服务器**: Uvicorn (ASGI服务器)

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd bountygo/backend

# 安装Python依赖
pip install -r requirements.txt

# 安装额外依赖
pip install psycopg2-binary email-validator python-jose[cryptography] redis[hiredis] structlog
```

### 2. 环境配置

确保 `.env` 文件包含正确的配置：

```env
# 应用配置
DEBUG=true
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development

# 数据库配置
DATABASE_URL=postgresql+asyncpg://username:password@host:port/database

# Redis配置
REDIS_URL=redis://host:port/db

# Google OAuth配置
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# CORS配置
ALLOWED_HOSTS=*
```

### 3. 数据库初始化和全面测试

运行全面测试脚本，它会自动完成数据库初始化、示例数据插入和所有功能测试：

```bash
# 运行全面测试（推荐）
python scripts/test_all.py
```

这个脚本会执行以下操作：
- ✅ 测试数据库连接
- ✅ 创建所有数据库表和索引
- ✅ 插入示例数据
- ✅ 验证模型和schemas
- ✅ 测试数据库查询
- ✅ 启动并测试API服务器

### 4. 启动应用程序

```bash
# 开发模式启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或者使用Python直接运行
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问API文档

启动成功后，访问以下地址：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc  
- **OpenAPI规范**: http://localhost:8000/openapi.json
- **健康检查**: http://localhost:8000/health

## 📊 数据库架构

### 核心表结构

| 表名 | 用途 | 主要字段 |
|------|------|----------|
| `users` | 用户信息 | id, email, nickname, google_id |
| `tags` | 系统标签 | id, name, category, usage_count |
| `tasks` | 赏金任务 | id, title, reward, sponsor_id, status |
| `user_wallets` | Web3钱包 | id, user_id, wallet_address |
| `user_tag_profiles` | 用户兴趣 | id, user_id, tag_id, weight |
| `task_tags` | 任务标签关联 | id, task_id, tag_id |
| `todos` | 用户待办 | id, user_id, task_id, remind_flags |
| `messages` | 任务讨论 | id, task_id, user_id, content |
| `task_views` | 浏览统计 | id, task_id, user_id, viewed_at |
| `refresh_tokens` | JWT令牌 | id, user_id, token_hash, expires_at |

### 性能优化

系统包含11个性能优化索引：
- 任务查询优化 (`idx_tasks_sponsor_status`)
- 用户数据优化 (`idx_todos_user_active`)
- 标签搜索优化 (`idx_tags_category`, `idx_tags_name`)
- 关联查询优化 (`idx_task_tags_*`, `idx_user_tag_profiles_*`)
- 分析统计优化 (`idx_task_views_*`, `idx_messages_task_created`)

## 🔌 API端点

### 认证相关
- `POST /api/v1/auth/google` - Google OAuth登录
- `POST /api/v1/auth/refresh` - 刷新JWT令牌
- `POST /api/v1/auth/logout` - 用户登出

### 用户管理
- `GET /api/v1/users/me` - 获取当前用户信息
- `PUT /api/v1/users/me` - 更新用户信息
- `POST /api/v1/users/wallets` - 添加钱包地址

### 任务管理
- `GET /api/v1/tasks` - 获取任务列表（支持筛选）
- `POST /api/v1/tasks` - 创建新任务
- `GET /api/v1/tasks/{id}` - 获取任务详情
- `PUT /api/v1/tasks/{id}` - 更新任务
- `DELETE /api/v1/tasks/{id}` - 删除任务

### 标签系统
- `GET /api/v1/tags` - 获取所有标签
- `POST /api/v1/tags` - 创建新标签
- `GET /api/v1/tags/search` - 搜索标签

### 系统监控
- `GET /health` - 健康检查
- `GET /docs` - API文档
- `GET /openapi.json` - OpenAPI规范

## 🧪 测试

### 全面测试
```bash
# 运行完整的系统测试
python scripts/test_all.py
```

### 单元测试
```bash
# 运行单元测试
pytest tests/ -v

# 运行测试并生成覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

### 手动测试API
```bash
# 健康检查
curl http://localhost:8000/health

# 获取API文档
curl http://localhost:8000/openapi.json
```

## 🏗️ 项目结构

```
backend/
├── app/                    # 应用程序代码
│   ├── api/v1/            # API路由
│   ├── core/              # 核心功能
│   ├── models/            # 数据库模型
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # 业务逻辑
│   └── main.py            # 应用程序入口
├── alembic/               # 数据库迁移
├── scripts/               # 工具脚本
│   └── test_all.py        # 全面测试脚本
├── tests/                 # 测试代码
├── requirements.txt       # Python依赖
├── .env                   # 环境变量
└── README.md             # 项目文档
```

## 🔧 开发指南

### 代码质量
```bash
# 代码格式化
black app/
isort app/

# 代码检查
flake8 app/
```

### 数据库迁移
```bash
# 生成新的迁移文件
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 添加新功能
1. 在 `app/models/` 中定义数据模型
2. 在 `app/schemas/` 中定义API schemas
3. 在 `app/services/` 中实现业务逻辑
4. 在 `app/api/v1/` 中添加API端点
5. 编写测试用例

## 🚢 部署

### Docker部署
```bash
# 构建和启动
docker-compose up -d

# 查看日志
docker-compose logs -f backend
```

### 生产环境
```bash
# 使用Gunicorn启动
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🔍 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查 `DATABASE_URL` 配置
   - 确认PostgreSQL服务运行正常
   - 验证网络连接

2. **模块导入错误**
   - 确认所有依赖已安装：`pip install -r requirements.txt`
   - 安装额外依赖：`pip install psycopg2-binary email-validator python-jose[cryptography] redis[hiredis] structlog`
   - 检查Python路径配置

3. **API启动失败**
   - 检查端口是否被占用
   - 查看详细错误日志
   - 验证环境变量配置

### 获取帮助

如果遇到问题：
1. 运行 `python scripts/test_all.py` 进行全面诊断
2. 检查应用程序日志
3. 查看API文档：http://localhost:8000/docs

## 📈 性能特性

- **异步架构**: 全异步处理，支持高并发
- **连接池**: 数据库连接池优化
- **缓存策略**: Redis缓存热点数据
- **索引优化**: 11个性能索引覆盖常用查询
- **类型安全**: 完整的类型提示和验证

## 🎯 下一步开发

- [ ] 实现AI推荐算法
- [ ] 添加实时通知系统
- [ ] 集成区块链支付
- [ ] 完善用户权限系统
- [ ] 添加数据分析面板

## 📄 许可证

MIT License

---

**🎉 BountyGo Backend - 让赏金任务管理更智能！**