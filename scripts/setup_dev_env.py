#!/usr/bin/env python3
"""
开发环境快速设置脚本
自动配置开发测试token和环境变量
"""
import os
import secrets
import shutil
from pathlib import Path


def generate_secure_token():
    """生成安全的测试token"""
    return f"dev-bountygo-{secrets.token_urlsafe(16)}-2024"


def setup_env_file():
    """设置环境变量文件"""
    backend_dir = Path(__file__).parent.parent
    env_file = backend_dir / ".env"
    env_dev_file = backend_dir / ".env.dev"
    env_example_file = backend_dir / ".env.example"
    
    print("🔧 设置开发环境配置...")
    
    # 如果.env文件不存在，从.env.dev复制
    if not env_file.exists():
        if env_dev_file.exists():
            shutil.copy2(env_dev_file, env_file)
            print(f"✅ 已从 {env_dev_file.name} 复制配置到 {env_file.name}")
        elif env_example_file.exists():
            shutil.copy2(env_example_file, env_file)
            print(f"✅ 已从 {env_example_file.name} 复制配置到 {env_file.name}")
        else:
            print("❌ 未找到配置模板文件")
            return False
    else:
        print(f"ℹ️  {env_file.name} 文件已存在")
    
    # 读取现有配置
    env_content = env_file.read_text(encoding='utf-8')
    
    # 检查是否需要生成新的测试token
    if "DEV_TEST_TOKEN=" not in env_content or "DEV_TEST_TOKEN=dev-bountygo-test-token-2024" in env_content:
        new_token = generate_secure_token()
        
        if "DEV_TEST_TOKEN=" in env_content:
            # 替换现有token
            lines = env_content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('DEV_TEST_TOKEN='):
                    lines[i] = f'DEV_TEST_TOKEN={new_token}'
                    break
            env_content = '\n'.join(lines)
        else:
            # 添加新token
            env_content += f'\n\n# 开发测试token (自动生成)\nDEV_TEST_TOKEN={new_token}\n'
        
        env_file.write_text(env_content, encoding='utf-8')
        print(f"🔑 已生成新的开发测试token: {new_token}")
    else:
        print("🔑 开发测试token已配置")
    
    return True


def verify_configuration():
    """验证配置是否正确"""
    print("\n🔍 验证配置...")
    
    try:
        # 临时设置环境变量路径
        backend_dir = Path(__file__).parent.parent
        env_file = backend_dir / ".env"
        
        if env_file.exists():
            # 读取.env文件
            env_vars = {}
            for line in env_file.read_text(encoding='utf-8').split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
            
            # 检查关键配置
            required_vars = ['ENVIRONMENT', 'DEBUG', 'DEV_TEST_TOKEN']
            missing_vars = []
            
            for var in required_vars:
                if var not in env_vars:
                    missing_vars.append(var)
                else:
                    print(f"✅ {var}: {env_vars[var]}")
            
            if missing_vars:
                print(f"❌ 缺少配置: {', '.join(missing_vars)}")
                return False
            
            # 检查开发环境设置
            if env_vars.get('ENVIRONMENT') != 'development':
                print("⚠️  建议设置 ENVIRONMENT=development")
            
            if env_vars.get('DEBUG') != 'true':
                print("⚠️  建议设置 DEBUG=true")
            
            return True
        else:
            print("❌ .env 文件不存在")
            return False
            
    except Exception as e:
        print(f"❌ 验证配置时出错: {e}")
        return False


def test_import():
    """测试导入应用程序配置"""
    print("\n🧪 测试应用程序配置...")
    
    try:
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        
        from app.core.config import settings
        
        print(f"✅ 应用程序名称: {settings.APP_NAME}")
        print(f"✅ 环境: {settings.ENVIRONMENT}")
        print(f"✅ 调试模式: {settings.DEBUG}")
        print(f"✅ 开发环境: {settings.is_development()}")
        print(f"✅ 测试token启用: {settings.is_dev_test_token_enabled()}")
        
        if settings.is_dev_test_token_enabled():
            print(f"✅ 测试token: {settings.get_dev_test_token()}")
        else:
            print("⚠️  测试token未启用")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入配置失败: {e}")
        return False


def print_usage_instructions():
    """打印使用说明"""
    print("\n📋 使用说明:")
    print("1. 启动应用程序:")
    print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print()
    print("2. 查看API信息:")
    print("   curl http://localhost:8000/api/v1/")
    print()
    print("3. 查看开发认证信息:")
    print("   curl http://localhost:8000/api/v1/dev-auth")
    print()
    print("4. 使用测试token访问API:")
    print("   curl -H 'Authorization: Bearer <your-test-token>' http://localhost:8000/api/v1/users/me")
    print()
    print("5. 运行认证测试:")
    print("   python scripts/test_auth_improvements.py")
    print()
    print("📖 详细文档: docs/DEV_AUTH_GUIDE.md")


def main():
    """主函数"""
    print("🚀 BountyGo 开发环境设置")
    print("=" * 50)
    
    success = True
    
    # 设置环境文件
    if not setup_env_file():
        success = False
    
    # 验证配置
    if not verify_configuration():
        success = False
    
    # 测试导入
    if not test_import():
        success = False
    
    print("\n" + "=" * 50)
    
    if success:
        print("🎉 开发环境设置完成！")
        print_usage_instructions()
    else:
        print("❌ 设置过程中遇到问题，请检查上述错误信息")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())