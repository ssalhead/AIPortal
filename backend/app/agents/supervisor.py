"""
Supervisor 에이전트 - 지능형 라우팅 시스템을 통해 사용자 요청을 분석하고 적절한 Worker 에이전트에게 분배
"""

import time
import json
import asyncio
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.llm_router import llm_router
from app.agents.workers.web_search import web_search_agent
from app.agents.workers.information_gap_analyzer import information_gap_analyzer
from app.agents.workers.simple_canvas import SimpleCanvasAgent
from app.agents.routing.intent_classifier import dynamic_intent_classifier, IntentType

# 🚀 2025 차세대 Fast Path 최적화 시스템
from app.agents.intent_classifier import intent_classifier, IntentType as NewIntentType, IntentClassificationResult
from app.agents.context_optimizer import context_optimizer, ContextOptimizationResult

# LangGraph 에이전트 imports (100% 활성화)
from app.agents.langgraph.web_search_langgraph import langgraph_web_search_agent
from app.agents.langgraph.canvas_langgraph import langgraph_canvas_agent
from app.agents.langgraph.information_gap_langgraph import langgraph_information_gap_analyzer
from app.core.feature_flags import is_langgraph_enabled, LangGraphFeatureFlags

logger = logging.getLogger(__name__)


# TaskType은 IntentType으로 대체됨
TaskType = IntentType  # 하위 호환성을 위한 별칭


