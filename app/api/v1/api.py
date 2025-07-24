"""
API v1 router configuration
"""
from fastapi import APIRouter

# Import routers when they are created
# from app.api.v1.endpoints import auth, users, tasks, tags, analytics

api_router = APIRouter()

# Include endpoint routers when they are implemented
# api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
# api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
# api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


@api_router.get("/")
async def api_info():
    """API information endpoint"""
    return {
        "message": "BountyGo API v1",
        "version": "1.0.0",
        "status": "active"
    }