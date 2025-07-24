"""
Tests for authentication system
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth import JWTService, RefreshTokenService, AuthenticationService
from app.core.auth import get_current_user, get_current_user_optional, SessionManager
from app.core.security import (
    validate_ethereum_address, 
    normalize_ethereum_address,
    create_web3_auth_message,
    sanitize_user_input,
    validate_email_format
)
from app.core.exceptions import AuthenticationError, InvalidTokenError
from app.models.user import User, RefreshToken
from app.schemas.user import TokenResponse


class TestJWTService:
    """Test JWT service functionality"""
    
    def setup_method(self):
        self.jwt_service = JWTService()
    
    def test_create_access_token(self):
        """Test access token creation"""
        user_id = 123
        token = self.jwt_service.create_access_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT format
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        user_id = 123
        token = self.jwt_service.create_refresh_token(user_id)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT format
    
    def test_verify_valid_token(self):
        """Test token verification with valid token"""
        user_id = 123
        token = self.jwt_service.create_access_token(user_id)
        
        payload = self.jwt_service.verify_token(token, "access")
        
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_verify_invalid_token(self):
        """Test token verification with invalid token"""
        with pytest.raises(AuthenticationError):
            self.jwt_service.verify_token("invalid.token.here", "access")
    
    def test_verify_wrong_token_type(self):
        """Test token verification with wrong token type"""
        user_id = 123
        access_token = self.jwt_service.create_access_token(user_id)
        
        with pytest.raises(AuthenticationError, match="Invalid token type"):
            self.jwt_service.verify_token(access_token, "refresh")
    
    def test_extract_user_id(self):
        """Test user ID extraction from token"""
        user_id = 123
        token = self.jwt_service.create_access_token(user_id)
        
        extracted_id = self.jwt_service.extract_user_id(token)
        
        assert extracted_id == user_id
    
    def test_extract_user_id_invalid_token(self):
        """Test user ID extraction from invalid token"""
        with pytest.raises(AuthenticationError):
            self.jwt_service.extract_user_id("invalid.token.here")
    
    def test_get_token_expiry(self):
        """Test token expiry extraction"""
        user_id = 123
        token = self.jwt_service.create_access_token(user_id)
        
        expiry = self.jwt_service.get_token_expiry(token)
        
        assert isinstance(expiry, datetime)
        assert expiry > datetime.utcnow()


class TestRefreshTokenService:
    """Test refresh token service functionality"""
    
    def setup_method(self):
        self.refresh_service = RefreshTokenService()
    
    def test_hash_token(self):
        """Test token hashing"""
        token = "test_token_123"
        hash1 = self.refresh_service._hash_token(token)
        hash2 = self.refresh_service._hash_token(token)
        
        assert hash1 == hash2  # Same input produces same hash
        assert len(hash1) == 64  # SHA256 hex length
        assert hash1 != token  # Hash is different from original
    
    @pytest.mark.asyncio
    async def test_store_refresh_token(self):
        """Test storing refresh token"""
        db_mock = AsyncMock(spec=AsyncSession)
        user_id = 123
        token = "test_refresh_token"
        
        result = await self.refresh_service.store_refresh_token(db_mock, user_id, token)
        
        assert db_mock.add.called
        assert db_mock.commit.called
        assert db_mock.refresh.called
    
    @pytest.mark.asyncio
    async def test_verify_refresh_token_valid(self):
        """Test verifying valid refresh token"""
        db_mock = AsyncMock(spec=AsyncSession)
        token = "test_refresh_token"
        
        # Mock database response
        mock_token = RefreshToken(
            id=1,
            user_id=123,
            token_hash=self.refresh_service._hash_token(token),
            expires_at=datetime.utcnow() + timedelta(days=1),
            is_revoked=False
        )
        
        # Create a mock result object
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_token
        db_mock.execute = AsyncMock(return_value=mock_result)
        
        result = await self.refresh_service.verify_refresh_token(db_mock, token)
        
        assert result == mock_token
        assert db_mock.execute.called
    
    @pytest.mark.asyncio
    async def test_verify_refresh_token_invalid(self):
        """Test verifying invalid refresh token"""
        db_mock = AsyncMock(spec=AsyncSession)
        token = "invalid_token"
        
        # Create a mock result object
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db_mock.execute = AsyncMock(return_value=mock_result)
        
        result = await self.refresh_service.verify_refresh_token(db_mock, token)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_revoke_refresh_token(self):
        """Test revoking refresh token"""
        db_mock = AsyncMock(spec=AsyncSession)
        token = "test_refresh_token"
        
        # Mock successful update
        db_mock.execute.return_value.rowcount = 1
        
        result = await self.refresh_service.revoke_refresh_token(db_mock, token)
        
        assert result is True
        assert db_mock.execute.called
        assert db_mock.commit.called
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens(self):
        """Test revoking all user tokens"""
        db_mock = AsyncMock(spec=AsyncSession)
        user_id = 123
        
        # Mock successful update
        db_mock.execute.return_value.rowcount = 3
        
        result = await self.refresh_service.revoke_user_tokens(db_mock, user_id)
        
        assert result == 3
        assert db_mock.execute.called
        assert db_mock.commit.called


class TestAuthenticationService:
    """Test main authentication service"""
    
    def setup_method(self):
        self.auth_service = AuthenticationService()
    
    @pytest.mark.asyncio
    async def test_create_token_pair(self):
        """Test creating token pair"""
        db_mock = AsyncMock(spec=AsyncSession)
        user_id = 123
        
        with patch.object(self.auth_service.refresh_service, 'store_refresh_token') as mock_store:
            mock_store.return_value = AsyncMock()
            
            result = await self.auth_service.create_token_pair(db_mock, user_id)
            
            assert isinstance(result, TokenResponse)
            assert result.access_token is not None
            assert result.refresh_token is not None
            assert result.token_type == "bearer"
            assert result.expires_in > 0
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_valid(self):
        """Test refreshing access token with valid refresh token"""
        db_mock = AsyncMock(spec=AsyncSession)
        refresh_token = self.auth_service.jwt_service.create_refresh_token(123)
        
        # Mock refresh token verification
        mock_stored_token = RefreshToken(
            id=1,
            user_id=123,
            token_hash="hash",
            expires_at=datetime.utcnow() + timedelta(days=1),
            is_revoked=False
        )
        
        with patch.object(self.auth_service.refresh_service, 'verify_refresh_token') as mock_verify:
            with patch.object(self.auth_service, 'get_user_by_id') as mock_get_user:
                with patch.object(self.auth_service, 'create_token_pair') as mock_create:
                    mock_verify.return_value = mock_stored_token
                    mock_get_user.return_value = User(id=123, email="test@example.com", nickname="test", is_active=True)
                    mock_create.return_value = TokenResponse(
                        access_token="new_access",
                        refresh_token="new_refresh",
                        token_type="bearer",
                        expires_in=900
                    )
                    
                    result = await self.auth_service.refresh_access_token(db_mock, refresh_token)
                    
                    assert isinstance(result, TokenResponse)
                    assert mock_verify.called
                    assert mock_get_user.called
                    assert mock_create.called
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid(self):
        """Test refreshing access token with invalid refresh token"""
        db_mock = AsyncMock(spec=AsyncSession)
        invalid_token = "invalid.refresh.token"
        
        with pytest.raises(AuthenticationError):
            await self.auth_service.refresh_access_token(db_mock, invalid_token)


class TestSecurityUtilities:
    """Test security utility functions"""
    
    def test_validate_ethereum_address_valid(self):
        """Test validating valid Ethereum addresses"""
        valid_addresses = [
            "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            "0x0000000000000000000000000000000000000000",
            "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        ]
        
        for address in valid_addresses:
            assert validate_ethereum_address(address) is True
    
    def test_validate_ethereum_address_invalid(self):
        """Test validating invalid Ethereum addresses"""
        invalid_addresses = [
            "",
            "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b",  # Too short
            "742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",   # No 0x prefix
            "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6G", # Invalid character
            "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b66"  # Too long
        ]
        
        for address in invalid_addresses:
            assert validate_ethereum_address(address) is False
    
    def test_normalize_ethereum_address(self):
        """Test normalizing Ethereum addresses"""
        address = "0x742D35CC6634C0532925A3B8D4C9DB96C4B4D8B6"
        normalized = normalize_ethereum_address(address)
        
        assert normalized == address.lower()
    
    def test_normalize_ethereum_address_invalid(self):
        """Test normalizing invalid Ethereum addresses"""
        with pytest.raises(ValueError):
            normalize_ethereum_address("invalid_address")
    
    def test_create_web3_auth_message(self):
        """Test creating Web3 authentication message"""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        nonce = "test_nonce_123"
        
        message = create_web3_auth_message(wallet_address, nonce)
        
        assert wallet_address in message
        assert nonce in message
        assert "BountyGo" in message
        assert "authenticate" in message
    
    def test_sanitize_user_input(self):
        """Test user input sanitization"""
        dangerous_input = "<script>alert('xss')</script>Hello & World"
        sanitized = sanitize_user_input(dangerous_input)
        
        assert "<script>" not in sanitized
        assert "&" not in sanitized
        assert "Hello  World" in sanitized
    
    def test_sanitize_user_input_max_length(self):
        """Test user input sanitization with max length"""
        long_input = "a" * 2000
        sanitized = sanitize_user_input(long_input, max_length=100)
        
        assert len(sanitized) == 100
    
    def test_validate_email_format_valid(self):
        """Test validating valid email formats"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org"
        ]
        
        for email in valid_emails:
            assert validate_email_format(email) is True
    
    def test_validate_email_format_invalid(self):
        """Test validating invalid email formats"""
        invalid_emails = [
            "",
            "invalid",
            "@example.com",
            "test@",
            "test.example.com"
        ]
        
        for email in invalid_emails:
            assert validate_email_format(email) is False


