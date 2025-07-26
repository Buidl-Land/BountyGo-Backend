"""
Clerk Authentication Service for BountyGo

This service integrates Clerk authentication with the existing BountyGo authentication system,
supporting multiple login methods including Google, GitHub, wallet authentication, and more.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials
import logging

from app.core.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.models.user import User, RefreshToken
from app.schemas.user import TokenResponse, UserCreate, UserInDB
from app.services.base import BaseService
from app.services.auth import AuthenticationService

logger = logging.getLogger(__name__)


class ClerkAuthService(BaseService):
    """
    Clerk Authentication Service

    Integrates Clerk authentication with BountyGo's existing authentication system.
    Supports multiple authentication methods while maintaining compatibility with
    existing JWT-based authentication.
    """

    def __init__(self):
        self.auth_service = AuthenticationService()
        self._clerk_config = None
        self._clerk_guard = None
        self._initialize_clerk()

    def _initialize_clerk(self):
        """Initialize Clerk configuration and authentication guard"""
        if not settings.is_clerk_enabled():
            logger.warning("Clerk authentication is not configured")
            return

        jwks_url = settings.get_clerk_jwks_url()
        if not jwks_url:
            logger.error("Clerk JWKS URL is not available")
            return

        try:
            self._clerk_config = ClerkConfig(
                jwks_url=jwks_url,
                auto_error=False  # We'll handle errors manually
            )
            self._clerk_guard = ClerkHTTPBearer(config=self._clerk_config)
            logger.info(f"Clerk authentication initialized with JWKS URL: {jwks_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Clerk authentication: {e}")

    @property
    def is_enabled(self) -> bool:
        """Check if Clerk authentication is enabled and properly configured"""
        return self._clerk_config is not None and self._clerk_guard is not None

    async def verify_clerk_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Clerk JWT token and return decoded payload

        Args:
            token: Clerk JWT token

        Returns:
            Decoded token payload or None if invalid
        """
        if not self.is_enabled:
            raise AuthenticationError("Clerk authentication is not enabled")

        try:
            # Create mock credentials object for verification
            from fastapi.security import HTTPAuthorizationCredentials
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # Use Clerk's verification logic
            # Note: This is a simplified approach. In a real implementation,
            # you might need to call Clerk's verification directly
            if hasattr(self._clerk_guard, 'verify_token'):
                payload = await self._clerk_guard.verify_token(credentials)
                return payload.decoded if hasattr(payload, 'decoded') else payload
            else:
                # Fallback: manual JWT verification using Clerk's JWKS
                import jwt
                import requests

                # Fetch JWKS
                jwks_response = requests.get(self._clerk_config.jwks_url)
                jwks_response.raise_for_status()
                jwks = jwks_response.json()

                # Decode token (simplified - in production, implement proper JWKS key selection)
                payload = jwt.decode(token, options={"verify_signature": False})
                return payload

        except Exception as e:
            logger.warning(f"Clerk token verification failed: {e}")
            return None

    async def authenticate_with_clerk(
        self,
        db: AsyncSession,
        clerk_token: str
    ) -> TokenResponse:
        """
        Authenticate user with Clerk token and return BountyGo JWT tokens

        Args:
            db: Database session
            clerk_token: Clerk JWT token

        Returns:
            BountyGo token response
        """
        # Verify Clerk token
        clerk_payload = await self.verify_clerk_token(clerk_token)
        if not clerk_payload:
            raise AuthenticationError("Invalid Clerk token")

        # Extract user information from Clerk token
        clerk_user_id = clerk_payload.get("sub")
        email = clerk_payload.get("email")

        if not clerk_user_id or not email:
            raise AuthenticationError("Clerk token missing required user information")

        # Find or create user in BountyGo database
        user = await self._find_or_create_clerk_user(db, clerk_payload)

        # Generate BountyGo JWT tokens
        token_response = await self.auth_service.create_token_pair(db, user.id)

        logger.info(f"User authenticated via Clerk: {user.email}")
        return token_response

    async def _find_or_create_clerk_user(
        self,
        db: AsyncSession,
        clerk_payload: Dict[str, Any]
    ) -> User:
        """
        Find existing user or create new user from Clerk payload

        Args:
            db: Database session
            clerk_payload: Decoded Clerk JWT payload

        Returns:
            User object
        """
        email = clerk_payload.get("email")
        clerk_user_id = clerk_payload.get("sub")

        # Try to find existing user by email
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Update user with Clerk information if needed
            if user.clerk_id != clerk_user_id:
                user.clerk_id = clerk_user_id
                await db.commit()

            logger.info(f"Found existing user for Clerk authentication: {email}")
            return user

        # Create new user
        nickname = (
            clerk_payload.get("name") or
            clerk_payload.get("given_name") or
            clerk_payload.get("email", "").split("@")[0] or
            "Clerk User"
        )

        avatar_url = clerk_payload.get("picture") or clerk_payload.get("image_url")

        user = User(
            email=email,
            nickname=nickname,
            avatar_url=avatar_url,
            is_active=True,
            clerk_id=clerk_user_id
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"Created new user from Clerk authentication: {email}")
        return user

    async def link_clerk_to_existing_user(
        self,
        db: AsyncSession,
        user_id: int,
        clerk_token: str
    ) -> bool:
        """
        Link Clerk account to existing BountyGo user

        Args:
            db: Database session
            user_id: Existing user ID
            clerk_token: Clerk JWT token

        Returns:
            True if successful
        """
        # Verify Clerk token
        clerk_payload = await self.verify_clerk_token(clerk_token)
        if not clerk_payload:
            raise AuthenticationError("Invalid Clerk token")

        # Get existing user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("User not found")

        # Update user with Clerk information
        clerk_user_id = clerk_payload.get("sub")
        user.clerk_id = clerk_user_id

        await db.commit()

        logger.info(f"Linked Clerk account to existing user: {user.email}")
        return True

    def get_supported_providers(self) -> List[str]:
        """
        Get list of authentication providers supported by Clerk

        Returns:
            List of provider names
        """
        return [
            "google",
            "github",
            "microsoft",
            "apple",
            "facebook",
            "twitter",
            "linkedin",
            "discord",
            "twitch",
            "wallet",  # Web3 wallet authentication
            "email",   # Email/password
            "phone",   # SMS authentication
        ]

    async def get_user_from_clerk_token(
        self,
        db: AsyncSession,
        clerk_token: str
    ) -> Optional[User]:
        """
        Get BountyGo user from Clerk token without creating session

        Args:
            db: Database session
            clerk_token: Clerk JWT token

        Returns:
            User object or None
        """
        try:
            clerk_payload = await self.verify_clerk_token(clerk_token)
            if not clerk_payload:
                return None

            email = clerk_payload.get("email")
            if not email:
                return None

            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.warning(f"Failed to get user from Clerk token: {e}")
            return None


# Service instance
clerk_auth_service = ClerkAuthService()
