"""
LangGraph 기반 WebSearchAgent - 점진적 마이그레이션을 위한 하이브리드 구현

이 모듈은 기존 WebSearchAgent의 LangGraph 버전입니다.
Feature Flag를 통해 점진적으로 활성화되며, 실패 시 자동으로 레거시 버전으로 fallback됩니다.
"""

import time
import asyncio
import json
from typing import Dict, Any, List, Optional, TypedDict, Union
from datetime import datetime
import logging

# LangGraph 핵심 imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

# 기존 시스템 imports
from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.workers.web_search import WebSearchAgent, SearchQuery, EnhancedSearchResult
from app.services.search_service import search_service
from app.services.web_crawler import web_crawler
from app.core.config import settings
from app.core.feature_flags import is_langgraph_enabled, LangGraphFeatureFlags
from app.services.langgraph_monitor import langgraph_monitor

logger = logging.getLogger(__name__)


class WebSearchState(TypedDict):
    """LangGraph 상태 관리를 위한 상태 정의"""
    # 입력 데이터
    original_query: str
    user_id: str
    session_id: Optional[str]
    model: str
    
    # 검색 계획 단계
    search_plan: Optional[Dict[str, Any]]
    search_queries: List[SearchQuery]
    
    # 검색 실행 단계
    search_results: List[EnhancedSearchResult]
    raw_content: List[Dict[str, Any]]
    
    # 분석 및 종합 단계
    relevance_analysis: Optional[Dict[str, Any]]
    synthesized_answer: Optional[str]
    final_response: Optional[str]
    
    # 메타데이터
    execution_metadata: Dict[str, Any]
    citations: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    
    # 에러 처리
    errors: List[str]
    should_fallback: bool


class LangGraphWebSearchAgent(BaseAgent):
    """LangGraph 기반 웹 검색 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_id="langgraph_web_search",
            name="LangGraph 웹 검색 에이간트",
            description="LangGraph StateGraph로 구현된 고급 웹 검색 에이전트"
        )
        
        # 레거시 에이전트 (fallback용)
        self.legacy_agent = WebSearchAgent()
        
        # LangGraph 워크플로우 구성
        self.workflow = self._build_workflow()
        
        # PostgreSQL 체크포인터 설정 (상태 영속성)
        if settings.DATABASE_URL:
            self.checkpointer = PostgresSaver.from_conn_string(
                settings.DATABASE_URL,
                
            )
        else:
            self.checkpointer = None
            logger.warning("DATABASE_URL이 설정되지 않음 - 체크포인터 비활성화")

    def _build_workflow(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        
        # StateGraph 생성
        workflow = StateGraph(WebSearchState)
        
        # 노드 정의
        workflow.add_node("plan_search", self._plan_search_node)
        workflow.add_node("execute_search", self._execute_search_node)
        workflow.add_node("analyze_relevance", self._analyze_relevance_node)
        workflow.add_node("synthesize_answer", self._synthesize_answer_node)
        workflow.add_node("generate_response", self._generate_response_node)
        
        # 엣지 정의
        workflow.set_entry_point("plan_search")
        workflow.add_edge("plan_search", "execute_search")
        workflow.add_edge("execute_search", "analyze_relevance")
        workflow.add_edge("analyze_relevance", "synthesize_answer")
        workflow.add_edge("synthesize_answer", "generate_response")
        workflow.add_edge("generate_response", END)
        
        # 조건부 엣지 (에러 처리)
        workflow.add_conditional_edges(
            "plan_search",
            self._should_continue,
            {
                "continue": "execute_search",
                "fallback": END
            }
        )
        
        return workflow

    async def _plan_search_node(self, state: WebSearchState) -> Dict[str, Any]:
        """검색 계획 생성 노드"""
        try:
            logger.info(f"🔍 LangGraph: 검색 계획 생성 중... (query: {state['original_query'][:50]})")
            
            # LLM을 사용한 검색 계획 생성
            model = self._get_llm_model(state["model"])
            
            planning_prompt = ChatPromptTemplate.from_messages([
                ("system", """당신은 웹 검색 전문가입니다. 사용자의 질문을 분석하여 최적의 검색 전략을 수립하세요.

