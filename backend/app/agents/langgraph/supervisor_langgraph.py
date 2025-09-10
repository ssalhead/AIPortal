"""
LangGraph 기반 Supervisor Agent - 완전한 지능형 라우팅 및 워크플로우 관리 시스템

최신 LangGraph StateGraph를 활용하여 복잡한 사용자 요청을 분석하고 
적절한 Worker 에이전트들에게 최적화된 방식으로 분배하는 고급 관리 시스템입니다.
"""

import time
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, TypedDict, Union, Annotated, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import logging
import operator

# LangGraph 핵심 imports
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Send
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

# 기존 시스템 imports
from app.agents.base import BaseAgent, AgentInput, AgentOutput, ConversationContext
from app.agents.supervisor import supervisor_agent, IntentType
from app.agents.routing.intent_classifier import dynamic_intent_classifier
from app.agents.langgraph.web_search_langgraph import langgraph_web_search_agent
from app.agents.langgraph.canvas_langgraph import langgraph_canvas_agent
from app.agents.langgraph.information_gap_langgraph import langgraph_information_gap_analyzer
from app.agents.langgraph.parallel_processor import langgraph_parallel_processor
from app.core.config import settings
from app.core.feature_flags import is_langgraph_enabled, LangGraphFeatureFlags
from app.services.langgraph_monitor import langgraph_monitor

logger = logging.getLogger(__name__)


class SupervisorState(TypedDict):
    """LangGraph Supervisor 상태 정의"""
    # 입력 데이터
    original_query: str
    user_id: str
    session_id: Optional[str]
    conversation_context: Optional[Dict[str, Any]]
    model: str
    
    # 분석 단계
    intent_analysis: Optional[Dict[str, Any]]
    context_evaluation: Optional[Dict[str, Any]]
    complexity_assessment: Optional[Dict[str, Any]]
    
    # 라우팅 전략
    routing_strategy: Optional[Dict[str, Any]]
    selected_agents: Optional[List[Dict[str, Any]]]
    execution_plan: Optional[Dict[str, Any]]
    
    # 실행 결과 수집 (Reducer 사용)
    agent_results: Annotated[List[Dict[str, Any]], operator.add]
    parallel_results: Optional[List[Dict[str, Any]]]
    
    # 결과 통합
    integrated_response: Optional[str]
    final_output: Optional[str]
    
    # 성능 및 품질 메트릭
    execution_metadata: Dict[str, Any]
    quality_metrics: Dict[str, Any]
    routing_confidence: float
    
    # 에러 처리 및 fallback
    errors: Annotated[List[str], operator.add]
    fallback_attempts: Annotated[List[Dict[str, Any]], operator.add]
    should_fallback: bool


class AgentType(Enum):
    """에이전트 유형"""
    WEB_SEARCH = "web_search"
    CANVAS = "canvas"
    INFORMATION_GAP = "information_gap"
    PARALLEL_PROCESSOR = "parallel_processor"
    MULTIMODAL_RAG = "multimodal_rag"
    GENERAL_CHAT = "general_chat"


class ExecutionMode(Enum):
    """실행 모드"""
    SINGLE_AGENT = "single_agent"          # 단일 에이전트 실행
    SEQUENTIAL = "sequential"              # 순차 실행
    PARALLEL = "parallel"                  # 병렬 실행
    CONDITIONAL = "conditional"            # 조건부 실행
    INTERACTIVE = "interactive"            # 대화형 실행


@dataclass
class AgentSelection:
    """에이전트 선택 정보"""
    agent_type: AgentType
    confidence: float
    priority: int
    expected_execution_time: float
    resource_requirements: Dict[str, Any]
    dependencies: List[str] = None


