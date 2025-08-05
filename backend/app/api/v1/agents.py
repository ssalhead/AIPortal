"""
AI 에이전트 API
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_active_user

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