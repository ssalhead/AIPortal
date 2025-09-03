"""
Dynamic Intent Classification Engine
완전 동적 LLM 기반 사용자 의도 분류 시스템
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import hashlib

from app.agents.base import BaseAgent, AgentInput, AgentOutput, ConversationContext
from app.agents.llm_router import llm_router

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """의도 유형 - 동적 확장 가능"""
    WEB_SEARCH = "web_search"
    DEEP_RESEARCH = "deep_research" 
    CANVAS = "canvas"
    GENERAL_CHAT = "general_chat"
    MULTI_STEP = "multi_step"  # 복합 작업
    CLARIFICATION = "clarification"  # 명확화 필요


@dataclass
class ClassificationResult:
    """분류 결과"""
    primary_intent: IntentType
    secondary_intents: List[IntentType]
    confidence_score: float
    reasoning: str
    context_factors: List[str]
    requires_clarification: bool = False
    suggested_follow_ups: List[str] = None
    complexity_score: float = 0.5  # 0.0 (단순) ~ 1.0 (복잡)


@dataclass
class UserBehaviorPattern:
    """사용자 행동 패턴"""
    preferred_agents: Dict[str, int]
    correction_history: List[Dict[str, Any]]
    conversation_style: str  # direct, exploratory, detailed
    domain_expertise: Dict[str, float]  # 도메인별 전문성 수준
    last_updated: datetime


class DynamicIntentClassifier(BaseAgent):
    """완전 동적 사용자 의도 분류 엔진"""
    
    def __init__(self):
        super().__init__(
            agent_id="dynamic_intent_classifier",
            name="지능형 의도 분류기",
            description="사용자 의도를 동적으로 분석하고 최적의 에이전트로 라우팅합니다"
        )
        
        # 성능 추적 및 학습 데이터
        self.classification_history = []
        self.user_patterns = {}  # user_id별 패턴
        self.performance_metrics = {
            "total_classifications": 0,
            "high_confidence_count": 0,
            "correction_count": 0,
            "accuracy_by_intent": {},
            "avg_confidence": 0.0
        }
        
        # 동적 학습 설정
        self.confidence_threshold = 0.75
        self.learning_enabled = True
        self.context_weight = 0.3  # 맥락 가중치
        
        # 실시간 성능 최적화를 위한 프롬프트 템플릿
        self.prompt_templates = {
            "base": self._get_base_classification_prompt,
            "context_aware": self._get_context_aware_prompt,
            "pattern_enhanced": self._get_pattern_enhanced_prompt
        }
        
        # 현재 사용 중인 프롬프트 전략
        self.current_strategy = "context_aware"
    
    async def execute(self, input_data: AgentInput, model: str = "claude-sonnet", progress_callback=None) -> AgentOutput:
        """의도 분류 실행"""
        start_time = time.time()
        
        try:
            if progress_callback:
                await progress_callback({
                    "step": "analyzing_intent",
                    "message": "사용자 의도 분석 중...",
                    "progress": 20
                })
            
            # 1. 사용자 패턴 로드
            user_pattern = self._get_user_pattern(input_data.user_id)
            
            # 2. 동적 의도 분류
            classification = await self._classify_intent(
                input_data.query,
                input_data.conversation_context,
                user_pattern,
                model
            )
            
            if progress_callback:
                await progress_callback({
                    "step": "classification_complete", 
                    "message": f"의도 분류 완료: {classification.primary_intent.value}",
                    "progress": 90
                })
            
            # 3. 성능 추적 및 학습
            await self._track_classification(classification, input_data)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return AgentOutput(
                result=json.dumps({
                    "primary_intent": classification.primary_intent.value,
                    "secondary_intents": [intent.value for intent in classification.secondary_intents],
                    "confidence": classification.confidence_score,
                    "reasoning": classification.reasoning,
                    "requires_clarification": classification.requires_clarification,
                    "suggested_follow_ups": classification.suggested_follow_ups or [],
                    "complexity_score": classification.complexity_score
                }, ensure_ascii=False),
                metadata={
                    "classification_strategy": self.current_strategy,
                    "context_factors": classification.context_factors,
                    "user_pattern_used": user_pattern is not None,
                    "performance_metrics": self.performance_metrics.copy()
                },
                execution_time_ms=execution_time,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"의도 분류 실행 중 오류: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return AgentOutput(
                result=json.dumps({
                    "primary_intent": "general_chat",
                    "confidence": 0.3,
                    "reasoning": f"분류 오류로 인한 기본값: {str(e)}"
                }),
                metadata={"error": str(e)},
                execution_time_ms=execution_time,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.utcnow().isoformat(),
                error=str(e)
            )
    
    async def _classify_intent(
        self,
        query: str,
        conversation_context: Optional[ConversationContext],
        user_pattern: Optional[UserBehaviorPattern],
        model: str
    ) -> ClassificationResult:
        """동적 의도 분류 실행"""
        
        # 프롬프트 전략 선택
        prompt_func = self.prompt_templates.get(self.current_strategy, self.prompt_templates["base"])
        prompt = prompt_func(query, conversation_context, user_pattern)
        
        try:
            response, _ = await llm_router.generate_response(
                model_name=model,
                prompt=prompt,
                temperature=0.1,  # 일관성 있는 분류를 위해 낮은 온도
                include_datetime=False
            )
            
            # JSON 응답 파싱
            clean_response = self._clean_json_response(response)
            classification_data = json.loads(clean_response)
            
            # ClassificationResult 객체 생성
            primary_intent = IntentType(classification_data.get("primary_intent", "general_chat"))
            secondary_intents = [
                IntentType(intent) for intent in classification_data.get("secondary_intents", [])
                if intent in [e.value for e in IntentType]
            ]
            
            return ClassificationResult(
                primary_intent=primary_intent,
                secondary_intents=secondary_intents,
                confidence_score=classification_data.get("confidence", 0.5),
                reasoning=classification_data.get("reasoning", ""),
                context_factors=classification_data.get("context_factors", []),
                requires_clarification=classification_data.get("requires_clarification", False),
                suggested_follow_ups=classification_data.get("suggested_follow_ups", []),
                complexity_score=classification_data.get("complexity_score", 0.5)
            )
            
        except Exception as e:
            logger.error(f"LLM 분류 실패, fallback 사용: {e}")
            return self._fallback_classification(query, conversation_context)
    
    def _get_context_aware_prompt(
        self,
        query: str,
        conversation_context: Optional[ConversationContext],
        user_pattern: Optional[UserBehaviorPattern]
    ) -> str:
        """맥락 인식 프롬프트 생성"""
        
        # 대화 맥락 정보
        context_info = ""
        if conversation_context and conversation_context.recent_messages:
            recent_msgs = conversation_context.recent_messages[-3:]  # 최근 3개
            context_info = f"""
