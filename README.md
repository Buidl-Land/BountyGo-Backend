# BountyGo Backend

🚀 AI-powered bounty task aggregation and matching platform backend service with intelligent URL parsing capabilities.

## 📖 项目概述

BountyGo是一个智能赏金任务聚合和匹配平台，解决Web3赏金生态系统中的碎片化问题。后端采用现代化的异步架构，集成了先进的AI技术，提供高性能的API服务和智能URL解析功能。

### 🎯 核心功能

#### 🤖 AI驱动的URL Agent（全新功能）
- **智能URL解析**: 自动从任何URL提取结构化任务信息
- **AI内容分析**: 使用PPIO模型智能识别任务标题、奖励、截止日期等
- **Playwright反爬虫**: 支持复杂JavaScript网站和社交媒体平台
- **多网站支持**: 支持GitHub、Twitter/X、任务众包平台等29+网站
- **实时处理**: 端到端处理时间< 15秒，高效稳定

#### 🖼️ 智能图片解析（新增功能）
- **视觉任务识别**: 从图片中智能提取任务信息
- **多格式支持**: 支持JPG、PNG、GIF、BMP、WebP等格式
- **PPIO视觉模型**: 使用先进的视觉语言模型进行图片分析
- **场景适配**: 支持任务截图、招聘海报、需求文档等多种场景
- **结构化输出**: 自动转换为标准JSON格式的任务信息

#### 🤝 多Agent协作系统（CAMEL-AI集成）
- **专业化分工**: 不同Agent负责不同专业领域（URL解析、图片分析、质量检查等）
- **CAMEL-AI Workforce**: 集成业界领先的多Agent协作框架
- **智能模型选择**: 根据任务类型自动选择最适合的AI模型
- **协作模式**: 支持Pipeline、Hierarchical、Workforce等多种协作模式
- **可配置架构**: 支持环境变量和代码配置两种方式

#### 🔐 身份认证与用户管理
- JWT + Google OAuth 身份认证
- 用户管理和Web3钱包集成
- 多钱包地址绑定支持

#### 📋 任务管理系统
- 赏金任务CRUD操作
- 智能任务推荐算法
- 任务状态跟踪和生命周期管理
- 任务浏览统计和分析

#### 🏷️ 智能标签系统
- 动态标签分类和管理
- 用户兴趣标签画像
- 标签权重算法优化

#### 💬 社交与交互
- 任务讨论和消息系统
- 用户行为分析和统计
- 实时通知机制

## 🛠️ 技术栈

### 后端框架
- **FastAPI 0.104+**: 高性能异步Web框架
- **Uvicorn**: ASGI服务器
- **Pydantic v2**: 数据验证和序列化

### 数据库与存储
- **PostgreSQL 17+**: 主数据库
- **SQLAlchemy 2.0**: 异步ORM
- **Alembic**: 数据库迁移工具
- **Redis**: 会话管理和缓存

### 🤖 AI与智能处理
- **PPIO模型**: 先进的AI语言模型，支持中英文和视觉理解
- **PPIO视觉模型**: 支持图片分析的多模态AI模型
- **CAMEL-AI**: 业界领先的多Agent协作框架，支持Workforce模块
- **Playwright**: 企业级网页自动化和反爬虫技术
- **BeautifulSoup4 + Readability**: 智能内容提取
- **Pillow (PIL)**: 图片处理和格式转换
- **异步处理**: 全异步AI推理和内容处理

### 安全与认证
- **JWT**: 无状态身份认证
- **Google OAuth**: 第三方登录
- **Python-JOSE**: 加密和签名

### 开发与测试
- **Pytest**: 单元测试和集成测试
- **Black + isort + flake8**: 代码质量工具
- **Structlog**: 结构化日志

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd BountyGo-Backend

# 创建虚拟环境（推荐）
conda create -n bountygo python=3.11
conda activate bountygo

# 或使用venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装Python依赖
pip install -r requirements.txt

