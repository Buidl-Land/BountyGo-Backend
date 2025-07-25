"""
Google OAuth authentication tests
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from datetime import datetime, timedelta

from app.main import app
from app.services.auth import auth_service
from app.models.user import User
from app.schemas.user import GoogleUserInfo, TokenResponse
from app.core.exceptions import GoogleAuthenticationError


class TestGoogleOAuthService:
    """Test Google OAuth service functionality"""
    
    @pytest.fixture
    def mock_google_user_info(self):
        """Mock Google user information"""
        return {
            "sub": "google_user_123",
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
            "locale": "en"
        }
    
    @pytest.fixture
    def mock_google_token_info(self):
        """Mock Google token information"""
        return {
            "iss": "https://accounts.google.com",
            "azp": "test-client-id.apps.googleusercontent.com",
            "aud": "test-client-id.apps.googleusercontent.com",
            "sub": "google_user_123",
            "email": "test@example.com",
            "email_verified": True,
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "given_name": "Test",
            "family_name": "User",
            "iat": int(datetime.utcnow().timestamp()),
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
    
    @patch('app.services.google_auth.GoogleAuthService.verify_google_token')
    @patch('app.services.google_auth.GoogleAuthService.get_google_user_info')
    async def test_google_token_verification_success(
        self, 
        mock_get_user_info, 
        mock_verify_token,
        mock_google_token_info,
        mock_google_user_info
    ):
        """Test successful Google token verification"""
        from app.services.google_auth import google_auth_service
        
        # Setup mocks
        mock_verify_token.return_value = mock_google_token_info
        mock_get_user_info.return_value = mock_google_user_info
        
        # Test token verification
        google_token = "valid.google.token"
        user_info = await google_auth_service.verify_and_get_user_info(google_token)
        
        assert user_info["sub"] == "google_user_123"
        assert user_info["email"] == "test@example.com"
        assert user_info["email_verified"] is True
        mock_verify_token.assert_called_once_with(google_token)
        mock_get_user_info.assert_called_once_with(google_token)
    
    @patch('app.services.google_auth.GoogleAuthService.verify_google_token')
    async def test_google_token_verification_invalid_token(self, mock_verify_token):
        """Test Google token verification with invalid token"""
        from app.services.google_auth import google_auth_service
        
        # Setup mock to raise exception
        mock_verify_token.side_effect = GoogleAuthenticationError("Invalid token")
        
        # Test invalid token
        with pytest.raises(GoogleAuthenticationError):
            await google_auth_service.verify_and_get_user_info("invalid.token")
    
    @patch('app.services.google_auth.GoogleAuthService.verify_google_token')
    async def test_google_token_verification_expired_token(self, mock_verify_token):
        """Test Google token verification with expired token"""
        from app.services.google_auth import google_auth_service
        
        # Setup mock with expired token
        expired_token_info = {
            "sub": "google_user_123",
            "email": "test@example.com",
            "exp": int((datetime.utcnow() - timedelta(hours=1)).timestamp())  # Expired
        }
        mock_verify_token.return_value = expired_token_info
        
        # Test expired token
        with pytest.raises(GoogleAuthenticationError, match="Token has expired"):
            await google_auth_service.verify_and_get_user_info("expired.token")
    
    @patch('app.services.google_auth.GoogleAuthService.verify_google_token')
    async def test_google_token_verification_unverified_email(self, mock_verify_token):
        """Test Google token verification with unverified email"""
        from app.services.google_auth import google_auth_service
        
        # Setup mock with unverified email
        unverified_token_info = {
            "sub": "google_user_123",
            "email": "test@example.com",
            "email_verified": False,
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        mock_verify_token.return_value = unverified_token_info
        
        # Test unverified email
        with pytest.raises(GoogleAuthenticationError, match="Email not verified"):
            await google_auth_service.verify_and_get_user_info("unverified.token")


class TestGoogleOAuthEndpoints:
    """Test Google OAuth API endpoints"""
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user"""
        return User(
            id=1,
            google_id="google_user_123",
            email="test@example.com",
            nickname="Test User",
            avatar_url="https://example.com/avatar.jpg",
            is_active=True
        )
    
    @pytest.mark.asyncio
    async def test_google_auth_endpoint_success(self, mock_user):
        """Test successful Google authentication endpoint"""
        with patch('app.services.google_auth.google_auth_service.verify_and_get_user_info') as mock_verify:
            with patch('app.services.user.user_service.get_or_create_google_user') as mock_get_create:
                with patch('app.services.auth.auth_service.create_token_pair') as mock_create_tokens:
                    
                    # Setup mocks
                    mock_verify.return_value = {
                        "sub": "google_user_123",
                        "email": "test@example.com",
                        "name": "Test User",
                        "picture": "https://example.com/avatar.jpg",
                        "email_verified": True
                    }
                    mock_get_create.return_value = mock_user
                    mock_create_tokens.return_value = TokenResponse(
                        access_token="access_token_123",
                        refresh_token="refresh_token_123",
                        token_type="bearer",
                        expires_in=900
                    )
                    
                    # Test the endpoint
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        response = await client.post(
                            "/api/v1/auth/google",
                            json={"google_token": "valid.google.token"}
                        )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["access_token"] == "access_token_123"
                    assert data["refresh_token"] == "refresh_token_123"
                    assert data["token_type"] == "bearer"
                    assert data["expires_in"] == 900
    
    @pytest.mark.asyncio
    async def test_google_auth_endpoint_invalid_token(self):
        """Test Google authentication endpoint with invalid token"""
        with patch('app.services.google_auth.google_auth_service.verify_and_get_user_info') as mock_verify:
            
            # Setup mock to raise exception
            mock_verify.side_effect = GoogleAuthenticationError("Invalid Google token")
            
            # Test the endpoint
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/google",
                    json={"google_token": "invalid.token"}
                )
            
            assert response.status_code == 401
            assert "Invalid Google token" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_google_auth_endpoint_missing_token(self):
        """Test Google authentication endpoint with missing token"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/google",
                json={}
            )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_google_auth_endpoint_empty_token(self):
        """Test Google authentication endpoint with empty token"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/google",
                json={"google_token": ""}
            )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_google_auth_endpoint_user_creation_failure(self):
        """Test Google authentication when user creation fails"""
        with patch('app.services.google_auth.google_auth_service.verify_and_get_user_info') as mock_verify:
            with patch('app.services.user.user_service.get_or_create_google_user') as mock_get_create:
                
                # Setup mocks
                mock_verify.return_value = {
                    "sub": "google_user_123",
                    "email": "test@example.com",
                    "name": "Test User",
                    "picture": "https://example.com/avatar.jpg",
                    "email_verified": True
                }
                mock_get_create.side_effect = Exception("Database error")
                
                # Test the endpoint
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.post(
                        "/api/v1/auth/google",
                        json={"google_token": "valid.google.token"}
                    )
                
                assert response.status_code == 500


