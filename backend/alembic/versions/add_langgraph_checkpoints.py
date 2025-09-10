"""Add LangGraph checkpoints table

Revision ID: add_langgraph_checkpoints
Revises: d9528217a1b2
Create Date: 2025-09-10 09:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_langgraph_checkpoints'
down_revision: Union[str, None] = 'd9528217a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create LangGraph checkpoints table for state persistence"""
    
    # Create langgraph_checkpoints table
    op.create_table(
        'langgraph_checkpoints',
        sa.Column('thread_id', sa.String(255), nullable=False, primary_key=True, comment='Thread identifier'),
        sa.Column('checkpoint_id', sa.String(255), nullable=False, primary_key=True, comment='Checkpoint identifier'),
        sa.Column('parent_checkpoint_id', sa.String(255), nullable=True, comment='Parent checkpoint ID for versioning'),
        sa.Column('checkpoint_ns', sa.String(255), nullable=False, default='', comment='Checkpoint namespace'),
        sa.Column('checkpoint', postgresql.JSONB, nullable=False, comment='Serialized checkpoint data'),
        sa.Column('metadata', postgresql.JSONB, nullable=True, comment='Checkpoint metadata'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False, comment='Creation timestamp'),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False, comment='Update timestamp')
    )
    
    # Create indexes for performance
    op.create_index('idx_langgraph_checkpoints_thread_id', 'langgraph_checkpoints', ['thread_id'])
    op.create_index('idx_langgraph_checkpoints_checkpoint_ns', 'langgraph_checkpoints', ['checkpoint_ns'])
    op.create_index('idx_langgraph_checkpoints_created_at', 'langgraph_checkpoints', ['created_at'])
    op.create_index('idx_langgraph_checkpoints_parent', 'langgraph_checkpoints', ['parent_checkpoint_id'])


def downgrade() -> None:
    """Drop LangGraph checkpoints table"""
    
    # Drop indexes
    op.drop_index('idx_langgraph_checkpoints_parent', table_name='langgraph_checkpoints')
    op.drop_index('idx_langgraph_checkpoints_created_at', table_name='langgraph_checkpoints')
    op.drop_index('idx_langgraph_checkpoints_checkpoint_ns', table_name='langgraph_checkpoints')
    op.drop_index('idx_langgraph_checkpoints_thread_id', table_name='langgraph_checkpoints')
    
    # Drop table
    op.drop_table('langgraph_checkpoints')