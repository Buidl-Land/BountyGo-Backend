"""
BountyGo Backend - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis import init_redis
from app.core.logging import configure_logging
import logging
from app.core.middleware import (
    logging_middleware,
    exception_handler,
    security_headers_middleware
)
from app.core.rate_limit import rate_limit_middleware
from app.core.health import check_health, check_basic_health, get_health_history
from app.core.exceptions import BountyGoException
from app.api.v1.api import api_router

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Database initialization failed: {e}")
        if not settings.DEBUG:
            raise e

    try:
        await init_redis()
        logger.info("✅ Redis initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Redis initialization failed: {e}")
        if not settings.DEBUG:
            raise e

    # Initialize Telegram Bot
    try:
        from app.services.telegram_bot import telegram_bot_service
        if settings.TELEGRAM_BOT_TOKEN:
            await telegram_bot_service.start_bot()
            logger.info("✅ Telegram Bot initialized successfully")
        else:
            logger.info("ℹ️ Telegram Bot token not configured, skipping initialization")
    except Exception as e:
        logger.warning(f"⚠️ Telegram Bot initialization failed: {e}")

    # Start background schedulers
    try:
        from app.services.scheduler import scheduler_manager
        await scheduler_manager.start_all()
        logger.info("✅ Background schedulers started successfully")
    except Exception as e:
        logger.warning(f"⚠️ Background schedulers failed to start: {e}")

    yield
    # Shutdown
    try:
        from app.services.scheduler import scheduler_manager
        await scheduler_manager.stop_all()
        logger.info("✅ Background schedulers stopped")
    except Exception as e:
        logger.warning(f"⚠️ Error stopping schedulers: {e}")

    try:
        from app.services.telegram_bot import telegram_bot_service
        await telegram_bot_service.stop_bot()
        logger.info("✅ Telegram Bot stopped")
    except Exception as e:
        logger.warning(f"⚠️ Error stopping Telegram Bot: {e}")

    try:
        await close_db()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.warning(f"⚠️ Error closing database: {e}")


app = FastAPI(
    title="🚀 BountyGo API",
    description="""
    ## AI-powered bounty task aggregation and matching platform

    BountyGo是一个智能赏金任务聚合和匹配平台，解决Web3赏金生态系统中的碎片化问题。

    ### 核心功能
    - 🔐 **身份认证**: JWT + Google OAuth + Web3钱包认证
    - 👤 **用户管理**: 用户资料、钱包地址管理
    - 📋 **任务管理**: 赏金任务发布、搜索、参与
    - 🏷️ **标签系统**: 智能分类和个性化推荐
    - 💬 **讨论系统**: 任务讨论和实时消息
    - 📊 **数据分析**: 用户行为分析和任务统计
    - 🤖 **AI代理**: 智能URL内容提取和任务信息解析
    - 🧠 **多智能体系统**: 智能协调、推荐引擎、图像解析
    - 🔔 **通知系统**: 实时通知、Telegram Bot集成
    - 🔌 **WebSocket**: 实时通信和状态同步

    ### 技术特性
    - ⚡ **异步架构**: 基于FastAPI的高性能异步API
    - 🗄️ **数据库**: PostgreSQL + SQLAlchemy 2.0 异步ORM
    - 🔒 **安全性**: JWT认证、CORS保护、请求限流
    - 📝 **数据验证**: Pydantic v2 完整类型验证
    - 🚀 **高性能**: Redis缓存、数据库连接池优化

    ### 开始使用
    1. 通过 `/api/v1/auth/google` 进行Google OAuth登录
    2. 使用 `/api/v1/users/me` 管理个人资料
    3. 通过 `/api/v1/tasks` 浏览和创建任务
    4. 使用 `/api/v1/tags` 管理标签和兴趣配置
    5. 通过 `/api/v1/multi-agent` 访问智能推荐和多智能体服务
    6. 使用 `/api/v1/notifications` 管理通知和提醒
    7. 通过 `/api/v1/ws` 建立WebSocket实时连接
    """,
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "BountyGo Team",
        "url": "https://bountygo.com",
        "email": "support@bountygo.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "开发环境"
        },
        {
            "url": "https://api.bountygo.com",
            "description": "生产环境"
        }
    ],
    tags_metadata=[
        {
            "name": "ℹ️ System",
            "description": "系统信息和健康检查"
        },
        {
            "name": "🔐 Authentication",
            "description": "用户认证和授权管理"
        },
        {
            "name": "👤 Users",
            "description": "用户资料和钱包管理"
        },
        {
            "name": "📋 Tasks",
            "description": "赏金任务管理和参与"
        },
        {
            "name": "🏷️ Tags",
            "description": "标签系统和兴趣配置"
        },
        {
            "name": "📊 Analytics",
            "description": "数据分析和统计报告"
        },
        {
            "name": "🤖 URL Agent",
            "description": "AI驱动的URL内容提取和任务信息解析"
        },
        {
            "name": "🧠 Multi-Agent",
            "description": "多智能体系统和协调服务"
        },
        {
            "name": "🔔 Notifications",
            "description": "通知系统和消息推送"
        },
        {
            "name": "🔌 WebSocket",
            "description": "WebSocket实时通信"
        }
    ]
)

# Exception handlers
app.add_exception_handler(BountyGoException, exception_handler)

# Middleware
app.middleware("http")(logging_middleware)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(security_headers_middleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_hosts(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", summary="基本健康检查", tags=["ℹ️ System"])
async def basic_health_check():
    """
    基本健康检查端点（快速响应）
    
    返回基本的系统状态信息，用于负载均衡器健康检查
    检查数据库连接、Redis连接等系统组件状态
    
    - **返回**: 基本健康状态信息
    """
    return await check_basic_health()


@app.get("/health/full", summary="完整健康检查", tags=["ℹ️ System"])
async def full_health_check():
    """
    完整健康检查端点
    
    检查所有系统组件的详细状态，包括数据库、Redis、Agent系统等
    
    - **返回**: 详细的系统健康状态信息
    """
    return await check_health()


@app.get("/health/history", summary="健康检查历史", tags=["ℹ️ System"])
async def health_check_history(limit: int = 10):
    """
    获取健康检查历史记录
    
    - **limit**: 返回记录数量限制（默认10条）
    - **返回**: 历史健康检查记录
    """
    return get_health_history(limit)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )