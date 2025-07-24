#!/usr/bin/env python3
"""
使用psycopg2进行数据库初始化
"""
import sys
import os
from pathlib import Path
from urllib.parse import urlparse

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

import psycopg2
import logging
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection_params():
    """获取数据库连接参数"""
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    parsed = urlparse(db_url)
    
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path[1:] if parsed.path else 'postgres',
        'user': parsed.username,
        'password': parsed.password
    }


def test_connection():
    """测试数据库连接"""
    try:
        logger.info("🔍 测试数据库连接...")
        
        conn_params = get_connection_params()
        logger.info(f"连接到: {conn_params['host']}:{conn_params['port']}")
        
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        logger.info(f"✅ 数据库连接成功!")
        logger.info(f"PostgreSQL版本: {version[:50]}...")
        
        # 检查现有表
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        if tables:
            logger.info("📋 现有表:")
            for table in tables:
                logger.info(f"  - {table[0]}")
        else:
            logger.info("📋 数据库中暂无表")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False


def create_tables():
    """创建数据库表"""
    try:
        logger.info("🔨 开始创建数据库表...")
        
        conn_params = get_connection_params()
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        # 创建扩展
        cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        cur.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
        logger.info("✅ 数据库扩展创建完成")
        
        # 创建用户表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                google_id VARCHAR(255) UNIQUE,
                email VARCHAR(255) UNIQUE NOT NULL,
                nickname VARCHAR(100) NOT NULL,
                avatar_url TEXT,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        logger.info("✅ users表创建完成")
        
        # 创建标签表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                category VARCHAR(50) NOT NULL,
                description TEXT,
                usage_count INTEGER NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        logger.info("✅ tags表创建完成")
        
        # 创建用户钱包表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_wallets (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                wallet_address VARCHAR(42) UNIQUE NOT NULL,
                wallet_type VARCHAR(20) NOT NULL DEFAULT 'ethereum',
                is_primary BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        logger.info("✅ user_wallets表创建完成")
        
        # 创建刷新令牌表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                is_revoked BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        logger.info("✅ refresh_tokens表创建完成")
        
        # 创建任务表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id BIGSERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                reward DECIMAL(18, 6),
                reward_currency VARCHAR(10) NOT NULL DEFAULT 'USD',
                deadline TIMESTAMPTZ,
                sponsor_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                external_link TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                view_count INTEGER NOT NULL DEFAULT 0,
                join_count INTEGER NOT NULL DEFAULT 0,
                has_escrow BOOLEAN NOT NULL DEFAULT false,
                escrow_amount DECIMAL(18, 6),
                escrow_token VARCHAR(42),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        logger.info("✅ tasks表创建完成")
        
        # 创建用户标签配置表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_tag_profiles (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                tag_id BIGINT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                weight DECIMAL(5, 4) NOT NULL DEFAULT 1.0,
                last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, tag_id)
            )
        """)
        logger.info("✅ user_tag_profiles表创建完成")
        
        # 创建任务标签关联表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS task_tags (
                id BIGSERIAL PRIMARY KEY,
                task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                tag_id BIGINT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(task_id, tag_id)
            )
        """)
        logger.info("✅ task_tags表创建完成")
        
        # 创建待办事项表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                remind_flags TEXT DEFAULT '{"t_3d": true, "t_1d": true, "ddl_2h": true}',
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, task_id)
            )
        """)
        logger.info("✅ todos表创建完成")
        
        # 创建消息表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL PRIMARY KEY,
                task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                is_deleted BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        logger.info("✅ messages表创建完成")
        
        # 创建任务浏览记录表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS task_views (
                id BIGSERIAL PRIMARY KEY,
                task_id BIGINT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                viewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        logger.info("✅ task_views表创建完成")
        
        # 创建性能索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_tasks_sponsor_status ON tasks(sponsor_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_todos_user_active ON todos(user_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_messages_task_created ON messages(task_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)",
            "CREATE INDEX IF NOT EXISTS idx_task_tags_task ON task_tags(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_tags_tag ON task_tags(tag_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_tag_profiles_user ON user_tag_profiles(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_tag_profiles_tag ON user_tag_profiles(tag_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_views_task ON task_views(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_task_views_user ON task_views(user_id)"
        ]
        
        for index_sql in indexes:
            cur.execute(index_sql)
        
        logger.info("✅ 性能索引创建完成")
        
        # 创建Alembic版本表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        """)
        
        # 插入版本记录
        cur.execute("""
            INSERT INTO alembic_version (version_num) 
            VALUES ('001') 
            ON CONFLICT (version_num) DO NOTHING
        """)
        logger.info("✅ Alembic版本表创建完成")
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("🎉 所有数据库表创建完成!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 创建表失败: {e}")
        return False