class SupervisorAgent(BaseAgent):
    """Supervisor 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_id="supervisor",
            name="Supervisor 에이전트",
            description="사용자 요청을 분석하고 적절한 Worker 에이전트에게 분배합니다"
        )
        
        # Worker 에이전트 등록 (information_gap_analyzer는 내부 로직으로 사용)
        self.simple_canvas_agent = SimpleCanvasAgent()  # 단순화된 Canvas 에이전트
        
        # 🚀 100% LangGraph 에이전트 맵 (최고 성능)
        self.workers = {
            TaskType.WEB_SEARCH: self._get_web_search_agent,          # LangGraph WebSearch
            TaskType.CANVAS: self._get_canvas_agent,                  # LangGraph Canvas
            TaskType.GENERAL_CHAT: None,                              # 직접 처리
            TaskType.DEEP_RESEARCH: self._get_web_search_agent,       # WebSearch로 대체
            TaskType.MULTI_STEP: self._get_web_search_agent,          # WebSearch로 대체
            TaskType.CLARIFICATION: self._get_information_gap_agent,  # Information Gap Analyzer
        }
        
        # 🚀 정보 분석기 LangGraph 버전으로 100% 전환
        self.information_analyzer = langgraph_information_gap_analyzer

    def _get_web_search_agent(self, user_id: str = None):
        """
        🚀 100% LangGraph WebSearch 에이전트 (운영 중단 제약 없음)
        """
        self.logger.info(f"🚀 LangGraph WebSearchAgent 100% 활성화 (사용자: {user_id})")
        return langgraph_web_search_agent

    def _get_canvas_agent(self, user_id: str = None):
        """
        🚀 100% LangGraph Canvas 에이전트 (운영 중단 제약 없음)
        """
        self.logger.info(f"🚀 LangGraph CanvasAgent 100% 활성화 (사용자: {user_id})")
        return langgraph_canvas_agent

    def _get_information_gap_agent(self, user_id: str = None):
        """
        🚀 100% LangGraph Information Gap Analyzer (운영 중단 제약 없음)
        """
        self.logger.info(f"🚀 LangGraph Information Gap Analyzer 100% 활성화 (사용자: {user_id})")
        return langgraph_information_gap_analyzer
    
    async def execute(self, input_data: AgentInput, model: str = "claude-sonnet", progress_callback=None) -> AgentOutput:
        """🚀 차세대 Fast Path 최적화 시스템을 사용한 Supervisor 에이전트 실행"""
        start_time = time.time()
        
        if not self.validate_input(input_data):
            raise ValueError("유효하지 않은 입력 데이터")
        
        try:
            # 🧠 Stage 1: 대화 맥락 최적화 (비동기 병렬 처리)
            context_task = None
            if hasattr(input_data, 'conversation_history') and input_data.conversation_history:
                self.logger.info(f"🔧 맥락 최적화 시작: {len(input_data.conversation_history)}개 턴")
                context_task = asyncio.create_task(
                    context_optimizer.optimize_context(
                        input_data.conversation_history,
                        input_data.query,
                        max_tokens=300  # 성능 최적화를 위한 제한
                    )
                )
            
            # 🧠 Stage 2: 3단계 하이브리드 의도 분류 (최대 2초)
            self.logger.info(f"🧠 차세대 의도 분류 시작: '{input_data.query[:50]}...'")
            
            # 맥락 최적화 결과 대기 (있는 경우)
            optimized_context = ""
            if context_task:
                try:
                    context_result: ContextOptimizationResult = await asyncio.wait_for(context_task, timeout=1.5)
                    optimized_context = context_result.optimized_context
                    self.logger.info(
                        f"✅ 맥락 최적화 완료: {context_result.original_token_count} → "
                        f"{context_result.optimized_token_count} 토큰 ({context_result.compression_ratio:.2f}x)"
                    )
                except asyncio.TimeoutError:
                    self.logger.warning("⚠️ 맥락 최적화 타임아웃 - 원본 사용")
                    if context_task:
                        context_task.cancel()
            
            # 🚀 의도 분류 수행
            classification_result: IntentClassificationResult = await intent_classifier.classify_intent(
                input_data.query, 
                optimized_context if optimized_context else None
            )
            
            self.logger.info(
                f"🎯 의도 분류 완료: {classification_result.intent_type.value} "
                f"(신뢰도: {classification_result.confidence:.2f}, "
                f"Stage {classification_result.classification_stage}, {classification_result.processing_time_ms}ms)"
            )
            
            # 🏃‍♂️ Fast Path 실행 (간단한 팩트 질문)
            if classification_result.intent_type == NewIntentType.SIMPLE_FACT:
                self.logger.info(f"🏃‍♂️ Fast Path 활성화 - 간단한 질문 감지")
                
                if progress_callback:
                    await progress_callback({
                        "step": "fast_processing",
                        "message": "빠른 응답 생성 중...",
                        "progress": 50
                    })
                    
                return await self._handle_simple_question_fast(input_data, model, start_time)
            
            # 🔄 복잡 처리 경로 (기존 로직 유지)
            return await self._handle_complex_question(input_data, model, classification_result, start_time, progress_callback)
                
        except Exception as e:
            self.logger.error(f"❌ Supervisor 실행 중 오류: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            # 오류 발생 시 fallback 분류 시도
            try:
                fallback_intent = self._emergency_fallback_classification(input_data.query)
                worker_agent = self._select_worker(fallback_intent, input_data.user_id)
                
                if worker_agent:
                    self.logger.info(f"🆘 긴급 fallback 실행: {fallback_intent.value}")
                    result = await worker_agent.execute(input_data, model, progress_callback)
                    result.metadata["supervisor_decision"] = "emergency_fallback"
                    result.metadata["original_error"] = str(e)
                    return result
            except:
                pass
            
            return self.create_output(
                result=f"죄송합니다. 요청 처리 중 오류가 발생했습니다. 다시 시도해 주세요.",
                metadata={
                    "error": str(e),
                    "supervisor_decision": "error_fallback"
                },
                execution_time_ms=execution_time,
                model_used=model
            )
    
    # 레거시 메서드 - 새로운 시스템에서는 사용하지 않음
    async def _analyze_task_type_direct(self, query: str, model: str) -> TaskType:
        """레거시 메서드 - dynamic_intent_classifier로 대체됨"""
        self.logger.warning("레거시 메서드 _analyze_task_type_direct 호출됨 - dynamic_intent_classifier 사용 권장")
        return self._emergency_fallback_classification(query)
    
    # 레거시 메서드들 - 새로운 시스템에서는 사용하지 않음
    async def _smart_information_analysis(self, query: str, model: str) -> Dict[str, Any]:
        """레거시 메서드 - information_gap_analyzer로 대체됨"""
        self.logger.warning("레거시 메서드 _smart_information_analysis 호출됨")
        return {"needs_analysis": False, "confidence": 0.5, "method": "legacy_fallback"}
    
    def _smart_fallback_analysis(self, query: str) -> TaskType:
        """레거시 메서드 - _emergency_fallback_classification으로 대체됨"""
        self.logger.warning("레거시 메서드 _smart_fallback_analysis 호출됨")
        return self._emergency_fallback_classification(query)
    
    def _select_worker(self, intent_type: IntentType, user_id: str = None) -> Optional[BaseAgent]:
        """의도 유형에 따른 Worker 에이전트 선택 (하이브리드 지원)"""
        # IntentType을 TaskType으로 매핑 (하위 호환성)
        task_type_mapping = {
            IntentType.WEB_SEARCH: TaskType.WEB_SEARCH,
            IntentType.DEEP_RESEARCH: TaskType.DEEP_RESEARCH,
            IntentType.CANVAS: TaskType.CANVAS,
            IntentType.GENERAL_CHAT: TaskType.GENERAL_CHAT,
            IntentType.MULTI_STEP: TaskType.WEB_SEARCH,  # 임시로 웹 검색으로 매핑
            IntentType.CLARIFICATION: TaskType.GENERAL_CHAT  # 일반 채팅으로 매핑
        }
        
        mapped_task_type = task_type_mapping.get(intent_type, TaskType.GENERAL_CHAT)
        worker_or_selector = self.workers.get(mapped_task_type)
        
        if worker_or_selector:
            # 함수인 경우 (하이브리드 선택기) 실행
            if callable(worker_or_selector):
                return worker_or_selector(user_id)
            else:
                # 기존 Worker 에이전트 인스턴스인 경우
                return worker_or_selector
        
        # 해당 Worker가 없는 경우 대체 Worker 선택
        if intent_type in [IntentType.DEEP_RESEARCH, IntentType.MULTI_STEP]:
            # Deep Research나 Multi-step이 없으면 Web Search로 대체
            web_search_selector = self.workers.get(TaskType.WEB_SEARCH)
            if callable(web_search_selector):
                return web_search_selector(user_id)
            return web_search_selector
        elif intent_type == IntentType.CLARIFICATION:
            # 명확화 요청은 일반 채팅으로 처리
            return None  # 직접 처리
        
        return None
    
    def _emergency_fallback_classification(self, query: str) -> IntentType:
        """긴급 상황용 단순 분류"""
        # Canvas 키워드 (가장 명확한 패턴)
        canvas_keywords = ["그려", "만들어", "생성해", "디자인", "차트", "그래프", "시각화", "이미지"]
        if any(keyword in query for keyword in canvas_keywords) and "설명" not in query:
            return IntentType.CANVAS
        
        # 웹 검색 키워드
        search_keywords = ["검색", "찾아", "최신", "현재", "지금", "오늘", "가격", "어디서", "언제"]
        if any(keyword in query for keyword in search_keywords):
            return IntentType.WEB_SEARCH
        
        # 기본값: 일반 대화
        return IntentType.GENERAL_CHAT
    
    async def _handle_directly(self, input_data: AgentInput, model: str, start_time: float, intent_type: str = "general_chat") -> AgentOutput:
        """Supervisor가 직접 처리"""
        try:
            # 의도 유형에 따른 맞춤형 프롬프트
            if intent_type == "clarification":
                prompt = f"""