검색 계획에 포함해야 할 요소:
1. 핵심 검색어 3-5개 (우선순위별로)
2. 검색 의도 분류 (정보형/추천형/비교형/방법형)
3. 언어 설정 (한국어/영어)
4. 특화 검색 전략 (일반/사이트특화/URL크롤링)

JSON 형식으로 응답하세요."""),
                ("human", "질문: {query}")
            ])
            
            response = await model.ainvoke(planning_prompt.format_messages(query=state["original_query"]))
            
            # JSON 파싱 시도
            try:
                search_plan = json.loads(response.content)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본 계획 생성
                search_plan = {
                    "primary_queries": [state["original_query"]],
                    "intent_type": "정보형",
                    "language": "ko",
                    "search_strategy": "일반"
                }
            
            # SearchQuery 객체들 생성
            search_queries = []
            for i, query in enumerate(search_plan.get("primary_queries", [])):
                search_queries.append(SearchQuery(
                    query=query,
                    priority=1 if i < 2 else 2,
                    intent_type=search_plan.get("intent_type", "정보형"),
                    language=search_plan.get("language", "ko"),
                    max_results=5,
                    search_type="general"
                ))
            
            return {
                "search_plan": search_plan,
                "search_queries": search_queries,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "plan_generation_time": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 검색 계획 생성 실패: {e}")
            return {
                "errors": state.get("errors", []) + [f"검색 계획 생성 실패: {str(e)}"],
                "should_fallback": True
            }

    async def _execute_search_node(self, state: WebSearchState) -> Dict[str, Any]:
        """검색 실행 노드"""
        try:
            logger.info(f"🔍 LangGraph: 검색 실행 중... ({len(state['search_queries'])}개 쿼리)")
            
            search_results = []
            raw_content = []
            
            # 병렬 검색 실행
            search_tasks = []
            for query in state["search_queries"]:
                task = self._execute_single_search(query)
                search_tasks.append(task)
            
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"검색 실패 (쿼리 {i}): {result}")
                    continue
                
                search_results.append(result)
                raw_content.extend(result.results)
            
            return {
                "search_results": search_results,
                "raw_content": raw_content,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "search_execution_time": time.time(),
                    "total_results": len(raw_content)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 검색 실행 실패: {e}")
            return {
                "errors": state.get("errors", []) + [f"검색 실행 실패: {str(e)}"],
                "should_fallback": True
            }

    async def _execute_single_search(self, query: SearchQuery) -> EnhancedSearchResult:
        """단일 검색 실행"""
        try:
            # 기존 search_service 활용
            search_results = await search_service.search(
                query=query.query,
                max_results=query.max_results,
                language=query.language
            )
            
            return EnhancedSearchResult(
                search_query=query,
                results=search_results,
                relevance_score=0.8,  # 임시값, 추후 LLM 기반 스코어링
                success=True
            )
            
        except Exception as e:
            logger.error(f"단일 검색 실패: {e}")
            return EnhancedSearchResult(
                search_query=query,
                results=[],
                relevance_score=0.0,
                success=False
            )

    async def _analyze_relevance_node(self, state: WebSearchState) -> Dict[str, Any]:
        """검색 결과 관련성 분석 노드"""
        try:
            logger.info("🔍 LangGraph: 검색 결과 관련성 분석 중...")
            
            model = self._get_llm_model(state["model"])
            
            # 검색 결과 요약 생성
            results_summary = []
            for result in state["raw_content"][:10]:  # 상위 10개만 분석
                results_summary.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", "")[:200],  # 200자 제한
                    "url": result.get("url", "")
                })
            
            analysis_prompt = ChatPromptTemplate.from_messages([
                ("system", """검색 결과를 분석하여 사용자 질문과의 관련성을 평가하세요.
각 결과에 대해 관련성 점수(0-10)와 핵심 정보를 추출하세요."""),
                ("human", """질문: {query}

검색 결과:
{results}

