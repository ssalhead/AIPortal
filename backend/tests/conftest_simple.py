"""
간단한 테스트 설정 및 픽스처 - 복잡한 의존성 제거
"""

import pytest
import asyncio
from typing import Generator
from unittest.mock import Mock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base


# 테스트용 인메모리 데이터베이스 설정
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """테스트용 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def db_session():
    """테스트용 데이터베이스 세션"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# 테스트 헬퍼 함수들
class TestHelpers:
    @staticmethod
    def create_test_feedback(session, **kwargs):
        """테스트용 피드백 생성"""
        from app.db.models.feedback import MessageFeedback, FeedbackType, FeedbackCategory
        
        feedback_data = {
            "message_id": "test-message-id",
            "user_id": "test-user-id",
            "feedback_type": FeedbackType.THUMBS,
            "is_positive": True,
            "category": FeedbackCategory.OVERALL
        }
        feedback_data.update(kwargs)
        
        feedback = MessageFeedback(**feedback_data)
        session.add(feedback)
        session.commit()
        session.refresh(feedback)
        return feedback


@pytest.fixture
def test_helpers():
    """테스트 헬퍼 클래스"""
    return TestHelpers


@pytest.fixture
def sample_feedback_data():
    """샘플 피드백 데이터"""
    return {
        "message_id": "test-message-id",
        "user_id": "test-user-id",
        "feedback_type": "thumbs",
        "is_positive": True,
        "category": "overall",
        "conversation_id": "test-conversation-id",
        "agent_type": "none",
        "model_used": "claude-3",
        "user_query": "테스트 질문",
        "ai_response": "테스트 응답"
    }


# 테스트 마커 설정
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.db = pytest.mark.db