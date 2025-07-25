# Environment Configuration Guide

This document provides comprehensive guidance for configuring the BountyGo Backend environment variables for different deployment scenarios.

## Table of Contents

- [Quick Start](#quick-start)
- [Environment Variables Reference](#environment-variables-reference)
- [Development Configuration](#development-configuration)
- [Production Configuration](#production-configuration)
- [PPIO Model Configuration](#ppio-model-configuration)
- [URL Agent Configuration](#url-agent-configuration)
- [Configuration Validation](#configuration-validation)
- [Troubleshooting](#troubleshooting)

## Quick Start

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Update required variables:**
   - `SECRET_KEY`: Generate a secure secret key
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET`: Google OAuth credentials
   - `PPIO_API_KEY`: Your PPIO API key for AI functionality

3. **Validate configuration:**
   ```bash
   python scripts/validate_config.py
   ```

## Environment Variables Reference

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `BountyGo Backend` | Application name |
| `DEBUG` | `false` | Enable debug mode (development only) |
| `VERSION` | `1.0.0` | Application version |
| `ENVIRONMENT` | `development` | Environment type (`development`, `production`) |

### Security Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | JWT signing key (min 32 characters) |
| `JWT_ALGORITHM` | ❌ | JWT algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | Access token expiry (default: 15) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | ❌ | Refresh token expiry (default: 30) |

### Database Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `DATABASE_POOL_SIZE` | ❌ | Connection pool size (default: 10) |
| `DATABASE_MAX_OVERFLOW` | ❌ | Max overflow connections (default: 20) |

**Example DATABASE_URL formats:**
```bash
# Local PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bountygo

# Remote PostgreSQL (Supabase, etc.)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database

# With SSL (production)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database?sslmode=require
```

### Redis Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_URL` | ❌ | Redis connection string |
| `REDIS_CACHE_TTL` | ❌ | Cache TTL in seconds (default: 300) |

**Example REDIS_URL formats:**
```bash
# Local Redis
REDIS_URL=redis://localhost:6379/0

# Redis with password
REDIS_URL=redis://default:password@host:6379/0

# Redis Cloud
REDIS_URL=redis://default:password@host:port/0
```

### Authentication

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth client secret |

### PPIO Model Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PPIO_API_KEY` | ✅ | - | PPIO API key (starts with `sk_`) |
| `PPIO_BASE_URL` | ❌ | `https://api.ppinfra.com/v3/openai` | PPIO API base URL |
| `PPIO_MODEL_NAME` | ❌ | `qwen/qwen3-coder-480b-a35b-instruct` | Model name |
| `PPIO_MAX_TOKENS` | ❌ | `4000` | Maximum tokens per request |
| `PPIO_TEMPERATURE` | ❌ | `0.1` | Model temperature (0-2) |
| `PPIO_TIMEOUT` | ❌ | `60` | Request timeout in seconds |
| `PPIO_MAX_RETRIES` | ❌ | `3` | Maximum retry attempts |

### URL Agent Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CONTENT_EXTRACTION_TIMEOUT` | ❌ | `30` | Web scraping timeout (seconds) |
| `MAX_CONTENT_LENGTH` | ❌ | `50000` | Max content length (bytes) |
| `USE_PROXY` | ❌ | `false` | Enable proxy for web requests |
| `PROXY_URL` | ❌ | - | Proxy URL (if USE_PROXY=true) |
| `ENABLE_CONTENT_CACHE` | ❌ | `true` | Enable content caching |
| `CONTENT_CACHE_TTL` | ❌ | `3600` | Content cache TTL (seconds) |
| `USER_AGENT` | ❌ | `BountyGo-URLAgent/1.0` | User agent string |
| `MAX_REDIRECTS` | ❌ | `5` | Maximum HTTP redirects |
| `VERIFY_SSL` | ❌ | `true` | Verify SSL certificates |

### Rate Limiting

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RATE_LIMIT_PER_MINUTE` | ❌ | `60` | API requests per minute per user |

### CORS Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALLOWED_HOSTS` | ❌ | `*` | Comma-separated allowed hosts |

## Development Configuration

### Recommended Development Settings

```bash
# Application
DEBUG=true
ENVIRONMENT=development

# Security (development only)
SECRET_KEY=dev-secret-key-at-least-32-characters-long

# Database (local PostgreSQL)
DATABASE_URL=postgresql+asyncpg://bountygo:password@localhost:5432/bountygo

# Redis (local)
REDIS_URL=redis://localhost:6379/0

# Development Testing
DEV_TEST_TOKEN=dev-bountygo-test-token-2024
DEV_TEST_USER_EMAIL=dev@bountygo.com
DEV_TEST_USER_NICKNAME=开发测试用户

# PPIO (use your actual API key)
PPIO_API_KEY=sk_your_actual_ppio_api_key_here

# URL Agent (relaxed settings for development)
CONTENT_EXTRACTION_TIMEOUT=30
USE_PROXY=false
VERIFY_SSL=true
```

### Development Testing

The development environment supports a special test token for API testing without Google OAuth:

1. Set `DEV_TEST_TOKEN` in your `.env` file
2. Use the token in API requests:
   ```bash
   curl -H "Authorization: Bearer dev-bountygo-test-token-2024" \
        http://localhost:8000/api/v1/users/me
   ```

### Local Database Setup

1. **Install PostgreSQL:**
   ```bash
   # Ubuntu/Debian
   sudo apt install postgresql postgresql-contrib
   
   # macOS
   brew install postgresql
   ```

2. **Create database and user:**
   ```sql
   sudo -u postgres psql
   CREATE DATABASE bountygo;
   CREATE USER bountygo WITH PASSWORD 'password';
   GRANT ALL PRIVILEGES ON DATABASE bountygo TO bountygo;
   ```

3. **Run migrations:**
   ```bash
   alembic upgrade head
   ```

## Production Configuration

### Security Requirements

```bash
# Application
DEBUG=false
ENVIRONMENT=production

# Security (CRITICAL)
SECRET_KEY=your-super-secure-secret-key-at-least-32-characters-long-and-random

# Remove development settings
# DEV_TEST_TOKEN=  # Must be empty or removed

# Database (with SSL)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db?sslmode=require
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis (with authentication)
REDIS_URL=redis://default:secure-password@redis-host:6379/0
REDIS_CACHE_TTL=1800  # 30 minutes

# CORS (restrict to your domains)
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com

# Rate limiting (adjust based on needs)
RATE_LIMIT_PER_MINUTE=100
```

### Performance Optimization

```bash
# Database connections
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Caching
REDIS_CACHE_TTL=1800
CONTENT_CACHE_TTL=7200  # 2 hours

# PPIO settings
PPIO_TIMEOUT=90
PPIO_MAX_RETRIES=5

# Content extraction
CONTENT_EXTRACTION_TIMEOUT=60
MAX_CONTENT_LENGTH=100000
```

### SSL and Security

```bash
# Always verify SSL in production
VERIFY_SSL=true

# Use secure database connections
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?sslmode=require

# Secure Redis connection
REDIS_URL=rediss://default:password@host:6380/0  # Note: rediss:// for SSL
```

## PPIO Model Configuration

### Supported Models (by Priority)

1. **qwen/qwen3-coder-480b-a35b-instruct** (Recommended)
   - Optimized for programming tasks
   - Supports function calling and structured outputs
   - Best for code analysis and task extraction

2. **moonshotai/kimi-k2-instruct**
   - Good cost-performance ratio
   - Strong Chinese language understanding
   - Supports function calling

3. **deepseek/deepseek-r1-0528**
   - Strong reasoning capabilities
   - Good for complex analysis tasks

4. **qwen/qwen3-235b-a22b-instruct-2507**
   - Large parameter model
   - High capability but higher cost

### Model Configuration Examples

```bash
# For code-heavy tasks (recommended)
PPIO_MODEL_NAME=qwen/qwen3-coder-480b-a35b-instruct
PPIO_MAX_TOKENS=4000
PPIO_TEMPERATURE=0.1

# For general tasks with cost optimization
PPIO_MODEL_NAME=moonshotai/kimi-k2-instruct
PPIO_MAX_TOKENS=3000
PPIO_TEMPERATURE=0.2

# For complex reasoning tasks
PPIO_MODEL_NAME=deepseek/deepseek-r1-0528
PPIO_MAX_TOKENS=6000
PPIO_TEMPERATURE=0.1
```

### Getting PPIO API Key

1. Visit [PPIO API Console](https://api.ppinfra.com/)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (starts with `sk_`)

## URL Agent Configuration

### Content Extraction Settings

```bash
# Basic settings
CONTENT_EXTRACTION_TIMEOUT=30  # Seconds to wait for page load
MAX_CONTENT_LENGTH=50000       # Maximum content size in bytes
USER_AGENT=BountyGo-URLAgent/1.0

# Network settings
MAX_REDIRECTS=5                # Maximum HTTP redirects to follow
VERIFY_SSL=true               # Verify SSL certificates

# Caching (recommended for production)
ENABLE_CONTENT_CACHE=true
CONTENT_CACHE_TTL=3600        # Cache content for 1 hour
```

### Proxy Configuration

If you need to use a proxy for web requests:

```bash
USE_PROXY=true
PROXY_URL=http://proxy-server:8080

# Or with authentication
PROXY_URL=http://username:password@proxy-server:8080

# SOCKS proxy
PROXY_URL=socks5://proxy-server:1080
```

### Performance Tuning

```bash
# For high-traffic environments
CONTENT_EXTRACTION_TIMEOUT=60
MAX_CONTENT_LENGTH=100000
CONTENT_CACHE_TTL=7200        # 2 hours

# For low-latency requirements
CONTENT_EXTRACTION_TIMEOUT=15
MAX_CONTENT_LENGTH=25000
CONTENT_CACHE_TTL=1800        # 30 minutes
```

## Configuration Validation

### Automatic Validation

The application includes built-in configuration validation:

```bash
# Run full validation
python scripts/validate_config.py

# Skip connection tests (faster)
python scripts/validate_config.py --skip-connections

# Skip PPIO API test
python scripts/validate_config.py --skip-ppio
```

### Manual Validation

You can also validate configuration programmatically:

```python
from app.core.config import settings

# Validate PPIO configuration
ppio_results = settings.validate_ppio_config()
print(f"PPIO valid: {ppio_results['valid']}")

# Validate URL agent configuration
agent_results = settings.validate_url_agent_config()
print(f"Agent valid: {agent_results['valid']}")

# Validate production settings
if settings.is_production():
    prod_results = settings.validate_production_config()
    print(f"Production valid: {prod_results['valid']}")
```

## Troubleshooting

### Common Issues

#### 1. PPIO API Key Issues

**Error:** `PPIO_API_KEY must start with 'sk_'`
**Solution:** Ensure your API key is correctly copied from PPIO console

**Error:** `PPIO API connection failed`
**Solutions:**
- Verify API key is valid and active
- Check network connectivity
- Verify PPIO_BASE_URL is correct
- Check if model name is supported

#### 2. Database Connection Issues

**Error:** `Database connection failed`
**Solutions:**
- Verify DATABASE_URL format
- Check database server is running
- Verify credentials and permissions
- For production, ensure SSL configuration

#### 3. Redis Connection Issues

**Error:** `Redis connection failed`
**Solutions:**
- Verify REDIS_URL format
- Check Redis server is running
- Verify authentication credentials
- Check network connectivity

#### 4. Content Extraction Issues

**Error:** `Content extraction timeout`
**Solutions:**
- Increase `CONTENT_EXTRACTION_TIMEOUT`
- Check network connectivity
- Configure proxy if needed
- Verify target website accessibility

#### 5. SSL Certificate Issues

**Error:** `SSL certificate verification failed`
**Solutions:**
- Set `VERIFY_SSL=false` for development only
- Update system certificates
- Configure proxy with SSL support

### Environment-Specific Issues

#### Development

- Use `DEBUG=true` for detailed error messages
- Enable `DEV_TEST_TOKEN` for easier API testing
- Use local database and Redis for faster development

#### Production

- Ensure `DEBUG=false` for security
- Use strong `SECRET_KEY` (32+ characters)
- Remove `DEV_TEST_TOKEN`
- Configure proper SSL certificates
- Use connection pooling for better performance

### Getting Help

1. **Check logs:** Application logs provide detailed error information
2. **Run validation:** Use `python scripts/validate_config.py` for diagnosis
3. **Check documentation:** Refer to API documentation in `docs/`
4. **Environment summary:** Use `settings.get_config_summary()` for debugging

### Configuration Templates

#### Minimal Development .env

```bash
SECRET_KEY=dev-secret-key-at-least-32-characters-long
DATABASE_URL=postgresql+asyncpg://bountygo:password@localhost:5432/bountygo
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
PPIO_API_KEY=sk_your_ppio_api_key_here
DEV_TEST_TOKEN=dev-bountygo-test-token-2024
```

#### Production .env Template

```bash
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=your-super-secure-random-secret-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db?sslmode=require
DATABASE_POOL_SIZE=20
REDIS_URL=rediss://default:password@host:6380/0
REDIS_CACHE_TTL=1800
GOOGLE_CLIENT_ID=your-production-google-client-id
GOOGLE_CLIENT_SECRET=your-production-google-client-secret
PPIO_API_KEY=sk_your_production_ppio_api_key
PPIO_TIMEOUT=90
CONTENT_CACHE_TTL=7200
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
RATE_LIMIT_PER_MINUTE=100
VERIFY_SSL=true
```