"""
Tests for Preference Manager
"""
import pytest
from unittest.mock import patch, mock_open, AsyncMock, MagicMock
from datetime import datetime, timedelta
import json
import tempfile
import os

from app.agent.preference_manager import (
    PreferenceManager, UserPreferences, UserInteraction, PreferenceSuggestion,
    OutputFormat, AnalysisFocus, get_preference_manager
)


class TestUserPreferences:
    """Test UserPreferences data class"""
    
    def test_user_preferences_creation(self):
        """Test UserPreferences creation with defaults"""
        prefs = UserPreferences(user_id="test_user")
        
        assert prefs.user_id == "test_user"
        assert prefs.output_format == OutputFormat.STRUCTURED
        assert prefs.analysis_focus == [AnalysisFocus.TECHNICAL, AnalysisFocus.BUSINESS]
        assert prefs.language == "中文"
        assert prefs.task_types == []
        assert prefs.quality_threshold == 0.7
        assert prefs.auto_create_tasks is False
        assert prefs.notification_enabled is True
        assert prefs.created_at is not None
        assert prefs.updated_at is not None
    
    def test_user_preferences_custom_values(self):
        """Test UserPreferences with custom values"""
        custom_time = datetime(2023, 1, 1)
        
        prefs = UserPreferences(
            user_id="custom_user",
            output_format=OutputFormat.JSON,
            analysis_focus=[AnalysisFocus.FINANCIAL],
            language="English",
            task_types=["development", "testing"],
            quality_threshold=0.9,
            auto_create_tasks=True,
            notification_enabled=False,
            created_at=custom_time,
            updated_at=custom_time
        )
        
        assert prefs.user_id == "custom_user"
        assert prefs.output_format == OutputFormat.JSON
        assert prefs.analysis_focus == [AnalysisFocus.FINANCIAL]
        assert prefs.language == "English"
        assert prefs.task_types == ["development", "testing"]
        assert prefs.quality_threshold == 0.9
        assert prefs.auto_create_tasks is True
        assert prefs.notification_enabled is False
        assert prefs.created_at == custom_time
        assert prefs.updated_at == custom_time
    
    def test_to_dict(self):
        """Test UserPreferences to_dict conversion"""
        prefs = UserPreferences(
            user_id="test_user",
            output_format=OutputFormat.JSON,
            analysis_focus=[AnalysisFocus.TECHNICAL, AnalysisFocus.BUSINESS]
        )
        
        data = prefs.to_dict()
        
        assert data["user_id"] == "test_user"
        assert data["output_format"] == "JSON"
        assert data["analysis_focus"] == ["TECHNICAL", "BUSINESS"]
        assert "created_at" in data
        assert "updated_at" in data
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)
    
    def test_from_dict(self):
        """Test UserPreferences from_dict creation"""
        data = {
            "user_id": "test_user",
            "output_format": "MARKDOWN",
            "analysis_focus": ["FINANCIAL", "QUALITY"],
            "language": "English",
            "task_types": ["review"],
            "quality_threshold": 0.8,
            "auto_create_tasks": True,
            "notification_enabled": False,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-02T00:00:00"
        }
        
        prefs = UserPreferences.from_dict(data)
        
        assert prefs.user_id == "test_user"
        assert prefs.output_format == OutputFormat.MARKDOWN
        assert prefs.analysis_focus == [AnalysisFocus.FINANCIAL, AnalysisFocus.QUALITY]
        assert prefs.language == "English"
        assert prefs.task_types == ["review"]
        assert prefs.quality_threshold == 0.8
        assert prefs.auto_create_tasks is True
        assert prefs.notification_enabled is False
        assert prefs.created_at == datetime(2023, 1, 1)
        assert prefs.updated_at == datetime(2023, 1, 2)


