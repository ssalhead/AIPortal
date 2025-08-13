"""
Supervisor 에이전트 - 사용자 요청을 분석하고 적절한 Worker 에이전트에게 분배
"""

import time
from typing import Dict, Any, Optional
from enum import Enum
import logging

from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.llm_router import llm_router
from app.agents.workers.web_search import web_search_agent

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """작업 유형"""
    WEB_SEARCH = "web_search"
    DEEP_RESEARCH = "deep_research"
    MULTIMODAL_RAG = "multimodal_rag"
    CANVAS = "canvas"
    GENERAL_CHAT = "general_chat"


class SupervisorAgent(BaseAgent):
    """Supervisor 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_id="supervisor",
            name="Supervisor 에이전트",
            description="사용자 요청을 분석하고 적절한 Worker 에이전트에게 분배합니다"
        )
        
        # Worker 에이전트 등록
        self.workers = {
            TaskType.WEB_SEARCH: web_search_agent,
            # TaskType.DEEP_RESEARCH: deep_research_agent,  # 추후 구현
            # TaskType.MULTIMODAL_RAG: multimodal_rag_agent,  # 추후 구현
        }
    
    async def execute(self, input_data: AgentInput, model: str = "gemini", progress_callback=None) -> AgentOutput:
        """Supervisor 에이전트 실행"""
        start_time = time.time()
        
        if not self.validate_input(input_data):
            raise ValueError("유효하지 않은 입력 데이터")
        
        try:
            # 작업 유형 분석
            task_type = await self._analyze_task_type(input_data.query, model)
            
            # 적절한 Worker 에이전트 선택
            worker_agent = self._select_worker(task_type)
            
            if worker_agent:
                # Worker 에이전트 실행 (progress_callback 전달)
                self.logger.info(f"작업을 {task_type.value} 에이전트에게 위임")
                result = await worker_agent.execute(input_data, model, progress_callback)
                
                # Supervisor 메타데이터 추가
                result.metadata["supervisor_decision"] = task_type.value
                result.metadata["delegated_to"] = worker_agent.agent_id
                
                return result
            else:
                # 사용할 수 있는 Worker가 없는 경우 직접 처리
                return await self._handle_directly(input_data, model, start_time)
                
        except Exception as e:
            self.logger.error(f"Supervisor 실행 중 오류: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return self.create_output(
                result=f"죄송합니다. 요청 처리 중 오류가 발생했습니다: {str(e)}",
                metadata={"error": str(e)},
                execution_time_ms=execution_time,
                model_used=model
            )
    
    async def _analyze_task_type(self, query: str, model: str) -> TaskType:
        """사용자 쿼리를 분석하여 작업 유형 결정"""
        try:
            prompt = f"""
사용자의 질문을 분석하여 가장 적합한 작업 유형을 결정해주세요.

사용자 질문: "{query}"

작업 유형:
1. web_search: 최신 정보 검색, 실시간 데이터 조회, 일반적인 정보 검색
2. deep_research: 심층적인 분석이 필요한 복잡한 주제, 종합적인 보고서 작성
3. multimodal_rag: 문서나 이미지 분석, 파일 기반 질문 답변
4. canvas: 이미지 생성, 마인드맵, 메모, 시각적 창작 요청
5. general_chat: 일반적인 대화, 간단한 질문, 창작 요청

다음 중 하나만 반환해주세요: web_search, deep_research, multimodal_rag, canvas, general_chat
"""
            
            response, _ = await llm_router.generate_response(model, prompt)
            task_type_str = response.strip().lower()
            
            # TaskType으로 변환
            if task_type_str == "web_search":
                return TaskType.WEB_SEARCH
            elif task_type_str == "deep_research":
                return TaskType.DEEP_RESEARCH
            elif task_type_str == "multimodal_rag":
                return TaskType.MULTIMODAL_RAG
            elif task_type_str == "canvas":
                return TaskType.CANVAS
            else:
                return TaskType.GENERAL_CHAT
                
        except Exception as e:
            self.logger.warning(f"작업 유형 분석 실패, 기본값 사용: {e}")
            # 기본적으로 웹 검색으로 처리
            return TaskType.WEB_SEARCH
    
    def _select_worker(self, task_type: TaskType) -> Optional[BaseAgent]:
        """작업 유형에 따른 Worker 에이전트 선택"""
        worker = self.workers.get(task_type)
        if worker:
            return worker
        
        # 해당 Worker가 없는 경우 대체 Worker 선택
        if task_type == TaskType.DEEP_RESEARCH:
            # Deep Research가 없으면 Web Search로 대체
            return self.workers.get(TaskType.WEB_SEARCH)
        elif task_type == TaskType.MULTIMODAL_RAG:
            # Multimodal RAG가 없으면 Web Search로 대체
            return self.workers.get(TaskType.WEB_SEARCH)
        
        return None
    
    async def _handle_directly(self, input_data: AgentInput, model: str, start_time: float) -> AgentOutput:
        """Supervisor가 직접 처리"""
        try:
            prompt = f"""
