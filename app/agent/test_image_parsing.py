"""
Test script for image parsing functionality.
"""
import asyncio
import base64
import os
import sys
from io import BytesIO
from PIL import Image

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agent.config import PPIOModelConfig
from app.agent.image_parsing_agent import ImageParsingAgent
from app.agent.factory import get_ppio_config


def create_test_image() -> str:
    """创建一个包含测试任务信息的图片"""
    # 创建一个简单的测试图片，包含任务信息
    img = Image.new('RGB', (800, 600), color='white')
    
    # 在实际应用中，这里应该是包含真实任务信息的图片
    # 这里我们创建一个简单的白色图片作为测试
    
    # 将图片转换为base64
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    img_bytes = buffer.getvalue()
    
    return base64.b64encode(img_bytes).decode('utf-8')


async def test_image_parsing_basic():
    """测试基本的图片解析功能"""
    print("🧪 测试基本图片解析功能...")
    
    try:
        # 获取配置
        config = get_ppio_config()
        
        # 确保使用支持视觉的模型
        if not config.supports_vision():
            config.model_name = config.get_preferred_vision_model()
            print(f"切换到视觉模型: {config.model_name}")
        
        # 创建测试图片
        test_image_b64 = create_test_image()
        
        # 创建图片解析代理
        async with ImageParsingAgent(config) as agent:
            # 分析图片
            task_info = await agent.analyze_image(
                image_data=test_image_b64,
                additional_prompt="这是一个测试图片，请根据图片内容创建一个合理的任务信息"
            )
            
            print(f"✅ 解析成功!")
            print(f"📝 标题: {task_info.title}")
            print(f"📄 描述: {task_info.description}")
            print(f"💰 奖励: {task_info.reward} {task_info.reward_currency}")
            print(f"🏷️ 标签: {task_info.tags}")
            print(f"⭐ 难度: {task_info.difficulty_level}")
            print(f"⏱️ 预估时长: {task_info.estimated_hours}小时")
            
            return True
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


async def test_image_parsing_with_context():
    """测试带上下文的图片解析"""
    print("\n🧪 测试带上下文的图片解析...")
    
    try:
        config = get_ppio_config()
        
        if not config.supports_vision():
            config.model_name = config.get_preferred_vision_model()
        
        test_image_b64 = create_test_image()
        
        # 测试上下文
        context = {
            "task_type": "编程",
            "platform": "GitHub", 
            "language": "中文"
        }
        
        async with ImageParsingAgent(config) as agent:
            task_info = await agent.analyze_image_with_context(
                image_data=test_image_b64,
                context=context
            )
            
            print(f"✅ 上下文解析成功!")
            print(f"📝 标题: {task_info.title}")
            print(f"🏷️ 标签: {task_info.tags}")
            
            return True
            
    except Exception as e:
        print(f"❌ 上下文测试失败: {e}")
        return False


async def test_image_validation():
    """测试图片验证功能"""
    print("\n🧪 测试图片验证功能...")
    
    try:
        config = get_ppio_config()
        
        if not config.supports_vision():
            config.model_name = config.get_preferred_vision_model()
        
        agent = ImageParsingAgent(config)
        await agent.initialize()
        
        # 测试无效的base64数据
        try:
            await agent.analyze_image("invalid_base64_data")
            print("❌ 应该拒绝无效的base64数据")
            return False
        except ValueError:
            print("✅ 正确拒绝了无效的base64数据")
        
        # 测试过大的图片（模拟）
        large_image_data = "x" * (11 * 1024 * 1024)  # 11MB
        try:
            await agent.analyze_image(base64.b64encode(large_image_data.encode()).decode())
            print("❌ 应该拒绝过大的图片")
            return False
        except ValueError as e:
            if "too large" in str(e):
                print("✅ 正确拒绝了过大的图片")
            else:
                print(f"❌ 意外的错误: {e}")
                return False
        
        await agent.client.close()
        return True
        
    except Exception as e:
        print(f"❌ 验证测试失败: {e}")
        return False


async def test_agent_info():
    """测试代理信息获取"""
    print("\n🧪 测试代理信息...")
    
    try:
        config = get_ppio_config()
        
        if not config.supports_vision():
            config.model_name = config.get_preferred_vision_model()
        
        agent = ImageParsingAgent(config)
        info = agent.get_agent_info()
        
        print(f"✅ 代理信息:")
        print(f"   角色: {info['role_name']}")
        print(f"   模型: {info['model_name']}")
        print(f"   支持视觉: {info['supports_vision']}")
        print(f"   支持格式: {info['supported_formats']}")
        print(f"   最大文件大小: {info['max_image_size']} bytes")
        print(f"   最大尺寸: {info['max_dimension']}px")
        
        return True
        
    except Exception as e:
        print(f"❌ 信息测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始图片解析功能测试\n")
    
    # 检查API密钥
    api_key = os.getenv("PPIO_API_KEY")
    if not api_key:
        print("❌ 未设置PPIO_API_KEY环境变量")
        print("请设置: export PPIO_API_KEY=your_api_key")
        return
    
    tests = [
        ("代理信息测试", test_agent_info),
        ("图片验证测试", test_image_validation),
        ("基本解析测试", test_image_parsing_basic),
        ("上下文解析测试", test_image_parsing_with_context),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 {test_name}")
        print('='*50)
        
        if await test_func():
            passed += 1
        
        # 短暂延迟避免API限流
        await asyncio.sleep(1)
    
    print(f"\n{'='*50}")
    print(f"📊 测试结果: {passed}/{total} 通过")
    print('='*50)
    
    if passed == total:
        print("🎉 所有测试通过！图片解析功能正常工作")
    else:
        print(f"⚠️ {total - passed} 个测试失败")


if __name__ == "__main__":
    asyncio.run(main()) 