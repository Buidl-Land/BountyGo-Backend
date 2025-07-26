"""
Integration tests for Agent Coordination
测试多Agent协作的集成测试
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
from datetime import datetime

from app.agent.smart_coordinator import SmartCoordinator, UserInput
from app.agent.agent_orchestrator import AgentOrchestrator, WorkflowType
from app.agent.input_analyzer import InputAnalyzer, InputType, UserIntent
from app.agent.preference_manager import PreferenceManager, UserPreferences, OutputFormat
from app.agent.unified_config import get_config_manager, AgentRole
from app.agent.models import TaskInfo, WebContent
from tests.test_mocks import (
    MockPPIOClient, MockContentExtractor, MockAgent, MockConfigManager,
    TestDataFactory, TestScenarios
)


class TestAgentCoordinationIntegration:
    """Integration tests for agent coordination"""
    
    @pytest.fixture
    async def setup_coordinator(self):
        """Setup coordinator with mocked dependencies"""
        # Mock config manager
        mock_config_manager = MockConfigManager()
        mock_config_manager.initialize()
        
        # Create coordinator
        coordinator = SmartCoordinator()
        
        # Mock dependencies
        coordinator.input_analyzer = InputAnalyzer()
        coordinator.preference_manager = PreferenceManager(storage_backend="memory")
        await coordinator.preference_manager.initialize()
        
        coordinator.agent_orchestrator = AgentOrchestrator()
        coordinator.agent_orchestrator.config_manager = mock_config_manager
        
        # Mock agents
        url_agent = MockAgent(AgentRole.URL_PARSER)
        image_agent = MockAgent(AgentRole.IMAGE_ANALYZER)
        
        coordinator.agent_orchestrator.agents = {
            AgentRole.URL_PARSER: url_agent,
            AgentRole.IMAGE_ANALYZER: image_agent
        }
        
        # Mock content extractor
        mock_extractor = MockContentExtractor()
        coordinator.agent_orchestrator.content_extractor = mock_extractor
        
        coordinator.agent_orchestrator._initialized = True
        
        return coordinator, mock_config_manager, url_agent, image_agent, mock_extractor
    
    @pytest.mark.asyncio
    async def test_url_analysis_workflow_integration(self, setup_coordinator):
        """Test complete URL analysis workflow integration"""
        coordinator, config_manager, url_agent, image_agent, content_extractor = setup_coordinator
        
        # Setup test scenario
        scenario = TestScenarios.get_url_analysis_scenario()
        
        # Add expected responses
        content_extractor.add_response(
            scenario["expected_url"],
            scenario["mock_web_content"]
        )
        url_agent.add_response("analyze_content", scenario["expected_task"])
        
        # Create user input
        user_input = UserInput.create(scenario["input"], "test_user")
        
        # Process input through coordinator
        result = await coordinator.process_user_input(user_input)
        
        # Verify results
        assert result.success is True
        assert result.user_intent == scenario["expected_intent"]
        assert result.task_info is not None
        assert result.task_info.title == scenario["expected_task"].title
        
        # Verify agent interactions
        assert content_extractor.call_count == 1
        assert content_extractor.last_url == scenario["expected_url"]
        assert url_agent.call_count == 1
        
        # Verify user preferences were updated
        user_prefs = await coordinator.preference_manager.get_user_preferences("test_user")
        assert user_prefs.user_id == "test_user"
    
    @pytest.mark.asyncio
    async def test_image_analysis_workflow_integration(self, setup_coordinator):
        """Test complete image analysis workflow integration"""
        coordinator, config_manager, url_agent, image_agent, content_extractor = setup_coordinator
        
        # Setup test scenario
        scenario = TestScenarios.get_image_analysis_scenario()
        
        # Add expected responses
        image_agent.add_response("analyze_image", scenario["expected_task"])
        
        # Create user input
        user_input = UserInput.create(scenario["input"], "test_user")
        
        # Process input through coordinator
        result = await coordinator.process_user_input(user_input)
        
        # Verify results
        assert result.success is True
        assert result.user_intent == scenario["expected_intent"]
        assert result.task_info is not None
        assert result.task_info.title == scenario["expected_task"].title
        
        # Verify agent interactions
        assert image_agent.call_count == 1
        assert content_extractor.call_count == 0  # No content extraction for images
    
    @pytest.mark.asyncio
    async def test_preference_setting_integration(self, setup_coordinator):
        """Test preference setting integration"""
        coordinator, config_manager, url_agent, image_agent, content_extractor = setup_coordinator
        
        # Setup test scenario
        scenario = TestScenarios.get_preference_setting_scenario()
        
        # Create user input
        user_input = UserInput.create(scenario["input"], "test_user")
        
        # Process input through coordinator
        result = await coordinator.process_user_input(user_input)
        
        # Verify results
        assert result.success is True
        assert result.user_intent == scenario["expected_intent"]
        assert "偏好设置已更新" in result.response_message
        
        # Verify preferences were updated
        user_prefs = await coordinator.preference_manager.get_user_preferences("test_user")
        assert user_prefs.output_format == OutputFormat.JSON
        assert user_prefs.language == "English"
    
    @pytest.mark.asyncio
    async def test_mixed_content_workflow_integration(self, setup_coordinator):
        """Test mixed content workflow integration"""
        coordinator, config_manager, url_agent, image_agent, content_extractor = setup_coordinator
        
        # Setup test scenario
        scenario = TestScenarios.get_mixed_content_scenario()
        
        # Add expected responses
        url_task = TestDataFactory.create_task_info(title="URL Task", description="URL analysis")
        image_task = TestDataFactory.create_task_info(title="Image Task", description="Image analysis")
        
        content_extractor.add_response(
            scenario["expected_data"]["urls"][0],
            TestDataFactory.create_web_content(url=scenario["expected_data"]["urls"][0])
        )
        url_agent.add_response("analyze_content", url_task)
        image_agent.add_response("analyze_image", image_task)
        
        # Create user input
        user_input = UserInput.create(scenario["input"], "test_user")
        
        # Process input through coordinator
        result = await coordinator.process_user_input(user_input)
        
        # Verify results
        assert result.success is True
        assert result.user_intent == scenario["expected_intent"]
        assert result.task_info is not None
        
        # Verify both agents were called
        assert url_agent.call_count == 1
        assert image_agent.call_count == 1
        assert content_extractor.call_count == 1
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, setup_coordinator):
        """Test error handling integration across components"""
        coordinator, config_manager, url_agent, image_agent, content_extractor = setup_coordinator
        
        # Setup failing content extractor
        async def failing_extract(url):
            raise Exception("Network error")
        
        content_extractor.extract_content = failing_extract
        
        # Create user input
        user_input = UserInput.create("https://failing-url.com", "test_user")
        
        # Process input through coordinator
        result = await coordinator.process_user_input(user_input)
        
        # Verify error handling
        assert result.success is False
        assert "处理失败" in result.response_message
        assert result.error_message is not None
    
    @pytest.mark.asyncio
    async def test_preference_learning_integration(self, setup_coordinator):
        """Test preference learning integration"""
        coordinator, config_manager, url_agent, image_agent, content_extractor = setup_coordinator
        
        # Setup successful URL analysis
        web_content = TestDataFactory.create_web_content()
        task_info = TestDataFactory.create_task_info()
        
        content_extractor.add_response("https://example.com", web_content)
        url_agent.add_response("analyze_content", task_info)
        
        # Process multiple URL inputs to trigger learning
        for i in range(5):
            user_input = UserInput.create(f"https://example{i}.com", "test_user")
            await coordinator.process_user_input(user_input)
        
        # Check if preferences were learned
        user_prefs = await coordinator.preference_manager.get_user_preferences("test_user")
        interaction_history = coordinator.preference_manager.get_user_interaction_history("test_user")
        
        assert len(interaction_history) == 5
        assert user_prefs.user_id == "test_user"
        
        # Get preference suggestions
        suggestions = await coordinator.preference_manager.suggest_preferences("test_user")
        assert len(suggestions) >= 0  # Should have some suggestions based on usage patterns
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, setup_coordinator):
        """Test handling concurrent requests"""
        coordinator, config_manager, url_agent, image_agent, content_extractor = setup_coordinator
        
        # Setup responses
        web_content = TestDataFactory.create_web_content()
        task_info = TestDataFactory.create_task_info()
        
        content_extractor.add_response("https://example.com", web_content)
        url_agent.add_response("analyze_content", task_info)
        
        # Create multiple concurrent requests
        async def process_request(i):
            user_input = UserInput.create(f"https://example.com?id={i}", f"user_{i}")
            return await coordinator.process_user_input(user_input)
        
        # Process requests concurrently
        tasks = [process_request(i) for i in range(3)]
        results = await asyncio.gather(*tasks)
        
        # Verify all requests succeeded
        for result in results:
            assert result.success is True
            assert result.task_info is not None
        
        # Verify agent was called for each request
        assert url_agent.call_count == 3
    
    @pytest.mark.asyncio
    async def test_workflow_quality_assessment(self, setup_coordinator):
        """Test workflow quality assessment integration"""
        coordinator, config_manager, url_agent, image_agent, content_extractor = setup_coordinator
        
        # Setup high-quality task response
        high_quality_task = TestDataFactory.create_task_info(
            title="High Quality Task with Detailed Title",
            description="This is a comprehensive description that provides detailed information about the task requirements and expected outcomes.",
            reward=500.0,
            tags=["high-quality", "detailed", "comprehensive"],
            deadline=datetime.utcnow()
        )
        
        web_content = TestDataFactory.create_web_content()
        content_extractor.add_response("https://quality-example.com", web_content)
        url_agent.add_response("analyze_content", high_quality_task)
        
        # Set high quality threshold
        user_prefs = await coordinator.preference_manager.get_user_preferences("test_user")
        await coordinator.preference_manager.update_user_preferences(
            "test_user", 
            {"quality_threshold": 0.8}
        )
        
        # Process input
        user_input = UserInput.create("https://quality-example.com", "test_user")
        result = await coordinator.process_user_input(user_input)
        
        # Verify high-quality result
        assert result.success is True
        assert result.task_info.title == high_quality_task.title
        assert len(result.task_info.description) > 50  # Detailed description
        assert result.task_info.reward > 0
        assert len(result.task_info.tags) > 0


class TestAgentOrchestrationIntegration:
    """Integration tests for agent orchestration"""
    
    @pytest.fixture
    async def setup_orchestrator(self):
        """Setup orchestrator with mocked dependencies"""
        orchestrator = AgentOrchestrator()
        
        # Mock config manager
        mock_config_manager = MockConfigManager()
        mock_config_manager.initialize()
        orchestrator.config_manager = mock_config_manager
        
        # Mock agents
        url_agent = MockAgent(AgentRole.URL_PARSER)
        image_agent = MockAgent(AgentRole.IMAGE_ANALYZER)
        
        orchestrator.agents = {
            AgentRole.URL_PARSER: url_agent,
            AgentRole.IMAGE_ANALYZER: image_agent
        }
        
        # Mock content extractor
        mock_extractor = MockContentExtractor()
        orchestrator.content_extractor = mock_extractor
        
        orchestrator._initialized = True
        
        return orchestrator, url_agent, image_agent, mock_extractor
    
    @pytest.mark.asyncio
    async def test_url_workflow_orchestration(self, setup_orchestrator):
        """Test URL workflow orchestration"""
        orchestrator, url_agent, image_agent, content_extractor = setup_orchestrator
        
        # Setup test data
        url = "https://test-orchestration.com"
        web_content = TestDataFactory.create_web_content(url=url)
        task_info = TestDataFactory.create_task_info()
        
        content_extractor.add_response(url, web_content)
        url_agent.add_response("analyze_content", task_info)
        
        # Create user preferences
        preferences = TestDataFactory.create_user_preferences()
        
        # Execute workflow
        result = await orchestrator.execute_workflow(
            WorkflowType.URL_PROCESSING,
            url,
            preferences
        )
        
        # Verify workflow result
        assert result.success is True
        assert result.task_info == task_info
        assert result.workflow_type == WorkflowType.URL_PROCESSING
        assert result.processing_time > 0
        assert result.quality_score > 0
        
        # Verify agent interactions
        assert content_extractor.call_count == 1
        assert url_agent.call_count == 1
    
    @pytest.mark.asyncio
    async def test_image_workflow_orchestration(self, setup_orchestrator):
        """Test image workflow orchestration"""
        orchestrator, url_agent, image_agent, content_extractor = setup_orchestrator
        
        # Setup test data
        image_data = b"fake_image_data"
        task_info = TestDataFactory.create_task_info(title="Image Analysis")
        
        image_agent.add_response("analyze_image", task_info)
        
        # Create user preferences
        preferences = TestDataFactory.create_user_preferences()
        
        # Execute workflow
        result = await orchestrator.execute_workflow(
            WorkflowType.IMAGE_PROCESSING,
            image_data,
            preferences
        )
        
        # Verify workflow result
        assert result.success is True
        assert result.task_info == task_info
        assert result.workflow_type == WorkflowType.IMAGE_PROCESSING
        assert result.processing_time > 0
        
        # Verify agent interactions
        assert image_agent.call_count == 1
        assert content_extractor.call_count == 0  # No content extraction for images
    
    @pytest.mark.asyncio
    async def test_mixed_workflow_orchestration(self, setup_orchestrator):
        """Test mixed content workflow orchestration"""
        orchestrator, url_agent, image_agent, content_extractor = setup_orchestrator
        
        # Setup test data
        mixed_data = {
            "urls": ["https://example.com"],
            "image_data": "fake_image_data",
            "text": "Some text content"
        }
        
        # Setup responses
        web_content = TestDataFactory.create_web_content()
        url_task = TestDataFactory.create_task_info(title="URL Task")
        image_task = TestDataFactory.create_task_info(title="Image Task")
        text_task = TestDataFactory.create_task_info(title="Text Task")
        
        content_extractor.add_response(mixed_data["urls"][0], web_content)
        url_agent.add_response("analyze_content", url_task)
        image_agent.add_response("analyze_image", image_task)
        
        # Create user preferences
        preferences = TestDataFactory.create_user_preferences()
        
        # Execute workflow
        result = await orchestrator.execute_workflow(
            WorkflowType.MIXED_PROCESSING,
            mixed_data,
            preferences
        )
        
        # Verify workflow result
        assert result.success is True
        assert result.task_info is not None
        assert result.workflow_type == WorkflowType.MIXED_PROCESSING
        
        # Verify multiple agents were used
        assert url_agent.call_count >= 1  # URL and text processing
        assert image_agent.call_count == 1
    
    @pytest.mark.asyncio
    async def test_workflow_error_recovery(self, setup_orchestrator):
        """Test workflow error recovery"""
        orchestrator, url_agent, image_agent, content_extractor = setup_orchestrator
        
        # Setup failing content extractor
        async def failing_extract(url):
            raise Exception("Network timeout")
        
        content_extractor.extract_content = failing_extract
        
        # Create user preferences
        preferences = TestDataFactory.create_user_preferences()
        
        # Execute workflow
        result = await orchestrator.execute_workflow(
            WorkflowType.URL_PROCESSING,
            "https://failing-url.com",
            preferences
        )
        
        # Verify error handling
        assert result.success is False
        assert result.error_message is not None
        assert result.workflow_type == WorkflowType.URL_PROCESSING
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_workflow_quality_scoring(self, setup_orchestrator):
        """Test workflow quality scoring"""
        orchestrator, url_agent, image_agent, content_extractor = setup_orchestrator
        
        # Setup high-confidence responses
        web_content = TestDataFactory.create_web_content()
        high_quality_task = TestDataFactory.create_task_info(
            title="High Quality Task",
            description="Detailed description with comprehensive information",
            reward=1000.0,
            tags=["premium", "detailed"]
        )
        
        content_extractor.add_response("https://example.com", web_content)
        url_agent.add_response("analyze_content", high_quality_task)
        
        # Create user preferences with high quality threshold
        preferences = TestDataFactory.create_user_preferences(quality_threshold=0.8)
        
        # Execute workflow
        result = await orchestrator.execute_workflow(
            WorkflowType.URL_PROCESSING,
            "https://example.com",
            preferences
        )
        
        # Verify quality scoring
        assert result.success is True
        assert result.quality_score > 0.5  # Should have reasonable quality score
        assert result.task_info == high_quality_task


class TestPreferenceIntegration:
    """Integration tests for preference management"""
    
    @pytest.mark.asyncio
    async def test_preference_persistence_integration(self):
        """Test preference persistence across sessions"""
        # Create preference manager with file storage
        manager = PreferenceManager(storage_backend="memory")
        await manager.initialize()
        
        # Set initial preferences
        initial_prefs = {
            "output_format": "JSON",
            "language": "English",
            "quality_threshold": 0.9
        }
        
        await manager.update_user_preferences("test_user", initial_prefs)
        
        # Simulate learning from interactions
        for i in range(10):
            user_input = MagicMock()
            user_input.content = f"URL input {i}"
            user_input.input_type = "url"
            
            result = MagicMock()
            result.user_intent = "create_task"
            result.success = True
            result.processing_time = 1.0
            
            await manager.learn_from_interaction("test_user", user_input, result)
        
        # Get updated preferences
        updated_prefs = await manager.get_user_preferences("test_user")
        
        # Verify preferences were maintained and potentially updated
        assert updated_prefs.output_format == OutputFormat.JSON
        assert updated_prefs.language == "English"
        assert updated_prefs.quality_threshold == 0.9
        
        # Get suggestions based on usage
        suggestions = await manager.suggest_preferences("test_user")
        
        # Should suggest auto-create tasks based on URL usage pattern
        auto_create_suggestion = next(
            (s for s in suggestions if s.preference_key == "auto_create_tasks"),
            None
        )
        assert auto_create_suggestion is not None
        assert auto_create_suggestion.suggested_value is True
    
    @pytest.mark.asyncio
    async def test_preference_learning_integration(self):
        """Test preference learning from user behavior"""
        manager = PreferenceManager(storage_backend="memory")
        await manager.initialize()
        
        # Simulate consistent user behavior pattern
        behavior_patterns = [
            {"input_type": "url", "success": True, "processing_time": 2.0},
            {"input_type": "url", "success": True, "processing_time": 1.8},
            {"input_type": "url", "success": True, "processing_time": 2.2},
            {"input_type": "image", "success": False, "processing_time": 5.0},
            {"input_type": "image", "success": False, "processing_time": 4.8},
        ]
        
        for i, pattern in enumerate(behavior_patterns * 3):  # Repeat pattern
            user_input = MagicMock()
            user_input.content = f"Input {i}"
            user_input.input_type = pattern["input_type"]
            
            result = MagicMock()
            result.user_intent = "create_task"
            result.success = pattern["success"]
            result.processing_time = pattern["processing_time"]
            
            await manager.learn_from_interaction("test_user", user_input, result)
        
        # Get suggestions based on learned patterns
        suggestions = await manager.suggest_preferences("test_user")
        
        # Should suggest preferences based on success patterns
        assert len(suggestions) > 0
        
        # Check for specific suggestions
        suggestion_keys = [s.preference_key for s in suggestions]
        
        # Should suggest auto-create for URLs (high success rate)
        if "auto_create_tasks" in suggestion_keys:
            auto_create_suggestion = next(s for s in suggestions if s.preference_key == "auto_create_tasks")
            assert auto_create_suggestion.suggested_value is True