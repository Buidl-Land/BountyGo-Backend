#!/usr/bin/env python3
"""
BountyGo多Agent系统使用示例
演示如何使用CAMEL-AI Workforce进行多Agent协作
"""
import os
import sys
import asyncio
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.camel_workforce_service import CAMELWorkforceService, create_camel_workforce_service
from app.agent.multi_agent_config import create_standard_bountygo_config


async def demo_basic_workforce():
    """基础Workforce使用示例"""
    print("🚀 基础CAMEL Workforce演示")
    print("="*50)
    
    try:
        # 创建Workforce服务
        workforce_service = create_camel_workforce_service(
            workforce_size=3,
            collaboration_mode="workforce"
        )
        
        print("✅ Workforce服务创建成功")
        
        # 初始化
        await workforce_service.initialize()
        print("✅ Workforce初始化完成")
        
        # 获取状态
        status = await workforce_service.get_workforce_status()
        print(f"📊 Workforce状态:")
        print(f"   - 框架: {status['framework']}")
        print(f"   - Agent数量: {status['agents_count']}")
        print(f"   - 协作模式: {status['collaboration_config']['mode']}")
        print(f"   - Workforce启用: {status['collaboration_config']['workforce_enabled']}")
        
        # 清理资源
        await workforce_service.cleanup()
        print("✅ 资源清理完成")
        
        return True
        
    except Exception as e:
        print(f"❌ 基础演示失败: {e}")
        return False


async def demo_url_processing():
    """URL处理演示"""
    print("\n🌐 URL处理多Agent协作演示")
    print("="*50)
    
    try:
        # 检查API密钥
        api_key = os.getenv("PPIO_API_KEY")
        if not api_key or api_key == "your-ppio-api-key-here":
            print("⚠️ 未设置有效的PPIO_API_KEY，跳过实际API调用")
            print("💡 请在.env文件中设置真实的API密钥以体验完整功能")
            return True
        
        # 创建服务
        workforce_service = CAMELWorkforceService()
        await workforce_service.initialize()
        
        # 处理URL任务
        test_url = "https://github.com/camel-ai/camel"
        context = {
            "task_type": "开源项目分析",
            "focus": "技术栈和功能特性",
            "language": "中文"
        }
        
        print(f"🔍 开始分析URL: {test_url}")
        print(f"📝 分析上下文: {context}")
        
        # 使用多Agent协作处理
        task_info = await workforce_service.process_url_with_workforce(
            url=test_url,
            additional_context=context
        )
        
        print("✅ 分析完成！")
        print(f"📋 任务标题: {task_info.title}")
        print(f"📄 任务描述: {task_info.description[:200]}...")
        print(f"💰 奖励: {task_info.reward} {task_info.reward_currency}")
        print(f"🏷️ 标签: {', '.join(task_info.tags)}")
        
        await workforce_service.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ URL处理演示失败: {e}")
        return False


async def demo_image_processing():
    """图片处理演示"""
    print("\n🖼️ 图片处理多Agent协作演示")
    print("="*50)
    
    try:
        # 检查API密钥
        api_key = os.getenv("PPIO_API_KEY")
        if not api_key or api_key == "your-ppio-api-key-here":
            print("⚠️ 未设置有效的PPIO_API_KEY，跳过实际API调用")
            return True
        
        # 检查是否有测试图片
        image_path = "xion.png"
        if not os.path.exists(image_path):
            print(f"⚠️ 未找到测试图片 {image_path}，跳过图片处理演示")
            return True
        
        # 创建服务
        workforce_service = CAMELWorkforceService()
        await workforce_service.initialize()
        
        # 读取图片
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        print(f"🔍 开始分析图片: {image_path}")
        
        # 使用多Agent协作处理图片
        task_info = await workforce_service.process_image_with_workforce(
            image_data=image_data,
            additional_prompt="请分析图片中的任务信息，重点关注技术要求和项目细节"
        )
        
        print("✅ 图片分析完成！")
        print(f"📋 任务标题: {task_info.title}")
        print(f"📄 任务描述: {task_info.description[:200]}...")
        print(f"💰 奖励: {task_info.reward} {task_info.reward_currency}")
        print(f"🏷️ 标签: {', '.join(task_info.tags)}")
        
        await workforce_service.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ 图片处理演示失败: {e}")
        return False


