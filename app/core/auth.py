"""
Authentication middleware and dependencies for FastAPI
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.models.user import User
from app.services.auth import auth_service


# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


class AuthenticationMiddleware:
    """Authentication middleware for request processing"""
    
    @staticmethod
    def extract_token_from_header(authorization: str) -> Optional[str]:
        """Extract token from Authorization header"""
        if not authorization:
            return None
        
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]
    
    @staticmethod
    async def authenticate_request(
        request: Request,
        db: AsyncSession
    ) -> Optional[User]:
        """Authenticate request and return user if valid"""
        authorization = request.headers.get("Authorization")
        if not authorization:
            return None
        
        token = AuthenticationMiddleware.extract_token_from_header(authorization)
        if not token:
            return None
        
        try:
            user = await auth_service.validate_user_session(db, token)
            return user
        except AuthenticationError:
            return None


# Dependency functions for FastAPI

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from token (optional - returns None if not authenticated)
    """
    if not credentials:
        return None
    
    try:
        user = await auth_service.validate_user_session(db, credentials.credentials)
        return user
    except AuthenticationError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current user from token (required - raises exception if not authenticated)
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = await auth_service.validate_user_session(db, credentials.credentials)
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (raises exception if user is inactive)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def require_roles(*roles: str):
    """
    Decorator factory for role-based access control
    Note: Role system not implemented yet, reserved for future use
    """
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        # TODO: Implement role checking when role system is added
        # For now, just return the user
        return current_user
    
    return role_checker


def require_permissions(*permissions: str):
    """
    Decorator factory for permission-based access control
    Note: Permission system not implemented yet, reserved for future use
    """
    def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        # TODO: Implement permission checking when permission system is added
        # For now, just return the user
        return current_user
    
    return permission_checker


class AuthenticationDecorators:
    """Authentication decorators for different access levels"""
    
    @staticmethod
    def authenticated(func):
        """Decorator to require authentication"""
        async def wrapper(*args, **kwargs):
            # This is handled by FastAPI dependencies
            return await func(*args, **kwargs)
        return wrapper
    
    @staticmethod
    def optional_auth(func):
        """Decorator for optional authentication"""
        async def wrapper(*args, **kwargs):
            # This is handled by FastAPI dependencies
            return await func(*args, **kwargs)
        return wrapper


# Utility functions for manual authentication

async def authenticate_user_by_token(
    token: str,
    db: AsyncSession
) -> User:
    """
    Manually authenticate user by token
    Useful for WebSocket connections or custom authentication flows
    """
    try:
        user = await auth_service.validate_user_session(db, token)
        return user
    except AuthenticationError as e:
        raise AuthorizationError(f"Authentication failed: {str(e)}")


async def extract_user_from_request(
    request: Request,
    db: AsyncSession
) -> Optional[User]:
    """
    Extract user from request headers
    Useful for middleware or custom authentication flows
    """
    return await AuthenticationMiddleware.authenticate_request(request, db)


def create_auth_header(token: str) -> dict:
    """Create Authorization header dict"""
    return {"Authorization": f"Bearer {token}"}


def validate_token_format(token: str) -> bool:
    """Validate token format without verifying signature"""
    if not token:
        return False
    
    # Basic JWT format check (3 parts separated by dots)
    parts = token.split('.')
    return len(parts) == 3


# Session management utilities

class SessionManager:
    """Session management utilities"""
    
    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: int
    ) -> dict:
        """Create new user session"""
        token_response = await auth_service.create_token_pair(db, user_id)
        return {
            "access_token": token_response.access_token,
            "refresh_token": token_response.refresh_token,
            "expires_in": token_response.expires_in,
            "token_type": token_response.token_type
        }
    
    @staticmethod
    async def refresh_session(
        db: AsyncSession,
        refresh_token: str
    ) -> dict:
        """Refresh user session"""
        token_response = await auth_service.refresh_access_token(db, refresh_token)
        return {
            "access_token": token_response.access_token,
            "refresh_token": token_response.refresh_token,
            "expires_in": token_response.expires_in,
            "token_type": token_response.token_type
        }
    
    @staticmethod
    async def revoke_session(
        db: AsyncSession,
        user_id: int,
        refresh_token: Optional[str] = None
    ) -> bool:
        """Revoke user session"""
        return await auth_service.revoke_tokens(db, user_id, refresh_token)
    
    @staticmethod
    async def cleanup_expired_sessions(db: AsyncSession) -> int:
        """Clean up expired sessions"""
        return await auth_service.refresh_service.cleanup_expired_tokens(db)


# Export commonly used dependencies
__all__ = [
    "get_current_user",
    "get_current_user_optional", 
    "get_current_active_user",
    "require_roles",
    "require_permissions",
    "authenticate_user_by_token",
    "extract_user_from_request",
    "SessionManager",
    "AuthenticationMiddleware",
    "security"
]