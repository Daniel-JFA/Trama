"""add_account_analytics_daily_and_post_analytics_columns

Revision ID: 065a57b9d092
Revises: ae8e56481230
Create Date: 2026-11-12 17:23:33.573423

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '065a57b9d092'
down_revision: Union[str, Sequence[str], None] = 'ae8e56481230'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema adding account_analytics_daily table and analytical metrics to post_snapshots."""
    op.create_table(
        'account_analytics_daily',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.String(length=32), nullable=False),
        sa.Column('views', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('watch_time_minutes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('average_view_duration_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_view_percentage', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('subscribers_gained', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('subscribers_lost', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('net_subscribers', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('impressions', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('ctr', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('traffic_sources', sa.JSON(), nullable=True),
        sa.Column('demographics', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id', 'date', name='uq_acc_analytics_daily_account_date'),
    )
    op.create_index(
        'idx_acc_analytics_daily_account_date',
        'account_analytics_daily',
        ['account_id', 'date'],
        unique=False,
    )

    with op.batch_alter_table('post_snapshots') as batch_op:
        batch_op.add_column(sa.Column('impressions', sa.BigInteger(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('ctr', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('subscribers_gained', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('subscribers_lost', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('retention_rate_pct', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('average_view_duration_seconds', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema removing analytical additions."""
    with op.batch_alter_table('post_snapshots') as batch_op:
        batch_op.drop_column('average_view_duration_seconds')
        batch_op.drop_column('retention_rate_pct')
        batch_op.drop_column('subscribers_lost')
        batch_op.drop_column('subscribers_gained')
        batch_op.drop_column('ctr')
        batch_op.drop_column('impressions')

    op.drop_index('idx_acc_analytics_daily_account_date', table_name='account_analytics_daily')
    op.drop_table('account_analytics_daily')