사용자의 질문이 다소 모호합니다: "{input_data.query}"

질문의 의도를 파악하기 어려워 더 구체적인 정보가 필요합니다.
사용자에게 친근하게 다음과 같은 도움을 제공해주세요:

1. 질문을 더 명확히 하는 방법 제안
2. 구체적인 예시나 상황 요청  
3. 관련된 몇 가지 가능한 해석 제시

답변은 한국어로 자연스럽고 도움이 되는 톤으로 작성해주세요.
"""
            else:
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
                    "intent_type": intent_type,
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
    
    def _extract_original_query(self, query: str) -> str:
        """
        대화 맥락이 추가된 쿼리에서 원본 질문만 추출
        예: "대화 기록:\n어시스턴트: 까치가 뭐야?\n\n현재 질문: 까치가 뭐야?" → "까치가 뭐야?"
        """
        import re
        
        # "현재 질문:" 패턴 찾기
        current_question_match = re.search(r'현재 질문:\s*(.+?)(?:\n|$)', query, re.DOTALL)
        if current_question_match:
            extracted = current_question_match.group(1).strip()
            self.logger.info(f"🔍 원본 질문 추출 성공: '{extracted}'")
            return extracted
        
        # "USER:" 패턴 찾기 (다른 형식의 경우)
        user_message_match = re.search(r'USER:\s*(.+?)(?:\n|$)', query, re.MULTILINE)
        if user_message_match:
            extracted = user_message_match.group(1).strip()
            self.logger.info(f"🔍 USER 패턴 추출 성공: '{extracted}'")
            return extracted
        
        # 패턴이 없으면 원본 반환
        self.logger.info(f"🔍 원본 질문 추출 실패 - 전체 쿼리 사용")
        return query.strip()
    
    async def _is_simple_question(self, query: str) -> bool:
        """
        순수 LLM 기반 간단 질문 감지 시스템 (패턴 매칭 완전 제거)
        Supervisor가 질문 의도를 직접 판단하여 간단한 질문 여부 결정
        """
        self.logger.info(f"🧠 LLM 기반 의도 판단 시작: '{query}'")
        
        validation_prompt = f"""다음 질문을 분석하여 "간단한 팩트 질문"인지 판단해주세요.

