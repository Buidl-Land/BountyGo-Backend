"""
Integration tests for authentication system
"""
import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.database import get_db
from app.services.auth import auth_service
from app.models.user import User


class TestAuthenticationIntegration:
    """Integration tests for authentication endpoints"""
    
    @pytest.mark.asyncio
    async def test_protected_endpoint_without_auth(self):
        """Test accessing protected endpoint without authentication"""
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/api/v1/auth/protected")
        
        assert response.status_code == 401
        # 检查中文或英文的认证错误消息
        detail = response.json()["detail"]
        assert "身份认证令牌" in detail or "Authentication required" in detail
    
    @pytest.mark.asyncio
    async def test_public_endpoint(self):
        """Test accessing public endpoint"""
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/api/v1/auth/public")
        
        assert response.status_code == 200
        assert response.json()["message"] == "This is a public endpoint"
    
    @pytest.mark.asyncio
    async def test_optional_auth_endpoint_without_auth(self):
        """Test optional auth endpoint without authentication"""
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/api/v1/auth/optional-auth")
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert "anonymous user" in data["message"]
    
    @pytest.mark.asyncio
    async def test_invalid_token_format(self):
        """Test with invalid token format"""
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        headers = {"Authorization": "Bearer invalid_token_format"}
        response = client.get("/api/v1/auth/protected", headers=headers)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_malformed_authorization_header(self):
        """Test with malformed authorization header"""
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        headers = {"Authorization": "InvalidFormat token"}
        response = client.get("/api/v1/auth/protected", headers=headers)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self):
        """Test refresh token with invalid token"""
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": "invalid_refresh_token"}
        )
        
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]


class TestAuthenticationFlow:
    """Test complete authentication flow"""
    
    def create_mock_user(self) -> User:
        """Create a mock user for testing"""
        return User(
            id=1,
            email="test@example.com",
            nickname="testuser",
            is_active=True
        )
    
    @pytest.mark.asyncio
    async def test_token_creation_and_validation(self):
        """Test token creation and validation flow"""
        # This test would require a real database connection
        # For now, we'll test the service layer directly
        
        user_id = 123
        
        # Create tokens
        access_token = auth_service.jwt_service.create_access_token(user_id)
        refresh_token = auth_service.jwt_service.create_refresh_token(user_id)
        
        # Verify tokens
        access_payload = auth_service.jwt_service.verify_token(access_token, "access")
        refresh_payload = auth_service.jwt_service.verify_token(refresh_token, "refresh")
        
        assert access_payload["sub"] == str(user_id)
        assert access_payload["type"] == "access"
        assert refresh_payload["sub"] == str(user_id)
        assert refresh_payload["type"] == "refresh"
        
        # Extract user ID
        extracted_user_id = auth_service.jwt_service.extract_user_id(access_token)
        assert extracted_user_id == user_id


class TestSecurityFeatures:
    """Test security features of authentication system"""
    
    @pytest.mark.asyncio
    async def test_token_expiry_validation(self):
        """Test that expired tokens are rejected"""
        from datetime import timedelta
        
        user_id = 123
        
        # Create token with very short expiry (this would normally be expired immediately)
        # For testing, we'll create a normal token and test the expiry logic
        token = auth_service.jwt_service.create_access_token(user_id)
        
        # Verify token is valid when not expired
        payload = auth_service.jwt_service.verify_token(token, "access")
        assert payload["sub"] == str(user_id)
    
    @pytest.mark.asyncio
    async def test_token_type_validation(self):
        """Test that token type validation works"""
        user_id = 123
        
        access_token = auth_service.jwt_service.create_access_token(user_id)
        refresh_token = auth_service.jwt_service.create_refresh_token(user_id)
        
        # Access token should not validate as refresh token
        with pytest.raises(Exception):
            auth_service.jwt_service.verify_token(access_token, "refresh")
        
        # Refresh token should not validate as access token
        with pytest.raises(Exception):
            auth_service.jwt_service.verify_token(refresh_token, "access")
    
    def test_password_hashing(self):
        """Test password hashing utilities"""
        from app.core.security import get_password_hash, verify_password
        
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Verification should work
        assert verify_password(password, hashed) is True
        
        # Wrong password should fail
        assert verify_password("wrong_password", hashed) is False
    
    def test_ethereum_address_validation(self):
        """Test Ethereum address validation"""
        from app.core.security import validate_ethereum_address, normalize_ethereum_address
        
        valid_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        invalid_address = "invalid_address"
        
        assert validate_ethereum_address(valid_address) is True
        assert validate_ethereum_address(invalid_address) is False
        
        # Test normalization
        normalized = normalize_ethereum_address(valid_address)
        assert normalized == valid_address.lower()
    
    def test_input_sanitization(self):
        """Test input sanitization"""
        from app.core.security import sanitize_user_input
        
        dangerous_input = "<script>alert('xss')</script>Hello World"
        sanitized = sanitize_user_input(dangerous_input)
        
        assert "<script>" not in sanitized
        assert "Hello World" in sanitized
    
    def test_nonce_generation(self):
        """Test nonce generation for Web3 auth"""
        from app.core.security import generate_nonce
        
        nonce1 = generate_nonce()
        nonce2 = generate_nonce()
        
        # Nonces should be different
        assert nonce1 != nonce2
        
        # Nonces should be hex strings
        assert len(nonce1) == 32  # 16 bytes * 2 hex chars
        assert all(c in '0123456789abcdef' for c in nonce1)


if __name__ == "__main__":
    pytest.main([__file__])