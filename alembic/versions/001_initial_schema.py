"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2025-01-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('google_id', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('nickname', sa.String(length=100), nullable=False),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('google_id')
    )
    
    # Create tags table
    op.create_table('tags',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create user_wallets table
    op.create_table('user_wallets',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('wallet_address', sa.String(length=42), nullable=False),
        sa.Column('wallet_type', sa.String(length=20), nullable=False, server_default='ethereum'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('wallet_address')
    )
    
    # Create refresh_tokens table
    op.create_table('refresh_tokens',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    
    # Create tasks table
    op.create_table('tasks',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reward', sa.DECIMAL(precision=18, scale=6), nullable=True),
        sa.Column('reward_currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sponsor_id', sa.BigInteger(), nullable=False),
        sa.Column('external_link', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('join_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('has_escrow', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('escrow_amount', sa.DECIMAL(precision=18, scale=6), nullable=True),
        sa.Column('escrow_token', sa.String(length=42), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sponsor_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_tag_profiles table
    op.create_table('user_tag_profiles',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('tag_id', sa.BigInteger(), nullable=False),
        sa.Column('weight', sa.DECIMAL(precision=5, scale=4), nullable=False, server_default='1.0'),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'tag_id', name='uq_user_tag')
    )
    
    # Create task_tags table
    op.create_table('task_tags',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.BigInteger(), nullable=False),
        sa.Column('tag_id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', 'tag_id', name='uq_task_tag')
    )
    
    # Create todos table
    op.create_table('todos',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('task_id', sa.BigInteger(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('remind_flags', sa.Text(), server_default='{"t_3d": true, "t_1d": true, "ddl_2h": true}', nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'task_id', name='uq_user_task')
    )
    
    # Create messages table
    op.create_table('messages',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create task_views table
    op.create_table('task_views',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('viewed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create performance indexes
    op.create_index('idx_tasks_sponsor_status', 'tasks', ['sponsor_id', 'status'])
    op.create_index('idx_todos_user_active', 'todos', ['user_id', 'is_active'])
    op.create_index('idx_messages_task_created', 'messages', ['task_id', 'created_at'])
    op.create_index('idx_tags_category', 'tags', ['category', 'is_active'])
    op.create_index('idx_tags_name', 'tags', ['name'])
    op.create_index('idx_task_tags_task', 'task_tags', ['task_id'])
    op.create_index('idx_task_tags_tag', 'task_tags', ['tag_id'])
    op.create_index('idx_user_tag_profiles_user', 'user_tag_profiles', ['user_id'])
    op.create_index('idx_user_tag_profiles_tag', 'user_tag_profiles', ['tag_id'])
    op.create_index('idx_task_views_task', 'task_views', ['task_id'])
    op.create_index('idx_task_views_user', 'task_views', ['user_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_task_views_user', table_name='task_views')
    op.drop_index('idx_task_views_task', table_name='task_views')
    op.drop_index('idx_user_tag_profiles_tag', table_name='user_tag_profiles')
    op.drop_index('idx_user_tag_profiles_user', table_name='user_tag_profiles')
    op.drop_index('idx_task_tags_tag', table_name='task_tags')
    op.drop_index('idx_task_tags_task', table_name='task_tags')
    op.drop_index('idx_tags_name', table_name='tags')
    op.drop_index('idx_tags_category', table_name='tags')
    op.drop_index('idx_messages_task_created', table_name='messages')
    op.drop_index('idx_todos_user_active', table_name='todos')
    op.drop_index('idx_tasks_sponsor_status', table_name='tasks')
    
    # Drop tables in reverse order
    op.drop_table('task_views')
    op.drop_table('messages')
    op.drop_table('todos')
    op.drop_table('task_tags')
    op.drop_table('user_tag_profiles')
    op.drop_table('tasks')
    op.drop_table('refresh_tokens')
    op.drop_table('user_wallets')
    op.drop_table('tags')
    op.drop_table('users')