async def demo_configuration_modes():
    """配置模式演示"""
    print("\n⚙️ 不同配置模式演示")
    print("="*50)
    
    modes = ["workforce", "role_playing", "pipeline"]
    
    for mode in modes:
        try:
            print(f"\n🔧 测试 {mode} 模式:")
            
            # 创建不同模式的服务
            if mode == "workforce":
                service = create_camel_workforce_service(
                    workforce_size=3,
                    collaboration_mode="workforce"
                )
            elif mode == "role_playing":
                service = create_camel_workforce_service(
                    workforce_size=2,
                    collaboration_mode="role_playing"
                )
            else:  # pipeline
                service = create_camel_workforce_service(
                    workforce_size=4,
                    collaboration_mode="pipeline"
                )
            
            await service.initialize()
            status = await service.get_workforce_status()
            
            print(f"   ✅ {mode}模式初始化成功")
            print(f"   📊 Agent数量: {status['agents_count']}")
            print(f"   🤝 协作配置: {status['collaboration_config']}")
            
            await service.cleanup()
            
        except Exception as e:
            print(f"   ❌ {mode}模式测试失败: {e}")


async def print_agent_model_mapping():
    """打印Agent模型映射"""
    print("\n🤖 Agent模型配置映射")
    print("="*50)
    
    config = create_standard_bountygo_config()
    
    for role, agent_config in config.agents.items():
        print(f"🎯 {role.value}:")
        print(f"   模型: {agent_config.model_name}")
        print(f"   提供商: {agent_config.provider.value}")
        print(f"   温度: {agent_config.temperature}")
        print(f"   视觉支持: {agent_config.supports_vision}")
        print(f"   系统消息: {agent_config.system_message[:50]}...")
        print()


async def main():
    """主演示函数"""
    print("🎉 BountyGo多Agent系统演示")
    print("🐫 基于CAMEL-AI Workforce框架")
    print("="*60)
    
    # 检查环境
    print("🔍 环境检查:")
    api_key = os.getenv("PPIO_API_KEY")
    if api_key and api_key != "your-ppio-api-key-here":
        print("✅ PPIO_API_KEY已配置")
    else:
        print("⚠️ PPIO_API_KEY未配置，部分演示将跳过")
        print("💡 请在.env文件中设置: PPIO_API_KEY=your_real_api_key")
    
    try:
        from app.agent.camel_workforce_service import check_camel_ai_availability
        if check_camel_ai_availability():
            print("✅ CAMEL-AI框架可用")
        else:
            print("❌ CAMEL-AI框架不可用")
            return
    except ImportError:
        print("❌ 无法导入CAMEL-AI相关模块")
        return
    
    # 执行演示
    demos = [
        ("基础Workforce功能", demo_basic_workforce),
        ("配置模式展示", demo_configuration_modes),
        ("Agent模型映射", print_agent_model_mapping),
        ("URL处理协作", demo_url_processing),
        ("图片处理协作", demo_image_processing),
    ]
    
    for demo_name, demo_func in demos:
        try:
            if asyncio.iscoroutinefunction(demo_func):
                await demo_func()
            else:
                await demo_func()
        except Exception as e:
            print(f"❌ {demo_name}演示失败: {e}")
        
        print("\n" + "-"*30 + "\n")
    
    print("🎉 演示完成！")
    print("\n📚 更多信息:")
    print("- 📖 配置文档: docs/multi_agent_configuration.md")
    print("- ⚙️ 配置示例: multi_agent_config_example.env")
    print("- 🧪 测试脚本: test_multi_agent_config.py")


if __name__ == "__main__":
    asyncio.run(main()) 