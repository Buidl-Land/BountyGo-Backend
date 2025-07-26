"""
Tests for Smart Coordinator
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.agent.smart_coordinator import (
    SmartCoordinator, UserInput, ProcessResult, ChatResponse,
    UserIntent, get_smart_coordinator
)
from app.agent.input_analyzer import InputType
from app.agent.preference_manager import UserPreferences, OutputFormat


class TestSmartCoordinator:
    """Test Smart Coordinator functionality"""
    
    @pytest.mark.asyncio
    async def test_coordinator_initialization(self):
        """Test coordinator initialization"""
        coordinator = SmartCoordinator()
        
        # Mock the dependencies
        with patch.object(coordinator.preference_manager, 'initialize', new_callable=AsyncMock):
            with patch.object(coordinator.agent_orchestrator, 'initialize', new_callable=AsyncMock):
                await coordinator.initialize()
                
                assert coordinator.is_initialized()
    
    @pytest.mark.asyncio
    async def test_process_url_input(self):
        """Test processing URL input"""
        coordinator = SmartCoordinator()
        
        # Mock dependencies
        coordinator.input_analyzer.analyze_input = AsyncMock(return_value=MagicMock(
            input_type=InputType.URL,
            user_intent=UserIntent.CREATE_TASK,
            extracted_data="https://example.com/task",
            extracted_preferences=None
        ))
        
        coordinator.preference_manager.get_user_preferences = AsyncMock(return_value=UserPreferences(
            user_id="test_user",
            output_format=OutputFormat.STRUCTURED
        ))
        
        coordinator.agent_orchestrator.execute_workflow = AsyncMock(return_value=MagicMock(
            success=True,
            task_info=MagicMock(title="Test Task"),
            error_message=None
        ))
        
        coordinator.preference_manager.learn_from_interaction = AsyncMock()
        
        # Test URL input
        user_input = UserInput.create("https://example.com/task", "test_user")
        result = await coordinator.process_user_input(user_input)
        
        assert result.success
        assert result.user_intent == UserIntent.CREATE_TASK
        assert "任务创建成功" in result.response_message
    
    @pytest.mark.asyncio
    async def test_process_text_input(self):
        """Test processing text input"""
        coordinator = SmartCoordinator()
        
        # Mock dependencies
        coordinator.input_analyzer.analyze_input = AsyncMock(return_value=MagicMock(
            input_type=InputType.TEXT,
            user_intent=UserIntent.CHAT,
            extracted_data="Hello",
            extracted_preferences=None
        ))
        
        coordinator.preference_manager.get_user_preferences = AsyncMock(return_value=UserPreferences(
            user_id="test_user"
        ))
        
        coordinator.preference_manager.learn_from_interaction = AsyncMock()
        
        # Test text input
        user_input = UserInput.create("Hello", "test_user")
        result = await coordinator.process_user_input(user_input)
        
        assert result.success
        assert result.user_intent == UserIntent.CHAT
    
    @pytest.mark.asyncio
    async def test_chat_functionality(self):
        """Test chat functionality"""
        coordinator = SmartCoordinator()
        
        # Mock process_user_input
        coordinator.process_user_input = AsyncMock(return_value=ProcessResult(
            success=True,
            response_message="Hello! How can I help you?",
            user_intent=UserIntent.CHAT
        ))
        
        # Test chat
        response = await coordinator.chat_with_user("Hello", "test_user")
        
        assert isinstance(response, ChatResponse)
        assert response.message == "Hello! How can I help you?"
        assert not response.requires_action
    
    @pytest.mark.asyncio
    async def test_preference_setting(self):
        """Test preference setting functionality"""
        coordinator = SmartCoordinator()
        
        # Mock dependencies
        coordinator.input_analyzer.analyze_input = AsyncMock(return_value=MagicMock(
            input_type=InputType.TEXT,
            user_intent=UserIntent.SET_PREFERENCES,
            extracted_data="Set output format to JSON",
            extracted_preferences={"output_format": "JSON"}
        ))
        
        coordinator.preference_manager.get_user_preferences = AsyncMock(return_value=UserPreferences(
            user_id="test_user"
        ))
        
        coordinator.preference_manager.update_user_preferences = AsyncMock()
        coordinator.preference_manager.learn_from_interaction = AsyncMock()
        
        # Test preference setting
        user_input = UserInput.create("Set output format to JSON", "test_user")
        result = await coordinator.process_user_input(user_input)
        
        assert result.success
        assert result.user_intent == UserIntent.SET_PREFERENCES
        assert "偏好设置已更新" in result.response_message
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling"""
        coordinator = SmartCoordinator()
        
        # Mock to raise exception
        coordinator.input_analyzer.analyze_input = AsyncMock(side_effect=Exception("Test error"))
        
        # Test error handling
        user_input = UserInput.create("Test input", "test_user")
        result = await coordinator.process_user_input(user_input)
        
        assert not result.success
        assert "处理失败" in result.response_message
        assert result.error_message == "Test error"
    
    def test_conversation_history(self):
        """Test conversation history management"""
        coordinator = SmartCoordinator()
        
        # Test updating conversation history
        coordinator._update_conversation_history("test_user", "Hello", "Hi there!")
        
        history = coordinator._get_conversation_history("test_user")
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"
    
    def test_task_suggestions(self):
        """Test task suggestion generation"""
        coordinator = SmartCoordinator()
        
        # Mock task info
        task_info = MagicMock()
        task_info.deadline = None
        task_info.reward = None
        task_info.tags = []
        task_info.difficulty_level = None
        
        suggestions = coordinator._generate_task_suggestions(task_info)
        
        assert "设置截止日期" in suggestions
        assert "设置奖励金额" in suggestions
        assert "添加相关标签" in suggestions
        assert "设置难度等级" in suggestions
    
    def test_stats_tracking(self):
        """Test statistics tracking"""
        coordinator = SmartCoordinator()
        
        # Test stats update
        coordinator._update_stats(True, 1.5)
        coordinator._update_stats(False, 2.0)
        
        stats = coordinator.get_stats()
        assert stats["total_requests"] == 2
        assert stats["successful_requests"] == 1
        assert stats["failed_requests"] == 1
        assert stats["avg_processing_time"] == 1.75
    
    @pytest.mark.asyncio
    async def test_global_coordinator_instance(self):
        """Test global coordinator instance"""
        with patch('app.agent.smart_coordinator.SmartCoordinator') as mock_coordinator_class:
            mock_instance = AsyncMock()
            mock_instance.initialize = AsyncMock()
            mock_coordinator_class.return_value = mock_instance
            
            # Reset global instance
            import app.agent.smart_coordinator
            app.agent.smart_coordinator._smart_coordinator = None
            
            coordinator = await get_smart_coordinator()
            assert coordinator is not None
            mock_instance.initialize.assert_called_once()