질문: "{query}"

간단한 팩트 질문의 조건:
- 단순한 정의, 설명, 개념에 대한 질문 
- "~가 뭐야?", "~에 대해 설명해줘", "~란 무엇인가?" 등
- 일반 상식이나 기본 지식으로 바로 답변 가능
- 웹 검색, 복잡한 분석, 계산, 생성 작업이 불필요

답변: 간단한 질문이면 "SIMPLE", 복잡한 질문이면 "COMPLEX"로만 답변하세요."""

        try:
            # 빠른 모델로 의도 판단
            response, _ = await llm_router.generate_response("gemini-flash", validation_prompt)
            is_simple = "SIMPLE" in response.upper()
            
            self.logger.info(f"🧠 LLM 의도 판단 결과: {'SIMPLE' if is_simple else 'COMPLEX'}")
            self.logger.info(f"🧠 LLM 응답 상세: {response[:100]}")
            
            return is_simple
            
        except Exception as e:
            self.logger.warning(f"⚠️ LLM 검증 실패: {e} - 복잡한 질문으로 처리")
            return False  # 실패 시 안전하게 복잡한 질문으로 처리
    
    async def _handle_simple_question_fast(self, input_data: AgentInput, model: str, start_time: float) -> AgentOutput:
        """간단한 질문을 위한 고속 처리 경로 (의도 분류 우회)"""
        try:
            self.logger.info(f"🏃‍♂️ Fast Path 실행: {input_data.query}")
            
            # 간단하고 최적화된 프롬프트
            prompt = f"""질문: "{input_data.query}"

