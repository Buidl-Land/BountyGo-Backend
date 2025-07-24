"""
Health check utilities
"""
from typing import Dict, Any
import asyncio
from datetime import datetime

from app.core.database import engine
from app.core.redis import get_redis
from app.core.config import settings


async def check_database_health() -> Dict[str, Any]:
    """Check database connection health"""
    try:
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            await result.fetchone()
        return {
            "status": "healthy",
            "response_time_ms": 0,  # Could add timing if needed
            "details": "Database connection successful"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "details": "Database connection failed"
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connection health"""
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        return {
            "status": "healthy",
            "response_time_ms": 0,  # Could add timing if needed
            "details": "Redis connection successful"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "details": "Redis connection failed"
        }


async def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status"""
    # Run health checks concurrently
    db_health, redis_health = await asyncio.gather(
        check_database_health(),
        check_redis_health(),
        return_exceptions=True
    )
    
    # Handle exceptions
    if isinstance(db_health, Exception):
        db_health = {
            "status": "unhealthy",
            "error": str(db_health),
            "details": "Database health check failed"
        }
    
    if isinstance(redis_health, Exception):
        redis_health = {
            "status": "unhealthy", 
            "error": str(redis_health),
            "details": "Redis health check failed"
        }
    
    # Determine overall status
    overall_status = "healthy"
    if db_health["status"] != "healthy" or redis_health["status"] != "healthy":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "service": settings.APP_NAME,
        "checks": {
            "database": db_health,
            "redis": redis_health
        }
    }