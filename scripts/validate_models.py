#!/usr/bin/env python3
"""
Model validation script - validates models without database connection
"""
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent))

import logging
from sqlalchemy import inspect
from app.models import (
    Base, User, UserWallet, RefreshToken,
    Tag, UserTagProfile,
    Task, TaskTag, Todo, Message, TaskView
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_models():
    """Validate all database models"""
    logger.info("🔍 Validating database models...")
    
    models = [
        User, UserWallet, RefreshToken,
        Tag, UserTagProfile,
        Task, TaskTag, Todo, Message, TaskView
    ]
    
    try:
        for model in models:
            # Check if model has required attributes
            assert hasattr(model, '__tablename__'), f"{model.__name__} missing __tablename__"
            assert hasattr(model, '__table__'), f"{model.__name__} missing __table__"
            
            # Check table structure
            table = model.__table__
            logger.info(f"✅ {model.__name__} -> {table.name}")
            
            # List columns
            for column in table.columns:
                logger.info(f"   - {column.name}: {column.type}")
            
            # List foreign keys
            for fk in table.foreign_keys:
                logger.info(f"   FK: {fk.parent.name} -> {fk.column}")
            
            # List indexes
            for index in table.indexes:
                logger.info(f"   IDX: {index.name} on {[col.name for col in index.columns]}")
            
            logger.info("")
        
        logger.info("✅ All models validated successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Model validation failed: {e}")
        return False


def validate_relationships():
    """Validate model relationships"""
    logger.info("🔗 Validating model relationships...")
    
    try:
        # Test User relationships
        user_relationships = inspect(User).relationships
        expected_user_rels = ['wallets', 'tag_profiles', 'sponsored_tasks', 'todos', 'messages', 'task_views', 'refresh_tokens']
        
        for rel_name in expected_user_rels:
            assert rel_name in user_relationships, f"User missing relationship: {rel_name}"
            logger.info(f"✅ User.{rel_name}")
        
        # Test Task relationships
        task_relationships = inspect(Task).relationships
        expected_task_rels = ['sponsor', 'task_tags', 'todos', 'messages', 'task_views']
        
        for rel_name in expected_task_rels:
            assert rel_name in task_relationships, f"Task missing relationship: {rel_name}"
            logger.info(f"✅ Task.{rel_name}")
        
        # Test Tag relationships
        tag_relationships = inspect(Tag).relationships
        expected_tag_rels = ['user_profiles', 'task_tags']
        
        for rel_name in expected_tag_rels:
            assert rel_name in tag_relationships, f"Tag missing relationship: {rel_name}"
            logger.info(f"✅ Tag.{rel_name}")
        
        logger.info("✅ All relationships validated successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Relationship validation failed: {e}")
        return False


def validate_schemas():
    """Validate Pydantic schemas"""
    logger.info("📋 Validating Pydantic schemas...")
    
    try:
        from app.schemas import (
            User as UserSchema, UserCreate, UserUpdate,
            Tag as TagSchema, TagCreate, TagUpdate,
            Task as TaskSchema, TaskCreate, TaskUpdate,
            Todo, TodoCreate, Message, MessageCreate
        )
        
        schemas = [
            UserSchema, UserCreate, UserUpdate,
            TagSchema, TagCreate, TagUpdate,
            TaskSchema, TaskCreate, TaskUpdate,
            Todo, TodoCreate, Message, MessageCreate
        ]
        
        for schema in schemas:
            # Check if schema has required attributes
            assert hasattr(schema, 'model_fields') or hasattr(schema, '__fields__'), f"{schema.__name__} missing fields"
            logger.info(f"✅ {schema.__name__}")
        
        logger.info("✅ All schemas validated successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema validation failed: {e}")
        return False


def main():
    """Main validation function"""
    logger.info("🚀 Starting model validation...")
    
    success = True
    
    # Validate models
    if not validate_models():
        success = False
    
    # Validate relationships
    if not validate_relationships():
        success = False
    
    # Validate schemas
    if not validate_schemas():
        success = False
    
    if success:
        logger.info("🎉 All validations passed!")
        return 0
    else:
        logger.error("❌ Some validations failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())