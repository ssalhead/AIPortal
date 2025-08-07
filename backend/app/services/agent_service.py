"""
AI 에이전트 서비스
"""

from typing import Dict, Any, List, AsyncGenerator
import logging
import asyncio

from app.agents.base import AgentInput
from app.agents.supervisor import supervisor_agent
from app.agents.workers.web_search import web_search_agent

logger = logging.getLogger(__name__)


class AgentService:
    """AI 에이전트 서비스"""
    
    def __init__(self):
        self.supervisor = supervisor_agent
        self.agents = {
            "supervisor": supervisor_agent,
            "web_search": web_search_agent,
        }
    
    async def execute_chat(
        self, 
        message: str, 
        model: str = "auto",
        agent_type: str = "auto",
        user_id: str = "default_user",
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        채팅 메시지 처리
        
        Args:
            message: 사용자 메시지
            model: 사용할 LLM 모델
            agent_type: 에이전트 타입 (auto는 supervisor가 자동 선택)
            user_id: 사용자 ID
            context: 추가 컨텍스트
            
        Returns:
            처리 결과
        """
        try:
            # LLM 라우터를 통한 최적 모델 선택
            from app.agents.llm_router import llm_router
            
            if model == "auto":
                task_type_mapping = {
                    "web_search": "speed",
                    "supervisor": "reasoning",
                    "auto": "general"
                }
                task_type = task_type_mapping.get(agent_type, "general")
                selected_model = llm_router.get_optimal_model(task_type, len(message))
            else:
                selected_model = model
            
            # 입력 데이터 생성
            agent_input = AgentInput(
                query=message,
                context=context or {},
                user_id=user_id
            )
            
            # 에이전트 선택 및 실행
            if agent_type == "none":
                # 일반 채팅 모드 - 에이전트 없이 LLM 직접 호출
                from app.agents.llm_router import llm_router
                response_text, actual_model = await llm_router.generate_response(
                    selected_model, 
                    message, 
                    user_id=user_id
                )
                
                # AgentResult 형태로 변환
                from app.agents.base import AgentResult
                from datetime import datetime
                result = AgentResult(
                    agent_id="direct_llm",
                    result=response_text,
                    model_used=actual_model,
                    timestamp=datetime.utcnow().isoformat(),
                    metadata={"mode": "direct_chat"},
                    execution_time_ms=0  # 실제 측정은 추후 구현
                )
            elif agent_type == "auto" or agent_type == "supervisor":
                # Supervisor가 자동으로 적절한 에이전트 선택
                result = await self.supervisor.execute(agent_input, selected_model)
            else:
                # 특정 에이전트 직접 실행
                agent = self.agents.get(agent_type)
                if not agent:
                    raise ValueError(f"알 수 없는 에이전트 타입: {agent_type}")
                result = await agent.execute(agent_input, selected_model)
            
            return {
                "response": result.result,
                "agent_used": result.agent_id,
                "model_used": result.model_used,
                "timestamp": result.timestamp,
                "user_id": user_id,
                "metadata": result.metadata,
                "execution_time_ms": result.execution_time_ms
            }
            
        except Exception as e:
            logger.error(f"채팅 처리 중 오류: {e}")
            return {
                "response": f"죄송합니다. 메시지 처리 중 오류가 발생했습니다: {str(e)}",
                "agent_used": "error_handler",
                "model_used": "system",
                "timestamp": "2024-01-01T00:00:00Z",
                "user_id": user_id,
                "metadata": {"error": str(e)},
                "execution_time_ms": 0
            }
    
    def get_agent_info(self, agent_id: str = None) -> List[Dict[str, Any]]:
        """
        에이전트 정보 조회
        
        Args:
            agent_id: 특정 에이전트 ID (None이면 전체 목록)
            
        Returns:
            에이전트 정보 목록
        """
        if agent_id:
            agent = self.agents.get(agent_id)
            if not agent:
                return []
            
            return [{
                "id": agent.agent_id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.get_capabilities(),
                "supported_models": agent.get_supported_models(),
                "is_enabled": True
            }]
        
        # 전체 에이전트 목록
        agent_info_list = []
        for agent_id, agent in self.agents.items():
            if agent_id == "supervisor":
                continue  # Supervisor는 내부 에이전트이므로 목록에서 제외
                
            agent_info_list.append({
                "id": agent.agent_id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.get_capabilities(),
                "supported_models": agent.get_supported_models(),
                "is_enabled": True
            })
        
        # 아직 구현되지 않은 에이전트들도 추가 (비활성화 상태)
        planned_agents = [
            {
                "id": "deep_research",
                "name": "심층 리서치 에이전트",
                "description": "특정 주제에 대해 심층적인 연구를 수행합니다",
                "capabilities": ["심층 분석", "보고서 생성", "다중 소스 종합"],
                "supported_models": ["claude", "gemini", "claude-haiku", "gemini-flash"],
                "is_enabled": False
            },
            {
                "id": "multimodal_rag",
                "name": "멀티모달 RAG 에이전트",
                "description": "문서와 이미지를 분석하여 답변을 생성합니다",
                "capabilities": ["문서 분석", "이미지 이해", "RAG 검색"],
                "supported_models": ["claude", "gemini", "claude-haiku", "gemini-flash"],
                "is_enabled": False
            }
        ]
        
        agent_info_list.extend(planned_agents)
        return agent_info_list
    
    async def execute_agent_directly(
        self,
        agent_id: str,
        input_data: Dict[str, Any],
        model: str = "auto"
    ) -> Dict[str, Any]:
        """
        특정 에이전트 직접 실행
        
        Args:
            agent_id: 에이전트 ID
            input_data: 입력 데이터
            model: 사용할 모델
            
        Returns:
            실행 결과
        """
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                raise ValueError(f"에이전트 '{agent_id}'를 찾을 수 없습니다")
            
            # AgentInput 생성
            agent_input = AgentInput(
                query=input_data.get("query", ""),
                context=input_data.get("context", {}),
                user_id=input_data.get("user_id", "default_user")
            )
            
            # 에이전트 실행
            result = await agent.execute(agent_input, model)
            
            return {
                "agent_id": result.agent_id,
                "result": {
                    "response": result.result,
                    "metadata": result.metadata
                },
                "execution_time_ms": result.execution_time_ms,
                "model_used": result.model_used
            }
            
        except Exception as e:
            logger.error(f"에이전트 '{agent_id}' 직접 실행 중 오류: {e}")
            return {
                "agent_id": agent_id,
                "result": {
                    "response": f"에이전트 실행 중 오류가 발생했습니다: {str(e)}",
                    "metadata": {"error": str(e)}
                },
                "execution_time_ms": 0,
                "model_used": model
            }
    
    async def stream_response(
        self,
        query: str,
        model: str = "auto",
        agent_type: str = "general",
        conversation_id: str = None,
        user_id: str = "default_user"
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 응답 생성
        
        Args:
            query: 사용자 쿼리
            model: 사용할 모델
            agent_type: 에이전트 타입
            conversation_id: 대화 ID
            user_id: 사용자 ID
            
        Yields:
            응답 텍스트 청크
        """
        try:
            # LLM 라우터를 통한 직접 스트리밍
            from app.agents.llm_router import llm_router
            
            # LLM 라우터를 통한 최적 모델 선택
            if model == "auto":
                # 에이전트 유형에 따른 최적 모델 선택
                task_type_mapping = {
                    "web_search": "speed",
                    "technical": "reasoning", 
                    "creative": "creative",
                    "general": "general"
                }
                task_type = task_type_mapping.get(agent_type, "general")
                normalized_model = llm_router.get_optimal_model(task_type, len(query))
            else:
                # 모델 이름 정규화 (새로운 형식 지원)
                model_mapping = {
                    "claude-3-haiku": "claude-haiku",
                    "claude-3-sonnet": "claude", 
                    "claude-3-5-sonnet": "claude-3.5",
                    "claude-3.5": "claude-3.5",
                    "gemini": "gemini-pro",  # 기존 gemini를 gemini-pro로 매핑
                    "gemini-1.5-pro": "gemini-pro",
                    "gemini-1.0-pro": "gemini-1.0",
                    "gemini-flash": "gemini-flash"
                }
                normalized_model = model_mapping.get(model, model)
            
            # 에이전트별 프롬프트 구성
            if agent_type == "none":
                # 일반 채팅 모드 - 간단한 프롬프트
                prompt = query
            elif agent_type == "web_search":
                prompt = f"웹 검색 요청: {query}\n\n최신 정보를 검색하여 정확하고 유용한 답변을 제공해주세요."
            elif agent_type == "technical":
                prompt = f"기술 질문: {query}\n\n기술적으로 정확하고 실용적인 답변을 제공해주세요."
            else:
                prompt = f"사용자 질문: {query}\n\n친근하고 도움이 되는 답변을 제공해주세요."
            
            # 컨텍스트 정보 추가
            if conversation_id:
                prompt += f"\n\n[대화 ID: {conversation_id}]"
            if user_id:
                prompt += f"\n[사용자 ID: {user_id}]"
            
            # LLM 라우터를 통한 스트리밍
            async for chunk in llm_router.stream_response(normalized_model, prompt):
                yield chunk
                
        except Exception as e:
            logger.error(f"스트리밍 응답 생성 중 오류: {e}")
            yield f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"


# 서비스 인스턴스
agent_service = AgentService()