=== 최근 대화 맥락 ===
{chr(10).join([f"- {msg.get('role', 'unknown')}: {msg.get('content', '')[:100]}..." for msg in recent_msgs])}

현재 주제: {conversation_context.current_focus_topic or '없음'}
대화 흐름: {conversation_context.conversation_flow or '초기 단계'}
이전 검색어: {', '.join(conversation_context.previous_search_queries[-2:]) if conversation_context.previous_search_queries else '없음'}
사용자 의도: {conversation_context.user_intent}
맥락 연결성: {conversation_context.context_connection}
검색 초점: {conversation_context.search_focus}
복잡도: {conversation_context.dynamic_categories.get('complexity', 'simple')}
긴급도: {conversation_context.dynamic_categories.get('urgency', 'low')}
"""
        
        # 사용자 패턴 정보
        pattern_info = ""
        if user_pattern:
            preferred = sorted(user_pattern.preferred_agents.items(), key=lambda x: x[1], reverse=True)[:2]
            pattern_info = f"""
=== 사용자 패턴 ===
선호 에이전트: {', '.join([f"{agent}({count}회)" for agent, count in preferred])}
대화 스타일: {user_pattern.conversation_style}
최근 수정 이력: {len(user_pattern.correction_history)}건
"""
        
        return f"""
사용자의 질문을 분석하여 가장 적합한 에이전트 유형을 결정해주세요.

=== 현재 사용자 질문 ===
"{query}"

{context_info}

{pattern_info}

=== 에이전트 유형 및 분류 기준 ===

**web_search** - 실시간/최신 정보가 필요한 경우:
- 현재 정보: 날씨, 뉴스, 주가, 이벤트 현황
- 쇼핑/구매: 가격 비교, 재고 확인, 제품 리뷰
- 지역 정보: 맛집, 병원, 교통, 영업시간
- 팩트 체크: 최신 통계, 현황, 트렌드

**deep_research** - 종합적 분석이 필요한 경우:
- 비교 분석: "A vs B 비교", "장단점 분석"  
- 심층 조사: "시장 분석", "기술 동향 분석"
- 다각도 검토: "종합적으로", "자세히 조사"

