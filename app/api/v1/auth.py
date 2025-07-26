"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_user_optional, SessionManager
from app.schemas.user import TokenResponse, User, GoogleAuthRequest, WalletAuthRequest, ClerkAuthRequest, ClerkLinkRequest
from app.models.user import User as UserModel

router = APIRouter()


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        refresh_token = request.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="refresh_token is required"
            )

        token_response = await SessionManager.refresh_session(db, refresh_token)
        return TokenResponse(**token_response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    request: dict,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user by revoking refresh token
    """
    try:
        refresh_token = request.get("refresh_token")
        success = await SessionManager.revoke_session(
            db,
            current_user.id,
            refresh_token
        )
        if success:
            return {"message": "Successfully logged out"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to logout"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/logout-all")
async def logout_all(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user from all devices by revoking all refresh tokens
    """
    try:
        success = await SessionManager.revoke_session(db, current_user.id)
        if success:
            return {"message": "Successfully logged out from all devices"}
        else:
            return {"message": "No active sessions found"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get current authenticated user information
    """
    return current_user


@router.get("/status")
async def get_auth_status(
    current_user: UserModel = Depends(get_current_user_optional)
):
    """
    Get authentication status and available authentication methods

    Returns information about:
    - Current authentication status
    - Available authentication providers
    - User's linked authentication methods
    """
    try:
        from app.services.clerk_auth import clerk_auth_service

        # Get available authentication methods
        auth_methods = {
            "google_oauth": True,  # Always available
            "web3_wallet": True,   # Always available
            "clerk": clerk_auth_service.is_enabled
        }

        if current_user:
            # User is authenticated
            linked_methods = []

            if current_user.google_id:
                if current_user.google_id.startswith("clerk_"):
                    linked_methods.append("clerk")
                else:
                    linked_methods.append("google_oauth")

            if current_user.clerk_id:
                linked_methods.append("clerk")

            # Check for linked wallets
            if hasattr(current_user, 'wallets') and current_user.wallets:
                linked_methods.append("web3_wallet")

            return {
                "authenticated": True,
                "user": {
                    "id": current_user.id,
                    "email": current_user.email,
                    "nickname": current_user.nickname,
                    "avatar_url": current_user.avatar_url
                },
                "linked_methods": list(set(linked_methods)),
                "available_methods": auth_methods,
                "clerk_providers": clerk_auth_service.get_supported_providers() if clerk_auth_service.is_enabled else []
            }
        else:
            # User is not authenticated
            return {
                "authenticated": False,
                "user": None,
                "linked_methods": [],
                "available_methods": auth_methods,
                "clerk_providers": clerk_auth_service.get_supported_providers() if clerk_auth_service.is_enabled else []
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get authentication status: {str(e)}"
        )


@router.get("/profile", response_model=User)
async def get_user_profile(
    current_user: UserModel = Depends(get_current_user_optional)
):
    """
    Get user profile (optional authentication)
    Returns user info if authenticated, otherwise returns public info
    """
    if current_user:
        return current_user
    else:
        # Return some public information or empty response
        return {"message": "Not authenticated"}


@router.get("/protected")
async def protected_endpoint(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Example protected endpoint that requires authentication
    """
    return {
        "message": f"Hello {current_user.nickname}!",
        "user_id": current_user.id,
        "email": current_user.email
    }


@router.get("/public")
async def public_endpoint():
    """
    Example public endpoint that doesn't require authentication
    """
    return {"message": "This is a public endpoint"}


@router.get("/optional-auth")
async def optional_auth_endpoint(
    current_user: UserModel = Depends(get_current_user_optional)
):
    """
    Example endpoint with optional authentication
    """
    if current_user:
        return {
            "message": f"Hello authenticated user {current_user.nickname}!",
            "authenticated": True,
            "user_id": current_user.id
        }
    else:
        return {
            "message": "Hello anonymous user!",
            "authenticated": False
        }


@router.post("/google", response_model=TokenResponse)
async def google_login(
    request: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Google OAuth login endpoint
    """
    try:
        from app.services.google_auth import google_auth_service

        token_response = await google_auth_service.authenticate_with_google(
            db,
            request.google_token
        )

        return token_response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


# Clerk Authentication Endpoints

@router.post("/clerk", response_model=TokenResponse)
async def clerk_login(
    request: ClerkAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Clerk authentication endpoint

    Supports multiple authentication methods through Clerk:
    - Google OAuth
    - GitHub OAuth
    - Microsoft OAuth
    - Apple Sign In
    - Facebook Login
    - Twitter OAuth
    - LinkedIn OAuth
    - Discord OAuth
    - Twitch OAuth
    - Web3 Wallet Authentication
    - Email/Password
    - SMS/Phone Authentication
    """
    try:
        from app.services.clerk_auth import clerk_auth_service

        if not clerk_auth_service.is_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Clerk authentication is not configured"
            )

        token_response = await clerk_auth_service.authenticate_with_clerk(
            db,
            request.clerk_token
        )

        return token_response

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Clerk authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/clerk/debug")
async def debug_clerk_token(
    request: ClerkAuthRequest
):
    """
    Debug endpoint to analyze Clerk token structure
    """
    try:
        from app.services.clerk_auth import clerk_auth_service

        if not clerk_auth_service.is_enabled:
            return {
                "error": "Clerk authentication is not configured",
                "clerk_enabled": False
            }

        # Basic token info
        token = request.clerk_token
        debug_info = {
            "token_length": len(token),
            "token_prefix": token[:50] if len(token) > 50 else token,
            "token_suffix": token[-20:] if len(token) > 20 else "",
            "is_mock_token": token.startswith("mock_"),
            "clerk_enabled": True
        }

        # Try to verify and decode the token
        try:
            payload = await clerk_auth_service.verify_clerk_token(token)

            if payload:
                debug_info.update({
                    "verification_success": True,
                    "payload": payload,
                    "available_fields": list(payload.keys()),
                    "user_info": {
                        "sub": payload.get("sub"),
                        "email": payload.get("email"),
                        "email_address": payload.get("email_address"),
                        "primary_email_address": payload.get("primary_email_address"),
                        "email_addresses": payload.get("email_addresses"),
                        "username": payload.get("username"),
                        "name": payload.get("name"),
                        "first_name": payload.get("first_name"),
                        "last_name": payload.get("last_name"),
                        "picture": payload.get("picture"),
                        "image_url": payload.get("image_url")
                    }
                })

                # If we have a user ID, try to get user info from Clerk API
                user_id = payload.get("sub")
                if user_id and not user_id.startswith("user_mock_"):
                    try:
                        user_info = await clerk_auth_service._get_clerk_user_info(user_id)
                        debug_info["api_user_info"] = user_info
                        debug_info["api_call_success"] = True
                    except Exception as api_e:
                        debug_info["api_call_success"] = False
                        debug_info["api_error"] = str(api_e)

            else:
                debug_info.update({
                    "verification_success": False,
                    "error": "Token verification returned None"
                })

        except Exception as verify_e:
            debug_info.update({
                "verification_success": False,
                "verification_error": str(verify_e)
            })

        return debug_info

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "clerk_enabled": clerk_auth_service.is_enabled if 'clerk_auth_service' in locals() else False
        }


@router.post("/clerk/link")
async def link_clerk_account(
    request: ClerkLinkRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Link Clerk account to existing BountyGo user

    This allows users who already have a BountyGo account to link their
    Clerk authentication methods (Google, GitHub, wallet, etc.) to their
    existing account.
    """
    try:
        from app.services.clerk_auth import clerk_auth_service

        if not clerk_auth_service.is_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Clerk authentication is not configured"
            )

        user_id = request.user_id or current_user.id

        # Verify user has permission to link to this account
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot link Clerk account to another user"
            )

        success = await clerk_auth_service.link_clerk_to_existing_user(
            db,
            user_id,
            request.clerk_token
        )

        if success:
            return {"message": "Clerk account linked successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to link Clerk account"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link Clerk account: {str(e)}"
        )


@router.get("/clerk/providers")
async def get_clerk_providers():
    """
    Get list of authentication providers supported by Clerk

    Returns the available authentication methods that users can use
    to sign in through Clerk.
    """
    try:
        from app.services.clerk_auth import clerk_auth_service

        if not clerk_auth_service.is_enabled:
            return {
                "enabled": False,
                "providers": [],
                "message": "Clerk authentication is not configured"
            }

        providers = clerk_auth_service.get_supported_providers()

        return {
            "enabled": True,
            "providers": providers,
            "message": f"Clerk authentication supports {len(providers)} providers"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Clerk providers: {str(e)}"
        )


@router.post("/google/revoke")
async def google_revoke(
    google_access_token: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke Google OAuth access
    """
    try:
        from app.services.google_auth import google_auth_service

        # 撤销Google访问权限
        success = await google_auth_service.revoke_google_access(google_access_token)

        # 撤销本地refresh tokens
        await SessionManager.revoke_session(db, current_user.id)

        return {
            "message": "Google access revoked successfully",
            "google_revoked": success
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke Google access: {str(e)}"
        )


# Web3 Wallet Authentication Endpoints

@router.post("/wallet/nonce")
async def get_wallet_nonce(wallet_address: str):
    """
    Generate authentication nonce for wallet address

    This endpoint generates a unique nonce that must be signed by the wallet
    to prove ownership. The nonce expires after 5 minutes.
    """
    try:
        from app.services.web3_auth import web3_auth_service

        # Generate nonce
        nonce = web3_auth_service.generate_auth_nonce(wallet_address)

        # Get authentication message
        message = web3_auth_service.get_auth_message(wallet_address, nonce)

        return {
            "nonce": nonce,
            "message": message,
            "wallet_address": wallet_address,
            "expires_in": 300  # 5 minutes
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/wallet/verify", response_model=TokenResponse)
async def wallet_login(
    auth_request: WalletAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user with wallet signature

    Verifies the wallet signature and returns JWT tokens if the wallet
    is linked to a user account.
    """
    try:
        from app.services.web3_auth import web3_auth_service

        token_response = await web3_auth_service.authenticate_wallet(
            db,
            auth_request
        )

        return token_response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/wallet/link")
async def link_wallet(
    auth_request: WalletAuthRequest,
    is_primary: bool = False,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Link wallet to current user account

    Verifies the wallet signature and links the wallet to the authenticated user.
    """
    try:
        from app.services.web3_auth import web3_auth_service

        wallet = await web3_auth_service.link_wallet_to_user(
            db,
            current_user.id,
            auth_request,
            is_primary
        )

        return {
            "message": "Wallet linked successfully",
            "wallet": {
                "id": wallet.id,
                "wallet_address": wallet.wallet_address,
                "wallet_type": wallet.wallet_type,
                "is_primary": wallet.is_primary,
                "created_at": wallet.created_at
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/wallet/{wallet_id}")
async def unlink_wallet(
    wallet_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Unlink wallet from current user account
    """
    try:
        from app.services.web3_auth import web3_auth_service

        success = await web3_auth_service.unlink_wallet_from_user(
            db,
            current_user.id,
            wallet_id
        )

        if success:
            return {"message": "Wallet unlinked successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found or not owned by user"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unlink wallet: {str(e)}"
        )