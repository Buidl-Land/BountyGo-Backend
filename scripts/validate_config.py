#!/usr/bin/env python3
"""
Configuration validation script for BountyGo Backend
Validates environment configuration and provides detailed feedback
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.core.config import settings
    from pydantic import ValidationError
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root and dependencies are installed")
    sys.exit(1)


def print_section(title: str) -> None:
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_validation_results(results: Dict[str, Any], section_name: str) -> bool:
    """Print validation results and return whether validation passed"""
    print(f"\n{section_name} Validation:")
    print("-" * 40)
    
    if results["valid"]:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration has errors")
    
    # Print errors
    if results["errors"]:
        print("\n🚨 Errors:")
        for error in results["errors"]:
            print(f"  • {error}")
    
    # Print warnings
    if results["warnings"]:
        print("\n⚠️  Warnings:")
        for warning in results["warnings"]:
            print(f"  • {warning}")
    
    return results["valid"]


def validate_environment_file() -> bool:
    """Validate that .env file exists and has required variables"""
    print("\nEnvironment File Validation:")
    print("-" * 40)
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("   Create .env file by copying from .env.example:")
        print("   cp .env.example .env")
        return False
    
    print("✅ .env file exists")
    
    # Check for required variables
    required_vars = [
        "SECRET_KEY",
        "DATABASE_URL", 
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "PPIO_API_KEY"
    ]
    
    missing_vars = []
    placeholder_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        elif value in [
            "your-secret-key-here-at-least-32-characters-long",
            "your-google-client-id",
            "your-google-client-secret", 
            "sk_your_ppio_api_key_here"
        ]:
            placeholder_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required variables: {', '.join(missing_vars)}")
        return False
    
    if placeholder_vars:
        print(f"⚠️  Variables with placeholder values: {', '.join(placeholder_vars)}")
        print("   Please update these with actual values")
    
    return len(missing_vars) == 0


def validate_database_connection() -> bool:
    """Validate database connection"""
    print("\nDatabase Connection Validation:")
    print("-" * 40)
    
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.engine import Engine
        
        # Create synchronous engine for testing
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
        engine: Engine = create_engine(sync_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            if result.fetchone()[0] == 1:
                print("✅ Database connection successful")
                return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    return False


def validate_redis_connection() -> bool:
    """Validate Redis connection"""
    print("\nRedis Connection Validation:")
    print("-" * 40)
    
    try:
        import redis
        
        # Parse Redis URL
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


def validate_ppio_api() -> bool:
    """Validate PPIO API connection"""
    print("\nPPIO API Validation:")
    print("-" * 40)
    
    try:
        import httpx
        import asyncio
        
        async def test_ppio_api():
            headers = {
                "Authorization": f"Bearer {settings.PPIO_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Test with a simple completion request
            data = {
                "model": settings.PPIO_MODEL_NAME,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.PPIO_BASE_URL}/chat/completions",
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    print("✅ PPIO API connection successful")
                    return True
                else:
                    print(f"❌ PPIO API returned status {response.status_code}: {response.text}")
                    return False
        
        return asyncio.run(test_ppio_api())
        
    except Exception as e:
        print(f"❌ PPIO API validation failed: {e}")
        return False


def print_config_summary():
    """Print configuration summary"""
    print_section("Configuration Summary")
    
    summary = settings.get_config_summary()
    
    print(f"Environment: {summary['environment']}")
    print(f"Debug Mode: {summary['debug']}")
    print(f"PPIO Model: {summary['ppio_model']}")
    print(f"PPIO Base URL: {summary['ppio_base_url']}")
    print(f"PPIO Timeout: {summary['ppio_timeout']}s")
    print(f"PPIO Max Retries: {summary['ppio_max_retries']}")
    print(f"Content Extraction Timeout: {summary['content_timeout']}s")
    print(f"Max Content Length: {summary['max_content_length']} bytes")
    print(f"Content Cache Enabled: {summary['cache_enabled']}")
    print(f"Content Cache TTL: {summary['cache_ttl']}s")
    print(f"Proxy Enabled: {summary['proxy_enabled']}")
    if summary['proxy_url']:
        print(f"Proxy URL: {summary['proxy_url']}")
    print(f"User Agent: {summary['user_agent']}")
    print(f"Max Redirects: {summary['max_redirects']}")
    print(f"Verify SSL: {summary['verify_ssl']}")
    print(f"Dev Test Token Enabled: {summary['dev_test_enabled']}")


def main():
    """Main validation function"""
    print_section("BountyGo Backend Configuration Validation")
    
    all_valid = True
    
    # Basic environment validation
    if not validate_environment_file():
        all_valid = False
    
    try:
        # Load settings (this will trigger pydantic validation)
        print(f"\nLoaded settings for environment: {settings.ENVIRONMENT}")
        
        # PPIO configuration validation
        ppio_results = settings.validate_ppio_config()
        if not print_validation_results(ppio_results, "PPIO"):
            all_valid = False
        
        # URL Agent configuration validation
        agent_results = settings.validate_url_agent_config()
        if not print_validation_results(agent_results, "URL Agent"):
            all_valid = False
        
        # Production configuration validation (if applicable)
        if settings.is_production():
            prod_results = settings.validate_production_config()
            if not print_validation_results(prod_results, "Production"):
                all_valid = False
        
        # Connection tests (optional, can be slow)
        if "--skip-connections" not in sys.argv:
            print_section("Connection Tests")
            
            # Database connection test
            if not validate_database_connection():
                all_valid = False
            
            # Redis connection test  
            if not validate_redis_connection():
                all_valid = False
            
            # PPIO API test (only if API key is not placeholder)
            if (settings.PPIO_API_KEY and 
                settings.PPIO_API_KEY != "sk_your_ppio_api_key_here" and
                "--skip-ppio" not in sys.argv):
                if not validate_ppio_api():
                    all_valid = False
        else:
            print("\n⏭️  Skipping connection tests (use --skip-connections to skip)")
        
        # Print configuration summary
        print_config_summary()
        
    except ValidationError as e:
        print(f"\n❌ Configuration validation failed:")
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            print(f"  • {field}: {error['msg']}")
        all_valid = False
    except Exception as e:
        print(f"\n❌ Unexpected error during validation: {e}")
        all_valid = False
    
    # Final result
    print_section("Validation Result")
    
    if all_valid:
        print("✅ All validations passed! Configuration is ready.")
        sys.exit(0)
    else:
        print("❌ Some validations failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()