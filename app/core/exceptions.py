"""
Custom exceptions for BountyGo application
"""
from typing import Any, Dict, Optional


class BountyGoException(Exception):
    """Base exception for BountyGo application"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(BountyGoException):
    """Authentication related errors"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class AuthorizationError(BountyGoException):
    """Authorization related errors"""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class TokenExpiredError(AuthenticationError):
    """Token has expired"""
    
    def __init__(self, message: str = "Token has expired", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class InvalidTokenError(AuthenticationError):
    """Invalid token format or signature"""
    
    def __init__(self, message: str = "Invalid token", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class UserNotFoundError(AuthenticationError):
    """User not found during authentication"""
    
    def __init__(self, message: str = "User not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class InactiveUserError(AuthorizationError):
    """User account is inactive"""
    
    def __init__(self, message: str = "User account is inactive", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class Web3AuthenticationError(AuthenticationError):
    """Web3 wallet authentication errors"""
    
    def __init__(self, message: str = "Web3 authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class GoogleAuthenticationError(AuthenticationError):
    """Google OAuth authentication errors"""
    
    def __init__(self, message: str = "Google authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class RefreshTokenError(AuthenticationError):
    """Refresh token related errors"""
    
    def __init__(self, message: str = "Refresh token error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class ValidationError(BountyGoException):
    """Data validation errors"""
    pass


class NotFoundError(BountyGoException):
    """Resource not found errors"""
    pass


class ExternalServiceError(BountyGoException):
    """External service integration errors"""
    pass


class DatabaseError(BountyGoException):
    """Database operation errors"""
    pass


class CacheError(BountyGoException):
    """Cache operation errors"""
    pass