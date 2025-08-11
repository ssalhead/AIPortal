"""워크스페이스 협업 기능 추가

Revision ID: 005_workspace_collaboration
Revises: 004_file_management_system
Create Date: 2025-01-08 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_workspace_collaboration'
down_revision = '004_file_management_system'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """워크스페이스 협업 기능을 위한 테이블 추가"""
    
    # 워크스페이스 협업자 테이블
    op.create_table('workspace_collaborators',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_level', sa.Enum('OWNER', 'EDITOR', 'VIEWER', 'COMMENTER', name='permissionlevel'), nullable=True),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspace_collaborators_workspace_id'), 'workspace_collaborators', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_workspace_collaborators_user_id'), 'workspace_collaborators', ['user_id'], unique=False)
    
    # 아티팩트 버전 관리 테이블
    op.create_table('artifact_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('diff_data', sa.JSON(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['artifact_id'], ['artifacts.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_artifact_versions_artifact_id'), 'artifact_versions', ['artifact_id'], unique=False)
    op.create_index(op.f('ix_artifact_versions_version_number'), 'artifact_versions', ['artifact_id', 'version_number'], unique=True)
    
    # 워크스페이스 활동 로그 테이블
    op.create_table('workspace_activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=True),
        sa.Column('target_id', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata_', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspace_activities_workspace_id'), 'workspace_activities', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_workspace_activities_created_at'), 'workspace_activities', ['created_at'], unique=False)
    
    # 기존 아티팩트 타입에 새로운 값 추가
    op.execute("ALTER TYPE artifacttype ADD VALUE 'mindmap'")
    op.execute("ALTER TYPE artifacttype ADD VALUE 'whiteboard'")


def downgrade() -> None:
    """워크스페이스 협업 기능 롤백"""
    
    op.drop_index(op.f('ix_workspace_activities_created_at'), table_name='workspace_activities')
    op.drop_index(op.f('ix_workspace_activities_workspace_id'), table_name='workspace_activities')
    op.drop_table('workspace_activities')
    
    op.drop_index(op.f('ix_artifact_versions_version_number'), table_name='artifact_versions')
    op.drop_index(op.f('ix_artifact_versions_artifact_id'), table_name='artifact_versions')
    op.drop_table('artifact_versions')
    
    op.drop_index(op.f('ix_workspace_collaborators_user_id'), table_name='workspace_collaborators')
    op.drop_index(op.f('ix_workspace_collaborators_workspace_id'), table_name='workspace_collaborators')
    op.drop_table('workspace_collaborators')
    
    # Enum 값 제거는 복잡하므로 생략 (필요시 별도 마이그레이션)