JSON 형식으로 분석 결과를 제공하세요.""")
            ])
            
            response = await model.ainvoke(analysis_prompt.format_messages(
                query=state["original_query"],
                results=json.dumps(results_summary, ensure_ascii=False, indent=2)
            ))
            
            try:
                relevance_analysis = json.loads(response.content)
            except json.JSONDecodeError:
                relevance_analysis = {"analysis": "분석 결과 파싱 실패"}
            
            return {
                "relevance_analysis": relevance_analysis,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "relevance_analysis_time": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 관련성 분석 실패: {e}")
            return {
                "errors": state.get("errors", []) + [f"관련성 분석 실패: {str(e)}"]
            }

    async def _synthesize_answer_node(self, state: WebSearchState) -> Dict[str, Any]:
        """답변 종합 노드"""
        try:
            logger.info("🔍 LangGraph: 답변 종합 중...")
            
            model = self._get_llm_model(state["model"])
            
            # 핵심 정보 추출
            key_info = []
            citations = []
            sources = []
            
            for i, result in enumerate(state["raw_content"][:8]):  # 상위 8개 결과
                key_info.append({
                    "content": result.get("snippet", ""),
                    "source": result.get("title", ""),
                    "url": result.get("url", ""),
                    "index": i + 1
                })
                
                citations.append({
                    "id": i + 1,
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", "")[:150]
                })
                
                sources.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "domain": result.get("domain", ""),
                    "published_date": result.get("published_date")
                })
            
            synthesis_prompt = ChatPromptTemplate.from_messages([
                ("system", """검색 결과를 종합하여 사용자 질문에 대한 정확하고 포괄적인 답변을 작성하세요.

답변 작성 원칙:
1. 정확한 정보만 포함
2. 출처를 명시하여 신뢰성 확보  
3. 구조화된 형태로 이해하기 쉽게 작성
4. 부족한 정보가 있으면 명시

답변 끝에는 [출처: 1, 2, 3] 형식으로 인용 번호를 추가하세요."""),
                ("human", """질문: {query}

검색된 정보:
{key_info}

