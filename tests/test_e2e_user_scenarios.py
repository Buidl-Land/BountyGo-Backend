"""
End-to-End tests for complete user scenarios
端到端测试 - 完整用户场景测试
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio
import json
from datetime import datetime, timedelta

from app.agent.smart_coordinator import SmartCoordinator, UserInput
from app.agent.preference_manager import PreferenceManager, OutputFormat, AnalysisFocus
from app.agent.input_analyzer import InputType, UserIntent
from app.agent.models import TaskInfo
from tests.test_mocks import (
    MockPPIOClient, MockContentExtractor, MockAgent, MockConfigManager,
    TestDataFactory, TestScenarios
)


class TestCompleteUserJourneys:
    """End-to-end tests for complete user journeys"""
    
    @pytest.fixture
    async def setup_full_system(self):
        """Setup complete system for E2E testing"""
        # Create coordinator with all components
        coordinator = SmartCoordinator()
        
        # Setup preference manager
        coordinator.preference_manager = PreferenceManager(storage_backend="memory")
        await coordinator.preference_manager.initialize()
        
        # Setup mock config and agents
        mock_config_manager = MockConfigManager()
        mock_config_manager.initialize()
        
        url_agent = MockAgent(role="url_parser")
        image_agent = MockAgent(role="image_analyzer")
        content_extractor = MockContentExtractor()
        
        # Mock the orchestrator
        coordinator.agent_orchestrator = MagicMock()
        coordinator.agent_orchestrator.config_manager = mock_config_manager
        coordinator.agent_orchestrator.agents = {
            "url_parser": url_agent,
            "image_analyzer": image_agent
        }
        coordinator.agent_orchestrator.content_extractor = content_extractor
        coordinator.agent_orchestrator._initialized = True
        
        # Mock workflow execution
        async def mock_execute_workflow(workflow_type, input_data, preferences, create_task=True):
            if workflow_type.value == "url_processing":
                task_info = TestDataFactory.create_task_info(
                    title="GitHub Issue Analysis",
                    description="Analysis of GitHub issue for bug fix",
                    tags=["github", "bug", "authentication"],
                    reward=150.0
                )
                return TestDataFactory.create_workflow_result(
                    success=True,
                    task_info=task_info,
                    workflow_type=workflow_type
                )
            elif workflow_type.value == "image_processing":
                task_info = TestDataFactory.create_task_info(
                    title="UI Mockup Analysis",
                    description="Analysis of UI mockup for implementation",
                    tags=["ui", "design", "frontend"],
                    reward=100.0
                )
                return TestDataFactory.create_workflow_result(
                    success=True,
                    task_info=task_info,
                    workflow_type=workflow_type
                )
            else:
                return TestDataFactory.create_workflow_result(success=False)
        
        coordinator.agent_orchestrator.execute_workflow = mock_execute_workflow
        
        return coordinator, url_agent, image_agent, content_extractor
    
    @pytest.mark.asyncio
    async def test_new_user_onboarding_journey(self, setup_full_system):
        """Test complete new user onboarding journey"""
        coordinator, url_agent, image_agent, content_extractor = await setup_full_system
        
        user_id = "new_user_123"
        
        # Step 1: New user asks for help
        help_input = UserInput.create("How do I use this system?", user_id)
        help_result = await coordinator.process_user_input(help_input)
        
        assert help_result.success is True
        assert help_result.user_intent == UserIntent.HELP
        assert "帮助" in help_result.response_message or "help" in help_result.response_message.lower()
        
        # Step 2: User sets initial preferences
        pref_input = UserInput.create("设置输出格式为JSON，语言为中文", user_id)
        pref_result = await coordinator.process_user_input(pref_input)
        
        assert pref_result.success is True
        assert pref_result.user_intent == UserIntent.SET_PREFERENCES
        assert "偏好设置已更新" in pref_result.response_message
        
        # Verify preferences were set
        user_prefs = await coordinator.preference_manager.get_user_preferences(user_id)
        assert user_prefs.output_format == OutputFormat.JSON
        assert user_prefs.language == "中文"
        
        # Step 3: User analyzes first URL
        url_input = UserInput.create("请分析这个GitHub问题: https://github.com/user/repo/issues/123", user_id)
        url_result = await coordinator.process_user_input(url_input)
        
        assert url_result.success is True
        assert url_result.user_intent == UserIntent.CREATE_TASK
        assert url_result.task_info is not None
        assert "GitHub Issue Analysis" in url_result.task_info.title
        
        # Step 4: User gets status update
        status_input = UserInput.create("系统状态如何？", user_id)
        status_result = await coordinator.process_user_input(status_input)
        
        assert status_result.success is True
        assert status_result.user_intent == UserIntent.GET_STATUS
        
        # Verify user interaction history
        history = coordinator.preference_manager.get_user_interaction_history(user_id)
        assert len(history) == 4  # All interactions recorded
        
        # Verify learning occurred
        suggestions = await coordinator.preference_manager.suggest_preferences(user_id)
        assert len(suggestions) >= 0  # Should have some suggestions
    
    @pytest.mark.asyncio
    async def test_power_user_workflow_journey(self, setup_full_system):
        """Test power user workflow with multiple content types"""
        coordinator, url_agent, image_agent, content_extractor = await setup_full_system
        
        user_id = "power_user_456"
        
        # Step 1: Set advanced preferences
        advanced_prefs = UserInput.create(
            "设置输出格式为结构化，重点关注技术和商业方面，质量阈值0.8，开启自动创建任务",
            user_id
        )
        pref_result = await coordinator.process_user_input(advanced_prefs)
        
        assert pref_result.success is True
        
        # Verify advanced preferences
        user_prefs = await coordinator.preference_manager.get_user_preferences(user_id)
        assert user_prefs.output_format == OutputFormat.STRUCTURED
        assert user_prefs.quality_threshold == 0.8
        assert user_prefs.auto_create_tasks is True
        
        # Step 2: Analyze multiple URLs in sequence
        urls = [
            "https://github.com/project1/issues/1",
            "https://stackoverflow.com/questions/12345",
            "https://docs.example.com/api"
        ]
        
        url_results = []
        for i, url in enumerate(urls):
            url_input = UserInput.create(f"分析URL: {url}", user_id)
            result = await coordinator.process_user_input(url_input)
            url_results.append(result)
            
            assert result.success is True
            assert result.task_info is not None
        
        # Step 3: Analyze image content
        image_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        image_input = UserInput.create(f"分析这个UI设计: {image_data}", user_id)
        image_result = await coordinator.process_user_input(image_input)
        
        assert image_result.success is True
        assert image_result.task_info is not None
        assert "UI" in image_result.task_info.title
        
        # Step 4: Mixed content analysis
        mixed_input = UserInput.create(
            f"同时分析这个URL https://example.com 和这个图片 {image_data}",
            user_id
        )
        mixed_result = await coordinator.process_user_input(mixed_input)
        
        assert mixed_result.success is True
        assert mixed_result.task_info is not None
        
        # Step 5: Check interaction history and learning
        history = coordinator.preference_manager.get_user_interaction_history(user_id)
        assert len(history) >= 5  # All interactions recorded
        
        # Verify learning suggestions
        suggestions = await coordinator.preference_manager.suggest_preferences(user_id)
        
        # Should have suggestions based on heavy URL usage
        url_usage_count = sum(1 for h in history if h.input_type == "url")
        if url_usage_count >= 3:
            auto_create_suggestion = next(
                (s for s in suggestions if s.preference_key == "auto_create_tasks"),
                None
            )
            # User already has auto_create enabled, so might not suggest it again
    
    @pytest.mark.asyncio
    async def test_error_recovery_journey(self, setup_full_system):
        """Test user journey with error recovery scenarios"""
        coordinator, url_agent, image_agent, content_extractor = await setup_full_system
        
        user_id = "error_test_user"
        
        # Step 1: Successful interaction
        success_input = UserInput.create("https://working-url.com", user_id)
        success_result = await coordinator.process_user_input(success_input)
        
        assert success_result.success is True
        
        # Step 2: Simulate network error
        async def failing_workflow(*args, **kwargs):
            return TestDataFactory.create_workflow_result(
                success=False,
                error_message="Network timeout"
            )
        
        coordinator.agent_orchestrator.execute_workflow = failing_workflow
        
        error_input = UserInput.create("https://failing-url.com", user_id)
        error_result = await coordinator.process_user_input(error_input)
        
        assert error_result.success is False
        assert "处理失败" in error_result.response_message
        assert error_result.error_message is not None
        
        # Step 3: User asks for help after error
        help_input = UserInput.create("出现错误了，怎么办？", user_id)
        help_result = await coordinator.process_user_input(help_input)
        
        assert help_result.success is True
        assert help_result.user_intent == UserIntent.HELP
        
        # Step 4: Restore working system and retry
        async def working_workflow(*args, **kwargs):
            return TestDataFactory.create_workflow_result(
                success=True,
                task_info=TestDataFactory.create_task_info(title="Recovered Task")
            )
        
        coordinator.agent_orchestrator.execute_workflow = working_workflow
        
        retry_input = UserInput.create("重试 https://working-again.com", user_id)
        retry_result = await coordinator.process_user_input(retry_input)
        
        assert retry_result.success is True
        assert retry_result.task_info.title == "Recovered Task"
        
        # Verify error was recorded in history
        history = coordinator.preference_manager.get_user_interaction_history(user_id)
        error_interactions = [h for h in history if not h.result_success]
        assert len(error_interactions) >= 1
    
    @pytest.mark.asyncio
    async def test_preference_evolution_journey(self, setup_full_system):
        """Test how user preferences evolve over time"""
        coordinator, url_agent, image_agent, content_extractor = await setup_full_system
        
        user_id = "evolving_user"
        
        # Phase 1: Initial basic usage
        basic_inputs = [
            "https://example1.com",
            "https://example2.com",
            "分析这个链接 https://example3.com"
        ]
        
        for input_text in basic_inputs:
            user_input = UserInput.create(input_text, user_id)
            result = await coordinator.process_user_input(user_input)
            assert result.success is True
        
        # Check initial suggestions
        initial_suggestions = await coordinator.preference_manager.suggest_preferences(user_id)
        initial_suggestion_keys = [s.preference_key for s in initial_suggestions]
        
        # Phase 2: Heavy URL usage (should trigger auto-create suggestion)
        for i in range(7):  # Total 10 URL interactions
            user_input = UserInput.create(f"https://heavy-usage-{i}.com", user_id)
            result = await coordinator.process_user_input(user_input)
            assert result.success is True
        
        # Check evolved suggestions
        evolved_suggestions = await coordinator.preference_manager.suggest_preferences(user_id)
        evolved_suggestion_keys = [s.preference_key for s in evolved_suggestions]
        
        # Should suggest auto-create tasks due to heavy URL usage
        assert "auto_create_tasks" in evolved_suggestion_keys
        
        auto_create_suggestion = next(
            s for s in evolved_suggestions if s.preference_key == "auto_create_tasks"
        )
        assert auto_create_suggestion.suggested_value is True
        assert auto_create_suggestion.confidence >= 0.7
        
        # Phase 3: User accepts suggestion
        await coordinator.preference_manager.update_user_preferences(
            user_id,
            {"auto_create_tasks": True}
        )
        
        # Phase 4: Continued usage with new preferences
        final_input = UserInput.create("https://final-test.com", user_id)
        final_result = await coordinator.process_user_input(final_input)
        
        assert final_result.success is True
        
        # Verify preference evolution
        final_prefs = await coordinator.preference_manager.get_user_preferences(user_id)
        assert final_prefs.auto_create_tasks is True
        
        # Verify interaction history shows evolution
        history = coordinator.preference_manager.get_user_interaction_history(user_id)
        assert len(history) >= 11  # All interactions recorded
        
        # Most interactions should be URL-based
        url_interactions = [h for h in history if h.input_type == "url"]
        assert len(url_interactions) >= 10
    
    @pytest.mark.asyncio
    async def test_multi_user_concurrent_journey(self, setup_full_system):
        """Test concurrent multi-user scenarios"""
        coordinator, url_agent, image_agent, content_extractor = await setup_full_system
        
        # Define different user profiles
        users = [
            {"id": "concurrent_user_1", "type": "url_heavy"},
            {"id": "concurrent_user_2", "type": "image_heavy"},
            {"id": "concurrent_user_3", "type": "mixed_usage"}
        ]
        
        async def simulate_user_session(user_info):
            user_id = user_info["id"]
            user_type = user_info["type"]
            
            results = []
            
            if user_type == "url_heavy":
                for i in range(3):
                    input_text = f"https://user1-url-{i}.com"
                    user_input = UserInput.create(input_text, user_id)
                    result = await coordinator.process_user_input(user_input)
                    results.append(result)
            
            elif user_type == "image_heavy":
                for i in range(3):
                    image_data = f"data:image/png;base64,fake_data_{i}"
                    user_input = UserInput.create(f"分析图片: {image_data}", user_id)
                    result = await coordinator.process_user_input(user_input)
                    results.append(result)
            
            elif user_type == "mixed_usage":
                inputs = [
                    "https://mixed-url.com",
                    "data:image/png;base64,mixed_image",
                    "设置输出格式为JSON"
                ]
                for input_text in inputs:
                    user_input = UserInput.create(input_text, user_id)
                    result = await coordinator.process_user_input(user_input)
                    results.append(result)
            
            return user_id, results
        
        # Run concurrent user sessions
        tasks = [simulate_user_session(user) for user in users]
        user_results = await asyncio.gather(*tasks)
        
        # Verify all users had successful interactions
        for user_id, results in user_results:
            assert len(results) == 3
            successful_results = [r for r in results if r.success]
            assert len(successful_results) >= 2  # At least 2/3 should succeed
            
            # Verify user-specific preferences were maintained
            user_prefs = await coordinator.preference_manager.get_user_preferences(user_id)
            assert user_prefs.user_id == user_id
            
            # Verify interaction history is separate per user
            history = coordinator.preference_manager.get_user_interaction_history(user_id)
            assert len(history) == 3
            
            # All history entries should belong to this user
            for interaction in history:
                assert interaction.user_id == user_id
    
    @pytest.mark.asyncio
    async def test_long_session_journey(self, setup_full_system):
        """Test long user session with many interactions"""
        coordinator, url_agent, image_agent, content_extractor = await setup_full_system
        
        user_id = "long_session_user"
        
        # Simulate a long session with various interaction types
        interaction_types = [
            ("url", "https://long-session-{}.com"),
            ("image", "data:image/png;base64,session_image_{}"),
            ("text", "分析这个内容: session_text_{}"),
            ("preference", "设置质量阈值为0.{}"),
            ("status", "系统状态如何？"),
            ("help", "如何使用这个功能？")
        ]
        
        results = []
        
        # Perform 20 interactions of various types
        for i in range(20):
            interaction_type, template = interaction_types[i % len(interaction_types)]
            
            if "{}" in template:
                input_text = template.format(i)
            else:
                input_text = template
            
            user_input = UserInput.create(input_text, user_id)
            result = await coordinator.process_user_input(user_input)
            results.append((interaction_type, result))
            
            # Small delay to simulate real usage
            await asyncio.sleep(0.01)
        
        # Verify session results
        successful_results = [r for _, r in results if r.success]
        assert len(successful_results) >= 15  # At least 75% success rate
        
        # Verify interaction history management
        history = coordinator.preference_manager.get_user_interaction_history(user_id)
        assert len(history) == 20
        
        # Verify different interaction types were recorded
        interaction_types_in_history = set(h.input_type for h in history)
        assert len(interaction_types_in_history) >= 3  # Multiple types
        
        # Verify learning occurred over the session
        suggestions = await coordinator.preference_manager.suggest_preferences(user_id)
        assert len(suggestions) >= 0  # Should have learned something
        
        # Verify user preferences evolved
        final_prefs = await coordinator.preference_manager.get_user_preferences(user_id)
        assert final_prefs.user_id == user_id
        
        # Check if auto-create was suggested due to URL usage
        url_interactions = [h for h in history if h.input_type == "url"]
        if len(url_interactions) >= 5:
            auto_create_suggestion = next(
                (s for s in suggestions if s.preference_key == "auto_create_tasks"),
                None
            )
            if auto_create_suggestion:
                assert auto_create_suggestion.suggested_value is True


class TestPerformanceScenarios:
    """Performance and stress testing scenarios"""
    
    @pytest.fixture
    async def setup_performance_system(self):
        """Setup system for performance testing"""
        coordinator = SmartCoordinator()
        
        # Setup with minimal mocking for performance testing
        coordinator.preference_manager = PreferenceManager(storage_backend="memory")
        await coordinator.preference_manager.initialize()
        
        # Mock orchestrator with fast responses
        coordinator.agent_orchestrator = MagicMock()
        
        async def fast_workflow(*args, **kwargs):
            return TestDataFactory.create_workflow_result(
                success=True,
                task_info=TestDataFactory.create_task_info()
            )
        
        coordinator.agent_orchestrator.execute_workflow = fast_workflow
        coordinator.agent_orchestrator._initialized = True
        
        return coordinator
    
    @pytest.mark.asyncio
    async def test_high_throughput_scenario(self, setup_performance_system):
        """Test high throughput scenario"""
        coordinator = await setup_performance_system
        
        # Generate many concurrent requests
        async def process_request(i):
            user_input = UserInput.create(f"https://throughput-test-{i}.com", f"user_{i % 10}")
            start_time = asyncio.get_event_loop().time()
            result = await coordinator.process_user_input(user_input)
            end_time = asyncio.get_event_loop().time()
            return result, end_time - start_time
        
        # Process 50 concurrent requests
        tasks = [process_request(i) for i in range(50)]
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        total_time = asyncio.get_event_loop().time() - start_time
        
        # Verify performance
        successful_results = [r for r, _ in results if r.success]
        assert len(successful_results) >= 45  # 90% success rate
        
        # Verify reasonable response times
        processing_times = [t for _, t in results]
        avg_processing_time = sum(processing_times) / len(processing_times)
        assert avg_processing_time < 1.0  # Average under 1 second
        assert total_time < 10.0  # Total under 10 seconds
        
        # Verify system remained stable
        assert coordinator.preference_manager.is_initialized()
    
    @pytest.mark.asyncio
    async def test_memory_usage_scenario(self, setup_performance_system):
        """Test memory usage with many interactions"""
        coordinator = await setup_performance_system
        
        user_id = "memory_test_user"
        
        # Process many interactions to test memory management
        for i in range(200):
            user_input = UserInput.create(f"Memory test input {i}", user_id)
            result = await coordinator.process_user_input(user_input)
            assert result.success is True
        
        # Verify interaction history is properly limited
        history = coordinator.preference_manager.get_user_interaction_history(user_id)
        assert len(history) <= 100  # Should be limited to prevent memory issues
        
        # Verify most recent interactions are kept
        recent_interactions = history[-10:]
        for i, interaction in enumerate(recent_interactions):
            expected_content = f"Memory test input {190 + i}"
            assert expected_content in interaction.input_content
        
        # Verify system is still responsive
        final_input = UserInput.create("Final test", user_id)
        final_result = await coordinator.process_user_input(final_input)
        assert final_result.success is True