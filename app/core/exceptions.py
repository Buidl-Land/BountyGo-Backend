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
    pass


class AuthorizationError(BountyGoException):
    """Authorization related errors"""
    pass


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