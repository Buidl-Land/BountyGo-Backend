"""
Tests for Agent Orchestrator
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import time
from datetime import datetime

from app.agent.agent_orchestrator import (
    AgentOrchestrator, WorkflowEngine, WorkflowType, AgentResult, WorkflowResult,
    get_agent_orchestrator
)
from app.agent.unified_config import AgentRole
from app.agent.preference_manager import UserPreferences, OutputFormat, AnalysisFocus
from app.agent.models import TaskInfo, WebContent
from app.agent.exceptions import ConfigurationError


class TestAgentResult:
    """Test AgentResult data class"""
    
    def test_agent_result_creation(self):
        """Test AgentResult creation"""
        result = AgentResult(
            agent_role=AgentRole.URL_PARSER,
            success=True,
            data={"test": "data"},
            confidence=0.8,
            processing_time=1.5,
            error_message=None
        )
        
        assert result.agent_role == AgentRole.URL_PARSER
        assert result.success is True
        assert result.data == {"test": "data"}
        assert result.confidence == 0.8
        assert result.processing_time == 1.5
        assert result.error_message is None
        assert result.metadata == {}
    
    def test_agent_result_with_error(self):
        """Test AgentResult with error"""
        result = AgentResult(
            agent_role=AgentRole.IMAGE_ANALYZER,
            success=False,
            data=None,
            confidence=0.0,
            processing_time=0.5,
            error_message="Test error",
            metadata={"error_code": 500}
        )
        
        assert result.agent_role == AgentRole.IMAGE_ANALYZER
        assert result.success is False
        assert result.data is None
        assert result.confidence == 0.0
        assert result.processing_time == 0.5
        assert result.error_message == "Test error"
        assert result.metadata["error_code"] == 500


class TestWorkflowResult:
    """Test WorkflowResult data class"""
    
    def test_workflow_result_creation(self):
        """Test WorkflowResult creation"""
        agent_results = {
            AgentRole.URL_PARSER: AgentResult(
                agent_role=AgentRole.URL_PARSER,
                success=True,
                data={"test": "data"},
                confidence=0.8,
                processing_time=1.0
            )
        }
        
        task_info = TaskInfo(
            title="Test Task",
            description="Test Description"
        )
        
        result = WorkflowResult(
            success=True,
            task_info=task_info,
            agent_results=agent_results,
            processing_time=2.0,
            quality_score=0.85,
            workflow_type=WorkflowType.URL_PROCESSING
        )
        
        assert result.success is True
        assert result.task_info == task_info
        assert result.agent_results == agent_results
        assert result.processing_time == 2.0
        assert result.quality_score == 0.85
        assert result.error_message is None
        assert result.workflow_type == WorkflowType.URL_PROCESSING
    
    def test_workflow_result_failure(self):
        """Test WorkflowResult for failure case"""
        result = WorkflowResult(
            success=False,
            error_message="Workflow failed",
            processing_time=1.0,
            workflow_type=WorkflowType.IMAGE_PROCESSING
        )
        
        assert result.success is False
        assert result.task_info is None
        assert result.agent_results == {}
        assert result.processing_time == 1.0
        assert result.quality_score == 0.0
        assert result.error_message == "Workflow failed"
        assert result.workflow_type == WorkflowType.IMAGE_PROCESSING


class TestWorkflowEngine:
    """Test WorkflowEngine functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_orchestrator = MagicMock()
        self.workflow_engine = WorkflowEngine(self.mock_orchestrator)
        
        # Setup default preferences
        self.preferences = UserPreferences(
            user_id="test_user",
            output_format=OutputFormat.STRUCTURED,
            quality_threshold=0.7
        )
    
    @pytest.mark.asyncio
    async def test_execute_url_workflow_success(self):
        """Test successful URL workflow execution"""
        # Mock content extractor
        mock_content_extractor = AsyncMock()
        web_content = WebContent(
            url="https://example.com",
            title="Test Page",
            content="Test content",
            meta_description="Test description",
            extracted_at=datetime.utcnow()
        )
        mock_content_extractor.extract_content.return_value = web_content
        self.mock_orchestrator.get_content_extractor.return_value = mock_content_extractor
        
        # Mock URL agent
        mock_url_agent = AsyncMock()
        task_info = TaskInfo(
            title="Test Task",
            description="Test Description",
            reward=100.0
        )
        mock_url_agent.analyze_content.return_value = task_info
        self.mock_orchestrator.get_agent.return_value = mock_url_agent
        
        # Execute workflow
        result = await self.workflow_engine.execute_url_workflow(
            "https://example.com", 
            self.preferences
        )
        
        assert result.success is True
        assert result.task_info == task_info
        assert result.workflow_type == WorkflowType.URL_PROCESSING
        assert AgentRole.CONTENT_EXTRACTOR in result.agent_results
        assert AgentRole.URL_PARSER in result.agent_results
        assert result.processing_time > 0
        assert result.quality_score > 0
    
    @pytest.mark.asyncio
    async def test_execute_url_workflow_no_agent(self):
        """Test URL workflow with missing agent"""
        # Mock content extractor
        mock_content_extractor = AsyncMock()
        mock_content_extractor.extract_content.return_value = MagicMock()
        self.mock_orchestrator.get_content_extractor.return_value = mock_content_extractor
        
        # No URL agent available
        self.mock_orchestrator.get_agent.return_value = None
        
        result = await self.workflow_engine.execute_url_workflow(
            "https://example.com", 
            self.preferences
        )
        
        assert result.success is False
        assert "URL解析Agent未配置" in result.error_message
        assert result.workflow_type == WorkflowType.URL_PROCESSING
    
    @pytest.mark.asyncio
    async def test_execute_url_workflow_with_quality_check(self):
        """Test URL workflow with quality check"""
        # Setup high quality threshold
        high_quality_prefs = UserPreferences(
            user_id="test_user",
            quality_threshold=0.8
        )
        
        # Mock content extractor
        mock_content_extractor = AsyncMock()
        web_content = WebContent(
            url="https://example.com",
            title="Test Page",
            content="Test content",
            meta_description="Test description",
            extracted_at=datetime.utcnow()
        )
        mock_content_extractor.extract_content.return_value = web_content
        self.mock_orchestrator.get_content_extractor.return_value = mock_content_extractor
        
        # Mock URL agent
        mock_url_agent = AsyncMock()
        task_info = TaskInfo(
            title="Test Task",
            description="Test Description with sufficient length for quality check",
            reward=100.0,
            tags=["test", "quality"]
        )
        mock_url_agent.analyze_content.return_value = task_info
        
        # Mock quality agent
        mock_quality_agent = AsyncMock()
        
        def mock_get_agent(role):
            if role == AgentRole.URL_PARSER:
                return mock_url_agent
            elif role == AgentRole.QUALITY_CHECKER:
                return mock_quality_agent
            return None
        
        self.mock_orchestrator.get_agent.side_effect = mock_get_agent
        
        result = await self.workflow_engine.execute_url_workflow(
            "https://example.com", 
            high_quality_prefs
        )
        
        assert result.success is True
        assert AgentRole.QUALITY_CHECKER in result.agent_results
    
    @pytest.mark.asyncio
    async def test_execute_image_workflow_success(self):
        """Test successful image workflow execution"""
        # Mock image agent
        mock_image_agent = AsyncMock()
        mock_image_agent.client = MagicMock()  # Simulate initialized agent
        task_info = TaskInfo(
            title="Image Analysis Task",
            description="Analysis of uploaded image"
        )
        mock_image_agent.analyze_image.return_value = task_info
        self.mock_orchestrator.get_agent.return_value = mock_image_agent
        
        # Execute workflow
        image_data = b"fake_image_data"
        result = await self.workflow_engine.execute_image_workflow(
            image_data, 
            self.preferences
        )
        
        assert result.success is True
        assert result.task_info == task_info
        assert result.workflow_type == WorkflowType.IMAGE_PROCESSING
        assert AgentRole.IMAGE_ANALYZER in result.agent_results
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_execute_image_workflow_agent_initialization(self):
        """Test image workflow with agent initialization"""
        # Mock image agent without client
        mock_image_agent = AsyncMock()
        mock_image_agent.client = None  # Not initialized
        mock_image_agent.initialize = AsyncMock()
        task_info = TaskInfo(title="Test", description="Test")
        mock_image_agent.analyze_image.return_value = task_info
        self.mock_orchestrator.get_agent.return_value = mock_image_agent
        
        result = await self.workflow_engine.execute_image_workflow(
            "image_data", 
            self.preferences
        )
        
        # Should call initialize
        mock_image_agent.initialize.assert_called_once()
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_image_workflow_no_agent(self):
        """Test image workflow with missing agent"""
        self.mock_orchestrator.get_agent.return_value = None
        
        result = await self.workflow_engine.execute_image_workflow(
            "image_data", 
            self.preferences
        )
        
        assert result.success is False
        assert "图片分析Agent未配置" in result.error_message
        assert result.workflow_type == WorkflowType.IMAGE_PROCESSING
    
    @pytest.mark.asyncio
    async def test_execute_text_workflow_success(self):
        """Test successful text workflow execution"""
        # Mock URL agent (used for text processing)
        mock_url_agent = AsyncMock()
        task_info = TaskInfo(
            title="Text Analysis Task",
            description="Analysis of text content"
        )
        mock_url_agent.analyze_content.return_value = task_info
        self.mock_orchestrator.get_agent.return_value = mock_url_agent
        
        result = await self.workflow_engine.execute_text_workflow(
            "This is test text content", 
            self.preferences
        )
        
        assert result.success is True
        assert result.task_info == task_info
        assert result.workflow_type == WorkflowType.TEXT_PROCESSING
        assert AgentRole.URL_PARSER in result.agent_results
        
        # Check that WebContent was created properly
        call_args = mock_url_agent.analyze_content.call_args[0][0]
        assert isinstance(call_args, WebContent)
        assert call_args.title == "Direct Text Input"
        assert call_args.content == "This is test text content"
    
    @pytest.mark.asyncio
    async def test_execute_mixed_workflow_success(self):
        """Test successful mixed workflow execution"""
        mixed_data = {
            "urls": ["https://example.com"],
            "image_data": "fake_image_data",
            "text": "Some text content"
        }
        
        # Mock workflow methods
        url_result = WorkflowResult(
            success=True,
            task_info=TaskInfo(title="URL Task", description="URL analysis"),
            agent_results={AgentRole.URL_PARSER: MagicMock()},
            workflow_type=WorkflowType.URL_PROCESSING
        )
        
        image_result = WorkflowResult(
            success=True,
            task_info=TaskInfo(title="Image Task", description="Image analysis"),
            agent_results={AgentRole.IMAGE_ANALYZER: MagicMock()},
            workflow_type=WorkflowType.IMAGE_PROCESSING
        )
        
        text_result = WorkflowResult(
            success=True,
            task_info=TaskInfo(title="Text Task", description="Text analysis"),
            agent_results={AgentRole.URL_PARSER: MagicMock()},
            workflow_type=WorkflowType.TEXT_PROCESSING
        )
        
        self.workflow_engine.execute_url_workflow = AsyncMock(return_value=url_result)
        self.workflow_engine.execute_image_workflow = AsyncMock(return_value=image_result)
        self.workflow_engine.execute_text_workflow = AsyncMock(return_value=text_result)
        
        # Mock merge method
        merged_task = TaskInfo(title="Merged Task", description="Merged analysis")
        self.workflow_engine._merge_task_infos = AsyncMock(return_value=merged_task)
        
        result = await self.workflow_engine.execute_mixed_workflow(
            mixed_data, 
            self.preferences
        )
        
        assert result.success is True
        assert result.task_info == merged_task
        assert result.workflow_type == WorkflowType.MIXED_PROCESSING
        
        # Verify all workflows were called
        self.workflow_engine.execute_url_workflow.assert_called_once()
        self.workflow_engine.execute_image_workflow.assert_called_once()
        self.workflow_engine.execute_text_workflow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_mixed_workflow_partial_failure(self):
        """Test mixed workflow with partial failures"""
        mixed_data = {
            "urls": ["https://example.com"],
            "image_data": "fake_image_data",
            "text": "Some text content"
        }
        
        # Mock partial success
        url_result = WorkflowResult(success=False, error_message="URL failed")
        image_result = WorkflowResult(
            success=True,
            task_info=TaskInfo(title="Image Task", description="Image analysis"),
            agent_results={AgentRole.IMAGE_ANALYZER: MagicMock()}
        )
        text_result = WorkflowResult(success=False, error_message="Text failed")
        
        self.workflow_engine.execute_url_workflow = AsyncMock(return_value=url_result)
        self.workflow_engine.execute_image_workflow = AsyncMock(return_value=image_result)
        self.workflow_engine.execute_text_workflow = AsyncMock(return_value=text_result)
        
        # Mock merge method
        self.workflow_engine._merge_task_infos = AsyncMock(return_value=image_result.task_info)
        
        result = await self.workflow_engine.execute_mixed_workflow(
            mixed_data, 
            self.preferences
        )
        
        assert result.success is True  # Should succeed if at least one workflow succeeds
        assert result.task_info == image_result.task_info
    
    @pytest.mark.asyncio
    async def test_execute_mixed_workflow_all_failures(self):
        """Test mixed workflow with all failures"""
        mixed_data = {
            "urls": ["https://example.com"],
            "image_data": "fake_image_data",
            "text": "Some text content"
        }
        
        # Mock all failures
        failure_result = WorkflowResult(success=False, error_message="Failed")
        
        self.workflow_engine.execute_url_workflow = AsyncMock(return_value=failure_result)
        self.workflow_engine.execute_image_workflow = AsyncMock(return_value=failure_result)
        self.workflow_engine.execute_text_workflow = AsyncMock(return_value=failure_result)
        
        result = await self.workflow_engine.execute_mixed_workflow(
            mixed_data, 
            self.preferences
        )
        
        assert result.success is False
        assert "所有内容处理都失败了" in result.error_message
        assert result.workflow_type == WorkflowType.MIXED_PROCESSING
    
    @pytest.mark.asyncio
    async def test_run_quality_check_pass(self):
        """Test quality check that passes"""
        task_info = TaskInfo(
            title="Good Task Title",
            description="This is a sufficiently long description that should pass quality check",
            reward=100.0,
            tags=["test", "quality"],
            deadline=datetime.utcnow()
        )
        
        result = await self.workflow_engine._run_quality_check(task_info, self.preferences)
        
        assert result.success is True
        assert result.agent_role == AgentRole.QUALITY_CHECKER
        assert result.confidence >= self.preferences.quality_threshold
        assert "quality_score" in result.data
        assert "issues" in result.data
    
    @pytest.mark.asyncio
    async def test_run_quality_check_fail(self):
        """Test quality check that fails"""
        task_info = TaskInfo(
            title="Bad",  # Too short
            description="Short"  # Too short
        )
        
        high_threshold_prefs = UserPreferences(
            user_id="test_user",
            quality_threshold=0.9
        )
        
        result = await self.workflow_engine._run_quality_check(task_info, high_threshold_prefs)
        
        assert result.success is False
        assert result.confidence < high_threshold_prefs.quality_threshold
        assert len(result.data["issues"]) > 0
    
    def test_calculate_quality_score(self):
        """Test quality score calculation"""
        agent_results = {
            AgentRole.URL_PARSER: AgentResult(
                agent_role=AgentRole.URL_PARSER,
                success=True,
                data=None,
                confidence=0.8,
                processing_time=1.0
            ),
            AgentRole.QUALITY_CHECKER: AgentResult(
                agent_role=AgentRole.QUALITY_CHECKER,
                success=True,
                data=None,
                confidence=0.9,
                processing_time=0.5
            )
        }
        
        score = self.workflow_engine._calculate_quality_score(agent_results, self.preferences)
        
        # Quality checker has weight 2.0, URL parser has weight 1.0
        # Expected: (0.8 * 1.0 + 0.9 * 2.0) / (1.0 + 2.0) = 2.6 / 3.0 = 0.867
        assert abs(score - 0.8666666666666667) < 0.001
    
    def test_calculate_quality_score_empty(self):
        """Test quality score calculation with empty results"""
        score = self.workflow_engine._calculate_quality_score({}, self.preferences)
        assert score == 0.0
    
    def test_calculate_quality_score_failed_agents(self):
        """Test quality score calculation with failed agents"""
        agent_results = {
            AgentRole.URL_PARSER: AgentResult(
                agent_role=AgentRole.URL_PARSER,
                success=False,
                data=None,
                confidence=0.0,
                processing_time=1.0
            )
        }
        
        score = self.workflow_engine._calculate_quality_score(agent_results, self.preferences)
        assert score == 0.0
    
    @pytest.mark.asyncio
    async def test_merge_task_infos_single(self):
        """Test merging single TaskInfo"""
        task_info = TaskInfo(title="Test", description="Test description")
        
        result = await self.workflow_engine._merge_task_infos([task_info])
        
        assert result == task_info
    
    @pytest.mark.asyncio
    async def test_merge_task_infos_multiple(self):
        """Test merging multiple TaskInfos"""
        task1 = TaskInfo(
            title="Task 1",
            description="Short desc",
            reward=50.0,
            reward_currency="USD",
            tags=["tag1", "tag2"],
            deadline=datetime(2024, 1, 1)
        )
        
        task2 = TaskInfo(
            title="Task 2",
            description="This is a much longer description that should be selected as base",
            reward=100.0,
            reward_currency="EUR",
            tags=["tag2", "tag3"],
            deadline=datetime(2023, 12, 1)  # Earlier deadline
        )
        
        result = await self.workflow_engine._merge_task_infos([task1, task2])
        
        assert result.title == "Task 2"  # Longest description
        assert result.description == task2.description
        assert result.reward == 100.0  # Highest reward
        assert result.reward_currency == "EUR"
        assert set(result.tags) == {"tag1", "tag2", "tag3"}  # Merged tags
        assert result.deadline == datetime(2023, 12, 1)  # Earliest deadline
    
    @pytest.mark.asyncio
    async def test_merge_task_infos_empty(self):
        """Test merging empty TaskInfo list"""
        with pytest.raises(ValueError, match="没有TaskInfo可以合并"):
            await self.workflow_engine._merge_task_infos([])


