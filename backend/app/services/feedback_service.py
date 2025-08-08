"""
피드백 서비스
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.feedback import (
    FeedbackRepository, UserFeedbackProfileRepository, FeedbackAnalyticsRepository
)
from app.db.models.feedback import (
    MessageFeedback, FeedbackType, FeedbackCategory, UserFeedbackProfile
)
from app.services.performance_monitor import performance_monitor
import logging

logger = logging.getLogger(__name__)


class FeedbackService:
    """피드백 서비스"""
    
    async def submit_feedback(
        self,
        session: AsyncSession,
        user_id: str,
        message_id: str,
        feedback_type: str,
        rating: Optional[int] = None,
        is_positive: Optional[bool] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        suggestions: Optional[str] = None,
        category: str = "overall",
        conversation_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        model_used: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        user_query: Optional[str] = None,
        ai_response: Optional[str] = None
    ) -> MessageFeedback:
        """피드백 제출"""
        try:
            feedback_repo = FeedbackRepository(session)
            profile_repo = UserFeedbackProfileRepository(session)
            
            # 입력 검증
            feedback_type_enum = FeedbackType(feedback_type)
            category_enum = FeedbackCategory(category)
            
            # AI 응답 미리보기 생성 (프라이버시 고려)
            ai_response_preview = None
            if ai_response:
                ai_response_preview = ai_response[:500] + "..." if len(ai_response) > 500 else ai_response
            
            # 기존 피드백 확인
            existing_feedback = await feedback_repo.get_message_feedback(message_id, user_id)
            if existing_feedback:
                # 기존 피드백 수정
                updated_feedback = await feedback_repo.update_feedback(
                    feedback_id=str(existing_feedback.id),
                    rating=rating,
                    is_positive=is_positive,
                    title=title,
                    content=content,
                    suggestions=suggestions
                )
                
                # 성능 메트릭 기록
                performance_monitor.record_api_metrics(
                    endpoint="feedback_update",
                    method="PUT",
                    duration_ms=0,
                    status_code=200
                )
                
                return updated_feedback
            
            # 새로운 피드백 생성
            feedback = await feedback_repo.create_feedback(
                user_id=user_id,
                message_id=message_id,
                feedback_type=feedback_type_enum,
                category=category_enum,
                conversation_id=conversation_id,
                rating=rating,
                is_positive=is_positive,
                title=title,
                content=content,
                suggestions=suggestions,
                agent_type=agent_type,
                model_used=model_used,
                response_time_ms=response_time_ms,
                user_query=user_query,
                ai_response_preview=ai_response_preview,
                priority=self._calculate_priority(feedback_type_enum, rating, content)
            )
            
            # 사용자 프로파일 업데이트
            await profile_repo.update_profile_stats(user_id, feedback)
            
            await session.commit()
            
            # 성능 메트릭 기록
            performance_monitor.record_api_metrics(
                endpoint="feedback_submit",
                method="POST",
                duration_ms=0,
                status_code=201
            )
            
            logger.info(f"피드백 제출 완료: user_id={user_id}, message_id={message_id}, type={feedback_type}")
            return feedback
            
        except Exception as e:
            await session.rollback()
            logger.error(f"피드백 제출 실패: {str(e)}")
            raise
    
    def _calculate_priority(
        self, 
        feedback_type: FeedbackType, 
        rating: Optional[int], 
        content: Optional[str]
    ) -> int:
        """피드백 우선순위 계산"""
        priority = 1  # 기본 우선순위
        
        # 피드백 타입에 따른 가중치
        if feedback_type == FeedbackType.DETAILED:
            priority += 2
        elif feedback_type == FeedbackType.RATING:
            priority += 1
        
        # 평점에 따른 가중치 (낮은 평점은 높은 우선순위)
        if rating:
            if rating <= 2:
                priority += 3
            elif rating <= 3:
                priority += 1
        
        # 내용 길이에 따른 가중치
        if content and len(content) > 100:
            priority += 1
        
        return min(priority, 5)  # 최대 5
    
    async def get_user_feedbacks(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 20,
        skip: int = 0,
        feedback_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """사용자 피드백 목록 조회"""
        try:
            feedback_repo = FeedbackRepository(session)
            
            feedback_type_enum = FeedbackType(feedback_type) if feedback_type else None
            category_enum = FeedbackCategory(category) if category else None
            
            feedbacks = await feedback_repo.get_user_feedbacks(
                user_id=user_id,
                limit=limit,
                skip=skip,
                feedback_type=feedback_type_enum,
                category=category_enum
            )
            
            # 피드백을 딕셔너리로 변환
            feedback_list = []
            for feedback in feedbacks:
                feedback_dict = {
                    "id": str(feedback.id),
                    "message_id": feedback.message_id,
                    "conversation_id": str(feedback.conversation_id) if feedback.conversation_id else None,
                    "feedback_type": feedback.feedback_type.value,
                    "category": feedback.category.value,
                    "rating": feedback.rating,
                    "is_positive": feedback.is_positive,
                    "title": feedback.title,
                    "content": feedback.content,
                    "suggestions": feedback.suggestions,
                    "agent_type": feedback.agent_type,
                    "model_used": feedback.model_used,
                    "created_at": feedback.created_at.isoformat(),
                    "updated_at": feedback.updated_at.isoformat()
                }
                feedback_list.append(feedback_dict)
            
            return {
                "feedbacks": feedback_list,
                "total": len(feedback_list),
                "skip": skip,
                "limit": limit
            }
            
        except Exception as e:
            logger.error(f"사용자 피드백 조회 실패: {str(e)}")
            raise
    
    async def get_message_feedback(
        self,
        session: AsyncSession,
        message_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """메시지 피드백 조회"""
        try:
            feedback_repo = FeedbackRepository(session)
            feedback = await feedback_repo.get_message_feedback(message_id, user_id)
            
            if not feedback:
                return None
            
            return {
                "id": str(feedback.id),
                "message_id": feedback.message_id,
                "feedback_type": feedback.feedback_type.value,
                "category": feedback.category.value,
                "rating": feedback.rating,
                "is_positive": feedback.is_positive,
                "title": feedback.title,
                "content": feedback.content,
                "suggestions": feedback.suggestions,
                "created_at": feedback.created_at.isoformat(),
                "updated_at": feedback.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"메시지 피드백 조회 실패: {str(e)}")
            raise
    
    async def get_feedback_statistics(
        self,
        session: AsyncSession,
        days: int = 30,
        agent_type: Optional[str] = None,
        model_used: Optional[str] = None
    ) -> Dict[str, Any]:
        """피드백 통계 조회"""
        try:
            feedback_repo = FeedbackRepository(session)
            
            since_date = datetime.utcnow() - timedelta(days=days)
            stats = await feedback_repo.get_feedback_statistics(
                since_date=since_date,
                agent_type=agent_type,
                model_used=model_used
            )
            
            return {
                "period_days": days,
                "statistics": stats,
                "filters": {
                    "agent_type": agent_type,
                    "model_used": model_used
                }
            }
            
        except Exception as e:
            logger.error(f"피드백 통계 조회 실패: {str(e)}")
            raise
    
    async def get_user_feedback_profile(
        self,
        session: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """사용자 피드백 프로파일 조회"""
        try:
            profile_repo = UserFeedbackProfileRepository(session)
            profile = await profile_repo.get_or_create_profile(user_id)
            
            return {
                "user_id": str(profile.user_id),
                "total_feedbacks": profile.total_feedbacks,
                "positive_feedbacks": profile.positive_feedbacks,
                "negative_feedbacks": profile.negative_feedbacks,
                "detailed_feedbacks": profile.detailed_feedbacks,
                "avg_rating_given": profile.avg_rating_given,
                "preferred_agents": profile.preferred_agents,
                "preferred_models": profile.preferred_models,
                "feedback_frequency": profile.feedback_frequency,
                "most_active_hours": profile.most_active_hours,
                "common_categories": profile.common_categories,
                "helpful_feedback_count": profile.helpful_feedback_count,
                "feedback_quality_score": profile.feedback_quality_score,
                "last_feedback_at": profile.last_feedback_at.isoformat() if profile.last_feedback_at else None,
                "created_at": profile.created_at.isoformat(),
                "updated_at": profile.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"사용자 피드백 프로파일 조회 실패: {str(e)}")
            raise
    
    async def get_recent_feedbacks(
        self,
        session: AsyncSession,
        limit: int = 50,
        hours: int = 24,
        priority_only: bool = False
    ) -> List[Dict[str, Any]]:
        """최근 피드백 조회"""
        try:
            feedback_repo = FeedbackRepository(session)
            feedbacks = await feedback_repo.get_recent_feedbacks(limit=limit, hours=hours)
            
            if priority_only:
                feedbacks = [f for f in feedbacks if f.priority >= 3]
            
            feedback_list = []
            for feedback in feedbacks:
                feedback_dict = {
                    "id": str(feedback.id),
                    "user_id": str(feedback.user_id),
                    "message_id": feedback.message_id,
                    "feedback_type": feedback.feedback_type.value,
                    "category": feedback.category.value,
                    "rating": feedback.rating,
                    "is_positive": feedback.is_positive,
                    "title": feedback.title,
                    "content": feedback.content,
                    "agent_type": feedback.agent_type,
                    "model_used": feedback.model_used,
                    "priority": feedback.priority,
                    "is_reviewed": feedback.is_reviewed,
                    "created_at": feedback.created_at.isoformat()
                }
                feedback_list.append(feedback_dict)
            
            return feedback_list
            
        except Exception as e:
            logger.error(f"최근 피드백 조회 실패: {str(e)}")
            raise
    
    async def generate_daily_analytics(
        self,
        session: AsyncSession,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """일간 분석 데이터 생성"""
        try:
            analytics_repo = FeedbackAnalyticsRepository(session)
            
            if not date:
                date = datetime.utcnow() - timedelta(days=1)  # 어제 데이터
            
            analytics = await analytics_repo.create_daily_analytics(date)
            await session.commit()
            
            return {
                "date": analytics.date.isoformat(),
                "period_type": analytics.period_type,
                "total_feedbacks": analytics.total_feedbacks,
                "positive_count": analytics.positive_count,
                "negative_count": analytics.negative_count,
                "neutral_count": analytics.neutral_count,
                "avg_rating": analytics.avg_rating,
                "rating_distribution": analytics.rating_distribution,
                "category_stats": analytics.category_stats,
                "agent_stats": analytics.agent_stats,
                "avg_response_time_ms": analytics.avg_response_time_ms
            }
            
        except Exception as e:
            await session.rollback()
            logger.error(f"일간 분석 데이터 생성 실패: {str(e)}")
            raise


# 전역 서비스 인스턴스
feedback_service = FeedbackService()