"""
AI 에이전트 API
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import logging

from app.api.deps import get_current_active_user
from app.agents.supervisor import supervisor_agent

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentInfo(BaseModel):
    """에이전트 정보 모델"""
    id: str
    name: str
    description: str
    capabilities: List[str]
    supported_models: List[str]
    is_enabled: bool


class AgentExecuteRequest(BaseModel):
    """에이전트 실행 요청 모델"""
    agent_id: str
    input_data: Dict[str, Any]
    model: str = "gemini"


class AgentExecuteResponse(BaseModel):
    """에이전트 실행 응답 모델"""
    agent_id: str
    result: Dict[str, Any]
    execution_time_ms: int
    model_used: str


class AgentSuggestionRequest(BaseModel):
    """에이전트 제안 요청 모델"""
    query: str
    current_agent: str
    model: Optional[str] = "gemini"


class AgentSuggestionResponse(BaseModel):
    """에이전트 제안 응답 모델"""
    needs_switch: bool
    suggested_agent: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    current_agent: Optional[str] = None
    error: Optional[str] = None


@router.get("/", response_model=List[AgentInfo])
async def list_agents(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> List[AgentInfo]:
    """
    사용 가능한 AI 에이전트 목록 조회
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        에이전트 목록
    """
    from app.services.agent_service import agent_service
    
    agent_info_list = agent_service.get_agent_info()
    
    return [
        AgentInfo(**agent_info) for agent_info in agent_info_list
    ]


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent_info(
    agent_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> AgentInfo:
    """
    특정 에이전트 정보 조회
    
    Args:
        agent_id: 에이전트 ID
        current_user: 현재 사용자 정보
        
    Returns:
        에이전트 정보
    """
    from app.services.agent_service import agent_service
    from fastapi import HTTPException, status
    
    agent_info_list = agent_service.get_agent_info(agent_id)
    
    if not agent_info_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"에이전트 '{agent_id}'를 찾을 수 없습니다"
        )
    
    return AgentInfo(**agent_info_list[0])


@router.post("/execute", response_model=AgentExecuteResponse)
async def execute_agent(
    request: AgentExecuteRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> AgentExecuteResponse:
    """
    AI 에이전트 실행
    
    Args:
        request: 에이전트 실행 요청
        current_user: 현재 사용자 정보
        
    Returns:
        에이전트 실행 결과
    """
    from app.services.agent_service import agent_service
    from fastapi import HTTPException, status
    
    # 에이전트 존재 여부 확인
    agent_info = await get_agent_info(request.agent_id, current_user)
    
    if not agent_info.is_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"에이전트 '{request.agent_id}'는 현재 사용할 수 없습니다"
        )
    
    # 에이전트 실행
    input_data = {
        "query": request.input_data.get("query", ""),
        "context": request.input_data.get("context", {}),
        "user_id": current_user["id"]
    }
    
    result = await agent_service.execute_agent_directly(
        agent_id=request.agent_id,
        input_data=input_data,
        model=request.model
    )
    
    return AgentExecuteResponse(
        agent_id=result["agent_id"],
        result=result["result"],
        execution_time_ms=result["execution_time_ms"],
        model_used=result["model_used"]
    )


@router.post("/analyze-suggestion", response_model=AgentSuggestionResponse)
async def analyze_agent_suggestion(
    request: AgentSuggestionRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> AgentSuggestionResponse:
    """
    사용자 쿼리를 분석하여 더 적합한 에이전트를 제안
    
    Args:
        request: 분석 요청 데이터
        current_user: 현재 사용자 정보
        
    Returns:
        에이전트 제안 결과
    """
    try:
        # 입력 검증
        if not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="질문이 비어있습니다."
            )
        
        # 유효한 에이전트 타입 확인
        valid_agents = {"none", "web_search", "deep_research", "canvas", "multimodal_rag"}
        if request.current_agent not in valid_agents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"유효하지 않은 에이전트 타입: {request.current_agent}"
            )
        
        # Supervisor 에이전트를 통한 분석
        suggestion_result = await supervisor_agent.analyze_and_suggest_agent(
            query=request.query,
            current_agent=request.current_agent,
            model=request.model
        )
        
        return AgentSuggestionResponse(**suggestion_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"에이전트 제안 분석 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"에이전트 분석 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/available-workers")
async def get_available_workers(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    사용 가능한 에이전트 워커 정보 조회
    
    Returns:
        사용 가능한 에이전트 워커 정보
    """
    try:
        agents_info = {
            "none": {
                "id": "none",
                "name": "일반 채팅",
                "description": "기본 AI 대화",
                "capabilities": ["일반 대화", "질문 답변", "창작 지원"]
            },
            "web_search": {
                "id": "web_search", 
                "name": "웹 검색",
                "description": "실시간 최신 정보 검색",
                "capabilities": ["실시간 정보 검색", "최신 뉴스 조회", "팩트 체크"]
            },
            "deep_research": {
                "id": "deep_research",
                "name": "심층 리서치", 
                "description": "종합적인 분석과 연구",
                "capabilities": ["심층 분석", "다각도 연구", "보고서 작성"]
            },
            "canvas": {
                "id": "canvas",
                "name": "Canvas",
                "description": "인터랙티브 워크스페이스",
                "capabilities": ["이미지 생성", "마인드맵", "텍스트 노트", "시각화"]
            },
            "multimodal_rag": {
                "id": "multimodal_rag",
                "name": "문서 분석",
                "description": "문서 및 이미지 분석",
                "capabilities": ["문서 분석", "이미지 해석", "파일 처리"]
            }
        }
        
        # 실제 사용 가능한 Worker 에이전트 목록
        available_workers = supervisor_agent.get_available_workers()
        
        return {
            "agents": agents_info,
            "available_workers": available_workers,
            "supervisor_capabilities": supervisor_agent.get_capabilities()
        }
        
    except Exception as e:
        logger.error(f"에이전트 워커 정보 조회 중 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="에이전트 워커 정보를 가져오는 중 오류가 발생했습니다."
        )