class TestGoogleOAuthUserManagement:
    """Test Google OAuth user management"""
    
    @pytest.mark.asyncio
    async def test_get_or_create_google_user_new_user(self):
        """Test creating new user from Google OAuth"""
        from app.services.user import user_service
        
        db_mock = AsyncMock()
        google_user_info = GoogleUserInfo(
            google_id="google_user_123",
            email="newuser@example.com",
            nickname="New User",
            avatar_url="https://example.com/avatar.jpg",
            verified_email=True
        )
        
        # Mock database operations
        db_mock.execute.return_value.scalar_one_or_none.return_value = None  # User doesn't exist
        
        with patch.object(user_service, 'create') as mock_create:
            mock_create.return_value = User(
                id=1,
                google_id="google_user_123",
                email="newuser@example.com",
                nickname="New User",
                avatar_url="https://example.com/avatar.jpg",
                is_active=True
            )
            
            user = await user_service.get_or_create_google_user(db_mock, google_user_info)
            
            assert user.google_id == "google_user_123"
            assert user.email == "newuser@example.com"
            assert user.nickname == "New User"
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_or_create_google_user_existing_user(self):
        """Test getting existing user from Google OAuth"""
        from app.services.user import user_service
        
        db_mock = AsyncMock()
        google_user_info = GoogleUserInfo(
            google_id="google_user_123",
            email="existing@example.com",
            nickname="Existing User",
            avatar_url="https://example.com/avatar.jpg",
            verified_email=True
        )
        
        existing_user = User(
            id=1,
            google_id="google_user_123",
            email="existing@example.com",
            nickname="Existing User",
            avatar_url="https://example.com/avatar.jpg",
            is_active=True
        )
        
        # Mock database operations
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        db_mock.execute.return_value = mock_result
        
        user = await user_service.get_or_create_google_user(db_mock, google_user_info)
        
        assert user.id == 1
        assert user.google_id == "google_user_123"
        assert user.email == "existing@example.com"
    
    @pytest.mark.asyncio
    async def test_get_or_create_google_user_inactive_user(self):
        """Test reactivating inactive user from Google OAuth"""
        from app.services.user import user_service
        
        db_mock = AsyncMock()
        google_user_info = GoogleUserInfo(
            google_id="google_user_123",
            email="inactive@example.com",
            nickname="Inactive User",
            avatar_url="https://example.com/avatar.jpg",
            verified_email=True
        )
        
        inactive_user = User(
            id=1,
            google_id="google_user_123",
            email="inactive@example.com",
            nickname="Inactive User",
            avatar_url="https://example.com/avatar.jpg",
            is_active=False  # Inactive user
        )
        
        # Mock database operations
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = inactive_user
        db_mock.execute.return_value = mock_result
        
        with patch.object(user_service, 'update') as mock_update:
            mock_update.return_value = User(
                id=1,
                google_id="google_user_123",
                email="inactive@example.com",
                nickname="Inactive User",
                avatar_url="https://example.com/avatar.jpg",
                is_active=True  # Reactivated
            )
            
            user = await user_service.get_or_create_google_user(db_mock, google_user_info)
            
            assert user.is_active is True
            mock_update.assert_called_once()


