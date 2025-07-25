#!/usr/bin/env python3
"""
PPIO客户端功能测试脚本
"""
import asyncio
import os
import json
from app.agent.config import PPIOModelConfig
from app.agent.client import PPIOModelClient


async def test_client_basic_functionality():
    """测试客户端基本功能"""
    print("=== PPIO客户端基本功能测试 ===")
    
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
        # 创建配置和客户端
        config = PPIOModelConfig(api_key=api_key)
        client = PPIOModelClient(config)
        
        print(f"✅ 客户端创建成功")
        print(f"   - 模型: {config.model_name}")
        print(f"   - 支持结构化输出: {'是' if config.supports_structured_output() else '否'}")
        print(f"   - 支持function calling: {'是' if config.supports_function_calling() else '否'}")
        
        # 测试连接
        print("\n🔄 测试连接...")
        connection_ok = await client.test_connection()
        
        if connection_ok:
            print("✅ 连接测试成功!")
        else:
            print("❌ 连接测试失败")
            return False
        
        # 显示统计信息
        stats = client.get_stats()
        print(f"\n📊 客户端统计:")
        print(f"   - 请求次数: {stats['request_count']}")
        print(f"   - 总token数: {stats['total_tokens']}")
        print(f"   - 错误次数: {stats['error_count']}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ 客户端测试失败: {e}")
        return False


async def test_structured_extraction():
    """测试结构化信息提取"""
    print("\n=== 结构化信息提取测试 ===")
    
    api_key = os.getenv("PPIO_API_KEY")
    if not api_key:
        try:
            from app.agent.config import URLAgentSettings
            settings = URLAgentSettings()
            api_key = settings.ppio_api_key
        except Exception:
            pass
    
    if not api_key:
        print("❌ 跳过测试: 未设置PPIO_API_KEY")
        return False
    
    try:
        config = PPIOModelConfig(api_key=api_key)
        client = PPIOModelClient(config)
        
        # 测试内容
        test_content = """
        标题: Python开发工程师招聘
        描述: 我们正在寻找一名有经验的Python开发工程师，负责后端API开发。
        薪资: 15000-25000元/月
        截止日期: 2024-12-31
        技能要求: Python, FastAPI, PostgreSQL, Redis
        """
        
        system_prompt = """
        你是一个专业的信息提取专家。请从给定的文本中提取结构化信息，并以JSON格式返回。
        
        返回格式:
        {
            "title": "标题",
            "description": "描述", 
            "reward": "薪资数字部分",
            "deadline": "截止日期",
            "tags": ["技能标签列表"]
        }
        """
        
        print("🔄 提取结构化信息...")
        result = await client.extract_structured_info(
            content=test_content,
            system_prompt=system_prompt
        )
        
        print("✅ 提取成功!")
        print("📋 提取结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 显示统计信息
        stats = client.get_stats()
        print(f"\n📊 本次提取统计:")
        print(f"   - 使用token数: {stats['total_tokens']}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ 结构化提取测试失败: {e}")
        return False


async def test_chat_completion():
    """测试聊天完成功能"""
    print("\n=== 聊天完成功能测试 ===")
    
    api_key = os.getenv("PPIO_API_KEY")
    if not api_key:
        try:
            from app.agent.config import URLAgentSettings
            settings = URLAgentSettings()
            api_key = settings.ppio_api_key
        except Exception:
            pass
    
    if not api_key:
        print("❌ 跳过测试: 未设置PPIO_API_KEY")
        return False
    
    try:
        config = PPIOModelConfig(api_key=api_key)
        client = PPIOModelClient(config)
        
        messages = [
            {"role": "system", "content": "你是一个有用的助手。"},
            {"role": "user", "content": "请简单介绍一下Python编程语言的特点。"}
        ]
        
        print("🔄 执行聊天完成...")
        response = await client.chat_completion(messages)
        
        print("✅ 聊天完成成功!")
        print("💬 AI回复:")
        print(response[:200] + "..." if len(response) > 200 else response)
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ 聊天完成测试失败: {e}")
        return False


async def test_function_calling():
    """测试function calling功能"""
    print("\n=== Function Calling功能测试 ===")
    
    api_key = os.getenv("PPIO_API_KEY")
    if not api_key:
        try:
            from app.agent.config import URLAgentSettings
            settings = URLAgentSettings()
            api_key = settings.ppio_api_key
        except Exception:
            pass
    
    if not api_key:
        print("❌ 跳过测试: 未设置PPIO_API_KEY")
        return False
    
    try:
        config = PPIOModelConfig(api_key=api_key)
        client = PPIOModelClient(config)
        
        if not config.supports_function_calling():
            print("⚠️  当前模型不支持function calling")
            return True
        
        # 定义函数
        functions = [{
            "name": "extract_task_info",
            "description": "从文本中提取任务信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "任务标题"},
                    "reward": {"type": "number", "description": "奖励金额"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "技能标签"}
                },
                "required": ["title"]
            }
        }]
        
        messages = [
            {"role": "user", "content": "请从这个文本中提取任务信息: 'React前端开发，薪资8000元，需要React、JavaScript技能'"}
        ]
        
        print("🔄 执行function calling...")
        result = await client.function_call(
            messages=messages,
            functions=functions,
            function_call={"name": "extract_task_info"}
        )
        
        print("✅ Function calling成功!")
        print("🔧 调用结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Function calling测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("开始PPIO客户端功能测试...\n")
    
    # 运行所有测试
    tests = [
        ("基本功能", test_client_basic_functionality),
        ("结构化提取", test_structured_extraction),
        ("聊天完成", test_chat_completion),
        ("Function Calling", test_function_calling)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results[test_name] = False
    
    # 显示测试结果
    print(f"\n=== 测试结果汇总 ===")
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过! PPIO客户端功能正常")
    else:
        print("⚠️  部分测试失败，请检查配置和网络连接")


if __name__ == "__main__":
    asyncio.run(main())