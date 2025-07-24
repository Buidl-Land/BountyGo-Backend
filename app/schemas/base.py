"""
Base schema classes and utilities
"""
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields"""
    created_at: datetime
    updated_at: datetime


class PaginationParams(BaseSchema):
    """Pagination parameters"""
    page: int = 1
    size: int = 20
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        return self.size


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper"""
    items: list[Any]
    total: int
    page: int
    size: int
    pages: int
    
    @classmethod
    def create(
        cls,
        items: list[Any],
        total: int,
        pagination: PaginationParams
    ) -> "PaginatedResponse":
        """Create paginated response"""
        pages = (total + pagination.size - 1) // pagination.size
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            size=pagination.size,
            pages=pages
        )


class ErrorResponse(BaseSchema):
    """Error response schema"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    path: str


class SuccessResponse(BaseSchema):
    """Success response schema"""
    success: bool = True
    message: str
    data: Optional[Any] = None