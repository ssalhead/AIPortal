"""
채팅 API
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio
from asyncio import Queue

from app.api.deps import get_current_active_user
from app.models.citation import CitedResponse

router = APIRouter()


class ChatMessage(BaseModel):
    """채팅 메시지 모델"""
    message: str
    model: str = "gemini"  # 기본값은 gemini
    agent_type: str = "web_search"  # 기본값은 web_search
    session_id: Optional[str] = None  # 대화 세션 ID
    include_citations: bool = True  # 인용 정보 포함 여부
    max_sources: int = 10  # 최대 출처 개수
    min_confidence: float = 0.7  # 최소 인용 신뢰도


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str
    agent_used: str
    model_used: str
    timestamp: str
    user_id: str
    session_id: Optional[str] = None  # 대화 세션 ID
    # 인용 정보 추가
    citations: List[Dict[str, Any]] = []
    sources: List[Dict[str, Any]] = []
    citation_stats: Optional[Dict[str, Any]] = None


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
        AI 응답 (인용 정보 포함)
    """
    from app.services.agent_service import agent_service
    from app.services.citation_service import CitationService
    from app.services.logging_service import logging_service
    
    # 에이전트 서비스를 통해 메시지 처리 (대화 컨텍스트 지원)
    result = await agent_service.execute_chat(
        message=chat_message.message,
        model=chat_message.model,
        agent_type=chat_message.agent_type,
        user_id=current_user["id"],
        session_id=chat_message.session_id
    )
    
    # 인용 정보 처리
    citations = []
    sources = []
    citation_stats = None
    
    if chat_message.include_citations and result.get("search_results"):
        citation_service = CitationService(logging_service)
        
        cited_response = await citation_service.extract_citations_from_response(
            response_text=result["response"],
            search_results=result["search_results"],
            min_confidence=chat_message.min_confidence
        )
        
        # Pydantic 모델을 딕셔너리로 변환
        citations = [citation.model_dump() for citation in cited_response.citations]
        sources = [source.model_dump() for source in cited_response.sources]
        
        # 통계 생성
        if citations or sources:
            stats = await citation_service.get_citation_stats(
                cited_response.citations,
                cited_response.sources
            )
            citation_stats = stats.model_dump()
    
    return ChatResponse(
        response=result["response"],
        agent_used=result["agent_used"],
        model_used=result["model_used"],
        timestamp=result["timestamp"],
        user_id=result["user_id"],
        session_id=result.get("session_id"),  # 세션 ID 포함
        citations=citations,
        sources=sources[:chat_message.max_sources],  # 최대 출처 개수 제한
        citation_stats=citation_stats
    )


