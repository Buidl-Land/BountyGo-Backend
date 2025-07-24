# BountyGo Backend

AI-powered bounty task aggregation and matching platform backend service built with FastAPI, Supabase, and Redis.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### Development Setup

1. **Clone and navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Copy environment configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services with Docker Compose**
   ```bash
   make docker-up
   # or
   docker-compose up -d
   ```

4. **Install dependencies and setup virtual environment**
   ```bash
   make setup
   ```

5. **Run database migrations**
   ```bash
   make migrate
   ```

6. **Verify setup**
   ```bash
   make verify
   ```

7. **Start development server**
   ```bash
   make dev
   ```

The API will be available at `http://localhost:8000`

## 📁 Project Structure

```
backend/
├── app/                    # Application code
│   ├── api/               # API routes and endpoints
│   │   └── v1/           # API version 1
│   ├── core/             # Core utilities and configuration
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   └── services/         # Business logic services
├── alembic/              # Database migrations
├── scripts/              # Utility scripts
├── tests/                # Test files
├── docker-compose.yml    # Development services
├── Dockerfile           # Development container
├── Dockerfile.prod      # Production container
└── requirements.txt     # Python dependencies
```

## 🛠 Development Commands

```bash
# Setup and installation
make setup              # Setup virtual environment and install dependencies
make install           # Install dependencies only
make install-dev       # Install with development dependencies

# Development server
make dev               # Start development server with auto-reload

# Testing and quality
make test              # Run tests with coverage
make lint              # Run linting checks
make format            # Format code with black and isort

# Database operations
make migrate           # Run database migrations
make migrate-create name="description"  # Create new migration
make migrate-downgrade # Downgrade one migration
make reset-db          # Reset database (WARNING: destroys data)

# Docker operations
make docker-build      # Build Docker image
make docker-up         # Start all services
make docker-down       # Stop all services
make docker-logs       # View service logs

# Development tools
make tools-up          # Start pgAdmin and Redis Commander
make tools-down        # Stop development tools

# Verification
make verify            # Verify setup is working correctly

# Cleanup
make clean             # Clean cache files
```

## 🔧 Configuration

### Environment Variables

Key environment variables (see `.env.example` for complete list):

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string  
- `SECRET_KEY`: JWT signing key (min 32 characters)
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `AI_SERVICE_API_KEY`: OpenAI API key

### Database

The application uses PostgreSQL (via Supabase) with async SQLAlchemy. Database migrations are managed with Alembic.

### Caching

Redis is used for caching and rate limiting.

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_main.py -v

# Run with coverage report
pytest --cov=app --cov-report=html
```

## 📊 Development Tools

When running `make tools-up`, you get access to:

- **pgAdmin**: Database management at `http://localhost:8082`
  - Email: `admin@bountygo.com`
  - Password: `admin`

- **Redis Commander**: Redis management at `http://localhost:8081`

## 🚀 Production Deployment

### Using Docker Compose

1. **Create production environment file**
   ```bash
   cp .env.example .env.prod
   # Configure production values
   ```

2. **Deploy with production compose**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Environment-specific Configuration

- **Development**: Uses `docker-compose.yml` with hot reload
- **Production**: Uses `docker-compose.prod.yml` with Gunicorn

## 🏗 Architecture

### Core Components

- **FastAPI**: Modern async web framework
- **SQLAlchemy**: Async ORM for database operations
- **Alembic**: Database migration management
- **Redis**: Caching and rate limiting
- **Pydantic**: Data validation and serialization
- **JWT**: Authentication and authorization

### Key Features

- **Async/await**: Full async support for high performance
- **Rate Limiting**: Redis-based request rate limiting
- **Health Checks**: Comprehensive health monitoring
- **Error Handling**: Structured error responses
- **Security**: JWT authentication, CORS, security headers
- **Logging**: Structured logging with correlation IDs
- **Caching**: Redis-based caching layer

## 🔐 Security

- JWT-based authentication
- Google OAuth 2.0 integration
- Web3 wallet signature verification
- Rate limiting and DDoS protection
- Input validation and sanitization
- Security headers and CORS configuration

## 📝 API Documentation

Once the server is running, visit:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## 🤝 Contributing

1. Follow the existing code style (Black + isort)
2. Write tests for new features
3. Update documentation as needed
4. Run `make lint` and `make test` before committing

## 📄 License

This project is part of the BountyGo platform.