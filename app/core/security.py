"""
Security utilities for authentication and authorization
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import re
import hashlib

from app.core.config import settings
from app.core.exceptions import AuthenticationError

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    """Create JWT refresh token"""
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def generate_random_string(length: int = 32) -> str:
    """Generate random string for tokens"""
    return secrets.token_urlsafe(length)


def generate_nonce() -> str:
    """Generate nonce for Web3 authentication"""
    return secrets.token_hex(16)


# Web3 Security Utilities

def validate_ethereum_address(address: str) -> bool:
    """Validate Ethereum address format"""
    if not address:
        return False
    
    # Check if it's a valid hex string with 0x prefix and 40 characters
    pattern = r'^0x[a-fA-F0-9]{40}$'
    return bool(re.match(pattern, address))


def normalize_ethereum_address(address: str) -> str:
    """Normalize Ethereum address to lowercase"""
    if not validate_ethereum_address(address):
        raise ValueError("Invalid Ethereum address format")
    return address.lower()


def create_web3_auth_message(wallet_address: str, nonce: str) -> str:
    """Create standardized message for Web3 signature verification"""
    timestamp = int(datetime.utcnow().timestamp())
    return (
        f"Sign this message to authenticate with BountyGo:\n\n"
        f"Wallet: {wallet_address}\n"
        f"Nonce: {nonce}\n"
        f"Timestamp: {timestamp}\n\n"
        f"This request will not trigger a blockchain transaction or cost any gas fees."
    )


def hash_message_for_signature(message: str) -> str:
    """Hash message for signature verification (Ethereum style)"""
    # Ethereum signed message prefix
    prefix = f"\x19Ethereum Signed Message:\n{len(message)}"
    full_message = prefix + message
    return hashlib.sha3_256(full_message.encode()).hexdigest()


# Session Security

def generate_session_id() -> str:
    """Generate secure session ID"""
    return secrets.token_urlsafe(32)


def create_csrf_token() -> str:
    """Create CSRF protection token"""
    return secrets.token_urlsafe(32)


def validate_csrf_token(token: str, expected: str) -> bool:
    """Validate CSRF token"""
    if not token or not expected:
        return False
    return secrets.compare_digest(token, expected)


# Rate Limiting Security

def create_rate_limit_key(identifier: str, endpoint: str) -> str:
    """Create rate limiting key"""
    return f"rate_limit:{identifier}:{endpoint}"


def hash_ip_address(ip: str) -> str:
    """Hash IP address for privacy-preserving rate limiting"""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


# Input Sanitization

def sanitize_user_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent XSS and other attacks"""
    if not text:
        return ""
    
    # Truncate to max length
    text = text[:max_length]
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    # Strip whitespace
    return text.strip()


def validate_email_format(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    
    # Basic email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


# Security Headers

def get_security_headers() -> Dict[str, str]:
    """Get security headers for HTTP responses"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY", 
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'",
    }


# Token Blacklisting (for logout)

def create_token_blacklist_key(token: str) -> str:
    """Create Redis key for token blacklisting"""
    # Use hash of token to avoid storing full token
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return f"blacklist:token:{token_hash}"


def get_token_ttl(token: str) -> int:
    """Get remaining TTL for token (for blacklist expiry)"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        exp = payload.get("exp")
        if exp:
            remaining = exp - int(datetime.utcnow().timestamp())
            return max(0, remaining)
    except JWTError:
        pass
    return 0