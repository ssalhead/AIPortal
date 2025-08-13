"""
AI 에이전트 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ConversationContext(BaseModel):
    """범용 대화 맥락 정보 모델 - 완전 동적 도메인 분류 지원"""
    recent_messages: List[Dict[str, Any]] = []  # 최근 3-5개 메시지
    conversation_topics: List[str] = []  # 추출된 주요 주제들
    mentioned_entities: List[str] = []  # 언급된 엔티티 (기술, 제품명 등)
    previous_search_queries: List[str] = []  # 이전 검색어들
    conversation_flow: str = ""  # 대화 흐름 요약
    current_focus_topic: Optional[str] = None  # 현재 포커스 주제
    question_depth_level: str = "basic"  # 질문 깊이: basic, intermediate, advanced
    
    # 동적 도메인 분류 필드들
    domain: str = "general"  # 동적으로 생성된 도메인명 (예: 우주항공공학, 푸드테크 등)
    domain_confidence: float = 0.5  # 도메인 분류 신뢰도 (0.0-1.0)
    main_domain: str = "general"  # 주요 도메인
    sub_domains: List[str] = []  # 세부 도메인들
    topic_evolution: List[str] = []  # 주제 진화 과정: ["초기주제", "세부주제", "확장주제"]
    user_intent: str = "정보수집"  # 사용자 의도 (동적 분류)
    context_connection: str = ""  # 현재 질문이 이전 맥락과 연결되는 방식
    search_focus: str = ""  # 검색에서 중점적으로 찾아야 할 내용
    optimal_search_queries: List[str] = []  # LLM이 생성한 최적 검색어들
    
    # 다차원 동적 카테고리
    dynamic_categories: Dict[str, str] = {
        "complexity": "simple",     # simple|moderate|complex
        "urgency": "low",          # low|medium|high
        "scope": "narrow",         # narrow|broad|comprehensive  
        "novelty": "familiar"      # familiar|emerging|cutting_edge
    }


class AgentInput(BaseModel):
    """에이전트 입력 데이터 모델"""
    query: str
    context: Optional[Dict[str, Any]] = None
    user_id: str
    session_id: Optional[str] = None
    conversation_context: Optional[ConversationContext] = None  # 대화 맥락 정보


class AgentOutput(BaseModel):
    """에이전트 출력 데이터 모델 - 모든 에이전트 실행 결과의 표준 형식"""
    result: str
    metadata: Dict[str, Any]
    execution_time_ms: int
    agent_id: str
    model_used: str
    timestamp: str
    canvas_data: Optional[Dict[str, Any]] = None  # Canvas 시각화 데이터
    citations: Optional[List[Dict[str, Any]]] = None  # 인용 정보
    sources: Optional[List[Dict[str, Any]]] = None  # 출처 정보
    error: Optional[str] = None  # 에러 메시지


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