"""
LangGraph 기반 Information Gap Analyzer - 지능형 정보 분석 시스템

Context7 최신 문서를 참조한 고급 LangGraph StateGraph 구현으로,
정보 부족 상황을 지능적으로 분석하고 최적의 해결책을 제안하는 시스템입니다.
"""

import time
import asyncio
import json
from typing import Dict, Any, List, Optional, TypedDict, Union
from datetime import datetime
import logging

# LangGraph 핵심 imports (최신 버전)
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

# 기존 시스템 imports
from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.workers.information_gap_analyzer import information_gap_analyzer
from app.core.config import settings
from app.core.feature_flags import is_langgraph_enabled, LangGraphFeatureFlags
from app.services.langgraph_monitor import langgraph_monitor

logger = logging.getLogger(__name__)


class InformationGapState(TypedDict):
    """LangGraph Information Gap 분석 상태 정의"""
    # 입력 데이터
    original_query: str
    user_id: str
    session_id: Optional[str]
    model: str
    conversation_context: Optional[Dict[str, Any]]
    
    # 1단계: 쿼리 이해
    query_understanding: Optional[Dict[str, Any]]
    intent_classification: Optional[Dict[str, Any]]
    complexity_assessment: Optional[Dict[str, Any]]
    
    # 2단계: 도메인 분류
    domain_analysis: Optional[Dict[str, Any]]
    expertise_requirements: Optional[Dict[str, Any]]
    
    # 3단계: 정보 격차 분석
    information_gaps: Optional[List[Dict[str, Any]]]
    missing_context: Optional[List[str]]
    ambiguity_points: Optional[List[Dict[str, Any]]]
    
    # 4단계: 해결 전략 수립
    resolution_strategy: Optional[Dict[str, Any]]
    clarification_questions: Optional[List[str]]
    fallback_approaches: Optional[List[Dict[str, Any]]]
    
    # 5단계: 추가 정보 수집 계획
    information_gathering_plan: Optional[Dict[str, Any]]
    research_directions: Optional[List[str]]
    
    # 6단계: 답변 가능성 평가
    answerability_assessment: Optional[Dict[str, Any]]
    confidence_score: Optional[float]
    
    # 7단계: 사용자 안내 생성
    user_guidance: Optional[Dict[str, Any]]
    recommended_actions: Optional[List[str]]
    
    # 8단계: 최종 응답 구성
    final_response: Optional[str]
    metadata_enrichment: Optional[Dict[str, Any]]
    
    # 메타데이터
    execution_metadata: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    
    # 에러 처리
    errors: List[str]
    error_recovery_attempts: int
    should_fallback: bool


def create_error_safe_node(agent_name: str, node_name: str, node_func):
    """에러 안전 노드 래퍼 - 모든 노드를 에러 안전하게 만듭니다"""
    async def error_safe_wrapper(state):
        try:
            logger.debug(f"🔍 {agent_name}: {node_name} 노드 실행 중...")
            result = await node_func(state)
            logger.debug(f"✅ {agent_name}: {node_name} 노드 완료")
            return result
        except Exception as e:
            logger.error(f"❌ {agent_name}: {node_name} 노드 에러: {e}")
            
            # 에러 컨텍스트 생성
            error_context = {
                "node_name": node_name,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat(),
                "state_snapshot": {
                    "errors_count": len(state.get("errors", [])),
                    "recovery_attempts": state.get("error_recovery_attempts", 0)
                }
            }
            
            # 에러 누적 및 복구 시도 증가
            current_errors = state.get("errors", [])
            current_errors.append(f"{node_name}: {str(e)}")
            
            recovery_attempts = state.get("error_recovery_attempts", 0) + 1
            
            # 복구 가능성 평가
            should_fallback = False
            if recovery_attempts >= 3:  # 3회 이상 실패 시 fallback
                should_fallback = True
                logger.warning(f"🚨 {agent_name}: 복구 시도 한계 도달 - Legacy fallback 준비")
            elif len(current_errors) >= 5:  # 에러 5개 이상 누적 시 fallback
                should_fallback = True
                logger.warning(f"🚨 {agent_name}: 에러 누적 한계 도달 - Legacy fallback 준비")
            
            return {
                "errors": current_errors,
                "error_recovery_attempts": recovery_attempts,
                "should_fallback": should_fallback,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    f"{node_name}_error": error_context
                }
            }
    
    return error_safe_wrapper