사용자 질문: "{input_data.query}"

위 질문에 대해 도움이 되는 답변을 제공해주세요.
현재 특별한 도구나 검색 기능을 사용할 수 없지만, 
가능한 한 유용하고 정확한 정보를 제공해주세요.

답변은 한국어로 자연스럽게 작성해주세요.
"""
            
            response, _ = await llm_router.generate_response(model, prompt)
            execution_time = int((time.time() - start_time) * 1000)
            
            return self.create_output(
                result=response,
                metadata={
                    "handled_by": "supervisor_direct",
                    "reason": "no_suitable_worker_available"
                },
                execution_time_ms=execution_time,
                model_used=model
            )
            
        except Exception as e:
            self.logger.error(f"직접 처리 중 오류: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return self.create_output(
                result="죄송합니다. 현재 요청을 처리할 수 없습니다.",
                metadata={"error": str(e)},
                execution_time_ms=execution_time,
                model_used=model
            )
    
    def get_capabilities(self) -> list[str]:
        """Supervisor 기능 목록"""
        return [
            "요청 분석",
            "작업 분배",
            "Worker 관리",
            "응답 조정"
        ]
    
    def get_supported_models(self) -> list[str]:
        """지원하는 모델 목록"""
        return ["gemini", "claude", "openai"]
    
    def get_available_workers(self) -> Dict[str, str]:
        """사용 가능한 Worker 에이전트 목록"""
        return {
            task_type.value: worker.name 
            for task_type, worker in self.workers.items()
        }
    
    async def analyze_and_suggest_agent(self, query: str, current_agent: str, model: str = "gemini") -> Dict[str, Any]:
        """현재 에이전트와 다른 더 적합한 에이전트를 제안"""
        try:
            # 사용자 쿼리 분석
            suggested_task_type = await self._analyze_task_type(query, model)
            suggested_agent = suggested_task_type.value
            
            # 현재 에이전트와 다른 경우에만 제안
            if suggested_agent != current_agent and suggested_agent != "general_chat":
                # 상세 분석으로 신뢰도 및 이유 생성
                confidence, reason = await self._analyze_suggestion_details(
                    query, current_agent, suggested_agent, model
                )
                
                return {
                    "needs_switch": True,
                    "suggested_agent": suggested_agent,
                    "confidence": confidence,
                    "reason": reason,
                    "current_agent": current_agent
                }
            
            return {"needs_switch": False}
            
        except Exception as e:
            self.logger.error(f"에이전트 제안 분석 실패: {e}")
            return {"needs_switch": False, "error": str(e)}
    
    async def _analyze_suggestion_details(self, query: str, current_agent: str, suggested_agent: str, model: str) -> tuple[float, str]:
        """제안 상세 분석 - 신뢰도와 이유 생성"""
        try:
            agent_descriptions = {
                "none": "일반 채팅",
                "web_search": "웹 검색을 통한 최신 정보 조회",
                "deep_research": "심층적인 분석과 연구",
                "canvas": "이미지 생성, 마인드맵, 시각적 창작",
                "multimodal_rag": "문서 및 이미지 분석"
            }
            
            prompt = f"""
사용자 질문을 분석하여 에이전트 전환이 필요한 이유와 신뢰도를 평가해주세요.

사용자 질문: "{query}"
현재 에이전트: {agent_descriptions.get(current_agent, current_agent)}
제안 에이전트: {agent_descriptions.get(suggested_agent, suggested_agent)}

다음 형식으로 응답해주세요:
신뢰도: [0.1-1.0 사이의 숫자]
이유: [한 문장으로 간단명료하게]

예시:
신뢰도: 0.9
이유: 최신 주가 정보 조회는 웹 검색이 더 정확한 결과를 제공할 수 있습니다
"""
            
            response, _ = await llm_router.generate_response(model, prompt)
            lines = response.strip().split('\n')
            
            confidence = 0.7  # 기본값
            reason = f"{agent_descriptions.get(suggested_agent, suggested_agent)}가 이 작업에 더 적합할 수 있습니다"
            
            for line in lines:
                if line.startswith('신뢰도:'):
                    try:
                        confidence = float(line.split(':')[1].strip())
                        confidence = max(0.1, min(1.0, confidence))  # 범위 제한
                    except:
                        pass
                elif line.startswith('이유:'):
                    reason = line.split(':', 1)[1].strip()
            
            return confidence, reason
            
        except Exception as e:
            self.logger.warning(f"제안 상세 분석 실패: {e}")
            return 0.7, f"{suggested_agent.replace('_', ' ')}이 더 적합할 수 있습니다"


# Supervisor 에이전트 인스턴스
supervisor_agent = SupervisorAgent()