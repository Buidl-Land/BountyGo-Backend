#!/usr/bin/env python3
"""
Script to verify the backend setup is working correctly
"""
import sys
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def verify_setup():
    """Verify all components can be imported and initialized"""
    print("🔍 Verifying BountyGo Backend Setup...")
    
    try:
        # Test core imports
        print("✅ Testing core imports...")
        from app.core.config import settings
        from app.core.exceptions import BountyGoException
        from app.core.security import create_access_token
        from app.core.health import get_system_health
        
        # Test FastAPI app
        print("✅ Testing FastAPI app...")
        from app.main import app
        
        # Test API router
        print("✅ Testing API router...")
        from app.api.v1.api import api_router
        
        # Test models and schemas
        print("✅ Testing models and schemas...")
        from app.models.base import Base, BaseModel
        from app.schemas.base import BaseSchema, PaginationParams
        from app.services.base import BaseService
        
        # Test configuration
        print("✅ Testing configuration...")
        print(f"   - App Name: {settings.APP_NAME}")
        print(f"   - Environment: {settings.ENVIRONMENT}")
        print(f"   - Debug Mode: {settings.DEBUG}")
        print(f"   - Allowed Hosts: {settings.get_allowed_hosts()}")
        
        # Test token creation
        print("✅ Testing JWT token creation...")
        token = create_access_token("test-user")
        print(f"   - Token created: {token[:20]}...")
        
        # Test database and Redis connections (if available)
        try:
            print("✅ Testing database connection...")
            from app.core.database import init_db
            await init_db()
            print("   - Database connection successful")
        except Exception as e:
            print(f"   - Database connection failed (expected in CI): {e}")
        
        try:
            print("✅ Testing Redis connection...")
            from app.core.redis import init_redis
            await init_redis()
            print("   - Redis connection successful")
        except Exception as e:
            print(f"   - Redis connection failed (expected in CI): {e}")
        
        # Test health check
        print("✅ Testing health check...")
        health = await get_system_health()
        print(f"   - Health status: {health['status']}")
        
        print("\n🎉 All components verified successfully!")
        print("🚀 Backend setup is ready for development!")
        print("\nNext steps:")
        print("  1. Copy .env.example to .env and configure your settings")
        print("  2. Start services: docker-compose up -d")
        print("  3. Run migrations: alembic upgrade head")
        print("  4. Start development server: make dev")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_setup())
    sys.exit(0 if success else 1)