class TestUserInteraction:
    """Test UserInteraction data class"""
    
    def test_user_interaction_creation(self):
        """Test UserInteraction creation"""
        timestamp = datetime.utcnow()
        
        interaction = UserInteraction(
            user_id="test_user",
            input_content="test input",
            input_type="text",
            user_intent="chat",
            result_success=True,
            processing_time=1.5,
            timestamp=timestamp
        )
        
        assert interaction.user_id == "test_user"
        assert interaction.input_content == "test input"
        assert interaction.input_type == "text"
        assert interaction.user_intent == "chat"
        assert interaction.result_success is True
        assert interaction.processing_time == 1.5
        assert interaction.timestamp == timestamp
        assert interaction.metadata == {}
    
    def test_user_interaction_with_metadata(self):
        """Test UserInteraction with metadata"""
        metadata = {"test_key": "test_value"}
        
        interaction = UserInteraction(
            user_id="test_user",
            input_content="test",
            input_type="text",
            user_intent="chat",
            result_success=True,
            processing_time=1.0,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )
        
        assert interaction.metadata == metadata


class TestPreferenceSuggestion:
    """Test PreferenceSuggestion data class"""
    
    def test_preference_suggestion_creation(self):
        """Test PreferenceSuggestion creation"""
        suggestion = PreferenceSuggestion(
            preference_key="output_format",
            suggested_value="JSON",
            reason="You often work with structured data",
            confidence=0.8
        )
        
        assert suggestion.preference_key == "output_format"
        assert suggestion.suggested_value == "JSON"
        assert suggestion.reason == "You often work with structured data"
        assert suggestion.confidence == 0.8