**canvas** - 시각적 창작/표현이 필요한 경우:
- 이미지 생성: "그려줘", "만들어줘", "디자인해줘"
- 다이어그램: "차트", "그래프", "마인드맵"
- 시각화: "도식화", "시각적으로 표현"

**general_chat** - 일반 지식/대화:
- 개념 설명: "~란 무엇인가", "원리 설명"
- 창작 요청: 시, 소설, 아이디어
- 일상 상담: 조언, 의견 교환
- 기본 지식: 정의, 방법론

**multi_step** - 복합 작업이 필요한 경우:
- 연속 작업: "검색해서 분석해줘", "찾아서 비교해줘", "조사해서 정리해줘"
- 단계적 처리: "먼저 A하고 그 다음 B해줘"
- 검색+분석: "~에 대해 찾아보고 장단점 분석해줘"
- 비교 분석: "A와 B를 비교 분석해줘" (검색 + 분석 필요한 경우)

=== 지능적 분류 원칙 ===
1. **맥락 우선**: 이전 대화와의 연관성을 최우선 고려
2. **의도 파악**: 표면적 키워드보다 진짜 의도 파악  
3. **복잡도 평가**: 단순/복합 작업 구분
4. **사용자 패턴**: 개인별 선호도 반영

=== 특별 케이스 처리 ===
- "그것", "그거", "관련된" → 이전 대화 주제와 연결
- "최신", "현재", "지금" → web_search 우선
- 전문 용어 + "설명" → 맥락에 따라 general_chat vs deep_research
- "그려줘"가 있어도 "설명"이 주목적이면 general_chat

다음 JSON 형식으로 응답해주세요:
{{
  "primary_intent": "가장 적합한 단일 의도",
  "secondary_intents": ["보조 의도들 (최대 2개)"],
  "confidence": 0.0-1.0,
  "reasoning": "분류 근거를 구체적으로 설명 (맥락/키워드/패턴 포함)",
  "context_factors": ["분류에 영향을 준 맥락 요소들"],
  "requires_clarification": false,
  "suggested_follow_ups": ["사용자가 도움될 수 있는 후속 질문들"],
  "complexity_score": 0.0-1.0
}}

**중요**: 반드시 정확한 JSON 형식으로만 응답하세요.
"""
    
    def _get_base_classification_prompt(self, query: str, context: Optional[ConversationContext], pattern: Optional[UserBehaviorPattern]) -> str:
        """기본 분류 프롬프트"""
        return f"""
사용자 질문: "{query}"

다음 중 가장 적합한 에이전트를 선택하고 JSON으로 응답하세요:
- web_search: 실시간 정보 검색
- deep_research: 심층 분석
- canvas: 시각적 창작
- general_chat: 일반 대화

