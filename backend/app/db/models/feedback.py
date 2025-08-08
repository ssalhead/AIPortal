"""
사용자 피드백 모델
"""

from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.db.base import Base


class FeedbackType(enum.Enum):
    """피드백 타입"""
    RATING = "rating"           # 별점 평가
    THUMBS = "thumbs"           # 좋아요/싫어요
    DETAILED = "detailed"       # 상세 피드백


class FeedbackCategory(enum.Enum):
    """피드백 카테고리"""
    ACCURACY = "accuracy"           # 정확성
    HELPFULNESS = "helpfulness"     # 도움이 됨
    CLARITY = "clarity"             # 명확성
    COMPLETENESS = "completeness"   # 완성도
    SPEED = "speed"                 # 응답 속도
    RELEVANCE = "relevance"         # 관련성
    OVERALL = "overall"             # 전체 평가


class MessageFeedback(Base):
    """메시지 피드백"""
    __tablename__ = "message_feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    message_id = Column(String, nullable=False, index=True)  # 프론트엔드 메시지 ID
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True, index=True)
    
    # 피드백 기본 정보
    feedback_type = Column(SQLEnum(FeedbackType), nullable=False)
    category = Column(SQLEnum(FeedbackCategory), nullable=False, default=FeedbackCategory.OVERALL)
    
    # 평가 데이터
    rating = Column(Integer, nullable=True)  # 1-5 또는 1-10 점수
    is_positive = Column(Boolean, nullable=True)  # 좋아요/싫어요
    
    # 상세 피드백
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)  # 개선 제안
    
    # 메타데이터
    agent_type = Column(String(50), nullable=True)  # 어떤 에이전트가 생성한 응답인지
    model_used = Column(String(50), nullable=True)  # 사용된 모델
    response_time_ms = Column(Integer, nullable=True)  # 응답 시간
    
    # 컨텍스트 정보
    user_query = Column(Text, nullable=True)  # 사용자 질문
    ai_response_preview = Column(Text, nullable=True)  # AI 응답 일부 (프라이버시 고려)
    
    # 추가 메타데이터
    metadata_ = Column(JSON, nullable=True, default=dict)
    
    # 태그 및 분류
    tags = Column(JSON, nullable=True, default=list)  # 피드백 태그
    priority = Column(Integer, nullable=False, default=1)  # 1: 낮음, 5: 높음
    
    # 처리 상태
    is_reviewed = Column(Boolean, nullable=False, default=False)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    
    # 시간 정보
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    conversation = relationship("Conversation", back_populates="feedbacks")

    def __repr__(self):
        return f"<MessageFeedback(id={self.id}, user_id={self.user_id}, type={self.feedback_type.value})>"


class FeedbackAnalytics(Base):
    """피드백 분석 통계"""
    __tablename__ = "feedback_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 분석 기간
    date = Column(DateTime, nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # "daily", "weekly", "monthly"
    
    # 기본 통계
    total_feedbacks = Column(Integer, nullable=False, default=0)
    positive_count = Column(Integer, nullable=False, default=0)
    negative_count = Column(Integer, nullable=False, default=0)
    neutral_count = Column(Integer, nullable=False, default=0)
    
    # 평점 통계
    avg_rating = Column(Float, nullable=True)
    rating_distribution = Column(JSON, nullable=True)  # {1: count, 2: count, ...}
    
    # 카테고리별 통계
    category_stats = Column(JSON, nullable=True)  # {category: {avg_rating, count, ...}}
    
    # 에이전트별 통계
    agent_stats = Column(JSON, nullable=True)  # {agent_type: {avg_rating, count, ...}}
    
    # 모델별 통계
    model_stats = Column(JSON, nullable=True)  # {model: {avg_rating, count, ...}}
    
    # 응답 시간 통계
    avg_response_time_ms = Column(Float, nullable=True)
    response_time_satisfaction = Column(Float, nullable=True)  # 응답 시간 만족도
    
    # 주요 키워드 및 이슈
    common_issues = Column(JSON, nullable=True)  # 자주 언급되는 문제점
    positive_highlights = Column(JSON, nullable=True)  # 자주 언급되는 장점
    improvement_suggestions = Column(JSON, nullable=True)  # 개선 제안 요약
    
    # 메타데이터
    metadata_ = Column(JSON, nullable=True, default=dict)
    
    # 시간 정보
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<FeedbackAnalytics(date={self.date}, period={self.period_type}, total={self.total_feedbacks})>"


class UserFeedbackProfile(Base):
    """사용자 피드백 프로파일"""
    __tablename__ = "user_feedback_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    
    # 피드백 활동 통계
    total_feedbacks = Column(Integer, nullable=False, default=0)
    positive_feedbacks = Column(Integer, nullable=False, default=0)
    negative_feedbacks = Column(Integer, nullable=False, default=0)
    detailed_feedbacks = Column(Integer, nullable=False, default=0)
    
    # 평균 평점
    avg_rating_given = Column(Float, nullable=True)
    
    # 선호도 분석
    preferred_agents = Column(JSON, nullable=True)  # 선호하는 에이전트 타입
    preferred_models = Column(JSON, nullable=True)  # 선호하는 모델
    
    # 피드백 패턴
    feedback_frequency = Column(Float, nullable=True)  # 피드백 빈도 (일주일 평균)
    most_active_hours = Column(JSON, nullable=True)  # 가장 활발한 시간대
    common_categories = Column(JSON, nullable=True)  # 자주 평가하는 카테고리
    
    # 품질 지표
    helpful_feedback_count = Column(Integer, nullable=False, default=0)  # 도움이 된 피드백 수
    feedback_quality_score = Column(Float, nullable=True)  # 피드백 품질 점수
    
    # 인사이트
    top_concerns = Column(JSON, nullable=True)  # 주요 관심사
    satisfaction_trend = Column(JSON, nullable=True)  # 만족도 트렌드
    
    # 메타데이터
    metadata_ = Column(JSON, nullable=True, default=dict)
    
    # 시간 정보
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_feedback_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<UserFeedbackProfile(user_id={self.user_id}, total_feedbacks={self.total_feedbacks})>"