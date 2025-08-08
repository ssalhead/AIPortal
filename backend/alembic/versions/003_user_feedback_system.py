"""User feedback system

Revision ID: 003_user_feedback_system
Revises: 002_conversation_history_optimization
Create Date: 2025-01-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = '003_user_feedback_system'
down_revision = '002_conversation_history_optimization'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """사용자 피드백 시스템 테이블 생성"""
    
    # FeedbackType enum 생성
    feedback_type_enum = sa.Enum(
        'RATING', 'THUMBS', 'DETAILED',
        name='feedbacktype'
    )
    feedback_type_enum.create(op.get_bind())
    
    # FeedbackCategory enum 생성
    feedback_category_enum = sa.Enum(
        'ACCURACY', 'HELPFULNESS', 'CLARITY', 'COMPLETENESS', 
        'SPEED', 'RELEVANCE', 'OVERALL',
        name='feedbackcategory'
    )
    feedback_category_enum.create(op.get_bind())
    
    # 메시지 피드백 테이블 생성
    op.create_table('message_feedbacks',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', sa.String(), nullable=False),
        sa.Column('conversation_id', UUID(as_uuid=True), nullable=True),
        sa.Column('feedback_type', feedback_type_enum, nullable=False),
        sa.Column('category', feedback_category_enum, nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('is_positive', sa.Boolean(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('suggestions', sa.Text(), nullable=True),
        sa.Column('agent_type', sa.String(length=50), nullable=True),
        sa.Column('model_used', sa.String(length=50), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('user_query', sa.Text(), nullable=True),
        sa.Column('ai_response_preview', sa.Text(), nullable=True),
        sa.Column('metadata_', JSON(), nullable=True),
        sa.Column('tags', JSON(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('is_reviewed', sa.Boolean(), nullable=False),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 피드백 분석 통계 테이블 생성
    op.create_table('feedback_analytics',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('period_type', sa.String(length=20), nullable=False),
        sa.Column('total_feedbacks', sa.Integer(), nullable=False),
        sa.Column('positive_count', sa.Integer(), nullable=False),
        sa.Column('negative_count', sa.Integer(), nullable=False),
        sa.Column('neutral_count', sa.Integer(), nullable=False),
        sa.Column('avg_rating', sa.Float(), nullable=True),
        sa.Column('rating_distribution', JSON(), nullable=True),
        sa.Column('category_stats', JSON(), nullable=True),
        sa.Column('agent_stats', JSON(), nullable=True),
        sa.Column('model_stats', JSON(), nullable=True),
        sa.Column('avg_response_time_ms', sa.Float(), nullable=True),
        sa.Column('response_time_satisfaction', sa.Float(), nullable=True),
        sa.Column('common_issues', JSON(), nullable=True),
        sa.Column('positive_highlights', JSON(), nullable=True),
        sa.Column('improvement_suggestions', JSON(), nullable=True),
        sa.Column('metadata_', JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 사용자 피드백 프로파일 테이블 생성
    op.create_table('user_feedback_profiles',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('total_feedbacks', sa.Integer(), nullable=False),
        sa.Column('positive_feedbacks', sa.Integer(), nullable=False),
        sa.Column('negative_feedbacks', sa.Integer(), nullable=False),
        sa.Column('detailed_feedbacks', sa.Integer(), nullable=False),
        sa.Column('avg_rating_given', sa.Float(), nullable=True),
        sa.Column('preferred_agents', JSON(), nullable=True),
        sa.Column('preferred_models', JSON(), nullable=True),
        sa.Column('feedback_frequency', sa.Float(), nullable=True),
        sa.Column('most_active_hours', JSON(), nullable=True),
        sa.Column('common_categories', JSON(), nullable=True),
        sa.Column('helpful_feedback_count', sa.Integer(), nullable=False),
        sa.Column('feedback_quality_score', sa.Float(), nullable=True),
        sa.Column('top_concerns', JSON(), nullable=True),
        sa.Column('satisfaction_trend', JSON(), nullable=True),
        sa.Column('metadata_', JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_feedback_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    
    # 인덱스 생성
    op.create_index('idx_message_feedbacks_user_id', 'message_feedbacks', ['user_id'])
    op.create_index('idx_message_feedbacks_message_id', 'message_feedbacks', ['message_id'])
    op.create_index('idx_message_feedbacks_conversation_id', 'message_feedbacks', ['conversation_id'])
    op.create_index('idx_message_feedbacks_created_at', 'message_feedbacks', ['created_at'])
    op.create_index('idx_message_feedbacks_agent_type', 'message_feedbacks', ['agent_type'])
    op.create_index('idx_message_feedbacks_model_used', 'message_feedbacks', ['model_used'])
    op.create_index('idx_message_feedbacks_rating', 'message_feedbacks', ['rating'])
    op.create_index('idx_message_feedbacks_is_positive', 'message_feedbacks', ['is_positive'])
    op.create_index('idx_message_feedbacks_priority', 'message_feedbacks', ['priority'])
    op.create_index('idx_message_feedbacks_is_reviewed', 'message_feedbacks', ['is_reviewed'])
    
    op.create_index('idx_feedback_analytics_date', 'feedback_analytics', ['date'])
    op.create_index('idx_feedback_analytics_period_type', 'feedback_analytics', ['period_type'])
    
    op.create_index('idx_user_feedback_profiles_user_id', 'user_feedback_profiles', ['user_id'])
    op.create_index('idx_user_feedback_profiles_last_feedback_at', 'user_feedback_profiles', ['last_feedback_at'])
    
    # 복합 인덱스 생성
    op.create_index('idx_message_feedbacks_user_date', 'message_feedbacks', ['user_id', 'created_at'])
    op.create_index('idx_message_feedbacks_agent_rating', 'message_feedbacks', ['agent_type', 'rating'])
    op.create_index('idx_message_feedbacks_model_rating', 'message_feedbacks', ['model_used', 'rating'])
    op.create_index('idx_feedback_analytics_date_period', 'feedback_analytics', ['date', 'period_type'])


def downgrade() -> None:
    """피드백 시스템 테이블 제거"""
    
    # 인덱스 제거
    op.drop_index('idx_feedback_analytics_date_period', table_name='feedback_analytics')
    op.drop_index('idx_message_feedbacks_model_rating', table_name='message_feedbacks')
    op.drop_index('idx_message_feedbacks_agent_rating', table_name='message_feedbacks')
    op.drop_index('idx_message_feedbacks_user_date', table_name='message_feedbacks')
    
    op.drop_index('idx_user_feedback_profiles_last_feedback_at', table_name='user_feedback_profiles')
    op.drop_index('idx_user_feedback_profiles_user_id', table_name='user_feedback_profiles')
    
    op.drop_index('idx_feedback_analytics_period_type', table_name='feedback_analytics')
    op.drop_index('idx_feedback_analytics_date', table_name='feedback_analytics')
    
    op.drop_index('idx_message_feedbacks_is_reviewed', table_name='message_feedbacks')
    op.drop_index('idx_message_feedbacks_priority', table_name='message_feedbacks')
    op.drop_index('idx_message_feedbacks_is_positive', table_name='message_feedbacks')
    op.drop_index('idx_message_feedbacks_rating', table_name='message_feedbacks')
    op.drop_index('idx_message_feedbacks_model_used', table_name='message_feedbacks')
    op.drop_index('idx_message_feedbacks_agent_type', table_name='message_feedbacks')
    op.drop_index('idx_message_feedbacks_created_at', table_name='message_feedbacks')
    op.drop_index('idx_message_feedbacks_conversation_id', table_name='message_feedbacks')
    op.drop_index('idx_message_feedbacks_message_id', table_name='message_feedbacks')
    op.drop_index('idx_message_feedbacks_user_id', table_name='message_feedbacks')
    
    # 테이블 제거
    op.drop_table('user_feedback_profiles')
    op.drop_table('feedback_analytics')
    op.drop_table('message_feedbacks')
    
    # Enum 제거
    op.execute('DROP TYPE feedbackcategory')
    op.execute('DROP TYPE feedbacktype')