class TestSessionManager:
    """Test session management utilities"""
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating user session"""
        db_mock = AsyncMock(spec=AsyncSession)
        user_id = 123
        
        with patch('app.core.auth.auth_service.create_token_pair') as mock_create:
            mock_create.return_value = TokenResponse(
                access_token="access_token",
                refresh_token="refresh_token",
                token_type="bearer",
                expires_in=900
            )
            
            result = await SessionManager.create_session(db_mock, user_id)
            
            assert "access_token" in result
            assert "refresh_token" in result
            assert "expires_in" in result
            assert "token_type" in result
            assert mock_create.called
    
    @pytest.mark.asyncio
    async def test_refresh_session(self):
        """Test refreshing user session"""
        db_mock = AsyncMock(spec=AsyncSession)
        refresh_token = "test_refresh_token"
        
        with patch('app.core.auth.auth_service.refresh_access_token') as mock_refresh:
            mock_refresh.return_value = TokenResponse(
                access_token="new_access_token",
                refresh_token="new_refresh_token",
                token_type="bearer",
                expires_in=900
            )
            
            result = await SessionManager.refresh_session(db_mock, refresh_token)
            
            assert "access_token" in result
            assert "refresh_token" in result
            assert mock_refresh.called
    
    @pytest.mark.asyncio
    async def test_revoke_session(self):
        """Test revoking user session"""
        db_mock = AsyncMock(spec=AsyncSession)
        user_id = 123
        refresh_token = "test_refresh_token"
        
        with patch('app.core.auth.auth_service.revoke_tokens') as mock_revoke:
            mock_revoke.return_value = True
            
            result = await SessionManager.revoke_session(db_mock, user_id, refresh_token)
            
            assert result is True
            assert mock_revoke.called


if __name__ == "__main__":
    pytest.main([__file__])