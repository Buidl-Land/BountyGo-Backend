"""
Tag-related Pydantic schemas
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class TagCategory(str, Enum):
    """Tag categories"""
    INDUSTRY = "industry"
    SKILL = "skill"
    MEDIA = "media"


class TagBase(BaseModel):
    """Base tag schema"""
    name: str = Field(..., min_length=1, max_length=100)
    category: TagCategory
    description: Optional[str] = None


class TagCreate(TagBase):
    """Schema for creating a tag"""
    pass


class TagUpdate(BaseModel):
    """Schema for updating a tag"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[TagCategory] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class Tag(TagBase):
    """Schema for tag response"""
    id: int
    usage_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserTagProfileBase(BaseModel):
    """Base user tag profile schema"""
    weight: float = Field(default=1.0, ge=0.0, le=10.0)


class UserTagProfileCreate(UserTagProfileBase):
    """Schema for creating user tag profile"""
    user_id: int
    tag_id: int


class UserTagProfileUpdate(BaseModel):
    """Schema for updating user tag profile"""
    weight: Optional[float] = Field(None, ge=0.0, le=10.0)


class UserTagProfile(UserTagProfileBase):
    """Schema for user tag profile response"""
    id: int
    user_id: int
    tag_id: int
    last_updated: datetime
    tag: Tag
    
    model_config = ConfigDict(from_attributes=True)


class UserTagVector(BaseModel):
    """User tag vector for recommendations"""
    user_id: int
    tags: List[Dict[str, Any]]  # [{"tag": Tag, "weight": float}]
    last_updated: datetime


class TagSuggestion(BaseModel):
    """Tag suggestion response"""
    tag: Tag
    similarity_score: float
    reason: Optional[str] = None


class TagSearchRequest(BaseModel):
    """Tag search request"""
    query: str = Field(..., min_length=1)
    category: Optional[TagCategory] = None
    limit: int = Field(default=20, ge=1, le=100)


class TagSearchResponse(BaseModel):
    """Tag search response"""
    tags: List[Tag]
    total: int
    query: str
    category: Optional[TagCategory] = None


class TagAnalytics(BaseModel):
    """Tag analytics response"""
    total_tags: int
    tags_by_category: Dict[str, int]
    most_used_tags: List[Dict[str, Any]]
    recent_tags: List[Tag]


class BulkTagCreate(BaseModel):
    """Schema for bulk tag creation"""
    tags: List[TagCreate] = Field(..., min_items=1, max_items=100)


class BulkTagResponse(BaseModel):
    """Response for bulk tag operations"""
    created: List[Tag]
    skipped: List[str]  # Tag names that were skipped
    errors: List[str]   # Error messages