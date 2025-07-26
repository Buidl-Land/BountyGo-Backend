"""
Mock services and test fixtures for unit tests
"""
import asyncio
from typing import Dict, List, Optional, Any, Union
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
import json

from app.agent.models import TaskInfo, WebContent
from app.agent.preference_manager import UserPreferences, OutputFormat, AnalysisFocus
from app.agent.unified_config import AgentRole, AgentConfig, ModelProvider
from app.agent.input_analyzer import InputType, UserIntent, InputAnalysisResult
from app.agent.agent_orchestrator import WorkflowResult, WorkflowType, AgentResult


class MockPPIOClient:
    """Mock PPIO API client for testing"""
    
    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.last_request = None
    
    async def chat_completion(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """Mock chat completion"""
        self.call_count += 1
        self.last_request = {
            "messages": messages,
            "kwargs": kwargs
        }
        
        # Return predefined response or default
        if "chat_completion" in self.responses:
            return self.responses["chat_completion"]
        
        return {
            "choices": [{
                "message": {
                    "content": "Mock response from PPIO API",
                    "role": "assistant"
                }
            }],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
    
    async def vision_completion(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """Mock vision completion"""
        self.call_count += 1
        self.last_request = {
            "messages": messages,
            "kwargs": kwargs
        }
        
        if "vision_completion" in self.responses:
            return self.responses["vision_completion"]
        
        return {
            "choices": [{
                "message": {
                    "content": "Mock vision analysis response",
                    "role": "assistant"
                }
            }],
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "total_tokens": 300
            }
        }
    
    def reset(self):
        """Reset mock state"""
        self.call_count = 0
        self.last_request = None


class MockContentExtractor:
    """Mock content extractor for testing"""
    
    def __init__(self, responses: Optional[Dict[str, WebContent]] = None):
        self.responses = responses or {}
        self.call_count = 0
        self.last_url = None
    
    async def extract_content(self, url: str) -> WebContent:
        """Mock content extraction"""
        self.call_count += 1
        self.last_url = url
        
        if url in self.responses:
            return self.responses[url]
        
        # Default response
        return WebContent(
            url=url,
            title=f"Mock Title for {url}",
            content=f"Mock content extracted from {url}",
            meta_description=f"Mock description for {url}",
            extracted_at=datetime.utcnow()
        )
    
    def add_response(self, url: str, content: WebContent):
        """Add predefined response for URL"""
        self.responses[url] = content
    
    def reset(self):
        """Reset mock state"""
        self.call_count = 0
        self.last_url = None


class MockAgent:
    """Mock agent for testing"""
    
    def __init__(self, role: Union[AgentRole, str], responses: Optional[Dict[str, Any]] = None, agent_id: Optional[str] = None):
        self.role = role
        # Handle both AgentRole enum and string inputs
        if isinstance(role, AgentRole):
            role_str = role.value
        else:
            role_str = str(role)
        self.agent_id = agent_id or f"mock_{role_str}_{id(self)}"
        self.responses = responses or {}
        self.call_count = 0
        self.last_input = None
        self.client = MagicMock()  # Mock client
        self.initialized = True
    
    async def initialize(self):
        """Mock initialization"""
        self.initialized = True
    
    async def analyze_content(self, content: Union[WebContent, str]) -> TaskInfo:
        """Mock content analysis"""
        self.call_count += 1
        self.last_input = content
        
        if "analyze_content" in self.responses:
            return self.responses["analyze_content"]
        
        # Handle both WebContent and string inputs
        if isinstance(content, WebContent):
            title = content.title
            description = f"Mock analysis of: {content.content[:100]}..."
        else:
            title = "Mock Task from String"
            description = f"Mock analysis of: {str(content)[:100]}..."
        
        return TaskInfo(
            title=title,
            description=description,
            reward=100.0,
            reward_currency="USD",
            tags=["mock", "test"],
            difficulty_level="medium",
            estimated_hours=2.0
        )
    
    async def analyze_image(self, image_data: Union[bytes, str]) -> TaskInfo:
        """Mock image analysis"""
        self.call_count += 1
        self.last_input = image_data
        
        if "analyze_image" in self.responses:
            return self.responses["analyze_image"]
        
        return TaskInfo(
            title="Mock Image Analysis Task",
            description="Mock analysis of uploaded image",
            reward=50.0,
            reward_currency="USD",
            tags=["image", "analysis", "mock"],
            difficulty_level="easy",
            estimated_hours=1.0
        )
    
    async def check_quality(self, task_info: TaskInfo) -> Dict[str, Any]:
        """Mock quality check"""
        self.call_count += 1
        self.last_input = task_info
        
        if "check_quality" in self.responses:
            return self.responses["check_quality"]
        
        return {
            "quality_score": 0.8,
            "issues": [],
            "suggestions": ["Mock suggestion"],
            "approved": True
        }
    
    async def extract(self, data: Any) -> Dict[str, Any]:
        """Mock data extraction"""
        self.call_count += 1
        self.last_input = data
        
        if "extract" in self.responses:
            return self.responses["extract"]
        
        return {
            "extracted_data": f"Mock extracted data from {type(data).__name__}",
            "metadata": {"source": "mock_agent"},
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def process(self, data: Any) -> Dict[str, Any]:
        """Mock data processing"""
        self.call_count += 1
        self.last_input = data
        
        if "process" in self.responses:
            return self.responses["process"]
        
        return {
            "processed_data": f"Mock processed data from {type(data).__name__}",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def validate(self, data: Any) -> Dict[str, Any]:
        """Mock data validation"""
        self.call_count += 1
        self.last_input = data
        
        if "validate" in self.responses:
            return self.responses["validate"]
        
        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "score": 0.9
        }
    
    async def analyze(self, data: Any) -> Dict[str, Any]:
        """Mock data analysis"""
        self.call_count += 1
        self.last_input = data
        
        if "analyze" in self.responses:
            return self.responses["analyze"]
        
        return {
            "analysis_result": f"Mock analysis of {type(data).__name__}",
            "confidence": 0.8,
            "metadata": {"agent_id": self.agent_id},
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def enhance(self, data: Any) -> Dict[str, Any]:
        """Mock data enhancement"""
        self.call_count += 1
        self.last_input = data
        
        if "enhance" in self.responses:
            return self.responses["enhance"]
        
        return {
            "enhanced_data": f"Mock enhanced {type(data).__name__}",
            "improvements": ["quality", "accuracy", "completeness"],
            "metadata": {"agent_id": self.agent_id},
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def add_response(self, method: str, response: Any):
        """Add predefined response for method"""
        self.responses[method] = response
    
    def reset(self):
        """Reset mock state"""
        self.call_count = 0
        self.last_input = None


class MockDatabase:
    """Mock database for testing"""
    
    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}
        self.call_count = 0
    
    async def get(self, table: str, key: str) -> Optional[Dict[str, Any]]:
        """Mock get operation"""
        self.call_count += 1
        return self.data.get(table, {}).get(key)
    
    async def set(self, table: str, key: str, value: Dict[str, Any]):
        """Mock set operation"""
        self.call_count += 1
        if table not in self.data:
            self.data[table] = {}
        self.data[table][key] = value
    
    async def delete(self, table: str, key: str):
        """Mock delete operation"""
        self.call_count += 1
        if table in self.data and key in self.data[table]:
            del self.data[table][key]
    
    async def list_keys(self, table: str) -> List[str]:
        """Mock list keys operation"""
        self.call_count += 1
        return list(self.data.get(table, {}).keys())
    
    def reset(self):
        """Reset mock state"""
        self.data.clear()
        self.call_count = 0


class TestDataFactory:
    """Factory for creating test data"""
    
    @staticmethod
    def create_user_preferences(
        user_id: str = "test_user",
        output_format: OutputFormat = OutputFormat.STRUCTURED,
        **kwargs
    ) -> UserPreferences:
        """Create test user preferences"""
        defaults = {
            "user_id": user_id,
            "output_format": output_format,
            "analysis_focus": [AnalysisFocus.TECHNICAL, AnalysisFocus.BUSINESS],
            "language": "中文",
            "quality_threshold": 0.7,
            "auto_create_tasks": False,
            "notification_enabled": True
        }
        defaults.update(kwargs)
        return UserPreferences(**defaults)
    
    @staticmethod
    def create_task_info(
        title: str = "Test Task",
        description: str = "Test task description",
        **kwargs
    ) -> TaskInfo:
        """Create test task info"""
        defaults = {
            "title": title,
            "description": description,
            "reward": 100.0,
            "reward_currency": "USD",
            "tags": ["test"],
            "difficulty_level": "medium",
            "estimated_hours": 2.0
        }
        defaults.update(kwargs)
        return TaskInfo(**defaults)
    
    @staticmethod
    def create_web_content(
        url: str = "https://example.com",
        title: str = "Test Page",
        **kwargs
    ) -> WebContent:
        """Create test web content"""
        defaults = {
            "url": url,
            "title": title,
            "content": "Test content from web page",
            "meta_description": "Test meta description",
            "extracted_at": datetime.utcnow()
        }
        defaults.update(kwargs)
        return WebContent(**defaults)
    
    @staticmethod
    def create_agent_config(
        role: AgentRole = AgentRole.URL_PARSER,
        **kwargs
    ) -> AgentConfig:
        """Create test agent config"""
        defaults = {
            "role": role,
            "provider": ModelProvider.PPIO,
            "model_name": "test-model",
            "api_key": "sk_test_key_12345",
            "temperature": 0.1,
            "max_tokens": 2000,
            "timeout": 30,
            "max_retries": 3
        }
        defaults.update(kwargs)
        return AgentConfig(**defaults)
    
    @staticmethod
    def create_input_analysis_result(
        input_type: InputType = InputType.TEXT,
        user_intent: UserIntent = UserIntent.CHAT,
        **kwargs
    ) -> InputAnalysisResult:
        """Create test input analysis result"""
        defaults = {
            "input_type": input_type,
            "user_intent": user_intent,
            "confidence": 0.8,
            "extracted_data": "test data",
            "extracted_preferences": None,
            "metadata": {}
        }
        defaults.update(kwargs)
        return InputAnalysisResult(**defaults)
    
    @staticmethod
    def create_agent_result(
        agent_role: AgentRole = AgentRole.URL_PARSER,
        success: bool = True,
        **kwargs
    ) -> AgentResult:
        """Create test agent result"""
        defaults = {
            "agent_role": agent_role,
            "success": success,
            "data": {"test": "data"},
            "confidence": 0.8,
            "processing_time": 1.0,
            "error_message": None,
            "metadata": {}
        }
        defaults.update(kwargs)
        return AgentResult(**defaults)
    
    @staticmethod
    def create_workflow_result(
        success: bool = True,
        workflow_type: WorkflowType = WorkflowType.URL_PROCESSING,
        **kwargs
    ) -> WorkflowResult:
        """Create test workflow result"""
        defaults = {
            "success": success,
            "task_info": TestDataFactory.create_task_info(),
            "agent_results": {},
            "processing_time": 2.0,
            "quality_score": 0.8,
            "error_message": None,
            "workflow_type": workflow_type
        }
        defaults.update(kwargs)
        return WorkflowResult(**defaults)


class MockConfigManager:
    """Mock configuration manager for testing"""
    
    def __init__(self):
        self.agent_configs: Dict[AgentRole, AgentConfig] = {}
        self.system_config = {
            "framework": "camel-ai",
            "default_provider": "ppio",
            "max_concurrent_agents": 5,
            "timeout_seconds": 60,
            "retry_attempts": 3
        }
        self.initialized = False
    
    def initialize(self):
        """Mock initialization"""
        # Add default configs
        self.agent_configs[AgentRole.URL_PARSER] = TestDataFactory.create_agent_config(
            role=AgentRole.URL_PARSER
        )
        self.agent_configs[AgentRole.IMAGE_ANALYZER] = TestDataFactory.create_agent_config(
            role=AgentRole.IMAGE_ANALYZER,
            model_name="vision-model"
        )
        self.initialized = True
    
    def get_agent_config(self, role: AgentRole) -> Optional[AgentConfig]:
        """Get agent configuration"""
        return self.agent_configs.get(role)
    
    def get_all_agent_configs(self) -> Dict[AgentRole, AgentConfig]:
        """Get all agent configurations"""
        return self.agent_configs.copy()
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get system configuration"""
        return self.system_config.copy()
    
    def is_initialized(self) -> bool:
        """Check if initialized"""
        return self.initialized
    
    def add_agent_config(self, role: AgentRole, config: AgentConfig):
        """Add agent configuration"""
        self.agent_configs[role] = config


class AsyncContextManager:
    """Helper for creating async context managers in tests"""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockHTTPResponse:
    """Mock HTTP response for testing"""
    
    def __init__(self, status_code: int = 200, content: str = "", headers: Optional[Dict] = None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.text = content
    
    async def json(self):
        """Mock JSON response"""
        return json.loads(self.content) if self.content else {}
    
    async def text(self):
        """Mock text response"""
        return self.content


def create_mock_async_function(return_value=None, side_effect=None):
    """Create a mock async function"""
    mock = AsyncMock()
    if return_value is not None:
        mock.return_value = return_value
    if side_effect is not None:
        mock.side_effect = side_effect
    return mock


def create_mock_sync_function(return_value=None, side_effect=None):
    """Create a mock sync function"""
    mock = MagicMock()
    if return_value is not None:
        mock.return_value = return_value
    if side_effect is not None:
        mock.side_effect = side_effect
    return mock


class TestScenarios:
    """Common test scenarios and data"""
    
    @staticmethod
    def get_url_analysis_scenario():
        """Get URL analysis test scenario"""
        return {
            "input": "Please analyze this URL: https://github.com/user/repo/issues/123",
            "expected_input_type": InputType.URL,
            "expected_intent": UserIntent.ANALYZE_CONTENT,
            "expected_url": "https://github.com/user/repo/issues/123",
            "mock_web_content": TestDataFactory.create_web_content(
                url="https://github.com/user/repo/issues/123",
                title="Bug Report: Fix authentication issue",
                content="This is a bug report about authentication problems..."
            ),
            "expected_task": TestDataFactory.create_task_info(
                title="Fix authentication issue",
                description="Bug report about authentication problems in the system",
                tags=["bug", "authentication", "github"],
                difficulty_level="medium",
                estimated_hours=4.0
            )
        }
    
    @staticmethod
    def get_image_analysis_scenario():
        """Get image analysis test scenario"""
        return {
            "input": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "expected_input_type": InputType.IMAGE,
            "expected_intent": UserIntent.ANALYZE_CONTENT,
            "expected_task": TestDataFactory.create_task_info(
                title="Image Analysis Task",
                description="Analysis of uploaded image content",
                tags=["image", "analysis"],
                difficulty_level="easy",
                estimated_hours=1.0
            )
        }
    
    @staticmethod
    def get_preference_setting_scenario():
        """Get preference setting test scenario"""
        return {
            "input": "设置输出格式为JSON，语言为English，重点关注技术方面",
            "expected_input_type": InputType.TEXT,
            "expected_intent": UserIntent.SET_PREFERENCES,
            "expected_preferences": {
                "output_format": "JSON",
                "language": "English",
                "analysis_focus": ["TECHNICAL"]
            }
        }
    
    @staticmethod
    def get_mixed_content_scenario():
        """Get mixed content test scenario"""
        return {
            "input": "分析这个URL https://example.com 和这张图片 data:image/png;base64,test",
            "expected_input_type": InputType.MIXED,
            "expected_intent": UserIntent.ANALYZE_CONTENT,
            "expected_data": {
                "urls": ["https://example.com"],
                "image_data": "test",
                "text": "分析这个URL https://example.com 和这张图片 data:image/png;base64,test"
            }
        }
    
    @staticmethod
    def get_error_scenarios():
        """Get error handling test scenarios"""
        return {
            "network_timeout": {
                "error": "NetworkError: Connection timeout",
                "expected_retry": True,
                "expected_message": "网络连接失败"
            },
            "api_rate_limit": {
                "error": "ModelAPIError: Rate limit exceeded",
                "expected_retry": True,
                "expected_message": "API调用失败"
            },
            "invalid_config": {
                "error": "ConfigurationError: Invalid API key",
                "expected_retry": False,
                "expected_message": "配置错误"
            },
            "validation_error": {
                "error": "ValidationError: Invalid input format",
                "expected_retry": False,
                "expected_message": "输入验证失败"
            }
        }


# Export commonly used mocks and factories
__all__ = [
    'MockPPIOClient',
    'MockContentExtractor', 
    'MockAgent',
    'MockDatabase',
    'MockConfigManager',
    'TestDataFactory',
    'AsyncContextManager',
    'MockHTTPResponse',
    'TestScenarios',
    'create_mock_async_function',
    'create_mock_sync_function'
]