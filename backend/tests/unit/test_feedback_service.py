"""
FeedbackService 단위 테스트
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.services.feedback_service import FeedbackService
from app.db.models.feedback import MessageFeedback, FeedbackAnalytics, UserFeedbackProfile
from app.core.exceptions import NotFoundError, ValidationError


@pytest.mark.unit
@pytest.mark.db
class TestFeedbackService:
    """FeedbackService 테스트 클래스"""
    
    def test_submit_feedback_thumbs_success(self, feedback_service, sample_feedback_data):
        """썸즈 피드백 제출 성공 테스트"""
        # Given
        feedback_data = sample_feedback_data
        
        # When
        result = feedback_service.submit_feedback(feedback_data)
        
        # Then
        assert result["message"] == "피드백이 성공적으로 제출되었습니다."
        assert "feedback_id" in result
        
        # 저장된 피드백 확인
        saved_feedback = feedback_service.get_message_feedback(feedback_data["message_id"])
        assert saved_feedback is not None
        assert saved_feedback.feedback_type == "thumbs"
        assert saved_feedback.is_positive == feedback_data["is_positive"]
        assert saved_feedback.category == feedback_data["category"]
    
    def test_submit_feedback_rating_success(self, feedback_service, sample_feedback_data):
        """별점 피드백 제출 성공 테스트"""
        # Given
        feedback_data = sample_feedback_data.copy()
        feedback_data.update({
            "feedback_type": "rating",
            "rating": 4.5,
            "is_positive": None
        })
        
        # When
        result = feedback_service.submit_feedback(feedback_data)
        
        # Then
        assert result["message"] == "피드백이 성공적으로 제출되었습니다."
        
        # 저장된 피드백 확인
        saved_feedback = feedback_service.get_message_feedback(feedback_data["message_id"])
        assert saved_feedback.feedback_type == "rating"
        assert saved_feedback.rating == 4.5
    
    def test_submit_feedback_detailed_success(self, feedback_service, sample_feedback_data):
        """상세 피드백 제출 성공 테스트"""
        # Given
        feedback_data = sample_feedback_data.copy()
        feedback_data.update({
            "feedback_type": "detailed",
            "title": "개선 제안",
            "content": "응답이 좀 더 구체적이었으면 좋겠습니다.",
            "suggestions": "예시를 추가해주세요.",
            "rating": 3.0
        })
        
        # When
        result = feedback_service.submit_feedback(feedback_data)
        
        # Then
        assert result["message"] == "피드백이 성공적으로 제출되었습니다."
        
        # 저장된 피드백 확인
        saved_feedback = feedback_service.get_message_feedback(feedback_data["message_id"])
        assert saved_feedback.feedback_type == "detailed"
        assert saved_feedback.title == "개선 제안"
        assert saved_feedback.content == "응답이 좀 더 구체적이었으면 좋겠습니다."
        assert saved_feedback.suggestions == "예시를 추가해주세요."
    
    def test_submit_feedback_validation_error(self, feedback_service):
        """피드백 제출 시 유효성 검사 실패 테스트"""
        # Given
        invalid_data = {
            "message_id": "",  # 빈 메시지 ID
            "feedback_type": "thumbs"
        }
        
        # When & Then
        with pytest.raises(ValidationError):
            feedback_service.submit_feedback(invalid_data)
    
    def test_submit_feedback_duplicate_update(self, feedback_service, sample_feedback_data):
        """중복 피드백 제출 시 업데이트 테스트"""
        # Given
        feedback_data = sample_feedback_data
        
        # 첫 번째 피드백 제출
        feedback_service.submit_feedback(feedback_data)
        
        # 같은 메시지에 대한 다른 피드백
        updated_data = feedback_data.copy()
        updated_data["is_positive"] = False
        
        # When
        result = feedback_service.submit_feedback(updated_data)
        
        # Then
        assert result["message"] == "피드백이 성공적으로 업데이트되었습니다."
        
        # 업데이트된 피드백 확인
        saved_feedback = feedback_service.get_message_feedback(feedback_data["message_id"])
        assert saved_feedback.is_positive == False
    
    def test_get_message_feedback_not_found(self, feedback_service):
        """존재하지 않는 메시지 피드백 조회 테스트"""
        # Given
        non_existent_id = str(uuid.uuid4())
        
        # When
        result = feedback_service.get_message_feedback(non_existent_id)
        
        # Then
        assert result is None
    
    def test_get_user_feedbacks_pagination(self, feedback_service, db_session, test_helpers):
        """사용자 피드백 목록 페이지네이션 테스트"""
        # Given
        # 여러 피드백 생성
        for i in range(5):
            feedback_data = {
                "message_id": f"message-{i}",
                "feedback_type": "thumbs",
                "is_positive": i % 2 == 0,
                "category": "overall"
            }
            feedback_service.submit_feedback(feedback_data)
        
        # When
        result = feedback_service.get_user_feedbacks(limit=2, skip=1)
        
        # Then
        assert len(result["feedbacks"]) == 2
        assert result["total"] == 5
        assert result["skip"] == 1
        assert result["limit"] == 2
    
    def test_get_user_feedbacks_filter_by_type(self, feedback_service):
        """피드백 타입별 필터링 테스트"""
        # Given
        # 다양한 타입의 피드백 생성
        thumbs_data = {
            "message_id": "msg-thumbs",
            "feedback_type": "thumbs",
            "is_positive": True,
            "category": "overall"
        }
        rating_data = {
            "message_id": "msg-rating",
            "feedback_type": "rating",
            "rating": 4.0,
            "category": "overall"
        }
        
        feedback_service.submit_feedback(thumbs_data)
        feedback_service.submit_feedback(rating_data)
        
        # When
        result = feedback_service.get_user_feedbacks(feedback_type="thumbs")
        
        # Then
        assert len(result["feedbacks"]) == 1
        assert result["feedbacks"][0].feedback_type == "thumbs"
    
    def test_get_feedback_statistics(self, feedback_service):
        """피드백 통계 조회 테스트"""
        # Given
        # 다양한 피드백 생성
        feedbacks = [
            {"message_id": "msg-1", "feedback_type": "thumbs", "is_positive": True, "category": "overall"},
            {"message_id": "msg-2", "feedback_type": "thumbs", "is_positive": False, "category": "overall"},
            {"message_id": "msg-3", "feedback_type": "rating", "rating": 4.0, "category": "accuracy"},
            {"message_id": "msg-4", "feedback_type": "rating", "rating": 5.0, "category": "helpfulness"}
        ]
        
        for feedback_data in feedbacks:
            feedback_service.submit_feedback(feedback_data)
        
        # When
        stats = feedback_service.get_statistics(days=30)
        
        # Then
        assert stats.total_feedback_count == 4
        assert stats.thumbs_up_count == 1
        assert stats.thumbs_down_count == 1
        assert stats.average_rating > 0
        assert stats.rating_distribution is not None
        assert stats.category_breakdown is not None
    
    def test_get_recent_feedbacks(self, feedback_service):
        """최근 피드백 조회 테스트"""
        # Given
        feedbacks = [
            {"message_id": "msg-1", "feedback_type": "thumbs", "is_positive": False, "category": "overall"},
            {"message_id": "msg-2", "feedback_type": "detailed", "title": "문제", "content": "응답이 부정확함", "category": "accuracy"}
        ]
        
        for feedback_data in feedbacks:
            feedback_service.submit_feedback(feedback_data)
        
        # When
        result = feedback_service.get_recent_feedbacks(limit=10, hours=24)
        
        # Then
        assert len(result["feedbacks"]) == 2
        assert result["filters"]["hours"] == 24
    
    def test_get_recent_feedbacks_priority_only(self, feedback_service):
        """우선순위 피드백만 조회 테스트"""
        # Given
        # 낮은 평점의 피드백 (우선순위 높음)
        priority_feedback = {
            "message_id": "msg-priority",
            "feedback_type": "rating",
            "rating": 1.0,
            "category": "overall"
        }
        
        # 높은 평점의 피드백 (우선순위 낮음)
        normal_feedback = {
            "message_id": "msg-normal",
            "feedback_type": "rating", 
            "rating": 5.0,
            "category": "overall"
        }
        
        feedback_service.submit_feedback(priority_feedback)
        feedback_service.submit_feedback(normal_feedback)
        
        # When
        result = feedback_service.get_recent_feedbacks(priority_only=True)
        
        # Then
        # 우선순위 피드백만 반환되어야 함
        assert len(result["feedbacks"]) == 1
        assert result["feedbacks"][0].message_id == "msg-priority"
    
    def test_calculate_priority_score(self, feedback_service):
        """우선순위 점수 계산 테스트"""
        # Given
        low_rating_feedback = MessageFeedback(
            message_id="test-1",
            feedback_type="rating",
            rating=1.0,
            category="overall"
        )
        
        high_rating_feedback = MessageFeedback(
            message_id="test-2", 
            feedback_type="rating",
            rating=5.0,
            category="overall"
        )
        
        negative_thumbs_feedback = MessageFeedback(
            message_id="test-3",
            feedback_type="thumbs",
            is_positive=False,
            category="overall"
        )
        
        # When
        low_score = feedback_service._calculate_priority_score(low_rating_feedback)
        high_score = feedback_service._calculate_priority_score(high_rating_feedback)
        negative_score = feedback_service._calculate_priority_score(negative_thumbs_feedback)
        
        # Then
        assert low_score > high_score  # 낮은 평점이 높은 우선순위
        assert negative_score > high_score  # 부정적 피드백이 높은 우선순위
    
    def test_get_feedback_categories(self, feedback_service):
        """피드백 카테고리 조회 테스트"""
        # When
        categories = feedback_service.get_categories()
        
        # Then
        assert len(categories) > 0
        assert any(cat.category == "overall" for cat in categories)
        assert any(cat.category == "accuracy" for cat in categories)
        assert any(cat.category == "helpfulness" for cat in categories)
    
    def test_get_feedback_types(self, feedback_service):
        """피드백 타입 조회 테스트"""
        # When
        types = feedback_service.get_types()
        
        # Then
        assert len(types) > 0
        assert any(t.feedback_type == "thumbs" for t in types)
        assert any(t.feedback_type == "rating" for t in types)
        assert any(t.feedback_type == "detailed" for t in types)
    
    @patch('app.services.feedback_service.datetime')
    def test_generate_daily_analytics(self, mock_datetime, feedback_service):
        """일간 분석 데이터 생성 테스트"""
        # Given
        test_date = datetime(2024, 1, 15)
        mock_datetime.now.return_value = test_date
        mock_datetime.strptime.return_value = test_date
        
        # 테스트 피드백 생성
        feedback_data = {
            "message_id": "msg-analytics",
            "feedback_type": "thumbs",
            "is_positive": True,
            "category": "overall"
        }
        feedback_service.submit_feedback(feedback_data)
        
        # When
        result = feedback_service.generate_daily_analytics(test_date.strftime("%Y-%m-%d"))
        
        # Then
        assert result["message"] == "분석 데이터가 생성되었습니다."
        assert "analysis_date" in result
    
    def test_user_feedback_profile_creation(self, feedback_service, db_session):
        """사용자 피드백 프로파일 생성 테스트"""
        # Given
        user_id = str(uuid.uuid4())
        
        # 사용자의 여러 피드백 제출
        feedbacks = [
            {"message_id": "msg-1", "feedback_type": "thumbs", "is_positive": True, "category": "overall"},
            {"message_id": "msg-2", "feedback_type": "rating", "rating": 4.0, "category": "accuracy"},
            {"message_id": "msg-3", "feedback_type": "thumbs", "is_positive": False, "category": "helpfulness"}
        ]
        
        for feedback_data in feedbacks:
            feedback_service.submit_feedback(feedback_data)
        
        # When
        profile = feedback_service.get_user_profile()
        
        # Then
        assert profile is not None
        assert profile.total_feedbacks >= 3
        assert profile.thumbs_up_count >= 1
        assert profile.thumbs_down_count >= 1
        assert profile.average_rating > 0
    
    def test_feedback_impact_on_statistics(self, feedback_service):
        """피드백이 통계에 미치는 영향 테스트"""
        # Given - 초기 통계
        initial_stats = feedback_service.get_statistics(days=30)
        
        # When - 새 피드백 추가
        feedback_data = {
            "message_id": "impact-test",
            "feedback_type": "rating",
            "rating": 3.0,
            "category": "overall"
        }
        feedback_service.submit_feedback(feedback_data)
        
        # Then - 통계 변화 확인
        updated_stats = feedback_service.get_statistics(days=30)
        assert updated_stats.total_feedback_count == initial_stats.total_feedback_count + 1