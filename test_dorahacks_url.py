#!/usr/bin/env python3
"""
测试DoraHacks URL解析功能
"""
import asyncio
import sys
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
load_dotenv()

# 检查关键环境变量
print(f"PPIO_API_KEY: {'已设置' if os.getenv('PPIO_API_KEY') else '未设置'}")
print(f"PPIO_BASE_URL: {os.getenv('PPIO_BASE_URL', '未设置')}")
print(f"PPIO_MODEL_NAME: {os.getenv('PPIO_MODEL_NAME', '未设置')}")
print()

from app.agent.service import URLAgentService

async def test_dorahacks_url():
    """测试DoraHacks URL解析"""
    url = "https://dorahacks.io/hackathon/gui-inu-ideathon/buidl"
    
    print(f"🚀 开始解析URL: {url}")
    print("=" * 80)
    
    try:
        # 创建URL Agent服务
        service = URLAgentService()
        
        # 测试服务状态
        print("📊 检查服务状态...")
        status = await service.get_service_status()
        print(f"服务状态: {status['service_name']}")
        
        # 检查PPIO连接
        print("\n🔗 测试PPIO连接...")
        config_test = await service.test_configuration()
        if config_test:
            print("✅ PPIO连接正常")
        else:
            print("❌ PPIO连接失败")
            return
        
        # 开始URL解析
        print(f"\n🔍 开始解析URL...")
        start_time = datetime.now()
        
        # 使用process_url方法（不自动创建任务）
        result = await service.process_url(
            url=url,
            user_id=1,  # 测试用户ID
            auto_create=False  # 只提取信息，不创建任务
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"⏱️  处理时间: {processing_time:.2f}秒")
        print("=" * 80)
        
        if result.success:
            print("✅ URL解析成功!")
            print("\n📋 解析结果:")
            
            info = result.extracted_info
            
            # 格式化输出结果
            print(f"📌 标题: {info.title}")
            print(f"📝 描述: {info.description}")
            print(f"💰 奖励: {info.reward} {info.reward_currency}")
            print(f"📅 截止日期: {info.deadline}")
            print(f"🏷️  标签: {', '.join(info.tags) if info.tags else '无'}")
            print(f"📊 难度等级: {info.difficulty_level}")
            print(f"⏰ 预估工时: {info.estimated_hours}小时")
            print(f"🌐 外部链接: {info.external_link or '无'}")
            
            # 输出JSON格式的完整结果
            print("\n" + "=" * 80)
            print("📄 完整JSON结果:")
            result_dict = {
                "success": result.success,
                "processing_time": result.processing_time,
                "extracted_info": {
                    "title": info.title,
                    "description": info.description,
                    "reward": float(info.reward) if info.reward else None,
                    "reward_currency": info.reward_currency,
                    "deadline": info.deadline,
                    "tags": info.tags,
                    "difficulty_level": info.difficulty_level,
                    "estimated_hours": info.estimated_hours,
                    "external_link": info.external_link
                }
            }
            # 处理Decimal类型的序列化
            import decimal
            def decimal_serializer(obj):
                if isinstance(obj, decimal.Decimal):
                    return float(obj)
                raise TypeError
            
            print(json.dumps(result_dict, indent=2, ensure_ascii=False, default=decimal_serializer))
            
        else:
            print("❌ URL解析失败!")
            print(f"错误信息: {result.error_message}")
            print(f"处理时间: {result.processing_time:.2f}秒")
        
        # 获取性能指标
        print("\n" + "=" * 80)
        print("📈 性能指标:")
        metrics = service.get_performance_metrics()
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
                
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        print(f"错误详情: {traceback.format_exc()}")

if __name__ == "__main__":
    print("🎯 DoraHacks URL解析测试")
    print("=" * 80)
    asyncio.run(test_dorahacks_url())