"""
Application middleware
"""
import time
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog

from app.core.exceptions import (
    BountyGoException,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ExternalServiceError
)

logger = structlog.get_logger(__name__)


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """Request/response logging middleware"""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None
    )
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=round(process_time, 4)
    )
    
    response.headers["X-Process-Time"] = str(process_time)
    return response


async def exception_handler(request: Request, exc: BountyGoException) -> JSONResponse:
    """Global exception handler for BountyGo exceptions"""
    logger.error(
        "Application exception",
        exception=exc.__class__.__name__,
        message=exc.message,
        details=exc.details,
        url=str(request.url)
    )
    
    status_code = 400
    if isinstance(exc, AuthenticationError):
        status_code = 401
    elif isinstance(exc, AuthorizationError):
        status_code = 403
    elif isinstance(exc, NotFoundError):
        status_code = 404
    elif isinstance(exc, ExternalServiceError):
        status_code = 502
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "timestamp": time.time(),
            "path": str(request.url.path)
        }
    )


async def security_headers_middleware(request: Request, call_next: Callable) -> Response:
    """Add security headers to responses"""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response