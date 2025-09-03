"""Add image history table only

Revision ID: d33d352c02de
Revises: 8f680a7ebc8b
Create Date: 2025-08-27 15:54:43.014227

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd33d352c02de'
down_revision: Union[str, None] = 'bbbbaa244cd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """단순화된 image_history 테이블만 생성"""
    
    # 1. 메인 image_history 테이블 생성 (without foreign key constraints to avoid issues)
    op.create_table('image_history',
        # 기본 식별자
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        
        # 이미지 콘텐츠 정보
        sa.Column('prompt', sa.Text, nullable=False),
        sa.Column('image_urls', postgresql.JSON, nullable=False, comment='생성된 이미지 URL 배열'),
        sa.Column('primary_image_url', sa.Text, nullable=False, comment='메인 표시 이미지 URL'),
        
        # 생성 파라미터
        sa.Column('style', sa.String(50), nullable=False, default='realistic'),
        sa.Column('size', sa.String(20), nullable=False, default='1024x1024'),
        sa.Column('generation_params', postgresql.JSON, default={}),
        
        # 이미지 진화 관계 (단순화)
        sa.Column('parent_image_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('evolution_type', sa.String(20), nullable=True, comment='기반/변형/확장 등'),
        
        # 보안 메타데이터
        sa.Column('prompt_hash', sa.String(64), nullable=False, comment='중복 방지용 프롬프트 해시'),
        sa.Column('content_filter_passed', sa.Boolean, default=False),
        sa.Column('safety_score', sa.Float, default=0.0),
        
        # 파일 정보
        sa.Column('file_size_bytes', sa.Integer, default=0),
        sa.Column('mime_type', sa.String(50), default='image/png'),
        
        # 상태 관리
        sa.Column('status', sa.String(20), nullable=False, default='completed'),
        sa.Column('is_deleted', sa.Boolean, default=False),
        sa.Column('is_selected', sa.Boolean, default=False, comment='conversation 내에서 선택된 이미지 여부'),
        
        # 타임스탬프
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        
        # 체크 제약조건 (보안)
        sa.CheckConstraint('safety_score >= 0.0 AND safety_score <= 1.0', name='valid_safety_score'),
        sa.CheckConstraint('file_size_bytes >= 0', name='valid_file_size'),
        sa.CheckConstraint("status IN ('generating', 'completed', 'failed')", name='valid_status'),
        sa.CheckConstraint("evolution_type IS NULL OR evolution_type IN ('based_on', 'variation', 'extension', 'modification')", name='valid_evolution_type'),
    )
    
    # 2. 성능 최적화 인덱스
    op.create_index('idx_image_history_conversation_user', 'image_history', ['conversation_id', 'user_id'])
    op.create_index('idx_image_history_user_created', 'image_history', ['user_id', 'created_at'])
    op.create_index('idx_image_history_parent_child', 'image_history', ['parent_image_id'], postgresql_where=sa.text('parent_image_id IS NOT NULL'))
    op.create_index('idx_image_history_selected', 'image_history', ['conversation_id', 'is_selected'], postgresql_where=sa.text('is_selected = true'))
    op.create_index('idx_image_history_active', 'image_history', ['conversation_id', 'created_at'], postgresql_where=sa.text('is_deleted = false'))


def downgrade() -> None:
    """image_history 테이블 삭제"""
    
    # 인덱스 삭제
    op.drop_index('idx_image_history_active', table_name='image_history')
    op.drop_index('idx_image_history_selected', table_name='image_history')
    op.drop_index('idx_image_history_parent_child', table_name='image_history')
    op.drop_index('idx_image_history_user_created', table_name='image_history')
    op.drop_index('idx_image_history_conversation_user', table_name='image_history')
    
    # 테이블 삭제
    op.drop_table('image_history')