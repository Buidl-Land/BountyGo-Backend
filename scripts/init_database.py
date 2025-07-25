#!/usr/bin/env python3
"""
初始化数据库脚本
创建所有必要的表结构
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """初始化数据库"""
    print("🔧 初始化数据库...")
    
    try:
        from app.core.database import engine
        from app.models.base import Base
        
        # Import all models to ensure they are registered
        from app.models.user import User, UserWallet, RefreshToken
        from app.models.tag import Tag, UserTagProfile
        from app.models.task import Task, TaskTag, Todo, Message, TaskView
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ 数据库表创建成功")
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False


async def test_user_creation():
    """测试用户创建"""
    print("\n🧪 测试用户创建...")
    
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.user import User
        from app.core.config import settings
        
        async with AsyncSessionLocal() as session:
            # 检查测试用户是否已存在
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.email == settings.DEV_TEST_USER_EMAIL)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"✅ 测试用户已存在: {existing_user.email}")
                return existing_user
            
            # 创建测试用户
            test_user = User(
                email=settings.DEV_TEST_USER_EMAIL,
                nickname=settings.DEV_TEST_USER_NICKNAME,
                google_id="dev_test_user_123",
                is_active=True
            )
            
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
            
            print(f"✅ 测试用户创建成功: {test_user.email} (ID: {test_user.id})")
            return test_user
            
    except Exception as e:
        print(f"❌ 用户创建测试失败: {e}")
        return None


async def main():
    """主函数"""
    print("🚀 BountyGo 数据库初始化")
    print("=" * 50)
    
    # 初始化数据库
    db_success = await init_database()
    if not db_success:
        print("❌ 数据库初始化失败，退出")
        return 1
    
    # 测试用户创建
    user = await test_user_creation()
    if not user:
        print("❌ 用户创建测试失败")
        return 1
    
    print("\n" + "=" * 50)
    print("🎉 数据库初始化完成！")
    print("现在可以启动应用程序并测试认证功能。")
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))