"""
Supervisor 에이전트 - 지능형 라우팅 시스템을 통해 사용자 요청을 분석하고 적절한 Worker 에이전트에게 분배
"""

import time
import json
from typing import Dict, Any, Optional, List
from enum import Enum
import logging

from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.llm_router import llm_router
from app.agents.workers.web_search import web_search_agent
from app.agents.workers.information_gap_analyzer import information_gap_analyzer
from app.agents.workers.simple_canvas import SimpleCanvasAgent
from app.agents.routing.intent_classifier import dynamic_intent_classifier, IntentType

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
        self.workers = {
            TaskType.WEB_SEARCH: web_search_agent,
            TaskType.CANVAS: self.simple_canvas_agent,
            # TaskType.DEEP_RESEARCH: deep_search_agent,  # 추후 구현
            # TaskType.MULTIMODAL_RAG: multimodal_rag_agent,  # 추후 구현
        }
        
        # 정보 분석기는 내부적으로 사용
        self.information_analyzer = information_gap_analyzer
    
    async def execute(self, input_data: AgentInput, model: str = "claude-sonnet", progress_callback=None) -> AgentOutput:
        """Supervisor 에이전트 실행 - 지능형 라우팅 시스템 사용"""
        start_time = time.time()
        
        if not self.validate_input(input_data):
            raise ValueError("유효하지 않은 입력 데이터")
        
        try:
            if progress_callback:
                await progress_callback({
                    "step": "intent_analysis",
                    "message": "사용자 의도 분석 중...",
                    "progress": 10
                })
            
            # 1단계: 대화 맥락 준비
            if not input_data.conversation_context and input_data.context:
                # 기존 context에서 conversation_context 추출하여 전달
                conversation_context_data = input_data.context.get('conversation_context', {})
                if conversation_context_data:
                    # ConversationContext 객체 생성
                    from app.agents.base import ConversationContext
                    input_data.conversation_context = ConversationContext(**conversation_context_data)
                    self.logger.info(f"🔍 대화 맥락 로드: 주제={input_data.conversation_context.current_focus_topic}")
            
            # 2단계: 지능형 의도 분류 실행
            self.logger.info(f"🧠 지능형 의도 분류 시작 - 쿼리: {input_data.query[:100]}...")
            
            classification_result = await dynamic_intent_classifier.execute(input_data, model)
            classification_data = json.loads(classification_result.result)
            
            primary_intent = IntentType(classification_data["primary_intent"])
            confidence = classification_data["confidence"]
            reasoning = classification_data["reasoning"]
            
            self.logger.info(f"🎯 분류 결과: {primary_intent.value} (신뢰도: {confidence:.2f})")
            self.logger.info(f"📝 분류 근거: {reasoning}")
            
            # 2단계: 신뢰도 기반 처리 결정
            if confidence < 0.6:
                self.logger.warning(f"⚠️  분류 신뢰도 낮음 ({confidence:.2f}) - 추가 분석 또는 사용자 확인 필요")
                
                if classification_data.get("requires_clarification", False):
                    # 명확화가 필요한 경우
                    return self.create_output(
                        result=f"질문이 다소 애매합니다. 더 구체적으로 말씀해 주시겠어요?\n\n추천 질문:\n" +
                               "\n".join([f"• {q}" for q in classification_data.get("suggested_follow_ups", [])]),
                        metadata={
                            "supervisor_decision": "clarification_needed",
                            "classification_confidence": confidence,
                            "original_intent": primary_intent.value,
                            "reasoning": reasoning
                        },
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        model_used=model
                    )
            
            # 3단계: 정보 부족 분석 (필요한 경우에만)
            if primary_intent in [IntentType.WEB_SEARCH, IntentType.DEEP_RESEARCH] and confidence >= 0.7:
                self.logger.info("🔍 정보 부족 분석 실행")
                
                info_analysis_result = await self.information_analyzer.execute(input_data, model)
                
                if info_analysis_result.metadata.get("needs_more_info", False):
                    self.logger.info("❓ 정보 부족 감지 - 사용자에게 추가 정보 요청")
                    info_analysis_result.metadata["supervisor_decision"] = "information_request"
                    info_analysis_result.metadata["original_intent"] = primary_intent.value
                    info_analysis_result.metadata["classification_confidence"] = confidence
                    return info_analysis_result
            
            # 4단계: 복합 의도 처리 (Multi-step)
            if primary_intent == IntentType.MULTI_STEP:
                self.logger.info("🔗 복합 작업 감지 - 단계별 처리 시작")
                
                if progress_callback:
                    await progress_callback({
                        "step": "multi_step_analysis",
                        "message": "복합 작업 분석 중...",
                        "progress": 25
                    })
                
                # 복합 작업 처리
                return await self._handle_multi_step_task(input_data, model, start_time, reasoning, progress_callback)
            
            # 5단계: 단일 Worker 에이전트 선택 및 실행
            worker_agent = self._select_worker(primary_intent)
            
            if worker_agent:
                self.logger.info(f"🚀 작업 위임: {primary_intent.value} → {worker_agent.agent_id}")
                
                if progress_callback:
                    await progress_callback({
                        "step": "delegating_to_worker",
                        "message": f"{worker_agent.name}에게 작업 위임 중...",
                        "progress": 30
                    })
                
                # Worker 에이전트 실행
                result = await worker_agent.execute(input_data, model, progress_callback)
                
                # 메타데이터 강화
                result.metadata.update({
                    "supervisor_decision": primary_intent.value,
                    "delegated_to": worker_agent.agent_id,
                    "classification_confidence": confidence,
                    "classification_reasoning": reasoning,
                    "routing_version": "v2_intelligent"
                })
                
                return result
            else:
                # Worker가 없는 경우 직접 처리
                self.logger.info(f"🤖 직접 처리: {primary_intent.value} (해당 Worker 없음)")
                return await self._handle_directly(input_data, model, start_time, primary_intent.value)
                
        except Exception as e:
            self.logger.error(f"❌ Supervisor 실행 중 오류: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            # 오류 발생 시 fallback 분류 시도
            try:
                fallback_intent = self._emergency_fallback_classification(input_data.query)
                worker_agent = self._select_worker(fallback_intent)
                
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
    
    def _select_worker(self, intent_type: IntentType) -> Optional[BaseAgent]:
        """의도 유형에 따른 Worker 에이전트 선택"""
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
        worker = self.workers.get(mapped_task_type)
        
        if worker:
            return worker
        
        # 해당 Worker가 없는 경우 대체 Worker 선택
        if intent_type in [IntentType.DEEP_RESEARCH, IntentType.MULTI_STEP]:
            # Deep Research나 Multi-step이 없으면 Web Search로 대체
            return self.workers.get(TaskType.WEB_SEARCH)
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
    
    def get_capabilities(self) -> list[str]:
        """Supervisor 기능 목록"""
        return [
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