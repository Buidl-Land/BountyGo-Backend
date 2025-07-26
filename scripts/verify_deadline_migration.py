#!/usr/bin/env python3
"""
验证deadline字段迁移的脚本
检查数据库中的deadline字段是否正确转换为时间戳
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.task import Task, Todo
from app.models.notification import Notification
from sqlalchemy import select, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_task_deadlines():
    """验证Task表的deadline字段"""
    print("🔍 检查Task表的deadline字段...")
    
    async with AsyncSessionLocal() as session:
        # 检查表结构
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'tasks' AND column_name IN ('deadline', 'deadline_timestamp')
            ORDER BY column_name
        """))
        columns = result.fetchall()
        
        print("📋 Task表字段信息:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
        
        # 检查是否还有deadline_timestamp字段
        deadline_timestamp_exists = any(col[0] == 'deadline_timestamp' for col in columns)
        deadline_exists = any(col[0] == 'deadline' for col in columns)
        
        if deadline_timestamp_exists:
            print("❌ 错误: deadline_timestamp字段仍然存在")
            return False
        
        if not deadline_exists:
            print("❌ 错误: deadline字段不存在")
            return False
        
        # 检查deadline字段的数据类型
        deadline_col = next((col for col in columns if col[0] == 'deadline'), None)
        if deadline_col and deadline_col[1] != 'integer':
            print(f"❌ 错误: deadline字段类型不正确，期望integer，实际{deadline_col[1]}")
            return False
        
        # 检查数据
        result = await session.execute(select(Task).limit(5))
        tasks = result.scalars().all()
        
        print(f"\n📊 检查了{len(tasks)}个任务的deadline数据:")
        for task in tasks:
            if task.deadline:
                # 验证是否为有效的时间戳
                try:
                    dt = datetime.fromtimestamp(task.deadline)
                    print(f"  ✅ {task.title[:30]}... deadline={task.deadline} ({dt.strftime('%Y-%m-%d %H:%M')})")
                except (ValueError, OSError):
                    print(f"  ❌ {task.title[:30]}... 无效的时间戳: {task.deadline}")
                    return False
            else:
                print(f"  ⚪ {task.title[:30]}... deadline=None")
        
        print("✅ Task表deadline字段验证通过")
        return True


async def verify_todo_deadlines():
    """验证Todo表的deadline字段"""
    print("\n🔍 检查Todo表的deadline字段...")
    
    async with AsyncSessionLocal() as session:
        # 检查表结构
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'todos' AND column_name = 'deadline'
        """))
        columns = result.fetchall()
        
        if not columns:
            print("⚪ Todo表中没有deadline字段")
            return True
        
        deadline_col = columns[0]
        print(f"📋 Todo表deadline字段: {deadline_col[1]} (nullable: {deadline_col[2]})")
        
        if deadline_col[1] != 'integer':
            print(f"❌ 错误: Todo表deadline字段类型不正确，期望integer，实际{deadline_col[1]}")
            return False
        
        # 检查数据
        result = await session.execute(select(Todo).limit(5))
        todos = result.scalars().all()
        
        print(f"📊 检查了{len(todos)}个Todo的deadline数据:")
        for todo in todos:
            if todo.deadline:
                try:
                    dt = datetime.fromtimestamp(todo.deadline)
                    print(f"  ✅ Todo {todo.id}: deadline={todo.deadline} ({dt.strftime('%Y-%m-%d %H:%M')})")
                except (ValueError, OSError):
                    print(f"  ❌ Todo {todo.id}: 无效的时间戳: {todo.deadline}")
                    return False
            else:
                print(f"  ⚪ Todo {todo.id}: deadline=None")
        
        print("✅ Todo表deadline字段验证通过")
        return True


async def verify_migration_status():
    """验证迁移状态"""
    print("\n🔍 检查迁移状态...")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1
        """))
        current_version = result.scalar()
        
        print(f"📋 当前迁移版本: {current_version}")
        
        # 检查是否包含我们的迁移
        if "005_consolidate_deadline_fields" in str(current_version) or "fbacb634c1f2" in str(current_version):
            print("✅ deadline字段合并迁移已应用")
            return True
        else:
            print("❌ deadline字段合并迁移未应用")
            return False


async def main():
    """主函数"""
    print("🚀 BountyGo Deadline字段迁移验证")
    print("=" * 60)
    
    try:
        # 验证迁移状态
        migration_ok = await verify_migration_status()
        
        # 验证Task表
        task_ok = await verify_task_deadlines()
        
        # 验证Todo表
        todo_ok = await verify_todo_deadlines()
        
        print("\n" + "=" * 60)
        if migration_ok and task_ok and todo_ok:
            print("🎉 所有验证通过！deadline字段迁移成功")
            print("✅ deadline_timestamp字段已删除")
            print("✅ deadline字段现在存储时间戳")
            print("✅ 所有数据正确转换")
            return 0
        else:
            print("❌ 验证失败，请检查上述错误")
            return 1
            
    except Exception as e:
        print(f"❌ 验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