class LangGraphSupervisorAgent(BaseAgent):
    """LangGraph 기반 Supervisor Agent"""
    
    def __init__(self):
        super().__init__(
            agent_id="langgraph_supervisor",
            name="LangGraph Supervisor 에이전트",
            description="LangGraph StateGraph로 구현된 고급 워크플로우 관리 시스템"
        )
        
        # 레거시 Supervisor (fallback용)
        self.legacy_supervisor = supervisor_agent
        
        # Worker 에이전트 등록
        self.worker_agents = {
            AgentType.WEB_SEARCH: langgraph_web_search_agent,
            AgentType.CANVAS: langgraph_canvas_agent,
            AgentType.INFORMATION_GAP: langgraph_information_gap_analyzer,
            AgentType.PARALLEL_PROCESSOR: langgraph_parallel_processor,
            # AgentType.MULTIMODAL_RAG: langgraph_multimodal_rag,  # 추후 구현
        }
        
        # LangGraph 워크플로우 구성
        self.workflow = self._build_workflow()
        
        # PostgreSQL 체크포인터 설정
        if settings.DATABASE_URL:
            self.checkpointer = PostgresSaver.from_conn_string(
                settings.DATABASE_URL,
                
            )
        else:
            self.checkpointer = None
            logger.warning("DATABASE_URL이 설정되지 않음 - 체크포인터 비활성화")

    def _build_workflow(self) -> StateGraph:
        """LangGraph Supervisor 워크플로우 구성"""
        
        # StateGraph 생성
        workflow = StateGraph(SupervisorState)
        
        # 노드 정의 - 8단계 고도화된 관리 파이프라인
        workflow.add_node("analyze_intent", self._analyze_intent_node)
        workflow.add_node("evaluate_context", self._evaluate_context_node)
        workflow.add_node("assess_complexity", self._assess_complexity_node)
        workflow.add_node("plan_routing_strategy", self._plan_routing_strategy_node)
        workflow.add_node("select_agents", self._select_agents_node)
        workflow.add_node("execute_agents", self._execute_agents_node)
        workflow.add_node("integrate_results", self._integrate_results_node)
        workflow.add_node("finalize_response", self._finalize_response_node)
        
        # 엣지 정의 - 선형 파이프라인
        workflow.set_entry_point("analyze_intent")
        workflow.add_edge("analyze_intent", "evaluate_context")
        workflow.add_edge("evaluate_context", "assess_complexity")
        workflow.add_edge("assess_complexity", "plan_routing_strategy")
        workflow.add_edge("plan_routing_strategy", "select_agents")
        workflow.add_edge("select_agents", "execute_agents")
        workflow.add_edge("execute_agents", "integrate_results")
        workflow.add_edge("integrate_results", "finalize_response")
        workflow.add_edge("finalize_response", END)
        
        # 조건부 엣지 (복잡한 라우팅 로직)
        workflow.add_conditional_edges(
            "analyze_intent",
            self._should_continue,
            {
                "continue": "evaluate_context",
                "fallback": END
            }
        )
        
        workflow.add_conditional_edges(
            "plan_routing_strategy",
            self._determine_execution_mode,
            {
                "single_agent": "select_agents",
                "parallel": "select_agents",
                "sequential": "select_agents",
                "interactive": "execute_agents"  # 바로 실행으로
            }
        )
        
        workflow.add_conditional_edges(
            "integrate_results",
            self._should_retry_failed_agents,
            {
                "retry": "execute_agents",
                "continue": "finalize_response"
            }
        )
        
        return workflow

    async def _analyze_intent_node(self, state: SupervisorState) -> Dict[str, Any]:
        """의도 분석 노드 - 고급 의도 분류 및 파악"""
        try:
            logger.info(f"🧠 LangGraph Supervisor: 의도 분석 중... (query: {state['original_query'][:50]})")
            
            model = self._get_llm_model(state["model"])
            
            # 기존 dynamic_intent_classifier 활용하되 더 상세한 분석
            intent_prompt = ChatPromptTemplate.from_messages([
                ("system", """고급 의도 분석 전문가로서 사용자의 질문을 다층적으로 분석하세요.

분석 항목:
1. 주요 의도 (primary_intent): web_search, canvas, general_chat, multi_step, etc.
2. 부차적 의도들 (secondary_intents): 복합적 요구사항
3. 감정적 맥락 (emotional_context): 긴급성, 중요도, 감정 상태
4. 기술적 복잡도 (technical_complexity): 단순/보통/복잡/고급
5. 상호작용 요구도 (interaction_level): 일회성/대화형/연속형
6. 개인화 필요성 (personalization_need): 없음/보통/높음/매우높음
7. 실시간성 요구 (real_time_requirement): 없음/선호/필수

각 항목에 대해 신뢰도와 근거를 포함하여 JSON으로 응답하세요."""),
                ("human", """질문: "{query}"
대화 맥락: {context}

이 질문을 다층적으로 분석해주세요.""")
            ])
            
            context = state.get("conversation_context", {})
            response = await model.ainvoke(intent_prompt.format_messages(
                query=state["original_query"],
                context=json.dumps(context, ensure_ascii=False) if context else "없음"
            ))
            
            try:
                intent_analysis = json.loads(response.content)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본 분석
                intent_analysis = {
                    "primary_intent": "general_chat",
                    "secondary_intents": [],
                    "emotional_context": {"urgency": "normal", "importance": "medium"},
                    "technical_complexity": "보통",
                    "interaction_level": "일회성",
                    "personalization_need": "보통",
                    "real_time_requirement": "없음",
                    "confidence": 0.7
                }
            
            return {
                "intent_analysis": intent_analysis,
                "routing_confidence": intent_analysis.get("confidence", 0.7),
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "intent_analysis_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 의도 분석 실패: {e}")
            return {
                "errors": [f"의도 분석 실패: {str(e)}"],
                "should_fallback": True
            }

    async def _evaluate_context_node(self, state: SupervisorState) -> Dict[str, Any]:
        """컨텍스트 평가 노드 - 대화 맥락 및 사용자 상황 분석"""
        try:
            logger.info("🧠 LangGraph Supervisor: 컨텍스트 평가 중...")
            
            model = self._get_llm_model(state["model"])
            context = state.get("conversation_context", {})
            intent_analysis = state.get("intent_analysis", {})
            
            context_prompt = ChatPromptTemplate.from_messages([
                ("system", """대화 맥락 평가 전문가로서 다음을 종합 분석하세요:

평가 항목:
1. 대화 연속성 (continuity): 이전 대화와의 연관성
2. 정보 축적도 (information_accumulation): 대화 중 수집된 정보량
3. 사용자 상태 (user_state): 만족도, 혼란도, 진행도
4. 맥락 완결성 (context_completeness): 필요한 배경 정보 충족도
5. 워크플로우 단계 (workflow_stage): 초기/중간/종료 단계
6. 개인화 수준 (personalization_level): 개별 맞춤 정도

JSON 형식으로 종합 평가 결과를 제공하세요."""),
                ("human", """현재 질문: "{query}"
의도 분석 결과: {intent_analysis}
대화 컨텍스트: {context}

컨텍스트를 종합 평가해주세요.""")
            ])
            
            response = await model.ainvoke(context_prompt.format_messages(
                query=state["original_query"],
                intent_analysis=json.dumps(intent_analysis, ensure_ascii=False, indent=2),
                context=json.dumps(context, ensure_ascii=False, indent=2) if context else "없음"
            ))
            
            try:
                context_evaluation = json.loads(response.content)
            except json.JSONDecodeError:
                context_evaluation = {
                    "continuity": 0.5,
                    "information_accumulation": 0.3,
                    "user_state": {"satisfaction": 0.7, "confusion": 0.2, "progress": 0.5},
                    "context_completeness": 0.6,
                    "workflow_stage": "중간",
                    "personalization_level": 0.4,
                    "confidence": 0.6
                }
            
            return {
                "context_evaluation": context_evaluation,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "context_evaluation_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 컨텍스트 평가 실패: {e}")
            return {
                "errors": [f"컨텍스트 평가 실패: {str(e)}"]
            }

    async def _assess_complexity_node(self, state: SupervisorState) -> Dict[str, Any]:
        """복잡도 평가 노드 - 작업 복잡도 및 리소스 요구사항 분석"""
        try:
            logger.info("🧠 LangGraph Supervisor: 복잡도 평가 중...")
            
            model = self._get_llm_model(state["model"])
            intent_analysis = state.get("intent_analysis", {})
            context_evaluation = state.get("context_evaluation", {})
            
            complexity_prompt = ChatPromptTemplate.from_messages([
                ("system", """작업 복잡도 평가 전문가로서 다음을 분석하세요:

평가 기준:
1. 정보 처리 복잡도 (1-5): 필요한 정보의 양과 복잡성
2. 계산 복잡도 (1-5): 처리에 필요한 연산량
3. 상호작용 복잡도 (1-5): 사용자와의 상호작용 횟수/복잡성
4. 통합 복잡도 (1-5): 여러 소스/결과 통합의 어려움
5. 시간 민감도 (1-5): 실시간 처리 요구도
6. 예상 처리 시간 (초): 전체 처리 예상 시간
7. 추천 실행 모드: single_agent/sequential/parallel/interactive

JSON 형식으로 상세한 복잡도 분석을 제공하세요."""),
                ("human", """질문: "{query}"
의도 분석: {intent_analysis}
컨텍스트 평가: {context_evaluation}

이 작업의 복잡도를 종합 평가해주세요.""")
            ])
            
            response = await model.ainvoke(complexity_prompt.format_messages(
                query=state["original_query"],
                intent_analysis=json.dumps(intent_analysis, ensure_ascii=False),
                context_evaluation=json.dumps(context_evaluation, ensure_ascii=False)
            ))
            
            try:
                complexity_assessment = json.loads(response.content)
            except json.JSONDecodeError:
                complexity_assessment = {
                    "information_processing": 3,
                    "computational": 2,
                    "interaction": 2,
                    "integration": 2,
                    "time_sensitivity": 2,
                    "estimated_processing_time": 10.0,
                    "recommended_execution_mode": "single_agent",
                    "overall_complexity": "보통"
                }
            
            return {
                "complexity_assessment": complexity_assessment,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "complexity_assessment_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 복잡도 평가 실패: {e}")
            return {
                "errors": [f"복잡도 평가 실패: {str(e)}"]
            }

    async def _plan_routing_strategy_node(self, state: SupervisorState) -> Dict[str, Any]:
        """라우팅 전략 수립 노드"""
        try:
            logger.info("🧠 LangGraph Supervisor: 라우팅 전략 수립 중...")
            
            model = self._get_llm_model(state["model"])
            intent_analysis = state.get("intent_analysis", {})
            complexity_assessment = state.get("complexity_assessment", {})
            
            strategy_prompt = ChatPromptTemplate.from_messages([
                ("system", """라우팅 전략 수립 전문가로서 최적의 실행 전략을 수립하세요.

사용 가능한 에이전트들:
- web_search: 웹 검색 및 정보 수집
- canvas: 시각적 콘텐츠 생성 (이미지, 마인드맵 등)
- information_gap: 정보 부족 분석 및 추가 정보 요청
- parallel_processor: 병렬 처리를 통한 고성능 작업
- general_chat: 일반 대화 처리

실행 모드:
- single_agent: 하나의 에이전트로 처리
- sequential: 여러 에이전트를 순차적으로 실행
- parallel: 여러 에이전트를 동시 실행
- interactive: 사용자 상호작용 필요

JSON 형식으로 상세한 라우팅 전략을 제공하세요."""),
                ("human", """질문: "{query}"
의도 분석: {intent_analysis}
복잡도 평가: {complexity_assessment}

최적의 라우팅 전략을 수립해주세요.""")
            ])
            
            response = await model.ainvoke(strategy_prompt.format_messages(
                query=state["original_query"],
                intent_analysis=json.dumps(intent_analysis, ensure_ascii=False),
                complexity_assessment=json.dumps(complexity_assessment, ensure_ascii=False)
            ))
            
            try:
                routing_strategy = json.loads(response.content)
            except json.JSONDecodeError:
                # 기본 라우팅 전략
                primary_intent = intent_analysis.get("primary_intent", "general_chat")
                routing_strategy = {
                    "execution_mode": "single_agent",
                    "primary_agent": self._map_intent_to_agent(primary_intent),
                    "backup_agents": [],
                    "parallel_eligible": False,
                    "interaction_required": False,
                    "estimated_total_time": 10.0,
                    "confidence": 0.7
                }
            
            return {
                "routing_strategy": routing_strategy,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "routing_strategy_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 라우팅 전략 수립 실패: {e}")
            return {
                "errors": [f"라우팅 전략 수립 실패: {str(e)}"]
            }

    async def _select_agents_node(self, state: SupervisorState) -> Dict[str, Any]:
        """에이전트 선택 노드"""
        try:
            logger.info("🧠 LangGraph Supervisor: 에이전트 선택 중...")
            
            routing_strategy = state.get("routing_strategy", {})
            complexity_assessment = state.get("complexity_assessment", {})
            
            # 선택된 에이전트들
            selected_agents = []
            
            execution_mode = routing_strategy.get("execution_mode", "single_agent")
            primary_agent = routing_strategy.get("primary_agent", "general_chat")
            
            if execution_mode == "single_agent":
                selected_agents.append({
                    "agent_type": primary_agent,
                    "priority": 1,
                    "expected_time": complexity_assessment.get("estimated_processing_time", 10.0),
                    "confidence": routing_strategy.get("confidence", 0.7)
                })
            elif execution_mode in ["sequential", "parallel"]:
                # 주요 에이전트
                selected_agents.append({
                    "agent_type": primary_agent,
                    "priority": 1,
                    "expected_time": complexity_assessment.get("estimated_processing_time", 10.0) * 0.6,
                    "confidence": routing_strategy.get("confidence", 0.7)
                })
                
                # 백업 에이전트들
                backup_agents = routing_strategy.get("backup_agents", [])
                for i, backup_agent in enumerate(backup_agents[:2]):  # 최대 2개
                    selected_agents.append({
                        "agent_type": backup_agent,
                        "priority": i + 2,
                        "expected_time": complexity_assessment.get("estimated_processing_time", 10.0) * 0.4,
                        "confidence": 0.6
                    })
            
            # 실행 계획 생성
            execution_plan = {
                "mode": execution_mode,
                "agents": selected_agents,
                "total_estimated_time": sum(a.get("expected_time", 0) for a in selected_agents),
                "parallel_eligible": routing_strategy.get("parallel_eligible", False),
                "fallback_strategy": "legacy_supervisor"
            }
            
            return {
                "selected_agents": selected_agents,
                "execution_plan": execution_plan,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "agent_selection_completed_at": time.time(),
                    "selected_agents_count": len(selected_agents)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 에이전트 선택 실패: {e}")
            return {
                "errors": [f"에이전트 선택 실패: {str(e)}"]
            }

    async def _execute_agents_node(self, state: SupervisorState) -> Dict[str, Any]:
        """에이전트 실행 노드"""
        try:
            logger.info("🚀 LangGraph Supervisor: 에이전트 실행 중...")
            
            execution_plan = state.get("execution_plan", {})
            selected_agents = state.get("selected_agents", [])
            
            if not selected_agents:
                return {"errors": ["선택된 에이전트가 없습니다"]}
            
            agent_results = []
            execution_mode = execution_plan.get("mode", "single_agent")
            
            # 실행 모드별 처리
            if execution_mode == "single_agent":
                # 단일 에이전트 실행
                primary_agent = selected_agents[0]
                result = await self._execute_single_agent(primary_agent, state)
                agent_results.append(result)
                
            elif execution_mode == "sequential":
                # 순차 실행
                for agent_config in selected_agents:
                    result = await self._execute_single_agent(agent_config, state)
                    agent_results.append(result)
                    
                    # 실패 시 다음 에이전트로 fallback 가능
                    if result.get("success", False):
                        break
                        
            elif execution_mode == "parallel":
                # 병렬 실행
                tasks = []
                for agent_config in selected_agents:
                    task = self._execute_single_agent(agent_config, state)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        agent_results.append({
                            "agent_type": selected_agents[i].get("agent_type", "unknown"),
                            "success": False,
                            "error": str(result),
                            "execution_time": 0
                        })
                    else:
                        agent_results.append(result)
            
            return {
                "agent_results": agent_results,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "agents_execution_completed_at": time.time(),
                    "executed_agents_count": len(agent_results)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 에이전트 실행 실패: {e}")
            return {
                "errors": [f"에이전트 실행 실패: {str(e)}"]
            }

    async def _integrate_results_node(self, state: SupervisorState) -> Dict[str, Any]:
        """결과 통합 노드"""
        try:
            logger.info("🔄 LangGraph Supervisor: 결과 통합 중...")
            
            agent_results = state.get("agent_results", [])
            intent_analysis = state.get("intent_analysis", {})
            
            if not agent_results:
                return {"integrated_response": "에이전트 실행 결과가 없습니다."}
            
            # 성공한 결과들만 필터링
            successful_results = [r for r in agent_results if r.get("success", False)]
            
            if not successful_results:
                return {
                    "integrated_response": "모든 에이전트 실행이 실패했습니다.",
                    "errors": [f"실행 실패: {r.get('error', 'Unknown error')}" for r in agent_results]
                }
            
            model = self._get_llm_model(state["model"])
            
            integration_prompt = ChatPromptTemplate.from_messages([
                ("system", """결과 통합 전문가로서 여러 에이전트의 실행 결과를 종합하여 최적의 답변을 생성하세요.

통합 원칙:
1. 가장 관련성 높은 결과를 우선 활용
2. 중복된 정보는 제거하고 보완 정보는 추가
3. 사용자의 원래 의도에 맞게 구성
4. 신뢰할 수 있는 정보와 추론된 정보 구분
5. 자연스럽고 이해하기 쉬운 형태로 정리

한국어로 완전하고 유용한 답변을 생성해주세요."""),
                ("human", """원본 질문: "{query}"
사용자 의도: {intent}

에이전트 실행 결과들:
{results}

이 결과들을 종합하여 최적의 답변을 생성해주세요.""")
            ])
            
            # 결과 요약 생성
            results_summary = []
            for result in successful_results:
                agent_type = result.get("agent_type", "unknown")
                response = result.get("response", "")
                metadata = result.get("metadata", {})
                
                results_summary.append({
                    "agent": agent_type,
                    "response": response[:500],  # 500자 제한
                    "confidence": metadata.get("confidence", 0.7),
                    "execution_time": result.get("execution_time", 0)
                })
            
            response = await model.ainvoke(integration_prompt.format_messages(
                query=state["original_query"],
                intent=json.dumps(intent_analysis, ensure_ascii=False),
                results=json.dumps(results_summary, ensure_ascii=False, indent=2)
            ))
            
            integrated_response = response.content
            
            # 품질 메트릭 계산
            quality_metrics = {
                "successful_agents": len(successful_results),
                "total_agents": len(agent_results),
                "success_rate": len(successful_results) / len(agent_results) * 100,
                "avg_confidence": sum(r.get("metadata", {}).get("confidence", 0.7) for r in successful_results) / len(successful_results),
                "total_execution_time": sum(r.get("execution_time", 0) for r in agent_results)
            }
            
            return {
                "integrated_response": integrated_response,
                "quality_metrics": quality_metrics,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "integration_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 결과 통합 실패: {e}")
            return {
                "errors": [f"결과 통합 실패: {str(e)}"],
                "integrated_response": "결과 통합 중 오류가 발생했습니다."
            }

    async def _finalize_response_node(self, state: SupervisorState) -> Dict[str, Any]:
        """최종 응답 생성 노드"""
        try:
            logger.info("🎯 LangGraph Supervisor: 최종 응답 생성 중...")
            
            integrated_response = state.get("integrated_response", "")
            quality_metrics = state.get("quality_metrics", {})
            routing_confidence = state.get("routing_confidence", 0.7)
            
            # 최종 응답에 품질 및 성능 정보 추가 (개발 모드에서만)
            final_output = integrated_response
            
            if settings.DEBUG and quality_metrics:
                success_rate = quality_metrics.get("success_rate", 0)
                avg_confidence = quality_metrics.get("avg_confidence", 0.7)
                
                if success_rate < 100:
                    final_output += f"\n\n*처리 성공률: {success_rate:.1f}%*"
                
                if routing_confidence > 0.9:
                    final_output += "\n\n*LangGraph 고성능 라우팅으로 처리되었습니다.*"
            
            return {
                "final_output": final_output,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "finalization_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 최종 응답 생성 실패: {e}")
            return {
                "final_output": "최종 응답 생성 중 오류가 발생했습니다.",
                "errors": [f"최종 응답 실패: {str(e)}"]
            }

    # 유틸리티 메서드들

    def _should_continue(self, state: SupervisorState) -> str:
        """조건부 라우팅: 계속 진행 여부 결정"""
        if state.get("should_fallback", False) or len(state.get("errors", [])) > 3:
            return "fallback"
        return "continue"

    def _determine_execution_mode(self, state: SupervisorState) -> str:
        """조건부 라우팅: 실행 모드 결정"""
        routing_strategy = state.get("routing_strategy", {})
        execution_mode = routing_strategy.get("execution_mode", "single_agent")
        
        # 유효한 실행 모드인지 확인
        valid_modes = ["single_agent", "parallel", "sequential", "interactive"]
        if execution_mode in valid_modes:
            return execution_mode
        return "single_agent"

    def _should_retry_failed_agents(self, state: SupervisorState) -> str:
        """조건부 라우팅: 실패한 에이전트 재시도 여부"""
        quality_metrics = state.get("quality_metrics", {})
        success_rate = quality_metrics.get("success_rate", 100)
        retry_count = state.get("execution_metadata", {}).get("retry_count", 0)
        
        if success_rate < 50 and retry_count < 1:  # 성공률 50% 미만이고 재시도 1회 미만
            return "retry"
        return "continue"

    def _get_llm_model(self, model_name: str):
        """LLM 모델 인스턴스 반환"""
        if "claude" in model_name.lower():
            return ChatAnthropic(
                model_name=model_name,
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.2
            )
        elif "gemini" in model_name.lower():
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.2
            )
        else:
            return ChatAnthropic(
                model_name="claude-3-sonnet-20240229",
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.2
            )

    def _map_intent_to_agent(self, intent: str) -> str:
        """의도를 에이전트 타입으로 매핑"""
        intent_mapping = {
            "web_search": "web_search",
            "deep_research": "web_search",
            "canvas": "canvas",
            "general_chat": "general_chat",
            "multi_step": "parallel_processor",
            "clarification": "information_gap"
        }
        return intent_mapping.get(intent, "general_chat")

    async def _execute_single_agent(self, agent_config: Dict[str, Any], state: SupervisorState) -> Dict[str, Any]:
        """단일 에이전트 실행"""
        start_time = time.time()
        
        try:
            agent_type_str = agent_config.get("agent_type", "general_chat")
            
            # 에이전트 타입 변환
            try:
                agent_type = AgentType(agent_type_str)
            except ValueError:
                agent_type = AgentType.GENERAL_CHAT
            
            # 해당 에이전트 가져오기
            worker_agent = self.worker_agents.get(agent_type)
            
            if not worker_agent:
                return {
                    "agent_type": agent_type_str,
                    "success": False,
                    "error": f"에이전트 {agent_type_str}를 찾을 수 없습니다",
                    "execution_time": time.time() - start_time
                }
            
            # 에이전트 실행을 위한 입력 준비
            agent_input = AgentInput(
                query=state["original_query"],
                user_id=state["user_id"],
                session_id=state["session_id"],
                context=state.get("conversation_context", {})
            )
            
            # 에이전트 실행
            result = await worker_agent.execute(agent_input, state["model"])
            
            execution_time = time.time() - start_time
            
            return {
                "agent_type": agent_type_str,
                "success": True,
                "response": result.result,
                "metadata": result.metadata,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"단일 에이전트 실행 실패 ({agent_config.get('agent_type', 'unknown')}): {e}")
            
            return {
                "agent_type": agent_config.get("agent_type", "unknown"),
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }

    async def execute(self, input_data: AgentInput, model: str = "claude-sonnet", progress_callback=None) -> AgentOutput:
        """
        LangGraph Supervisor Agent 실행
        Feature Flag에 따라 LangGraph 또는 Legacy 모드로 실행
        """
        start_time = time.time()
        
        # Feature Flag 확인
        if not is_langgraph_enabled(
            LangGraphFeatureFlags.LANGGRAPH_SUPERVISOR, 
            input_data.user_id
        ):
            logger.info("🔄 Feature Flag: Legacy SupervisorAgent 사용")
            return await self.legacy_supervisor.execute(input_data, model, progress_callback)
        
        logger.info(f"🚀 LangGraph Supervisor Agent 실행 시작 (사용자: {input_data.user_id})")
        
        try:
            # 성능 모니터링 시작 (optional)
            try:
                await langgraph_monitor.start_execution("langgraph_supervisor")
            except Exception as monitoring_error:
                logger.warning(f"⚠️ 모니터링 시작 실패 (무시됨): {monitoring_error}")
            
            # 대화 컨텍스트 준비
            conversation_context = {}
            if input_data.conversation_context:
                conversation_context = {
                    "current_focus_topic": input_data.conversation_context.current_focus_topic,
                    "interaction_count": input_data.conversation_context.interaction_count,
                    "user_preferences": input_data.conversation_context.user_preferences or {},
                    "previous_messages": input_data.conversation_context.previous_messages or []
                }
            elif input_data.context:
                conversation_context = input_data.context.get('conversation_context', {})
            
            # 초기 상태 설정
            initial_state = SupervisorState(
                original_query=input_data.query,
                user_id=input_data.user_id,
                session_id=input_data.session_id,
                conversation_context=conversation_context,
                model=model,
                intent_analysis=None,
                context_evaluation=None,
                complexity_assessment=None,
                routing_strategy=None,
                selected_agents=None,
                execution_plan=None,
                agent_results=[],
                parallel_results=None,
                integrated_response=None,
                final_output=None,
                execution_metadata={"start_time": start_time},
                quality_metrics={},
                routing_confidence=0.0,
                errors=[],
                fallback_attempts=[],
                should_fallback=False
            )
            
            # LangGraph 워크플로우 실행 (에러 안전 처리)
            try:
                if self.checkpointer:
                    app = self.workflow.compile(checkpointer=self.checkpointer)
                    config = {"configurable": {"thread_id": f"supervisor_{input_data.user_id}_{input_data.session_id}"}}
                    final_state = await app.ainvoke(initial_state, config=config)
                else:
                    app = self.workflow.compile()
                    final_state = await app.ainvoke(initial_state)
            except Exception as workflow_error:
                logger.error(f"❌ LangGraph Supervisor 워크플로우 실행 실패: {workflow_error}")
                raise workflow_error  # 상위로 전파하여 fallback 처리
            
            # 결과 처리
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # 에러가 있거나 fallback이 필요한 경우
            if final_state.get("should_fallback", False) or len(final_state.get("errors", [])) > 0:
                logger.warning("🔄 LangGraph Supervisor 실행 실패 - Legacy 모드로 fallback")
                langgraph_monitor.record_fallback("langgraph_supervisor", f"Errors: {final_state.get('errors', [])}")
                return await self.legacy_supervisor.execute(input_data, model, progress_callback)
            
            # 성공적인 LangGraph 결과 반환
            final_output = final_state.get("final_output", "처리가 완료되었습니다.")
            quality_metrics = final_state.get("quality_metrics", {})
            routing_confidence = final_state.get("routing_confidence", 0.7)
            
            try:
                await langgraph_monitor.track_execution(
                    agent_name="langgraph_supervisor",
                    execution_time=execution_time_ms / 1000,
                    status="success",
                    query=input_data.query,
                    response_length=len(final_output) if final_output else 0,
                    user_id=input_data.user_id
                )
            except Exception as monitoring_error:
                logger.warning(f"⚠️ 모니터링 기록 실패 (무시됨): {monitoring_error}")
            
            result = AgentOutput(
                result=final_output,
                metadata={
                    "agent_version": "langgraph_supervisor_v2",
                    "routing_system": "advanced_langgraph",
                    "routing_confidence": routing_confidence,
                    "supervisor_decision": final_state.get("routing_strategy", {}).get("execution_mode", "single_agent"),
                    "quality_metrics": quality_metrics,
                    "langgraph_execution": True,
                    "performance_optimized": True,
                    **final_state.get("execution_metadata", {})
                },
                execution_time_ms=execution_time_ms,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.utcnow().isoformat()
            )
            
            logger.info(f"✅ LangGraph Supervisor Agent 완료 ({execution_time_ms}ms, 신뢰도: {routing_confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"❌ LangGraph Supervisor Agent 실행 실패: {e}")
            
            # 에러 시 자동 fallback
            try:
                await langgraph_monitor.track_execution(
                    agent_name="langgraph_supervisor",
                    execution_time=(time.time() - start_time),
                    status="error",
                    query=input_data.query,
                    response_length=0,
                    user_id=input_data.user_id,
                    error_message=str(e)
                )
            except Exception as monitoring_error:
                logger.warning(f"⚠️ 모니터링 기록 실패 (무시됨): {monitoring_error}")
            
            langgraph_monitor.record_fallback("langgraph_supervisor", f"Exception: {str(e)}")
            
            logger.info("🔄 예외 발생 - Legacy SupervisorAgent로 fallback")
            return await self.legacy_supervisor.execute(input_data, model, progress_callback)

    def get_capabilities(self) -> List[str]:
        """에이전트 기능 목록"""
        return [
            "고급 의도 분석 및 분류",
            "다층적 컨텍스트 평가",
            "작업 복잡도 및 리소스 분석",
            "지능형 라우팅 전략 수립",
            "동적 에이전트 선택 및 관리",
            "다중 실행 모드 지원",
            "실시간 결과 통합 및 최적화",
            "자동 품질 관리 및 fallback"
        ]

    def get_supported_models(self) -> List[str]:
        """지원 모델 목록"""
        return [
            "claude-sonnet",
            "claude-haiku", 
            "claude-opus",
            "gemini-pro",
            "gemini-flash"
        ]


# 전역 인스턴스 생성
langgraph_supervisor_agent = LangGraphSupervisorAgent()