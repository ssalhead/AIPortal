"""
간단한 모델 테스트 - 복잡한 의존성 없이 시작
"""

import pytest
from datetime import datetime
import uuid

from app.db.models.feedback import FeedbackType, FeedbackCategory, MessageFeedback


@pytest.mark.unit
class TestFeedbackModels:
    """피드백 모델 테스트"""
    
    def test_feedback_type_enum(self):
        """FeedbackType 열거형 테스트"""
        assert FeedbackType.THUMBS.value == "thumbs"
        assert FeedbackType.RATING.value == "rating"
        assert FeedbackType.DETAILED.value == "detailed"
    
    def test_feedback_category_enum(self):
        """FeedbackCategory 열거형 테스트"""
        assert FeedbackCategory.OVERALL.value == "overall"
        assert FeedbackCategory.ACCURACY.value == "accuracy"
        assert FeedbackCategory.HELPFULNESS.value == "helpfulness"
        assert FeedbackCategory.CLARITY.value == "clarity"
        assert FeedbackCategory.COMPLETENESS.value == "completeness"
        assert FeedbackCategory.SPEED.value == "speed"
    
    def test_message_feedback_creation(self):
        """MessageFeedback 모델 생성 테스트"""
        feedback = MessageFeedback(
            message_id="test-message-123",
            user_id="test-user-456",
            feedback_type=FeedbackType.THUMBS,
            is_positive=True,
            category=FeedbackCategory.OVERALL
        )
        
        assert feedback.message_id == "test-message-123"
        assert feedback.user_id == "test-user-456"
        assert feedback.feedback_type == FeedbackType.THUMBS
        assert feedback.is_positive is True
        assert feedback.category == FeedbackCategory.OVERALL
        # 모델 인스턴스만 생성하므로 DB 기본값은 설정되지 않음
        assert feedback.message_id == "test-message-123"
        assert feedback.user_id == "test-user-456"
    
    def test_message_feedback_rating(self):
        """별점 피드백 모델 테스트"""
        feedback = MessageFeedback(
            message_id="test-message-123",
            user_id="test-user-456", 
            feedback_type=FeedbackType.RATING,
            rating=4.5,
            category=FeedbackCategory.ACCURACY
        )
        
        assert feedback.feedback_type == FeedbackType.RATING
        assert feedback.rating == 4.5
        assert feedback.is_positive is None  # 별점에서는 is_positive 사용 안함
    
    def test_message_feedback_detailed(self):
        """상세 피드백 모델 테스트"""
        feedback = MessageFeedback(
            message_id="test-message-123",
            user_id="test-user-456",
            feedback_type=FeedbackType.DETAILED,
            title="개선 제안",
            content="응답이 더 구체적이었으면 좋겠습니다.",
            suggestions="예시를 추가해주세요.",
            category=FeedbackCategory.COMPLETENESS,
            rating=3.0
        )
        
        assert feedback.feedback_type == FeedbackType.DETAILED
        assert feedback.title == "개선 제안"
        assert feedback.content == "응답이 더 구체적이었으면 좋겠습니다."
        assert feedback.suggestions == "예시를 추가해주세요."
        assert feedback.rating == 3.0