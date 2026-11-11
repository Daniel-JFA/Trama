"""create_creator_growth_and_niche_tables

Revision ID: ae8e56481230
Revises: e2df3eeb0964
Create Date: 2026-11-11 17:35:13.568258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae8e56481230'
down_revision: Union[str, Sequence[str], None] = 'e2df3eeb0964'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include creator growth and niche tracking tables."""
    op.create_table(
        'accounts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.String(length=64), nullable=False),
        sa.Column('platform', sa.String(length=32), nullable=False),
        sa.Column('external_id', sa.String(length=128), nullable=False),
        sa.Column('handle', sa.String(length=128), nullable=False),
        sa.Column('display_name', sa.String(length=128), nullable=False, server_default=''),
        sa.Column('is_owned', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('platform', 'external_id', 'project_id', name='uq_accounts_platform_ext_proj'),
    )
    op.create_index('idx_accounts_project_id', 'accounts', ['project_id'], unique=False)
    op.create_index('idx_accounts_platform', 'accounts', ['platform'], unique=False)
    op.create_index('idx_accounts_external_id', 'accounts', ['external_id'], unique=False)
    op.create_index('idx_accounts_handle', 'accounts', ['handle'], unique=False)
    op.create_index('idx_accounts_proj_platform', 'accounts', ['project_id', 'platform'], unique=False)

    op.create_table(
        'account_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('taken_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('followers', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('following', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('posts_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_views', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('engagement_rate', sa.Float(), nullable=True),
        sa.Column('raw', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_acc_snapshots_account_id', 'account_snapshots', ['account_id'], unique=False)
    op.create_index('idx_acc_snapshots_taken_at', 'account_snapshots', ['taken_at'], unique=False)
    op.create_index('idx_acc_snapshots_account_taken', 'account_snapshots', ['account_id', 'taken_at'], unique=False)

    op.create_table(
        'post_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('external_post_id', sa.String(length=128), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('taken_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('views', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('likes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('shares', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('hashtags', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_post_snapshots_account_id', 'post_snapshots', ['account_id'], unique=False)
    op.create_index('idx_post_snapshots_published_at', 'post_snapshots', ['published_at'], unique=False)
    op.create_index('idx_post_snapshots_account_pub', 'post_snapshots', ['account_id', 'published_at'], unique=False)
    op.create_index('idx_post_snapshots_acc_ext', 'post_snapshots', ['account_id', 'external_post_id'], unique=False)

    op.create_table(
        'oauth_credentials',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('access_token_enc', sa.Text(), nullable=False),
        sa.Column('refresh_token_enc', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_oauth_credentials_account_id', 'oauth_credentials', ['account_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema removing creator growth and niche tracking tables."""
    op.drop_table('oauth_credentials')
    op.drop_table('post_snapshots')
    op.drop_table('account_snapshots')
    op.drop_table('accounts')
