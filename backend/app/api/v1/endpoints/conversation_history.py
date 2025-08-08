"""
대화 이력 관리 API 엔드포인트
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user
from app.services.conversation_history_service import conversation_history_service
from app.db.models.conversation import ConversationStatus, MessageRole
from app.db.models.user import User

router = APIRouter()


# Pydantic 모델들
class ConversationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    model: Optional[str] = Field(None, max_length=100)
    agent_type: Optional[str] = Field(None, max_length=100)
    metadata_: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ConversationStatus] = None
    metadata_: Optional[Dict[str, Any]] = None


class MessageCreate(BaseModel):
    role: MessageRole
    content: str = Field(..., min_length=1)
    model: Optional[str] = Field(None, max_length=100)
    tokens_input: Optional[int] = Field(None, ge=0)
    tokens_output: Optional[int] = Field(None, ge=0)
    latency_ms: Optional[int] = Field(None, ge=0)
    metadata_: Optional[Dict[str, Any]] = Field(default_factory=dict)
    attachments: Optional[list] = Field(default_factory=list)


# API 엔드포인트들
@router.get("/conversations")
async def get_user_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[ConversationStatus] = Query(ConversationStatus.ACTIVE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """사용자 대화 목록 조회"""
    try:
        result = await conversation_history_service.get_user_conversations(
            user_id=str(current_user.id),
            session=db,
            skip=skip,
            limit=limit,
            status=status
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(
    conversation_id: str,
    message_skip: int = Query(0, ge=0),
    message_limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """대화 상세 정보 조회 (메시지 포함)"""
    try:
        result = await conversation_history_service.get_conversation_detail(
            conversation_id=conversation_id,
            user_id=str(current_user.id),
            session=db,
            message_limit=message_limit,
            message_skip=message_skip
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/search")
async def search_conversations(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """대화 전문검색"""
    try:
        result = await conversation_history_service.search_conversations(
            user_id=str(current_user.id),
            query=q,
            session=db,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations")
async def create_conversation(
    conversation_data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """새 대화 생성"""
    try:
        result = await conversation_history_service.create_conversation(
            user_id=str(current_user.id),
            title=conversation_data.title,
            session=db,
            description=conversation_data.description,
            model=conversation_data.model,
            agent_type=conversation_data.agent_type,
            metadata_=conversation_data.metadata_
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    conversation_data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """대화 정보 수정"""
    try:
        result = await conversation_history_service.update_conversation(
            conversation_id=conversation_id,
            user_id=str(current_user.id),
            session=db,
            title=conversation_data.title,
            description=conversation_data.description,
            status=conversation_data.status,
            metadata_=conversation_data.metadata_
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    hard_delete: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """대화 삭제"""
    try:
        success = await conversation_history_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=str(current_user.id),
            session=db,
            soft_delete=not hard_delete
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
        
        return {"message": "대화가 삭제되었습니다.", "conversation_id": conversation_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """메시지 추가"""
    try:
        result = await conversation_history_service.add_message(
            conversation_id=conversation_id,
            user_id=str(current_user.id),
            role=message_data.role,
            content=message_data.content,
            session=db,
            model=message_data.model,
            tokens_input=message_data.tokens_input,
            tokens_output=message_data.tokens_output,
            latency_ms=message_data.latency_ms,
            metadata_=message_data.metadata_,
            attachments=message_data.attachments
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/statistics")
async def get_conversation_statistics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """대화 통계 조회"""
    try:
        result = await conversation_history_service.get_conversation_statistics(
            user_id=str(current_user.id),
            session=db,
            days=days
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats")
async def get_cache_statistics(
    current_user: User = Depends(get_current_user)
):
    """캐시 통계 조회 (개발/디버깅용)"""
    try:
        stats = conversation_history_service.cache_manager.get_cache_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))