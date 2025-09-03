"""Create image series tables

Revision ID: create_image_series_tables
Revises: d33d352c02de
Create Date: 2025-09-01 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_image_series_tables'
down_revision = 'd33d352c02de'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 이미지 히스토리 테이블에 시리즈 관련 컬럼 추가
    op.add_column('image_history', sa.Column('series_id', postgresql.UUID(as_uuid=True), nullable=True, comment='시리즈 그룹 ID'))
    op.add_column('image_history', sa.Column('series_index', sa.Integer(), nullable=True, comment='시리즈 내 순서 번호 (1부터 시작)'))
    op.add_column('image_history', sa.Column('series_type', sa.String(length=30), nullable=True, comment='시리즈 타입 (webtoon, instagram, brand, educational, story)'))
    op.add_column('image_history', sa.Column('series_metadata', sa.JSON(), default=dict, comment='시리즈별 메타데이터'))
    
    # 이미지 히스토리 인덱스 추가
    op.create_index(op.f('ix_image_history_series_id'), 'image_history', ['series_id'], unique=False)
    
    # 이미지 히스토리 제약조건 추가
    op.create_check_constraint('valid_series_type', 'image_history', "series_type IS NULL OR series_type IN ('webtoon', 'instagram', 'brand', 'educational', 'story', 'custom')")
    op.create_check_constraint('valid_series_index', 'image_history', "series_index IS NULL OR series_index >= 1")
    
    # 이미지 시리즈 테이블 생성
    op.create_table('image_series',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='시리즈 고유 ID'),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False, comment='대화 ID'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='사용자 ID'),
        sa.Column('title', sa.String(length=255), nullable=False, comment='시리즈 제목'),
        sa.Column('description', sa.Text(), nullable=True, comment='시리즈 설명'),
        sa.Column('series_type', sa.String(length=30), nullable=False, comment='시리즈 타입 (webtoon, instagram, brand, educational, story)'),
        sa.Column('template_config', sa.JSON(), default=dict, comment='템플릿 설정 (레이아웃, 스타일 등)'),
        sa.Column('target_count', sa.Integer(), nullable=False, default=4, comment='목표 이미지 개수'),
        sa.Column('current_count', sa.Integer(), default=0, comment='현재 생성된 이미지 개수'),
        sa.Column('completion_status', sa.String(length=20), default='planning', comment='완성 상태 (planning, generating, completed, failed)'),
        sa.Column('base_style', sa.String(length=50), nullable=False, comment='기본 스타일'),
        sa.Column('consistency_prompt', sa.Text(), nullable=True, comment='일관성 유지용 공통 프롬프트'),
        sa.Column('character_descriptions', sa.JSON(), default=dict, comment='캐릭터 설명 딕셔너리'),
        sa.Column('scene_continuity', sa.JSON(), default=dict, comment='씬 연속성 정보'),
        sa.Column('base_prompt_template', sa.Text(), nullable=True, comment='기본 프롬프트 템플릿'),
        sa.Column('prompt_variables', sa.JSON(), default=dict, comment='프롬프트 변수 딕셔너리'),
        sa.Column('chaining_strategy', sa.String(length=30), default='sequential', comment='체이닝 전략 (sequential, parallel, reference_based)'),
        sa.Column('generation_queue', sa.JSON(), default=list, comment='생성 대기열 (프롬프트 리스트)'),
        sa.Column('generation_progress', sa.JSON(), default=dict, comment='생성 진행 상황'),
        sa.Column('failed_generations', sa.JSON(), default=list, comment='실패한 생성 기록'),
        sa.Column('tags', sa.JSON(), default=list, comment='시리즈 태그'),
        sa.Column('settings', sa.JSON(), default=dict, comment='추가 설정'),
        sa.Column('is_public', sa.Boolean(), default=False, comment='공개 여부'),
        sa.Column('is_active', sa.Boolean(), default=True, comment='활성 상태'),
        sa.Column('is_template', sa.Boolean(), default=False, comment='템플릿으로 사용 가능 여부'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('target_count >= 1 AND target_count <= 50', name='valid_target_count'),
        sa.CheckConstraint('current_count >= 0', name='valid_current_count'),
        sa.CheckConstraint("completion_status IN ('planning', 'generating', 'completed', 'failed', 'paused')", name='valid_completion_status'),
        sa.CheckConstraint("series_type IN ('webtoon', 'instagram', 'brand', 'educational', 'story', 'custom')", name='valid_series_type_series'),
        sa.CheckConstraint("chaining_strategy IN ('sequential', 'parallel', 'reference_based', 'hybrid')", name='valid_chaining_strategy')
    )
    
    # 이미지 시리즈 인덱스 추가
    op.create_index(op.f('ix_image_series_id'), 'image_series', ['id'], unique=False)
    op.create_index(op.f('ix_image_series_conversation_id'), 'image_series', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_image_series_user_id'), 'image_series', ['user_id'], unique=False)
    
    # 시리즈 템플릿 테이블 생성
    op.create_table('series_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='템플릿 고유 ID'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True, comment='템플릿 생성자 ID'),
        sa.Column('name', sa.String(length=255), nullable=False, comment='템플릿 이름'),
        sa.Column('description', sa.Text(), nullable=True, comment='템플릿 설명'),
        sa.Column('series_type', sa.String(length=30), nullable=False, comment='시리즈 타입'),
        sa.Column('category', sa.String(length=50), nullable=True, comment='템플릿 카테고리'),
        sa.Column('template_config', sa.JSON(), nullable=False, comment='템플릿 설정'),
        sa.Column('default_target_count', sa.Integer(), default=4, comment='기본 목표 개수'),
        sa.Column('recommended_style', sa.String(length=50), default='realistic', comment='추천 스타일'),
        sa.Column('prompt_templates', sa.JSON(), default=list, comment='프롬프트 템플릿 리스트'),
        sa.Column('consistency_rules', sa.JSON(), default=dict, comment='일관성 규칙'),
        sa.Column('tags', sa.JSON(), default=list, comment='템플릿 태그'),
        sa.Column('usage_count', sa.Integer(), default=0, comment='사용 횟수'),
        sa.Column('rating', sa.Integer(), default=0, comment='평점 (0-5)'),
        sa.Column('is_active', sa.Boolean(), default=True, comment='활성 상태'),
        sa.Column('is_featured', sa.Boolean(), default=False, comment='추천 템플릿 여부'),
        sa.Column('is_public', sa.Boolean(), default=True, comment='공개 여부'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('default_target_count >= 1 AND default_target_count <= 50', name='valid_default_target_count'),
        sa.CheckConstraint('rating >= 0 AND rating <= 5', name='valid_rating'),
        sa.CheckConstraint('usage_count >= 0', name='valid_usage_count'),
        sa.CheckConstraint("series_type IN ('webtoon', 'instagram', 'brand', 'educational', 'story', 'custom')", name='valid_template_series_type')
    )
    
    # 시리즈 템플릿 인덱스 추가
    op.create_index(op.f('ix_series_templates_id'), 'series_templates', ['id'], unique=False)
    
    # 이미지 히스토리에 시리즈 외래키 추가
    op.create_foreign_key(None, 'image_history', 'image_series', ['series_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    # 외래키 제약조건 삭제
    op.drop_constraint(None, 'image_history', type_='foreignkey')
    
    # 시리즈 템플릿 테이블 삭제
    op.drop_index(op.f('ix_series_templates_id'), table_name='series_templates')
    op.drop_table('series_templates')
    
    # 이미지 시리즈 테이블 삭제
    op.drop_index(op.f('ix_image_series_user_id'), table_name='image_series')
    op.drop_index(op.f('ix_image_series_conversation_id'), table_name='image_series')
    op.drop_index(op.f('ix_image_series_id'), table_name='image_series')
    op.drop_table('image_series')
    
    # 이미지 히스토리 제약조건 삭제
    op.drop_constraint('valid_series_index', 'image_history', type_='check')
    op.drop_constraint('valid_series_type', 'image_history', type_='check')
    
    # 이미지 히스토리 인덱스 삭제
    op.drop_index(op.f('ix_image_history_series_id'), table_name='image_history')
    
    # 이미지 히스토리 컬럼 삭제
    op.drop_column('image_history', 'series_metadata')
    op.drop_column('image_history', 'series_type')
    op.drop_column('image_history', 'series_index')
    op.drop_column('image_history', 'series_id')