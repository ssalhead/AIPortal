"""
피드백 리포지토리
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func, text
from sqlalchemy.orm import selectinload

from app.db.models.feedback import (
    MessageFeedback, FeedbackAnalytics, UserFeedbackProfile,
    FeedbackType, FeedbackCategory
)
import logging

logger = logging.getLogger(__name__)


class FeedbackRepository:
    """피드백 리포지토리"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_feedback(
        self,
        user_id: str,
        message_id: str,
        feedback_type: FeedbackType,
        category: FeedbackCategory = FeedbackCategory.OVERALL,
        conversation_id: Optional[str] = None,
        rating: Optional[int] = None,
        is_positive: Optional[bool] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        suggestions: Optional[str] = None,
        agent_type: Optional[str] = None,
        model_used: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        user_query: Optional[str] = None,
        ai_response_preview: Optional[str] = None,
        metadata_: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        priority: int = 1
    ) -> MessageFeedback:
        """피드백 생성"""
        feedback = MessageFeedback(
            user_id=user_id,
            message_id=message_id,
            conversation_id=conversation_id,
            feedback_type=feedback_type,
            category=category,
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
            metadata_=metadata_ or {},
            tags=tags or [],
            priority=priority
        )
        
        self.session.add(feedback)
        await self.session.flush()
        return feedback
    
    async def get_feedback_by_id(self, feedback_id: str) -> Optional[MessageFeedback]:
        """ID로 피드백 조회"""
        query = select(MessageFeedback).where(MessageFeedback.id == feedback_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_message_feedback(
        self, 
        message_id: str, 
        user_id: Optional[str] = None
    ) -> Optional[MessageFeedback]:
        """메시지의 피드백 조회"""
        query = select(MessageFeedback).where(MessageFeedback.message_id == message_id)
        
        if user_id:
            query = query.where(MessageFeedback.user_id == user_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_feedbacks(
        self,
        user_id: str,
        limit: int = 20,
        skip: int = 0,
        feedback_type: Optional[FeedbackType] = None,
        category: Optional[FeedbackCategory] = None
    ) -> List[MessageFeedback]:
        """사용자 피드백 목록 조회"""
        query = select(MessageFeedback).where(MessageFeedback.user_id == user_id)
        
        if feedback_type:
            query = query.where(MessageFeedback.feedback_type == feedback_type)
        
        if category:
            query = query.where(MessageFeedback.category == category)
        
        query = query.order_by(desc(MessageFeedback.created_at)).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update_feedback(
        self,
        feedback_id: str,
        rating: Optional[int] = None,
        is_positive: Optional[bool] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        suggestions: Optional[str] = None,
        tags: Optional[List[str]] = None,
        priority: Optional[int] = None
    ) -> Optional[MessageFeedback]:
        """피드백 수정"""
        feedback = await self.get_feedback_by_id(feedback_id)
        if not feedback:
            return None
        
        if rating is not None:
            feedback.rating = rating
        if is_positive is not None:
            feedback.is_positive = is_positive
        if title is not None:
            feedback.title = title
        if content is not None:
            feedback.content = content
        if suggestions is not None:
            feedback.suggestions = suggestions
        if tags is not None:
            feedback.tags = tags
        if priority is not None:
            feedback.priority = priority
        
        feedback.updated_at = datetime.utcnow()
        return feedback
    
    async def delete_feedback(self, feedback_id: str) -> bool:
        """피드백 삭제"""
        feedback = await self.get_feedback_by_id(feedback_id)
        if not feedback:
            return False
        
        await self.session.delete(feedback)
        return True
    
    async def get_conversation_feedbacks(
        self, 
        conversation_id: str,
        limit: int = 50
    ) -> List[MessageFeedback]:
        """대화의 모든 피드백 조회"""
        query = select(MessageFeedback).where(
            MessageFeedback.conversation_id == conversation_id
        ).order_by(desc(MessageFeedback.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_agent_feedbacks(
        self,
        agent_type: str,
        limit: int = 100,
        since_date: Optional[datetime] = None
    ) -> List[MessageFeedback]:
        """특정 에이전트의 피드백 조회"""
        query = select(MessageFeedback).where(MessageFeedback.agent_type == agent_type)
        
        if since_date:
            query = query.where(MessageFeedback.created_at >= since_date)
        
        query = query.order_by(desc(MessageFeedback.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_model_feedbacks(
        self,
        model_used: str,
        limit: int = 100,
        since_date: Optional[datetime] = None
    ) -> List[MessageFeedback]:
        """특정 모델의 피드백 조회"""
        query = select(MessageFeedback).where(MessageFeedback.model_used == model_used)
        
        if since_date:
            query = query.where(MessageFeedback.created_at >= since_date)
        
        query = query.order_by(desc(MessageFeedback.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_recent_feedbacks(
        self,
        limit: int = 50,
        hours: int = 24
    ) -> List[MessageFeedback]:
        """최근 피드백 조회"""
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = select(MessageFeedback).where(
            MessageFeedback.created_at >= since_time
        ).order_by(desc(MessageFeedback.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_feedback_statistics(
        self,
        since_date: Optional[datetime] = None,
        agent_type: Optional[str] = None,
        model_used: Optional[str] = None
    ) -> Dict[str, Any]:
        """피드백 통계 조회"""
        base_query = select(MessageFeedback)
        
        if since_date:
            base_query = base_query.where(MessageFeedback.created_at >= since_date)
        if agent_type:
            base_query = base_query.where(MessageFeedback.agent_type == agent_type)
        if model_used:
            base_query = base_query.where(MessageFeedback.model_used == model_used)
        
        # 기본 통계
        total_query = select(func.count(MessageFeedback.id)).select_from(base_query)
        positive_query = select(func.count(MessageFeedback.id)).select_from(
            base_query.where(MessageFeedback.is_positive == True)
        )
        negative_query = select(func.count(MessageFeedback.id)).select_from(
            base_query.where(MessageFeedback.is_positive == False)
        )
        avg_rating_query = select(func.avg(MessageFeedback.rating)).select_from(
            base_query.where(MessageFeedback.rating.isnot(None))
        )
        
        total_result = await self.session.execute(total_query)
        positive_result = await self.session.execute(positive_query)
        negative_result = await self.session.execute(negative_query)
        avg_rating_result = await self.session.execute(avg_rating_query)
        
        total_count = total_result.scalar() or 0
        positive_count = positive_result.scalar() or 0
        negative_count = negative_result.scalar() or 0
        avg_rating = avg_rating_result.scalar()
        
        return {
            "total_feedbacks": total_count,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": total_count - positive_count - negative_count,
            "positive_rate": (positive_count / total_count * 100) if total_count > 0 else 0,
            "negative_rate": (negative_count / total_count * 100) if total_count > 0 else 0,
            "avg_rating": float(avg_rating) if avg_rating else None
        }


class UserFeedbackProfileRepository:
    """사용자 피드백 프로파일 리포지토리"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create_profile(self, user_id: str) -> UserFeedbackProfile:
        """사용자 피드백 프로파일 조회 또는 생성"""
        query = select(UserFeedbackProfile).where(UserFeedbackProfile.user_id == user_id)
        result = await self.session.execute(query)
        profile = result.scalar_one_or_none()
        
        if not profile:
            profile = UserFeedbackProfile(user_id=user_id)
            self.session.add(profile)
            await self.session.flush()
        
        return profile
    
    async def update_profile_stats(self, user_id: str, feedback: MessageFeedback):
        """피드백 추가 시 프로파일 통계 업데이트"""
        profile = await self.get_or_create_profile(user_id)
        
        # 기본 통계 업데이트
        profile.total_feedbacks += 1
        profile.last_feedback_at = datetime.utcnow()
        
        if feedback.is_positive is True:
            profile.positive_feedbacks += 1
        elif feedback.is_positive is False:
            profile.negative_feedbacks += 1
        
        if feedback.feedback_type == FeedbackType.DETAILED:
            profile.detailed_feedbacks += 1
        
        # 평균 평점 업데이트
        if feedback.rating:
            if profile.avg_rating_given:
                # 이동평균 계산
                total_ratings = profile.total_feedbacks
                profile.avg_rating_given = (
                    (profile.avg_rating_given * (total_ratings - 1) + feedback.rating) / total_ratings
                )
            else:
                profile.avg_rating_given = float(feedback.rating)
        
        # 선호도 업데이트 (에이전트, 모델)
        if feedback.agent_type:
            preferred_agents = profile.preferred_agents or {}
            preferred_agents[feedback.agent_type] = preferred_agents.get(feedback.agent_type, 0) + 1
            profile.preferred_agents = preferred_agents
        
        if feedback.model_used:
            preferred_models = profile.preferred_models or {}
            preferred_models[feedback.model_used] = preferred_models.get(feedback.model_used, 0) + 1
            profile.preferred_models = preferred_models
        
        # 카테고리 빈도 업데이트
        common_categories = profile.common_categories or {}
        category_name = feedback.category.value
        common_categories[category_name] = common_categories.get(category_name, 0) + 1
        profile.common_categories = common_categories
        
        profile.updated_at = datetime.utcnow()
        return profile


class FeedbackAnalyticsRepository:
    """피드백 분석 리포지토리"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_daily_analytics(self, date: datetime) -> FeedbackAnalytics:
        """일간 분석 데이터 생성"""
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
        
        # 해당 날짜의 피드백 조회
        query = select(MessageFeedback).where(
            and_(
                MessageFeedback.created_at >= start_date,
                MessageFeedback.created_at < end_date
            )
        )
        result = await self.session.execute(query)
        feedbacks = result.scalars().all()
        
        # 통계 계산
        total_feedbacks = len(feedbacks)
        positive_count = sum(1 for f in feedbacks if f.is_positive is True)
        negative_count = sum(1 for f in feedbacks if f.is_positive is False)
        neutral_count = total_feedbacks - positive_count - negative_count
        
        # 평균 평점
        ratings = [f.rating for f in feedbacks if f.rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        # 평점 분포
        rating_distribution = {}
        for rating in ratings:
            rating_distribution[rating] = rating_distribution.get(rating, 0) + 1
        
        # 카테고리별 통계
        category_stats = {}
        for feedback in feedbacks:
            category = feedback.category.value
            if category not in category_stats:
                category_stats[category] = {"count": 0, "ratings": []}
            category_stats[category]["count"] += 1
            if feedback.rating:
                category_stats[category]["ratings"].append(feedback.rating)
        
        # 각 카테고리의 평균 평점 계산
        for category, stats in category_stats.items():
            if stats["ratings"]:
                stats["avg_rating"] = sum(stats["ratings"]) / len(stats["ratings"])
                del stats["ratings"]  # 평균만 저장
        
        # 에이전트별 통계
        agent_stats = {}
        for feedback in feedbacks:
            if feedback.agent_type:
                agent = feedback.agent_type
                if agent not in agent_stats:
                    agent_stats[agent] = {"count": 0, "positive": 0, "ratings": []}
                agent_stats[agent]["count"] += 1
                if feedback.is_positive:
                    agent_stats[agent]["positive"] += 1
                if feedback.rating:
                    agent_stats[agent]["ratings"].append(feedback.rating)
        
        # 에이전트별 평균 평점 및 만족도 계산
        for agent, stats in agent_stats.items():
            if stats["ratings"]:
                stats["avg_rating"] = sum(stats["ratings"]) / len(stats["ratings"])
                del stats["ratings"]
            stats["satisfaction_rate"] = (stats["positive"] / stats["count"] * 100) if stats["count"] > 0 else 0
        
        # 응답 시간 통계
        response_times = [f.response_time_ms for f in feedbacks if f.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        analytics = FeedbackAnalytics(
            date=start_date,
            period_type="daily",
            total_feedbacks=total_feedbacks,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            avg_rating=avg_rating,
            rating_distribution=rating_distribution,
            category_stats=category_stats,
            agent_stats=agent_stats,
            avg_response_time_ms=avg_response_time
        )
        
        self.session.add(analytics)
        await self.session.flush()
        return analytics
    
    async def get_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        period_type: str = "daily"
    ) -> List[FeedbackAnalytics]:
        """분석 데이터 조회"""
        query = select(FeedbackAnalytics).where(
            and_(
                FeedbackAnalytics.date >= start_date,
                FeedbackAnalytics.date <= end_date,
                FeedbackAnalytics.period_type == period_type
            )
        ).order_by(FeedbackAnalytics.date)
        
        result = await self.session.execute(query)
        return result.scalars().all()