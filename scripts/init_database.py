#!/usr/bin/env python3
"""
Database initialization script
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import init_db, close_db
from app.models import (
    User, UserWallet, RefreshToken,
    Tag, UserTagProfile,
    Task, TaskTag, Todo, Message, TaskView
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """Test database connection"""
    try:
        logger.info("Testing database connection...")
        await init_db()
        logger.info("✅ Database connection successful!")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
    finally:
        await close_db()


async def create_sample_data():
    """Create sample data for testing"""
    from app.core.database import get_db
    
    try:
        logger.info("Creating sample data...")
        
        async for db in get_db():
            # Create sample tags
            sample_tags = [
                Tag(name="Python", category="skill", description="Python programming language"),
                Tag(name="JavaScript", category="skill", description="JavaScript programming language"),
                Tag(name="Web Development", category="industry", description="Web development industry"),
                Tag(name="Mobile Development", category="industry", description="Mobile app development"),
                Tag(name="Video", category="media", description="Video content"),
                Tag(name="Article", category="media", description="Written articles"),
            ]
            
            for tag in sample_tags:
                db.add(tag)
            
            await db.commit()
            logger.info("✅ Sample tags created!")
            
            # Create sample user
            sample_user = User(
                email="test@example.com",
                nickname="Test User",
                google_id="test_google_id"
            )
            db.add(sample_user)
            await db.commit()
            await db.refresh(sample_user)
            logger.info("✅ Sample user created!")
            
            # Create sample task
            sample_task = Task(
                title="Sample Bounty Task",
                description="This is a sample bounty task for testing",
                reward=100.0,
                reward_currency="USD",
                sponsor_id=sample_user.id,
                external_link="https://example.com"
            )
            db.add(sample_task)
            await db.commit()
            logger.info("✅ Sample task created!")
            
            break
            
    except Exception as e:
        logger.error(f"❌ Failed to create sample data: {e}")
        raise


async def main():
    """Main function"""
    logger.info("🚀 Starting database initialization...")
    
    # Test connection
    if not await test_database_connection():
        logger.error("Database connection failed. Please check your configuration.")
        sys.exit(1)
    
    # Create sample data if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--sample-data":
        await create_sample_data()
    
    logger.info("✅ Database initialization completed!")


if __name__ == "__main__":
    asyncio.run(main())