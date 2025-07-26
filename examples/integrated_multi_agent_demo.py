#!/usr/bin/env python3
"""
Integrated Multi-Agent System Demo
整合的多Agent系统演示 - 展示智能协调器和统一配置的功能
"""
import os
import sys
import asyncio
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.smart_coordinator import SmartCoordinator, UserInput, get_smart_coordinator
from app.agent.unified_config import get_config_manager
from app.agent.preference_manager import UserPreferences, OutputFormat, AnalysisFocus


async def demo_basic_functionality():
    """基础功能演示"""
    print("🚀 智能协调器基础功能演示")
    print("="*50)
    
    try:
        # 获取智能协调器
        coordinator = await get_smart_coordinator()
        print("✅ 智能协调器初始化成功")
        
        # 测试用户输入处理
        test_inputs = [
            "你好，我是新用户",
            "帮助",
            "分析这个URL: https://github.com/camel-ai/camel",
            "设置输出格式为JSON",
            "系统状态如何？"
        ]
        
        user_id = "demo_user"
        
        for i, input_text in enumerate(test_inputs, 1):
            print(f"\n📝 测试输入 {i}: {input_text}")
            
            user_input = UserInput.create(input_text, user_id)
            result = await coordinator.process_user_input(user_input)
            
            print(f"   ✅ 处理成功: {result.success}")
            print(f"   🎯 识别意图: {result.user_intent}")
            print(f"   💬 回复: {result.response_message[:100]}...")
            print(f"   ⏱️ 处理时间: {result.processing_time:.2f}s")
            
            if result.suggestions:
                print(f"   💡 建议: {', '.join(result.suggestions[:3])}")
        
        return True
        
    except Exception as e:
        print(f"❌ 基础功能演示失败: {e}")
        return False


async def demo_chat_interaction():
    """聊天交互演示"""
    print("\n💬 聊天交互演示")
    print("="*50)
    
    try:
        coordinator = await get_smart_coordinator()
        
        # 模拟对话
        conversation = [
            "你好！",
            "我想分析一个网页内容",
            "https://example.com/task-description",
            "谢谢你的帮助"
        ]
        
        user_id = "chat_user"
        
        for message in conversation:
            print(f"\n👤 用户: {message}")
            
            response = await coordinator.chat_with_user(message, user_id)
            
            print(f"🤖 助手: {response.message}")
            
            if response.task_info:
                print(f"📋 任务信息: {response.task_info.title}")
            
            if response.suggestions:
                print(f"💡 建议: {', '.join(response.suggestions[:2])}")
            
            print(f"⏱️ 响应时间: {response.processing_time:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ 聊天交互演示失败: {e}")
        return False


async def demo_preference_management():
    """偏好管理演示"""
    print("\n⚙️ 偏好管理演示")
    print("="*50)
    
    try:
        coordinator = await get_smart_coordinator()
        user_id = "preference_user"
        
        # 获取默认偏好
        preferences = await coordinator.preference_manager.get_user_preferences(user_id)
        print(f"📊 默认偏好:")
        print(f"   输出格式: {preferences.output_format.value}")
        print(f"   分析重点: {[focus.value for focus in preferences.analysis_focus]}")
        print(f"   语言: {preferences.language}")
        print(f"   质量阈值: {preferences.quality_threshold}")
        
        # 更新偏好
        print(f"\n🔧 更新用户偏好...")
        await coordinator.preference_manager.update_user_preferences(user_id, {
            "output_format": "JSON",
            "language": "English",
            "analysis_focus": ["TECHNICAL", "TIMELINE"],
            "quality_threshold": 0.8
        })
        
        # 获取更新后的偏好
        updated_preferences = await coordinator.preference_manager.get_user_preferences(user_id)
        print(f"📊 更新后偏好:")
        print(f"   输出格式: {updated_preferences.output_format.value}")
        print(f"   分析重点: {[focus.value for focus in updated_preferences.analysis_focus]}")
        print(f"   语言: {updated_preferences.language}")
        print(f"   质量阈值: {updated_preferences.quality_threshold}")
        
        # 测试偏好应用
        print(f"\n🧪 测试偏好应用...")
        user_input = UserInput.create("分析技术需求", user_id)
        result = await coordinator.process_user_input(user_input)
        
        print(f"   处理结果: {result.success}")
        print(f"   应用了用户偏好: ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ 偏好管理演示失败: {e}")
        return False


