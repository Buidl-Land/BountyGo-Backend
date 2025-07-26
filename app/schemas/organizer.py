"""
Organizer-related Pydantic schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class OrganizerBase(BaseModel):
    """Base organizer schema"""
    name: str = Field(..., min_length=1, max_length=255, description="主办方名称")


class OrganizerCreate(OrganizerBase):
    """Schema for creating an organizer"""
    pass


class OrganizerUpdate(BaseModel):
    """Schema for updating an organizer"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_verified: Optional[bool] = None


class Organizer(OrganizerBase):
    """Schema for organizer response"""
    id: int
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizerSummary(BaseModel):
    """Summary organizer schema for lists"""
    id: int
    name: str
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)
