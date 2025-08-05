"""
채팅 API
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_active_user

router = APIRouter()


class ChatMessage(BaseModel):
    """채팅 메시지 모델"""
    message: str
    model: str = "gemini"  # 기본값은 gemini
    agent_type: str = "web_search"  # 기본값은 web_search


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str
    agent_used: str
    model_used: str
    timestamp: str
    user_id: str


@router.post("/", response_model=ChatResponse)
async def send_message(
    chat_message: ChatMessage,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> ChatResponse:
    """
    채팅 메시지 전송
    
    Args:
        chat_message: 채팅 메시지 데이터
        current_user: 현재 사용자 정보
        
    Returns:
        AI 응답
    """
    from app.services.agent_service import agent_service
    
    # 에이전트 서비스를 통해 메시지 처리
    result = await agent_service.execute_chat(
        message=chat_message.message,
        model=chat_message.model,
        agent_type=chat_message.agent_type,
        user_id=current_user["id"]
    )
    
    return ChatResponse(
        response=result["response"],
        agent_used=result["agent_used"],
        model_used=result["model_used"],
        timestamp=result["timestamp"],
        user_id=result["user_id"]
    )


@router.get("/history")
async def get_chat_history(
    limit: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> List[Dict[str, Any]]:
    """
    채팅 히스토리 조회
    
    Args:
        limit: 조회할 메시지 수
        current_user: 현재 사용자 정보
        
    Returns:
        채팅 히스토리 목록
    """
    # 임시 데이터 (실제 DB 연동 전)
    return [
        {
            "id": "1",
            "message": "안녕하세요!",
            "response": "안녕하세요! 무엇을 도와드릴까요?",
            "timestamp": "2024-01-01T10:00:00Z",
            "agent_type": "web_search",
            "model": "gemini"
        }
    ]