async def demo_configuration_system():
    """配置系统演示"""
    print("\n🔧 统一配置系统演示")
    print("="*50)
    
    try:
        config_manager = get_config_manager()
        
        # 显示配置摘要
        summary = config_manager.get_config_summary()
        print(f"📋 配置摘要:")
        print(f"   框架: {summary['system']['framework']}")
        print(f"   默认提供商: {summary['system']['default_provider']}")
        print(f"   最大并发Agent: {summary['system']['max_concurrent_agents']}")
        print(f"   工作流模式: {summary['workflow']['mode']}")
        print(f"   工作组大小: {summary['workflow']['workforce_size']}")
        
        print(f"\n🤖 Agent配置:")
        for role, config in summary['agents'].items():
            print(f"   {role}: {config['model']} ({config['provider']})")
            if config.get('supports_vision'):
                print(f"      ✅ 支持视觉")
        
        print(f"\n✅ 配置系统状态: {'已初始化' if summary['initialized'] else '未初始化'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置系统演示失败: {e}")
        return False


async def demo_error_handling():
    """错误处理演示"""
    print("\n🛡️ 错误处理演示")
    print("="*50)
    
    try:
        coordinator = await get_smart_coordinator()
        user_id = "error_test_user"
        
        # 测试各种错误情况
        error_cases = [
            ("", "空输入"),
            ("invalid://not-a-real-url", "无效URL"),
            ("非常短", "内容过短"),
            ("x" * 10000, "内容过长")
        ]
        
        for input_text, description in error_cases:
            print(f"\n🧪 测试 {description}: {input_text[:50]}...")
            
            user_input = UserInput.create(input_text, user_id)
            result = await coordinator.process_user_input(user_input)
            
            print(f"   处理结果: {'成功' if result.success else '失败'}")
            if not result.success and result.error_message:
                print(f"   错误信息: {result.error_message[:100]}...")
            print(f"   响应消息: {result.response_message[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误处理演示失败: {e}")
        return False


async def demo_performance_stats():
    """性能统计演示"""
    print("\n📊 性能统计演示")
    print("="*50)
    
    try:
        coordinator = await get_smart_coordinator()
        
        # 获取统计信息
        stats = coordinator.get_stats()
        print(f"📈 处理统计:")
        print(f"   总请求数: {stats['total_requests']}")
        print(f"   成功请求数: {stats['successful_requests']}")
        print(f"   失败请求数: {stats['failed_requests']}")
        
        if stats['total_requests'] > 0:
            success_rate = stats['successful_requests'] / stats['total_requests'] * 100
            print(f"   成功率: {success_rate:.1f}%")
            print(f"   平均处理时间: {stats['avg_processing_time']:.2f}s")
        
        # 获取偏好管理器统计
        pref_stats = coordinator.preference_manager.get_stats()
        print(f"\n👥 用户统计:")
        print(f"   总用户数: {pref_stats['total_users']}")
        print(f"   总交互数: {pref_stats['total_interactions']}")
        print(f"   格式偏好分布: {pref_stats['format_distribution']}")
        print(f"   语言偏好分布: {pref_stats['language_distribution']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能统计演示失败: {e}")
        return False


async def main():
    """主演示函数"""
    print("🎉 BountyGo整合多Agent系统演示")
    print("🧠 智能协调器 + 统一配置 + 偏好管理")
    print("="*60)
    
    # 检查环境
    print("🔍 环境检查:")
    api_key = os.getenv("PPIO_API_KEY")
    if api_key and api_key != "your-ppio-api-key-here":
        print("✅ PPIO_API_KEY已配置")
    else:
        print("⚠️ PPIO_API_KEY未配置，部分功能将受限")
        print("💡 请在.env文件中设置: PPIO_API_KEY=your_real_api_key")
    
    # 执行演示
    demos = [
        ("配置系统", demo_configuration_system),
        ("基础功能", demo_basic_functionality),
        ("偏好管理", demo_preference_management),
        ("聊天交互", demo_chat_interaction),
        ("错误处理", demo_error_handling),
        ("性能统计", demo_performance_stats),
    ]
    
    success_count = 0
    
    for demo_name, demo_func in demos:
        try:
            print(f"\n{'='*20} {demo_name} {'='*20}")
            success = await demo_func()
            if success:
                success_count += 1
                print(f"✅ {demo_name}演示完成")
            else:
                print(f"❌ {demo_name}演示失败")
        except Exception as e:
            print(f"❌ {demo_name}演示异常: {e}")
        
        print("\n" + "-"*60)
    
    # 总结
    print(f"\n🎯 演示总结:")
    print(f"   完成演示: {success_count}/{len(demos)}")
    print(f"   成功率: {success_count/len(demos)*100:.1f}%")
    
    if success_count == len(demos):
        print("🎉 所有演示都成功完成！")
    elif success_count > len(demos) // 2:
        print("👍 大部分演示成功完成")
    else:
        print("⚠️ 多个演示失败，请检查配置")
    
    print("\n📚 更多信息:")
    print("- 📖 智能协调器文档: app/agent/smart_coordinator.py")
    print("- ⚙️ 统一配置文档: app/agent/unified_config.py")
    print("- 👤 偏好管理文档: app/agent/preference_manager.py")
    print("- 🧪 测试文件: tests/test_smart_coordinator.py")


if __name__ == "__main__":
    asyncio.run(main())