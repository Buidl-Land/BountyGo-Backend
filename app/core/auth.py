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
# Lazy import to avoid circular dependency


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
            from app.services.auth import auth_service
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
    
    # 开发环境测试token支持
    from app.core.config import settings
    dev_token = settings.get_dev_test_token()
    if dev_token and credentials.credentials == dev_token:
        return await get_dev_test_user(db)
    
    try:
        from app.services.auth import auth_service
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
    from app.core.config import settings
    
    if not credentials:
        dev_info = ""
        if settings.is_dev_test_token_enabled():
            dev_info = f" 开发环境可使用测试token: {settings.get_dev_test_token()}"
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"缺少身份认证令牌。请在请求头中添加 'Authorization: Bearer <token>'。{dev_info}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # 检查token基本格式
    if not token or token.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="访问令牌为空。请提供有效的Bearer token。",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if token in ["null", "undefined", "None"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="访问令牌格式错误。请检查前端是否正确传递token。",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 开发环境测试token支持
    dev_token = settings.get_dev_test_token()
    if dev_token and token == dev_token:
        try:
            return await get_dev_test_user(db)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建开发测试用户失败：{str(e)}"
            )
    
    # JWT token验证
    try:
        from app.services.auth import auth_service
        user = await auth_service.validate_user_session(db, token)
        return user
    except AuthenticationError as e:
        error_msg = str(e).lower()
        
        if "expired" in error_msg or "exp" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="访问令牌已过期。请使用refresh token刷新令牌或重新登录。",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif "invalid" in error_msg or "decode" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="访问令牌格式无效。请检查token是否完整且未被篡改。",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif "user not found" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌对应的用户不存在。该账户可能已被删除，请重新注册。",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif "revoked" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="访问令牌已被撤销。请重新登录获取新的令牌。",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif "inactive" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户账户已被禁用。请联系管理员激活账户。"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"身份认证失败：{str(e)}。请检查令牌有效性或重新登录。",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception as e:
        # 处理其他意外错误
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"认证过程中发生意外错误: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="认证服务暂时不可用，请稍后重试。"
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
        from app.services.auth import auth_service
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
        from app.services.auth import auth_service
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
        from app.services.auth import auth_service
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
        from app.services.auth import auth_service
        return await auth_service.revoke_tokens(db, user_id, refresh_token)
    
    @staticmethod
    async def cleanup_expired_sessions(db: AsyncSession) -> int:
        """Clean up expired sessions"""
        from app.services.auth import auth_service
        return await auth_service.refresh_service.cleanup_expired_tokens(db)


async def get_dev_test_user(db: AsyncSession) -> User:
    """
    获取开发环境测试用户
    如果不存在则创建一个
    """
    from sqlalchemy import select
    from app.models.user import User
    from app.core.config import settings
    
    # 查找测试用户
    result = await db.execute(
        select(User).where(User.email == settings.DEV_TEST_USER_EMAIL)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # 创建测试用户
        user = User(
            email=settings.DEV_TEST_USER_EMAIL,
            nickname=settings.DEV_TEST_USER_NICKNAME,
            google_id="dev_test_user_123",
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"创建开发测试用户: {user.email}")
    
    return user


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
    "security",
    "get_dev_test_user"
]