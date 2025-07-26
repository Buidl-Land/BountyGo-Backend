#!/usr/bin/env python3
"""
完整的数据库设置脚本
包含迁移、初始化和种子数据
"""
import asyncio
import sys
import subprocess
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_command(command: str, description: str) -> bool:
    """运行命令并返回是否成功"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        print(f"✅ {description}成功")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}失败: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


async def run_python_script(script_path: str, description: str) -> bool:
    """运行Python脚本"""
    print(f"\n🔧 {description}...")
    try:
        # Import and run the script
        if "init_database" in script_path:
            from scripts.init_database import main
            result = await main()
            return result == 0
        elif "simple_seed" in script_path:
            from scripts.simple_seed import insert_test_data
            await insert_test_data()
            return True
        elif "seed_tasks" in script_path:
            from scripts.seed_tasks import main
            await main()
            return True
        else:
            print(f"❌ 未知的脚本: {script_path}")
            return False
    except Exception as e:
        print(f"❌ {description}失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("🚀 BountyGo 数据库完整设置")
    print("=" * 60)
    print("这个脚本将执行以下操作:")
    print("1. 运行数据库迁移 (alembic upgrade)")
    print("2. 初始化数据库表结构")
    print("3. 创建测试用户")
    print("4. 插入种子数据")
    print("=" * 60)

    # 确认是否继续
    response = input("\n是否继续? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("操作已取消")
        return 1

    success_count = 0
    total_steps = 4

    # 1. 运行数据库迁移
    # 首先检查是否有多个head，如果有则先合并
    heads_result = subprocess.run("alembic heads", shell=True, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    if heads_result.returncode == 0 and heads_result.stdout.count("(head)") > 1:
        print("⚠️  检测到多个head revision，尝试自动合并...")
        merge_result = subprocess.run("alembic merge -m 'auto merge heads' heads", shell=True, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        if merge_result.returncode == 0:
            print("✅ Head revision合并成功")
        else:
            print("❌ Head revision合并失败，请手动处理")

    if run_command("alembic upgrade head", "运行数据库迁移"):
        success_count += 1

    # 2. 初始化数据库
    if await run_python_script("init_database.py", "初始化数据库表结构"):
        success_count += 1

    # 3. 插入简单种子数据
    if await run_python_script("simple_seed.py", "插入基础种子数据"):
        success_count += 1

    # 4. 运行完整种子脚本（可选）
    print(f"\n🔧 运行完整种子脚本...")
    try:
        await run_python_script("seed_tasks.py", "插入完整测试数据")
        success_count += 1
    except Exception as e:
        print(f"⚠️  完整种子脚本运行失败，但这不影响基本功能: {e}")

    print("\n" + "=" * 60)
    print(f"🎉 数据库设置完成！成功执行 {success_count}/{total_steps} 个步骤")

    if success_count >= 3:  # 至少前3步成功
        print("✅ 数据库已准备就绪，可以启动应用程序")
        print("\n下一步:")
        print("1. 启动后端服务: python -m uvicorn app.main:app --reload")
        print("2. 访问 API 文档: http://localhost:8000/docs")
        print("3. 检查数据库中的测试数据")
        return 0
    else:
        print("❌ 数据库设置未完全成功，请检查错误信息")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
