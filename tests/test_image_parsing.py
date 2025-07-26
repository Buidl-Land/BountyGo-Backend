"""
Tests for image parsing functionality.
"""
import pytest
import base64
from unittest.mock import Mock, AsyncMock, patch
from PIL import Image
import io

from app.agent.image_parsing_agent import ImageParsingAgent
from app.agent.config import PPIOModelConfig
from app.agent.models import TaskInfo
from app.agent.exceptions import ModelAPIError, ConfigurationError


class TestImageParsingAgent:
    """ImageParsingAgent测试类"""
    
    @pytest.fixture
    def mock_config(self):
        """模拟PPIO配置"""
        return PPIOModelConfig(
            api_key="sk_test_key_12345",
            base_url="https://api.ppinfra.com/v3/openai",
            model_name="baidu/ernie-4.5-vl-28b-a3b",
            max_tokens=4000,
            temperature=0.1
        )
    
    @pytest.fixture
    def sample_base64_image(self):
        """生成示例base64图片"""
        # 创建一个简单的测试图片
        img = Image.new('RGB', (100, 100), color='red')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_data = buffer.getvalue()
        return base64.b64encode(img_data).decode('utf-8')
    
    @pytest.fixture
    def sample_ai_response(self):
        """示例AI响应"""
        return {
            "title": "Python开发任务",
            "summary": "开发一个Web爬虫工具",
            "description": "使用Python和BeautifulSoup开发网页爬虫工具，需要处理动态内容",
            "category": "开发实战",
            "reward_details": "完成奖励500 USDC",
            "reward_type": "每人",
            "reward": 500.0,
            "reward_currency": "USDC",
            "deadline": 1735689600,
            "tags": ["python", "爬虫", "beautifulsoup"],
            "difficulty_level": "中级",
            "estimated_hours": 30,
            "organizer_name": "技术团队",
            "external_link": "https://example.com/task"
        }
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    def test_agent_initialization(self, mock_client_class, mock_config):
        """测试代理初始化"""
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        
        agent = ImageParsingAgent(mock_config)
        
        # 验证PPIO客户端创建
        mock_client_class.assert_called_once_with(mock_config)
        assert agent.client == mock_client_instance
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    def test_agent_initialization_failure(self, mock_client_class, mock_config):
        """测试代理初始化失败"""
        mock_client_class.side_effect = Exception("Client creation failed")
        
        with pytest.raises(ConfigurationError):
            ImageParsingAgent(mock_config)
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    def test_system_prompt_generation(self, mock_client_class, mock_config):
        """测试系统提示生成"""
        mock_client_class.return_value = Mock()
        agent = ImageParsingAgent(mock_config)
        system_prompt = agent._get_system_prompt()
        
        assert "图片内容分析专家" in system_prompt
        assert "JSON格式" in system_prompt
        assert "title" in system_prompt
    
    def test_validate_base64_image_valid(self, mock_config, sample_base64_image):
        """测试有效base64图片验证"""
        with patch('app.agent.image_parsing_agent.PPIOModelClient'):
            agent = ImageParsingAgent(mock_config)
            
            # 测试带前缀的base64
            data_url = f"data:image/png;base64,{sample_base64_image}"
            result = agent._validate_base64_image(data_url)
            assert result == sample_base64_image
            
            # 测试不带前缀的base64
            result = agent._validate_base64_image(sample_base64_image)
            assert result == sample_base64_image
    
    def test_validate_base64_image_invalid(self, mock_config):
        """测试无效base64图片验证"""
        with patch('app.agent.image_parsing_agent.PPIOModelClient'):
            agent = ImageParsingAgent(mock_config)
            
            # 测试无效base64
            with pytest.raises(ValueError):
                agent._validate_base64_image("invalid_base64_data")
            
            # 测试空字符串
            with pytest.raises(ValueError):
                agent._validate_base64_image("")
    
    def test_validate_image_format(self, mock_config, sample_base64_image):
        """测试图片格式验证"""
        with patch('app.agent.image_parsing_agent.PPIOModelClient'):
            agent = ImageParsingAgent(mock_config)
            
            # 应该通过验证（PNG格式）
            try:
                agent._validate_image_format(sample_base64_image)
            except Exception:
                pytest.fail("Valid PNG image should pass validation")
    
    def test_validate_image_format_invalid(self, mock_config):
        """测试无效图片格式验证"""
        with patch('app.agent.image_parsing_agent.PPIOModelClient'):
            agent = ImageParsingAgent(mock_config)
            
            # 测试无效图片数据
            invalid_data = base64.b64encode(b"not an image").decode('utf-8')
            with pytest.raises(ValueError):
                agent._validate_image_format(invalid_data)
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    def test_parse_response_success(self, mock_client_class, mock_config, sample_ai_response):
        """测试响应解析成功"""
        mock_client_class.return_value = Mock()
        agent = ImageParsingAgent(mock_config)
        
        response_json = json.dumps(sample_ai_response)
        task_info = agent._parse_response(response_json)
        
        assert isinstance(task_info, TaskInfo)
        assert task_info.title == sample_ai_response["title"]
        assert task_info.summary == sample_ai_response["summary"]
        assert task_info.category == sample_ai_response["category"]
        assert task_info.reward == sample_ai_response["reward"]
        assert task_info.reward_currency == sample_ai_response["reward_currency"]
        assert len(task_info.tags) == 3
        assert task_info.difficulty_level == sample_ai_response["difficulty_level"]
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    def test_parse_response_with_markdown(self, mock_client_class, mock_config, sample_ai_response):
        """测试解析带markdown标记的响应"""
        mock_client_class.return_value = Mock()
        agent = ImageParsingAgent(mock_config)
        
        response_json = f"```json\\n{json.dumps(sample_ai_response)}\\n```"
        task_info = agent._parse_response(response_json)
        
        assert isinstance(task_info, TaskInfo)
        assert task_info.title == sample_ai_response["title"]
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    def test_parse_response_invalid_json(self, mock_client_class, mock_config):
        """测试解析无效JSON响应"""
        mock_client_class.return_value = Mock()
        agent = ImageParsingAgent(mock_config)
        
        with pytest.raises(ModelAPIError):
            agent._parse_response("invalid json content")
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    async def test_analyze_image_success(self, mock_client_class, mock_config, 
                                       sample_base64_image, sample_ai_response):
        """测试图片分析成功"""
        # 设置模拟
        mock_client_instance = Mock()
        mock_client_instance.chat_completion = AsyncMock(return_value=json.dumps(sample_ai_response))
        mock_client_class.return_value = mock_client_instance
        
        # 测试分析
        agent = ImageParsingAgent(mock_config)
        result = await agent.analyze_image(
            image_base64=f"data:image/png;base64,{sample_base64_image}",
            additional_prompt="请分析任务信息"
        )
        
        assert isinstance(result, TaskInfo)
        assert result.title == sample_ai_response["title"]
        assert result.reward == sample_ai_response["reward"]
        
        # 验证客户端调用
        mock_client_instance.chat_completion.assert_called_once()
        call_args = mock_client_instance.chat_completion.call_args[0][0]
        assert len(call_args) == 2  # system + user message
        assert call_args[0]["role"] == "system"
        assert call_args[1]["role"] == "user"
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    async def test_analyze_image_no_response(self, mock_client_class, mock_config, sample_base64_image):
        """测试图片分析无响应"""
        # 设置模拟
        mock_client_instance = Mock()
        mock_client_instance.chat_completion = AsyncMock(return_value="")
        mock_client_class.return_value = mock_client_instance
        
        # 测试分析
        agent = ImageParsingAgent(mock_config)
        
        with pytest.raises(ModelAPIError):
            await agent.analyze_image(
                image_base64=f"data:image/png;base64,{sample_base64_image}"
            )
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    async def test_analyze_image_client_not_initialized(self, mock_client_class, mock_config, sample_base64_image):
        """测试客户端未初始化时的图片分析"""
        mock_client_class.return_value = Mock()
        
        agent = ImageParsingAgent(mock_config)
        agent.client = None  # 模拟未初始化
        
        with pytest.raises(ConfigurationError):
            await agent.analyze_image(
                image_base64=f"data:image/png;base64,{sample_base64_image}"
            )
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    def test_get_agent_info(self, mock_client_class, mock_config):
        """测试获取代理信息"""
        mock_client_class.return_value = Mock()
        agent = ImageParsingAgent(mock_config)
        info = agent.get_agent_info()
        
        assert info["role_name"] == "Image Content Analyzer"
        assert info["model_name"] == mock_config.model_name
        assert info["initialized"] is True
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    async def test_test_agent_success(self, mock_client_class, mock_config):
        """测试代理测试成功"""
        # 设置模拟
        mock_client_instance = Mock()
        mock_client_instance.chat_completion = AsyncMock(return_value=json.dumps({
            "title": "Test Task",
            "description": "Test description"
        }))
        mock_client_class.return_value = mock_client_instance
        
        agent = ImageParsingAgent(mock_config)
        result = await agent.test_agent()
        
        assert result is True
    
    @patch('app.agent.image_parsing_agent.PPIOModelClient')
    async def test_test_agent_failure(self, mock_client_class, mock_config):
        """测试代理测试失败"""
        # 设置模拟
        mock_client_instance = Mock()
        mock_client_instance.chat_completion = AsyncMock(side_effect=Exception("Test failed"))
        mock_client_class.return_value = mock_client_instance
        
        agent = ImageParsingAgent(mock_config)
        result = await agent.test_agent()
        
        assert result is False


class TestImageParsingIntegration:
    """图片解析集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_image_analysis_workflow(self):
        """测试完整的图片分析工作流程"""
        # 这个测试需要真实的API密钥，通常在CI/CD中跳过
        pytest.skip("Integration test requires real API key")
        
        config = PPIOModelConfig(
            api_key="sk_real_api_key",
            model_name="baidu/ernie-4.5-vl-28b-a3b"
        )
        
        # 创建测试图片
        img = Image.new('RGB', (200, 100), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_data = buffer.getvalue()
        base64_image = base64.b64encode(img_data).decode('utf-8')
        
        agent = ImageParsingAgent(config)
        result = await agent.analyze_image(
            image_base64=f"data:image/png;base64,{base64_image}",
            additional_prompt="这是一个测试图片，请分析其中的任务信息"
        )
        
        assert isinstance(result, TaskInfo)
        assert result.title is not None
        assert len(result.title) > 0


if __name__ == "__main__":
    import json
    pytest.main([__file__])