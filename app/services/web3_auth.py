"""
Web3 wallet authentication service for signature verification and wallet linking
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from eth_account.messages import encode_defunct
from eth_account import Account
import secrets

from app.core.config import settings
from app.core.exceptions import Web3AuthenticationError, ValidationError, NotFoundError
from app.core.security import (
    validate_ethereum_address, 
    normalize_ethereum_address,
    create_web3_auth_message,
    generate_nonce
)
from app.models.user import User, UserWallet
from app.schemas.user import TokenResponse, WalletAuthRequest, UserWalletCreate
from app.services.base import BaseService
from app.services.auth import auth_service
from app.services.user import user_service


class Web3AuthService(BaseService):
    """Web3 wallet authentication service"""
    
    def __init__(self):
        # Store nonces temporarily (in production, use Redis)
        self._nonces: Dict[str, Dict[str, Any]] = {}
        self._nonce_ttl = 300  # 5 minutes
    
    def _cleanup_expired_nonces(self):
        """Clean up expired nonces"""
        current_time = datetime.utcnow()
        expired_keys = []
        
        for key, data in self._nonces.items():
            if current_time > data['expires_at']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._nonces[key]
    
    def generate_auth_nonce(self, wallet_address: str) -> str:
        """Generate authentication nonce for wallet"""
        # Validate wallet address
        if not validate_ethereum_address(wallet_address):
            raise ValidationError("Invalid Ethereum wallet address format")
        
        # Normalize address
        normalized_address = normalize_ethereum_address(wallet_address)
        
        # Clean up expired nonces
        self._cleanup_expired_nonces()
        
        # Generate new nonce
        nonce = generate_nonce()
        expires_at = datetime.utcnow() + timedelta(seconds=self._nonce_ttl)
        
        # Store nonce
        self._nonces[normalized_address] = {
            'nonce': nonce,
            'expires_at': expires_at,
            'used': False
        }
        
        return nonce
    
    def get_auth_message(self, wallet_address: str, nonce: str) -> str:
        """Get standardized authentication message"""
        if not validate_ethereum_address(wallet_address):
            raise ValidationError("Invalid Ethereum wallet address format")
        
        return create_web3_auth_message(wallet_address, nonce)
    
    def verify_wallet_signature(
        self, 
        wallet_address: str, 
        signature: str, 
        message: str
    ) -> bool:
        """Verify wallet signature against message"""
        try:
            # Validate wallet address
            if not validate_ethereum_address(wallet_address):
                raise ValidationError("Invalid Ethereum wallet address format")
            
            # Normalize address
            normalized_address = normalize_ethereum_address(wallet_address)
            
            # Encode message for Ethereum signing
            encoded_message = encode_defunct(text=message)
            
            # Recover address from signature
            recovered_address = Account.recover_message(encoded_message, signature=signature)
            
            # Compare addresses (case-insensitive)
            return recovered_address.lower() == normalized_address.lower()
            
        except Exception as e:
            raise Web3AuthenticationError(f"Signature verification failed: {str(e)}")
    
    def _validate_nonce(self, wallet_address: str, nonce: str) -> bool:
        """Validate nonce for wallet address"""
        normalized_address = normalize_ethereum_address(wallet_address)
        
        # Clean up expired nonces
        self._cleanup_expired_nonces()
        
        nonce_data = self._nonces.get(normalized_address)
        if not nonce_data:
            return False
        
        # Check if nonce matches and hasn't been used
        if nonce_data['nonce'] != nonce or nonce_data['used']:
            return False
        
        # Check if nonce hasn't expired
        if datetime.utcnow() > nonce_data['expires_at']:
            return False
        
        # Mark nonce as used
        nonce_data['used'] = True
        
        return True
    
    async def authenticate_wallet(
        self, 
        db: AsyncSession, 
        auth_request: WalletAuthRequest
    ) -> TokenResponse:
        """Authenticate user with wallet signature"""
        wallet_address = auth_request.wallet_address
        signature = auth_request.signature
        message = auth_request.message
        
        # Validate wallet address format
        if not validate_ethereum_address(wallet_address):
            raise ValidationError("Invalid Ethereum wallet address format")
        
        # Extract nonce from message
        nonce = self._extract_nonce_from_message(message)
        if not nonce:
            raise Web3AuthenticationError("Invalid authentication message format")
        
        # Validate nonce
        if not self._validate_nonce(wallet_address, nonce):
            raise Web3AuthenticationError("Invalid or expired nonce")
        
        # Verify signature
        if not self.verify_wallet_signature(wallet_address, signature, message):
            raise Web3AuthenticationError("Invalid wallet signature")
        
        # Find user by wallet address
        user = await self._get_user_by_wallet(db, wallet_address)
        if not user:
            raise Web3AuthenticationError(
                "Wallet not linked to any user account. Please link your wallet first."
            )
        
        # Check if user is active
        if not user.is_active:
            raise Web3AuthenticationError("User account is inactive")
        
        # Create token pair
        return await auth_service.create_token_pair(db, user.id)
    
    async def link_wallet_to_user(
        self, 
        db: AsyncSession, 
        user_id: int, 
        auth_request: WalletAuthRequest,
        is_primary: bool = False
    ) -> UserWallet:
        """Link wallet to existing user account"""
        wallet_address = auth_request.wallet_address
        signature = auth_request.signature
        message = auth_request.message
        
        # Validate wallet address format
        if not validate_ethereum_address(wallet_address):
            raise ValidationError("Invalid Ethereum wallet address format")
        
        # Extract nonce from message
        nonce = self._extract_nonce_from_message(message)
        if not nonce:
            raise Web3AuthenticationError("Invalid authentication message format")
        
        # Validate nonce
        if not self._validate_nonce(wallet_address, nonce):
            raise Web3AuthenticationError("Invalid or expired nonce")
        
        # Verify signature
        if not self.verify_wallet_signature(wallet_address, signature, message):
            raise Web3AuthenticationError("Invalid wallet signature")
        
        # Check if wallet is already linked
        existing_wallet = await self._get_wallet_by_address(db, wallet_address)
        if existing_wallet:
            raise ValidationError("Wallet address is already linked to an account")
        
        # Link wallet to user
        wallet_data = UserWalletCreate(
            wallet_address=normalize_ethereum_address(wallet_address),
            wallet_type="ethereum",
            is_primary=is_primary
        )
        
        return await user_service.add_wallet(db, user_id, wallet_data)
    
    async def unlink_wallet_from_user(
        self, 
        db: AsyncSession, 
        user_id: int, 
        wallet_id: int
    ) -> bool:
        """Unlink wallet from user account"""
        return await user_service.remove_wallet(db, user_id, wallet_id)
    
    def _extract_nonce_from_message(self, message: str) -> Optional[str]:
        """Extract nonce from authentication message"""
        # Look for nonce pattern in message (hex characters only for generated nonces)
        nonce_pattern = r'Nonce:\s*([a-fA-F0-9]+)'
        match = re.search(nonce_pattern, message)
        return match.group(1) if match else None
    
    async def _get_user_by_wallet(
        self, 
        db: AsyncSession, 
        wallet_address: str
    ) -> Optional[User]:
        """Get user by wallet address"""
        normalized_address = normalize_ethereum_address(wallet_address)
        
        stmt = select(User).join(UserWallet).where(
            UserWallet.wallet_address == normalized_address,
            User.is_active == True
        )
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_wallet_by_address(
        self, 
        db: AsyncSession, 
        wallet_address: str
    ) -> Optional[UserWallet]:
        """Get wallet by address"""
        normalized_address = normalize_ethereum_address(wallet_address)
        
        stmt = select(UserWallet).where(
            UserWallet.wallet_address == normalized_address
        )
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    def validate_wallet_address_format(self, address: str) -> bool:
        """Validate wallet address format"""
        return validate_ethereum_address(address)
    
    def normalize_wallet_address(self, address: str) -> str:
        """Normalize wallet address"""
        return normalize_ethereum_address(address)


# Service instance
web3_auth_service = Web3AuthService()