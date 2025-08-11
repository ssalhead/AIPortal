"""파일 관리 시스템 추가

Revision ID: 004_file_management_system
Revises: 003_user_feedback_system
Create Date: 2025-01-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

# revision identifiers, used by Alembic.
revision = '004_file_management_system'
down_revision = '003_user_feedback_system'
branch_labels = None
depends_on = None


def upgrade():
    """파일 관리 시스템 테이블 생성"""
    
    # 파일 메타데이터 테이블
    op.create_table(
        'files',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('file_id', sa.String(50), nullable=False, unique=True),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('original_name', sa.String(255), nullable=False),
        sa.Column('file_size', sa.BigInteger, nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_extension', sa.String(10), nullable=False),
        sa.Column('upload_path', sa.String(500), nullable=False),
        sa.Column('checksum', sa.String(32), nullable=False),  # MD5 해시
        sa.Column('status', sa.String(20), nullable=False, default='uploaded'),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', JSONB, nullable=True, default='[]'),
        sa.Column('processing_result', JSONB, nullable=True),
        sa.Column('metadata_', JSONB, nullable=True, default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Index('idx_files_user_id', 'user_id'),
        sa.Index('idx_files_file_id', 'file_id'),
        sa.Index('idx_files_status', 'status'),
        sa.Index('idx_files_mime_type', 'mime_type'),
        sa.Index('idx_files_created_at', 'created_at'),
    )
    
    # 파일 처리 작업 큐 테이블
    op.create_table(
        'file_processing_jobs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('job_id', sa.String(50), nullable=False, unique=True),
        sa.Column('file_id', sa.String(50), nullable=False),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('processing_type', sa.String(50), nullable=False),  # 'text_extraction', 'ocr', 'embedding', 'auto'
        sa.Column('status', sa.String(20), nullable=False, default='pending'),  # 'pending', 'processing', 'completed', 'failed'
        sa.Column('progress', sa.Integer, nullable=False, default=0),  # 0-100
        sa.Column('result', JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Index('idx_processing_jobs_file_id', 'file_id'),
        sa.Index('idx_processing_jobs_user_id', 'user_id'),
        sa.Index('idx_processing_jobs_status', 'status'),
        sa.Index('idx_processing_jobs_job_id', 'job_id'),
    )
    
    # 파일 공유 및 권한 관리 테이블
    op.create_table(
        'file_shares',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('file_id', sa.String(50), nullable=False),
        sa.Column('owner_user_id', sa.String(50), nullable=False),
        sa.Column('shared_with_user_id', sa.String(50), nullable=False),
        sa.Column('permission', sa.String(20), nullable=False, default='read'),  # 'read', 'write', 'admin'
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('file_id', 'shared_with_user_id', name='unique_file_share'),
        sa.Index('idx_file_shares_file_id', 'file_id'),
        sa.Index('idx_file_shares_shared_user', 'shared_with_user_id'),
        sa.Index('idx_file_shares_owner', 'owner_user_id'),
    )

    # 파일 버전 관리 테이블 (향후 확장용)
    op.create_table(
        'file_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('file_id', sa.String(50), nullable=False),
        sa.Column('version_number', sa.Integer, nullable=False),
        sa.Column('upload_path', sa.String(500), nullable=False),
        sa.Column('checksum', sa.String(32), nullable=False),
        sa.Column('file_size', sa.BigInteger, nullable=False),
        sa.Column('created_by', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('file_id', 'version_number', name='unique_file_version'),
        sa.Index('idx_file_versions_file_id', 'file_id'),
        sa.Index('idx_file_versions_created_by', 'created_by'),
    )


def downgrade():
    """파일 관리 시스템 테이블 삭제"""
    op.drop_table('file_versions')
    op.drop_table('file_shares')
    op.drop_table('file_processing_jobs')
    op.drop_table('files')