def insert_sample_data():
    """插入示例数据"""
    try:
        logger.info("📝 开始插入示例数据...")
        
        conn_params = get_connection_params()
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        # 插入示例标签
        sample_tags = [
            ("Python", "skill", "Python编程语言"),
            ("JavaScript", "skill", "JavaScript编程语言"),
            ("Web开发", "industry", "Web开发行业"),
            ("移动开发", "industry", "移动应用开发"),
            ("视频", "media", "视频内容"),
            ("文章", "media", "文字文章"),
            ("区块链", "industry", "区块链技术"),
            ("AI/ML", "skill", "人工智能和机器学习"),
        ]
        
        for name, category, description in sample_tags:
            cur.execute("""
                INSERT INTO tags (name, category, description) 
                VALUES (%s, %s, %s) 
                ON CONFLICT (name) DO NOTHING
            """, (name, category, description))
        
        logger.info("✅ 示例标签插入完成")
        
        # 插入示例用户
        cur.execute("""
            INSERT INTO users (email, nickname, google_id) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (email) DO UPDATE SET nickname = EXCLUDED.nickname
            RETURNING id
        """, ("test@bountygo.com", "测试用户", "test_google_123"))
        
        user_result = cur.fetchone()
        user_id = user_result[0] if user_result else None
        
        if not user_id:
            # 如果插入失败，尝试获取现有用户ID
            cur.execute("SELECT id FROM users WHERE email = %s", ("test@bountygo.com",))
            result = cur.fetchone()
            user_id = result[0] if result else None
        
        logger.info(f"✅ 示例用户插入完成 (ID: {user_id})")
        
        if user_id:
            # 插入示例任务
            cur.execute("""
                INSERT INTO tasks (title, description, reward, reward_currency, sponsor_id, external_link) 
                VALUES (%s, %s, %s, %s, %s, %s) 
                RETURNING id
            """, (
                "BountyGo平台测试任务", 
                "这是一个用于测试BountyGo平台功能的示例任务。请完成基本的功能测试。", 
                100.0, 
                "USD", 
                user_id, 
                "https://github.com/bountygo/test-task"
            ))
            
            task_result = cur.fetchone()
            task_id = task_result[0] if task_result else None
            logger.info(f"✅ 示例任务插入完成 (ID: {task_id})")
            
            if task_id:
                # 为任务添加标签
                cur.execute("SELECT id FROM tags WHERE name = %s", ("Python",))
                python_tag_result = cur.fetchone()
                python_tag_id = python_tag_result[0] if python_tag_result else None
                
                cur.execute("SELECT id FROM tags WHERE name = %s", ("Web开发",))
                web_tag_result = cur.fetchone()
                web_tag_id = web_tag_result[0] if web_tag_result else None
                
                if python_tag_id and web_tag_id:
                    cur.execute("""
                        INSERT INTO task_tags (task_id, tag_id) 
                        VALUES (%s, %s), (%s, %s)
                        ON CONFLICT (task_id, tag_id) DO NOTHING
                    """, (task_id, python_tag_id, task_id, web_tag_id))
                    logger.info("✅ 任务标签关联完成")
                
                # 为用户添加标签配置
                if python_tag_id and web_tag_id:
                    cur.execute("""
                        INSERT INTO user_tag_profiles (user_id, tag_id, weight) 
                        VALUES (%s, %s, %s), (%s, %s, %s)
                        ON CONFLICT (user_id, tag_id) DO UPDATE SET weight = EXCLUDED.weight
                    """, (user_id, python_tag_id, 0.9, user_id, web_tag_id, 0.8))
                    
                    logger.info("✅ 用户标签配置完成")
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("🎉 示例数据插入完成!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 插入示例数据失败: {e}")
        return False


def test_queries():
    """测试查询功能"""
    try:
        logger.info("🔍 开始测试数据库查询...")
        
        conn_params = get_connection_params()
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        # 测试用户查询
        cur.execute("SELECT id, email, nickname FROM users LIMIT 5")
        users = cur.fetchall()
        logger.info(f"👥 用户数量: {len(users)}")
        for user in users:
            logger.info(f"  - {user[2]} ({user[1]})")
        
        # 测试标签查询
        cur.execute("SELECT name, category FROM tags ORDER BY category, name")
        tags = cur.fetchall()
        logger.info(f"🏷️ 标签数量: {len(tags)}")
        for tag in tags:
            logger.info(f"  - {tag[0]} ({tag[1]})")
        
        # 测试任务查询
        cur.execute("""
            SELECT t.id, t.title, t.reward, t.reward_currency, u.nickname as sponsor
            FROM tasks t 
            JOIN users u ON t.sponsor_id = u.id 
            LIMIT 5
        """)
        tasks = cur.fetchall()
        logger.info(f"📋 任务数量: {len(tasks)}")
        for task in tasks:
            logger.info(f"  - {task[1]} (${task[2]} {task[3]}) by {task[4]}")
        
        # 测试复杂查询 - 带标签的任务
        cur.execute("""
            SELECT t.title, array_agg(tag.name) as tags
            FROM tasks t
            LEFT JOIN task_tags tt ON t.id = tt.task_id
            LEFT JOIN tags tag ON tt.tag_id = tag.id
            GROUP BY t.id, t.title
            LIMIT 3
        """)
        task_with_tags = cur.fetchall()
        logger.info("📋 任务及其标签:")
        for task in task_with_tags:
            tags_str = ", ".join(task[1]) if task[1] and task[1][0] else "无标签"
            logger.info(f"  - {task[0]}: {tags_str}")
        
        cur.close()
        conn.close()
        logger.info("✅ 数据库查询测试完成!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 查询测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("🚀 开始BountyGo数据库初始化和测试...")
    
    # 1. 测试连接
    if not test_connection():
        logger.error("数据库连接失败，请检查配置")
        return 1
    
    # 2. 创建表
    if not create_tables():
        logger.error("创建表失败")
        return 1
    
    # 3. 插入示例数据
    if not insert_sample_data():
        logger.error("插入示例数据失败")
        return 1
    
    # 4. 测试查询
    if not test_queries():
        logger.error("查询测试失败")
        return 1
    
    logger.info("🎉 BountyGo数据库初始化和测试完成!")
    logger.info("💡 你现在可以启动应用程序了: uvicorn app.main:app --reload")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)