"""Add Canvas share system

Revision ID: 004_add_canvas_share_system
Revises: 3ad8f5041abd
Create Date: 2025-09-01 15:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_add_canvas_share_system'
down_revision: Union[str, None] = '3ad8f5041abd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Canvas 공유 시스템 테이블 생성"""
    
    # canvas_shares 테이블 생성
    op.create_table(
        'canvas_shares',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('share_token', sa.String(32), nullable=False, unique=True),
        sa.Column('canvas_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('creator_id', sa.String(255), nullable=False),
        
        # 공유 설정
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permission', sa.Enum('read_only', 'copy_enabled', 'edit_enabled', name='sharepermission'), nullable=False, default='read_only'),
        sa.Column('visibility', sa.Enum('public', 'private', 'password_protected', 'user_limited', name='sharevisibility'), nullable=False, default='public'),
        sa.Column('duration', sa.Enum('24_hours', '7_days', '30_days', 'unlimited', name='shareduration'), nullable=False, default='7_days'),
        
        # 보안 설정
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('allowed_users', sa.JSON(), nullable=True),
        sa.Column('max_views', sa.Integer(), nullable=True),
        
        # 메타데이터
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('view_count', sa.BigInteger(), nullable=False, default=0),
        sa.Column('download_count', sa.BigInteger(), nullable=False, default=0),
        
        # 만료 시간
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        
        # 소셜 메타데이터
        sa.Column('og_image_url', sa.String(1000), nullable=True),
        sa.Column('preview_image_url', sa.String(1000), nullable=True),
        
        # 시간 정보
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # canvas_share_analytics 테이블 생성
    op.create_table(
        'canvas_share_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('share_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # 방문자 정보
        sa.Column('visitor_ip', sa.String(45), nullable=True),
        sa.Column('visitor_country', sa.String(10), nullable=True),
        sa.Column('visitor_city', sa.String(100), nullable=True),
        sa.Column('visitor_user_agent', sa.Text(), nullable=True),
        sa.Column('visitor_referrer', sa.String(1000), nullable=True),
        
        # 방문 정보
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        
        # 디바이스 정보
        sa.Column('device_type', sa.String(50), nullable=True),
        sa.Column('browser', sa.String(100), nullable=True),
        sa.Column('os', sa.String(100), nullable=True),
        
        # 시간 정보
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        # 외래키 제약조건
        sa.ForeignKeyConstraint(['share_id'], ['canvas_shares.id'], ondelete='CASCADE'),
    )
    
    # canvas_share_reports 테이블 생성
    op.create_table(
        'canvas_share_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('share_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        # 신고 정보
        sa.Column('reporter_ip', sa.String(45), nullable=True),
        sa.Column('reporter_email', sa.String(255), nullable=True),
        sa.Column('reason', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        
        # 처리 정보
        sa.Column('status', sa.String(50), nullable=False, default='pending'),
        sa.Column('reviewed_by', sa.String(255), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        
        # 시간 정보
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        
        # 외래키 제약조건
        sa.ForeignKeyConstraint(['share_id'], ['canvas_shares.id'], ondelete='CASCADE'),
    )
    
    # 인덱스 생성
    op.create_index('ix_canvas_shares_share_token', 'canvas_shares', ['share_token'])
    op.create_index('ix_canvas_shares_canvas_id', 'canvas_shares', ['canvas_id'])
    op.create_index('ix_canvas_shares_creator_id', 'canvas_shares', ['creator_id'])
    op.create_index('ix_canvas_shares_expires_at', 'canvas_shares', ['expires_at'])
    op.create_index('ix_canvas_shares_visibility_active', 'canvas_shares', ['visibility', 'is_active'])
    
    op.create_index('ix_canvas_share_analytics_share_id', 'canvas_share_analytics', ['share_id'])
    op.create_index('ix_canvas_share_analytics_action_created', 'canvas_share_analytics', ['action_type', 'created_at'])
    op.create_index('ix_canvas_share_analytics_visitor_ip', 'canvas_share_analytics', ['visitor_ip'])
    
    op.create_index('ix_canvas_share_reports_share_id', 'canvas_share_reports', ['share_id'])
    op.create_index('ix_canvas_share_reports_status', 'canvas_share_reports', ['status'])
    
    # 제약조건 추가
    op.create_check_constraint(
        'valid_permission', 'canvas_shares',
        "permission IN ('read_only', 'copy_enabled', 'edit_enabled')"
    )
    op.create_check_constraint(
        'valid_visibility', 'canvas_shares',
        "visibility IN ('public', 'private', 'password_protected', 'user_limited')"
    )
    op.create_check_constraint(
        'valid_duration', 'canvas_shares',
        "duration IN ('24_hours', '7_days', '30_days', 'unlimited')"
    )
    op.create_check_constraint(
        'valid_view_count', 'canvas_shares',
        'view_count >= 0'
    )
    op.create_check_constraint(
        'valid_download_count', 'canvas_shares',
        'download_count >= 0'
    )
    op.create_check_constraint(
        'valid_max_views', 'canvas_shares',
        'max_views IS NULL OR max_views > 0'
    )
    
    op.create_check_constraint(
        'valid_action_type', 'canvas_share_analytics',
        "action_type IN ('view', 'download', 'copy', 'share', 'report')"
    )
    op.create_check_constraint(
        'valid_duration_seconds', 'canvas_share_analytics',
        'duration_seconds IS NULL OR duration_seconds >= 0'
    )
    
    op.create_check_constraint(
        'valid_report_reason', 'canvas_share_reports',
        "reason IN ('inappropriate', 'copyright', 'spam', 'harassment', 'violence', 'illegal', 'misinformation', 'other')"
    )
    op.create_check_constraint(
        'valid_report_status', 'canvas_share_reports',
        "status IN ('pending', 'reviewed', 'resolved', 'dismissed')"
    )


def downgrade() -> None:
    """Canvas 공유 시스템 테이블 삭제"""
    
    # 제약조건 삭제
    op.drop_constraint('valid_report_status', 'canvas_share_reports', type_='check')
    op.drop_constraint('valid_report_reason', 'canvas_share_reports', type_='check')
    op.drop_constraint('valid_duration_seconds', 'canvas_share_analytics', type_='check')
    op.drop_constraint('valid_action_type', 'canvas_share_analytics', type_='check')
    op.drop_constraint('valid_max_views', 'canvas_shares', type_='check')
    op.drop_constraint('valid_download_count', 'canvas_shares', type_='check')
    op.drop_constraint('valid_view_count', 'canvas_shares', type_='check')
    op.drop_constraint('valid_duration', 'canvas_shares', type_='check')
    op.drop_constraint('valid_visibility', 'canvas_shares', type_='check')
    op.drop_constraint('valid_permission', 'canvas_shares', type_='check')
    
    # 인덱스 삭제
    op.drop_index('ix_canvas_share_reports_status', 'canvas_share_reports')
    op.drop_index('ix_canvas_share_reports_share_id', 'canvas_share_reports')
    op.drop_index('ix_canvas_share_analytics_visitor_ip', 'canvas_share_analytics')
    op.drop_index('ix_canvas_share_analytics_action_created', 'canvas_share_analytics')
    op.drop_index('ix_canvas_share_analytics_share_id', 'canvas_share_analytics')
    op.drop_index('ix_canvas_shares_visibility_active', 'canvas_shares')
    op.drop_index('ix_canvas_shares_expires_at', 'canvas_shares')
    op.drop_index('ix_canvas_shares_creator_id', 'canvas_shares')
    op.drop_index('ix_canvas_shares_canvas_id', 'canvas_shares')
    op.drop_index('ix_canvas_shares_share_token', 'canvas_shares')
    
    # 테이블 삭제
    op.drop_table('canvas_share_reports')
    op.drop_table('canvas_share_analytics')
    op.drop_table('canvas_shares')
    
    # Enum 타입 삭제
    op.execute('DROP TYPE IF EXISTS sharepermission')
    op.execute('DROP TYPE IF EXISTS sharevisibility')  
    op.execute('DROP TYPE IF EXISTS shareduration')