class TestPreferenceManager:
    """Test PreferenceManager functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.manager = PreferenceManager(storage_backend="memory")
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test preference manager initialization"""
        await self.manager.initialize()
        
        assert self.manager.is_initialized()
        assert self.manager.storage_backend == "memory"
        assert self.manager.learning_enabled is True
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_new_user(self):
        """Test getting preferences for new user"""
        await self.manager.initialize()
        
        prefs = await self.manager.get_user_preferences("new_user")
        
        assert prefs.user_id == "new_user"
        assert prefs.output_format == OutputFormat.STRUCTURED
        assert "new_user" in self.manager.user_preferences
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_existing_user(self):
        """Test getting preferences for existing user"""
        await self.manager.initialize()
        
        # Create existing preferences
        existing_prefs = UserPreferences(
            user_id="existing_user",
            output_format=OutputFormat.JSON
        )
        self.manager.user_preferences["existing_user"] = existing_prefs
        
        prefs = await self.manager.get_user_preferences("existing_user")
        
        assert prefs.user_id == "existing_user"
        assert prefs.output_format == OutputFormat.JSON
    
    @pytest.mark.asyncio
    async def test_update_user_preferences(self):
        """Test updating user preferences"""
        await self.manager.initialize()
        
        # Get initial preferences
        prefs = await self.manager.get_user_preferences("test_user")
        initial_updated_at = prefs.updated_at
        
        # Update preferences
        updates = {
            "output_format": "JSON",
            "language": "English",
            "quality_threshold": 0.9,
            "auto_create_tasks": True,
            "analysis_focus": ["TECHNICAL", "FINANCIAL"],
            "task_types": ["development"]
        }
        
        await self.manager.update_user_preferences("test_user", updates)
        
        # Check updates
        updated_prefs = await self.manager.get_user_preferences("test_user")
        assert updated_prefs.output_format == OutputFormat.JSON
        assert updated_prefs.language == "English"
        assert updated_prefs.quality_threshold == 0.9
        assert updated_prefs.auto_create_tasks is True
        assert updated_prefs.analysis_focus == [AnalysisFocus.TECHNICAL, AnalysisFocus.FINANCIAL]
        assert updated_prefs.task_types == ["development"]
        assert updated_prefs.updated_at > initial_updated_at
    
    @pytest.mark.asyncio
    async def test_update_user_preferences_invalid_key(self):
        """Test updating user preferences with invalid key"""
        await self.manager.initialize()
        
        updates = {"invalid_key": "invalid_value"}
        
        # Should not raise exception, just ignore invalid keys
        await self.manager.update_user_preferences("test_user", updates)
        
        prefs = await self.manager.get_user_preferences("test_user")
        assert not hasattr(prefs, "invalid_key")
    
    @pytest.mark.asyncio
    async def test_learn_from_interaction(self):
        """Test learning from user interaction"""
        await self.manager.initialize()
        
        # Create mock user input and result
        user_input = MagicMock()
        user_input.content = "test input"
        user_input.input_type = "url"
        
        result = MagicMock()
        result.user_intent = "create_task"
        result.success = True
        result.processing_time = 2.0
        
        await self.manager.learn_from_interaction("test_user", user_input, result)
        
        # Check interaction was recorded
        history = self.manager.get_user_interaction_history("test_user")
        assert len(history) == 1
        assert history[0].user_id == "test_user"
        assert history[0].input_content == "test input"
        assert history[0].input_type == "url"
        assert history[0].user_intent == "create_task"
        assert history[0].result_success is True
        assert history[0].processing_time == 2.0
    
    @pytest.mark.asyncio
    async def test_learn_from_interaction_disabled(self):
        """Test learning when disabled"""
        await self.manager.initialize()
        self.manager.learning_enabled = False
        
        user_input = MagicMock()
        result = MagicMock()
        
        await self.manager.learn_from_interaction("test_user", user_input, result)
        
        # Should not record interaction
        history = self.manager.get_user_interaction_history("test_user")
        assert len(history) == 0
    
    @pytest.mark.asyncio
    async def test_learn_from_interaction_history_limit(self):
        """Test interaction history limit"""
        await self.manager.initialize()
        
        # Add more than 100 interactions
        for i in range(105):
            user_input = MagicMock()
            user_input.content = f"input {i}"
            user_input.input_type = "text"
            
            result = MagicMock()
            result.user_intent = "chat"
            result.success = True
            result.processing_time = 1.0
            
            await self.manager.learn_from_interaction("test_user", user_input, result)
        
        # Should keep only last 100
        history = self.manager.get_user_interaction_history("test_user")
        assert len(history) == 100
        assert history[0].input_content == "input 5"  # First 5 should be removed
        assert history[-1].input_content == "input 104"
    
    @pytest.mark.asyncio
    async def test_suggest_preferences_auto_create_tasks(self):
        """Test preference suggestions for auto create tasks"""
        await self.manager.initialize()
        
        # Add multiple URL interactions
        for i in range(6):
            user_input = MagicMock()
            user_input.content = f"url input {i}"
            user_input.input_type = "url"
            
            result = MagicMock()
            result.user_intent = "create_task"
            result.success = True
            result.processing_time = 1.0
            
            await self.manager.learn_from_interaction("test_user", user_input, result)
        
        suggestions = await self.manager.suggest_preferences("test_user")
        
        # Should suggest auto_create_tasks
        auto_create_suggestion = next(
            (s for s in suggestions if s.preference_key == "auto_create_tasks"), 
            None
        )
        assert auto_create_suggestion is not None
        assert auto_create_suggestion.suggested_value is True
        assert auto_create_suggestion.confidence == 0.8
    
    @pytest.mark.asyncio
    async def test_suggest_preferences_quality_threshold(self):
        """Test preference suggestions for quality threshold"""
        await self.manager.initialize()
        
        # Set high quality threshold
        await self.manager.update_user_preferences("test_user", {"quality_threshold": 0.8})
        
        # Add interactions with low success rate
        for i in range(10):
            user_input = MagicMock()
            user_input.content = f"input {i}"
            user_input.input_type = "text"
            
            result = MagicMock()
            result.user_intent = "analyze"
            result.success = i < 3  # Only first 3 succeed (30% success rate)
            result.processing_time = 1.0
            
            await self.manager.learn_from_interaction("test_user", user_input, result)
        
        suggestions = await self.manager.suggest_preferences("test_user")
        
        # Should suggest lowering quality threshold
        quality_suggestion = next(
            (s for s in suggestions if s.preference_key == "quality_threshold"), 
            None
        )
        assert quality_suggestion is not None
        assert quality_suggestion.suggested_value == 0.5
        assert quality_suggestion.confidence == 0.6
    
    @pytest.mark.asyncio
    async def test_suggest_preferences_analysis_focus(self):
        """Test preference suggestions for analysis focus"""
        await self.manager.initialize()
        
        # Add interactions with high processing time
        for i in range(10):
            user_input = MagicMock()
            user_input.content = f"input {i}"
            user_input.input_type = "text"
            
            result = MagicMock()
            result.user_intent = "analyze"
            result.success = True
            result.processing_time = 6.0  # High processing time
            
            await self.manager.learn_from_interaction("test_user", user_input, result)
        
        suggestions = await self.manager.suggest_preferences("test_user")
        
        # Should suggest reducing analysis focus
        focus_suggestion = next(
            (s for s in suggestions if s.preference_key == "analysis_focus"), 
            None
        )
        assert focus_suggestion is not None
        assert focus_suggestion.suggested_value == [AnalysisFocus.TECHNICAL]
        assert focus_suggestion.confidence == 0.7
    
    @pytest.mark.asyncio
    async def test_suggest_preferences_no_history(self):
        """Test preference suggestions with no interaction history"""
        await self.manager.initialize()
        
        suggestions = await self.manager.suggest_preferences("new_user")
        
        assert suggestions == []
    
    @pytest.mark.asyncio
    async def test_learn_preferences_output_format(self):
        """Test learning output format preferences"""
        await self.manager.initialize()
        
        # Add successful URL interactions (should prefer structured format)
        for i in range(15):
            user_input = MagicMock()
            user_input.content = f"url input {i}"
            user_input.input_type = "url"
            
            result = MagicMock()
            result.user_intent = "create_task"
            result.success = True
            result.processing_time = 1.0
            
            await self.manager.learn_from_interaction("test_user", user_input, result)
        
        # Trigger learning by adding one more interaction
        user_input = MagicMock()
        user_input.content = "final input"
        user_input.input_type = "url"
        
        result = MagicMock()
        result.user_intent = "create_task"
        result.success = True
        result.processing_time = 1.0
        
        await self.manager.learn_from_interaction("test_user", user_input, result)
        
        # Check if preferences were learned
        prefs = await self.manager.get_user_preferences("test_user")
        assert prefs.output_format == OutputFormat.STRUCTURED
    
    def test_get_user_interaction_history(self):
        """Test getting user interaction history"""
        # Add some interactions
        interactions = []
        for i in range(5):
            interaction = UserInteraction(
                user_id="test_user",
                input_content=f"input {i}",
                input_type="text",
                user_intent="chat",
                result_success=True,
                processing_time=1.0,
                timestamp=datetime.utcnow()
            )
            interactions.append(interaction)
        
        self.manager.interaction_history["test_user"] = interactions
        
        # Get history
        history = self.manager.get_user_interaction_history("test_user")
        assert len(history) == 5
        
        # Get limited history
        limited_history = self.manager.get_user_interaction_history("test_user", limit=3)
        assert len(limited_history) == 3
        assert limited_history[0].input_content == "input 2"  # Last 3
    
    def test_get_user_interaction_history_no_user(self):
        """Test getting interaction history for non-existent user"""
        history = self.manager.get_user_interaction_history("non_existent_user")
        assert history == []
    
    def test_get_stats(self):
        """Test getting preference manager statistics"""
        # Add some test data
        self.manager.user_preferences["user1"] = UserPreferences(
            user_id="user1",
            output_format=OutputFormat.JSON,
            language="English"
        )
        self.manager.user_preferences["user2"] = UserPreferences(
            user_id="user2",
            output_format=OutputFormat.JSON,
            language="中文"
        )
        
        self.manager.interaction_history["user1"] = [
            UserInteraction(
                user_id="user1",
                input_content="test",
                input_type="text",
                user_intent="chat",
                result_success=True,
                processing_time=1.0,
                timestamp=datetime.utcnow()
            )
        ]
        
        stats = self.manager.get_stats()
        
        assert stats["total_users"] == 2
        assert stats["total_interactions"] == 1
        assert stats["format_distribution"]["JSON"] == 2
        assert stats["language_distribution"]["English"] == 1
        assert stats["language_distribution"]["中文"] == 1
        assert stats["learning_enabled"] is True
        assert stats["storage_backend"] == "memory"
    
    @pytest.mark.asyncio
    async def test_file_storage_save_and_load(self):
        """Test file storage backend"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        
        try:
            # Mock the preferences file path
            with patch('app.agent.preference_manager.PreferenceManager._save_to_file') as mock_save:
                with patch('app.agent.preference_manager.PreferenceManager._load_from_file') as mock_load:
                    manager = PreferenceManager(storage_backend="file")
                    await manager.initialize()
                    
                    mock_load.assert_called_once()
                    
                    # Test saving
                    prefs = UserPreferences(user_id="test_user")
                    await manager._save_preferences("test_user", prefs)
                    
                    mock_save.assert_called_once_with("test_user", prefs)
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_database_storage_not_implemented(self):
        """Test database storage backend (not implemented)"""
        manager = PreferenceManager(storage_backend="database")
        
        with patch('app.agent.preference_manager.logger') as mock_logger:
            await manager.initialize()
            mock_logger.warning.assert_called_with("数据库存储后端尚未实现")
    
    @pytest.mark.asyncio
    async def test_error_handling_in_learning(self):
        """Test error handling in learning process"""
        await self.manager.initialize()
        
        # Mock an exception in _learn_preferences
        with patch.object(self.manager, '_learn_preferences', side_effect=Exception("Test error")):
            with patch('app.agent.preference_manager.logger') as mock_logger:
                # Add enough interactions to trigger learning
                for i in range(5):
                    user_input = MagicMock()
                    user_input.content = f"input {i}"
                    user_input.input_type = "text"
                    
                    result = MagicMock()
                    result.user_intent = "chat"
                    result.success = True
                    result.processing_time = 1.0
                    
                    await self.manager.learn_from_interaction("test_user", user_input, result)
                
                # Should log error but not crash
                mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_suggestions(self):
        """Test error handling in suggestion generation"""
        await self.manager.initialize()
        
        # Mock an exception in suggest_preferences
        with patch.object(self.manager, 'get_user_preferences', side_effect=Exception("Test error")):
            with patch('app.agent.preference_manager.logger') as mock_logger:
                suggestions = await self.manager.suggest_preferences("test_user")
                
                assert suggestions == []
                mock_logger.error.assert_called()


class TestGlobalPreferenceManager:
    """Test global preference manager instance"""
    
    @pytest.mark.asyncio
    async def test_get_preference_manager_singleton(self):
        """Test global preference manager singleton"""
        # Reset global instance
        import app.agent.preference_manager
        app.agent.preference_manager._preference_manager = None
        
        # First call should create instance
        manager1 = await get_preference_manager()
        assert manager1 is not None
        assert manager1.is_initialized()
        
        # Second call should return same instance
        manager2 = await get_preference_manager()
        assert manager1 is manager2
    
    @pytest.mark.asyncio
    async def test_get_preference_manager_initialization_error(self):
        """Test global preference manager initialization error"""
        # Reset global instance
        import app.agent.preference_manager
        app.agent.preference_manager._preference_manager = None
        
        with patch.object(PreferenceManager, 'initialize', side_effect=Exception("Init error")):
            with pytest.raises(Exception, match="Init error"):
                await get_preference_manager()