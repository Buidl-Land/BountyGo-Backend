"""
Application configuration and settings management
"""
from typing import List, Optional
from pydantic import BaseModel, field_validator, validator
from pydantic_settings import BaseSettings
import os
import secrets


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "BountyGo Backend"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 5 minutes
    
    # CORS
    ALLOWED_HOSTS: str = "*"
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    
    # External Services
    AI_SERVICE_URL: Optional[str] = None
    AI_SERVICE_API_KEY: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Development Testing
    DEV_TEST_TOKEN: Optional[str] = None
    DEV_TEST_USER_EMAIL: str = "dev@bountygo.com"
    DEV_TEST_USER_NICKNAME: str = "开发测试用户"
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key"""
        if not v or len(v) < 32:
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            # Generate a random key for development
            return secrets.token_urlsafe(32)
        return v
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL"""
        if not v:
            raise ValueError("DATABASE_URL is required")
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v
    
    def get_allowed_hosts(self) -> List[str]:
        """Get CORS allowed hosts as list"""
        if self.ALLOWED_HOSTS == "*":
            return ["*"]
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"
    
    def get_dev_test_token(self) -> Optional[str]:
        """Get development test token if available"""
        if self.is_development() and self.DEV_TEST_TOKEN:
            return self.DEV_TEST_TOKEN
        return None
    
    def is_dev_test_token_enabled(self) -> bool:
        """Check if development test token is enabled"""
        return self.is_development() and bool(self.DEV_TEST_TOKEN)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()