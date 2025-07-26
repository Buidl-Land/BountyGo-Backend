"""
Task-related database models
"""
from datetime import datetime
from typing import List, Optional
from enum import Enum
from sqlalchemy import String, Text, DECIMAL, Integer, Boolean, ForeignKey, DateTime, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin





class Organizer(Base, TimestampMixin):
    """任务主办方模型"""
    __tablename__ = "organizers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 关联关系
    tasks: Mapped[List["Task"]] = relationship(
        "Task", back_populates="organizer", cascade="all, delete-orphan"
    )


class Task(Base, TimestampMixin):
    """Bounty task model"""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="任务简介")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="任务分类")
    deadline: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="截止日期时间戳")
    sponsor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organizer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizers.id", ondelete="SET NULL"), nullable=True)
    external_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="活动原始链接")
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    join_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    sponsor: Mapped["User"] = relationship("User", back_populates="sponsored_tasks")
    organizer: Mapped[Optional["Organizer"]] = relationship("Organizer", back_populates="tasks")
    task_tags: Mapped[List["TaskTag"]] = relationship(
        "TaskTag", back_populates="task", cascade="all, delete-orphan"
    )
    todos: Mapped[List["Todo"]] = relationship(
        "Todo", back_populates="task", cascade="all, delete-orphan"
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="task", cascade="all, delete-orphan"
    )
    task_views: Mapped[List["TaskView"]] = relationship(
        "TaskView", back_populates="task", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="task", cascade="all, delete-orphan"
    )


class TaskTag(Base, TimestampMixin):
    """Task-tag relationship"""
    __tablename__ = "task_tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="task_tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="task_tags")

    # Constraints
    __table_args__ = (
        UniqueConstraint("task_id", "tag_id", name="uq_task_tag"),
    )


class Todo(Base, TimestampMixin):
    """User todo items - can be linked to tasks or be personal todos"""
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="自定义todo标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="自定义todo描述")
    deadline: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="自定义截止时间戳")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    remind_flags: Mapped[Optional[str]] = mapped_column(
        Text,
        default='{"t_3d": true, "t_1d": true, "ddl_2h": true}',
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否已完成")

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="todos")
    task: Mapped[Optional["Task"]] = relationship("Task", back_populates="todos")

    # Constraints - 移除唯一约束，允许用户创建多个相同任务的todo或私人todo
    __table_args__ = ()


class Message(Base, TimestampMixin):
    """Discussion messages for tasks"""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="messages")
    user: Mapped["User"] = relationship("User", back_populates="messages")


class TaskView(Base, TimestampMixin):
    """Task view analytics tracking"""
    __tablename__ = "task_views"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="NOW()")
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # Support IPv6
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="task_views")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="task_views")