class TestAgentOrchestrator:
    """Test AgentOrchestrator functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.orchestrator = AgentOrchestrator()
        self.preferences = UserPreferences(user_id="test_user")
    
    @pytest.mark.asyncio
    async def test_initialization_success(self):
        """Test successful orchestrator initialization"""
        with patch.object(self.orchestrator, '_initialize_agents', new_callable=AsyncMock):
            await self.orchestrator.initialize()
            
            assert self.orchestrator.is_initialized()
            assert self.orchestrator.content_extractor is not None
            assert isinstance(self.orchestrator.workflow_engine, WorkflowEngine)
    
    @pytest.mark.asyncio
    async def test_initialization_failure(self):
        """Test orchestrator initialization failure"""
        with patch.object(self.orchestrator, '_initialize_agents', side_effect=Exception("Init failed")):
            with pytest.raises(ConfigurationError, match="Agent orchestrator initialization failed"):
                await self.orchestrator.initialize()
    
    @pytest.mark.asyncio
    async def test_initialize_agents(self):
        """Test agent initialization"""
        # Mock config manager
        mock_config_manager = MagicMock()
        mock_config_manager.get_all_agent_configs.return_value = {
            AgentRole.URL_PARSER: MagicMock(),
            AgentRole.IMAGE_ANALYZER: MagicMock()
        }
        self.orchestrator.config_manager = mock_config_manager
        
        # Mock agent creation
        mock_url_agent = MagicMock()
        mock_image_agent = MagicMock()
        
        with patch.object(self.orchestrator, '_create_agent') as mock_create:
            mock_create.side_effect = [mock_url_agent, mock_image_agent]
            
            await self.orchestrator._initialize_agents()
            
            assert len(self.orchestrator.agents) == 2
            assert self.orchestrator.agents[AgentRole.URL_PARSER] == mock_url_agent
            assert self.orchestrator.agents[AgentRole.IMAGE_ANALYZER] == mock_image_agent
    
    @pytest.mark.asyncio
    async def test_create_agent_url_parser(self):
        """Test creating URL parser agent"""
        from app.agent.config import PPIOModelConfig
        from app.agent.unified_config import AgentConfig, ModelProvider
        
        config = AgentConfig(
            role=AgentRole.URL_PARSER,
            provider=ModelProvider.PPIO,
            model_name="test-model",
            api_key="sk_test_key",
            temperature=0.1
        )
        
        with patch('app.agent.agent_orchestrator.URLParsingAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent
            
            agent = await self.orchestrator._create_agent(AgentRole.URL_PARSER, config)
            
            assert agent == mock_agent
            mock_agent_class.assert_called_once()
            
            # Check that PPIOModelConfig was created correctly
            call_args = mock_agent_class.call_args[0][0]
            assert isinstance(call_args, PPIOModelConfig)
            assert call_args.api_key == "sk_test_key"
            assert call_args.model_name == "test-model"
    
    @pytest.mark.asyncio
    async def test_create_agent_image_analyzer(self):
        """Test creating image analyzer agent"""
        from app.agent.unified_config import AgentConfig, ModelProvider
        
        config = AgentConfig(
            role=AgentRole.IMAGE_ANALYZER,
            provider=ModelProvider.PPIO,
            model_name="vision-model",
            api_key="sk_test_key",
            temperature=0.1
        )
        
        with patch('app.agent.agent_orchestrator.ImageParsingAgent') as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            
            agent = await self.orchestrator._create_agent(AgentRole.IMAGE_ANALYZER, config)
            
            assert agent == mock_agent
            mock_agent.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_agent_unsupported_role(self):
        """Test creating agent with unsupported role"""
        from app.agent.unified_config import AgentConfig, ModelProvider
        
        config = AgentConfig(
            role=AgentRole.QUALITY_CHECKER,  # Not implemented
            provider=ModelProvider.PPIO,
            model_name="test-model",
            api_key="sk_test_key",
            temperature=0.1
        )
        
        agent = await self.orchestrator._create_agent(AgentRole.QUALITY_CHECKER, config)
        
        assert agent is None
    
    @pytest.mark.asyncio
    async def test_create_agent_error(self):
        """Test agent creation error handling"""
        from app.agent.unified_config import AgentConfig, ModelProvider
        
        config = AgentConfig(
            role=AgentRole.URL_PARSER,
            provider=ModelProvider.PPIO,
            model_name="test-model",
            api_key="sk_test_key",
            temperature=0.1
        )
        
        with patch('app.agent.agent_orchestrator.URLParsingAgent', side_effect=Exception("Creation failed")):
            agent = await self.orchestrator._create_agent(AgentRole.URL_PARSER, config)
            
            assert agent is None
    
    def test_get_agent(self):
        """Test getting agent instance"""
        mock_agent = MagicMock()
        self.orchestrator.agents[AgentRole.URL_PARSER] = mock_agent
        
        agent = self.orchestrator.get_agent(AgentRole.URL_PARSER)
        assert agent == mock_agent
        
        # Test non-existent agent
        agent = self.orchestrator.get_agent(AgentRole.IMAGE_ANALYZER)
        assert agent is None
    
    def test_get_content_extractor(self):
        """Test getting content extractor"""
        # First call should create extractor
        extractor1 = self.orchestrator.get_content_extractor()
        assert extractor1 is not None
        
        # Second call should return same instance
        extractor2 = self.orchestrator.get_content_extractor()
        assert extractor1 is extractor2
        
        # If already set, should return existing
        self.orchestrator.content_extractor = MagicMock()
        extractor3 = self.orchestrator.get_content_extractor()
        assert extractor3 == self.orchestrator.content_extractor
    
    @pytest.mark.asyncio
    async def test_execute_workflow_url_processing(self):
        """Test executing URL processing workflow"""
        self.orchestrator._initialized = True
        
        # Mock workflow engine
        mock_result = WorkflowResult(success=True, workflow_type=WorkflowType.URL_PROCESSING)
        self.orchestrator.workflow_engine.execute_url_workflow = AsyncMock(return_value=mock_result)
        
        result = await self.orchestrator.execute_workflow(
            WorkflowType.URL_PROCESSING,
            "https://example.com",
            self.preferences
        )
        
        assert result == mock_result
        self.orchestrator.workflow_engine.execute_url_workflow.assert_called_once_with(
            "https://example.com", self.preferences, True
        )
    
    @pytest.mark.asyncio
    async def test_execute_workflow_image_processing(self):
        """Test executing image processing workflow"""
        self.orchestrator._initialized = True
        
        mock_result = WorkflowResult(success=True, workflow_type=WorkflowType.IMAGE_PROCESSING)
        self.orchestrator.workflow_engine.execute_image_workflow = AsyncMock(return_value=mock_result)
        
        result = await self.orchestrator.execute_workflow(
            WorkflowType.IMAGE_PROCESSING,
            b"image_data",
            self.preferences
        )
        
        assert result == mock_result
        self.orchestrator.workflow_engine.execute_image_workflow.assert_called_once_with(
            b"image_data", self.preferences, True
        )
    
    @pytest.mark.asyncio
    async def test_execute_workflow_text_processing(self):
        """Test executing text processing workflow"""
        self.orchestrator._initialized = True
        
        mock_result = WorkflowResult(success=True, workflow_type=WorkflowType.TEXT_PROCESSING)
        self.orchestrator.workflow_engine.execute_text_workflow = AsyncMock(return_value=mock_result)
        
        result = await self.orchestrator.execute_workflow(
            WorkflowType.TEXT_PROCESSING,
            "text content",
            self.preferences
        )
        
        assert result == mock_result
        self.orchestrator.workflow_engine.execute_text_workflow.assert_called_once_with(
            "text content", self.preferences, True
        )
    
    @pytest.mark.asyncio
    async def test_execute_workflow_mixed_processing(self):
        """Test executing mixed processing workflow"""
        self.orchestrator._initialized = True
        
        mixed_data = {"urls": ["https://example.com"], "text": "content"}
        mock_result = WorkflowResult(success=True, workflow_type=WorkflowType.MIXED_PROCESSING)
        self.orchestrator.workflow_engine.execute_mixed_workflow = AsyncMock(return_value=mock_result)
        
        result = await self.orchestrator.execute_workflow(
            WorkflowType.MIXED_PROCESSING,
            mixed_data,
            self.preferences
        )
        
        assert result == mock_result
        self.orchestrator.workflow_engine.execute_mixed_workflow.assert_called_once_with(
            mixed_data, self.preferences, True
        )
    
    @pytest.mark.asyncio
    async def test_execute_workflow_not_initialized(self):
        """Test executing workflow when not initialized"""
        self.orchestrator._initialized = False
        
        with pytest.raises(ConfigurationError, match="Agent编排器未初始化"):
            await self.orchestrator.execute_workflow(
                WorkflowType.URL_PROCESSING,
                "https://example.com",
                self.preferences
            )
    
    @pytest.mark.asyncio
    async def test_execute_workflow_unsupported_type(self):
        """Test executing unsupported workflow type"""
        self.orchestrator._initialized = True
        
        result = await self.orchestrator.execute_workflow(
            "UNSUPPORTED_TYPE",
            "data",
            self.preferences
        )
        
        assert result.success is False
        assert "不支持的工作流类型" in result.error_message
    
    @pytest.mark.asyncio
    async def test_execute_workflow_exception(self):
        """Test workflow execution with exception"""
        self.orchestrator._initialized = True
        
        self.orchestrator.workflow_engine.execute_url_workflow = AsyncMock(
            side_effect=Exception("Workflow error")
        )
        
        result = await self.orchestrator.execute_workflow(
            WorkflowType.URL_PROCESSING,
            "https://example.com",
            self.preferences
        )
        
        assert result.success is False
        assert result.error_message == "Workflow error"
        assert result.workflow_type == WorkflowType.URL_PROCESSING
    
    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting orchestrator status"""
        # Setup some agents
        self.orchestrator.agents[AgentRole.URL_PARSER] = MagicMock()
        self.orchestrator.agents[AgentRole.IMAGE_ANALYZER] = MagicMock()
        self.orchestrator._initialized = True
        
        # Setup content extractor
        from app.agent.content_extractor import ContentExtractor
        self.orchestrator.content_extractor = ContentExtractor()
        
        status = await self.orchestrator.get_status()
        
        assert status["initialized"] is True
        assert status["agent_count"] == 2
        assert AgentRole.URL_PARSER.value in status["available_agents"]
        assert AgentRole.IMAGE_ANALYZER.value in status["available_agents"]
        assert status["content_extractor_available"] is True
    
    def test_is_initialized(self):
        """Test initialization check"""
        assert not self.orchestrator.is_initialized()
        
        self.orchestrator._initialized = True
        assert self.orchestrator.is_initialized()


class TestGlobalAgentOrchestrator:
    """Test global agent orchestrator instance"""
    
    @pytest.mark.asyncio
    async def test_get_agent_orchestrator_singleton(self):
        """Test global agent orchestrator singleton"""
        # Reset global instance
        import app.agent.agent_orchestrator
        app.agent.agent_orchestrator._agent_orchestrator = None
        
        with patch.object(AgentOrchestrator, 'initialize', new_callable=AsyncMock):
            # First call should create instance
            orchestrator1 = await get_agent_orchestrator()
            assert orchestrator1 is not None
            
            # Second call should return same instance
            orchestrator2 = await get_agent_orchestrator()
            assert orchestrator1 is orchestrator2
    
    @pytest.mark.asyncio
    async def test_get_agent_orchestrator_initialization_error(self):
        """Test global agent orchestrator initialization error"""
        # Reset global instance
        import app.agent.agent_orchestrator
        app.agent.agent_orchestrator._agent_orchestrator = None
        
        with patch.object(AgentOrchestrator, 'initialize', side_effect=Exception("Init error")):
            with pytest.raises(Exception, match="Init error"):
                await get_agent_orchestrator()