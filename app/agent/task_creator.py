"""
Task creation service for URL agent functionality.
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from app.models.task import Task, TaskTag, Organizer
from app.models.tag import Tag as TagModel
from app.agent.models import TaskInfo
from app.agent.exceptions import TaskCreationError
from app.agent.tag_manager import TagManager

logger = logging.getLogger(__name__)


class TaskCreator:
    """
    Service class for creating tasks from AI-extracted information.

    Handles task creation with database transaction management,
    data validation, and error handling.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize TaskCreator with database session.

        Args:
            db_session: Async database session
        """
        self.db_session = db_session

    async def create_task(self, task_info: TaskInfo, user_id: int, source_url: Optional[str] = None) -> Task:
        """
        Create a new task from AI-extracted information.

        Args:
            task_info: AI-extracted task information
            user_id: ID of the user creating the task
            source_url: Optional source URL for the task

        Returns:
            Task: Created task instance

        Raises:
            TaskCreationError: If task creation fails
        """
        try:
            # Validate task data
            validated_info = self._validate_task_data(task_info)

            # Handle organizer information
            organizer_id = None
            if validated_info.organizer_name:
                organizer_id = await self._get_or_create_organizer(validated_info.organizer_name)

            # Create task instance
            task = Task(
                title=validated_info.title,
                summary=validated_info.summary,
                description=validated_info.description,
                category=validated_info.category,
                reward_details=validated_info.reward_details,
                reward_type=validated_info.reward_type,
                deadline=validated_info.deadline,
                sponsor_id=user_id,
                organizer_id=organizer_id,
                external_link=source_url,
                status="active"
            )

            # Add to session and flush to get ID
            self.db_session.add(task)
            await self.db_session.flush()

            # Process tags if any
            if validated_info.tags:
                await self._associate_tags(task, validated_info.tags)

            # Commit transaction
            await self.db_session.commit()

            logger.info(f"Successfully created task {task.id} for user {user_id}")
            return task

        except SQLAlchemyError as e:
            await self.db_session.rollback()
            logger.error(f"Database error creating task: {str(e)}")
            raise TaskCreationError(f"Database error: {str(e)}")
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Unexpected error creating task: {str(e)}")
            raise TaskCreationError(f"Failed to create task: {str(e)}")

    def _validate_task_data(self, task_info: TaskInfo) -> TaskInfo:
        """
        Validate and clean task data.

        Args:
            task_info: Task information to validate

        Returns:
            TaskInfo: Validated task information

        Raises:
            TaskCreationError: If validation fails
        """
        # Validate title
        if not task_info.title or not task_info.title.strip():
            raise TaskCreationError("Task title is required")

        title = task_info.title.strip()
        if len(title) > 255:
            title = title[:255]
            logger.warning(f"Task title truncated to 255 characters")

        # Note: reward and reward_currency are stored in reward_details field
        # No separate validation needed as they're part of the description

        # Validate description
        description = task_info.description
        if description and len(description) > 65535:  # TEXT field limit
            description = description[:65535]
            logger.warning("Task description truncated to 65535 characters")

        # Validate tags
        tags = []
        if task_info.tags:
            for tag in task_info.tags:
                if tag and tag.strip():
                    clean_tag = tag.strip()[:100]  # Tag name limit
                    if clean_tag not in tags:  # Avoid duplicates
                        tags.append(clean_tag)

        return TaskInfo(
            title=title,
            summary=task_info.summary,
            description=description,
            category=task_info.category,
            reward_details=task_info.reward_details,
            reward_type=task_info.reward_type,
            reward=task_info.reward,
            reward_currency=task_info.reward_currency,
            deadline=task_info.deadline,
            tags=tags,
            difficulty_level=task_info.difficulty_level,
            estimated_hours=task_info.estimated_hours,
            organizer_name=task_info.organizer_name,
            external_link=task_info.external_link
        )

    async def _associate_tags(self, task: Task, tag_names: List[str]) -> None:
        """
        Associate tags with the task, creating new tags if necessary.

        Args:
            task: Task instance to associate tags with
            tag_names: List of tag names to associate

        Raises:
            SQLAlchemyError: If database operations fail
        """
        for tag_name in tag_names:
            try:
                # Check if tag exists
                result = await self.db_session.execute(
                    select(TagModel).where(TagModel.name == tag_name)
                )
                tag = result.scalar_one_or_none()

                if not tag:
                    # Create new tag
                    tag = TagModel(
                        name=tag_name,
                        category="skill",  # Default category for AI-generated tags
                        description=f"Auto-generated tag: {tag_name}",
                        usage_count=0,
                        is_active=True
                    )
                    self.db_session.add(tag)
                    await self.db_session.flush()  # Get tag ID

                # Check if association already exists
                existing_result = await self.db_session.execute(
                    select(TaskTag).where(
                        TaskTag.task_id == task.id,
                        TaskTag.tag_id == tag.id
                    )
                )
                existing_association = existing_result.scalar_one_or_none()

                if not existing_association:
                    # Create task-tag association
                    task_tag = TaskTag(task_id=task.id, tag_id=tag.id)
                    self.db_session.add(task_tag)

                    # Update tag usage count
                    tag.usage_count += 1

                    logger.debug(f"Associated tag '{tag_name}' with task {task.id}")
                else:
                    logger.debug(f"Tag '{tag_name}' already associated with task {task.id}")

            except SQLAlchemyError as e:
                logger.error(f"Error associating tag '{tag_name}': {str(e)}")
                raise

    async def update_task(self, task_id: int, task_info: TaskInfo, user_id: int) -> Task:
        """
        Update an existing task with new information.

        Args:
            task_id: ID of the task to update
            task_info: Updated task information
            user_id: ID of the user updating the task

        Returns:
            Task: Updated task instance

        Raises:
            TaskCreationError: If task update fails
        """
        try:
            # Get existing task
            result = await self.db_session.execute(
                select(Task).where(Task.id == task_id, Task.sponsor_id == user_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                raise TaskCreationError(f"Task {task_id} not found or access denied")

            # Validate new data
            validated_info = self._validate_task_data(task_info)

            # Update task fields
            task.title = validated_info.title
            task.summary = validated_info.summary
            task.description = validated_info.description
            task.category = validated_info.category
            task.reward_details = validated_info.reward_details
            task.reward_type = validated_info.reward_type
            task.deadline = validated_info.deadline
            task.external_link = validated_info.external_link
            task.updated_at = datetime.utcnow()

            # Update tags if provided
            if validated_info.tags is not None:
                # Remove existing tag associations
                await self.db_session.execute(
                    TaskTag.__table__.delete().where(TaskTag.task_id == task_id)
                )

                # Add new tag associations
                if validated_info.tags:
                    await self._associate_tags(task, validated_info.tags)

            await self.db_session.commit()

            logger.info(f"Successfully updated task {task_id}")
            return task

        except SQLAlchemyError as e:
            await self.db_session.rollback()
            logger.error(f"Database error updating task {task_id}: {str(e)}")
            raise TaskCreationError(f"Database error: {str(e)}")
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Unexpected error updating task {task_id}: {str(e)}")
            raise TaskCreationError(f"Failed to update task: {str(e)}")

    async def delete_task(self, task_id: int, user_id: int) -> bool:
        """
        Delete a task (soft delete by setting status to cancelled).

        Args:
            task_id: ID of the task to delete
            user_id: ID of the user deleting the task

        Returns:
            bool: True if task was deleted successfully

        Raises:
            TaskCreationError: If task deletion fails
        """
        try:
            # Get existing task
            result = await self.db_session.execute(
                select(Task).where(Task.id == task_id, Task.sponsor_id == user_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                raise TaskCreationError(f"Task {task_id} not found or access denied")

            # Soft delete by setting status
            task.status = "cancelled"
            task.updated_at = datetime.utcnow()

            await self.db_session.commit()

            logger.info(f"Successfully deleted task {task_id}")
            return True

        except SQLAlchemyError as e:
            await self.db_session.rollback()
            logger.error(f"Database error deleting task {task_id}: {str(e)}")
            raise TaskCreationError(f"Database error: {str(e)}")
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Unexpected error deleting task {task_id}: {str(e)}")
            raise TaskCreationError(f"Failed to delete task: {str(e)}")

    async def _get_or_create_organizer(self, organizer_name: str) -> Optional[int]:
        """
        Get or create organizer by name.

        Args:
            organizer_name: Name of the organizer

        Returns:
            Optional[int]: Organizer ID if created/found, None if failed
        """
        try:
            # Check if organizer exists
            result = await self.db_session.execute(
                select(Organizer).where(Organizer.name == organizer_name)
            )
            organizer = result.scalar_one_or_none()

            if not organizer:
                # Create new organizer
                organizer = Organizer(
                    name=organizer_name,
                    is_verified=False  # Default to unverified
                )
                self.db_session.add(organizer)
                await self.db_session.flush()  # Get organizer ID
                logger.info(f"Created new organizer: {organizer_name}")

            return organizer.id

        except SQLAlchemyError as e:
            logger.error(f"Error handling organizer '{organizer_name}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error handling organizer '{organizer_name}': {str(e)}")
            return None