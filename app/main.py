"""
BountyGo Backend - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.redis import init_redis
from app.core.logging import configure_logging
from app.core.middleware import (
    logging_middleware,
    exception_handler,
    security_headers_middleware
)
from app.core.rate_limit import rate_limit_middleware
from app.core.health import get_system_health
from app.core.exceptions import BountyGoException
from app.api.v1.api import api_router

# Configure logging
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    try:
        await init_db()
        await init_redis()
    except Exception as e:
        # In test environment, we might not have DB/Redis running
        if not settings.DEBUG:
            raise e
    yield
    # Shutdown
    pass


app = FastAPI(
    title="BountyGo API",
    description="AI-powered bounty task aggregation and matching platform",
    version="1.0.0",
    lifespan=lifespan
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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return await get_system_health()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )