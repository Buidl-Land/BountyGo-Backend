"""
Authentication service for JWT token management and user session handling
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from jose import JWTError, jwt
import hashlib
import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.models.user import User, RefreshToken
from app.schemas.user import TokenResponse, UserInDB
from app.services.base import BaseService


class AuthBaseService:
    """Base service class for authentication services"""
    pass


class JWTService(AuthBaseService):
    """JWT token management service"""
    
    def create_access_token(
        self, 
        user_id: int, 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        to_encode = {
            "exp": expire,
            "sub": str(user_id),
            "type": "access",
            "iat": datetime.utcnow()
        }
        
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    def create_refresh_token(self, user_id: int) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode = {
            "exp": expire,
            "sub": str(user_id),
            "type": "refresh",
            "iat": datetime.utcnow(),
            "jti": secrets.token_hex(16)  # JWT ID for token tracking
        }
        
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Check token type
            if payload.get("type") != token_type:
                raise AuthenticationError(f"Invalid token type. Expected {token_type}")
            
            # Check expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                raise AuthenticationError("Token has expired")
            
            return payload
            
        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
    
    def extract_user_id(self, token: str) -> int:
        """Extract user ID from token"""
        payload = self.verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Token missing user ID")
        
        try:
            return int(user_id)
        except ValueError:
            raise AuthenticationError("Invalid user ID in token")
    
    def get_token_expiry(self, token: str) -> datetime:
        """Get token expiration time"""
        payload = self.verify_token(token)
        exp = payload.get("exp")
        if not exp:
            raise AuthenticationError("Token missing expiration")
        return datetime.fromtimestamp(exp)


class RefreshTokenService(AuthBaseService):
    """Refresh token management service"""
    
    def _hash_token(self, token: str) -> str:
        """Hash refresh token for storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def store_refresh_token(
        self, 
        db: AsyncSession, 
        user_id: int, 
        token: str
    ) -> RefreshToken:
        """Store refresh token in database"""
        token_hash = self._hash_token(token)
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Create new refresh token record
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        
        db.add(refresh_token)
        await db.commit()
        await db.refresh(refresh_token)
        
        return refresh_token
    
    async def verify_refresh_token(
        self, 
        db: AsyncSession, 
        token: str
    ) -> Optional[RefreshToken]:
        """Verify refresh token exists and is valid"""
        token_hash = self._hash_token(token)
        
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        )
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def revoke_refresh_token(
        self, 
        db: AsyncSession, 
        token: str
    ) -> bool:
        """Revoke a refresh token"""
        token_hash = self._hash_token(token)
        
        stmt = update(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        ).values(is_revoked=True)
        
        result = await db.execute(stmt)
        await db.commit()
        
        return result.rowcount > 0
    
    async def revoke_user_tokens(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> int:
        """Revoke all refresh tokens for a user"""
        stmt = update(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).values(is_revoked=True)
        
        result = await db.execute(stmt)
        await db.commit()
        
        return result.rowcount
    
    async def cleanup_expired_tokens(self, db: AsyncSession) -> int:
        """Clean up expired refresh tokens"""
        from sqlalchemy import delete
        
        stmt = delete(RefreshToken).where(
            RefreshToken.expires_at < datetime.utcnow()
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        return result.rowcount


class AuthenticationService(AuthBaseService):
    """Main authentication service combining JWT and refresh token services"""
    
    def __init__(self):
        self.jwt_service = JWTService()
        self.refresh_service = RefreshTokenService()
    
    async def create_token_pair(
        self, 
        db: AsyncSession, 
        user_id: int
    ) -> TokenResponse:
        """Create access and refresh token pair"""
        # Create tokens
        access_token = self.jwt_service.create_access_token(user_id)
        refresh_token = self.jwt_service.create_refresh_token(user_id)
        
        # Store refresh token
        await self.refresh_service.store_refresh_token(db, user_id, refresh_token)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def refresh_access_token(
        self, 
        db: AsyncSession, 
        refresh_token: str
    ) -> TokenResponse:
        """Refresh access token using refresh token"""
        # Verify refresh token format
        try:
            payload = self.jwt_service.verify_token(refresh_token, "refresh")
            user_id = int(payload.get("sub"))
        except (AuthenticationError, ValueError):
            raise AuthenticationError("Invalid refresh token")
        
        # Verify refresh token in database
        stored_token = await self.refresh_service.verify_refresh_token(db, refresh_token)
        if not stored_token:
            raise AuthenticationError("Refresh token not found or expired")
        
        # Verify user still exists and is active
        user = await self.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        
        # Create new token pair
        return await self.create_token_pair(db, user_id)
    
    async def revoke_tokens(
        self, 
        db: AsyncSession, 
        user_id: int, 
        refresh_token: Optional[str] = None
    ) -> bool:
        """Revoke tokens for logout"""
        if refresh_token:
            # Revoke specific refresh token
            return await self.refresh_service.revoke_refresh_token(db, refresh_token)
        else:
            # Revoke all user tokens
            count = await self.refresh_service.revoke_user_tokens(db, user_id)
            return count > 0
    
    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def validate_user_session(
        self, 
        db: AsyncSession, 
        access_token: str
    ) -> User:
        """Validate user session from access token"""
        try:
            # Verify token
            payload = self.jwt_service.verify_token(access_token, "access")
            user_id = int(payload.get("sub"))
            
            # Get user
            user = await self.get_user_by_id(db, user_id)
            if not user:
                raise AuthenticationError("User not found")
            
            return user
            
        except (ValueError, AuthenticationError):
            raise AuthenticationError("Invalid session")


# Service instances
jwt_service = JWTService()
refresh_token_service = RefreshTokenService()
auth_service = AuthenticationService()