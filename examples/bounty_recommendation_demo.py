#!/usr/bin/env python3
"""
Bounty Recommendation System Demo
基于RAG的Bounty推荐系统演示
"""
import os
import sys
import asyncio
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.bounty_recommendation_agent import BountyRecommendationAgent, RecommendationContext
from app.agent.preference_manager import UserPreferences, OutputFormat, AnalysisFocus
from app.agent.smart_coordinator import SmartCoordinator, UserInput


class MockDBSession:
    """模拟数据库会话"""
    async def execute(self, stmt):
        return MockResult()
    
    async def commit(self):
        pass
    
    async def rollback(self):
        pass


class MockResult:
    """模拟查询结果"""
    def scalars(self):
        return MockScalars()
    
    def fetchall(self):
        return []


class MockScalars:
    """模拟标量结果"""
    def all(self):
        return []


async def demo_recommendation_agent():
    """演示推荐Agent基础功能"""
    print("🎯 Bounty推荐Agent演示")
    print("="*50)
    
    try:
        # 创建模拟数据库会话
        db_session = MockDBSession()
        
        # 创建推荐Agent
        recommendation_agent = BountyRecommendationAgent(db_session)
        await recommendation_agent.initialize()
        
        print("✅ 推荐Agent初始化成功")
        
        # 测试用户
        test_user_id = "demo_user_123"
        
        # 获取推荐
        print(f"\n🔍 为用户 {test_user_id} 获取推荐...")
        recommendations = await recommendation_agent.get_recommendations(
            user_id=test_user_id,
            limit=3
        )
        
        print(f"✅ 获取到 {len(recommendations)} 个推荐")
        
        # 显示推荐结果
        for i, rec in enumerate(recommendations, 1):
            print(f"\n📋 推荐 {i}:")
            print(f"   标题: {rec.title}")
            print(f"   奖励: {rec.reward} {rec.reward_currency}")
            print(f"   标签: {', '.join(rec.tags)}")
            print(f"   匹配度: {rec.match_score:.1%}")
            print(f"   匹配原因: {', '.join(rec.match_reasons)}")
            print(f"   描述: {rec.description[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 推荐Agent演示失败: {e}")
        return False


async def demo_user_profile_extraction():
    """演示用户档案提取"""
    print("\n👤 用户档案提取演示")
    print("="*50)
    
    try:
        db_session = MockDBSession()
        recommendation_agent = BountyRecommendationAgent(db_session)
        await recommendation_agent.initialize()
        
        # 模拟用户交互历史
        test_user_id = "profile_test_user"
        
        # 模拟一些交互记录到偏好管理器
        from app.agent.preference_manager import UserInteraction
        from datetime import datetime
        
        mock_interactions = [
            UserInteraction(
                user_id=test_user_id,
                input_content="我想找一个Python开发的任务",
                input_type="text",
                user_intent="get_recommendations",
                result_success=True,
                processing_time=1.2,
                timestamp=datetime.utcnow()
            ),
            UserInteraction(
                user_id=test_user_id,
                input_content="有没有Web3相关的智能合约开发工作",
                input_type="text",
                user_intent="get_recommendations",
                result_success=True,
                processing_time=1.5,
                timestamp=datetime.utcnow()
            ),
            UserInteraction(
                user_id=test_user_id,
                input_content="我对区块链和DeFi很感兴趣",
                input_type="text",
                user_intent="chat",
                result_success=True,
                processing_time=0.8,
                timestamp=datetime.utcnow()
            )
        ]
        
        # 将交互记录添加到偏好管理器
        recommendation_agent.preference_manager.interaction_history[test_user_id] = mock_interactions
        
        # 提取用户档案
        skills, interests = await recommendation_agent._extract_user_profile(test_user_id)
        
        print(f"📊 用户档案分析结果:")
        print(f"   识别技能: {skills}")
        print(f"   识别兴趣: {interests}")
        
        # 更新用户嵌入向量
        await recommendation_agent.update_user_embedding(test_user_id)
        print(f"✅ 用户嵌入向量已更新")
        
        return True
        
    except Exception as e:
        print(f"❌ 用户档案提取演示失败: {e}")
        return False


async def demo_smart_coordinator_integration():
    """演示智能协调器集成推荐功能"""
    print("\n🧠 智能协调器推荐集成演示")
    print("="*50)
    
    try:
        # 创建带数据库会话的智能协调器
        db_session = MockDBSession()
        coordinator = SmartCoordinator(db_session=db_session)
        await coordinator.initialize()
        
        print("✅ 智能协调器初始化成功")
        
        # 测试推荐相关的用户输入
        test_inputs = [
            "推荐一些适合我的bounty任务",
            "有什么好的编程任务吗？",
            "我想找Web3相关的工作",
            "根据我的技能推荐任务"
        ]
        
        user_id = "integration_test_user"
        
        for i, input_text in enumerate(test_inputs, 1):
            print(f"\n💬 测试输入 {i}: {input_text}")
            
            user_input = UserInput.create(input_text, user_id)
            result = await coordinator.process_user_input(user_input)
            
            print(f"   ✅ 处理成功: {result.success}")
            print(f"   🎯 识别意图: {result.user_intent}")
            print(f"   💬 回复: {result.response_message[:150]}...")
            
            if result.suggestions:
                print(f"   💡 建议: {', '.join(result.suggestions[:2])}")
        
        return True
        
    except Exception as e:
        print(f"❌ 智能协调器集成演示失败: {e}")
        return False


