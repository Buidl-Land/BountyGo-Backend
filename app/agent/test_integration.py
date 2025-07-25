"""
Integration test for URL parsing agent functionality.
"""
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agent.config import PPIOModelConfig
from app.agent.url_parsing_agent import URLParsingAgent
from app.agent.models import WebContent, TaskInfo


async def test_url_parsing_agent_integration():
    """测试URL解析代理集成功能"""
    
    # 创建测试配置
    config = PPIOModelConfig(
        api_key="sk_test_key_12345",
        base_url="https://api.ppinfra.com/v3/openai",
        model_name="qwen/qwen3-coder-480b-a35b-instruct"
    )
    
    # 创建测试内容
    web_content = WebContent(
        url="https://example.com/task",
        title="Python开发任务",
        content="需要开发一个Python Web应用，使用FastAPI框架。奖励：$500。截止日期：2024-12-31。需要Python、FastAPI、数据库技能。",
        meta_description="Python开发任务描述",
        extracted_at=datetime.utcnow()
    )
    
    # 模拟AI响应
    mock_ai_response = {
        "title": "Python Web应用开发",
        "description": "使用FastAPI框架开发Web应用",
        "reward": 500.0,
        "reward_currency": "USD",
        "deadline": "2024-12-31",
        "tags": ["python", "fastapi", "web开发"],
        "difficulty_level": "中级",
        "estimated_hours": 40
    }
    
    # 使用模拟对象测试
    with patch('app.agent.url_parsing_agent.PPIOModelClient') as mock_ppio_client:
        
        # 设置模拟客户端
        mock_client_instance = Mock()
        
        # 创建异步模拟函数
        async def mock_chat_completion(*args, **kwargs):
            return json.dumps(mock_ai_response)
        
        mock_client_instance.chat_completion = mock_chat_completion
        mock_ppio_client.return_value = mock_client_instance
        
        # 创建代理并测试
        agent = URLParsingAgent(config)
        
        # 测试代理信息
        info = agent.get_agent_info()
        assert info["role_name"] == "URL Content Analyzer"
        assert info["model_name"] == config.model_name
        assert info["initialized"] is True
        print("✓ Agent info test passed")
        
        # 测试内容分析
        result = await agent.analyze_content(web_content)
        
        assert isinstance(result, TaskInfo)
        assert result.title == mock_ai_response["title"]
        assert result.reward == mock_ai_response["reward"]
        assert result.reward_currency == mock_ai_response["reward_currency"]
        assert len(result.tags) == 3
        assert result.difficulty_level == mock_ai_response["difficulty_level"]
        assert result.estimated_hours == mock_ai_response["estimated_hours"]
        print("✓ Content analysis test passed")
        
        # 测试代理测试功能
        test_result = await agent.test_agent()
        assert test_result is True
        print("✓ Agent test functionality passed")
        
        # 测试重置对话
        agent.reset_conversation()
        assert agent.client is not None
        print("✓ Conversation reset test passed")
    
    print("All integration tests passed!")


def test_validation_functions():
    """测试验证函数"""
    config = PPIOModelConfig(
        api_key="sk_test_key_12345",
        base_url="https://api.ppinfra.com/v3/openai",
        model_name="qwen/qwen3-coder-480b-a35b-instruct"
    )
    
    with patch('app.agent.url_parsing_agent.PPIOModelClient'):
        agent = URLParsingAgent(config)
        
        # 测试响应数据验证
        print("Testing response data validation...")
        
        # 正常数据
        valid_data = {
            "title": "Test Task",
            "description": "Test description",
            "reward": 100.0,
            "reward_currency": "USD",
            "estimated_hours": 10
        }
        result = agent._validate_response_data(valid_data)
        assert result["title"] == "Test Task"
        assert result["reward"] == 100.0
        
        # 无效奖励金额
        invalid_reward_data = {
            "title": "Test Task",
            "reward": "invalid"
        }
        result = agent._validate_response_data(invalid_reward_data)
        assert result["reward"] is None
        
        # 负数奖励
        negative_reward_data = {
            "title": "Test Task",
            "reward": -100
        }
        result = agent._validate_response_data(negative_reward_data)
        assert result["reward"] is None
        
        # 过长标题
        long_title_data = {
            "title": "A" * 300,
            "description": "Test"
        }
        result = agent._validate_response_data(long_title_data)
        assert len(result["title"]) == 200
        
        print("✓ Response data validation tests passed")
        
        # 测试标签验证
        print("Testing tag validation...")
        
        # 正常标签
        tags = agent._validate_tags(["Python", "FastAPI", "Web开发"])
        assert len(tags) == 3
        assert "python" in tags
        
        # 重复标签
        tags = agent._validate_tags(["Python", "python", "PYTHON"])
        assert len(tags) == 1
        
        # 过长标签
        long_tag = "a" * 100
        tags = agent._validate_tags([long_tag])
        assert len(tags) == 0
        
        # 过多标签
        many_tags = [f"tag{i}" for i in range(20)]
        tags = agent._validate_tags(many_tags)
        assert len(tags) == 10
        
        print("✓ Tag validation tests passed")
        
        # 测试难度等级验证
        print("Testing difficulty level validation...")
        
        assert agent._validate_difficulty_level("初级") == "初级"
        assert agent._validate_difficulty_level("beginner") == "初级"
        assert agent._validate_difficulty_level("easy") == "初级"
        assert agent._validate_difficulty_level("invalid") is None
        
        print("✓ Difficulty level validation tests passed")
        
        # 测试日期解析
        print("Testing deadline parsing...")
        
        deadline = agent._parse_deadline("2024-12-31")
        assert deadline.year == 2024
        assert deadline.month == 12
        assert deadline.day == 31
        
        deadline = agent._parse_deadline("2024/12/31")
        assert deadline is not None
        
        deadline = agent._parse_deadline("invalid date")
        assert deadline is None
        
        print("✓ Deadline parsing tests passed")
    
    print("All validation tests passed!")


if __name__ == "__main__":
    # 运行集成测试
    asyncio.run(test_url_parsing_agent_integration())
    
    # 运行验证测试
    test_validation_functions()
    
    print("\n🎉 All tests completed successfully!")