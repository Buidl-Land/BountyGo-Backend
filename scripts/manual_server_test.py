#!/usr/bin/env python3
"""
手动服务器测试 - 启动服务器并提供测试指令
"""
import sys
import os
from pathlib import Path
import subprocess
import time

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """测试导入"""
    try:
        logger.info("🧪 测试模块导入...")
        
        from app.main import app
        logger.info("✅ FastAPI应用导入成功")
        
        # 获取路由信息
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = getattr(route, 'methods', set())
                routes.append(f"{list(methods)} {route.path}")
            elif hasattr(route, 'path'):
                routes.append(f"[MOUNT] {route.path}")
        
        logger.info(f"📍 发现 {len(routes)} 个路由:")
        for route in routes:
            logger.info(f"   {route}")
        
        return True
    except Exception as e:
        logger.error(f"❌ 导入测试失败: {e}")
        return False


def start_server_interactive():
    """交互式启动服务器"""
    logger.info("🚀 准备启动BountyGo API服务器...")
    logger.info("=" * 60)
    
    # 显示启动信息
    logger.info("📋 服务器配置:")
    logger.info("   - 主机: 0.0.0.0")
    logger.info("   - 端口: 8000")
    logger.info("   - 重载: 启用")
    logger.info("   - 调试: 启用")
    
    logger.info("\n🔗 启动后可访问:")
    logger.info("   - API文档: http://localhost:8000/docs")
    logger.info("   - ReDoc: http://localhost:8000/redoc")
    logger.info("   - 健康检查: http://localhost:8000/health")
    logger.info("   - OpenAPI规范: http://localhost:8000/openapi.json")
    
    logger.info("\n⚠️ 注意:")
    logger.info("   - 数据库连接可能失败，但API仍可运行")
    logger.info("   - 使用 Ctrl+C 停止服务器")
    
    logger.info("\n" + "=" * 60)
    
    try:
        # 启动服务器
        logger.info("🚀 启动服务器...")
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ], cwd=Path(__file__).parent.parent)
        
    except KeyboardInterrupt:
        logger.info("\n🛑 服务器已停止")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")


def show_test_commands():
    """显示测试命令"""
    logger.info("🧪 手动测试命令:")
    logger.info("=" * 60)
    
    commands = [
        ("健康检查", "curl http://localhost:8000/health"),
        ("API文档", "浏览器访问 http://localhost:8000/docs"),
        ("ReDoc文档", "浏览器访问 http://localhost:8000/redoc"),
        ("OpenAPI规范", "curl http://localhost:8000/openapi.json"),
        ("根路径", "curl http://localhost:8000/"),
        ("认证端点", "curl http://localhost:8000/api/v1/auth/refresh"),
        ("用户端点", "curl http://localhost:8000/api/v1/users/me"),
        ("任务端点", "curl http://localhost:8000/api/v1/tasks"),
        ("标签端点", "curl http://localhost:8000/api/v1/tags"),
    ]
    
    for name, command in commands:
        logger.info(f"📌 {name}:")
        logger.info(f"   {command}")
        logger.info("")


def main():
    """主函数"""
    logger.info("🎯 BountyGo API手动测试工具")
    logger.info("=" * 60)
    
    # 测试导入
    if not test_imports():
        return 1
    
    logger.info("")
    
    # 显示测试命令
    show_test_commands()
    
    # 询问是否启动服务器
    try:
        response = input("是否启动服务器进行测试? (y/n): ").lower().strip()
        if response in ['y', 'yes', '是', '']:
            start_server_interactive()
        else:
            logger.info("💡 你可以手动运行以下命令启动服务器:")
            logger.info("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    except KeyboardInterrupt:
        logger.info("\n👋 再见!")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)