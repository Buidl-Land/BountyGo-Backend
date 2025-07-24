-- BountyGo Database Initialization Script
-- This script sets up the initial database configuration

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create database user for application (if needed)
-- Note: This is handled by environment variables in docker-compose

-- Set timezone
SET timezone = 'UTC';

-- Create initial database schema will be handled by Alembic migrations
-- This file is mainly for extensions and initial setup