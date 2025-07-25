"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_current_user_optional, SessionManager
from app.schemas.user import TokenResponse, User, GoogleAuthRequest
from app.models.user import User as UserModel

router = APIRouter()


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        token_response = await SessionManager.refresh_session(db, refresh_token)
        return TokenResponse(**token_response)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    refresh_token: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user by revoking refresh token
    """
    try:
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