class LangGraphInformationGapAnalyzer(BaseAgent):
    """LangGraph 기반 Information Gap 분석 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_id="langgraph_information_gap",
            name="LangGraph Information Gap Analyzer",
            description="지능형 정보 격차 분석 및 해결 전략 수립 시스템"
        )
        
        # Legacy 에이전트 (fallback용)
        self.legacy_agent = information_gap_analyzer
        
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
        """LangGraph Information Gap 분석 워크플로우 구성"""
        
        # StateGraph 생성
        workflow = StateGraph(InformationGapState)
        
        # 노드 정의 - 8단계 고급 분석 파이프라인 (모두 에러 안전)
        workflow.add_node("understand_query", 
                         create_error_safe_node("langgraph_information_gap", "understand_query", self._understand_query_node))
        workflow.add_node("classify_domain", 
                         create_error_safe_node("langgraph_information_gap", "classify_domain", self._classify_domain_node))
        workflow.add_node("analyze_gaps", 
                         create_error_safe_node("langgraph_information_gap", "analyze_gaps", self._analyze_gaps_node))
        workflow.add_node("develop_strategy", 
                         create_error_safe_node("langgraph_information_gap", "develop_strategy", self._develop_strategy_node))
        workflow.add_node("plan_information_gathering", 
                         create_error_safe_node("langgraph_information_gap", "plan_information_gathering", self._plan_information_gathering_node))
        workflow.add_node("assess_answerability", 
                         create_error_safe_node("langgraph_information_gap", "assess_answerability", self._assess_answerability_node))
        workflow.add_node("generate_guidance", 
                         create_error_safe_node("langgraph_information_gap", "generate_guidance", self._generate_guidance_node))
        workflow.add_node("construct_response", 
                         create_error_safe_node("langgraph_information_gap", "construct_response", self._construct_response_node))
        
        # 엣지 정의 - 조건부 라우팅
        workflow.set_entry_point("understand_query")
        
        # 조건부 엣지 - 각 단계에서 에러 체크
        workflow.add_conditional_edges(
            "understand_query",
            self._should_continue_or_abort,
            {
                "continue": "classify_domain",
                "abort": END,
                "fallback": END
            }
        )
        
        workflow.add_conditional_edges(
            "classify_domain",
            self._should_continue_or_abort,
            {
                "continue": "analyze_gaps",
                "abort": END,
                "fallback": END
            }
        )
        
        # 선형 진행 (에러 발생 시 각 노드에서 자체 처리)
        workflow.add_edge("analyze_gaps", "develop_strategy")
        workflow.add_edge("develop_strategy", "plan_information_gathering")
        workflow.add_edge("plan_information_gathering", "assess_answerability")
        workflow.add_edge("assess_answerability", "generate_guidance")
        workflow.add_edge("generate_guidance", "construct_response")
        workflow.add_edge("construct_response", END)
        
        return workflow

    def _should_continue_or_abort(self, state: InformationGapState) -> str:
        """조건부 라우팅 함수 - 에러 상황에 따른 흐름 제어"""
        if state.get("should_fallback", False):
            return "fallback"
        
        errors_count = len(state.get("errors", []))
        recovery_attempts = state.get("error_recovery_attempts", 0)
        
        if errors_count >= 3 or recovery_attempts >= 2:
            logger.warning(f"⚠️ Information Gap: 조건부 중단 (에러: {errors_count}, 복구시도: {recovery_attempts})")
            return "abort"
        
        return "continue"

    async def _understand_query_node(self, state: InformationGapState) -> Dict[str, Any]:
        """1단계: 쿼리 이해 노드"""
        logger.info(f"🔍 Information Gap: 쿼리 이해 분석 중... (query: {state['original_query'][:50]})")
        
        model = self._get_llm_model(state["model"])
        
        understanding_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 전문 언어 분석가입니다. 사용자 질문을 깊이 있게 분석하여 다음을 파악하세요:

1. 핵심 의도 (정보 수집, 문제 해결, 비교 분석, 창작 지원 등)
2. 질문 복잡도 (단순, 보통, 복합, 고도 전문)
3. 명확성 수준 (매우 명확, 명확, 보통, 모호, 매우 모호)
4. 필요 정보 유형 (사실, 분석, 의견, 절차, 창의적 내용)
5. 시급성 및 중요도

JSON 형식으로 상세 분석 결과를 제공하세요."""),
            ("human", """분석할 질문: "{query}"

이 질문에 대한 종합적 이해 분석을 수행해주세요.""")
        ])
        
        response = await model.ainvoke(understanding_prompt.format_messages(query=state["original_query"]))
        
        try:
            understanding_result = json.loads(response.content)
        except json.JSONDecodeError:
            understanding_result = {
                "core_intent": "정보_수집",
                "complexity": "보통",
                "clarity_level": "보통",
                "required_info_type": ["사실", "분석"],
                "urgency": "보통",
                "importance": "보통"
            }
        
        # 의도 분류
        intent_classification = {
            "primary_intent": understanding_result.get("core_intent", "정보_수집"),
            "secondary_intents": understanding_result.get("secondary_intents", []),
            "confidence": understanding_result.get("intent_confidence", 0.8)
        }
        
        # 복잡도 평가
        complexity_assessment = {
            "level": understanding_result.get("complexity", "보통"),
            "factors": understanding_result.get("complexity_factors", []),
            "estimated_effort": understanding_result.get("estimated_effort", "중간")
        }
        
        return {
            "query_understanding": understanding_result,
            "intent_classification": intent_classification,
            "complexity_assessment": complexity_assessment,
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "query_understood_at": time.time()
            }
        }

    async def _classify_domain_node(self, state: InformationGapState) -> Dict[str, Any]:
        """2단계: 도메인 분류 노드"""
        logger.info("🔍 Information Gap: 도메인 분류 중...")
        
        model = self._get_llm_model(state["model"])
        
        domain_prompt = ChatPromptTemplate.from_messages([
            ("system", """전문 도메인 분류 전문가로서 질문이 속한 영역과 필요한 전문성을 분석하세요:

1. 주요 도메인 (기술, 비즈니스, 창작, 학술, 일상, 전문직업 등)
2. 세부 전문 분야
3. 필요한 전문성 수준 (일반인, 초급전문가, 중급전문가, 고급전문가)
4. 관련 지식 영역들
5. 도메인간 융합 필요성

JSON 형식으로 도메인 분석 결과를 제공하세요."""),
            ("human", """질문: "{query}"
질문 이해 결과: {understanding}

도메인 분류 및 전문성 요구사항을 분석해주세요.""")
        ])
        
        response = await model.ainvoke(domain_prompt.format_messages(
            query=state["original_query"],
            understanding=json.dumps(state.get("query_understanding", {}), ensure_ascii=False)
        ))
        
        try:
            domain_analysis = json.loads(response.content)
        except json.JSONDecodeError:
            domain_analysis = {
                "primary_domain": "일반",
                "sub_domains": [],
                "expertise_level": "일반인",
                "knowledge_areas": [],
                "interdisciplinary": False
            }
        
        # 전문성 요구사항
        expertise_requirements = {
            "level": domain_analysis.get("expertise_level", "일반인"),
            "specific_skills": domain_analysis.get("specific_skills", []),
            "knowledge_depth": domain_analysis.get("knowledge_depth", "기본"),
            "tools_needed": domain_analysis.get("tools_needed", [])
        }
        
        return {
            "domain_analysis": domain_analysis,
            "expertise_requirements": expertise_requirements,
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "domain_classified_at": time.time()
            }
        }

    async def _analyze_gaps_node(self, state: InformationGapState) -> Dict[str, Any]:
        """3단계: 정보 격차 분석 노드"""
        logger.info("🔍 Information Gap: 정보 격차 분석 중...")
        
        model = self._get_llm_model(state["model"])
        
        gap_analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """정보 격차 분석 전문가로서 다음을 수행하세요:

1. 누락된 핵심 정보 식별
2. 모호하거나 불분명한 요소들
3. 가정이 필요한 부분들
4. 추가 맥락이 필요한 영역
5. 질문 범위의 명확성 평가

각 정보 격차에 대해 중요도와 해결 가능성을 평가하세요."""),
            ("human", """질문: "{query}"
도메인 분석: {domain}
전문성 요구사항: {expertise}

정보 격차를 체계적으로 분석해주세요.""")
        ])
        
        response = await model.ainvoke(gap_analysis_prompt.format_messages(
            query=state["original_query"],
            domain=json.dumps(state.get("domain_analysis", {}), ensure_ascii=False),
            expertise=json.dumps(state.get("expertise_requirements", {}), ensure_ascii=False)
        ))
        
        try:
            gap_result = json.loads(response.content)
            information_gaps = gap_result.get("information_gaps", [])
            missing_context = gap_result.get("missing_context", [])
            ambiguity_points = gap_result.get("ambiguity_points", [])
        except json.JSONDecodeError:
            information_gaps = [{"type": "일반", "importance": "중간", "description": "추가 맥락 필요"}]
            missing_context = ["구체적 상황 정보"]
            ambiguity_points = [{"point": "질문 범위", "clarification_needed": True}]
        
        return {
            "information_gaps": information_gaps,
            "missing_context": missing_context,
            "ambiguity_points": ambiguity_points,
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "gaps_analyzed_at": time.time()
            }
        }

    async def _develop_strategy_node(self, state: InformationGapState) -> Dict[str, Any]:
        """4단계: 해결 전략 수립 노드"""
        logger.info("🔍 Information Gap: 해결 전략 수립 중...")
        
        model = self._get_llm_model(state["model"])
        
        strategy_prompt = ChatPromptTemplate.from_messages([
            ("system", """해결 전략 수립 전문가로서 정보 격차 해결 방안을 제시하세요:

1. 우선순위별 해결 전략
2. 사용자 확인이 필요한 명료화 질문들
3. 추정/가정 기반 접근법
4. 대안적 답변 방향
5. 부분적 답변 가능성

각 전략의 효과성과 실현 가능성을 평가하세요."""),
            ("human", """질문: "{query}"
정보 격차: {gaps}
모호한 점들: {ambiguities}

최적의 해결 전략을 수립해주세요.""")
        ])
        
        response = await model.ainvoke(strategy_prompt.format_messages(
            query=state["original_query"],
            gaps=json.dumps(state.get("information_gaps", []), ensure_ascii=False),
            ambiguities=json.dumps(state.get("ambiguity_points", []), ensure_ascii=False)
        ))
        
        try:
            strategy_result = json.loads(response.content)
        except json.JSONDecodeError:
            strategy_result = {
                "primary_strategy": "부분_답변_및_명료화",
                "clarification_questions": ["더 구체적인 정보를 제공해 주실 수 있나요?"],
                "fallback_approaches": [{"type": "일반적_답변", "feasibility": "높음"}]
            }
        
        return {
            "resolution_strategy": strategy_result,
            "clarification_questions": strategy_result.get("clarification_questions", []),
            "fallback_approaches": strategy_result.get("fallback_approaches", []),
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "strategy_developed_at": time.time()
            }
        }

    async def _plan_information_gathering_node(self, state: InformationGapState) -> Dict[str, Any]:
        """5단계: 추가 정보 수집 계획 노드"""
        logger.info("🔍 Information Gap: 정보 수집 계획 중...")
        
        # 정보 수집 계획 생성
        gathering_plan = {
            "immediate_actions": [
                "사용자 명료화 요청",
                "기존 지식 기반 답변 준비"
            ],
            "research_directions": [
                "관련 주제 탐색",
                "유사 사례 분석"
            ],
            "information_sources": [
                "웹 검색",
                "전문 지식 베이스"
            ],
            "priority": "높음"
        }
        
        # 연구 방향
        research_directions = [
            f"'{state['original_query'][:30]}...' 관련 세부 정보",
            "유사한 상황의 모범 사례",
            "전문가 권장 사항"
        ]
        
        return {
            "information_gathering_plan": gathering_plan,
            "research_directions": research_directions,
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "gathering_planned_at": time.time()
            }
        }

    async def _assess_answerability_node(self, state: InformationGapState) -> Dict[str, Any]:
        """6단계: 답변 가능성 평가 노드"""
        logger.info("🔍 Information Gap: 답변 가능성 평가 중...")
        
        # 답변 가능성 점수 계산
        gaps_count = len(state.get("information_gaps", []))
        ambiguity_count = len(state.get("ambiguity_points", []))
        
        # 기본 점수에서 격차와 모호함에 따라 차감
        base_score = 0.8
        gap_penalty = min(gaps_count * 0.1, 0.3)
        ambiguity_penalty = min(ambiguity_count * 0.05, 0.2)
        
        confidence_score = max(0.1, base_score - gap_penalty - ambiguity_penalty)
        
        # 답변 가능성 평가
        answerability_assessment = {
            "confidence_score": confidence_score,
            "answerability_level": "높음" if confidence_score > 0.7 else "보통" if confidence_score > 0.4 else "낮음",
            "limitations": [
                f"정보 격차 {gaps_count}개",
                f"모호한 점 {ambiguity_count}개"
            ],
            "recommendation": "부분_답변_및_명료화" if confidence_score < 0.6 else "직접_답변"
        }
        
        return {
            "answerability_assessment": answerability_assessment,
            "confidence_score": confidence_score,
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "answerability_assessed_at": time.time()
            }
        }

    async def _generate_guidance_node(self, state: InformationGapState) -> Dict[str, Any]:
        """7단계: 사용자 안내 생성 노드"""
        logger.info("🔍 Information Gap: 사용자 안내 생성 중...")
        
        model = self._get_llm_model(state["model"])
        
        confidence_score = state.get("confidence_score", 0.5)
        clarification_questions = state.get("clarification_questions", [])
        
        guidance_prompt = ChatPromptTemplate.from_messages([
            ("system", """사용자 안내 전문가로서 친근하고 도움이 되는 안내를 작성하세요:

1. 현재 상황 설명 (정보 부족 등)
2. 가능한 도움 범위 안내
3. 더 나은 답변을 위한 구체적 요청
4. 대안적 접근 방법 제시
5. 격려와 지지 메시지

사용자가 실망하지 않고 적극적으로 협력할 수 있도록 긍정적 톤으로 작성하세요."""),
            ("human", """원래 질문: "{query}"
신뢰도 점수: {confidence}
명료화 질문들: {questions}

효과적인 사용자 안내를 생성해주세요.""")
        ])
        
        response = await model.ainvoke(guidance_prompt.format_messages(
            query=state["original_query"],
            confidence=confidence_score,
            questions=json.dumps(clarification_questions, ensure_ascii=False)
        ))
        
        # 권장 행동
        recommended_actions = [
            "더 구체적인 정보 제공",
            "명료화 질문에 응답",
            "관련 맥락 정보 추가"
        ]
        
        user_guidance = {
            "guidance_text": response.content,
            "tone": "친근하고_도움이_되는",
            "approach": "협력적_문제해결"
        }
        
        return {
            "user_guidance": user_guidance,
            "recommended_actions": recommended_actions,
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "guidance_generated_at": time.time()
            }
        }

    async def _construct_response_node(self, state: InformationGapState) -> Dict[str, Any]:
        """8단계: 최종 응답 구성 노드"""
        logger.info("🔍 Information Gap: 최종 응답 구성 중...")
        
        confidence_score = state.get("confidence_score", 0.5)
        user_guidance = state.get("user_guidance", {})
        clarification_questions = state.get("clarification_questions", [])
        
        # 응답 구성
        response_parts = []
        
        # 상황 설명
        if confidence_score < 0.6:
            response_parts.append("**🔍 추가 정보가 필요합니다**\n")
            response_parts.append("더 정확한 답변을 드리기 위해 몇 가지 확인이 필요합니다.\n")
        else:
            response_parts.append("**✅ 답변 준비 완료**\n")
            response_parts.append("제공해주신 정보를 바탕으로 도움을 드릴 수 있습니다.\n")
        
        # 사용자 안내 추가
        guidance_text = user_guidance.get("guidance_text", "")
        if guidance_text:
            response_parts.append(f"\n{guidance_text}\n")
        
        # 명료화 질문 추가
        if clarification_questions:
            response_parts.append("\n**구체적으로 다음 사항들을 알려주시면 더 도움이 됩니다:**\n")
            for i, question in enumerate(clarification_questions[:3], 1):
                response_parts.append(f"{i}. {question}\n")
        
        final_response = "".join(response_parts)
        
        # 메타데이터 강화
        metadata_enrichment = {
            "analysis_depth": "상세",
            "confidence_level": confidence_score,
            "response_type": "정보_격차_분석",
            "user_interaction_needed": len(clarification_questions) > 0,
            "processing_quality": "높음"
        }
        
        return {
            "final_response": final_response,
            "metadata_enrichment": metadata_enrichment,
            "execution_metadata": {
                **state.get("execution_metadata", {}),
                "response_constructed_at": time.time()
            }
        }

    def _get_llm_model(self, model_name: str):
        """LLM 모델 인스턴스 반환"""
        if "claude" in model_name.lower():
            return ChatAnthropic(
                model_name=model_name,
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.3
            )
        elif "gemini" in model_name.lower():
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=0.3
            )
        else:
            return ChatAnthropic(
                model_name="claude-3-sonnet-20240229",
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.3
            )

    async def execute(self, input_data: AgentInput, model: str = "claude-sonnet", progress_callback=None) -> AgentOutput:
        """
        LangGraph Information Gap Analyzer 실행
        100% LangGraph 버전 (에러 안전 보장)
        """
        start_time = time.time()
        
        logger.info(f"🚀 LangGraph Information Gap Analyzer 실행 시작 (사용자: {input_data.user_id})")
        
        try:
            # 성능 모니터링 시작 (optional)
            try:
                await langgraph_monitor.start_execution("langgraph_information_gap")
            except Exception as monitoring_error:
                logger.warning(f"⚠️ 모니터링 시작 실패 (무시됨): {monitoring_error}")
            
            # 초기 상태 설정
            initial_state = InformationGapState(
                original_query=input_data.query,
                user_id=input_data.user_id,
                session_id=input_data.session_id,
                model=model,
                conversation_context=getattr(input_data, 'conversation_context', None),
                query_understanding=None,
                intent_classification=None,
                complexity_assessment=None,
                domain_analysis=None,
                expertise_requirements=None,
                information_gaps=None,
                missing_context=None,
                ambiguity_points=None,
                resolution_strategy=None,
                clarification_questions=None,
                fallback_approaches=None,
                information_gathering_plan=None,
                research_directions=None,
                answerability_assessment=None,
                confidence_score=None,
                user_guidance=None,
                recommended_actions=None,
                final_response=None,
                metadata_enrichment=None,
                execution_metadata={"start_time": start_time},
                performance_metrics={},
                errors=[],
                error_recovery_attempts=0,
                should_fallback=False
            )
            
            # LangGraph 워크플로우 실행 (에러 안전 처리)
            try:
                if self.checkpointer:
                    app = self.workflow.compile(checkpointer=self.checkpointer)
                    config = {"configurable": {"thread_id": f"info_gap_{input_data.user_id}_{input_data.session_id}"}}
                    final_state = await app.ainvoke(initial_state, config=config)
                else:
                    app = self.workflow.compile()
                    final_state = await app.ainvoke(initial_state)
            except Exception as workflow_error:
                logger.error(f"❌ LangGraph Information Gap 워크플로우 실행 실패: {workflow_error}")
                raise workflow_error  # 상위로 전파하여 fallback 처리
            
            # 결과 처리
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Fallback 필요 시 Legacy 호출
            if final_state.get("should_fallback", False) or len(final_state.get("errors", [])) >= 3:
                logger.warning(f"🔄 Information Gap: 심각한 에러 발생 - Legacy 모드로 fallback")
                langgraph_monitor.record_fallback("langgraph_information_gap", f"Errors: {final_state.get('errors', [])}")
                return await self.legacy_agent.execute(input_data, model, progress_callback)
            
            # 성공적인 LangGraph 결과 반환
            try:
                await langgraph_monitor.track_execution(
                    agent_name="langgraph_information_gap",
                    execution_time=execution_time_ms / 1000,
                    status="success",
                    query=input_data.query,
                    response_length=len(final_response) if final_response else 0,
                    user_id=input_data.user_id
                )
            except Exception as monitoring_error:
                logger.warning(f"⚠️ 모니터링 기록 실패 (무시됨): {monitoring_error}")
            
            confidence_score = final_state.get("confidence_score", 0.5)
            final_response = final_state.get("final_response", "정보 분석을 완료했습니다.")
            
            result = AgentOutput(
                result=final_response,
                metadata={
                    "agent_version": "langgraph_v2",
                    "analysis_type": "information_gap",
                    "confidence_score": confidence_score,
                    "needs_clarification": len(final_state.get("clarification_questions", [])) > 0,
                    "information_gaps_count": len(final_state.get("information_gaps", [])),
                    "langgraph_execution": True,
                    **final_state.get("metadata_enrichment", {}),
                    **final_state.get("execution_metadata", {})
                },
                execution_time_ms=execution_time_ms,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.utcnow().isoformat()
            )
            
            logger.info(f"✅ LangGraph Information Gap Analyzer 완료 ({execution_time_ms}ms, 신뢰도: {confidence_score:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"❌ LangGraph Information Gap Analyzer 실행 실패: {e}")
            
            try:
                await langgraph_monitor.track_execution(
                    agent_name="langgraph_information_gap",
                    execution_time=(time.time() - start_time),
                    status="error",
                    query=input_data.query,
                    response_length=0,
                    user_id=input_data.user_id,
                    error_message=str(e)
                )
            except Exception as monitoring_error:
                logger.warning(f"⚠️ 모니터링 기록 실패 (무시됨): {monitoring_error}")
            
            # 에러 시 Legacy fallback
            langgraph_monitor.record_fallback("langgraph_information_gap", f"Exception: {str(e)}")
            logger.info("🔄 예외 발생 - Legacy Information Gap Analyzer로 fallback")
            return await self.legacy_agent.execute(input_data, model, progress_callback)

    def get_capabilities(self) -> List[str]:
        """에이전트 기능 목록"""
        return [
            "지능형 쿼리 이해 및 분석",
            "도메인 분류 및 전문성 평가",
            "정보 격차 체계적 분석",
            "해결 전략 수립",
            "사용자 맞춤 안내 생성",
            "답변 가능성 정확한 평가",
            "에러 안전 처리 시스템"
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
langgraph_information_gap_analyzer = LangGraphInformationGapAnalyzer()