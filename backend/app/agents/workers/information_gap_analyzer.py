"""
정보 부족 분석 에이전트 - 사용자 질문에서 부족한 정보를 식별하고 추가 정보를 요구
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.llm_router import llm_router
from app.utils.timezone import now_kst

logger = logging.getLogger(__name__)


class InformationType(Enum):
    """정보 타입 분류"""
    TEMPORAL = "temporal"      # 시간/날짜 정보
    SPATIAL = "spatial"        # 위치/지역 정보  
    CONDITIONAL = "conditional" # 조건/기준 정보
    PREFERENTIAL = "preferential" # 선호도/취향 정보
    QUANTITATIVE = "quantitative" # 수량/범위 정보
    CATEGORICAL = "categorical"   # 카테고리/종류 정보


class UrgencyLevel(Enum):
    """정보 필요성 긴급도"""
    CRITICAL = "critical"    # 필수 - 답변 불가능
    HIGH = "high"           # 중요 - 품질 저하
    MEDIUM = "medium"       # 보통 - 개선 가능
    LOW = "low"            # 선택 - 부가 정보


@dataclass
class InformationGap:
    """부족한 정보 항목"""
    gap_type: InformationType
    field_name: str
    description: str
    urgency: UrgencyLevel
    suggestions: List[str]
    question: str
    context_hint: str = ""


@dataclass
class GapAnalysisResult:
    """정보 부족 분석 결과"""
    has_gaps: bool
    critical_gaps: List[InformationGap]
    optional_gaps: List[InformationGap]
    confidence_score: float
    analysis_reason: str
    suggested_questions: List[str]
    can_proceed_anyway: bool


class InformationGapAnalyzer(BaseAgent):
    """정보 부족 분석 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_id="information_gap_analyzer",
            name="정보 부족 분석 에이전트",
            description="사용자 질문에서 부족한 정보를 식별하고 추가 정보를 요구합니다"
        )
        
        # 도메인별 필수 정보 패턴
        self.domain_requirements = {
            "weather": {
                "required": ["location"],
                "optional": ["time_period", "specific_conditions"]
            },
            "restaurant": {
                "required": ["location"],
                "optional": ["cuisine_type", "price_range", "group_size", "occasion"]
            },
            "shopping": {
                "required": ["product_category"],
                "optional": ["budget", "brand_preference", "specific_features"]
            },
            "travel": {
                "required": ["destination", "travel_dates"],
                "optional": ["budget", "travel_style", "group_size", "interests"]
            },
            "entertainment": {
                "required": ["content_type"],
                "optional": ["genre", "age_rating", "platform", "mood"]
            }
        }
        
    async def execute(self, input_data: AgentInput, model: str = "gemini", progress_callback=None) -> AgentOutput:
        """정보 부족 분석 실행"""
        start_time = time.time()
        
        if not self.validate_input(input_data):
            raise ValueError("유효하지 않은 입력 데이터")
            
        try:
            # 진행 상태 알림
            if progress_callback:
                progress_callback("사용자 질문 분석 중...", 20, {
                    "step_id": "question_analysis",
                    "step_name": "질문 분석",
                    "description": "질문의 의도와 필요 정보를 분석합니다"
                })
            
            # 질문 분석 및 정보 부족 식별
            gap_analysis = await self._analyze_information_gaps(
                input_data.query, 
                input_data.context or {},
                model
            )
            
            if progress_callback:
                progress_callback("정보 부족 분석 완료", 80, {
                    "step_id": "gap_analysis_complete", 
                    "step_name": "분석 완료",
                    "description": f"{'추가 정보 필요' if gap_analysis.has_gaps else '정보 충족'}"
                })
            
            # 결과 생성
            execution_time = int((time.time() - start_time) * 1000)
            
            if gap_analysis.has_gaps:
                # 추가 정보 요구 응답
                response = await self._generate_information_request(gap_analysis, model)
                
                return AgentOutput(
                    result=response,
                    metadata={
                        "needs_more_info": True,
                        "gap_analysis": {
                            "critical_gaps": len(gap_analysis.critical_gaps),
                            "optional_gaps": len(gap_analysis.optional_gaps),
                            "confidence_score": gap_analysis.confidence_score,
                            "can_proceed_anyway": gap_analysis.can_proceed_anyway
                        },
                        "information_gaps": [
                            {
                                "type": gap.gap_type.value,
                                "field": gap.field_name,
                                "description": gap.description,
                                "urgency": gap.urgency.value,
                                "question": gap.question,
                                "suggestions": gap.suggestions
                            }
                            for gap in gap_analysis.critical_gaps + gap_analysis.optional_gaps
                        ],
                        "suggested_questions": gap_analysis.suggested_questions
                    },
                    execution_time_ms=execution_time,
                    agent_id=self.agent_id,
                    model_used=model,
                    timestamp=now_kst().isoformat()
                )
            else:
                # 정보가 충분한 경우
                return AgentOutput(
                    result="질문에 필요한 정보가 충분합니다. 검색을 진행하겠습니다.",
                    metadata={
                        "needs_more_info": False,
                        "analysis_confidence": gap_analysis.confidence_score,
                        "analysis_reason": gap_analysis.analysis_reason
                    },
                    execution_time_ms=execution_time,
                    agent_id=self.agent_id,
                    model_used=model,
                    timestamp=now_kst().isoformat()
                )
                
        except Exception as e:
            self.logger.error(f"정보 부족 분석 중 오류: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return AgentOutput(
                result="질문 분석 중 오류가 발생했습니다. 일반적인 방법으로 진행하겠습니다.",
                metadata={"error": str(e), "needs_more_info": False},
                execution_time_ms=execution_time,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=now_kst().isoformat(),
                error=str(e)
            )
    
    async def _analyze_information_gaps(
        self, 
        query: str, 
        context: Dict[str, Any],
        model: str
    ) -> GapAnalysisResult:
        """LLM을 사용하여 정보 부족을 분석"""
        
        # 현재 시간 정보
        current_time = now_kst()
        current_date = current_time.strftime("%Y년 %m월 %d일")
        current_day = current_time.strftime("%A")
        
        # 대화 컨텍스트 정보 추출
        conversation_context = context.get('conversation_context', {})
        previous_messages = conversation_context.get('previous_messages', [])
        
        # 대화 히스토리 구성
        conversation_history = ""
        if previous_messages:
            conversation_history = "\n이전 대화 내용:\n"
            for msg in previous_messages[-6:]:  # 최근 6개 메시지만 사용
                role = "사용자" if msg.get('role') == 'user' else "AI"
                content = msg.get('content', '')[:100]  # 내용 길이 제한
                conversation_history += f"- {role}: {content}\n"
        
        prompt = f"""
사용자의 질문을 분석하여 답변을 위해 필요한 추가 정보가 있는지 판단해주세요.

현재 시간 정보:
- 오늘: {current_date} ({current_day})
- 현재 시각: {current_time.strftime("%H시 %M분")}

{conversation_history}

현재 사용자 질문: "{query}"

**중요**: 이전 대화에서 이미 제공된 정보는 충분한 것으로 간주하세요.

다음 기준으로 분석해주세요:

1. **필수 정보 (Critical)**: 이 정보 없이는 정확한 답변이 불가능
   - 위치/지역 (날씨, 맛집, 이벤트 등)
   - 시간/날짜 (특정 시점의 정보가 필요한 경우)
   - 구체적 조건 (예산, 인원수, 선호도 등)

2. **선택적 정보 (Optional)**: 있으면 더 나은 답변 가능
   - 세부 선호사항
   - 부가적 조건
   - 개인화 요소

3. **분석 원칙**:
   - "오늘", "현재", "지금" 등은 시간 정보가 충분함
   - "여기", "근처" 등은 위치 정보 부족
   - 일반적인 정보 요청은 추가 정보 불필요
   - 추천/비교 요청은 조건 정보 검토
   - **이전 대화에서 구체적 정보가 제공되었다면 추가 요청 불필요**
   - **"검색해서", "찾아서" 등 강력한 검색 지시어가 있으면 정보 충족으로 간주**

다음 JSON 형식으로 응답해주세요:

{{
  "has_gaps": true/false,
  "confidence_score": 0.0-1.0,
  "analysis_reason": "분석 결과에 대한 간단한 설명",
  "can_proceed_anyway": true/false,
  "critical_gaps": [
    {{
      "gap_type": "spatial|temporal|conditional|preferential|quantitative|categorical",
      "field_name": "필드명",
      "description": "부족한 정보 설명",
      "urgency": "critical|high|medium|low", 
      "suggestions": ["제안1", "제안2", "제안3"],
      "question": "사용자에게 물어볼 구체적 질문",
      "context_hint": "맥락 설명"
    }}
  ],
  "optional_gaps": [
    {{
      "gap_type": "...",
      "field_name": "...",
      "description": "...",
      "urgency": "...",
      "suggestions": ["..."],
      "question": "...",
      "context_hint": "..."
    }}
  ],
  "suggested_questions": [
    "사용자에게 제안할 구체적 질문들"
  ]
}}

**분석 예시**:
- "오늘 날씨 어때?" → 지역 정보 필수 (critical gap)
- "맛집 추천해줘" → 지역 필수, 음식종류/가격대 선택적
- "파이썬 문법 알려줘" → 추가 정보 불필요
- "최신 스마트폰 추천" → 예산/용도 선택적

JSON만 응답해주세요.
"""
        
        try:
            response, _ = await llm_router.generate_response(model, prompt, include_datetime=False)
            
            # JSON 파싱
            clean_response = self._clean_json_response(response)
            analysis_data = json.loads(clean_response)
            
            # GapAnalysisResult 객체 생성
            critical_gaps = []
            for gap_data in analysis_data.get("critical_gaps", []):
                gap = InformationGap(
                    gap_type=InformationType(gap_data["gap_type"]),
                    field_name=gap_data["field_name"],
                    description=gap_data["description"],
                    urgency=UrgencyLevel(gap_data["urgency"]),
                    suggestions=gap_data.get("suggestions", []),
                    question=gap_data["question"],
                    context_hint=gap_data.get("context_hint", "")
                )
                critical_gaps.append(gap)
            
            optional_gaps = []
            for gap_data in analysis_data.get("optional_gaps", []):
                gap = InformationGap(
                    gap_type=InformationType(gap_data["gap_type"]),
                    field_name=gap_data["field_name"],
                    description=gap_data["description"],
                    urgency=UrgencyLevel(gap_data["urgency"]),
                    suggestions=gap_data.get("suggestions", []),
                    question=gap_data["question"],
                    context_hint=gap_data.get("context_hint", "")
                )
                optional_gaps.append(gap)
            
            return GapAnalysisResult(
                has_gaps=analysis_data.get("has_gaps", False),
                critical_gaps=critical_gaps,
                optional_gaps=optional_gaps,
                confidence_score=analysis_data.get("confidence_score", 0.5),
                analysis_reason=analysis_data.get("analysis_reason", ""),
                suggested_questions=analysis_data.get("suggested_questions", []),
                can_proceed_anyway=analysis_data.get("can_proceed_anyway", True)
            )
            
        except Exception as e:
            self.logger.error(f"정보 부족 분석 실패: {e}")
            # 기본적인 패턴 기반 분석으로 fallback
            return self._basic_gap_analysis(query)
    
    def _clean_json_response(self, response: str) -> str:
        """LLM 응답에서 JSON 부분만 추출"""
        response = response.strip()
        
        if response.startswith('```json'):
            response = response[7:]
        if response.endswith('```'):
            response = response[:-3]
        
        return response.strip()
    
    def _basic_gap_analysis(self, query: str) -> GapAnalysisResult:
        """기본 패턴 기반 정보 부족 분석"""
        critical_gaps = []
        optional_gaps = []
        
        # 위치 관련 키워드
        location_keywords = ["날씨", "맛집", "식당", "카페", "병원", "약국", "마트", "쇼핑", "근처", "주변"]
        needs_location = any(keyword in query for keyword in location_keywords)
        
        if needs_location and not any(loc in query for loc in ["서울", "부산", "대구", "인천", "광주", "대전", "울산"]):
            gap = InformationGap(
                gap_type=InformationType.SPATIAL,
                field_name="location",
                description="지역 정보가 필요합니다",
                urgency=UrgencyLevel.CRITICAL,
                suggestions=["서울", "부산", "대구", "인천", "광주"],
                question="어느 지역을 원하시나요?",
                context_hint="구체적인 지역명을 알려주세요"
            )
            critical_gaps.append(gap)
        
        # 추천 관련 키워드  
        recommendation_keywords = ["추천", "어떤", "뭐가", "좋은"]
        needs_preference = any(keyword in query for keyword in recommendation_keywords)
        
        if needs_preference:
            gap = InformationGap(
                gap_type=InformationType.PREFERENTIAL,
                field_name="preferences",
                description="선호사항 정보가 있으면 더 좋은 추천이 가능합니다",
                urgency=UrgencyLevel.MEDIUM,
                suggestions=["가격대", "스타일", "특징"],
                question="어떤 조건이나 선호사항이 있으신가요?",
                context_hint="예산, 스타일, 특별한 요구사항 등"
            )
            optional_gaps.append(gap)
        
        has_gaps = len(critical_gaps) > 0 or len(optional_gaps) > 0
        
        return GapAnalysisResult(
            has_gaps=has_gaps,
            critical_gaps=critical_gaps,
            optional_gaps=optional_gaps,
            confidence_score=0.7,
            analysis_reason="기본 패턴 분석 결과",
            suggested_questions=[gap.question for gap in critical_gaps + optional_gaps],
            can_proceed_anyway=len(critical_gaps) == 0
        )
    
    async def _generate_information_request(
        self, 
        gap_analysis: GapAnalysisResult, 
        model: str
    ) -> str:
        """사용자 친화적인 정보 요청 메시지 생성"""
        
        # 필수 정보와 선택적 정보 구분
        critical_questions = [gap.question for gap in gap_analysis.critical_gaps]
        optional_questions = [gap.question for gap in gap_analysis.optional_gaps]
        
        suggestions = []
        for gap in gap_analysis.critical_gaps + gap_analysis.optional_gaps:
            if gap.suggestions:
                suggestions.extend(gap.suggestions)
        
        prompt = f"""
사용자에게 추가 정보를 요청하는 친근하고 자연스러운 메시지를 작성해주세요.

필수 질문: {critical_questions}
선택적 질문: {optional_questions}
제안사항: {suggestions[:5]}
진행 가능 여부: {gap_analysis.can_proceed_anyway}

다음 규칙을 따라주세요:
1. 친근하고 도움이 되는 톤 사용
2. 필수 정보는 반드시 포함
3. 선택적 정보는 "더 정확한 답변을 위해" 식으로 부드럽게 요청
4. 구체적인 예시나 선택지 제공
5. 사용자가 답변하기 쉽도록 구조화

한국어로 자연스럽게 작성해주세요.
"""
        
        try:
            response, _ = await llm_router.generate_response(model, prompt, include_datetime=False)
            return response.strip()
        except Exception as e:
            self.logger.error(f"정보 요청 메시지 생성 실패: {e}")
            
            # fallback 메시지
            if critical_questions:
                return f"더 정확한 답변을 위해 다음 정보가 필요합니다:\n\n{chr(10).join([f'• {q}' for q in critical_questions])}"
            else:
                return "추가 정보를 알려주시면 더 정확한 답변을 드릴 수 있습니다."
    
    def get_capabilities(self) -> List[str]:
        """에이전트 기능 목록"""
        return [
            "질문 의도 분석",
            "필수 정보 식별", 
            "선택적 정보 추천",
            "정보 부족 수준 평가",
            "사용자 친화적 질문 생성",
            "도메인별 요구사항 분석"
        ]
    
    def get_supported_models(self) -> List[str]:
        """지원하는 모델 목록"""
        return ["gemini", "claude", "gemini-flash"]


# 에이전트 인스턴스
information_gap_analyzer = InformationGapAnalyzer()