# 可选：安装CAMEL-AI多Agent框架
pip install camel-ai  # 启用多Agent协作功能
```

### 2. 环境配置

创建 `.env` 文件并配置以下变量：

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

# 🤖 AI Agent配置（URL解析 + 图片解析 + 多Agent协作）
PPIO_API_KEY=your-ppio-api-key
PPIO_BASE_URL=https://api.ppinfra.com/v3/openai
PPIO_MODEL_NAME=moonshotai/kimi-k2-instruct

# 多Agent系统配置（可选）
MULTI_AGENT_FRAMEWORK=camel-ai
URL_PARSER_MODEL=qwen/qwen3-coder-480b-a35b-instruct
IMAGE_ANALYZER_MODEL=baidu/ernie-4.5-vl-28b-a3b
CONTENT_EXTRACTOR_MODEL=moonshotai/kimi-k2-instruct
TASK_CREATOR_MODEL=deepseek/deepseek-r1-0528
QUALITY_CHECKER_MODEL=qwen/qwen3-235b-a22b-instruct-2507

# CORS配置
ALLOWED_HOSTS=*
```

### 3. 🤖 URL Agent功能测试

验证AI驱动的URL解析功能：

```bash
# 激活环境
conda activate bountygo  # 或其他环境

# 测试URL Agent核心功能
python app/agent/test_integration.py

# 验证实现完整性
python app/agent/verify_implementation.py

# 测试真实URL解析（需要PPIO API密钥）
python -c "
import asyncio
from app.agent.service import URLAgentService

async def test():
    service = URLAgentService()
    result = await service.process_url('https://github.com/microsoft/vscode', user_id='test')
    if result.success:
        info = result.extracted_info
        print(f'标题: {info.title}')
        print(f'奖励: {info.reward} {info.reward_currency}')
        print(f'标签: {info.tags}')
    else:
        print(f'失败: {result.error_message}')

asyncio.run(test())
"
```

### 4. 数据库初始化和全面测试

```bash
# 运行全面系统测试
python scripts/test_all.py
```

这个脚本会执行：
- ✅ 测试数据库连接
- ✅ 创建所有数据库表和索引
- ✅ 插入示例数据
- ✅ 验证模型和schemas
- ✅ 测试数据库查询
- ✅ 启动并测试API服务器
- ✅ 测试URL Agent功能

### 5. 启动应用程序

```bash
# 开发模式启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或者使用Python直接运行
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 访问API文档

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

### 🤖 URL Agent相关（新增）
- `POST /api/v1/url-agent/extract-info` - 从URL提取任务信息
- `POST /api/v1/url-agent/process` - 完整URL处理+可选创建任务
- `POST /api/v1/url-agent/extract-from-content` - 从文本内容提取信息
- `GET /api/v1/url-agent/status` - 检查URL Agent服务状态
- `GET /api/v1/url-agent/metrics` - 获取处理性能指标
- `POST /api/v1/url-agent/reset-metrics` - 重置性能统计

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

## 🤖 URL Agent使用指南

### 基本用法

```python
# 方式一：直接使用Service类（推荐）
import asyncio
from app.agent.service import URLAgentService

async def parse_url():
    service = URLAgentService()
    result = await service.process_url(
        url="https://github.com/microsoft/vscode",
        user_id="user_123",
        auto_create=False  # 不自动创建任务，只提取信息
    )
    
    if result.success:
        info = result.extracted_info
        print(f"标题: {info.title}")
        print(f"奖励: {info.reward} {info.reward_currency}")
        print(f"截止日期: {info.deadline}")
        print(f"标签: {info.tags}")
        print(f"难度: {info.difficulty_level}")
        print(f"工时: {info.estimated_hours}小时")

asyncio.run(parse_url())
```

```python
# 方式二：使用Factory方法
from app.agent.factory import get_url_parsing_agent
from app.agent.playwright_extractor import PlaywrightContentExtractor

async def simple_parse():
    agent = get_url_parsing_agent()
    extractor = PlaywrightContentExtractor()
    
    try:
        # 提取网页内容
        web_content = await extractor.extract_content(url)
        # AI分析内容
        task_info = await agent.analyze_content(web_content)
        print(f"解析结果: {task_info.title}")
    finally:
        await extractor.close()
```

### API调用示例

```bash
# 使用curl测试URL解析
curl -X POST "http://localhost:8000/api/v1/url-agent/extract-info" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://github.com/microsoft/vscode"}'

