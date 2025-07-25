"""
Tests for Web3 wallet authentication service
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from eth_account import Account
from eth_account.messages import encode_defunct

from app.services.web3_auth import web3_auth_service
from app.schemas.user import WalletAuthRequest, UserWalletCreate
from app.core.exceptions import Web3AuthenticationError, ValidationError
from app.models.user import User, UserWallet


class TestWeb3AuthService:
    """Test Web3 authentication service"""
    
    def test_generate_auth_nonce_valid_address(self):
        """Test generating nonce for valid wallet address"""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        nonce = web3_auth_service.generate_auth_nonce(wallet_address)
        
        assert nonce is not None
        assert len(nonce) == 32  # 16 bytes hex = 32 characters
        assert all(c in '0123456789abcdef' for c in nonce)
    
    def test_generate_auth_nonce_invalid_address(self):
        """Test generating nonce for invalid wallet address"""
        invalid_addresses = [
            "",
            "invalid_address",
            "0x123",  # Too short
            "742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",  # Missing 0x prefix
            "0xGGGd35Cc6634C0532925a3b8D4C9db96C4b4d8b6"  # Invalid hex characters
        ]
        
        for address in invalid_addresses:
            with pytest.raises(ValidationError):
                web3_auth_service.generate_auth_nonce(address)
    
    def test_get_auth_message(self):
        """Test getting authentication message"""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        nonce = "test_nonce_123"
        
        message = web3_auth_service.get_auth_message(wallet_address, nonce)
        
        assert wallet_address in message
        assert nonce in message
        assert "BountyGo" in message
        assert "Sign this message" in message
    
    def test_verify_wallet_signature_valid(self):
        """Test verifying valid wallet signature"""
        # Create a test account
        account = Account.create()
        wallet_address = account.address
        
        # Create message and sign it
        nonce = "test_nonce_123"
        message = web3_auth_service.get_auth_message(wallet_address, nonce)
        
        # Sign the message
        encoded_message = encode_defunct(text=message)
        signed_message = account.sign_message(encoded_message)
        signature = signed_message.signature.hex()
        
        # Verify signature
        is_valid = web3_auth_service.verify_wallet_signature(
            wallet_address, signature, message
        )
        
        assert is_valid is True
    
    def test_verify_wallet_signature_invalid(self):
        """Test verifying invalid wallet signature"""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        message = "test message"
        invalid_signature = "0x" + "0" * 130  # Invalid signature
        
        with pytest.raises(Web3AuthenticationError):
            web3_auth_service.verify_wallet_signature(
                wallet_address, invalid_signature, message
            )
    
    def test_verify_wallet_signature_wrong_address(self):
        """Test verifying signature with wrong wallet address"""
        # Create two different accounts
        account1 = Account.create()
        account2 = Account.create()
        
        message = "test message"
        
        # Sign with account1
        encoded_message = encode_defunct(text=message)
        signed_message = account1.sign_message(encoded_message)
        signature = signed_message.signature.hex()
        
        # Try to verify with account2's address
        is_valid = web3_auth_service.verify_wallet_signature(
            account2.address, signature, message
        )
        
        assert is_valid is False
    
    def test_validate_nonce_valid(self):
        """Test validating valid nonce"""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Generate nonce
        nonce = web3_auth_service.generate_auth_nonce(wallet_address)
        
        # Validate nonce
        is_valid = web3_auth_service._validate_nonce(wallet_address, nonce)
        
        assert is_valid is True
    
    def test_validate_nonce_invalid(self):
        """Test validating invalid nonce"""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        invalid_nonce = "invalid_nonce"
        
        is_valid = web3_auth_service._validate_nonce(wallet_address, invalid_nonce)
        
        assert is_valid is False
    
    def test_validate_nonce_used(self):
        """Test validating already used nonce"""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Generate nonce
        nonce = web3_auth_service.generate_auth_nonce(wallet_address)
        
        # Use nonce once
        web3_auth_service._validate_nonce(wallet_address, nonce)
        
        # Try to use again
        is_valid = web3_auth_service._validate_nonce(wallet_address, nonce)
        
        assert is_valid is False
    
    def test_validate_nonce_expired(self):
        """Test validating expired nonce"""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Generate nonce
        nonce = web3_auth_service.generate_auth_nonce(wallet_address)
        
        # Manually expire the nonce
        normalized_address = wallet_address.lower()
        web3_auth_service._nonces[normalized_address]['expires_at'] = (
            datetime.utcnow() - timedelta(seconds=1)
        )
        
        # Try to validate expired nonce
        is_valid = web3_auth_service._validate_nonce(wallet_address, nonce)
        
        assert is_valid is False
    
    def test_extract_nonce_from_message(self):
        """Test extracting nonce from authentication message"""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        nonce = "48ce06fc247671892e765f45e36f5913"  # Hex nonce like generated ones
        
        message = web3_auth_service.get_auth_message(wallet_address, nonce)
        extracted_nonce = web3_auth_service._extract_nonce_from_message(message)
        
        assert extracted_nonce == nonce
    
    def test_extract_nonce_from_invalid_message(self):
        """Test extracting nonce from invalid message"""
        invalid_message = "This message has no nonce"
        
        extracted_nonce = web3_auth_service._extract_nonce_from_message(invalid_message)
        
        assert extracted_nonce is None
    
    def test_validate_wallet_address_format(self):
        """Test wallet address format validation"""
        valid_addresses = [
            "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            "0x0000000000000000000000000000000000000000",
            "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"
        ]
        
        for address in valid_addresses:
            assert web3_auth_service.validate_wallet_address_format(address) is True
        
        invalid_addresses = [
            "",
            "invalid_address",
            "0x123",
            "742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            "0xGGGd35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        ]
        
        for address in invalid_addresses:
            assert web3_auth_service.validate_wallet_address_format(address) is False
    
    def test_normalize_wallet_address(self):
        """Test wallet address normalization"""
        address = "0x742D35CC6634C0532925A3B8D4C9DB96C4B4D8B6"
        normalized = web3_auth_service.normalize_wallet_address(address)
        
        assert normalized == address.lower()
    
    def test_normalize_invalid_wallet_address(self):
        """Test normalizing invalid wallet address"""
        invalid_address = "invalid_address"
        
        with pytest.raises(ValueError):
            web3_auth_service.normalize_wallet_address(invalid_address)
    
    def test_cleanup_expired_nonces(self):
        """Test cleanup of expired nonces"""
        wallet_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Generate nonce
        nonce = web3_auth_service.generate_auth_nonce(wallet_address)
        
        # Manually expire the nonce
        normalized_address = wallet_address.lower()
        web3_auth_service._nonces[normalized_address]['expires_at'] = (
            datetime.utcnow() - timedelta(seconds=1)
        )
        
        # Cleanup should remove expired nonce
        web3_auth_service._cleanup_expired_nonces()
        
        assert normalized_address not in web3_auth_service._nonces


@pytest.mark.asyncio
class TestWeb3AuthIntegration:
    """Integration tests for Web3 wallet authentication - database operations"""
    
    async def test_authenticate_wallet_success(self, db_session, test_user):
        """Test successful wallet authentication with database"""
        from eth_account import Account
        from eth_account.messages import encode_defunct
        
        # Create test account
        account = Account.create()
        wallet_address = account.address
        
        # Add wallet to user
        from app.models.user import UserWallet
        wallet = UserWallet(
            user_id=test_user.id,
            wallet_address=wallet_address.lower(),
            wallet_type="ethereum",
            is_primary=True
        )
        db_session.add(wallet)
        await db_session.commit()
        
        # Generate nonce and message
        nonce = web3_auth_service.generate_auth_nonce(wallet_address)
        message = web3_auth_service.get_auth_message(wallet_address, nonce)
        
        # Sign message
        encoded_message = encode_defunct(text=message)
        signed_message = account.sign_message(encoded_message)
        signature = signed_message.signature.hex()
        
        # Create auth request
        auth_request = WalletAuthRequest(
            wallet_address=wallet_address,
            signature=signature,
            message=message
        )
        
        # Authenticate
        token_response = await web3_auth_service.authenticate_wallet(db_session, auth_request)
        
        assert token_response.access_token is not None
        assert token_response.refresh_token is not None
        assert token_response.token_type == "bearer"
    
    async def test_authenticate_wallet_not_linked(self, db_session):
        """Test wallet authentication with unlinked wallet"""
        from eth_account import Account
        from eth_account.messages import encode_defunct
        
        # Create test account
        account = Account.create()
        wallet_address = account.address
        
        # Generate nonce and message
        nonce = web3_auth_service.generate_auth_nonce(wallet_address)
        message = web3_auth_service.get_auth_message(wallet_address, nonce)
        
        # Sign message
        encoded_message = encode_defunct(text=message)
        signed_message = account.sign_message(encoded_message)
        signature = signed_message.signature.hex()
        
        # Create auth request
        auth_request = WalletAuthRequest(
            wallet_address=wallet_address,
            signature=signature,
            message=message
        )
        
        # Try to authenticate (should fail)
        with pytest.raises(Web3AuthenticationError, match="not linked"):
            await web3_auth_service.authenticate_wallet(db_session, auth_request)
    
    async def test_link_wallet_success(self, db_session, test_user):
        """Test successful wallet linking"""
        from eth_account import Account
        from eth_account.messages import encode_defunct
        
        # Create test account
        account = Account.create()
        wallet_address = account.address
        
        # Generate nonce and message
        nonce = web3_auth_service.generate_auth_nonce(wallet_address)
        message = web3_auth_service.get_auth_message(wallet_address, nonce)
        
        # Sign message
        encoded_message = encode_defunct(text=message)
        signed_message = account.sign_message(encoded_message)
        signature = signed_message.signature.hex()
        
        # Create auth request
        auth_request = WalletAuthRequest(
            wallet_address=wallet_address,
            signature=signature,
            message=message
        )
        
        # Link wallet
        wallet = await web3_auth_service.link_wallet_to_user(
            db_session, test_user.id, auth_request, is_primary=True
        )
        
        assert wallet.wallet_address == wallet_address.lower()
        assert wallet.wallet_type == "ethereum"
        assert wallet.is_primary is True
        assert wallet.user_id == test_user.id
    
    async def test_link_wallet_already_linked(self, db_session, test_user):
        """Test linking already linked wallet"""
        from eth_account import Account
        from eth_account.messages import encode_defunct
        
        # Create test account
        account = Account.create()
        wallet_address = account.address
        
        # Add wallet to user first
        from app.models.user import UserWallet
        existing_wallet = UserWallet(
            user_id=test_user.id,
            wallet_address=wallet_address.lower(),
            wallet_type="ethereum",
            is_primary=False
        )
        db_session.add(existing_wallet)
        await db_session.commit()
        
        # Generate nonce and message
        nonce = web3_auth_service.generate_auth_nonce(wallet_address)
        message = web3_auth_service.get_auth_message(wallet_address, nonce)
        
        # Sign message
        encoded_message = encode_defunct(text=message)
        signed_message = account.sign_message(encoded_message)
        signature = signed_message.signature.hex()
        
        # Create auth request
        auth_request = WalletAuthRequest(
            wallet_address=wallet_address,
            signature=signature,
            message=message
        )
        
        # Try to link already linked wallet
        with pytest.raises(ValidationError, match="already linked"):
            await web3_auth_service.link_wallet_to_user(
                db_session, test_user.id, auth_request
            )
    
    async def test_unlink_wallet_success(self, db_session, test_user):
        """Test successful wallet unlinking"""
        # Add wallet to user
        from app.models.user import UserWallet
        wallet = UserWallet(
            user_id=test_user.id,
            wallet_address="0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b6",
            wallet_type="ethereum",
            is_primary=False
        )
        db_session.add(wallet)
        await db_session.commit()
        await db_session.refresh(wallet)
        
        # Unlink wallet
        result = await web3_auth_service.unlink_wallet_from_user(
            db_session, test_user.id, wallet.id
        )
        
        assert result is True