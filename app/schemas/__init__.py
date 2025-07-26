"""
Pydantic schemas package
"""
from .base import (
    BaseSchema,
    TimestampSchema,
    PaginationParams,
    PaginatedResponse,
    ErrorResponse,
    SuccessResponse
)
from .user import (
    User, UserCreate, UserUpdate, UserProfile, UserInDB,
    UserWallet, UserWalletCreate,
    RefreshToken, RefreshTokenCreate,
    TokenResponse, GoogleAuthRequest, WalletAuthRequest, GoogleUserInfo
)
from .tag import (
    Tag, TagCreate, TagUpdate, TagCategory,
    UserTagProfile, UserTagProfileCreate, UserTagProfileUpdate,
    UserTagVector, TagSuggestion, TagSearchRequest, TagSearchResponse,
    TagAnalytics, BulkTagCreate, BulkTagResponse
)
from .task import (
    Task, TaskCreate, TaskUpdate, TaskSummary, TaskStatus,
    TaskFilters, TaskList, Pagination,
    Todo, TodoCreate, TodoUpdate,
    Message, MessageCreate, MessageUpdate, MessageList,
    TaskAnalytics, SponsorDashboard, TaskView, ExportData
)

__all__ = [
    # Base
    "BaseSchema", "TimestampSchema", "PaginationParams", "PaginatedResponse",
    "ErrorResponse", "SuccessResponse",
    # User
    "User", "UserCreate", "UserUpdate", "UserProfile", "UserInDB",
    "UserWallet", "UserWalletCreate",
    "RefreshToken", "RefreshTokenCreate",
    "TokenResponse", "GoogleAuthRequest", "WalletAuthRequest", "GoogleUserInfo",
    # Tag
    "Tag", "TagCreate", "TagUpdate", "TagCategory",
    "UserTagProfile", "UserTagProfileCreate", "UserTagProfileUpdate",
    "UserTagVector", "TagSuggestion", "TagSearchRequest", "TagSearchResponse",
    "TagAnalytics", "BulkTagCreate", "BulkTagResponse",
    # Task
    "Task", "TaskCreate", "TaskUpdate", "TaskSummary", "TaskStatus",
    "TaskFilters", "TaskList", "Pagination",
    "Todo", "TodoCreate", "TodoUpdate",
    "Message", "MessageCreate", "MessageUpdate", "MessageList",
    "TaskAnalytics", "SponsorDashboard", "TaskView", "ExportData",
    # Organizer
    "Organizer", "OrganizerCreate", "OrganizerUpdate", "OrganizerSummary"
]