class TestUserInput:
    """Test UserInput data class"""
    
    def test_user_input_creation(self):
        """Test UserInput creation"""
        user_input = UserInput.create("Test content", "test_user", {"key": "value"})
        
        assert user_input.content == "Test content"
        assert user_input.user_id == "test_user"
        assert user_input.input_type == InputType.TEXT
        assert user_input.metadata["key"] == "value"
        assert user_input.timestamp is not None


class TestProcessResult:
    """Test ProcessResult data class"""
    
    def test_process_result_creation(self):
        """Test ProcessResult creation"""
        result = ProcessResult(
            success=True,
            response_message="Success",
            user_intent=UserIntent.CREATE_TASK,
            suggestions=["suggestion1", "suggestion2"]
        )
        
        assert result.success
        assert result.response_message == "Success"
        assert result.user_intent == UserIntent.CREATE_TASK
        assert len(result.suggestions) == 2


class TestChatResponse:
    """Test ChatResponse data class"""
    
    def test_chat_response_creation(self):
        """Test ChatResponse creation"""
        response = ChatResponse(
            message="Hello!",
            suggestions=["help", "status"],
            requires_action=False
        )
        
        assert response.message == "Hello!"
        assert len(response.suggestions) == 2
        assert not response.requires_action
        assert response.task_info is None