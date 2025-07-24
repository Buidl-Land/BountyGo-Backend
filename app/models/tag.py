"""
Tag-related database models
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, DECIMAL, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class Tag(Base, TimestampMixin):
    """System tags for categorization"""
    __tablename__ = "tags"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # 'industry', 'skill', 'media'
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    user_profiles: Mapped[List["UserTagProfile"]] = relationship(
        "UserTagProfile", back_populates="tag", cascade="all, delete-orphan"
    )
    task_tags: Mapped[List["TaskTag"]] = relationship(
        "TaskTag", back_populates="tag", cascade="all, delete-orphan"
    )


class UserTagProfile(Base):
    """User tag profiles with weights"""
    __tablename__ = "user_tag_profiles"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    weight: Mapped[float] = mapped_column(DECIMAL(5, 4), default=1.0, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(nullable=False, server_default="NOW()")
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tag_profiles")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="user_profiles")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "tag_id", name="uq_user_tag"),
    )