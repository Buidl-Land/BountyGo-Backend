
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(
    title="BountyGo API",
    description="AI-powered bounty task aggregation and matching platform",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    """简化的健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "BountyGo Backend",
        "version": "1.0.0",
        "message": "API服务运行正常"
    }

@app.get("/")
async def root():
    """根端点"""
    return {"message": "Welcome to BountyGo API"}

@app.get("/api/v1/status")
async def api_status():
    """API状态端点"""
    return {
        "api_version": "v1",
        "status": "operational",
        "features": [
            "用户管理",
            "任务管理", 
            "标签系统",
            "AI推荐"
        ]
    }
