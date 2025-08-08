"""대화 이력 최적화 인덱스 추가

Revision ID: 002_conversation_history_optimization
Revises: 001_initial_schema
Create Date: 2025-01-08 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_conversation_history_optimization'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """대화 이력 최적화를 위한 인덱스 추가"""
    
    # 1. 사용자별 대화 목록 조회 최적화 (user_id + updated_at DESC)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_user_updated 
        ON conversations(user_id, updated_at DESC)
    """)
    
    # 2. 활성 대화 필터링 최적화 (status + updated_at)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_status_updated 
        ON conversations(status, updated_at DESC) 
        WHERE status = 'active'
    """)
    
    # 3. 대화별 메시지 시간순 조회 최적화 (conversation_id + created_at)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_conversation_time 
        ON messages(conversation_id, created_at ASC)
    """)
    
    # 4. 메시지 전문검색 최적화 (content GIN 인덱스)
    op.execute("""
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_content_search 
        ON messages USING GIN(to_tsvector('korean', content))
    """)
    
    # 5. 영어 전문검색 추가 지원
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_content_search_en 
        ON messages USING GIN(to_tsvector('english', content))
    """)
    
    # 6. 메시지 메타데이터 검색 최적화 (metadata_ GIN 인덱스)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_metadata_search 
        ON messages USING GIN(metadata_)
    """)
    
    # 7. 역할별 메시지 필터링 최적화 (role + created_at)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_role_time 
        ON messages(role, created_at DESC)
    """)
    
    # 8. 사용자 메시지만 빠른 조회 (부분 인덱스)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_user_only 
        ON messages(conversation_id, created_at ASC) 
        WHERE role = 'user'
    """)
    
    # 9. AI 응답만 빠른 조회 (부분 인덱스)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_assistant_only 
        ON messages(conversation_id, created_at ASC) 
        WHERE role = 'assistant'
    """)
    
    # 10. 모델별 성능 분석을 위한 인덱스
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_model_performance 
        ON messages(model, created_at DESC) 
        WHERE model IS NOT NULL AND latency_ms IS NOT NULL
    """)
    
    # 11. 토큰 사용량 분석을 위한 인덱스
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_tokens_analysis 
        ON messages(created_at DESC, tokens_input, tokens_output) 
        WHERE tokens_input IS NOT NULL OR tokens_output IS NOT NULL
    """)


def downgrade() -> None:
    """인덱스 제거"""
    
    # 인덱스 제거 (역순)
    op.execute("DROP INDEX IF EXISTS idx_messages_tokens_analysis")
    op.execute("DROP INDEX IF EXISTS idx_messages_model_performance")
    op.execute("DROP INDEX IF EXISTS idx_messages_assistant_only")
    op.execute("DROP INDEX IF EXISTS idx_messages_user_only")
    op.execute("DROP INDEX IF EXISTS idx_messages_role_time")
    op.execute("DROP INDEX IF EXISTS idx_messages_metadata_search")
    op.execute("DROP INDEX IF EXISTS idx_messages_content_search_en")
    op.execute("DROP INDEX IF EXISTS idx_messages_content_search")
    op.execute("DROP INDEX IF EXISTS idx_messages_conversation_time")
    op.execute("DROP INDEX IF EXISTS idx_conversations_status_updated")
    op.execute("DROP INDEX IF EXISTS idx_conversations_user_updated")