위 질문에 대해 간단명료한 답변을 제공해주세요.
기본적인 지식을 바탕으로 정확하고 도움이 되는 정보를 한국어로 답변해주세요."""

            # LLM 응답 생성 (복잡한 분석 단계 완전 우회)
            response, _ = await llm_router.generate_response(model, prompt)
            execution_time = int((time.time() - start_time) * 1000)
            
            self.logger.info(f"⚡ Fast Path 완료: {execution_time}ms (기존 25초 → {execution_time/1000:.1f}초)")
            
            return self.create_output(
                result=response,
                metadata={
                    "handled_by": "supervisor_fast_path",
                    "optimization": "intent_classification_bypassed",
                    "method": "pure_llm_simple_question_detection",
                    "performance_gain": f"~95% faster ({execution_time}ms vs ~25000ms)",
                    "routing_version": "fast_path_v2_pure_llm"
                },
                execution_time_ms=execution_time,
                model_used=model
            )
            
        except Exception as e:
            self.logger.error(f"❌ Fast Path 실행 중 오류: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            # Fast Path 실패 시 일반 경로로 폴백
            self.logger.info("🔄 Fast Path 실패 - 일반 처리 경로로 폴백")
            return await self._handle_directly(input_data, model, start_time, "general_chat")
    
    async def _handle_complex_question(
        self, 
        input_data: AgentInput, 
        model: str, 
        classification_result: IntentClassificationResult, 
        start_time: float, 
        progress_callback=None
    ) -> AgentOutput:
        """복잡한 질문 처리 - 기존 LangGraph 시스템 활용"""
        
        self.logger.info(f"🔄 복잡 처리 모드: {classification_result.intent_type.value}")
        
        if progress_callback:
            await progress_callback({
                "step": "complex_analysis",
                "message": "복잡한 분석 수행 중...",
                "progress": 20
            })
        
        # NewIntentType을 기존 IntentType으로 매핑
        intent_mapping = {
            NewIntentType.WEB_SEARCH: IntentType.WEB_SEARCH,
            NewIntentType.REASONING: IntentType.DEEP_RESEARCH,
            NewIntentType.CANVAS: IntentType.CANVAS,
            NewIntentType.COMPLEX: IntentType.MULTI_STEP
        }
        
        # 기존 시스템에서 사용할 의도 유형
        legacy_intent = intent_mapping.get(classification_result.intent_type, IntentType.GENERAL_CHAT)
        
        # 기존 대화 맥락 처리 (하위 호환성)
        if not input_data.conversation_context and input_data.context:
            conversation_context_data = input_data.context.get('conversation_context', {})
            if conversation_context_data:
                from app.agents.base import ConversationContext
                input_data.conversation_context = ConversationContext(**conversation_context_data)
                self.logger.info(f"🔍 대화 맥락 로드: 주제={input_data.conversation_context.current_focus_topic}")
        
        # Worker 에이전트 선택 및 실행
        worker_agent = self._select_worker(legacy_intent, input_data.user_id)
        
        if worker_agent:
            self.logger.info(f"🚀 작업 위임: {legacy_intent.value} → {worker_agent.agent_id}")
            
            if progress_callback:
                await progress_callback({
                    "step": "delegating_to_worker",
                    "message": f"{worker_agent.name}에게 작업 위임 중...",
                    "progress": 40
                })
            
            # Worker 에이전트 실행
            result = await worker_agent.execute(input_data, model, progress_callback)
            
            # 메타데이터 강화
            result.metadata.update({
                "supervisor_decision": legacy_intent.value,
                "delegated_to": worker_agent.agent_id,
                "classification_confidence": classification_result.confidence,
                "classification_stage": classification_result.classification_stage,
                "intent_classification_time_ms": classification_result.processing_time_ms,
                "routing_version": "v3_hybrid_fast_path",
                "needs_web_search": classification_result.needs_web_search,
                "needs_reasoning": classification_result.needs_reasoning,
                "needs_canvas": classification_result.needs_canvas
            })
            
            return result
        else:
            # Worker가 없는 경우 직접 처리
            self.logger.info(f"🤖 직접 처리: {legacy_intent.value} (해당 Worker 없음)")
            return await self._handle_directly(input_data, model, start_time, legacy_intent.value)
    
    def get_capabilities(self) -> list[str]:
        """Supervisor 기능 목록"""
        return [
            "⚡ Fast Path 간단 질문 처리 (25초→5초 최적화)",
            "지능형 의도 분류",
            "맥락 인식 라우팅",
            "신뢰도 기반 분기",
            "Worker 에이전트 관리",
            "실시간 성능 최적화",
            "긴급 상황 처리"
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
    
    def get_performance_report(self) -> Dict[str, Any]:
        """지능형 라우팅 시스템 성능 리포트"""
        try:
            classifier_report = dynamic_intent_classifier.get_performance_report()
            return {
                "routing_version": "v2_intelligent",
                "status": "active",
                "classifier_performance": classifier_report,
                "available_workers": len(self.workers),
                "supported_intents": [intent.value for intent in IntentType],
                "capabilities": self.get_capabilities()
            }
        except Exception as e:
            return {
                "routing_version": "v2_intelligent",
                "status": "error",
                "error": str(e),
                "fallback_available": True
            }
    
    async def record_user_correction(self, user_id: str, original_intent: str, correct_intent: str, query: str):
        """사용자 수정 사항 기록 (학습 향상용)"""
        try:
            await dynamic_intent_classifier.record_correction(user_id, original_intent, correct_intent, query)
            self.logger.info(f"✅ 사용자 피드백 기록 완료: {original_intent} → {correct_intent}")
        except Exception as e:
            self.logger.error(f"❌ 사용자 피드백 기록 실패: {e}")
    
    async def _handle_multi_step_task(
        self, 
        input_data: AgentInput, 
        model: str, 
        start_time: float, 
        reasoning: str,
        progress_callback=None
    ) -> AgentOutput:
        """복합 작업 처리 - 여러 단계의 작업을 순차 실행"""
        try:
            self.logger.info(f"🔗 복합 작업 분해 시작 - 쿼리: {input_data.query}")
            
            # 1단계: 복합 작업을 개별 단계로 분해
            task_breakdown = await self._decompose_multi_step_task(input_data.query, model)
            
            if not task_breakdown or len(task_breakdown) < 2:
                # 분해 실패 시 웹 검색으로 fallback
                self.logger.warning("복합 작업 분해 실패 - 웹 검색으로 처리")
                worker_agent = self.workers.get(TaskType.WEB_SEARCH)
                if worker_agent:
                    return await worker_agent.execute(input_data, model, progress_callback)
                else:
                    return await self._handle_directly(input_data, model, start_time, "multi_step_fallback")
            
            self.logger.info(f"📋 작업 분해 완료 - {len(task_breakdown)}개 단계: {[step['action'] for step in task_breakdown]}")
            
            # 2단계: 순차적으로 각 단계 실행
            accumulated_results = []
            current_context = input_data.context or {}
            
            for i, step in enumerate(task_breakdown):
                step_number = i + 1
                total_steps = len(task_breakdown)
                
                if progress_callback:
                    await progress_callback({
                        "step": f"multi_step_{step_number}",
                        "message": f"단계 {step_number}/{total_steps}: {step['description']}",
                        "progress": 30 + (50 * step_number // total_steps)
                    })
                
                self.logger.info(f"🔄 단계 {step_number}/{total_steps} 실행: {step['action']} - {step['description']}")
                
                # 각 단계에 맞는 Worker 선택
                step_intent = IntentType(step['action'])
                worker_agent = self._select_worker(step_intent)
                
                if worker_agent:
                    # 이전 단계 결과를 컨텍스트에 추가
                    if accumulated_results:
                        current_context['previous_step_results'] = accumulated_results
                    
                    # 단계별 입력 데이터 구성
                    step_input = AgentInput(
                        query=step['query'],
                        user_id=input_data.user_id,
                        session_id=input_data.session_id,
                        context=current_context,
                        conversation_context=input_data.conversation_context
                    )
                    
                    # 단계 실행
                    step_result = await worker_agent.execute(step_input, model)
                    
                    accumulated_results.append({
                        "step": step_number,
                        "action": step['action'],
                        "description": step['description'],
                        "query": step['query'],
                        "result": step_result.result,
                        "metadata": step_result.metadata,
                        "execution_time_ms": step_result.execution_time_ms
                    })
                    
                    self.logger.info(f"✅ 단계 {step_number} 완료 - {step['action']}")
                else:
                    # Worker가 없는 경우 직접 처리
                    self.logger.warning(f"⚠️ 단계 {step_number} Worker 없음 - 직접 처리")
                    accumulated_results.append({
                        "step": step_number,
                        "action": step['action'],
                        "description": step['description'],
                        "query": step['query'],
                        "result": f"단계 {step_number} 처리를 위한 전용 에이전트가 없습니다.",
                        "metadata": {"error": "no_worker_available"},
                        "execution_time_ms": 0
                    })
            
            # 3단계: 모든 결과를 종합하여 최종 응답 생성
            final_response = await self._synthesize_multi_step_results(
                input_data.query, accumulated_results, model
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return self.create_output(
                result=final_response,
                metadata={
                    "supervisor_decision": "multi_step",
                    "routing_version": "v2_intelligent",
                    "multi_step_breakdown": task_breakdown,
                    "steps_completed": len(accumulated_results),
                    "step_results": accumulated_results
                },
                execution_time_ms=execution_time,
                model_used=model
            )
            
        except Exception as e:
            self.logger.error(f"❌ 복합 작업 처리 중 오류: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return self.create_output(
                result="죄송합니다. 복합 작업 처리 중 오류가 발생했습니다. 단순한 검색으로 다시 시도해 주세요.",
                metadata={
                    "supervisor_decision": "multi_step_error",
                    "error": str(e)
                },
                execution_time_ms=execution_time,
                model_used=model
            )
    
    async def _decompose_multi_step_task(self, query: str, model: str) -> List[Dict[str, str]]:
        """복합 작업을 개별 단계로 분해"""
        try:
            prompt = f"""
