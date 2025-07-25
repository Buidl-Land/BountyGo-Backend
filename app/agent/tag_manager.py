"""
Tag management service for URL agent functionality.
"""
import logging
from typing import List, Optional, Dict, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, func, and_

from app.models.tag import Tag as TagModel
from app.models.task import TaskTag
from app.agent.exceptions import TaskCreationError

logger = logging.getLogger(__name__)


class TagManager:
    """
    Service class for managing tags and tag associations.
    
    Handles tag creation, deduplication, usage count updates,
    and tag association management.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize TagManager with database session.
        
        Args:
            db_session: Async database session
        """
        self.db_session = db_session
    
    async def get_or_create_tags(self, tag_names: List[str], category: str = "skill") -> List[TagModel]:
        """
        Get existing tags or create new ones for the given tag names.
        
        Args:
            tag_names: List of tag names to get or create
            category: Category for new tags (default: "skill")
            
        Returns:
            List[TagModel]: List of tag instances
            
        Raises:
            TaskCreationError: If tag operations fail
        """
        try:
            tags = []
            normalized_names = self._normalize_tag_names(tag_names)
            
            for tag_name in normalized_names:
                # Check if tag exists
                result = await self.db_session.execute(
                    select(TagModel).where(TagModel.name == tag_name)
                )
                tag = result.scalar_one_or_none()
                
                if not tag:
                    # Create new tag
                    tag = TagModel(
                        name=tag_name,
                        category=category,
                        description=f"Auto-generated tag: {tag_name}",
                        usage_count=0,
                        is_active=True
                    )
                    self.db_session.add(tag)
                    await self.db_session.flush()  # Get tag ID
                    logger.info(f"Created new tag: {tag_name}")
                
                tags.append(tag)
            
            return tags
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_or_create_tags: {str(e)}")
            raise TaskCreationError(f"Tag operation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in get_or_create_tags: {str(e)}")
            raise TaskCreationError(f"Tag operation failed: {str(e)}")
    
    async def associate_tags_with_task(self, task_id: int, tag_names: List[str]) -> List[TagModel]:
        """
        Associate tags with a task, creating tags if necessary and avoiding duplicates.
        
        Args:
            task_id: ID of the task to associate tags with
            tag_names: List of tag names to associate
            
        Returns:
            List[TagModel]: List of associated tags
            
        Raises:
            TaskCreationError: If tag association fails
        """
        try:
            # Get or create tags
            tags = await self.get_or_create_tags(tag_names)
            
            # Get existing associations to avoid duplicates
            existing_result = await self.db_session.execute(
                select(TaskTag.tag_id).where(TaskTag.task_id == task_id)
            )
            existing_tag_ids = {row[0] for row in existing_result.fetchall()}
            
            # Create new associations and update usage counts
            associated_tags = []
            for tag in tags:
                if tag.id not in existing_tag_ids:
                    # Create new association
                    task_tag = TaskTag(task_id=task_id, tag_id=tag.id)
                    self.db_session.add(task_tag)
                    
                    # Update usage count
                    tag.usage_count += 1
                    
                    logger.debug(f"Associated tag '{tag.name}' with task {task_id}")
                else:
                    logger.debug(f"Tag '{tag.name}' already associated with task {task_id}")
                
                associated_tags.append(tag)
            
            return associated_tags
            
        except SQLAlchemyError as e:
            logger.error(f"Database error associating tags with task {task_id}: {str(e)}")
            raise TaskCreationError(f"Tag association failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error associating tags with task {task_id}: {str(e)}")
            raise TaskCreationError(f"Tag association failed: {str(e)}")
    
    async def remove_tag_associations(self, task_id: int, tag_names: Optional[List[str]] = None) -> None:
        """
        Remove tag associations from a task and update usage counts.
        
        Args:
            task_id: ID of the task to remove associations from
            tag_names: Optional list of specific tag names to remove. If None, removes all.
            
        Raises:
            TaskCreationError: If tag removal fails
        """
        try:
            if tag_names:
                # Remove specific tags
                normalized_names = self._normalize_tag_names(tag_names)
                
                # Get tag IDs for the specified names
                tag_result = await self.db_session.execute(
                    select(TagModel.id, TagModel.name).where(TagModel.name.in_(normalized_names))
                )
                tag_mapping = {name: tag_id for tag_id, name in tag_result.fetchall()}
                
                # Get existing associations to remove
                associations_result = await self.db_session.execute(
                    select(TaskTag).where(
                        and_(
                            TaskTag.task_id == task_id,
                            TaskTag.tag_id.in_(tag_mapping.values())
                        )
                    )
                )
                associations = associations_result.fetchall()
                
                # Remove associations and update usage counts
                for association in associations:
                    await self.db_session.delete(association)
                    
                    # Update usage count
                    tag_result = await self.db_session.execute(
                        select(TagModel).where(TagModel.id == association.tag_id)
                    )
                    tag = tag_result.scalar_one_or_none()
                    if tag and tag.usage_count > 0:
                        tag.usage_count -= 1
                        logger.debug(f"Decreased usage count for tag '{tag.name}'")
            else:
                # Remove all associations for the task
                associations_result = await self.db_session.execute(
                    select(TaskTag).where(TaskTag.task_id == task_id)
                )
                associations = associations_result.fetchall()
                
                for association in associations:
                    await self.db_session.delete(association)
                    
                    # Update usage count
                    tag_result = await self.db_session.execute(
                        select(TagModel).where(TagModel.id == association.tag_id)
                    )
                    tag = tag_result.scalar_one_or_none()
                    if tag and tag.usage_count > 0:
                        tag.usage_count -= 1
                        logger.debug(f"Decreased usage count for tag '{tag.name}'")
            
        except SQLAlchemyError as e:
            logger.error(f"Database error removing tag associations for task {task_id}: {str(e)}")
            raise TaskCreationError(f"Tag removal failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error removing tag associations for task {task_id}: {str(e)}")
            raise TaskCreationError(f"Tag removal failed: {str(e)}")
    
    async def update_task_tags(self, task_id: int, new_tag_names: List[str]) -> List[TagModel]:
        """
        Update all tags for a task by removing old associations and creating new ones.
        
        Args:
            task_id: ID of the task to update tags for
            new_tag_names: List of new tag names
            
        Returns:
            List[TagModel]: List of newly associated tags
            
        Raises:
            TaskCreationError: If tag update fails
        """
        try:
            # Remove all existing associations
            await self.remove_tag_associations(task_id)
            
            # Add new associations
            if new_tag_names:
                return await self.associate_tags_with_task(task_id, new_tag_names)
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error updating tags for task {task_id}: {str(e)}")
            raise TaskCreationError(f"Tag update failed: {str(e)}")
    
    async def get_popular_tags(self, category: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Get popular tags ordered by usage count.
        
        Args:
            category: Optional category filter
            limit: Maximum number of tags to return
            
        Returns:
            List[Dict]: List of tag information with usage counts
        """
        try:
            query = select(TagModel).where(TagModel.is_active == True)
            
            if category:
                query = query.where(TagModel.category == category)
            
            query = query.order_by(TagModel.usage_count.desc()).limit(limit)
            
            result = await self.db_session.execute(query)
            tags = result.scalars().all()
            
            return [
                {
                    "id": tag.id,
                    "name": tag.name,
                    "category": tag.category,
                    "usage_count": tag.usage_count,
                    "description": tag.description
                }
                for tag in tags
            ]
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting popular tags: {str(e)}")
            raise TaskCreationError(f"Failed to get popular tags: {str(e)}")
    
    async def search_tags(self, query: str, category: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """
        Search for tags by name.
        
        Args:
            query: Search query string
            category: Optional category filter
            limit: Maximum number of results
            
        Returns:
            List[Dict]: List of matching tag information
        """
        try:
            search_query = select(TagModel).where(
                and_(
                    TagModel.is_active == True,
                    TagModel.name.ilike(f"%{query}%")
                )
            )
            
            if category:
                search_query = search_query.where(TagModel.category == category)
            
            search_query = search_query.order_by(
                TagModel.usage_count.desc(),
                TagModel.name
            ).limit(limit)
            
            result = await self.db_session.execute(search_query)
            tags = result.scalars().all()
            
            return [
                {
                    "id": tag.id,
                    "name": tag.name,
                    "category": tag.category,
                    "usage_count": tag.usage_count,
                    "description": tag.description
                }
                for tag in tags
            ]
            
        except SQLAlchemyError as e:
            logger.error(f"Database error searching tags: {str(e)}")
            raise TaskCreationError(f"Tag search failed: {str(e)}")
    
    async def cleanup_unused_tags(self, min_usage_count: int = 0) -> int:
        """
        Clean up tags with usage count below threshold.
        
        Args:
            min_usage_count: Minimum usage count to keep tags
            
        Returns:
            int: Number of tags cleaned up
        """
        try:
            # Find tags to clean up
            result = await self.db_session.execute(
                select(TagModel).where(
                    and_(
                        TagModel.usage_count <= min_usage_count,
                        TagModel.is_active == True
                    )
                )
            )
            tags_to_cleanup = result.scalars().all()
            
            # Mark as inactive instead of deleting
            count = 0
            for tag in tags_to_cleanup:
                tag.is_active = False
                count += 1
                logger.info(f"Marked tag '{tag.name}' as inactive (usage: {tag.usage_count})")
            
            return count
            
        except SQLAlchemyError as e:
            logger.error(f"Database error cleaning up tags: {str(e)}")
            raise TaskCreationError(f"Tag cleanup failed: {str(e)}")
    
    def _normalize_tag_names(self, tag_names: List[str]) -> List[str]:
        """
        Normalize tag names by cleaning and deduplicating.
        
        Args:
            tag_names: List of raw tag names
            
        Returns:
            List[str]: List of normalized, unique tag names
        """
        normalized = []
        seen = set()
        
        for tag_name in tag_names:
            if not tag_name:
                continue
                
            # Clean the tag name
            clean_name = tag_name.strip()[:100]  # Tag name limit
            
            if clean_name and clean_name.lower() not in seen:
                normalized.append(clean_name)
                seen.add(clean_name.lower())
        
        return normalized
    
    async def get_tag_statistics(self) -> Dict:
        """
        Get tag usage statistics.
        
        Returns:
            Dict: Statistics about tag usage
        """
        try:
            # Total tags
            total_result = await self.db_session.execute(
                select(func.count(TagModel.id)).where(TagModel.is_active == True)
            )
            total_tags = total_result.scalar()
            
            # Tags by category
            category_result = await self.db_session.execute(
                select(TagModel.category, func.count(TagModel.id))
                .where(TagModel.is_active == True)
                .group_by(TagModel.category)
            )
            categories = {category: count for category, count in category_result.fetchall()}
            
            # Usage statistics
            usage_result = await self.db_session.execute(
                select(
                    func.avg(TagModel.usage_count),
                    func.max(TagModel.usage_count),
                    func.min(TagModel.usage_count)
                ).where(TagModel.is_active == True)
            )
            avg_usage, max_usage, min_usage = usage_result.first()
            
            return {
                "total_tags": total_tags,
                "categories": categories,
                "usage_stats": {
                    "average": float(avg_usage) if avg_usage else 0,
                    "maximum": max_usage or 0,
                    "minimum": min_usage or 0
                }
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting tag statistics: {str(e)}")
            raise TaskCreationError(f"Failed to get tag statistics: {str(e)}")