"""
AI 에이전트 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AgentInput(BaseModel):
    """에이전트 입력 데이터 모델"""
    query: str
    context: Optional[Dict[str, Any]] = None
    user_id: str
    session_id: Optional[str] = None


class AgentOutput(BaseModel):
    """에이전트 출력 데이터 모델 - 모든 에이전트 실행 결과의 표준 형식"""
    result: str
    metadata: Dict[str, Any]
    execution_time_ms: int
    agent_id: str
    model_used: str
    timestamp: str


class BaseAgent(ABC):
    """AI 에이전트 베이스 클래스"""
    
    def __init__(self, agent_id: str, name: str, description: str):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"{__name__}.{agent_id}")
    
    @abstractmethod
    async def execute(
        self, 
        input_data: AgentInput, 
        model: str = "gemini",
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> AgentOutput:
        """
        에이전트 실행 메서드
        
        Args:
            input_data: 입력 데이터
            model: 사용할 LLM 모델
            progress_callback: 진행 상태 콜백 함수 (단계명, 진행률)
            
        Returns:
            에이전트 실행 결과
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """
        에이전트 기능 목록 반환
        
        Returns:
            기능 목록
        """
        pass
    
    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """
        지원하는 모델 목록 반환
        
        Returns:
            지원 모델 목록
        """
        pass
    
    def validate_input(self, input_data: AgentInput) -> bool:
        """
        입력 데이터 검증
        
        Args:
            input_data: 입력 데이터
            
        Returns:
            검증 결과
        """
        if not input_data.query.strip():
            return False
        return True
    
    def create_output(
        self, 
        result: str, 
        metadata: Dict[str, Any], 
        execution_time_ms: int,
        model_used: str
    ) -> AgentOutput:
        """
        출력 데이터 생성
        
        Args:
            result: 실행 결과
            metadata: 메타데이터
            execution_time_ms: 실행 시간
            model_used: 사용된 모델
            
        Returns:
            출력 데이터
        """
        return AgentOutput(
            result=result,
            metadata=metadata,
            execution_time_ms=execution_time_ms,
            agent_id=self.agent_id,
            model_used=model_used,
            timestamp=datetime.utcnow().isoformat()
        )