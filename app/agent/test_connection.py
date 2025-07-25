#!/usr/bin/env python3
"""
PPIO模型连接测试脚本
"""
import asyncio
import os
from app.agent.config import PPIOModelConfig


async def test_ppio_connection():
    """测试PPIO模型连接"""
    print("=== PPIO模型连接测试 ===")
    
    # 从环境变量或配置文件获取API密钥
    api_key = os.getenv("PPIO_API_KEY")
    if not api_key:
        try:
            from app.agent.config import URLAgentSettings
            settings = URLAgentSettings()
            api_key = settings.ppio_api_key
        except Exception:
            pass
    
    if not api_key:
        print("❌ 错误: 未设置PPIO_API_KEY")
        print("请设置环境变量: export PPIO_API_KEY=your_api_key")
        print("或在.env文件中配置PPIO_API_KEY")
        return False
    
    try:
        # 创建配置实例
        config = PPIOModelConfig(api_key=api_key)
        print(f"✅ 配置创建成功")
        print(f"   - 模型: {config.model_name}")
        print(f"   - 基础URL: {config.base_url}")
        print(f"   - 最大tokens: {config.max_tokens}")
        print(f"   - 温度: {config.temperature}")
        
        # 检查模型支持的功能
        print(f"   - 支持结构化输出: {'是' if config.supports_structured_output() else '否'}")
        print(f"   - 支持function calling: {'是' if config.supports_function_calling() else '否'}")
        
        # 测试API连接
        print("\n🔄 测试API连接...")
        is_valid = await config.validate_api_connection()
        
        if is_valid:
            print("✅ API连接测试成功!")
            print("   - API密钥有效")
            print("   - 模型可正常访问")
            return True
        else:
            print("❌ API连接测试失败")
            return False
            
    except ValueError as e:
        print(f"❌ 配置验证错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False


async def test_model_selection():
    """测试模型选择功能"""
    print("\n=== 支持的模型列表 ===")
    
    try:
        # 使用默认配置创建实例（仅用于获取模型列表）
        config = PPIOModelConfig(api_key="sk_test_key_12345")
        supported_models = config.get_supported_models()
        
        print("推荐模型（按优先级排序）:")
        for i, model in enumerate(supported_models, 1):
            print(f"  {i}. {model}")
            
        return True
        
    except Exception as e:
        print(f"❌ 获取模型列表失败: {e}")
        return False


if __name__ == "__main__":
    async def main():
        """主测试函数"""
        print("开始PPIO模型配置测试...\n")
        
        # 测试模型选择
        model_test = await test_model_selection()
        
        # 测试连接
        connection_test = await test_ppio_connection()
        
        print(f"\n=== 测试结果 ===")
        print(f"模型选择测试: {'✅ 通过' if model_test else '❌ 失败'}")
        print(f"连接测试: {'✅ 通过' if connection_test else '❌ 失败'}")
        
        if model_test and connection_test:
            print("\n🎉 所有测试通过! PPIO模型配置正常工作")
        else:
            print("\n⚠️  部分测试失败，请检查配置")
    
    asyncio.run(main())