{{
  "primary_intent": "선택된_에이전트",
  "confidence": 0.0-1.0,
  "reasoning": "선택 이유"
}}
"""
    
    def _get_pattern_enhanced_prompt(self, query: str, context: Optional[ConversationContext], pattern: Optional[UserBehaviorPattern]) -> str:
        """패턴 강화 프롬프트 (추후 구현)"""
        # TODO: 사용자 패턴을 더 활용한 고급 프롬프트
        return self._get_context_aware_prompt(query, context, pattern)
    
    def _clean_json_response(self, response: str) -> str:
        """LLM 응답에서 JSON 부분만 추출"""
        response = response.strip()
        
        if response.startswith('```json'):
            response = response[7:]
        if response.endswith('```'):
            response = response[:-3]
        
        # 첫 번째 {부터 마지막 }까지 추출
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            response = response[start_idx:end_idx + 1]
        
        return response.strip()
    
    def _fallback_classification(self, query: str, context: Optional[ConversationContext]) -> ClassificationResult:
        """LLM 실패 시 규칙 기반 분류"""
        
        # Canvas 키워드 (가장 명확한 패턴)
        canvas_keywords = ["그려", "만들어", "생성해", "디자인", "차트", "그래프", "시각화", "이미지"]
        if any(keyword in query for keyword in canvas_keywords):
            # 단, "설명"이 함께 있으면 일반 대화로 분류
            if "설명" in query and not any(visual in query for visual in ["그림으로", "도식으로", "차트로"]):
                return ClassificationResult(
                    primary_intent=IntentType.GENERAL_CHAT,
                    secondary_intents=[],
                    confidence_score=0.6,
                    reasoning="시각 키워드가 있지만 설명 중심 요청으로 판단",
                    context_factors=["fallback_classification", "explanation_priority"]
                )
            else:
                return ClassificationResult(
                    primary_intent=IntentType.CANVAS,
                    secondary_intents=[],
                    confidence_score=0.7,
                    reasoning="시각적 창작 키워드 감지",
                    context_factors=["fallback_classification", "canvas_keywords"]
                )
        
        # 웹 검색 키워드
        search_keywords = ["검색", "찾아", "최신", "현재", "지금", "오늘", "가격", "어디서"]
        if any(keyword in query for keyword in search_keywords):
            return ClassificationResult(
                primary_intent=IntentType.WEB_SEARCH,
                secondary_intents=[],
                confidence_score=0.6,
                reasoning="검색 관련 키워드 감지",
                context_factors=["fallback_classification", "search_keywords"]
            )
        
        # 기본값: 일반 대화
        return ClassificationResult(
            primary_intent=IntentType.GENERAL_CHAT,
            secondary_intents=[],
            confidence_score=0.4,
            reasoning="명확한 패턴이 없어 일반 대화로 분류",
            context_factors=["fallback_classification", "default"]
        )
    
    def _get_user_pattern(self, user_id: str) -> Optional[UserBehaviorPattern]:
        """사용자 패턴 조회"""
        return self.user_patterns.get(user_id)
    
    async def _track_classification(self, classification: ClassificationResult, input_data: AgentInput):
        """분류 결과 추적 및 학습 데이터 수집"""
        
        classification_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": input_data.user_id,
            "query": input_data.query,
            "primary_intent": classification.primary_intent.value,
            "confidence": classification.confidence_score,
            "reasoning": classification.reasoning,
            "strategy": self.current_strategy
        }
        
        self.classification_history.append(classification_record)
        
        # 성능 메트릭 업데이트
        self.performance_metrics["total_classifications"] += 1
        
        if classification.confidence_score >= self.confidence_threshold:
            self.performance_metrics["high_confidence_count"] += 1
        
        # 최근 100개만 유지
        if len(self.classification_history) > 100:
            self.classification_history = self.classification_history[-50:]
    
    async def record_correction(self, user_id: str, original_intent: str, correct_intent: str, query: str):
        """사용자 수정 사항 기록 (실시간 학습용)"""
        
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = UserBehaviorPattern(
                preferred_agents={},
                correction_history=[],
                conversation_style="unknown",
                domain_expertise={},
                last_updated=datetime.utcnow()
            )
        
        pattern = self.user_patterns[user_id]
        pattern.correction_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "original_intent": original_intent,
            "correct_intent": correct_intent
        })
        
        # 선호도 업데이트
        if correct_intent not in pattern.preferred_agents:
            pattern.preferred_agents[correct_intent] = 0
        pattern.preferred_agents[correct_intent] += 1
        
        pattern.last_updated = datetime.utcnow()
        
        # 성능 메트릭 업데이트
        self.performance_metrics["correction_count"] += 1
        
        logger.info(f"사용자 수정 기록: {user_id} | {original_intent} → {correct_intent}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 생성"""
        total = self.performance_metrics["total_classifications"]
        if total == 0:
            return {"message": "분류 데이터가 없습니다"}
        
        accuracy = (total - self.performance_metrics["correction_count"]) / total if total > 0 else 0
        confidence_rate = self.performance_metrics["high_confidence_count"] / total if total > 0 else 0
        
        return {
            "total_classifications": total,
            "accuracy": accuracy,
            "high_confidence_rate": confidence_rate,
            "correction_count": self.performance_metrics["correction_count"],
            "current_strategy": self.current_strategy,
            "users_tracked": len(self.user_patterns),
            "recent_classifications": self.classification_history[-10:]
        }
    
    def get_capabilities(self) -> List[str]:
        """에이전트 기능 목록"""
        return [
            "동적 의도 분류",
            "맥락 인식 분석",
            "사용자 패턴 학습",
            "실시간 성능 최적화",
            "복합 의도 처리",
            "신뢰도 기반 분류"
        ]
    
    def get_supported_models(self) -> List[str]:
        """지원하는 모델 목록"""
        return ["claude-sonnet", "claude-haiku", "gemini-pro", "gemini-flash"]


# 전역 인스턴스
dynamic_intent_classifier = DynamicIntentClassifier()