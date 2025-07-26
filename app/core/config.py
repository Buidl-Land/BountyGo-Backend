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

    # PostgreSQL Configuration (for building DATABASE_URL if needed)
    POSTGRES_DB: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 5 minutes

    # CORS
    ALLOWED_HOSTS: str = "*"

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # Clerk Authentication
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_JWKS_URL: Optional[str] = None
    CLERK_FRONTEND_API: Optional[str] = None

    # External Services
    AI_SERVICE_URL: Optional[str] = None
    AI_SERVICE_API_KEY: Optional[str] = None

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = None

    # PPIO Model Configuration
    PPIO_API_KEY: str
    PPIO_BASE_URL: str = "https://api.ppinfra.com/v3/openai"
    PPIO_MODEL_NAME: str = "qwen/qwen3-coder-480b-a35b-instruct"
    PPIO_MAX_TOKENS: int = 4000
    PPIO_TEMPERATURE: float = 0.1
    PPIO_TIMEOUT: int = 60
    PPIO_MAX_RETRIES: int = 3

    # Content Extraction Configuration
    CONTENT_EXTRACTION_TIMEOUT: int = 30
    MAX_CONTENT_LENGTH: int = 50000
    USE_PROXY: bool = False
    PROXY_URL: Optional[str] = None
    ENABLE_CONTENT_CACHE: bool = True
    CONTENT_CACHE_TTL: int = 3600
    USER_AGENT: str = "BountyGo-URLAgent/1.0"
    MAX_REDIRECTS: int = 5
    VERIFY_SSL: bool = True

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

    def validate_ppio_config(self) -> dict:
        """Validate PPIO configuration and return validation results"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Validate API key
        if not self.PPIO_API_KEY:
            validation_results["valid"] = False
            validation_results["errors"].append("PPIO_API_KEY is required")
        elif self.PPIO_API_KEY == "sk_your_ppio_api_key_here":
            validation_results["valid"] = False
            validation_results["errors"].append("PPIO_API_KEY must be replaced with actual API key")
        elif not self.PPIO_API_KEY.startswith('sk_'):
            validation_results["valid"] = False
            validation_results["errors"].append("PPIO_API_KEY must start with 'sk_'")
        elif len(self.PPIO_API_KEY) < 20:
            validation_results["valid"] = False
            validation_results["errors"].append("PPIO_API_KEY appears to be too short")

        # Validate base URL
        if not self.PPIO_BASE_URL.startswith(('http://', 'https://')):
            validation_results["valid"] = False
            validation_results["errors"].append("PPIO_BASE_URL must be a valid HTTP/HTTPS URL")

        # Validate model name
        supported_models = [
            "qwen/qwen3-coder-480b-a35b-instruct",
            "moonshotai/kimi-k2-instruct",
            "deepseek/deepseek-r1-0528",
            "qwen/qwen3-235b-a22b-instruct-2507"
        ]
        if self.PPIO_MODEL_NAME not in supported_models:
            validation_results["warnings"].append(
                f"PPIO_MODEL_NAME '{self.PPIO_MODEL_NAME}' is not in the recommended list. "
                f"Supported models: {', '.join(supported_models)}"
            )

        # Validate numeric parameters
        if not 1 <= self.PPIO_MAX_TOKENS <= 32000:
            validation_results["valid"] = False
            validation_results["errors"].append("PPIO_MAX_TOKENS must be between 1 and 32000")

        if not 0 <= self.PPIO_TEMPERATURE <= 2:
            validation_results["valid"] = False
            validation_results["errors"].append("PPIO_TEMPERATURE must be between 0 and 2")

        if not 1 <= self.PPIO_TIMEOUT <= 300:
            validation_results["valid"] = False
            validation_results["errors"].append("PPIO_TIMEOUT must be between 1 and 300 seconds")

        if not 1 <= self.PPIO_MAX_RETRIES <= 10:
            validation_results["valid"] = False
            validation_results["errors"].append("PPIO_MAX_RETRIES must be between 1 and 10")

        return validation_results

    def validate_url_agent_config(self) -> dict:
        """Validate URL agent configuration"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Validate timeout settings
        if self.CONTENT_EXTRACTION_TIMEOUT <= 0:
            validation_results["valid"] = False
            validation_results["errors"].append("CONTENT_EXTRACTION_TIMEOUT must be positive")
        elif self.CONTENT_EXTRACTION_TIMEOUT > 300:  # 5 minutes
            validation_results["warnings"].append(
                "CONTENT_EXTRACTION_TIMEOUT is very high (>5 minutes), this may cause request timeouts"
            )

        # Validate content length
        if self.MAX_CONTENT_LENGTH <= 0:
            validation_results["valid"] = False
            validation_results["errors"].append("MAX_CONTENT_LENGTH must be positive")
        elif self.MAX_CONTENT_LENGTH > 1000000:  # 1MB
            validation_results["warnings"].append(
                "MAX_CONTENT_LENGTH is very high (>1MB), this may cause memory issues"
            )

        # Validate cache TTL
        if self.CONTENT_CACHE_TTL <= 0:
            validation_results["valid"] = False
            validation_results["errors"].append("CONTENT_CACHE_TTL must be positive")

        # Validate proxy configuration
        if self.USE_PROXY and not self.PROXY_URL:
            validation_results["valid"] = False
            validation_results["errors"].append("PROXY_URL is required when USE_PROXY is true")

        if self.PROXY_URL and not self.PROXY_URL.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
            validation_results["valid"] = False
            validation_results["errors"].append("PROXY_URL must be a valid proxy URL")

        # Validate redirects
        if not 0 <= self.MAX_REDIRECTS <= 20:
            validation_results["valid"] = False
            validation_results["errors"].append("MAX_REDIRECTS must be between 0 and 20")

        # Validate user agent
        if not self.USER_AGENT or len(self.USER_AGENT.strip()) == 0:
            validation_results["valid"] = False
            validation_results["errors"].append("USER_AGENT cannot be empty")

        return validation_results

    def validate_production_config(self) -> dict:
        """Validate configuration for production environment"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        if not self.is_production():
            validation_results["warnings"].append("Not running in production environment")
            return validation_results

        # Production security checks
        if self.DEBUG:
            validation_results["valid"] = False
            validation_results["errors"].append("DEBUG must be False in production")

        if len(self.SECRET_KEY) < 32:
            validation_results["valid"] = False
            validation_results["errors"].append("SECRET_KEY must be at least 32 characters in production")

        if self.DEV_TEST_TOKEN:
            validation_results["valid"] = False
            validation_results["errors"].append("DEV_TEST_TOKEN must not be set in production")

        # Production performance recommendations
        if self.DATABASE_POOL_SIZE < 10:
            validation_results["warnings"].append("Consider increasing DATABASE_POOL_SIZE for production")

        if self.CONTENT_CACHE_TTL < 1800:  # 30 minutes
            validation_results["warnings"].append("Consider increasing CONTENT_CACHE_TTL for production")

        if self.PPIO_TIMEOUT < 60:
            validation_results["warnings"].append("Consider increasing PPIO_TIMEOUT for production")

        # SSL verification should be enabled in production
        if not self.VERIFY_SSL:
            validation_results["warnings"].append("VERIFY_SSL should be True in production")

        return validation_results

    def validate_clerk_config(self) -> dict:
        """Validate Clerk configuration and return validation results"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # Check if Clerk is configured
        if not self.CLERK_SECRET_KEY and not self.CLERK_JWKS_URL:
            validation_results["warnings"].append("Clerk authentication not configured")
            return validation_results

        # Validate secret key
        if self.CLERK_SECRET_KEY:
            if not self.CLERK_SECRET_KEY.startswith('sk_'):
                validation_results["valid"] = False
                validation_results["errors"].append("CLERK_SECRET_KEY must start with 'sk_'")
            elif len(self.CLERK_SECRET_KEY) < 20:
                validation_results["valid"] = False
                validation_results["errors"].append("CLERK_SECRET_KEY appears to be too short")

        # Validate publishable key
        if self.CLERK_PUBLISHABLE_KEY:
            if not self.CLERK_PUBLISHABLE_KEY.startswith('pk_'):
                validation_results["valid"] = False
                validation_results["errors"].append("CLERK_PUBLISHABLE_KEY must start with 'pk_'")

        # Validate JWKS URL
        if self.CLERK_JWKS_URL:
            if not self.CLERK_JWKS_URL.startswith(('http://', 'https://')):
                validation_results["valid"] = False
                validation_results["errors"].append("CLERK_JWKS_URL must be a valid HTTP/HTTPS URL")
            elif not self.CLERK_JWKS_URL.endswith('/.well-known/jwks.json'):
                validation_results["warnings"].append("CLERK_JWKS_URL should end with '/.well-known/jwks.json'")

        # Validate frontend API
        if self.CLERK_FRONTEND_API:
            if not self.CLERK_FRONTEND_API.startswith(('http://', 'https://')):
                validation_results["valid"] = False
                validation_results["errors"].append("CLERK_FRONTEND_API must be a valid HTTP/HTTPS URL")

        return validation_results

    def is_clerk_enabled(self) -> bool:
        """Check if Clerk authentication is enabled"""
        return bool(self.CLERK_SECRET_KEY or self.CLERK_JWKS_URL)

    def get_clerk_jwks_url(self) -> Optional[str]:
        """Get Clerk JWKS URL, auto-generate if frontend API is provided"""
        if self.CLERK_JWKS_URL:
            return self.CLERK_JWKS_URL
        elif self.CLERK_FRONTEND_API:
            return f"{self.CLERK_FRONTEND_API.rstrip('/')}/.well-known/jwks.json"
        return None

    def get_config_summary(self) -> dict:
        """Get a summary of current configuration for debugging"""
        return {
            "environment": self.ENVIRONMENT,
            "debug": self.DEBUG,
            "ppio_model": self.PPIO_MODEL_NAME,
            "ppio_base_url": self.PPIO_BASE_URL,
            "ppio_timeout": self.PPIO_TIMEOUT,
            "ppio_max_retries": self.PPIO_MAX_RETRIES,
            "content_timeout": self.CONTENT_EXTRACTION_TIMEOUT,
            "max_content_length": self.MAX_CONTENT_LENGTH,
            "cache_enabled": self.ENABLE_CONTENT_CACHE,
            "cache_ttl": self.CONTENT_CACHE_TTL,
            "proxy_enabled": self.USE_PROXY,
            "proxy_url": self.PROXY_URL if self.USE_PROXY else None,
            "user_agent": self.USER_AGENT,
            "max_redirects": self.MAX_REDIRECTS,
            "verify_ssl": self.VERIFY_SSL,
            "dev_test_enabled": self.is_dev_test_token_enabled(),
            "clerk_enabled": self.is_clerk_enabled(),
            "clerk_jwks_url": self.get_clerk_jwks_url()
        }

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()