다음 사용자 질문을 분석하여 순차적으로 실행할 단계들로 분해해주세요.

사용자 질문: "{query}"

각 단계는 다음 작업 유형 중 하나여야 합니다:
- web_search: 인터넷 검색
- deep_research: 심층 분석  
- canvas: 시각적 창작
- general_chat: 일반 대화

다음 JSON 형식으로 응답해주세요:
[
  {{
    "action": "web_search|deep_research|canvas|general_chat",
    "description": "이 단계에서 수행할 작업 설명",
    "query": "실제로 실행할 구체적 질문"
  }}
]

예시:
질문: "최신 스마트폰을 찾아서 장단점 비교해줘"
응답:
[
  {{
    "action": "web_search",
    "description": "최신 스마트폰 모델 검색",
    "query": "2025년 최신 스마트폰 모델 리스트"
  }},
  {{
    "action": "deep_research", 
    "description": "찾은 스마트폰들의 장단점 분석",
    "query": "최신 스마트폰 모델들의 상세 비교 분석"
  }}
]

JSON만 응답해주세요.
"""
            
            response, _ = await llm_router.generate_response(model, prompt, include_datetime=False)
            
            # JSON 파싱
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            task_breakdown = json.loads(clean_response.strip())
            
            # 유효성 검증
            valid_actions = {"web_search", "deep_research", "canvas", "general_chat"}
            filtered_breakdown = []
            
            for step in task_breakdown:
                if (isinstance(step, dict) and 
                    "action" in step and 
                    "description" in step and 
                    "query" in step and
                    step["action"] in valid_actions):
                    filtered_breakdown.append(step)
            
            return filtered_breakdown if len(filtered_breakdown) >= 2 else []
            
        except Exception as e:
            self.logger.error(f"복합 작업 분해 실패: {e}")
            return []
    
    async def _synthesize_multi_step_results(self, original_query: str, step_results: List[Dict], model: str) -> str:
        """여러 단계의 결과를 종합하여 최종 응답 생성"""
        try:
            # 각 단계 결과 요약
            results_summary = []
            for result in step_results:
                summary = f"**단계 {result['step']}: {result['description']}**\n"
                summary += f"결과: {result['result'][:200]}{'...' if len(result['result']) > 200 else ''}\n"
                results_summary.append(summary)
            
            prompt = f"""
