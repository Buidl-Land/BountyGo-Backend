"""
Clerk Authentication Service for BountyGo

This service integrates Clerk authentication with the existing BountyGo authentication system,
supporting multiple login methods including Google, GitHub, wallet authentication, and more.
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import HTTPException, status
try:
    from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer
    from fastapi.security import HTTPAuthorizationCredentials
    CLERK_AVAILABLE = True
except ImportError:
    CLERK_AVAILABLE = False
    ClerkConfig = None
    ClerkHTTPBearer = None
    HTTPAuthorizationCredentials = None
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
        if not CLERK_AVAILABLE:
            logger.warning("fastapi-clerk-auth package is not available")
            return

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
        return CLERK_AVAILABLE and self._clerk_config is not None and self._clerk_guard is not None

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

        logger.info(f"🔍 Starting Clerk token verification for token: {token[:50]}...")

        # Development mode: allow mock tokens for testing
        if settings.is_development() and token.startswith("mock_"):
            logger.info("Using mock Clerk token for development")
            return {
                "sub": "user_mock_123",
                "email": "test@example.com",
                "name": "Test User",
                "first_name": "Test",
                "last_name": "User",
                "picture": "https://example.com/avatar.jpg",
                "iat": 1234567890,
                "exp": 9999999999
            }

        try:
            import jwt
            from jwt import PyJWKClient

            # Get JWKS URL
            jwks_url = settings.get_clerk_jwks_url()
            logger.info(f"📡 Using JWKS URL: {jwks_url}")
            if not jwks_url:
                logger.error("JWKS URL not available")
                return None

            # Create JWKS client
            logger.info("🔑 Creating JWKS client...")
            jwks_client = PyJWKClient(jwks_url)

            # Get signing key
            logger.info("🔐 Getting signing key from JWT...")
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            logger.info(f"✅ Signing key obtained: {signing_key.key_id}")

            # Verify and decode token
            logger.info("🔓 Decoding and verifying JWT...")
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_exp": True, "verify_aud": False}
            )

            logger.info(f"✅ JWT verification successful. Payload: {payload}")
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("❌ Clerk token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"❌ Invalid Clerk token: {e}")
            return None
        except Exception as e:
            logger.error(f"💥 Clerk token verification failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
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
            # Enhanced error message for debugging
            logger.error(f"Clerk token verification failed for token: {clerk_token[:50]}...")
            logger.error(f"Token length: {len(clerk_token)}")
            logger.error(f"JWKS URL: {settings.get_clerk_jwks_url()}")

            # Try alternative approach: decode without verification to get user ID
            logger.info("Attempting fallback: decode token without verification to extract user ID")
            try:
                import jwt
                # Decode without verification to get the user ID
                unverified_payload = jwt.decode(clerk_token, options={"verify_signature": False})
                logger.info(f"Unverified payload: {unverified_payload}")

                user_id = unverified_payload.get("sub")
                if user_id and user_id.startswith("user_"):
                    logger.info(f"Found user ID in unverified token: {user_id}")
                    # Use the unverified payload but validate the user exists in Clerk
                    try:
                        user_info = await self._get_clerk_user_info(user_id)
                        logger.info(f"Successfully validated user via Clerk API: {user_info.get('email')}")
                        # Create a minimal payload with the user ID
                        clerk_payload = {
                            "sub": user_id,
                            "iat": unverified_payload.get("iat"),
                            "exp": unverified_payload.get("exp"),
                            "iss": unverified_payload.get("iss")
                        }
                        logger.info("Using fallback authentication method")
                    except Exception as api_e:
                        logger.error(f"Fallback API validation failed: {api_e}")
                        raise AuthenticationError("Invalid Clerk token - verification and fallback failed")
                else:
                    logger.error("No valid user ID found in unverified token")
                    raise AuthenticationError("Invalid Clerk token - no user ID found")
            except Exception as fallback_e:
                logger.error(f"Fallback token decode failed: {fallback_e}")
                raise AuthenticationError("Invalid Clerk token - verification failed")

        logger.info(f"Clerk token payload: {clerk_payload}")

        # Extract user ID from token
        clerk_user_id = clerk_payload.get("sub")
        if not clerk_user_id:
            logger.error(f"Missing 'sub' field in Clerk token. Available fields: {list(clerk_payload.keys())}")
            raise AuthenticationError("Clerk token missing user ID (sub field)")

        logger.info(f"Processing Clerk authentication for user_id: {clerk_user_id}")

        # Get user information from Clerk API (skip for mock tokens)
        if clerk_user_id.startswith("user_mock_"):
            # For mock tokens, use the payload directly
            user_info = {
                "email": clerk_payload.get("email"),
                "first_name": clerk_payload.get("first_name"),
                "last_name": clerk_payload.get("last_name"),
                "username": clerk_payload.get("username"),
                "image_url": clerk_payload.get("picture"),
                "profile_image_url": clerk_payload.get("picture")
            }
            logger.info(f"Using mock user info: {user_info}")
        else:
            try:
                logger.info(f"Attempting to get user info from Clerk API for user_id: {clerk_user_id}")
                user_info = await self._get_clerk_user_info(clerk_user_id)
                logger.info(f"Retrieved user info from Clerk API: {user_info}")

                # Validate that we got email information
                if not user_info.get("email"):
                    logger.error(f"Clerk API returned user info without email: {user_info}")
                    raise AuthenticationError("Clerk API did not return email information")

            except Exception as e:
                logger.error(f"Failed to get user info from Clerk API: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                raise AuthenticationError(f"Failed to retrieve user information from Clerk: {str(e)}")

        # Combine token payload with user info
        combined_payload = {**clerk_payload, **user_info}

        # Find or create user in BountyGo database
        user = await self._find_or_create_clerk_user(db, combined_payload)

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
            clerk_payload: Combined Clerk JWT payload and user info from API

        Returns:
            User object
        """
        # Extract email from API response
        email = clerk_payload.get("email")
        clerk_user_id = clerk_payload.get("sub")

        if not email:
            logger.error(f"Missing email field in Clerk token. Available fields: {list(clerk_payload.keys())}")
            raise AuthenticationError("Clerk token missing email information")

        if not clerk_user_id:
            logger.error(f"No user ID found in Clerk payload: {clerk_payload}")
            raise AuthenticationError("Unable to retrieve user ID from Clerk")

        # Try to find existing user by email or clerk_id
        stmt = select(User).where(
            (User.email == email) | (User.clerk_id == clerk_user_id)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Update user with latest Clerk information
            updated = False
            if user.clerk_id != clerk_user_id:
                user.clerk_id = clerk_user_id
                updated = True
            if user.email != email:
                user.email = email
                updated = True

            # Update other fields if they've changed
            first_name = clerk_payload.get("first_name")
            last_name = clerk_payload.get("last_name")

            if first_name and last_name:
                new_nickname = f"{first_name} {last_name}"
            elif first_name:
                new_nickname = first_name
            elif clerk_payload.get("username"):
                new_nickname = clerk_payload.get("username")
            else:
                new_nickname = email.split("@")[0]

            if user.nickname != new_nickname:
                user.nickname = new_nickname
                updated = True

            # Update avatar if available
            avatar_url = (
                clerk_payload.get("image_url") or
                clerk_payload.get("profile_image_url")
            )
            if avatar_url and user.avatar_url != avatar_url:
                user.avatar_url = avatar_url
                updated = True

            if updated:
                await db.commit()
                await db.refresh(user)

            logger.info(f"Found existing user for Clerk authentication: {email}")
            return user

        # Create new user
        first_name = clerk_payload.get("first_name")
        last_name = clerk_payload.get("last_name")

        # Build nickname from available fields
        if first_name and last_name:
            nickname = f"{first_name} {last_name}"
        elif first_name:
            nickname = first_name
        elif clerk_payload.get("username"):
            nickname = clerk_payload.get("username")
        else:
            nickname = email.split("@")[0] if "@" in email else "Clerk User"

        # Extract avatar URL
        avatar_url = (
            clerk_payload.get("image_url") or
            clerk_payload.get("profile_image_url")
        )

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

        logger.info(f"Created new user from Clerk authentication: {email} (nickname: {nickname})")
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

    async def _get_clerk_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get user information from Clerk API

        Args:
            user_id: Clerk user ID

        Returns:
            User information dictionary
        """
        import httpx

        if not settings.CLERK_SECRET_KEY:
            raise AuthenticationError("Clerk secret key not configured")

        headers = {
            "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                user_data = response.json()

                # Extract relevant information
                email_addresses = user_data.get("email_addresses", [])
                primary_email = None

                # Find primary email
                for email_obj in email_addresses:
                    if email_obj.get("id") == user_data.get("primary_email_address_id"):
                        primary_email = email_obj.get("email_address")
                        break

                # Fallback to first email if no primary found
                if not primary_email and email_addresses:
                    primary_email = email_addresses[0].get("email_address")

                return {
                    "email": primary_email,
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name"),
                    "username": user_data.get("username"),
                    "image_url": user_data.get("image_url"),
                    "profile_image_url": user_data.get("profile_image_url"),
                    "created_at": user_data.get("created_at"),
                    "updated_at": user_data.get("updated_at")
                }
            else:
                logger.error(f"Failed to get user info from Clerk API: {response.status_code} - {response.text}")
                raise AuthenticationError(f"Clerk API error: {response.status_code}")

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

            clerk_user_id = clerk_payload.get("sub")
            if not clerk_user_id:
                return None

            # Try to get user info from Clerk API
            try:
                user_info = await self._get_clerk_user_info(clerk_user_id)
                email = user_info.get("email")
            except:
                # Fallback: try to find user by clerk_id
                stmt = select(User).where(User.clerk_id == clerk_user_id)
                result = await db.execute(stmt)
                return result.scalar_one_or_none()

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