# 完整处理（需要认证）
curl -X POST "http://localhost:8000/api/v1/url-agent/process" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://github.com/microsoft/vscode", "auto_create": false}'
```

### 支持的网站类型

#### ✅ 代码托管平台
- GitHub, GitLab, Bitbucket

#### ✅ 开发者社区  
- StackOverflow, Dev.to, HackerNoon

#### ✅ 任务平台
- DoraHacks, Gitcoin, Upwork, Freelancer

#### ✅ 社交媒体
- Twitter/X, Facebook, LinkedIn, Reddit

#### ✅ 博客平台
- Medium, Substack, Notion

### 性能特征
- **处理速度**: 平均10-15秒端到端处理
- **成功率**: GitHub等主流网站100%成功率
- **准确性**: AI信息提取准确率80%+
- **并发支持**: 异步处理，支持高并发

## 🧪 测试

### URL Agent专项测试
```bash
# 核心功能集成测试
python app/agent/test_integration.py

# 实现完整性验证
python app/agent/verify_implementation.py

# PPIO模型连接测试
python -m app.agent.test_connection

# 客户端功能测试
python -m app.agent.test_client
```

### 传统测试
```bash
# 全面系统测试
python scripts/test_all.py

# 单元测试
pytest tests/ -v

# 测试覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

### 手动API测试
```bash
# 健康检查
curl http://localhost:8000/health

# URL Agent状态检查
curl http://localhost:8000/api/v1/url-agent/status

# 获取API文档
curl http://localhost:8000/openapi.json
```

## 🏗️ 项目结构

```
BountyGo-Backend/
├── app/                        # 应用程序代码
│   ├── agent/                  # 🤖 URL Agent模块（新增）
│   │   ├── service.py          # URLAgentService主服务
│   │   ├── url_parsing_agent.py # AI解析代理
│   │   ├── playwright_extractor.py # Playwright内容提取
│   │   ├── client.py           # PPIO模型客户端
│   │   ├── config.py           # Agent配置管理
│   │   ├── factory.py          # 工厂方法
│   │   ├── models.py           # 数据模型
│   │   ├── test_integration.py # 集成测试
│   │   └── verify_implementation.py # 验证脚本
│   ├── api/v1/                 # API路由
│   │   └── endpoints/
│   │       └── url_agent.py    # URL Agent API端点
│   ├── core/                   # 核心功能
│   ├── models/                 # 数据库模型
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # 业务逻辑
│   └── main.py                 # 应用程序入口
├── alembic/                    # 数据库迁移
├── scripts/                    # 工具脚本
├── tests/                      # 测试代码
├── requirements.txt            # Python依赖
├── .env                        # 环境变量
└── README.md                   # 项目文档
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

### 添加新的URL Agent功能
1. 在 `app/agent/models.py` 中定义新的数据模型
2. 在 `app/agent/client.py` 中扩展AI客户端功能
3. 在 `app/agent/playwright_extractor.py` 中增强内容提取
4. 在 `app/api/v1/endpoints/url_agent.py` 中添加新API端点
5. 编写相应的测试用例

### URL Agent配置优化
```python
# 扩展支持的网站域名
# 在 app/agent/playwright_extractor.py 中修改
self.playwright_domains.add('new-website.com')

# 调整AI模型参数
# 在 app/agent/config.py 中配置
PPIO_MODEL_NAME=your-preferred-model
PPIO_MAX_TOKENS=4000
PPIO_TEMPERATURE=0.1
```

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

# 环境变量配置
export ENVIRONMENT=production
export DEBUG=false
export PPIO_API_KEY=your-production-api-key
```

## 🔍 故障排除

### URL Agent相关问题

1. **PPIO API连接失败**
   - 检查 `PPIO_API_KEY` 配置
   - 验证API密钥有效性：`python -m app.agent.test_connection`
   - 确认网络连接正常

2. **Playwright启动失败**
   - 安装浏览器：`playwright install chromium`
   - 检查系统依赖：`playwright install-deps`
   - 验证Playwright配置

3. **URL解析失败**
   - 检查目标网站是否在支持列表中
   - 查看详细错误日志
   - 测试网络连接：`curl -I target-url`

### 传统问题

1. **数据库连接失败**
   - 检查 `DATABASE_URL` 配置
   - 确认PostgreSQL服务运行正常
   - 验证网络连接

2. **模块导入错误**
   - 确认所有依赖已安装：`pip install -r requirements.txt`
   - 检查Python路径配置
   - 验证虚拟环境激活

3. **API启动失败**
   - 检查端口是否被占用
   - 查看详细错误日志
   - 验证环境变量配置

### 获取帮助

如果遇到问题：
1. 运行相应的测试脚本进行诊断
2. 检查应用程序日志
3. 查看API文档：http://localhost:8000/docs

## 📈 性能特性

### 🤖 AI驱动特性
- **智能解析**: PPIO模型支持复杂内容理解
- **反爬虫技术**: Playwright企业级网页自动化
- **异步处理**: 全异步AI推理，无阻塞
- **缓存优化**: 智能缓存解析结果

### 系统性能
- **异步架构**: 全异步处理，支持高并发
- **连接池**: 数据库连接池优化
- **缓存策略**: Redis缓存热点数据
- **索引优化**: 11个性能索引覆盖常用查询
- **类型安全**: 完整的类型提示和验证

### 性能指标
- **URL解析速度**: 10-15秒端到端处理
- **并发处理**: 支持100+并发请求
- **成功率**: 主流网站99%+成功率
- **AI准确率**: 信息提取准确率80%+

## 🎯 技术亮点

### 🚀 创新功能
- **多模态AI**: 结合内容提取和语言理解
- **渐进式等待**: 智能网页加载策略
- **反检测技术**: 规避自动化检测机制
- **结构化输出**: AI生成标准化数据结构

### 🔒 安全特性
- **URL验证**: 防止内网地址访问
- **内容过滤**: 安全的内容提取和清理
- **错误隔离**: 异常处理和服务降级
- **资源限制**: 内容长度和处理时间限制

### 🌐 兼容性
- **跨平台**: Linux, macOS, Windows
- **多浏览器**: Chromium内核
- **多语言**: 中英文内容理解
- **多格式**: HTML, JSON,纯文本

## 🛣️ 下一步开发

### 🤖 AI功能增强
- [ ] 多模型支持（GPT-4, Claude等）
- [ ] 图像内容理解
- [ ] 实时学习和优化
- [ ] 自定义提示词模板

### 🌐 网站支持扩展
- [ ] 更多任务平台集成
- [ ] 国际化网站支持
- [ ] 移动端网页适配
- [ ] API直接集成

### 🚀 系统优化
- [ ] 分布式处理
- [ ] 实时推送通知
- [ ] 高级缓存策略
- [ ] 性能监控面板

### 🔗 生态集成
- [ ] 区块链支付集成
- [ ] Web3身份验证
- [ ] DeFi协议集成
- [ ] NFT任务凭证

## 📚 API文档

完整的API使用文档请参考：

- **[URL Agent API 文档](./docs/URL_AGENT_API.md)** - URL解析和图片解析API
- **[多Agent系统配置指南](./docs/multi_agent_configuration.md)** - CAMEL-AI多Agent协作配置
- **[图片解析API 详细文档](./docs/image_parsing_api.md)** - 图片分析功能的完整说明

### 🎯 快速体验

```bash
# URL解析
curl -X POST "http://localhost:8000/api/v1/url-agent/extract-info" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/example/project"}'

# 图片解析
curl -X POST "http://localhost:8000/api/v1/url-agent/upload-image" \
  -F "file=@task_image.png" \
  -F "additional_prompt=请分析任务信息"

# 多Agent协作（Python示例）
python -c "
from app.agent.camel_workforce_service import create_camel_workforce_service
import asyncio

async def demo():
    service = create_camel_workforce_service(workforce_size=3)
    await service.initialize()
    result = await service.process_url_with_workforce('https://github.com/example/project')
    print(f'任务标题: {result.title}')

asyncio.run(demo())
"
```

## 📄 许可证

MIT License

---

**🎉 BountyGo Backend - AI驱动的智能赏金任务平台！**

集成了先进的URL解析、Playwright反爬虫、PPIO AI模型，为Web3赏金生态提供强大的技术支撑。