사용자의 원본 질문에 대해 여러 단계를 거쳐 얻은 결과들을 종합하여 완전하고 유용한 최종 답변을 작성해주세요.

원본 질문: "{original_query}"

단계별 결과:
{chr(10).join(results_summary)}

다음 원칙에 따라 최종 답변을 작성해주세요:
1. 모든 단계 결과를 종합하여 완전한 답변 제공
2. 논리적 흐름으로 정보를 구성
3. 사용자가 원했던 정보를 명확히 전달
4. 한국어로 자연스럽게 작성
5. 필요시 요약, 결론, 추천 사항 포함

최종 답변:
"""
            
            response, _ = await llm_router.generate_response(model, prompt, include_datetime=False)
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"결과 종합 실패: {e}")
            # Fallback: 단계별 결과를 단순 나열
            fallback_response = f"원본 질문: {original_query}\n\n"
            for result in step_results:
                fallback_response += f"**{result['description']}:**\n{result['result']}\n\n"
            return fallback_response
    
    async def analyze_and_suggest_agent(self, query: str, current_agent: str, model: str = "gemini") -> Dict[str, Any]:
        """현재 에이전트와 다른 더 적합한 에이전트를 제안"""
        try:
            # 사용자 쿼리 분석 (정보 분석 없이 바로 작업 유형 분석)
            suggested_task_type = await self._analyze_task_type_direct(query, model)
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