"""create_interaction_events_table

Revision ID: e2df3eeb0964
Revises: d032792f8ca2
Create Date: 2026-11-10 21:29:04.872185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2df3eeb0964'
down_revision: Union[str, Sequence[str], None] = 'd032792f8ca2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include interaction_events table."""
    op.create_table(
        'interaction_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.String(length=64), nullable=True),
        sa.Column('actor', sa.String(length=128), nullable=False),
        sa.Column('target', sa.String(length=128), nullable=True),
        sa.Column('timestamp', sa.String(length=64), nullable=False),
        sa.Column('action_type', sa.String(length=32), nullable=False),
        sa.Column('platform', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=True, server_default=''),
        sa.Column('extra_json', sa.Text(), nullable=True, server_default='{}'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_events_actor', 'interaction_events', ['actor'], unique=False)
    op.create_index('idx_events_target', 'interaction_events', ['target'], unique=False)
    op.create_index('idx_events_timestamp', 'interaction_events', ['timestamp'], unique=False)
    op.create_index('idx_events_action_type', 'interaction_events', ['action_type'], unique=False)
    op.create_index('idx_events_platform', 'interaction_events', ['platform'], unique=False)
    op.create_index('idx_events_proj_ts', 'interaction_events', ['project_id', 'timestamp'], unique=False)
    op.create_index('idx_events_actor_target', 'interaction_events', ['actor', 'target'], unique=False)
    op.create_index('idx_events_platform_action', 'interaction_events', ['platform', 'action_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema removing interaction_events table."""
    op.drop_table('interaction_events')