종합적인 답변을 작성하세요.""")
            ])
            
            response = await model.ainvoke(synthesis_prompt.format_messages(
                query=state["original_query"],
                key_info=json.dumps(key_info, ensure_ascii=False, indent=2)
            ))
            
            synthesized_answer = response.content
            
            return {
                "synthesized_answer": synthesized_answer,
                "citations": citations,
                "sources": sources,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "synthesis_time": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 답변 종합 실패: {e}")
            return {
                "errors": state.get("errors", []) + [f"답변 종합 실패: {str(e)}"]
            }

    async def _generate_response_node(self, state: WebSearchState) -> Dict[str, Any]:
        """최종 응답 생성 노드"""
        try:
            logger.info("🔍 LangGraph: 최종 응답 생성 중...")
            
            # 실행 시간 계산
            start_time = state.get("execution_metadata", {}).get("plan_generation_time", time.time())
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            final_response = state.get("synthesized_answer", "검색 결과를 찾을 수 없습니다.")
            
            return {
                "final_response": final_response,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "total_execution_time_ms": execution_time_ms,
                    "completion_time": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 최종 응답 생성 실패: {e}")
            return {
                "errors": state.get("errors", []) + [f"최종 응답 생성 실패: {str(e)}"],
                "final_response": "응답 생성 중 오류가 발생했습니다."
            }

    def _should_continue(self, state: WebSearchState) -> str:
        """조건부 라우팅 함수"""
        if state.get("should_fallback", False) or len(state.get("errors", [])) > 2:
            return "fallback"
        return "continue"

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
            # 기본값: Claude
            return ChatAnthropic(
                model_name="claude-3-sonnet-20240229",
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.3
            )

    async def execute(self, input_data: AgentInput, model: str = "claude-sonnet", progress_callback=None) -> AgentOutput:
        """
        LangGraph 웹 검색 에이전트 실행
        Feature Flag에 따라 LangGraph 또는 Legacy 모드로 실행
        """
        start_time = time.time()
        
        # Feature Flag 확인
        if not is_langgraph_enabled(
            LangGraphFeatureFlags.LANGGRAPH_WEB_SEARCH, 
            input_data.user_id
        ):
            logger.info("🔄 Feature Flag: Legacy WebSearchAgent 사용")
            return await self.legacy_agent.execute(input_data, model, progress_callback)
        
        logger.info(f"🚀 LangGraph WebSearchAgent 실행 시작 (사용자: {input_data.user_id})")
        
        try:
            # 성능 모니터링 시작
            await langgraph_monitor.start_execution("langgraph_web_search")
            
            # 초기 상태 설정
            initial_state = WebSearchState(
                original_query=input_data.query,
                user_id=input_data.user_id,
                session_id=input_data.session_id,
                model=model,
                search_plan=None,
                search_queries=[],
                search_results=[],
                raw_content=[],
                relevance_analysis=None,
                synthesized_answer=None,
                final_response=None,
                execution_metadata={"start_time": start_time},
                citations=[],
                sources=[],
                errors=[],
                should_fallback=False
            )
            
            # LangGraph 워크플로우 실행
            if self.checkpointer:
                # 체크포인터 사용 (상태 영속성)
                app = self.workflow.compile(checkpointer=self.checkpointer)
                config = {"configurable": {"thread_id": f"{input_data.user_id}_{input_data.session_id}"}}
                final_state = await app.ainvoke(initial_state, config=config)
            else:
                # 체크포인터 없이 실행
                app = self.workflow.compile()
                final_state = await app.ainvoke(initial_state)
            
            # 결과 처리
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # 에러가 있거나 fallback이 필요한 경우
            if final_state.get("should_fallback", False) or len(final_state.get("errors", [])) > 0:
                logger.warning("🔄 LangGraph 실행 실패 - Legacy 모드로 fallback")
                langgraph_monitor.record_fallback("langgraph_web_search", f"Errors: {final_state.get('errors', [])}")
                return await self.legacy_agent.execute(input_data, model, progress_callback)
            
            # 성공적인 LangGraph 결과 반환
            await langgraph_monitor.track_execution(
                agent_type="langgraph_web_search",
                execution_time=execution_time_ms / 1000,
                success=True,
                user_id=input_data.user_id
            )
            
            result = AgentOutput(
                result=final_state.get("final_response", "검색 결과를 생성할 수 없습니다."),
                metadata={
                    "agent_version": "langgraph",
                    "search_queries_count": len(final_state.get("search_queries", [])),
                    "results_count": len(final_state.get("raw_content", [])),
                    "langgraph_execution": True,
                    **final_state.get("execution_metadata", {})
                },
                execution_time_ms=execution_time_ms,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.utcnow().isoformat(),
                citations=final_state.get("citations", []),
                sources=final_state.get("sources", [])
            )
            
            logger.info(f"✅ LangGraph WebSearchAgent 실행 완료 ({execution_time_ms}ms)")
            return result
            
        except Exception as e:
            logger.error(f"❌ LangGraph WebSearchAgent 실행 실패: {e}")
            
            # 에러 시 자동 fallback
            await langgraph_monitor.track_execution(
                agent_type="langgraph_web_search",
                execution_time=(time.time() - start_time),
                success=False,
                error_message=str(e),
                user_id=input_data.user_id
            )
            
            langgraph_monitor.record_fallback("langgraph_web_search", f"Exception: {str(e)}")
            
            logger.info("🔄 예외 발생 - Legacy WebSearchAgent로 fallback")
            return await self.legacy_agent.execute(input_data, model, progress_callback)

    def get_capabilities(self) -> List[str]:
        """에이전트 기능 목록"""
        return [
            "다단계 검색 계획 수립",
            "병렬 검색 실행",
            "LLM 기반 관련성 분석",
            "지능형 답변 종합",
            "자동 fallback 지원",
            "상태 영속성 (PostgreSQL)",
            "실시간 성능 모니터링"
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
langgraph_web_search_agent = LangGraphWebSearchAgent()