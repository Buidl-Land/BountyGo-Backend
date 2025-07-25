"""
Tests for TagManager service.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.agent.tag_manager import TagManager
from app.agent.exceptions import TaskCreationError
from app.models.tag import Tag as TagModel
from app.models.task import TaskTag


class TestTagManager:
    """Test cases for TagManager service"""
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.execute = AsyncMock()
        session.delete = AsyncMock()
        return session
    
    @pytest.fixture
    def tag_manager(self, mock_session):
        """Create TagManager instance with mock session"""
        return TagManager(mock_session)
    
    @pytest.fixture
    def sample_tags(self):
        """Create sample tag data"""
        return [
            TagModel(id=1, name="python", category="skill", usage_count=10, is_active=True),
            TagModel(id=2, name="web-development", category="skill", usage_count=5, is_active=True),
            TagModel(id=3, name="api", category="skill", usage_count=8, is_active=True)
        ]
    
    @pytest.mark.asyncio
    async def test_get_or_create_tags_new_tags(self, tag_manager, mock_session):
        """Test creating new tags"""
        tag_names = ["python", "javascript", "react"]
        
        # Mock no existing tags
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await tag_manager.get_or_create_tags(tag_names)
        
        # Should create 3 new tags
        assert mock_session.add.call_count == 3
        assert mock_session.flush.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_or_create_tags_existing_tags(self, tag_manager, mock_session, sample_tags):
        """Test getting existing tags"""
        tag_names = ["python", "web-development"]
        
        # Mock existing tags
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            sample_tags[0],  # python exists
            sample_tags[1]   # web-development exists
        ]
        
        result = await tag_manager.get_or_create_tags(tag_names)
        
        # Should not create new tags
        mock_session.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_or_create_tags_mixed(self, tag_manager, mock_session, sample_tags):
        """Test mix of existing and new tags"""
        tag_names = ["python", "new-tag"]
        
        # Mock one existing, one new
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            sample_tags[0],  # python exists
            None             # new-tag doesn't exist
        ]
        
        result = await tag_manager.get_or_create_tags(tag_names)
        
        # Should create only one new tag
        assert mock_session.add.call_count == 1
        assert mock_session.flush.call_count == 1
    
    @pytest.mark.asyncio
    async def test_normalize_tag_names(self, tag_manager):
        """Test tag name normalization"""
        tag_names = ["  Python  ", "python", "PYTHON", "", "Web-Dev", "web-dev"]
        
        normalized = tag_manager._normalize_tag_names(tag_names)
        
        # Should remove duplicates (case-insensitive) and clean whitespace
        assert len(normalized) == 2
        assert "Python" in normalized
        assert "Web-Dev" in normalized
    
    @pytest.mark.asyncio
    async def test_normalize_tag_names_long_names(self, tag_manager):
        """Test tag name truncation"""
        long_name = "x" * 150  # Longer than 100 chars
        tag_names = [long_name]
        
        normalized = tag_manager._normalize_tag_names(tag_names)
        
        # Should truncate to 100 characters
        assert len(normalized) == 1
        assert len(normalized[0]) == 100
    
    @pytest.mark.asyncio
    async def test_associate_tags_with_task_new_associations(self, tag_manager, mock_session, sample_tags):
        """Test associating tags with task (no existing associations)"""
        task_id = 1
        tag_names = ["python", "web-development"]
        
        # Mock tag creation/retrieval
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            sample_tags[0],  # python exists
            sample_tags[1]   # web-development exists
        ]
        
        # Mock no existing associations
        mock_session.execute.return_value.fetchall.return_value = []
        
        result = await tag_manager.associate_tags_with_task(task_id, tag_names)
        
        # Should create 2 associations
        assert mock_session.add.call_count == 2
        
        # Should update usage counts
        assert sample_tags[0].usage_count == 11
        assert sample_tags[1].usage_count == 6
    
    @pytest.mark.asyncio
    async def test_associate_tags_with_task_existing_associations(self, tag_manager, mock_session, sample_tags):
        """Test associating tags when some associations already exist"""
        task_id = 1
        tag_names = ["python", "web-development"]
        
        # Mock tag retrieval
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            sample_tags[0],  # python exists
            sample_tags[1]   # web-development exists
        ]
        
        # Mock existing association for python
        mock_session.execute.return_value.fetchall.return_value = [(1,)]  # tag_id=1 (python)
        
        result = await tag_manager.associate_tags_with_task(task_id, tag_names)
        
        # Should create only 1 new association (for web-development)
        assert mock_session.add.call_count == 1
        
        # Should update only web-development usage count
        assert sample_tags[0].usage_count == 10  # unchanged
        assert sample_tags[1].usage_count == 6   # incremented
    
    @pytest.mark.asyncio
    async def test_remove_tag_associations_specific_tags(self, tag_manager, mock_session, sample_tags):
        """Test removing specific tag associations"""
        task_id = 1
        tag_names = ["python"]
        
        # Mock tag ID lookup
        mock_session.execute.return_value.fetchall.return_value = [(1, "python")]
        
        # Mock existing association
        mock_association = TaskTag(id=1, task_id=1, tag_id=1)
        mock_session.execute.return_value.fetchall.return_value = [mock_association]
        
        # Mock tag retrieval for usage count update
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_tags[0]
        
        await tag_manager.remove_tag_associations(task_id, tag_names)
        
        # Should delete association
        mock_session.delete.assert_called_once()
        
        # Should decrease usage count
        assert sample_tags[0].usage_count == 9
    
    @pytest.mark.asyncio
    async def test_remove_tag_associations_all_tags(self, tag_manager, mock_session, sample_tags):
        """Test removing all tag associations for a task"""
        task_id = 1
        
        # Mock existing associations
        mock_associations = [
            TaskTag(id=1, task_id=1, tag_id=1),
            TaskTag(id=2, task_id=1, tag_id=2)
        ]
        mock_session.execute.return_value.fetchall.return_value = mock_associations
        
        # Mock tag retrieval for usage count updates
        mock_session.execute.return_value.scalar_one_or_none.side_effect = [
            sample_tags[0],  # First tag
            sample_tags[1]   # Second tag
        ]
        
        await tag_manager.remove_tag_associations(task_id)
        
        # Should delete both associations
        assert mock_session.delete.call_count == 2
        
        # Should decrease both usage counts
        assert sample_tags[0].usage_count == 9
        assert sample_tags[1].usage_count == 4
    
    @pytest.mark.asyncio
    async def test_update_task_tags(self, tag_manager, mock_session, sample_tags):
        """Test updating all tags for a task"""
        task_id = 1
        new_tag_names = ["python", "react"]
        
        # Mock the remove and associate operations
        tag_manager.remove_tag_associations = AsyncMock()
        tag_manager.associate_tags_with_task = AsyncMock(return_value=sample_tags[:2])
        
        result = await tag_manager.update_task_tags(task_id, new_tag_names)
        
        # Should remove old associations and create new ones
        tag_manager.remove_tag_associations.assert_called_once_with(task_id)
        tag_manager.associate_tags_with_task.assert_called_once_with(task_id, new_tag_names)
    
    @pytest.mark.asyncio
    async def test_update_task_tags_empty_list(self, tag_manager, mock_session):
        """Test updating task with empty tag list"""
        task_id = 1
        new_tag_names = []
        
        # Mock the remove operation
        tag_manager.remove_tag_associations = AsyncMock()
        
        result = await tag_manager.update_task_tags(task_id, new_tag_names)
        
        # Should remove old associations but not create new ones
        tag_manager.remove_tag_associations.assert_called_once_with(task_id)
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_popular_tags(self, tag_manager, mock_session, sample_tags):
        """Test getting popular tags"""
        # Mock query result
        mock_session.execute.return_value.scalars.return_value.all.return_value = sample_tags
        
        result = await tag_manager.get_popular_tags(limit=10)
        
        # Should return tag information
        assert len(result) == 3
        assert result[0]["name"] == "python"
        assert result[0]["usage_count"] == 10
        assert "id" in result[0]
        assert "category" in result[0]
    
    @pytest.mark.asyncio
    async def test_get_popular_tags_with_category(self, tag_manager, mock_session, sample_tags):
        """Test getting popular tags filtered by category"""
        # Mock query result
        mock_session.execute.return_value.scalars.return_value.all.return_value = sample_tags
        
        result = await tag_manager.get_popular_tags(category="skill", limit=5)
        
        # Should return filtered results
        assert len(result) == 3
        for tag_info in result:
            assert tag_info["category"] == "skill"
    
    @pytest.mark.asyncio
    async def test_search_tags(self, tag_manager, mock_session, sample_tags):
        """Test searching tags by name"""
        query = "web"
        
        # Mock search result
        mock_session.execute.return_value.scalars.return_value.all.return_value = [sample_tags[1]]
        
        result = await tag_manager.search_tags(query)
        
        # Should return matching tags
        assert len(result) == 1
        assert result[0]["name"] == "web-development"
    
    @pytest.mark.asyncio
    async def test_search_tags_with_category(self, tag_manager, mock_session, sample_tags):
        """Test searching tags with category filter"""
        query = "python"
        category = "skill"
        
        # Mock search result
        mock_session.execute.return_value.scalars.return_value.all.return_value = [sample_tags[0]]
        
        result = await tag_manager.search_tags(query, category=category)
        
        # Should return filtered results
        assert len(result) == 1
        assert result[0]["name"] == "python"
        assert result[0]["category"] == "skill"
    
    @pytest.mark.asyncio
    async def test_cleanup_unused_tags(self, tag_manager, mock_session):
        """Test cleaning up unused tags"""
        # Create tags with low usage
        unused_tags = [
            TagModel(id=4, name="unused1", category="skill", usage_count=0, is_active=True),
            TagModel(id=5, name="unused2", category="skill", usage_count=1, is_active=True)
        ]
        
        # Mock query result
        mock_session.execute.return_value.scalars.return_value.all.return_value = unused_tags
        
        result = await tag_manager.cleanup_unused_tags(min_usage_count=1)
        
        # Should mark tags as inactive
        assert result == 2
        assert unused_tags[0].is_active == False
        assert unused_tags[1].is_active == False
    
    @pytest.mark.asyncio
    async def test_get_tag_statistics(self, tag_manager, mock_session):
        """Test getting tag statistics"""
        # Mock total count
        mock_session.execute.return_value.scalar.return_value = 100
        
        # Mock category counts
        mock_session.execute.return_value.fetchall.return_value = [
            ("skill", 80),
            ("industry", 15),
            ("media", 5)
        ]
        
        # Mock usage stats
        mock_session.execute.return_value.first.return_value = (5.5, 50, 0)
        
        result = await tag_manager.get_tag_statistics()
        
        # Should return comprehensive statistics
        assert result["total_tags"] == 100
        assert result["categories"]["skill"] == 80
        assert result["categories"]["industry"] == 15
        assert result["usage_stats"]["average"] == 5.5
        assert result["usage_stats"]["maximum"] == 50
        assert result["usage_stats"]["minimum"] == 0
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, tag_manager, mock_session):
        """Test database error handling"""
        mock_session.execute.side_effect = SQLAlchemyError("Database connection failed")
        
        with pytest.raises(TaskCreationError, match="Tag operation failed"):
            await tag_manager.get_or_create_tags(["python"])
    
    @pytest.mark.asyncio
    async def test_associate_tags_database_error(self, tag_manager, mock_session):
        """Test database error during tag association"""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(TaskCreationError, match="Tag association failed"):
            await tag_manager.associate_tags_with_task(1, ["python"])
    
    @pytest.mark.asyncio
    async def test_remove_associations_database_error(self, tag_manager, mock_session):
        """Test database error during tag removal"""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")
        
        with pytest.raises(TaskCreationError, match="Tag removal failed"):
            await tag_manager.remove_tag_associations(1, ["python"])
    
    @pytest.mark.asyncio
    async def test_empty_tag_names_handling(self, tag_manager):
        """Test handling of empty or invalid tag names"""
        tag_names = ["", "  ", None, "valid-tag"]
        
        # This should not raise an error but filter out invalid names
        normalized = tag_manager._normalize_tag_names([name for name in tag_names if name is not None])
        
        # Should only keep the valid tag
        assert len(normalized) == 1
        assert normalized[0] == "valid-tag"
    
    @pytest.mark.asyncio
    async def test_case_insensitive_deduplication(self, tag_manager):
        """Test case-insensitive tag deduplication"""
        tag_names = ["Python", "python", "PYTHON", "PyThOn"]
        
        normalized = tag_manager._normalize_tag_names(tag_names)
        
        # Should keep only one (the first occurrence)
        assert len(normalized) == 1
        assert normalized[0] == "Python"