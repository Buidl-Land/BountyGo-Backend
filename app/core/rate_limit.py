"""
Rate limiting utilities using Redis
"""
import time
from typing import Optional
from fastapi import Request, HTTPException
import redis.asyncio as redis

from app.core.config import settings
from app.core.redis import get_redis


class RateLimiter:
    """Redis-based rate limiter"""
    
    def __init__(self, max_requests: int = None, window_seconds: int = 60):
        self.max_requests = max_requests or settings.RATE_LIMIT_PER_MINUTE
        self.window_seconds = window_seconds
    
    async def is_allowed(self, key: str) -> tuple[bool, dict]:
        """Check if request is allowed and return rate limit info"""
        try:
            redis_client = await get_redis()
            current_time = int(time.time())
            window_start = current_time - self.window_seconds
            
            # Use sliding window log approach
            pipe = redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, self.window_seconds)
            
            results = await pipe.execute()
            current_requests = results[1]
            
            # Check if limit exceeded
            allowed = current_requests < self.max_requests
            
            rate_limit_info = {
                "limit": self.max_requests,
                "remaining": max(0, self.max_requests - current_requests - 1),
                "reset": current_time + self.window_seconds,
                "retry_after": self.window_seconds if not allowed else None
            }
            
            return allowed, rate_limit_info
            
        except Exception:
            # If Redis is down, allow the request
            return True, {
                "limit": self.max_requests,
                "remaining": self.max_requests - 1,
                "reset": int(time.time()) + self.window_seconds,
                "retry_after": None
            }


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)
    
    # Get client identifier
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    rate_limit_key = f"rate_limit:{client_ip}:{hash(user_agent)}"
    
    # Check rate limit
    rate_limiter = RateLimiter()
    allowed, rate_info = await rate_limiter.is_allowed(rate_limit_key)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": str(rate_info["remaining"]),
                "X-RateLimit-Reset": str(rate_info["reset"]),
                "Retry-After": str(rate_info["retry_after"])
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])
    
    return response