"""
Standalone tests for PPIO model configuration.
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from pydantic import ValidationError

from app.agent.config import PPIOModelConfig


class TestPPIOModelConfig:
    """Test PPIO model configuration"""
    
    def test_valid_config(self):
        """Test valid configuration"""
        config = PPIOModelConfig(
            api_key="sk_test_key_12345",
            base_url="https://api.ppinfra.com/v3/openai",
            model_name="qwen/qwen3-coder-480b-a35b-instruct"
        )
        
        assert config.api_key == "sk_test_key_12345"
        assert config.base_url == "https://api.ppinfra.com/v3/openai"
        assert config.model_name == "qwen/qwen3-coder-480b-a35b-instruct"
        assert config.max_tokens == 4000
        assert config.temperature == 0.1
    
    def test_default_values(self):
        """Test default configuration values"""
        config = PPIOModelConfig(api_key="sk_test_key_12345")
        
        assert config.base_url == "https://api.ppinfra.com/v3/openai"
        assert config.model_name == "qwen/qwen3-coder-480b-a35b-instruct"
        assert config.max_tokens == 4000
        assert config.temperature == 0.1
        assert config.timeout == 60
        assert config.max_retries == 3

    def test_api_key_validation(self):
        """Test API key validation"""
        # Valid API key
        config = PPIOModelConfig(api_key="sk_valid_key_12345")
        assert config.api_key == "sk_valid_key_12345"
        
        # Invalid API key - empty
        with pytest.raises(ValidationError) as exc_info:
            PPIOModelConfig(api_key="")
        assert "API密钥不能为空" in str(exc_info.value)
        
        # Invalid API key - wrong format
        with pytest.raises(ValidationError) as exc_info:
            PPIOModelConfig(api_key="invalid_key")
        assert "API密钥格式无效" in str(exc_info.value)
        
        # Invalid API key - too short
        with pytest.raises(ValidationError) as exc_info:
            PPIOModelConfig(api_key="sk_short")
        assert "API密钥长度过短" in str(exc_info.value)

    def test_temperature_validation(self):
        """Test temperature parameter validation"""
        # Valid temperature
        config = PPIOModelConfig(api_key="sk_test_key_12345", temperature=0.5)
        assert config.temperature == 0.5
        
        # Invalid temperature - too low
        with pytest.raises(ValidationError) as exc_info:
            PPIOModelConfig(api_key="sk_test_key_12345", temperature=-0.1)
        assert "温度参数必须在0-2之间" in str(exc_info.value)
        
        # Invalid temperature - too high
        with pytest.raises(ValidationError) as exc_info:
            PPIOModelConfig(api_key="sk_test_key_12345", temperature=2.1)
        assert "温度参数必须在0-2之间" in str(exc_info.value)

    def test_max_tokens_validation(self):
        """Test max tokens validation"""
        # Valid max_tokens
        config = PPIOModelConfig(api_key="sk_test_key_12345", max_tokens=2000)
        assert config.max_tokens == 2000
        
        # Invalid max_tokens - too low
        with pytest.raises(ValidationError) as exc_info:
            PPIOModelConfig(api_key="sk_test_key_12345", max_tokens=0)
        assert "最大token数必须在1-32000之间" in str(exc_info.value)
        
        # Invalid max_tokens - too high
        with pytest.raises(ValidationError) as exc_info:
            PPIOModelConfig(api_key="sk_test_key_12345", max_tokens=50000)
        assert "最大token数必须在1-32000之间" in str(exc_info.value)

    def test_supported_models(self):
        """Test supported models list"""
        config = PPIOModelConfig(api_key="sk_test_key_12345")
        models = config.get_supported_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert "qwen/qwen3-coder-480b-a35b-instruct" in models
        assert "moonshotai/kimi-k2-instruct" in models

    def test_structured_output_support(self):
        """Test structured output support detection"""
        # Test with supported model
        config = PPIOModelConfig(
            api_key="sk_test_key_12345",
            model_name="qwen/qwen3-coder-480b-a35b-instruct"
        )
        assert config.supports_structured_output() is True
        
        # Test with unsupported model
        config = PPIOModelConfig(
            api_key="sk_test_key_12345",
            model_name="unsupported/model"
        )
        assert config.supports_structured_output() is False

    def test_function_calling_support(self):
        """Test function calling support detection"""
        # Test with supported model
        config = PPIOModelConfig(
            api_key="sk_test_key_12345",
            model_name="moonshotai/kimi-k2-instruct"
        )
        assert config.supports_function_calling() is True
        
        # Test with unsupported model
        config = PPIOModelConfig(
            api_key="sk_test_key_12345",
            model_name="unsupported/model"
        )
        assert config.supports_function_calling() is False

    @pytest.mark.asyncio
    async def test_api_connection_validation_success(self):
        """Test successful API connection validation"""
        config = PPIOModelConfig(api_key="sk_test_key_12345")
        
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"choices": []}')
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await config.validate_api_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_api_connection_validation_invalid_key(self):
        """Test API connection validation with invalid key"""
        config = PPIOModelConfig(api_key="sk_test_key_12345")
        
        # Mock 401 response
        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.text = AsyncMock(return_value='{"error": "Invalid API key"}')
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(ValueError) as exc_info:
                await config.validate_api_connection()
            assert "API密钥无效或已过期" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_connection_validation_timeout(self):
        """Test API connection validation timeout"""
        config = PPIOModelConfig(api_key="sk_test_key_12345", timeout=1)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(ValueError) as exc_info:
                await config.validate_api_connection()
            assert "API连接超时" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_connection_validation_network_error(self):
        """Test API connection validation with network error"""
        config = PPIOModelConfig(api_key="sk_test_key_12345")
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            with pytest.raises(ValueError) as exc_info:
                await config.validate_api_connection()
            assert "API验证失败" in str(exc_info.value)