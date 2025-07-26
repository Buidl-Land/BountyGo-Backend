#!/usr/bin/env python3
"""
测试图片解析功能
"""
import asyncio
import sys
import os
import json
import base64
from datetime import datetime
from dotenv import load_dotenv

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
load_dotenv()

# 检查关键环境变量
print(f"PPIO_API_KEY: {'已设置' if os.getenv('PPIO_API_KEY') else '未设置'}")
print(f"IMAGE_ANALYZER_MODEL: {os.getenv('IMAGE_ANALYZER_MODEL', '未设置')}")
print()

from app.agent.service import URLAgentService

async def test_image_parsing():
    """测试图片解析功能"""
    image_path = "test_image.png"
    
    print(f"🖼️  开始解析图片: {image_path}")
    print("=" * 80)
    
    try:
        # 检查图片文件是否存在
        if not os.path.exists(image_path):
            print(f"❌ 图片文件不存在: {image_path}")
            return
        
        # 读取图片文件
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        print(f"📁 图片文件大小: {len(image_data)} bytes")
        
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
        
        # 开始图片解析
        print(f"\n🔍 开始解析图片...")
        start_time = datetime.now()
        
        # 第一步：OCR提取图片内容
        print("📝 步骤1: 使用OCR大模型提取图片内容...")
        
        # 第二步：结构化为JSON
        print("🏗️  步骤2: 将内容结构化为任务信息...")
        
        # 使用图片解析功能
        result = await service.extract_task_info_from_image(
            image_data=image_data,
            additional_prompt="请分析这张图片中的任务信息，提取标题、描述、奖励、截止日期等关键信息"
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f"⏱️  处理时间: {processing_time:.2f}秒")
        print("=" * 80)
        
        print("✅ 图片解析成功!")
        print("\n📋 解析结果:")
        
        # 格式化输出结果
        print(f"📌 标题: {result.title}")
        print(f"📝 描述: {result.description or '无'}")
        print(f"💰 奖励: {result.reward} {result.reward_currency or ''}")
        print(f"📅 截止日期: {result.deadline}")
        print(f"🏷️  标签: {', '.join(result.tags) if result.tags else '无'}")
        print(f"📊 难度等级: {result.difficulty_level or '无'}")
        print(f"⏰ 预估工时: {result.estimated_hours or '无'}小时")
        print(f"🏢 主办方: {result.organizer_name or '无'}")
        print(f"🌐 外部链接: {result.external_link or '无'}")
        
        # 输出JSON格式的完整结果
        print("\n" + "=" * 80)
        print("📄 完整JSON结果:")
        
        # 处理Decimal类型的序列化
        import decimal
        def decimal_serializer(obj):
            if isinstance(obj, decimal.Decimal):
                return float(obj)
            raise TypeError
        
        result_dict = {
            "success": True,
            "processing_time": processing_time,
            "extracted_info": {
                "title": result.title,
                "summary": result.summary,
                "description": result.description,
                "reward": float(result.reward) if result.reward else None,
                "reward_currency": result.reward_currency,
                "deadline": result.deadline,
                "category": result.category,
                "reward_details": result.reward_details,
                "reward_type": result.reward_type,
                "tags": result.tags,
                "difficulty_level": result.difficulty_level,
                "estimated_hours": result.estimated_hours,
                "organizer_name": result.organizer_name,
                "external_link": result.external_link
            }
        }
        
        print(json.dumps(result_dict, indent=2, ensure_ascii=False, default=decimal_serializer))
        
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
    print("🎯 图片解析功能测试")
    print("=" * 80)
    asyncio.run(test_image_parsing())