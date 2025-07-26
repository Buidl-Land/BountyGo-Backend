"""
Tests for URLParsingAgent functionality.
"""
import json
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from app.agent.url_parsing_agent import URLParsingAgent
from app.agent.config import PPIOModelConfig
from app.agent.models import WebContent, TaskInfo
from app.agent.exceptions import ModelAPIError, ConfigurationError


class TestURLParsingAgent:
    """URLParsingAgent测试类"""
    
    @pytest.fixture
    def mock_config(self):
        """模拟PPIO配置"""
        return PPIOModelConfig(
            api_key="sk_test_key_12345",
            base_url="https://api.ppinfra.com/v3/openai",
            model_name="qwen/qwen3-coder-480b-a35b-instruct",
            max_tokens=4000,
            temperature=0.1
        )
    
    @pytest.fixture
    def sample_web_content(self):
        """示例网页内容"""
        return WebContent(
            url="https://example.com/task",
            title="Python开发任务",
            content="需要开发一个Python Web应用，使用FastAPI框架。奖励：$500。截止日期：2024-12-31。需要Python、FastAPI、数据库技能。",
            meta_description="Python开发任务描述",
            extracted_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_ai_response(self):
        """示例AI响应"""
        return {
            "title": "Python Web应用开发",
            "summary": "使用FastAPI框架开发Web应用",
            "description": "使用FastAPI框架开发Web应用，包括数据库设计和API开发",
            "category": "开发实战",
            "reward_details": "一等奖500 USD",
            "reward_type": "每人",
            "reward": 500.0,
            "reward_currency": "USD",
            "deadline": 1735689600,
            "tags": ["python", "fastapi", "web开发"],
            "difficulty_level": "中级",
            "estimated_hours": 40,
            "organizer_name": "测试主办方",
            "external_link": "https://example.com/task"
        }
    
    @patch('app.agent.url_parsing_agent.PPIOModelClient')
    def test_agent_initialization(self, mock_client_class, mock_config):
        """测试代理初始化"""
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        
        agent = URLParsingAgent(mock_config)
        
        # 验证PPIO客户端创建
        mock_client_class.assert_called_once_with(mock_config)
        assert agent.client == mock_client_instance
    
    @patch('app.agent.url_parsing_agent.PPIOModelClient')
    def test_agent_initialization_failure(self, mock_client_class, mock_config):
        """测试代理初始化失败"""
        mock_client_class.side_effect = Exception("Client creation failed")
        
        with pytest.raises(ConfigurationError):
            URLParsingAgent(mock_config)
    
    @patch('app.agent.url_parsing_agent.PPIOModelClient')
    def test_system_prompt_generation(self, mock_client_class, mock_config):
        """测试系统提示生成"""
        mock_client_class.return_value = Mock()
        agent = URLParsingAgent(mock_config)
        system_prompt = agent._get_system_prompt()
        
        assert "URL内容分析专家" in system_prompt
        assert "JSON格式" in system_prompt
        assert "title" in system_prompt
    
    @patch('app.agent.url_parsing_agent.PPIOModelClient')
    def test_build_analysis_content(self, mock_client_class, mock_config, sample_web_content):
        """测试分析内容构建"""
        mock_client_class.return_value = Mock()
        agent = URLParsingAgent(mock_config)
        content = agent._build_analysis_content(sample_web_content)
        
        assert sample_web_content.url in content
        assert sample_web_content.title in content
        assert sample_web_content.content in content
        assert sample_web_content.meta_description in content
    
    @patch('app.agent.url_parsing_agent.PPIOModelClient')
    def test_parse_response_success(self, mock_client_class, mock_config, sample_ai_response):
        """测试响应解析成功"""
        mock_client_class.return_value = Mock()
        agent = URLParsingAgent(mock_config)
        
        response_json = json.dumps(sample_ai_response)
        task_info = agent._parse_response(response_json)
        
        assert isinstance(task_info, TaskInfo)
        assert task_info.title == sample_ai_response["title"]
        assert task_info.summary == sample_ai_response["summary"]
        assert task_info.category == sample_ai_response["category"]
        assert task_info.reward_details == sample_ai_response["reward_details"]
        assert task_info.reward_type == sample_ai_response["reward_type"]
        assert task_info.reward == sample_ai_response["reward"]
        assert task_info.reward_currency == sample_ai_response["reward_currency"]
        assert task_info.deadline == sample_ai_response["deadline"]
        assert len(task_info.tags) == 3
        assert task_info.difficulty_level == sample_ai_response["difficulty_level"]
        assert task_info.estimated_hours == sample_ai_response["estimated_hours"]
        assert task_info.organizer_name == sample_ai_response["organizer_name"]
        assert task_info.external_link == sample_ai_response["external_link"]
    
    @patch('app.agent.url_parsing_agent.PPIOModelClient')
    def test_parse_response_with_markdown(self, mock_client_class, mock_config, sample_ai_response):
        """测试解析带markdown标记的响应"""
        mock_client_class.return_value = Mock()
        agent = URLParsingAgent(mock_config)
        
        response_json = f"```json\n{json.dumps(sample_ai_response)}\n```"
        task_info = agent._parse_response(response_json)
        
        assert isinstance(task_info, TaskInfo)
        assert task_info.title == sample_ai_response["title"]
    
    def test_parse_response_invalid_json(self, mock_config):
        """测试解析无效JSON响应"""
        with patch('app.agent.url_parsing_agent.ModelFactory'), \
             patch('app.agent.url_parsing_agent.ChatAgent'):
            agent = URLParsingAgent(mock_config)
            
            with pytest.raises(ModelAPIError):
                agent._parse_response("invalid json content")
    
    def test_parse_response_missing_title(self, mock_config):
        """测试解析缺少标题的响应"""
        with patch('app.agent.url_parsing_agent.ModelFactory'), \
             patch('app.agent.url_parsing_agent.ChatAgent'):
            agent = URLParsingAgent(mock_config)
            
            response_data = {"description": "test description"}
            response_json = json.dumps(response_data)
            
            with pytest.raises(ModelAPIError):
                agent._parse_response(response_json)
    
    def test_validate_response_data(self, mock_config):
        """测试响应数据验证"""
        with patch('app.agent.url_parsing_agent.ModelFactory'), \
             patch('app.agent.url_parsing_agent.ChatAgent'):
            agent = URLParsingAgent(mock_config)
            
            # 测试正常数据
            valid_data = {
                "title": "Test Task",
                "description": "Test description",
                "reward": 100.0,
                "reward_currency": "USD"
            }
            result = agent._validate_response_data(valid_data)
            assert result["title"] == "Test Task"
            assert result["reward"] == 100.0
            
            # 测试无效奖励金额
            invalid_reward_data = {
                "title": "Test Task",
                "reward": "invalid"
            }
            result = agent._validate_response_data(invalid_reward_data)
            assert result["reward"] is None
            
            # 测试负数奖励
            negative_reward_data = {
                "title": "Test Task", 
                "reward": -100
            }
            result = agent._validate_response_data(negative_reward_data)
            assert result["reward"] is None
    
    def test_parse_deadline(self, mock_config):
        """测试截止日期解析"""
        with patch('app.agent.url_parsing_agent.ModelFactory'), \
             patch('app.agent.url_parsing_agent.ChatAgent'):
            agent = URLParsingAgent(mock_config)
            
            # 测试标准格式
            deadline = agent._parse_deadline("2024-12-31")
            assert deadline.year == 2024
            assert deadline.month == 12
            assert deadline.day == 31
            
            # 测试其他格式
            deadline = agent._parse_deadline("2024/12/31")
            assert deadline is not None
            
            # 测试无效格式
            deadline = agent._parse_deadline("invalid date")
            assert deadline is None
            
            # 测试空值
            deadline = agent._parse_deadline(None)
            assert deadline is None
    
    def test_validate_tags(self, mock_config):
        """测试标签验证"""
        with patch('app.agent.url_parsing_agent.ModelFactory'), \
             patch('app.agent.url_parsing_agent.ChatAgent'):
            agent = URLParsingAgent(mock_config)
            
            # 测试正常标签
            tags = agent._validate_tags(["Python", "FastAPI", "Web开发"])
            assert len(tags) == 3
            assert "python" in tags
            assert "fastapi" in tags
            
            # 测试重复标签
            tags = agent._validate_tags(["Python", "python", "PYTHON"])
            assert len(tags) == 1
            assert tags[0] == "python"
            
            # 测试过长标签
            long_tag = "a" * 100
            tags = agent._validate_tags([long_tag])
            assert len(tags) == 0
            
            # 测试非字符串标签
            tags = agent._validate_tags([123, None, "valid"])
            assert len(tags) == 1
            assert tags[0] == "valid"
    
    def test_validate_difficulty_level(self, mock_config):
        """测试难度等级验证"""
        with patch('app.agent.url_parsing_agent.ModelFactory'), \
             patch('app.agent.url_parsing_agent.ChatAgent'):
            agent = URLParsingAgent(mock_config)
            
            # 测试中文难度等级
            assert agent._validate_difficulty_level("初级") == "初级"
            assert agent._validate_difficulty_level("中级") == "中级"
            assert agent._validate_difficulty_level("高级") == "高级"
            
            # 测试英文难度等级
            assert agent._validate_difficulty_level("beginner") == "初级"
            assert agent._validate_difficulty_level("intermediate") == "中级"
            assert agent._validate_difficulty_level("advanced") == "高级"
            
            # 测试无效难度等级
            assert agent._validate_difficulty_level("invalid") is None
            assert agent._validate_difficulty_level(None) is None
    
    @patch('app.agent.url_parsing_agent.ModelFactory')
    @patch('app.agent.url_parsing_agent.ChatAgent')
    async def test_analyze_content_success(self, mock_chat_agent, mock_model_factory, 
                                         mock_config, sample_web_content, sample_ai_response):
        """测试内容分析成功"""
        # 设置模拟
        mock_model = Mock()
        mock_model_factory.create.return_value = mock_model
        
        mock_agent_instance = Mock()
        mock_response = Mock()
        mock_response.msgs = [Mock()]
        mock_response.msgs[0].content = json.dumps(sample_ai_response)
        mock_agent_instance.step.return_value = mock_response
        mock_chat_agent.return_value = mock_agent_instance
        
        # 测试分析
        agent = URLParsingAgent(mock_config)
        result = await agent.analyze_content(sample_web_content)
        
        assert isinstance(result, TaskInfo)
        assert result.title == sample_ai_response["title"]
        assert result.reward == sample_ai_response["reward"]
    
    @patch('app.agent.url_parsing_agent.ModelFactory')
    @patch('app.agent.url_parsing_agent.ChatAgent')
    async def test_analyze_content_no_response(self, mock_chat_agent, mock_model_factory, 
                                             mock_config, sample_web_content):
        """测试内容分析无响应"""
        # 设置模拟
        mock_model = Mock()
        mock_model_factory.create.return_value = mock_model
        
        mock_agent_instance = Mock()
        mock_response = Mock()
        mock_response.msgs = []
        mock_agent_instance.step.return_value = mock_response
        mock_chat_agent.return_value = mock_agent_instance
        
        # 测试分析
        agent = URLParsingAgent(mock_config)
        
        with pytest.raises(ModelAPIError):
            await agent.analyze_content(sample_web_content)
    
    @patch('app.agent.url_parsing_agent.ModelFactory')
    @patch('app.agent.url_parsing_agent.ChatAgent')
    async def test_analyze_content_agent_not_initialized(self, mock_chat_agent, mock_model_factory, 
                                                        mock_config, sample_web_content):
        """测试代理未初始化时的内容分析"""
        # 设置模拟
        mock_model = Mock()
        mock_model_factory.create.return_value = mock_model
        mock_chat_agent.return_value = Mock()
        
        agent = URLParsingAgent(mock_config)
        agent.agent = None  # 模拟未初始化
        
        with pytest.raises(ConfigurationError):
            await agent.analyze_content(sample_web_content)
    
    def test_get_agent_info(self, mock_config):
        """测试获取代理信息"""
        with patch('app.agent.url_parsing_agent.ModelFactory'), \
             patch('app.agent.url_parsing_agent.ChatAgent'):
            agent = URLParsingAgent(mock_config)
            info = agent.get_agent_info()
            
            assert info["role_name"] == "URL Content Analyzer"
            assert info["model_name"] == mock_config.model_name
            assert info["initialized"] is True
    
    @patch('app.agent.url_parsing_agent.ModelFactory')
    @patch('app.agent.url_parsing_agent.ChatAgent')
    async def test_test_agent_success(self, mock_chat_agent, mock_model_factory, mock_config):
        """测试代理测试成功"""
        # 设置模拟
        mock_model = Mock()
        mock_model_factory.create.return_value = mock_model
        
        mock_agent_instance = Mock()
        mock_response = Mock()
        mock_response.msgs = [Mock()]
        mock_response.msgs[0].content = json.dumps({
            "title": "Test Task",
            "description": "Test description"
        })
        mock_agent_instance.step.return_value = mock_response
        mock_chat_agent.return_value = mock_agent_instance
        
        agent = URLParsingAgent(mock_config)
        result = await agent.test_agent()
        
        assert result is True
    
    @patch('app.agent.url_parsing_agent.ModelFactory')
    @patch('app.agent.url_parsing_agent.ChatAgent')
    async def test_test_agent_failure(self, mock_chat_agent, mock_model_factory, mock_config):
        """测试代理测试失败"""
        # 设置模拟
        mock_model = Mock()
        mock_model_factory.create.return_value = mock_model
        
        mock_agent_instance = Mock()
        mock_agent_instance.step.side_effect = Exception("Test failed")
        mock_chat_agent.return_value = mock_agent_instance
        
        agent = URLParsingAgent(mock_config)
        result = await agent.test_agent()
        
        assert result is False
    
    @patch('app.agent.url_parsing_agent.ModelFactory')
    @patch('app.agent.url_parsing_agent.ChatAgent')
    def test_reset_conversation(self, mock_chat_agent, mock_model_factory, mock_config):
        """测试重置对话历史"""
        mock_model = Mock()
        mock_model_factory.create.return_value = mock_model
        mock_chat_agent.return_value = Mock()
        
        agent = URLParsingAgent(mock_config)
        original_agent = agent.agent
        
        agent.reset_conversation()
        
        # 验证代理被重新初始化
        assert agent.agent is not None
        # 注意：由于重新初始化，agent实例会不同
        mock_chat_agent.assert_called()


class TestURLParsingAgentIntegration:
    """URLParsingAgent集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self):
        """测试完整的分析工作流程"""
        # 这个测试需要真实的API密钥，通常在CI/CD中跳过
        pytest.skip("Integration test requires real API key")
        
        config = PPIOModelConfig(
            api_key="sk_real_api_key",
            model_name="qwen/qwen3-coder-480b-a35b-instruct"
        )
        
        web_content = WebContent(
            url="https://example.com/task",
            title="Python开发任务",
            content="开发一个使用FastAPI的Web应用，奖励$500，截止2024-12-31",
            extracted_at=datetime.utcnow()
        )
        
        agent = URLParsingAgent(config)
        result = await agent.analyze_content(web_content)
        
        assert isinstance(result, TaskInfo)
        assert result.title is not None
        assert len(result.title) > 0


if __name__ == "__main__":
    pytest.main([__file__])