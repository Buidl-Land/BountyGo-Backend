"""
Database connection and session management utilities
"""
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from .config import settings

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    poolclass=NullPool if "pytest" in str(settings.DATABASE_URL) else None,  # Use NullPool for tests
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database connection and create tables if needed
    """
    try:
        # Import all models to ensure they are registered with SQLAlchemy
        from app.models import (
            User, UserWallet, RefreshToken,
            Tag, UserTagProfile,
            Task, TaskTag, Todo, Message, TaskView
        )
        
        # Test connection
        async with engine.begin() as conn:
            logger.info("Database connection established successfully")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """
    Close database connections
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


class DatabaseManager:
    """Database manager for handling connections and sessions"""
    
    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal
    
    async def health_check(self) -> bool:
        """
        Check database health
        
        Returns:
            bool: True if database is healthy
        """
        try:
            async with self.session_factory() as session:
                await session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def get_session(self) -> AsyncSession:
        """
        Get a new database session
        
        Returns:
            AsyncSession: Database session
        """
        return self.session_factory()


# Global database manager instance
db_manager = DatabaseManager()