@router.post("/stream")
async def send_message_stream(
    chat_message: ChatMessage,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    실시간 진행 상태와 함께 채팅 메시지 전송 (SSE)
    
    Args:
        chat_message: 채팅 메시지 데이터
        current_user: 현재 사용자 정보
        
    Returns:
        Server-Sent Events 스트림
    """
    from app.services.agent_service import agent_service
    from app.services.citation_service import CitationService
    from app.services.logging_service import logging_service
    
    async def generate():
        try:
            # 진행 상태 저장
            progress_events = []
            
            def progress_callback(step: str, progress: int):
                """진행 상태 콜백"""
                progress_events.append({'step': step, 'progress': progress})
            
            # 시작 이벤트
            yield f"data: {json.dumps({'type': 'start', 'data': {'message': '채팅 처리를 시작합니다...'}})}\n\n"
            
            # 메시지 처리 (진행상태는 콜백으로 수집)
            result = await agent_service.execute_chat(
                message=chat_message.message,
                model=chat_message.model,
                agent_type=chat_message.agent_type,
                user_id=current_user["id"],
                session_id=chat_message.session_id,
                progress_callback=progress_callback
            )
            
            # 수집된 진행상태 전송
            for progress_data in progress_events:
                yield f"data: {json.dumps({'type': 'progress', 'data': progress_data})}\n\n"
                await asyncio.sleep(0.1)  # 시각적 효과를 위한 짧은 지연
            
            # 인용 정보 처리
            citations = []
            sources = []
            citation_stats = None
            
            if chat_message.include_citations and result.get("search_results"):
                citation_service = CitationService(logging_service)
                
                cited_response = await citation_service.extract_citations_from_response(
                    response_text=result["response"],
                    search_results=result["search_results"],
                    min_confidence=chat_message.min_confidence
                )
                
                citations = [citation.model_dump() for citation in cited_response.citations]
                sources = [source.model_dump() for source in cited_response.sources]
                
                if citations or sources:
                    stats = await citation_service.get_citation_stats(
                        cited_response.citations,
                        cited_response.sources
                    )
                    citation_stats = stats.model_dump()
            
            # 최종 결과 전송
            final_result = {
                "type": "result",
                "data": {
                    "response": result["response"],
                    "agent_used": result["agent_used"],
                    "model_used": result["model_used"],
                    "timestamp": result["timestamp"],
                    "user_id": result["user_id"],
                    "session_id": result.get("session_id"),  # 세션 ID 포함
                    "citations": citations,
                    "sources": sources[:chat_message.max_sources],
                    "citation_stats": citation_stats
                }
            }
            yield f"data: {json.dumps(final_result)}\n\n"
            
            # 완료 이벤트
            yield f"data: {json.dumps({'type': 'end', 'data': {'message': '채팅 처리가 완료되었습니다.'}})}\n\n"
            
        except Exception as e:
            # 오류 이벤트
            error_result = {
                "type": "error",
                "data": {
                    "message": f"채팅 처리 중 오류가 발생했습니다: {str(e)}",
                    "error": str(e)
                }
            }
            yield f"data: {json.dumps(error_result)}\n\n"
    
    # SSE 응답 헤더 설정
    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )


@router.get("/history")
async def get_chat_history(
    session_id: Optional[str] = None,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> List[Dict[str, Any]]:
    """
    채팅 히스토리 조회
    
    Args:
        session_id: 특정 세션의 히스토리 (없으면 최신 세션)
        limit: 조회할 메시지 수
        current_user: 현재 사용자 정보
        
    Returns:
        채팅 히스토리 목록
    """
    from app.services.conversation_service import conversation_service
    
    if session_id:
        # 특정 세션의 히스토리
        return await conversation_service.get_session_history(
            session_id=session_id,
            user_id=current_user["id"],
            limit=limit
        )
    else:
        # 사용자의 모든 세션 조회 (기본 동작을 위한 빈 리스트 반환)
        return []


@router.get("/sessions")
async def get_user_sessions(
    limit: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> List[Dict[str, Any]]:
    """
    사용자의 대화 세션 목록 조회
    
    Args:
        limit: 조회할 세션 수
        current_user: 현재 사용자 정보
        
    Returns:
        대화 세션 목록
    """
    from app.services.conversation_service import conversation_service
    
    return await conversation_service.get_user_sessions(
        user_id=current_user["id"],
        limit=limit
    )


@router.post("/sessions/new")
async def create_new_session(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    새 대화 세션 생성
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        새 세션 정보
    """
    from app.services.conversation_service import conversation_service
    
    session = await conversation_service.create_new_session(
        user_id=current_user["id"]
    )
    
    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "title": session.title
    }


@router.delete("/sessions/{session_id}")
async def end_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    대화 세션 종료
    
    Args:
        session_id: 종료할 세션 ID
        current_user: 현재 사용자 정보
        
    Returns:
        결과 메시지
    """
    from app.services.conversation_service import conversation_service
    
    success = await conversation_service.end_session(
        session_id=session_id,
        user_id=current_user["id"]
    )
    
    if success:
        return {"message": "세션이 성공적으로 종료되었습니다."}
    else:
        raise HTTPException(
            status_code=404,
            detail="세션을 찾을 수 없거나 권한이 없습니다."
        )


@router.patch("/sessions/{session_id}/title")
async def update_session_title(
    session_id: str,
    title: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    세션 제목 수정
    
    Args:
        session_id: 세션 ID
        title: 새 제목
        current_user: 현재 사용자 정보
        
    Returns:
        결과 메시지
    """
    from app.services.conversation_service import conversation_service
    
    success = await conversation_service.update_session_title(
        session_id=session_id,
        user_id=current_user["id"],
        title=title
    )
    
    if success:
        return {"message": "세션 제목이 성공적으로 수정되었습니다."}
    else:
        raise HTTPException(
            status_code=404,
            detail="세션을 찾을 수 없거나 권한이 없습니다."
        )