"""
Core application components
"""
from .auth import (
    get_current_user,
    get_current_user_optional,
    get_current_active_user,
    require_roles,
    require_permissions,
    SessionManager,
    AuthenticationMiddleware,
    security
)
from .exceptions import (
    BountyGoException,
    AuthenticationError,
    AuthorizationError,
    TokenExpiredError,
    InvalidTokenError,
    UserNotFoundError,
    InactiveUserError,
    Web3AuthenticationError,
    GoogleAuthenticationError,
    RefreshTokenError
)

__all__ = [
    # Authentication
    "get_current_user",
    "get_current_user_optional", 
    "get_current_active_user",
    "require_roles",
    "require_permissions",
    "SessionManager",
    "AuthenticationMiddleware",
    "security",
    # Exceptions
    "BountyGoException",
    "AuthenticationError",
    "AuthorizationError", 
    "TokenExpiredError",
    "InvalidTokenError",
    "UserNotFoundError",
    "InactiveUserError",
    "Web3AuthenticationError",
    "GoogleAuthenticationError",
    "RefreshTokenError"
]