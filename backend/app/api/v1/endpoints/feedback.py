"""
피드백 API 엔드포인트
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.services.feedback_service import feedback_service
from app.db.models.user import User

router = APIRouter()


class FeedbackSubmitRequest(BaseModel):
    """피드백 제출 요청"""
    message_id: str = Field(..., description="메시지 ID")
    feedback_type: str = Field(..., description="피드백 타입 (rating, thumbs, detailed)")
    category: str = Field(default="overall", description="피드백 카테고리")
    rating: Optional[int] = Field(None, description="평점 (1-5)", ge=1, le=5)
    is_positive: Optional[bool] = Field(None, description="긍정/부정 평가")
    title: Optional[str] = Field(None, description="피드백 제목", max_length=200)
    content: Optional[str] = Field(None, description="피드백 내용")
    suggestions: Optional[str] = Field(None, description="개선 제안")
    conversation_id: Optional[str] = Field(None, description="대화 ID")
    agent_type: Optional[str] = Field(None, description="에이전트 타입")
    model_used: Optional[str] = Field(None, description="사용된 모델")
    response_time_ms: Optional[int] = Field(None, description="응답 시간(ms)")
    user_query: Optional[str] = Field(None, description="사용자 질문")
    ai_response: Optional[str] = Field(None, description="AI 응답")


class FeedbackUpdateRequest(BaseModel):
    """피드백 수정 요청"""
    rating: Optional[int] = Field(None, description="평점 (1-5)", ge=1, le=5)
    is_positive: Optional[bool] = Field(None, description="긍정/부정 평가")
    title: Optional[str] = Field(None, description="피드백 제목", max_length=200)
    content: Optional[str] = Field(None, description="피드백 내용")
    suggestions: Optional[str] = Field(None, description="개선 제안")


@router.post("/submit")
async def submit_feedback(
    request: FeedbackSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """피드백 제출"""
    try:
        feedback = await feedback_service.submit_feedback(
            session=db,
            user_id=str(current_user.id),
            message_id=request.message_id,
            feedback_type=request.feedback_type,
            category=request.category,
            rating=request.rating,
            is_positive=request.is_positive,
            title=request.title,
            content=request.content,
            suggestions=request.suggestions,
            conversation_id=request.conversation_id,
            agent_type=request.agent_type,
            model_used=request.model_used,
            response_time_ms=request.response_time_ms,
            user_query=request.user_query,
            ai_response=request.ai_response
        )
        
        return {
            "message": "피드백이 성공적으로 제출되었습니다.",
            "feedback_id": str(feedback.id),
            "status": "success"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="피드백 제출 중 오류가 발생했습니다.")


@router.get("/my")
async def get_my_feedbacks(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    feedback_type: Optional[str] = Query(None, description="피드백 타입 필터"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """내 피드백 목록 조회"""
    try:
        result = await feedback_service.get_user_feedbacks(
            session=db,
            user_id=str(current_user.id),
            limit=limit,
            skip=skip,
            feedback_type=feedback_type,
            category=category
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="피드백 조회 중 오류가 발생했습니다.")


@router.get("/message/{message_id}")
async def get_message_feedback(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 메시지의 피드백 조회"""
    try:
        feedback = await feedback_service.get_message_feedback(
            session=db,
            message_id=message_id,
            user_id=str(current_user.id)
        )
        
        if not feedback:
            return {"message": "해당 메시지에 대한 피드백이 없습니다.", "feedback": None}
        
        return {"feedback": feedback}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="피드백 조회 중 오류가 발생했습니다.")


@router.get("/profile")
async def get_my_feedback_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """내 피드백 프로파일 조회"""
    try:
        profile = await feedback_service.get_user_feedback_profile(
            session=db,
            user_id=str(current_user.id)
        )
        return profile
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="프로파일 조회 중 오류가 발생했습니다.")


@router.get("/statistics")
async def get_feedback_statistics(
    days: int = Query(30, ge=1, le=365, description="조회 기간 (일)"),
    agent_type: Optional[str] = Query(None, description="에이전트 타입 필터"),
    model_used: Optional[str] = Query(None, description="모델 필터"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """피드백 통계 조회"""
    try:
        stats = await feedback_service.get_feedback_statistics(
            session=db,
            days=days,
            agent_type=agent_type,
            model_used=model_used
        )
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="통계 조회 중 오류가 발생했습니다.")


@router.get("/recent")
async def get_recent_feedbacks(
    limit: int = Query(50, ge=1, le=100),
    hours: int = Query(24, ge=1, le=168, description="조회 기간 (시간)"),
    priority_only: bool = Query(False, description="우선순위 높은 피드백만"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """최근 피드백 조회 (관리자용)"""
    try:
        # TODO: 관리자 권한 확인 추가
        feedbacks = await feedback_service.get_recent_feedbacks(
            session=db,
            limit=limit,
            hours=hours,
            priority_only=priority_only
        )
        
        return {
            "feedbacks": feedbacks,
            "total": len(feedbacks),
            "filters": {
                "hours": hours,
                "priority_only": priority_only
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="최근 피드백 조회 중 오류가 발생했습니다.")


@router.post("/analytics/generate")
async def generate_daily_analytics(
    date: Optional[str] = Query(None, description="분석할 날짜 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """일간 분석 데이터 생성 (관리자용)"""
    try:
        # TODO: 관리자 권한 확인 추가
        
        target_date = None
        if date:
            try:
                target_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="잘못된 날짜 형식입니다. YYYY-MM-DD 형식으로 입력하세요.")
        
        analytics = await feedback_service.generate_daily_analytics(
            session=db,
            date=target_date
        )
        
        return {
            "message": "일간 분석 데이터가 성공적으로 생성되었습니다.",
            "analytics": analytics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail="분석 데이터 생성 중 오류가 발생했습니다.")


@router.get("/categories")
async def get_feedback_categories():
    """피드백 카테고리 목록 조회"""
    return {
        "categories": [
            {"value": "overall", "name": "전체 평가", "description": "전반적인 만족도"},
            {"value": "accuracy", "name": "정확성", "description": "정보의 정확성과 신뢰성"},
            {"value": "helpfulness", "name": "도움이 됨", "description": "답변이 얼마나 도움이 되었는지"},
            {"value": "clarity", "name": "명확성", "description": "답변의 명확성과 이해하기 쉬움"},
            {"value": "completeness", "name": "완성도", "description": "답변의 완성도와 포괄성"},
            {"value": "speed", "name": "응답 속도", "description": "응답 생성 속도"},
            {"value": "relevance", "name": "관련성", "description": "질문과 답변의 관련성"}
        ]
    }


@router.get("/types")
async def get_feedback_types():
    """피드백 타입 목록 조회"""
    return {
        "types": [
            {"value": "thumbs", "name": "좋아요/싫어요", "description": "간단한 긍정/부정 평가"},
            {"value": "rating", "name": "별점 평가", "description": "1-5점 점수 평가"},
            {"value": "detailed", "name": "상세 피드백", "description": "텍스트 기반 상세 피드백"}
        ]
    }