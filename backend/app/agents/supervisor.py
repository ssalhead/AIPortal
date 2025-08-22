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
from app.agents.workers.information_gap_analyzer import information_gap_analyzer
from app.agents.workers.canvas import canvas_agent

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
        
        # Worker 에이전트 등록 (information_gap_analyzer는 내부 로직으로 사용)
        self.workers = {
            TaskType.WEB_SEARCH: web_search_agent,
            TaskType.CANVAS: canvas_agent,
            # TaskType.DEEP_RESEARCH: deep_search_agent,  # 추후 구현
            # TaskType.MULTIMODAL_RAG: multimodal_rag_agent,  # 추후 구현
        }
        
        # 정보 분석기는 내부적으로 사용
        self.information_analyzer = information_gap_analyzer
    
    async def execute(self, input_data: AgentInput, model: str = "gemini", progress_callback=None) -> AgentOutput:
        """Supervisor 에이전트 실행"""
        start_time = time.time()
        
        if not self.validate_input(input_data):
            raise ValueError("유효하지 않은 입력 데이터")
        
        try:
            # 1단계: 대화 컨텍스트 기반 우선순위 체크
            conversation_context = input_data.context.get('conversation_context', {}) if input_data.context else {}
            previous_messages = conversation_context.get('previous_messages', [])
            
            # 강력한 검색 지시어 체크 (정보 분석보다 우선)
            strong_search_indicators = ["검색해서", "찾아서", "조회해서", "알아보고", "웹에서"]
            has_strong_search = any(indicator in input_data.query for indicator in strong_search_indicators)
            
            # 이전 대화에서 정보 요청이 있었는지 체크
            recent_info_request = False
            if previous_messages and len(previous_messages) >= 2:
                last_ai_message = previous_messages[-1].get('content', '') if previous_messages[-1].get('role') == 'assistant' else ''
                if any(keyword in last_ai_message for keyword in ["알려주세요", "정보", "지역", "언제"]):
                    recent_info_request = True
            
            if has_strong_search or recent_info_request:
                # 강력한 검색 지시어가 있거나 최근 정보 요청 후라면 바로 작업 분류로
                self.logger.info("강력한 검색 지시어 감지 또는 정보 요청 후속 - 정보 분석 생략")
                task_type = await self._analyze_task_type_direct(input_data.query, model)
            else:
                # 2단계: 일반적인 경우 정보 분석 실행
                self.logger.info("자동 정보 분석 시작")
                
                # 정보 부족 분석 실행
                info_analysis_result = await self.information_analyzer.execute(input_data, model)
                
                # 정보가 부족한 경우 정보 요청 응답 반환
                if info_analysis_result.metadata.get("needs_more_info", False):
                    self.logger.info("정보 부족 감지 - 사용자에게 추가 정보 요청")
                    # Supervisor 메타데이터 추가
                    info_analysis_result.metadata["supervisor_decision"] = "information_request"
                    info_analysis_result.metadata["auto_analysis"] = True
                    return info_analysis_result
                
                # 3단계: 정보가 충분한 경우 작업 유형 분석
                self.logger.info("정보 충족 - 작업 유형 분석 진행")
                task_type = await self._analyze_task_type_direct(input_data.query, model)
            
            # 4단계: 적절한 Worker 에이전트 선택
            worker_agent = self._select_worker(task_type)
            
            if worker_agent:
                # Worker 에이전트 실행 (progress_callback 전달)
                self.logger.info(f"🎯 작업을 {task_type.value} 에이전트에게 위임 - 에이전트 ID: {worker_agent.agent_id}")
                if task_type == TaskType.CANVAS:
                    self.logger.info(f"🎨 Canvas 에이전트 실행 시작 - 쿼리: {input_data.query[:100]}...")
                result = await worker_agent.execute(input_data, model, progress_callback)
                
                # Supervisor 메타데이터 추가
                result.metadata["supervisor_decision"] = task_type.value
                result.metadata["delegated_to"] = worker_agent.agent_id
                result.metadata["auto_analysis_passed"] = True
                
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
    
    async def _analyze_task_type_direct(self, query: str, model: str) -> TaskType:
        """사용자 쿼리를 분석하여 작업 유형 결정 (LLM 기반 지능형 분류)"""
        try:
            prompt = f"""
사용자의 질문을 분석하여 가장 적합한 작업 유형을 결정해주세요.

사용자 질문: "{query}"

**작업 유형 분류 기준**:

1. **web_search** - 인터넷 검색이 필요한 경우:
   - 실시간/최신 정보 (날씨, 뉴스, 주가, 현재 상황)
   - 쇼핑/구매 정보 (제품 가격, 재고, 서점 도서, 온라인몰)
   - 지역 정보 (맛집, 병원, 교통, 근처 상점)
   - 비교/추천 (제품 비교, 서비스 추천, 베스트셀러)
   - 사실 확인 (최신 정보, 통계, 현황)

2. **deep_research** - 심층 분석이 필요한 경우:
   - 복합적 분석 ("비교 분석", "심층 연구", "종합적 검토")
   - 학술적 조사 (논문, 보고서, 전문 자료)
   - 다각도 검토 (장단점 분석, 트렌드 분석)

3. **canvas** - 시각적 창작:
   - 이미지 생성 ("그려줘", "만들어줘", "디자인", "이미지 생성", "사진", "그림", "일러스트", "AI 이미지")
   - 다이어그램 ("마인드맵", "차트", "그래프", "시각화", "도표")
   - 시각적 콘텐츠 ("포스터", "로고", "배경", "캐릭터", "풍경")

4. **general_chat** - 일반 대화:
   - 기본 지식 질문 (개념 설명, 정의, 방법)
   - 창작 요청 (시, 소설, 아이디어)
   - 일상 대화 (상담, 의견)

**분류 예시**:
- "서점에서 판매중인 책 추천해줘" → web_search (쇼핑/추천 정보)
- "오늘 날씨 어때?" → web_search (실시간 정보)
- "파이썬 문법 설명해줘" → general_chat (기본 지식)
- "마케팅 전략 분석해줘" → deep_research (복합 분석)
- "로고 그려줘" → canvas (시각적 창작)

다음 중 하나만 정확히 반환해주세요: web_search, deep_research, canvas, general_chat
"""
            
            response, _ = await llm_router.generate_response(model, prompt, include_datetime=False)
            task_type_str = response.strip().lower()
            
            # TaskType으로 변환
            if task_type_str == "web_search":
                return TaskType.WEB_SEARCH
            elif task_type_str == "deep_research":
                return TaskType.DEEP_RESEARCH
            elif task_type_str == "canvas":
                return TaskType.CANVAS
            else:
                return TaskType.GENERAL_CHAT
                
        except Exception as e:
            self.logger.warning(f"작업 유형 분석 실패, 스마트 fallback 사용: {e}")
            return self._smart_fallback_analysis(query)
    
    async def _smart_information_analysis(self, query: str, model: str) -> Dict[str, Any]:
        """LLM 기반 정보 부족 분석 - 맥락적 이해로 정보 요청 필요성 판단"""
        try:
            prompt = f"""
사용자의 질문을 분석하여 추가 정보가 필요한지 판단해주세요.

사용자 질문: "{query}"

**분석 기준**:
- 질문이 구체적이고 바로 답변 가능한가?
- 지역, 시간, 취향 등 개인화 정보가 필요한가?
- 맥락이나 상세 조건이 부족한가?

**정보 요청이 필요한 경우**:
- 위치 정보 부족: "근처 맛집" (어디 근처인지 불명확)
- 시간 정보 부족: "언제가 좋을까?" (무엇에 대한 시기인지 불명확)
- 취향/조건 부족: "추천해줘" (연령, 장르, 예산 등 조건 불명확)
- 과도하게 모호한 질문

**바로 답변 가능한 경우**:
- 구체적인 정보 요청: "서울 날씨", "파이썬 문법"
- 일반적인 추천: "어린이 도서 추천" (일반적 범주)
- 명확한 질문: "비트코인 현재 가격"

다음 형식으로 응답해주세요:
판단: [needs_more_info 또는 can_answer_directly]
이유: [한 문장 설명]
신뢰도: [0.1-1.0]
"""

            response, _ = await llm_router.generate_response(model, prompt, include_datetime=False)
            lines = response.strip().split('\n')
            
            needs_analysis = False
            reason = "충분한 정보가 제공되었습니다"
            confidence = 0.7
            
            for line in lines:
                if line.startswith('판단:'):
                    judgment = line.split(':', 1)[1].strip().lower()
                    needs_analysis = 'needs_more_info' in judgment
                elif line.startswith('이유:'):
                    reason = line.split(':', 1)[1].strip()
                elif line.startswith('신뢰도:'):
                    try:
                        confidence = float(line.split(':', 1)[1].strip())
                        confidence = max(0.1, min(1.0, confidence))
                    except:
                        pass
            
            return {
                "needs_analysis": needs_analysis,
                "reason": reason,
                "confidence": confidence,
                "method": "llm_based"
            }
            
        except Exception as e:
            self.logger.error(f"LLM 정보 분석 실패, 간단한 휴리스틱 사용: {e}")
            # LLM 실패 시 간단한 fallback
            simple_incomplete_patterns = ["추천", "어떤", "뭐가", "언제", "어디"]
            has_incomplete = any(pattern in query for pattern in simple_incomplete_patterns)
            is_too_short = len(query.split()) < 4
            
            return {
                "needs_analysis": has_incomplete and is_too_short,
                "reason": "간단한 휴리스틱 분석 결과",
                "confidence": 0.5,
                "method": "fallback_heuristic"
            }
    
    
    def _smart_fallback_analysis(self, query: str) -> TaskType:
        """단순화된 fallback 분석 - LLM 실패 시에만 사용"""
        # Canvas 관련 키워드 (명확한 시각적 요청)
        canvas_keywords = [
            "그려", "만들어", "생성", "시각화", "차트", "그래프", "다이어그램", "마인드맵", "그림", "이미지",
            "디자인", "포스터", "로고", "배경", "캐릭터", "풍경", "일러스트", "사진", "AI 이미지"
        ]
        matched_keywords = [k for k in canvas_keywords if k in query]
        if matched_keywords:
            self.logger.info(f"🎨 Canvas 키워드 감지 (fallback) - 매칭 키워드: {matched_keywords}, 쿼리: {query[:50]}...")
            return TaskType.CANVAS
        
        # 명확한 검색 요청 키워드
        search_keywords = ["검색", "찾아", "추천", "날씨", "가격", "현재", "최신", "오늘"]
        if any(k in query for k in search_keywords):
            return TaskType.WEB_SEARCH
        
        # 기본적으로 일반 채팅으로 처리
        return TaskType.GENERAL_CHAT
    
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