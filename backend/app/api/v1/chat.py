"""
채팅 API
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio
from app.utils.timezone import now_kst
from app.utils.logger import get_logger
# from asyncio import Queue  # 더 이상 사용하지 않음

logger = get_logger(__name__)

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
    # 메타데이터 추가 (맥락 통합 정보 포함)
    metadata: Optional[Dict[str, Any]] = None
    # Canvas 데이터 추가 (이미지 생성, 마인드맵 등)
    canvas_data: Optional[Dict[str, Any]] = None


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
    
    # current_user 안전성 검증
    if not current_user or not isinstance(current_user, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자 인증 정보가 올바르지 않습니다"
        )
    
    user_id = current_user.get("id", "default_user")
    
    # 에이전트 서비스를 통해 메시지 처리 (대화 컨텍스트 지원)
    result = await agent_service.execute_chat(
        message=chat_message.message,
        model=chat_message.model,
        agent_type=chat_message.agent_type,
        user_id=user_id,
        session_id=chat_message.session_id
    )
    
    # AgentOutput 객체인 경우 딕셔너리로 변환
    if hasattr(result, 'model_dump'):
        result = result.model_dump()
    elif not isinstance(result, dict):
        # AgentOutput 타입인 경우 수동 변환
        result = {
            "response": getattr(result, 'result', '응답을 생성할 수 없습니다'),
            "agent_used": getattr(result, 'agent_id', 'unknown'),
            "model_used": getattr(result, 'model_used', chat_message.model),
            "timestamp": getattr(result, 'timestamp', ''),
            "user_id": user_id,
            "session_id": chat_message.session_id,
            "citations": [],
            "sources": []
        }
    
    # 인용 정보 처리 - 에이전트에서 직접 제공된 citations와 sources 사용
    citations = result.get("citations", [])
    sources = result.get("sources", [])
    citation_stats = None
    
    # 추가적인 citation 처리가 필요한 경우에만 CitationService 사용
    if chat_message.include_citations and not citations and result.get("search_results"):
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
        try:
            from app.services.citation_service import CitationService
            citation_service = CitationService(logging_service)
            # 딕셔너리 형태의 citations를 적절히 처리
            citation_stats = {
                "total_citations": len(citations),
                "total_sources": len(sources),
                "avg_confidence": sum(c.get("score", 0.8) for c in citations) / len(citations) if citations else 0
            }
        except Exception as e:
            logger.warning(f"Citation 통계 생성 실패: {e}")
            citation_stats = None
    
    return ChatResponse(
        response=result["response"],
        agent_used=result["agent_used"],
        model_used=result["model_used"],
        timestamp=result["timestamp"],
        user_id=result["user_id"],
        session_id=result.get("session_id"),  # 세션 ID 포함
        citations=citations or [],
        sources=(sources or [])[:chat_message.max_sources],  # 최대 출처 개수 제한
        citation_stats=citation_stats,
        metadata=result.get("metadata"),  # 메타데이터 포함 (맥락 통합 정보)
        canvas_data=result.get("canvas_data")  # Canvas 데이터 포함 (이미지 생성, 마인드맵 등)
    )


@router.post("/stream")
async def send_message_stream(
    chat_message: ChatMessage,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    실시간 진행 상태와 함께 채팅 메시지 전송 (SSE) - 대화 컨텍스트 지원
    
    Args:
        chat_message: 채팅 메시지 데이터
        current_user: 현재 사용자 정보
        
    Returns:
        Server-Sent Events 스트림 (대화 컨텍스트 포함)
    """
    from app.services.agent_service import agent_service
    
    # current_user 안전성 검증
    if not current_user or not isinstance(current_user, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자 인증 정보가 올바르지 않습니다"
        )
    
    user_id = current_user.get("id", "default_user")
    
    async def generate():
        try:
            # 🎨 진행 상태를 스트림에 추가하기 위한 큐
            progress_queue = asyncio.Queue()
            
            # 🎨 진행 상태 콜백 함수 (Canvas 에이전트용)
            async def progress_callback(progress_data):
                """Canvas 에이전트의 진행 상태를 큐에 추가"""
                progress_event = {
                    "type": "progress",
                    "data": {
                        "step": progress_data.get("step", "processing"),
                        "message": progress_data.get("message", "처리 중..."),
                        "progress": progress_data.get("progress", 0),
                        "timestamp": now_kst().isoformat()
                    }
                }
                logger.info(f"🎨 Canvas 진행상태 큐 추가: {progress_event}")
                await progress_queue.put(progress_event)
            
            # 프로그레스 이벤트를 먼저 전송하는 태스크
            async def send_progress_events():
                while True:
                    try:
                        # 0.1초 대기로 진행 상태 이벤트 확인
                        progress_event = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                        yield f"data: {json.dumps(progress_event)}\n\n"
                    except asyncio.TimeoutError:
                        break
            
            # 🎨 진행 상태 이벤트 먼저 전송
            async for progress_data in send_progress_events():
                yield progress_data
            
            # 새로운 execute_chat_stream 메서드로 대화 컨텍스트 지원 스트리밍
            async for event in agent_service.execute_chat_stream(
                message=chat_message.message,
                model=chat_message.model,
                agent_type=chat_message.agent_type,
                user_id=user_id,
                session_id=chat_message.session_id,
                progress_callback=progress_callback  # 🎨 Canvas 진행 상태 콜백 추가
            ):
                # 스트리밍 중간에도 진행 상태 이벤트 확인
                try:
                    while True:
                        progress_event = progress_queue.get_nowait()
                        yield f"data: {json.dumps(progress_event)}\n\n"
                except asyncio.QueueEmpty:
                    pass
                
                # 이벤트를 JSON으로 직렬화하여 SSE 형태로 전송
                yield f"data: {json.dumps(event)}\n\n"
                
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
    from app.services.conversation_history_service import conversation_history_service
    from app.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        if session_id:
            # 특정 세션의 히스토리
            conversation_detail = await conversation_history_service.get_conversation_detail(
                conversation_id=session_id,
                user_id=current_user["id"],
                session=db,
                message_limit=limit
            )
            if conversation_detail and conversation_detail.get('messages'):
                # 디버깅: API 응답 데이터 확인
                messages = conversation_detail['messages']
                logger.debug("메시지 샘플", {"count": len(messages)})
                for i, msg in enumerate(messages[:2]):  # 처음 2개만 로깅
                    logger.debug(f"메시지 {i+1}", {
                        "role": msg.get('role'),
                        "role_type": type(msg.get('role')),
                        "content_preview": msg.get('content', '')[:30] + '...'
                    })
                return messages
            return []
        else:
            # 사용자의 모든 대화 조회
            conversations = await conversation_history_service.get_user_conversations(
                user_id=current_user["id"],
                session=db,
                limit=limit
            )
            return conversations


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
    from app.services.conversation_history_service import conversation_history_service
    from app.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        result = await conversation_history_service.get_user_conversations(
            user_id=current_user["id"],
            session=db,
            limit=limit
        )
        # 딕셔너리에서 conversations 리스트만 반환
        if isinstance(result, dict) and 'conversations' in result:
            return result['conversations']
        return result


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
    from app.services.conversation_history_service import conversation_history_service
    from app.db.session import AsyncSessionLocal
    from datetime import datetime
    
    async with AsyncSessionLocal() as db:
        conversation = await conversation_history_service.create_conversation(
            user_id=current_user["id"],
            title=f"대화 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            session=db
        )
    
    return {
        "session_id": conversation["id"],
        "created_at": conversation["created_at"],
        "title": conversation["title"]
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
    from app.services.conversation_history_service import conversation_history_service
    from app.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        success = await conversation_history_service.delete_conversation(
            conversation_id=session_id,
            user_id=current_user["id"],
            session=db
        )
    
    if success:
        return {"message": "세션이 성공적으로 종료되었습니다."}
    else:
        raise HTTPException(
            status_code=404,
            detail="세션을 찾을 수 없거나 권한이 없습니다."
        )


class TitleUpdateRequest(BaseModel):
    title: str

@router.patch("/sessions/{session_id}/title")
async def update_session_title(
    session_id: str,
    request: TitleUpdateRequest,
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
    from app.services.conversation_history_service import conversation_history_service
    from app.db.session import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        success = await conversation_history_service.update_conversation_title(
            conversation_id=session_id,
            user_id=current_user["id"],
            title=request.title,
            session=db
        )
    
    if success:
        return {"message": "세션 제목이 성공적으로 수정되었습니다."}
    else:
        raise HTTPException(
            status_code=404,
            detail="세션을 찾을 수 없거나 권한이 없습니다."
        )


class TitleGenerateRequest(BaseModel):
    """제목 생성 요청 모델"""
    message: str
    model: str = "gemini"


@router.post("/generate-title")
async def generate_conversation_title(
    request: TitleGenerateRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    대화 제목 자동 생성
    
    Args:
        request: 제목 생성 요청 (첫 번째 사용자 메시지)
        current_user: 현재 사용자 정보
        
    Returns:
        생성된 제목
    """
    try:
        from app.agents.llm_router import llm_router
        
        # 제목 생성을 위한 프롬프트
        title_prompt = f"""다음 사용자의 질문이나 요청을 바탕으로 대화의 제목을 생성해주세요.

사용자 메시지: "{request.message}"

제목 생성 규칙:
1. 50자 이내로 작성
2. 구체적이고 명확하게 작성
3. 한국어로 작성
4. 질문의 핵심 내용을 담아서 작성
5. "대화", "채팅" 같은 일반적인 단어는 피하고 구체적인 내용으로 작성

제목만 응답하고 다른 설명은 하지 마세요."""

        # LLM을 통해 제목 생성
        response_content, used_model = await llm_router.generate_response(
            model_name=request.model,
            prompt=title_prompt,
            user_id=current_user["id"],
            conversation_id=None
        )
        
        # 생성된 제목 정리
        generated_title = response_content.strip()
        
        # 따옴표 제거
        if generated_title.startswith('"') and generated_title.endswith('"'):
            generated_title = generated_title[1:-1]
        
        # 길이 제한
        if len(generated_title) > 50:
            generated_title = generated_title[:47] + "..."
            
        return {"title": generated_title}
        
    except Exception as e:
        logger.error(f"제목 생성 실패: {e}")
        # 실패 시 기본 제목 반환
        fallback_title = request.message[:30] + ("..." if len(request.message) > 30 else "")
        return {"title": fallback_title}