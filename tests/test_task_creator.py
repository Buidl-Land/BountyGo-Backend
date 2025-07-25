"""
Tests for TaskCreator service.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.agent.task_creator import TaskCreator
from app.agent.models import TaskInfo
from app.agent.exceptions import TaskCreationError
from app.models.task import Task, TaskTag
from app.models.tag import Tag


class TestTaskCreator:
    """Test cases for TaskCreator service"""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.execute = AsyncMock()
        return session
    
    @pytest.fixture
    def task_creator(self, mock_session):
        """Create TaskCreator instance with mock session"""
        return TaskCreator(mock_session)
    
    @pytest.fixture
    def sample_task_info(self):
        """Create sample TaskInfo for testing"""
        return TaskInfo(
            title="Test Task",
            description="This is a test task description",
            reward=Decimal("100.50"),
            reward_currency="USD",
            deadline=datetime.utcnow() + timedelta(days=7),
            tags=["python", "web-development", "api"],
            difficulty_level="intermediate",
            estimated_hours=20
        )
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, task_creator, mock_session, sample_task_info):
        """Test successful task creation"""
        user_id = 1
        source_url = "https://example.com/task"
        
        # Mock task creation
        mock_task = Task(
            id=1,
            title=sample_task_info.title,
            description=sample_task_info.description,
            reward=sample_task_info.reward,
            reward_currency=sample_task_info.reward_currency,
            deadline=sample_task_info.deadline,
            sponsor_id=user_id,
            external_link=source_url,
            status="active"
        )
        
        # Mock tag queries
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await task_creator.create_task(sample_task_info, user_id, source_url)
        
        # Verify session operations
        mock_session.add.assert_called()
        mock_session.flush.assert_called()
        mock_session.commit.assert_called()
        
        # Verify task properties would be set correctly
        assert mock_session.add.call_count >= 1  # Task + potential tags
    
    @pytest.mark.asyncio
    async def test_create_task_with_invalid_title(self, task_creator, sample_task_info):
        """Test task creation with invalid title"""
        sample_task_info.title = ""
        
        with pytest.raises(TaskCreationError, match="Task title is required"):
            await task_creator.create_task(sample_task_info, 1)
    
    @pytest.mark.asyncio
    async def test_create_task_with_long_title(self, task_creator, mock_session, sample_task_info):
        """Test task creation with title that needs truncation"""
        sample_task_info.title = "x" * 300  # Longer than 255 chars
        
        # Mock successful creation
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        await task_creator.create_task(sample_task_info, 1)
        
        # Verify task was created (title would be truncated internally)
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_task_with_negative_reward(self, task_creator, mock_session, sample_task_info):
        """Test task creation with negative reward"""
        sample_task_info.reward = Decimal("-50.00")
        
        # Mock successful creation
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        await task_creator.create_task(sample_task_info, 1)
        
        # Verify task was created (reward would be set to None internally)
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_task_database_error(self, task_creator, mock_session, sample_task_info):
        """Test task creation with database error"""
        mock_session.commit.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(TaskCreationError, match="Database error"):
            await task_creator.create_task(sample_task_info, 1)
        
        # Verify rollback was called
        mock_session.rollback.assert_called()
    
    @pytest.mark.asyncio
    async def test_validate_task_data_success(self, task_creator, sample_task_info):
        """Test successful task data validation"""
        validated = task_creator._validate_task_data(sample_task_info)
        
        assert validated.title == sample_task_info.title
        assert validated.description == sample_task_info.description
        assert validated.reward == sample_task_info.reward
        assert validated.reward_currency == sample_task_info.reward_currency
        assert len(validated.tags) == 3
    
    @pytest.mark.asyncio
    async def test_validate_task_data_empty_title(self, task_creator, sample_task_info):
        """Test validation with empty title"""
        sample_task_info.title = "   "
        
        with pytest.raises(TaskCreationError, match="Task title is required"):
            task_creator._validate_task_data(sample_task_info)
    
    @pytest.mark.asyncio
    async def test_validate_task_data_duplicate_tags(self, task_creator, sample_task_info):
        """Test validation removes duplicate tags"""
        sample_task_info.tags = ["python", "Python", "python", "web-dev"]
        
        validated = task_creator._validate_task_data(sample_task_info)
        
        # Should remove duplicates (case-sensitive)
        assert len(validated.tags) == 3
        assert "python" in validated.tags
        assert "Python" in validated.tags
        assert "web-dev" in validated.tags
    
    @pytest.mark.asyncio
    async def test_associate_tags_new_tags(self, task_creator, mock_session):
        """Test associating new tags with task"""
        mock_task = Task(id=1, title="Test Task", sponsor_id=1)
        tag_names = ["python", "web-dev"]
        
        # Mock no existing tags
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        await task_creator._associate_tags(mock_task, tag_names)
        
        # Should create new tags and associations
        assert mock_session.add.call_count >= 4  # 2 tags + 2 associations
        assert mock_session.flush.call_count >= 2  # For getting tag IDs
    
    @pytest.mark.asyncio
    async def test_associate_tags_existing_tags(self, task_creator, mock_session):
        """Test associating existing tags with task"""
        mock_task = Task(id=1, title="Test Task", sponsor_id=1)
        tag_names = ["python"]
        
        # Mock existing tag
        existing_tag = Tag(id=1, name="python", category="skill", usage_count=5)
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            existing_tag,  # Tag exists
            None  # No existing association
        ]
        
        await task_creator._associate_tags(mock_task, tag_names)
        
        # Should create association and update usage count
        mock_session.add.assert_called()  # For TaskTag association
        assert existing_tag.usage_count == 6
    
    @pytest.mark.asyncio
    async def test_update_task_success(self, task_creator, mock_session, sample_task_info):
        """Test successful task update"""
        task_id = 1
        user_id = 1
        
        # Mock existing task
        existing_task = Task(
            id=task_id,
            title="Old Title",
            description="Old description",
            sponsor_id=user_id,
            status="active"
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_task
        
        result = await task_creator.update_task(task_id, sample_task_info, user_id)
        
        # Verify task was updated
        assert existing_task.title == sample_task_info.title
        assert existing_task.description == sample_task_info.description
        assert existing_task.reward == sample_task_info.reward
        mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_task_not_found(self, task_creator, mock_session, sample_task_info):
        """Test updating non-existent task"""
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(TaskCreationError, match="Task 1 not found or access denied"):
            await task_creator.update_task(1, sample_task_info, 1)
    
    @pytest.mark.asyncio
    async def test_delete_task_success(self, task_creator, mock_session):
        """Test successful task deletion"""
        task_id = 1
        user_id = 1
        
        # Mock existing task
        existing_task = Task(
            id=task_id,
            title="Test Task",
            sponsor_id=user_id,
            status="active"
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_task
        
        result = await task_creator.delete_task(task_id, user_id)
        
        # Verify task was soft deleted
        assert result is True
        assert existing_task.status == "cancelled"
        mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, task_creator, mock_session):
        """Test deleting non-existent task"""
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(TaskCreationError, match="Task 1 not found or access denied"):
            await task_creator.delete_task(1, 1)
    
    @pytest.mark.asyncio
    async def test_create_task_without_tags(self, task_creator, mock_session, sample_task_info):
        """Test creating task without tags"""
        sample_task_info.tags = []
        
        await task_creator.create_task(sample_task_info, 1)
        
        # Should still create task successfully
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_task_with_none_values(self, task_creator, mock_session):
        """Test creating task with minimal required data"""
        minimal_task_info = TaskInfo(
            title="Minimal Task",
            description=None,
            reward=None,
            reward_currency="USD",
            deadline=None,
            tags=[],
            difficulty_level=None,
            estimated_hours=None
        )
        
        await task_creator.create_task(minimal_task_info, 1)
        
        # Should create task successfully with minimal data
        mock_session.add.assert_called()
        mock_session.commit.assert_called()