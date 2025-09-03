"""Add Canvas request-based fields to image_history

Revision ID: 3ad8f5041abd
Revises: d33d352c02de
Create Date: 2025-08-27 17:59:02.394657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3ad8f5041abd'
down_revision: Union[str, None] = 'd33d352c02de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new Canvas-related fields to image_history table
    
    # Add canvas_id field
    op.add_column('image_history', sa.Column('canvas_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Canvas 요청별 고유 ID'))
    
    # Add canvas_version field (nullable first, then update and make NOT NULL)
    op.add_column('image_history', sa.Column('canvas_version', sa.Integer(), nullable=True, comment='Canvas 내 버전 번호'))
    
    # Update existing rows with default value for canvas_version
    op.execute("UPDATE image_history SET canvas_version = 1 WHERE canvas_version IS NULL")
    
    # Make canvas_version NOT NULL
    op.alter_column('image_history', 'canvas_version', nullable=False, server_default='1')
    
    # Add edit_mode field (nullable first, then update and make NOT NULL)
    op.add_column('image_history', sa.Column('edit_mode', sa.String(length=20), nullable=True, comment='생성 모드 (CREATE/EDIT)'))
    
    # Update existing rows with default value for edit_mode
    op.execute("UPDATE image_history SET edit_mode = 'CREATE' WHERE edit_mode IS NULL")
    
    # Make edit_mode NOT NULL
    op.alter_column('image_history', 'edit_mode', nullable=False, server_default='CREATE')
    
    # Add reference_image_id field (foreign key to image_history.id)
    op.add_column('image_history', sa.Column('reference_image_id', postgresql.UUID(as_uuid=True), nullable=True, comment='편집 시 참조 이미지 ID'))
    
    # Create indexes
    op.create_index('ix_image_history_canvas_id', 'image_history', ['canvas_id'], unique=False)
    
    # Add foreign key constraint for reference_image_id
    op.create_foreign_key('fk_image_history_reference_image_id', 'image_history', 'image_history', ['reference_image_id'], ['id'], ondelete='SET NULL')
    
    # Add check constraints
    op.create_check_constraint('valid_edit_mode', 'image_history', "edit_mode IN ('CREATE', 'EDIT')")
    op.create_check_constraint('valid_canvas_version', 'image_history', 'canvas_version >= 1')
    
    # Update evolution_type constraint to include new 'reference_edit' type
    op.drop_constraint('valid_evolution_type', 'image_history', type_='check')
    op.create_check_constraint('valid_evolution_type', 'image_history', 
                             "evolution_type IS NULL OR evolution_type IN ('based_on', 'variation', 'extension', 'modification', 'reference_edit')")


def downgrade() -> None:
    # Remove check constraints
    op.drop_constraint('valid_evolution_type', 'image_history', type_='check')
    op.drop_constraint('valid_canvas_version', 'image_history', type_='check')
    op.drop_constraint('valid_edit_mode', 'image_history', type_='check')
    
    # Remove foreign key constraint
    op.drop_constraint('fk_image_history_reference_image_id', 'image_history', type_='foreignkey')
    
    # Remove indexes
    op.drop_index('ix_image_history_canvas_id', 'image_history')
    
    # Remove server defaults before dropping columns
    op.alter_column('image_history', 'edit_mode', server_default=None)
    op.alter_column('image_history', 'canvas_version', server_default=None)
    
    # Remove columns
    op.drop_column('image_history', 'reference_image_id')
    op.drop_column('image_history', 'edit_mode')
    op.drop_column('image_history', 'canvas_version')
    op.drop_column('image_history', 'canvas_id')
    
    # Restore original evolution_type constraint
    op.create_check_constraint('valid_evolution_type', 'image_history', 
                             "evolution_type IS NULL OR evolution_type IN ('based_on', 'variation', 'extension', 'modification')")