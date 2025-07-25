#!/usr/bin/env python3
"""
数据库连接测试脚本
诊断和修复数据库连接问题
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """测试数据库连接"""
    print("🔍 测试数据库连接...")
    
    try:
        from app.core.config import settings
        print(f"数据库URL: {settings.DATABASE_URL}")
        
        # 测试基本连接
        from sqlalchemy.ext.asyncio import create_async_engine
        
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_size=1,
            max_overflow=0
        )
        
        async with engine.begin() as conn:
            from sqlalchemy import text
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ 数据库连接成功: {row}")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


async def test_app_database():
    """测试应用程序数据库配置"""
    print("\n🔍 测试应用程序数据库配置...")
    
    try:
        from app.core.database import db_manager
        
        health = await db_manager.health_check()
        if health:
            print("✅ 应用程序数据库健康检查通过")
            return True
        else:
            print("❌ 应用程序数据库健康检查失败")
            return False
            
    except Exception as e:
        print(f"❌ 应用程序数据库测试失败: {e}")
        return False


def suggest_local_database():
    """建议本地数据库配置"""
    print("\n💡 建议使用本地数据库配置:")
    print("1. 使用Docker启动本地PostgreSQL:")
    print("   docker run --name bountygo-postgres -e POSTGRES_PASSWORD=bountygo123 -e POSTGRES_DB=bountygo -p 5432:5432 -d postgres:15")
    print()
    print("2. 更新.env文件中的DATABASE_URL:")
    print("   DATABASE_URL=postgresql+asyncpg://postgres:bountygo123@localhost:5432/bountygo")
    print()
    print("3. 或者使用SQLite (仅用于开发):")
    print("   DATABASE_URL=sqlite+aiosqlite:///./bountygo.db")


def create_local_env_config():
    """创建本地环境配置"""
    print("\n🔧 创建本地数据库配置...")
    
    backend_dir = Path(__file__).parent.parent
    env_file = backend_dir / ".env"
    
    # 读取现有配置
    if env_file.exists():
        content = env_file.read_text(encoding='utf-8')
        
        # 替换数据库URL为本地SQLite
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('DATABASE_URL='):
                lines[i] = 'DATABASE_URL=sqlite+aiosqlite:///./bountygo.db'
                break
        
        # 写回文件
        env_file.write_text('\n'.join(lines), encoding='utf-8')
        print("✅ 已更新.env文件使用本地SQLite数据库")
        return True
    else:
        print("❌ .env文件不存在")
        return False


async def test_sqlite_connection():
    """测试SQLite连接"""
    print("\n🔍 测试SQLite连接...")
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        
        sqlite_url = "sqlite+aiosqlite:///./bountygo.db"
        engine = create_async_engine(sqlite_url, echo=False)
        
        async with engine.begin() as conn:
            from sqlalchemy import text
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ SQLite连接成功: {row}")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ SQLite连接失败: {e}")
        return False


async def main():
    """主函数"""
    print("🚀 BountyGo 数据库连接诊断")
    print("=" * 50)
    
    # 测试当前数据库连接
    db_success = await test_database_connection()
    
    if not db_success:
        print("\n⚠️  当前数据库连接失败，可能的原因:")
        print("1. 网络连接问题")
        print("2. 数据库服务器不可达")
        print("3. 认证信息错误")
        
        suggest_local_database()
        
        # 询问是否切换到本地SQLite
        try:
            choice = input("\n是否切换到本地SQLite数据库? (y/n): ").lower().strip()
            if choice in ['y', 'yes']:
                if create_local_env_config():
                    print("\n重新测试SQLite连接...")
                    sqlite_success = await test_sqlite_connection()
                    if sqlite_success:
                        print("\n✅ 本地SQLite数据库配置成功!")
                        print("现在可以重启应用程序并测试认证功能。")
                    else:
                        print("\n❌ SQLite配置失败")
        except KeyboardInterrupt:
            print("\n操作取消")
    else:
        # 测试应用程序数据库
        app_success = await test_app_database()
        if app_success:
            print("\n✅ 数据库配置完全正常!")
        else:
            print("\n⚠️  应用程序数据库配置有问题")


if __name__ == "__main__":
    asyncio.run(main())