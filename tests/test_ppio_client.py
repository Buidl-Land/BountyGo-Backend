"""
Tests for PPIO model client.
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

# Import without triggering app initialization
import sys
sys.path.append('.')
from app.agent.config import PPIOModelConfig
from app.agent.client import PPIOModelClient
from app.agent.exceptions import ModelAPIError, ConfigurationError


class TestPPIOModelClient:
    """Test PPIO model client"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = PPIOModelConfig(
            api_key="sk_test_key_12345",
            model_name="qwen/qwen3-coder-480b-a35b-instruct"
        )
        self.client = PPIOModelClient(self.config)
    
    def test_client_initialization(self):
        """Test client initialization"""
        assert self.client.config == self.config
        assert self.client.request_count == 0
        assert self.client.total_tokens == 0
        assert self.client.error_count == 0
    
    def test_invalid_config(self):
        """Test client with invalid configuration"""
        # Test with empty API key
        try:
            invalid_config = PPIOModelConfig(api_key="")
            PPIOModelClient(invalid_config)
            assert False, "Should have raised ValidationError"
        except Exception:
            pass  # Expected to fail at Pydantic validation level
    
    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Test successful connection"""
        # Mock successful response
        mock_choice = Choice(
            index=0,
            message=ChatCompletionMessage(role="assistant", content="Hello!"),
            finish_reason="stop"
        )
        mock_response = ChatCompletion(
            id="test-id",
            choices=[mock_choice],
            created=1234567890,
            model="qwen/qwen3-coder-480b-a35b-instruct",
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=5, completion_tokens=2, total_tokens=7)
        )
        
        with patch.object(self.client.client.chat.completions, 'create', return_value=mock_response):
            result = await self.client.test_connection()
            assert result is True
            assert self.client.request_count == 1
            assert self.client.total_tokens == 7
    
    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test connection failure"""
        with patch.object(self.client.client.chat.completions, 'create', side_effect=Exception("Connection failed")):
            result = await self.client.test_connection()
            assert result is False
            assert self.client.error_count == 1
    
    @pytest.mark.asyncio
    async def test_extract_structured_info_json(self):
        """Test structured info extraction with JSON response"""
        json_response = '{"title": "Test Task", "description": "Test description"}'
        
        mock_choice = Choice(
            index=0,
            message=ChatCompletionMessage(role="assistant", content=json_response),
            finish_reason="stop"
        )
        mock_response = ChatCompletion(
            id="test-id",
            choices=[mock_choice],
            created=1234567890,
            model="qwen/qwen3-coder-480b-a35b-instruct",
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        )
        
        with patch.object(self.client.client.chat.completions, 'create', return_value=mock_response):
            result = await self.client.extract_structured_info(
                content="Test content",
                system_prompt="Extract task info"
            )
            
            assert result == {"title": "Test Task", "description": "Test description"}
            assert self.client.request_count == 1
            assert self.client.total_tokens == 150
    
    @pytest.mark.asyncio
    async def test_extract_structured_info_raw_text(self):
        """Test structured info extraction with raw text response"""
        raw_response = "This is not JSON"
        
        mock_choice = Choice(
            index=0,
            message=ChatCompletionMessage(role="assistant", content=raw_response),
            finish_reason="stop"
        )
        mock_response = ChatCompletion(
            id="test-id",
            choices=[mock_choice],
            created=1234567890,
            model="qwen/qwen3-coder-480b-a35b-instruct",
            object="chat.completion"
        )
        
        with patch.object(self.client.client.chat.completions, 'create', return_value=mock_response):
            result = await self.client.extract_structured_info(
                content="Test content",
                system_prompt="Extract task info"
            )
            
            assert result == {"raw_content": "This is not JSON"}
    
    @pytest.mark.asyncio
    async def test_extract_structured_info_with_response_format(self):
        """Test structured info extraction with response format"""
        json_response = '{"title": "Test Task"}'
        response_format = {"type": "json_object"}
        
        mock_choice = Choice(
            index=0,
            message=ChatCompletionMessage(role="assistant", content=json_response),
            finish_reason="stop"
        )
        mock_response = ChatCompletion(
            id="test-id",
            choices=[mock_choice],
            created=1234567890,
            model="qwen/qwen3-coder-480b-a35b-instruct",
            object="chat.completion"
        )
        
        with patch.object(self.client.client.chat.completions, 'create', return_value=mock_response) as mock_create:
            result = await self.client.extract_structured_info(
                content="Test content",
                system_prompt="Extract task info",
                response_format=response_format
            )
            
            # Verify response_format was passed to the API call
            call_args = mock_create.call_args[1]
            assert "response_format" in call_args
            assert call_args["response_format"] == response_format
            assert result == {"title": "Test Task"}
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self):
        """Test successful chat completion"""
        response_text = "This is a test response"
        
        mock_choice = Choice(
            index=0,
            message=ChatCompletionMessage(role="assistant", content=response_text),
            finish_reason="stop"
        )
        mock_response = ChatCompletion(
            id="test-id",
            choices=[mock_choice],
            created=1234567890,
            model="qwen/qwen3-coder-480b-a35b-instruct",
            object="chat.completion",
            usage=CompletionUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30)
        )
        
        with patch.object(self.client.client.chat.completions, 'create', return_value=mock_response):
            result = await self.client.chat_completion([
                {"role": "user", "content": "Hello"}
            ])
            
            assert result == response_text
            assert self.client.request_count == 1
            assert self.client.total_tokens == 30
    
    @pytest.mark.asyncio
    async def test_chat_completion_empty_response(self):
        """Test chat completion with empty response"""
        mock_choice = Choice(
            index=0,
            message=ChatCompletionMessage(role="assistant", content=None),
            finish_reason="stop"
        )
        mock_response = ChatCompletion(
            id="test-id",
            choices=[mock_choice],
            created=1234567890,
            model="qwen/qwen3-coder-480b-a35b-instruct",
            object="chat.completion"
        )
        
        with patch.object(self.client.client.chat.completions, 'create', return_value=mock_response):
            with pytest.raises(ModelAPIError) as exc_info:
                await self.client.chat_completion([
                    {"role": "user", "content": "Hello"}
                ])
            assert "Empty response from model" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_function_call_success(self):
        """Test successful function call"""
        function_call_mock = MagicMock()
        function_call_mock.name = "extract_task_info"
        function_call_mock.arguments = '{"title": "Test Task", "reward": 100}'
        
        mock_choice = Choice(
            index=0,
            message=ChatCompletionMessage(
                role="assistant", 
                content=None,
                function_call=function_call_mock
            ),
            finish_reason="function_call"
        )
        mock_response = ChatCompletion(
            id="test-id",
            choices=[mock_choice],
            created=1234567890,
            model="qwen/qwen3-coder-480b-a35b-instruct",
            object="chat.completion"
        )
        
        functions = [{
            "name": "extract_task_info",
            "description": "Extract task information",
            "parameters": {"type": "object"}
        }]
        
        with patch.object(self.client.client.chat.completions, 'create', return_value=mock_response):
            result = await self.client.function_call(
                messages=[{"role": "user", "content": "Extract info"}],
                functions=functions
            )
            
            assert result["type"] == "function_call"
            assert result["function_call"]["name"] == "extract_task_info"
            assert result["function_call"]["arguments"]["title"] == "Test Task"
            assert result["function_call"]["arguments"]["reward"] == 100
    
    @pytest.mark.asyncio
    async def test_function_call_unsupported_model(self):
        """Test function call with unsupported model"""
        # Create client with unsupported model
        unsupported_config = PPIOModelConfig(
            api_key="sk_test_key_12345",
            model_name="unsupported/model"
        )
        unsupported_client = PPIOModelClient(unsupported_config)
        
        functions = [{"name": "test_function"}]
        
        with pytest.raises(ModelAPIError) as exc_info:
            await unsupported_client.function_call(
                messages=[{"role": "user", "content": "test"}],
                functions=functions
            )
        assert "does not support function calling" in str(exc_info.value)
    
    def test_get_stats(self):
        """Test getting client statistics"""
        # Simulate some usage
        self.client.request_count = 5
        self.client.total_tokens = 1000
        self.client.error_count = 1
        
        stats = self.client.get_stats()
        
        assert stats["request_count"] == 5
        assert stats["total_tokens"] == 1000
        assert stats["error_count"] == 1
        assert stats["error_rate"] == 0.2
        assert stats["model_name"] == "qwen/qwen3-coder-480b-a35b-instruct"
        assert stats["supports_structured_output"] is True
        assert stats["supports_function_calling"] is True
    
    def test_reset_stats(self):
        """Test resetting client statistics"""
        # Set some stats
        self.client.request_count = 10
        self.client.total_tokens = 2000
        self.client.error_count = 2
        
        # Reset
        self.client.reset_stats()
        
        assert self.client.request_count == 0
        assert self.client.total_tokens == 0
        assert self.client.error_count == 0
    
    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing client"""
        mock_close = AsyncMock()
        self.client.client.close = mock_close
        
        await self.client.close()
        mock_close.assert_called_once()


if __name__ == "__main__":
    # Run basic tests without pytest
    import asyncio
    
    async def run_basic_tests():
        test_class = TestPPIOModelClient()
        
        print("Testing client initialization...")
        test_class.setup_method()
        test_class.test_client_initialization()
        print("✅ Client initialization test passed")
        
        print("Testing invalid config...")
        test_class.test_invalid_config()
        print("✅ Invalid config test passed")
        
        print("Testing get stats...")
        test_class.test_get_stats()
        print("✅ Get stats test passed")
        
        print("Testing reset stats...")
        test_class.test_reset_stats()
        print("✅ Reset stats test passed")
        
        print("\n🎉 All basic client tests passed!")
    
    asyncio.run(run_basic_tests())