class TestGoogleOAuthSecurity:
    """Test Google OAuth security features"""
    
    def test_google_client_id_validation(self):
        """Test Google client ID validation"""
        from app.services.google_auth import GoogleAuthService
        
        service = GoogleAuthService()
        
        # Valid client IDs
        valid_ids = [
            "123456789-abcdefghijklmnop.apps.googleusercontent.com",
            "987654321-zyxwvutsrqponmlk.apps.googleusercontent.com"
        ]
        
        for client_id in valid_ids:
            assert service._validate_client_id(client_id) is True
        
        # Invalid client IDs
        invalid_ids = [
            "invalid-client-id",
            "123456789-invalid",
            "",
            None,
            "123456789-abcdefghijklmnop.invalid.com"
        ]
        
        for client_id in invalid_ids:
            assert service._validate_client_id(client_id) is False
    
    def test_google_token_format_validation(self):
        """Test Google token format validation"""
        from app.services.google_auth import GoogleAuthService
        
        service = GoogleAuthService()
        
        # Valid JWT format (3 parts separated by dots, long enough for Google tokens)
        valid_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE2NzAyNzk4YWJjZGVmZ2hpams" + "." + "eyJpc3MiOiJhY2NvdW50cy5nb29nbGUuY29tIiwiYXVkIjoiMTIzNDU2Nzg5LWFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHl6LmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwic3ViIjoiZ29vZ2xlX3VzZXJfMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsIm5hbWUiOiJUZXN0IFVzZXIiLCJwaWN0dXJlIjoiaHR0cHM6Ly9leGFtcGxlLmNvbS9hdmF0YXIuanBnIiwiZXhwIjoxNjcwMjc5ODAwfQ" + "." + "signature_part_that_makes_this_token_long_enough_to_pass_validation_checks_and_meet_google_requirements"
        assert service._validate_token_format(valid_token) is True
        
        # Invalid formats
        invalid_tokens = [
            "invalid.token",  # Only 2 parts
            "invalid.token.format.extra",  # 4 parts
            "invalidtoken",  # No dots
            "",  # Empty
            None  # None
        ]
        
        for token in invalid_tokens:
            assert service._validate_token_format(token) is False
    
    @patch('app.services.google_auth.requests.get')
    def test_google_token_verification_with_google_api(self, mock_get):
        """Test Google token verification using Google API"""
        from app.services.google_auth import GoogleAuthService
        
        service = GoogleAuthService()
        
        # Mock successful Google API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "iss": "https://accounts.google.com",
            "aud": "test-client-id.apps.googleusercontent.com",
            "sub": "google_user_123",
            "email": "test@example.com",
            "email_verified": "true",
            "exp": str(int((datetime.utcnow() + timedelta(hours=1)).timestamp()))
        }
        mock_get.return_value = mock_response
        
        # Test token verification
        token_info = service._verify_with_google_api("valid.google.token")
        
        assert token_info["sub"] == "google_user_123"
        assert token_info["email"] == "test@example.com"
        assert token_info["email_verified"] is True
    
    @patch('app.services.google_auth.requests.get')
    def test_google_token_verification_api_error(self, mock_get):
        """Test Google token verification API error handling"""
        from app.services.google_auth import GoogleAuthService
        
        service = GoogleAuthService()
        
        # Mock Google API error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_token",
            "error_description": "Invalid token"
        }
        mock_get.return_value = mock_response
        
        # Test token verification error
        with pytest.raises(GoogleAuthenticationError, match="Invalid token"):
            service._verify_with_google_api("invalid.token")
    
    def test_audience_validation(self):
        """Test Google token audience validation"""
        from app.services.google_auth import GoogleAuthService
        from app.core.config import settings
        
        service = GoogleAuthService()
        
        # Valid audience (matches client ID)
        valid_token_info = {
            "aud": settings.GOOGLE_CLIENT_ID,
            "iss": "https://accounts.google.com",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        
        # Should not raise exception
        service._validate_token_claims(valid_token_info)
        
        # Invalid audience
        invalid_token_info = {
            "aud": "wrong-client-id.apps.googleusercontent.com",
            "iss": "https://accounts.google.com",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        
        with pytest.raises(GoogleAuthenticationError, match="Invalid audience"):
            service._validate_token_claims(invalid_token_info)
    
    def test_issuer_validation(self):
        """Test Google token issuer validation"""
        from app.services.google_auth import GoogleAuthService
        from app.core.config import settings
        
        service = GoogleAuthService()
        
        # Valid issuers
        valid_issuers = [
            "https://accounts.google.com",
            "accounts.google.com"
        ]
        
        for issuer in valid_issuers:
            token_info = {
                "aud": settings.GOOGLE_CLIENT_ID,
                "iss": issuer,
                "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
            }
            # Should not raise exception
            service._validate_token_claims(token_info)
        
        # Invalid issuer
        invalid_token_info = {
            "aud": settings.GOOGLE_CLIENT_ID,
            "iss": "https://malicious.com",
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }
        
        with pytest.raises(GoogleAuthenticationError, match="Invalid issuer"):
            service._validate_token_claims(invalid_token_info)


class TestGoogleOAuthIntegration:
    """Integration tests for Google OAuth flow"""
    
    @pytest.mark.asyncio
    async def test_complete_google_oauth_flow(self):
        """Test complete Google OAuth authentication flow"""
        # This test simulates the complete flow from frontend to backend
        
        # Step 1: Frontend receives Google token
        google_token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE2NzAyNzk4.eyJpc3MiOiJhY2NvdW50cy5nb29nbGUuY29tIiwiYXVkIjoi.signature"
        
        # Step 2: Frontend sends token to backend
        with patch('app.services.google_auth.google_auth_service.verify_and_get_user_info') as mock_verify:
            with patch('app.services.user.user_service.get_or_create_google_user') as mock_get_create:
                with patch('app.services.auth.auth_service.create_token_pair') as mock_create_tokens:
                    
                    # Setup mocks for successful flow
                    mock_verify.return_value = {
                        "sub": "google_user_123",
                        "email": "integration@example.com",
                        "name": "Integration Test User",
                        "picture": "https://example.com/avatar.jpg",
                        "email_verified": True
                    }
                    
                    mock_user = User(
                        id=1,
                        google_id="google_user_123",
                        email="integration@example.com",
                        nickname="Integration Test User",
                        avatar_url="https://example.com/avatar.jpg",
                        is_active=True
                    )
                    mock_get_create.return_value = mock_user
                    
                    mock_create_tokens.return_value = TokenResponse(
                        access_token="access_token_123",
                        refresh_token="refresh_token_123",
                        token_type="bearer",
                        expires_in=900
                    )
                    
                    # Step 3: Test the authentication endpoint
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        auth_response = await client.post(
                            "/api/v1/auth/google",
                            json={"google_token": google_token}
                        )
                    
                    assert auth_response.status_code == 200
                    auth_data = auth_response.json()
                    
                    # Step 4: Use access token to access protected endpoint
                    headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
                    
                    with patch('app.core.auth.auth_service.validate_user_session') as mock_validate:
                        mock_validate.return_value = mock_user
                        
                        protected_response = await client.get(
                            "/api/v1/auth/me",
                            headers=headers
                        )
                    
                    assert protected_response.status_code == 200
                    user_data = protected_response.json()
                    assert user_data["email"] == "integration@example.com"
                    assert user_data["nickname"] == "Integration Test User"
    
    @pytest.mark.asyncio
    async def test_google_oauth_error_handling_flow(self):
        """Test Google OAuth error handling in complete flow"""
        
        # Test with invalid Google token
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/google",
                json={"google_token": "invalid.google.token"}
            )
        
        assert response.status_code == 401
        
        # Test with malformed request
        response = await client.post(
            "/api/v1/auth/google",
            json={"wrong_field": "value"}
        )
        
        assert response.status_code == 422


class TestGoogleOAuthPerformance:
    """Performance tests for Google OAuth"""
    
    @pytest.mark.asyncio
    async def test_concurrent_google_auth_requests(self):
        """Test handling concurrent Google authentication requests"""
        import asyncio
        
        async def make_auth_request():
            with patch('app.services.google_auth.google_auth_service.verify_and_get_user_info') as mock_verify:
                with patch('app.services.user.user_service.get_or_create_google_user') as mock_get_create:
                    with patch('app.services.auth.auth_service.create_token_pair') as mock_create_tokens:
                        
                        # Setup mocks
                        mock_verify.return_value = {
                            "sub": f"google_user_{asyncio.current_task().get_name()}",
                            "email": f"user{asyncio.current_task().get_name()}@example.com",
                            "name": "Test User",
                            "email_verified": True
                        }
                        
                        mock_get_create.return_value = User(
                            id=1,
                            google_id=f"google_user_{asyncio.current_task().get_name()}",
                            email=f"user{asyncio.current_task().get_name()}@example.com",
                            nickname="Test User",
                            is_active=True
                        )
                        
                        mock_create_tokens.return_value = TokenResponse(
                            access_token="access_token",
                            refresh_token="refresh_token",
                            token_type="bearer",
                            expires_in=900
                        )
                        
                        async with AsyncClient(app=app, base_url="http://test") as client:
                            response = await client.post(
                                "/api/v1/auth/google",
                                json={"google_token": "valid.google.token"}
                            )
                        
                        return response.status_code
        
        # Create multiple concurrent requests
        tasks = [make_auth_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert all(status == 200 for status in results)
    
    @pytest.mark.asyncio
    async def test_google_auth_response_time(self):
        """Test Google authentication response time"""
        import time
        
        with patch('app.services.google_auth.google_auth_service.verify_and_get_user_info') as mock_verify:
            with patch('app.services.user.user_service.get_or_create_google_user') as mock_get_create:
                with patch('app.services.auth.auth_service.create_token_pair') as mock_create_tokens:
                    
                    # Setup mocks
                    mock_verify.return_value = {
                        "sub": "google_user_123",
                        "email": "performance@example.com",
                        "name": "Performance Test User",
                        "email_verified": True
                    }
                    
                    mock_get_create.return_value = User(
                        id=1,
                        google_id="google_user_123",
                        email="performance@example.com",
                        nickname="Performance Test User",
                        is_active=True
                    )
                    
                    mock_create_tokens.return_value = TokenResponse(
                        access_token="access_token",
                        refresh_token="refresh_token",
                        token_type="bearer",
                        expires_in=900
                    )
                    
                    # Measure response time
                    start_time = time.time()
                    
                    async with AsyncClient(app=app, base_url="http://test") as client:
                        response = await client.post(
                            "/api/v1/auth/google",
                            json={"google_token": "valid.google.token"}
                        )
                    
                    end_time = time.time()
                    response_time = end_time - start_time
                    
                    assert response.status_code == 200
                    assert response_time < 1.0  # Should respond within 1 second


if __name__ == "__main__":
    pytest.main([__file__])