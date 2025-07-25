"""
API v1 router configuration
"""
from fastapi import APIRouter, HTTPException, status

# Import routers
from app.api.v1.auth import router as auth_router
from app.api.v1.endpoints import users, tasks, tags, analytics, url_agent

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth_router, prefix="/auth", tags=["🔐 Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["👤 Users"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["📋 Tasks"])
api_router.include_router(tags.router, prefix="/tags", tags=["🏷️ Tags"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["📊 Analytics"])
api_router.include_router(url_agent.router, prefix="/url-agent", tags=["🤖 URL Agent"])


@api_router.get("/", summary="API信息", tags=["ℹ️ System"])
async def api_info():
    """
    获取API基本信息
    
    - **返回**: API版本和状态信息
    """
    from app.core.config import settings
    
    info = {
        "message": "BountyGo API v1",
        "version": "1.0.0",
        "status": "active",
        "description": "AI-powered bounty task aggregation and matching platform",
        "features": [
            "用户认证和管理",
            "赏金任务发布和管理",
            "智能标签分类系统",
            "任务讨论和消息",
            "数据分析和统计",
            "Web3钱包集成",
            "AI驱动的URL内容提取",
            "智能任务信息解析"
        ],
        "endpoints": {
            "authentication": "/api/v1/auth",
            "users": "/api/v1/users",
            "tasks": "/api/v1/tasks",
            "tags": "/api/v1/tags",
            "analytics": "/api/v1/analytics",
            "url_agent": "/api/v1/url-agent"
        },
        "authentication": {
            "required_for": [
                "用户管理 (/api/v1/users/*)",
                "任务创建和修改",
                "个人分析数据",
                "标签兴趣配置",
                "URL处理和任务创建 (/api/v1/url-agent/process)",
                "性能指标查看 (/api/v1/url-agent/metrics)"
            ],
            "public_endpoints": [
                "任务列表和详情",
                "标签搜索",
                "系统统计",
                "最近活动",
                "URL信息提取 (/api/v1/url-agent/extract-info)",
                "文本内容分析 (/api/v1/url-agent/extract-from-content)",
                "服务状态查询 (/api/v1/url-agent/status)"
            ]
        }
    }
    
    # 开发环境添加测试信息
    if settings.is_development():
        dev_info = {
            "environment": "development",
            "test_user": settings.DEV_TEST_USER_EMAIL
        }
        
        if settings.is_dev_test_token_enabled():
            dev_info.update({
                "test_token": settings.get_dev_test_token(),
                "note": f"在开发环境下，可以使用 '{settings.get_dev_test_token()}' 作为Bearer token进行测试"
            })
        else:
            dev_info["note"] = "开发测试token未配置。请在环境变量中设置 DEV_TEST_TOKEN"
        
        info["development"] = dev_info
    
    return info


@api_router.get("/dev-auth", summary="开发环境认证说明", tags=["ℹ️ System"])
async def dev_auth_info():
    """
    开发环境认证说明
    
    - **返回**: 开发环境认证方式说明
    """
    from app.core.config import settings
    
    if not settings.is_development():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="此端点仅在开发环境可用"
        )
    
    if not settings.is_dev_test_token_enabled():
        return {
            "message": "开发环境认证说明",
            "status": "未配置",
            "note": "开发测试token未配置。请在环境变量中设置 DEV_TEST_TOKEN",
            "setup_instructions": [
                "1. 在 .env 文件中添加: DEV_TEST_TOKEN=your-test-token",
                "2. 重启应用程序",
                "3. 使用该token进行API测试"
            ]
        }
    
    test_token = settings.get_dev_test_token()
    return {
        "message": "开发环境认证说明",
        "status": "已配置",
        "test_token": test_token,
        "usage": {
            "header": f"Authorization: Bearer {test_token}",
            "curl_example": f"curl -H 'Authorization: Bearer {test_token}' http://localhost:8000/api/v1/users/me",
            "test_user": {
                "email": settings.DEV_TEST_USER_EMAIL,
                "nickname": settings.DEV_TEST_USER_NICKNAME,
                "note": "测试用户会自动创建"
            }
        },
        "protected_endpoints": [
            "/api/v1/users/me",
            "/api/v1/users/me/wallets",
            "/api/v1/analytics/me",
            "/api/v1/analytics/sponsor-dashboard",
            "/api/v1/tags/me/profile"
        ],
        "note": "使用测试token可以访问所有需要认证的端点，无需真实的Google OAuth流程"
    }