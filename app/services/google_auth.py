"""
Google OAuth authentication service
"""
import httpx
from typing import Optional, Dict, Any
from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.exceptions import GoogleAuthenticationError, ValidationError
from app.models.user import User
from app.schemas.user import GoogleUserInfo, UserCreate, TokenResponse
from app.services.auth import AuthBaseService, auth_service


class GoogleAuthService(AuthBaseService):
    """Google OAuth authentication service"""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        
    async def verify_google_token(self, token: str) -> GoogleUserInfo:
        """
        验证Google ID token并提取用户信息
        """
        try:
            # 验证Google ID token
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                self.client_id
            )
            
            # 检查token发行者
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise GoogleAuthenticationError('Invalid token issuer')
            
            # 提取用户信息
            google_user_info = GoogleUserInfo(
                google_id=idinfo['sub'],
                email=idinfo['email'],
                nickname=idinfo.get('name', ''),
                avatar_url=idinfo.get('picture'),
                verified_email=idinfo.get('email_verified', False)
            )
            
            return google_user_info
            
        except ValueError as e:
            raise GoogleAuthenticationError(f'Invalid Google token: {str(e)}')
        except Exception as e:
            raise GoogleAuthenticationError(f'Google token verification failed: {str(e)}')
    
    async def get_user_by_google_id(self, db: AsyncSession, google_id: str) -> Optional[User]:
        """
        通过Google ID查找用户
        """
        stmt = select(User).where(
            User.google_id == google_id,
            User.is_active == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """
        通过邮箱查找用户
        """
        stmt = select(User).where(
            User.email == email,
            User.is_active == True
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_user_from_google(
        self, 
        db: AsyncSession, 
        google_user_info: GoogleUserInfo
    ) -> User:
        """
        从Google用户信息创建新用户
        """
        try:
            user_create = UserCreate(
                google_id=google_user_info.google_id,
                email=google_user_info.email,
                nickname=google_user_info.nickname,
                avatar_url=google_user_info.avatar_url
            )
            
            # 创建用户
            user = User(
                google_id=user_create.google_id,
                email=user_create.email,
                nickname=user_create.nickname,
                avatar_url=user_create.avatar_url,
                is_active=True
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            return user
            
        except Exception as e:
            await db.rollback()
            raise GoogleAuthenticationError(f'Failed to create user: {str(e)}')
    
    async def update_user_from_google(
        self, 
        db: AsyncSession, 
        user: User, 
        google_user_info: GoogleUserInfo
    ) -> User:
        """
        从Google信息更新现有用户
        """
        try:
            # 更新用户信息
            if not user.google_id:
                user.google_id = google_user_info.google_id
            
            # 更新昵称和头像（如果Google提供了新信息）
            if google_user_info.nickname and google_user_info.nickname != user.nickname:
                user.nickname = google_user_info.nickname
            
            if google_user_info.avatar_url and google_user_info.avatar_url != user.avatar_url:
                user.avatar_url = google_user_info.avatar_url
            
            await db.commit()
            await db.refresh(user)
            
            return user
            
        except Exception as e:
            await db.rollback()
            raise GoogleAuthenticationError(f'Failed to update user: {str(e)}')
    
    async def authenticate_with_google(
        self, 
        db: AsyncSession, 
        google_token: str
    ) -> TokenResponse:
        """
        使用Google token进行认证
        """
        # 1. 验证Google token并获取用户信息
        token_info = await self.verify_and_get_user_info(google_token)
        
        # 2. 创建GoogleUserInfo对象
        google_user_info = GoogleUserInfo(
            google_id=token_info['sub'],
            email=token_info['email'],
            nickname=token_info.get('name', ''),
            avatar_url=token_info.get('picture'),
            verified_email=token_info.get('email_verified', False)
        )
        
        if not google_user_info.verified_email:
            raise GoogleAuthenticationError('Email not verified by Google')
        
        # 3. 获取或创建用户
        from app.services.user import user_service
        user = await user_service.get_or_create_google_user(db, google_user_info)
        
        # 4. 生成JWT tokens
        token_response = await auth_service.create_token_pair(db, user.id)
        
        return token_response
    
    async def revoke_google_access(self, access_token: str) -> bool:
        """
        撤销Google访问权限
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': access_token},
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                return response.status_code == 200
        except Exception as e:
            # 记录错误但不抛出异常，因为本地token仍然可以被撤销
            print(f"Failed to revoke Google access: {str(e)}")
            return False
    
    async def get_google_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        使用access token获取Google用户信息
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                
                if response.status_code == 200:
                    return response.json()
                return None
                
        except Exception as e:
            print(f"Failed to get Google user info: {str(e)}")
            return None
    
    def validate_google_token_format(self, token: str) -> bool:
        """
        验证Google token格式
        """
        if not token or not isinstance(token, str):
            return False
        
        # Google ID token是JWT格式
        parts = token.split('.')
        if len(parts) != 3:
            return False
        
        # 检查token长度（Google ID token通常很长）
        if len(token) < 100:
            return False
        
        return True
    
    async def refresh_google_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        刷新Google access token
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://oauth2.googleapis.com/token',
                    data={
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'refresh_token': refresh_token,
                        'grant_type': 'refresh_token'
                    },
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                
                if response.status_code == 200:
                    return response.json()
                return None
                
        except Exception as e:
            print(f"Failed to refresh Google token: {str(e)}")
            return None
    
    async def verify_and_get_user_info(self, google_token: str) -> Dict[str, Any]:
        """
        Verify Google token and get user information
        """
        # Validate token format first
        if not self.validate_google_token_format(google_token):
            raise GoogleAuthenticationError("Invalid token format")
        
        try:
            # Verify Google ID token
            idinfo = id_token.verify_oauth2_token(
                google_token, 
                requests.Request(), 
                self.client_id
            )
            
            # Validate token claims
            self._validate_token_claims(idinfo)
            
            # Check if email is verified
            if not idinfo.get('email_verified', False):
                raise GoogleAuthenticationError('Email not verified')
            
            return idinfo
            
        except ValueError as e:
            raise GoogleAuthenticationError(f'Invalid Google token: {str(e)}')
        except Exception as e:
            raise GoogleAuthenticationError(f'Google token verification failed: {str(e)}')
    
    def _validate_client_id(self, client_id: str) -> bool:
        """Validate Google client ID format"""
        if not client_id or not isinstance(client_id, str):
            return False
        
        # Google client IDs end with .apps.googleusercontent.com
        return client_id.endswith('.apps.googleusercontent.com')
    
    def _validate_token_format(self, token: str) -> bool:
        """Validate Google token format (JWT)"""
        if not token or not isinstance(token, str):
            return False
        
        # JWT has 3 parts separated by dots
        parts = token.split('.')
        return len(parts) == 3
    
    def _validate_token_claims(self, token_info: Dict[str, Any]) -> None:
        """Validate Google token claims"""
        # Check issuer
        valid_issuers = ['https://accounts.google.com', 'accounts.google.com']
        if token_info.get('iss') not in valid_issuers:
            raise GoogleAuthenticationError('Invalid issuer')
        
        # Check audience (should match our client ID)
        if token_info.get('aud') != self.client_id:
            raise GoogleAuthenticationError('Invalid audience')
        
        # Check expiration
        exp = token_info.get('exp')
        if exp and int(exp) < datetime.utcnow().timestamp():
            raise GoogleAuthenticationError('Token has expired')
    
    def _verify_with_google_api(self, token: str) -> Dict[str, Any]:
        """Verify token with Google API (alternative method)"""
        try:
            # This would use Google's tokeninfo endpoint
            # For now, we'll use the id_token.verify_oauth2_token method
            return self.verify_and_get_user_info(token)
        except Exception as e:
            raise GoogleAuthenticationError(f'Invalid token: {str(e)}')


# Service instance
google_auth_service = GoogleAuthService()