async def demo_recommendation_scoring():
    """演示推荐评分算法"""
    print("\n📊 推荐评分算法演示")
    print("="*50)
    
    try:
        db_session = MockDBSession()
        recommendation_agent = BountyRecommendationAgent(db_session)
        await recommendation_agent.initialize()
        
        # 创建测试用户上下文
        user_preferences = UserPreferences(
            user_id="scoring_test_user",
            output_format=OutputFormat.STRUCTURED,
            analysis_focus=[AnalysisFocus.TECHNICAL, AnalysisFocus.BUSINESS],
            language="中文",
            task_types=["programming", "web3"],
            quality_threshold=0.8
        )
        
        context = RecommendationContext(
            user_id="scoring_test_user",
            user_preferences=user_preferences,
            user_skills=["python", "solidity", "javascript"],
            user_interests=["web3", "defi", "blockchain"],
            recent_interactions=[
                {
                    "input_content": "我想找智能合约开发的工作",
                    "input_type": "text",
                    "result_success": True,
                    "timestamp": "2024-01-01T00:00:00"
                }
            ]
        )
        
        # 获取候选任务
        candidate_tasks = await recommendation_agent._get_candidate_tasks(context)
        print(f"📋 获取到 {len(candidate_tasks)} 个候选任务")
        
        # 计算评分
        scored_tasks = await recommendation_agent._score_tasks(candidate_tasks, context)
        print(f"📊 评分完成，{len(scored_tasks)} 个任务通过阈值")
        
        # 显示评分结果
        for task, score, reasons in scored_tasks:
            print(f"\n🎯 任务: {task['title']}")
            print(f"   评分: {score:.2f}")
            print(f"   原因: {', '.join(reasons)}")
            print(f"   标签: {', '.join(task.get('tags', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ 推荐评分演示失败: {e}")
        return False


async def demo_api_integration():
    """演示API集成"""
    print("\n🌐 API集成演示")
    print("="*50)
    
    try:
        print("📡 推荐API端点:")
        print("   GET /api/v1/multi-agent/recommendations")
        print("   POST /api/v1/multi-agent/ask-recommendations")
        print("   POST /api/v1/multi-agent/update-user-profile")
        
        print("\n📝 API使用示例:")
        
        # 获取推荐的curl示例
        print("\n1. 获取推荐:")
        print('curl -X GET "http://localhost:8000/api/v1/multi-agent/recommendations?limit=5" \\')
        print('  -H "Authorization: Bearer your-token"')
        
        # 自然语言推荐请求示例
        print("\n2. 自然语言推荐请求:")
        print('curl -X POST "http://localhost:8000/api/v1/multi-agent/ask-recommendations" \\')
        print('  -H "Authorization: Bearer your-token" \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"message": "推荐一些Python和Web3相关的任务"}\'')
        
        # 更新用户档案示例
        print("\n3. 更新用户档案:")
        print('curl -X POST "http://localhost:8000/api/v1/multi-agent/update-user-profile" \\')
        print('  -H "Authorization: Bearer your-token" \\')
        print('  -H "Content-Type: application/json" \\')
        print('  -d \'{"skills": ["python", "solidity"], "interests": ["web3", "defi"]}\'')
        
        print("\n✅ API集成信息展示完成")
        return True
        
    except Exception as e:
        print(f"❌ API集成演示失败: {e}")
        return False


async def main():
    """主演示函数"""
    print("🎉 BountyGo RAG推荐系统演示")
    print("🤖 智能推荐 + 用户偏好学习 + 多Agent协作")
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
        ("推荐Agent基础功能", demo_recommendation_agent),
        ("用户档案提取", demo_user_profile_extraction),
        ("智能协调器集成", demo_smart_coordinator_integration),
        ("推荐评分算法", demo_recommendation_scoring),
        ("API集成", demo_api_integration),
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
    
    print("\n🚀 RAG推荐系统特性:")
    print("- 🧠 基于用户交互历史的智能档案提取")
    print("- 🎯 多维度匹配评分（技能、兴趣、偏好、行为）")
    print("- 📊 实时学习和偏好更新")
    print("- 🔄 与现有多Agent系统无缝集成")
    print("- 🌐 完整的API支持")
    
    print("\n📚 相关文件:")
    print("- 📖 推荐Agent: app/agent/bounty_recommendation_agent.py")
    print("- 🧠 智能协调器: app/agent/smart_coordinator.py")
    print("- 🌐 API端点: app/api/v1/endpoints/multi_agent.py")
    print("- 🧪 演示脚本: examples/bounty_recommendation_demo.py")


if __name__ == "__main__":
    asyncio.run(main())