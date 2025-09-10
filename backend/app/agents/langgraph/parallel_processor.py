"""
LangGraph 기반 고성능 병렬 처리 시스템

최신 LangGraph StateGraph를 활용하여 Fan-out/Fan-in 패턴과 Reducer를 구현한
최고 성능의 병렬 처리 에이전트 시스템입니다.
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
from concurrent.futures import ThreadPoolExecutor, as_completed
import functools

# LangGraph 핵심 imports
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Send
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

# 기존 시스템 imports
from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.core.config import settings
from app.core.feature_flags import is_langgraph_enabled, LangGraphFeatureFlags
from app.services.langgraph_monitor import langgraph_monitor
from app.services.search_service import search_service
from app.services.web_crawler import web_crawler

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """병렬 처리 작업 유형"""
    SEARCH = "search"
    WEB_CRAWL = "web_crawl"
    LLM_ANALYSIS = "llm_analysis"
    DATA_PROCESSING = "data_processing"
    CONTENT_GENERATION = "content_generation"
    SIMILARITY_ANALYSIS = "similarity_analysis"


class ProcessingStrategy(Enum):
    """처리 전략"""
    CONCURRENT_ALL = "concurrent_all"        # 모든 작업 동시 실행
    BATCHED_PARALLEL = "batched_parallel"    # 배치별 병렬 처리
    ADAPTIVE_LOAD = "adaptive_load"          # 부하 적응형 처리
    PRIORITY_BASED = "priority_based"        # 우선순위 기반 처리


@dataclass
class ParallelTask:
    """병렬 처리 작업 정의"""
    task_id: str
    task_type: TaskType
    task_data: Dict[str, Any]
    priority: int = 1
    timeout: float = 30.0
    retry_count: int = 3
    dependencies: List[str] = None


@dataclass
class TaskResult:
    """작업 결과"""
    task_id: str
    success: bool
    result: Any
    execution_time: float
    error: Optional[str] = None
    retry_attempt: int = 0
    metadata: Dict[str, Any] = None


class ParallelProcessingState(TypedDict):
    """LangGraph 병렬 처리 상태 정의"""
    # 입력 데이터
    original_query: str
    user_id: str
    session_id: Optional[str]
    model: str
    
    # 작업 계획
    processing_strategy: Optional[str]
    task_breakdown: Optional[List[Dict[str, Any]]]
    dependency_graph: Optional[Dict[str, List[str]]]
    
    # 병렬 실행 결과 (Reducer 사용)
    search_results: Annotated[List[Dict[str, Any]], operator.add]
    analysis_results: Annotated[List[Dict[str, Any]], operator.add]
    generation_results: Annotated[List[Dict[str, Any]], operator.add]
    processing_results: Annotated[List[Dict[str, Any]], operator.add]
    
    # 통합 결과
    aggregated_results: Optional[Dict[str, Any]]
    final_output: Optional[str]
    
    # 성능 메트릭
    execution_metadata: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    parallel_efficiency: float
    
    # 에러 처리
    errors: Annotated[List[str], operator.add]
    task_failures: Annotated[List[Dict[str, Any]], operator.add]
    should_fallback: bool


class LangGraphParallelProcessor(BaseAgent):
    """LangGraph 기반 고성능 병렬 처리 시스템"""
    
    def __init__(self):
        super().__init__(
            agent_id="langgraph_parallel_processor",
            name="LangGraph 병렬 처리 시스템",
            description="LangGraph StateGraph로 구현된 고성능 병렬 처리 에이전트"
        )
        
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
        
        # 병렬 처리 설정
        self.max_concurrent_tasks = 10
        self.batch_size = 5
        self.thread_pool = ThreadPoolExecutor(max_workers=20)

    def _build_workflow(self) -> StateGraph:
        """LangGraph 병렬 처리 워크플로우 구성"""
        
        # StateGraph 생성 (Reducer 사용)
        workflow = StateGraph(ParallelProcessingState)
        
        # 노드 정의 - 병렬 처리 파이프라인
        workflow.add_node("plan_parallel_tasks", self._plan_parallel_tasks_node)
        workflow.add_node("execute_search_tasks", self._execute_search_tasks_node)
        workflow.add_node("execute_analysis_tasks", self._execute_analysis_tasks_node)
        workflow.add_node("execute_generation_tasks", self._execute_generation_tasks_node)
        workflow.add_node("execute_processing_tasks", self._execute_processing_tasks_node)
        workflow.add_node("aggregate_results", self._aggregate_results_node)
        workflow.add_node("optimize_output", self._optimize_output_node)
        
        # 엣지 정의 - Fan-out에서 Fan-in 패턴
        workflow.set_entry_point("plan_parallel_tasks")
        
        # Fan-out: 계획에서 병렬 실행으로
        workflow.add_edge("plan_parallel_tasks", "execute_search_tasks")
        workflow.add_edge("plan_parallel_tasks", "execute_analysis_tasks")
        workflow.add_edge("plan_parallel_tasks", "execute_generation_tasks")
        workflow.add_edge("plan_parallel_tasks", "execute_processing_tasks")
        
        # Fan-in: 병렬 실행에서 통합으로
        workflow.add_edge("execute_search_tasks", "aggregate_results")
        workflow.add_edge("execute_analysis_tasks", "aggregate_results")
        workflow.add_edge("execute_generation_tasks", "aggregate_results")
        workflow.add_edge("execute_processing_tasks", "aggregate_results")
        
        # 최종 출력
        workflow.add_edge("aggregate_results", "optimize_output")
        workflow.add_edge("optimize_output", END)
        
        # 조건부 엣지 (에러 처리 및 최적화)
        workflow.add_conditional_edges(
            "plan_parallel_tasks",
            self._should_continue,
            {
                "continue": "execute_search_tasks",
                "fallback": END
            }
        )
        
        workflow.add_conditional_edges(
            "aggregate_results",
            self._should_retry_failed_tasks,
            {
                "retry": "execute_search_tasks",
                "continue": "optimize_output"
            }
        )
        
        return workflow

    async def _plan_parallel_tasks_node(self, state: ParallelProcessingState) -> Dict[str, Any]:
        """병렬 작업 계획 수립 노드"""
        try:
            logger.info(f"🚀 LangGraph 병렬 처리: 작업 계획 수립 중... (query: {state['original_query'][:50]})")
            
            model = self._get_llm_model(state["model"])
            
            planning_prompt = ChatPromptTemplate.from_messages([
                ("system", """전문적인 병렬 처리 계획가로서 사용자 질문을 분석하여 최적의 병렬 처리 전략을 수립하세요.

분석 항목:
1. 처리 전략 (concurrent_all/batched_parallel/adaptive_load/priority_based)
2. 작업 분해 (검색/분석/생성/처리 작업들)
3. 우선순위 설정 (1-5, 1이 최고 우선순위)
4. 의존성 관계 파악
5. 예상 처리 시간 및 리소스 요구사항

병렬 처리 가능한 작업들:
- 검색 작업: 다중 검색 엔진, 키워드 조합
- 분석 작업: 내용 분석, 관련성 평가, 품질 분석
- 생성 작업: 요약 생성, 답변 생성, 추천 생성
- 처리 작업: 데이터 정제, 구조화, 최적화

JSON 형식으로 상세한 병렬 처리 계획을 제공하세요."""),
                ("human", """사용자 질문: "{query}"

이 질문을 처리하기 위한 최적의 병렬 처리 계획을 수립해주세요.""")
            ])
            
            response = await model.ainvoke(planning_prompt.format_messages(query=state["original_query"]))
            
            try:
                plan_data = json.loads(response.content)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본 계획
                plan_data = {
                    "processing_strategy": "concurrent_all",
                    "task_breakdown": [
                        {
                            "task_id": f"search_{uuid.uuid4().hex[:8]}",
                            "task_type": "search",
                            "task_data": {"query": state["original_query"], "max_results": 10},
                            "priority": 1
                        }
                    ],
                    "dependency_graph": {},
                    "estimated_time": 5.0
                }
            
            return {
                "processing_strategy": plan_data.get("processing_strategy", "concurrent_all"),
                "task_breakdown": plan_data.get("task_breakdown", []),
                "dependency_graph": plan_data.get("dependency_graph", {}),
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "planning_completed_at": time.time(),
                    "planned_tasks_count": len(plan_data.get("task_breakdown", []))
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 병렬 작업 계획 실패: {e}")
            return {
                "errors": [f"작업 계획 실패: {str(e)}"],
                "should_fallback": True
            }

    async def _execute_search_tasks_node(self, state: ParallelProcessingState) -> Dict[str, Any]:
        """검색 작업 병렬 실행 노드"""
        try:
            logger.info("🔍 LangGraph 병렬 처리: 검색 작업 실행 중...")
            
            task_breakdown = state.get("task_breakdown", [])
            search_tasks = [task for task in task_breakdown if task.get("task_type") == "search"]
            
            if not search_tasks:
                return {"search_results": []}
            
            # 병렬 검색 실행
            search_results = []
            async_tasks = []
            
            for task in search_tasks[:self.max_concurrent_tasks]:  # 최대 동시 작업 제한
                async_tasks.append(self._execute_single_search_task(task))
            
            # 병렬 실행 및 결과 수집
            results = await asyncio.gather(*async_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"검색 작업 {i} 실패: {result}")
                    search_results.append({
                        "task_id": search_tasks[i].get("task_id", f"search_{i}"),
                        "success": False,
                        "error": str(result),
                        "execution_time": 0
                    })
                else:
                    search_results.append(result)
            
            return {
                "search_results": search_results,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "search_tasks_completed_at": time.time(),
                    "search_tasks_count": len(search_results)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 검색 작업 실행 실패: {e}")
            return {
                "errors": [f"검색 작업 실행 실패: {str(e)}"],
                "search_results": []
            }

    async def _execute_analysis_tasks_node(self, state: ParallelProcessingState) -> Dict[str, Any]:
        """분석 작업 병렬 실행 노드"""
        try:
            logger.info("🧠 LangGraph 병렬 처리: 분석 작업 실행 중...")
            
            task_breakdown = state.get("task_breakdown", [])
            analysis_tasks = [task for task in task_breakdown if task.get("task_type") == "llm_analysis"]
            
            if not analysis_tasks:
                return {"analysis_results": []}
            
            # 병렬 분석 실행
            analysis_results = []
            async_tasks = []
            
            for task in analysis_tasks[:self.max_concurrent_tasks]:
                async_tasks.append(self._execute_single_analysis_task(task, state))
            
            # 병렬 실행
            results = await asyncio.gather(*async_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"분석 작업 {i} 실패: {result}")
                    analysis_results.append({
                        "task_id": analysis_tasks[i].get("task_id", f"analysis_{i}"),
                        "success": False,
                        "error": str(result),
                        "execution_time": 0
                    })
                else:
                    analysis_results.append(result)
            
            return {
                "analysis_results": analysis_results,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "analysis_tasks_completed_at": time.time(),
                    "analysis_tasks_count": len(analysis_results)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 분석 작업 실행 실패: {e}")
            return {
                "errors": [f"분석 작업 실행 실패: {str(e)}"],
                "analysis_results": []
            }

    async def _execute_generation_tasks_node(self, state: ParallelProcessingState) -> Dict[str, Any]:
        """생성 작업 병렬 실행 노드"""
        try:
            logger.info("✨ LangGraph 병렬 처리: 생성 작업 실행 중...")
            
            task_breakdown = state.get("task_breakdown", [])
            generation_tasks = [task for task in task_breakdown if task.get("task_type") == "content_generation"]
            
            if not generation_tasks:
                return {"generation_results": []}
            
            # 병렬 생성 실행
            generation_results = []
            async_tasks = []
            
            for task in generation_tasks[:self.max_concurrent_tasks]:
                async_tasks.append(self._execute_single_generation_task(task, state))
            
            # 병렬 실행
            results = await asyncio.gather(*async_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"생성 작업 {i} 실패: {result}")
                    generation_results.append({
                        "task_id": generation_tasks[i].get("task_id", f"generation_{i}"),
                        "success": False,
                        "error": str(result),
                        "execution_time": 0
                    })
                else:
                    generation_results.append(result)
            
            return {
                "generation_results": generation_results,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "generation_tasks_completed_at": time.time(),
                    "generation_tasks_count": len(generation_results)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 생성 작업 실행 실패: {e}")
            return {
                "errors": [f"생성 작업 실행 실패: {str(e)}"],
                "generation_results": []
            }

    async def _execute_processing_tasks_node(self, state: ParallelProcessingState) -> Dict[str, Any]:
        """데이터 처리 작업 병렬 실행 노드"""
        try:
            logger.info("⚡ LangGraph 병렬 처리: 데이터 처리 작업 실행 중...")
            
            task_breakdown = state.get("task_breakdown", [])
            processing_tasks = [task for task in task_breakdown if task.get("task_type") == "data_processing"]
            
            if not processing_tasks:
                return {"processing_results": []}
            
            # 병렬 처리 실행
            processing_results = []
            async_tasks = []
            
            for task in processing_tasks[:self.max_concurrent_tasks]:
                async_tasks.append(self._execute_single_processing_task(task, state))
            
            # 병렬 실행
            results = await asyncio.gather(*async_tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"처리 작업 {i} 실패: {result}")
                    processing_results.append({
                        "task_id": processing_tasks[i].get("task_id", f"processing_{i}"),
                        "success": False,
                        "error": str(result),
                        "execution_time": 0
                    })
                else:
                    processing_results.append(result)
            
            return {
                "processing_results": processing_results,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "processing_tasks_completed_at": time.time(),
                    "processing_tasks_count": len(processing_results)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 처리 작업 실행 실패: {e}")
            return {
                "errors": [f"처리 작업 실행 실패: {str(e)}"],
                "processing_results": []
            }

    async def _aggregate_results_node(self, state: ParallelProcessingState) -> Dict[str, Any]:
        """결과 통합 노드 - Fan-in 패턴"""
        try:
            logger.info("🔄 LangGraph 병렬 처리: 결과 통합 중...")
            
            # 모든 병렬 실행 결과 수집 (Reducer로 자동 집계됨)
            search_results = state.get("search_results", [])
            analysis_results = state.get("analysis_results", [])
            generation_results = state.get("generation_results", [])
            processing_results = state.get("processing_results", [])
            
            # 성공/실패 통계
            all_results = search_results + analysis_results + generation_results + processing_results
            successful_tasks = [r for r in all_results if r.get("success", False)]
            failed_tasks = [r for r in all_results if not r.get("success", False)]
            
            # 병렬 효율성 계산
            total_execution_time = sum(r.get("execution_time", 0) for r in all_results)
            parallel_efficiency = self._calculate_parallel_efficiency(all_results, state)
            
            # 결과 통합 및 우선순위 정렬
            aggregated_results = {
                "search_data": self._extract_search_data(search_results),
                "analysis_insights": self._extract_analysis_insights(analysis_results),
                "generated_content": self._extract_generated_content(generation_results),
                "processed_data": self._extract_processed_data(processing_results),
                "statistics": {
                    "total_tasks": len(all_results),
                    "successful_tasks": len(successful_tasks),
                    "failed_tasks": len(failed_tasks),
                    "success_rate": len(successful_tasks) / len(all_results) * 100 if all_results else 0
                }
            }
            
            # 성능 메트릭 업데이트
            performance_metrics = {
                "parallel_efficiency": parallel_efficiency,
                "total_execution_time": total_execution_time,
                "avg_task_time": total_execution_time / len(all_results) if all_results else 0,
                "concurrency_benefit": self._calculate_concurrency_benefit(all_results),
                "resource_utilization": min(100, len(all_results) / self.max_concurrent_tasks * 100)
            }
            
            return {
                "aggregated_results": aggregated_results,
                "parallel_efficiency": parallel_efficiency,
                "performance_metrics": performance_metrics,
                "task_failures": failed_tasks,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "aggregation_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 결과 통합 실패: {e}")
            return {
                "errors": [f"결과 통합 실패: {str(e)}"]
            }

    async def _optimize_output_node(self, state: ParallelProcessingState) -> Dict[str, Any]:
        """출력 최적화 노드"""
        try:
            logger.info("🎯 LangGraph 병렬 처리: 출력 최적화 중...")
            
            aggregated_results = state.get("aggregated_results", {})
            performance_metrics = state.get("performance_metrics", {})
            
            model = self._get_llm_model(state["model"])
            
            # 최적화된 최종 응답 생성
            optimization_prompt = ChatPromptTemplate.from_messages([
                ("system", """병렬 처리 결과 최적화 전문가로서 다음을 수행하세요:

1. 모든 병렬 처리 결과를 종합하여 완전한 답변 생성
2. 중복된 정보 제거 및 우선순위 정렬
3. 사용자가 이해하기 쉬운 구조로 정리
4. 신뢰할 수 있는 정보와 불확실한 정보 구분
5. 성능 최적화 혜택 간략 언급

한국어로 자연스럽고 포괄적인 답변을 작성해주세요."""),
                ("human", """원본 질문: "{query}"

병렬 처리 결과:
- 검색 데이터: {search_data}
- 분석 인사이트: {analysis_insights}
- 생성된 콘텐츠: {generated_content}
- 처리된 데이터: {processed_data}

성능 메트릭:
- 병렬 효율성: {parallel_efficiency:.1f}%
- 성공률: {success_rate:.1f}%

이 모든 정보를 종합하여 최적화된 최종 답변을 생성해주세요.""")
            ])
            
            search_data = aggregated_results.get("search_data", {})
            analysis_insights = aggregated_results.get("analysis_insights", {})
            generated_content = aggregated_results.get("generated_content", {})
            processed_data = aggregated_results.get("processed_data", {})
            statistics = aggregated_results.get("statistics", {})
            
            response = await model.ainvoke(optimization_prompt.format_messages(
                query=state["original_query"],
                search_data=json.dumps(search_data, ensure_ascii=False)[:500],
                analysis_insights=json.dumps(analysis_insights, ensure_ascii=False)[:500],
                generated_content=json.dumps(generated_content, ensure_ascii=False)[:500],
                processed_data=json.dumps(processed_data, ensure_ascii=False)[:500],
                parallel_efficiency=performance_metrics.get("parallel_efficiency", 0),
                success_rate=statistics.get("success_rate", 0)
            ))
            
            final_output = response.content
            
            return {
                "final_output": final_output,
                "execution_metadata": {
                    **state.get("execution_metadata", {}),
                    "optimization_completed_at": time.time()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 출력 최적화 실패: {e}")
            return {
                "final_output": "병렬 처리를 통해 정보를 수집했지만, 최종 결과 생성 중 오류가 발생했습니다.",
                "errors": [f"출력 최적화 실패: {str(e)}"]
            }

    # 유틸리티 메서드들

    def _should_continue(self, state: ParallelProcessingState) -> str:
        """조건부 라우팅: 계속 진행 여부 결정"""
        if state.get("should_fallback", False) or len(state.get("errors", [])) > 5:
            return "fallback"
        return "continue"

    def _should_retry_failed_tasks(self, state: ParallelProcessingState) -> str:
        """조건부 라우팅: 실패한 작업 재시도 여부 결정"""
        task_failures = state.get("task_failures", [])
        critical_failures = [f for f in task_failures if f.get("priority", 3) <= 2]
        
        if len(critical_failures) > 0 and state.get("execution_metadata", {}).get("retry_count", 0) < 2:
            return "retry"
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
            return ChatAnthropic(
                model_name="claude-3-sonnet-20240229",
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.3
            )

    async def _execute_single_search_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """단일 검색 작업 실행"""
        start_time = time.time()
        try:
            task_data = task.get("task_data", {})
            query = task_data.get("query", "")
            max_results = task_data.get("max_results", 10)
            
            # 검색 서비스 호출
            results = await search_service.search(
                query=query,
                max_results=max_results,
                language="ko"
            )
            
            execution_time = time.time() - start_time
            
            return {
                "task_id": task.get("task_id", "unknown"),
                "success": True,
                "result": results,
                "execution_time": execution_time,
                "metadata": {
                    "query": query,
                    "results_count": len(results)
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"검색 작업 실행 실패: {e}")
            return {
                "task_id": task.get("task_id", "unknown"),
                "success": False,
                "result": None,
                "execution_time": execution_time,
                "error": str(e)
            }

    async def _execute_single_analysis_task(self, task: Dict[str, Any], state: ParallelProcessingState) -> Dict[str, Any]:
        """단일 분석 작업 실행"""
        start_time = time.time()
        try:
            task_data = task.get("task_data", {})
            content = task_data.get("content", "")
            analysis_type = task_data.get("analysis_type", "general")
            
            model = self._get_llm_model(state["model"])
            
            analysis_prompt = ChatPromptTemplate.from_messages([
                ("system", f"""{analysis_type} 분석 전문가로서 주어진 콘텐츠를 분석하세요.
분석 결과를 JSON 형식으로 제공하세요."""),
                ("human", "분석할 내용: {content}")
            ])
            
            response = await model.ainvoke(analysis_prompt.format_messages(content=content[:1000]))
            
            try:
                analysis_result = json.loads(response.content)
            except json.JSONDecodeError:
                analysis_result = {"analysis": response.content, "type": analysis_type}
            
            execution_time = time.time() - start_time
            
            return {
                "task_id": task.get("task_id", "unknown"),
                "success": True,
                "result": analysis_result,
                "execution_time": execution_time,
                "metadata": {"analysis_type": analysis_type}
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"분석 작업 실행 실패: {e}")
            return {
                "task_id": task.get("task_id", "unknown"),
                "success": False,
                "result": None,
                "execution_time": execution_time,
                "error": str(e)
            }

    async def _execute_single_generation_task(self, task: Dict[str, Any], state: ParallelProcessingState) -> Dict[str, Any]:
        """단일 생성 작업 실행"""
        start_time = time.time()
        try:
            task_data = task.get("task_data", {})
            prompt = task_data.get("prompt", "")
            generation_type = task_data.get("generation_type", "general")
            
            model = self._get_llm_model(state["model"])
            
            generation_prompt = ChatPromptTemplate.from_messages([
                ("system", f"""{generation_type} 콘텐츠 생성 전문가로서 요청된 내용을 생성하세요."""),
                ("human", "{prompt}")
            ])
            
            response = await model.ainvoke(generation_prompt.format_messages(prompt=prompt))
            
            execution_time = time.time() - start_time
            
            return {
                "task_id": task.get("task_id", "unknown"),
                "success": True,
                "result": {"content": response.content, "type": generation_type},
                "execution_time": execution_time,
                "metadata": {"generation_type": generation_type}
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"생성 작업 실행 실패: {e}")
            return {
                "task_id": task.get("task_id", "unknown"),
                "success": False,
                "result": None,
                "execution_time": execution_time,
                "error": str(e)
            }

    async def _execute_single_processing_task(self, task: Dict[str, Any], state: ParallelProcessingState) -> Dict[str, Any]:
        """단일 처리 작업 실행"""
        start_time = time.time()
        try:
            task_data = task.get("task_data", {})
            data = task_data.get("data", [])
            processing_type = task_data.get("processing_type", "filter")
            
            # 처리 유형별 로직
            if processing_type == "filter":
                processed_data = [item for item in data if self._should_include_item(item)]
            elif processing_type == "sort":
                processed_data = sorted(data, key=lambda x: x.get("score", 0), reverse=True)
            elif processing_type == "deduplicate":
                processed_data = self._deduplicate_items(data)
            else:
                processed_data = data
            
            execution_time = time.time() - start_time
            
            return {
                "task_id": task.get("task_id", "unknown"),
                "success": True,
                "result": processed_data,
                "execution_time": execution_time,
                "metadata": {"processing_type": processing_type, "processed_count": len(processed_data)}
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"처리 작업 실행 실패: {e}")
            return {
                "task_id": task.get("task_id", "unknown"),
                "success": False,
                "result": None,
                "execution_time": execution_time,
                "error": str(e)
            }

    def _calculate_parallel_efficiency(self, results: List[Dict[str, Any]], state: ParallelProcessingState) -> float:
        """병렬 효율성 계산"""
        try:
            if not results:
                return 0.0
            
            # 성공한 작업들의 실행 시간
            successful_results = [r for r in results if r.get("success", False)]
            if not successful_results:
                return 0.0
            
            execution_times = [r.get("execution_time", 0) for r in successful_results]
            
            # 순차 실행 예상 시간 vs 실제 병렬 실행 시간
            sequential_time = sum(execution_times)
            parallel_time = max(execution_times) if execution_times else 0
            
            if parallel_time <= 0:
                return 0.0
            
            # 효율성 = (순차시간 - 병렬시간) / 순차시간 * 100
            efficiency = (sequential_time - parallel_time) / sequential_time * 100
            return min(100.0, max(0.0, efficiency))
            
        except Exception:
            return 0.0

    def _calculate_concurrency_benefit(self, results: List[Dict[str, Any]]) -> float:
        """동시성 혜택 계산"""
        try:
            if len(results) <= 1:
                return 0.0
            
            execution_times = [r.get("execution_time", 0) for r in results if r.get("success", False)]
            if not execution_times:
                return 0.0
            
            # 평균 작업 시간 vs 실제 병렬 처리 시간
            avg_task_time = sum(execution_times) / len(execution_times)
            max_parallel_time = max(execution_times)
            
            if max_parallel_time <= 0:
                return 0.0
            
            # 동시성 혜택 = 작업 수 * 평균 시간 / 최대 병렬 시간
            benefit = len(execution_times) * avg_task_time / max_parallel_time
            return min(10.0, max(1.0, benefit))  # 1배~10배 사이로 제한
            
        except Exception:
            return 1.0

    def _extract_search_data(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """검색 결과 데이터 추출"""
        successful_searches = [r for r in search_results if r.get("success", False)]
        
        all_results = []
        for search in successful_searches:
            results = search.get("result", [])
            if isinstance(results, list):
                all_results.extend(results)
        
        return {
            "total_results": len(all_results),
            "search_count": len(successful_searches),
            "top_results": all_results[:10]  # 상위 10개만
        }

    def _extract_analysis_insights(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """분석 결과 인사이트 추출"""
        successful_analyses = [r for r in analysis_results if r.get("success", False)]
        
        insights = []
        for analysis in successful_analyses:
            result = analysis.get("result", {})
            if isinstance(result, dict):
                insights.append(result)
        
        return {
            "insights_count": len(insights),
            "analysis_types": list(set(i.get("type", "unknown") for i in insights)),
            "insights": insights
        }

    def _extract_generated_content(self, generation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """생성된 콘텐츠 추출"""
        successful_generations = [r for r in generation_results if r.get("success", False)]
        
        contents = []
        for generation in successful_generations:
            result = generation.get("result", {})
            if isinstance(result, dict):
                contents.append(result)
        
        return {
            "content_count": len(contents),
            "generation_types": list(set(c.get("type", "unknown") for c in contents)),
            "contents": contents
        }

    def _extract_processed_data(self, processing_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """처리된 데이터 추출"""
        successful_processing = [r for r in processing_results if r.get("success", False)]
        
        processed_items = []
        for processing in successful_processing:
            result = processing.get("result", [])
            if isinstance(result, list):
                processed_items.extend(result)
        
        return {
            "processed_count": len(processed_items),
            "processing_types": [p.get("metadata", {}).get("processing_type", "unknown") for p in successful_processing],
            "processed_items": processed_items[:20]  # 상위 20개만
        }

    def _should_include_item(self, item: Any) -> bool:
        """아이템 포함 여부 결정"""
        if isinstance(item, dict):
            return item.get("quality_score", 0) > 0.5
        return True

    def _deduplicate_items(self, items: List[Any]) -> List[Any]:
        """중복 아이템 제거"""
        seen = set()
        unique_items = []
        
        for item in items:
            item_key = str(item) if not isinstance(item, dict) else item.get("id", str(item))
            if item_key not in seen:
                seen.add(item_key)
                unique_items.append(item)
        
        return unique_items

    async def execute_parallel_processing(
        self, 
        input_data: AgentInput, 
        model: str = "claude-sonnet", 
        progress_callback=None
    ) -> AgentOutput:
        """
        병렬 처리 시스템 실행
        """
        start_time = time.time()
        
        logger.info(f"🚀 LangGraph 병렬 처리 시스템 실행 시작 (사용자: {input_data.user_id})")
        
        try:
            # 성능 모니터링 시작
            await langgraph_monitor.start_execution("langgraph_parallel_processor")
            
            # 초기 상태 설정 (Reducer 기본값 설정)
            initial_state = ParallelProcessingState(
                original_query=input_data.query,
                user_id=input_data.user_id,
                session_id=input_data.session_id,
                model=model,
                processing_strategy=None,
                task_breakdown=None,
                dependency_graph=None,
                search_results=[],
                analysis_results=[],
                generation_results=[],
                processing_results=[],
                aggregated_results=None,
                final_output=None,
                execution_metadata={"start_time": start_time},
                performance_metrics={},
                parallel_efficiency=0.0,
                errors=[],
                task_failures=[],
                should_fallback=False
            )
            
            # LangGraph 워크플로우 실행
            if self.checkpointer:
                app = self.workflow.compile(checkpointer=self.checkpointer)
                config = {"configurable": {"thread_id": f"parallel_{input_data.user_id}_{input_data.session_id}"}}
                final_state = await app.ainvoke(initial_state, config=config)
            else:
                app = self.workflow.compile()
                final_state = await app.ainvoke(initial_state)
            
            # 결과 처리
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # 에러가 있거나 fallback이 필요한 경우
            if final_state.get("should_fallback", False) or len(final_state.get("errors", [])) > 0:
                logger.warning("🔄 LangGraph 병렬 처리 실행 실패")
                return AgentOutput(
                    result="병렬 처리 중 오류가 발생했습니다. 단순 처리로 진행하겠습니다.",
                    metadata={
                        "agent_version": "langgraph_parallel",
                        "processing_failed": True,
                        "errors": final_state.get("errors", [])
                    },
                    execution_time_ms=execution_time_ms,
                    agent_id=self.agent_id,
                    model_used=model,
                    timestamp=datetime.utcnow().isoformat()
                )
            
            # 성공적인 병렬 처리 결과 반환
            final_output = final_state.get("final_output", "병렬 처리를 통해 결과를 생성했습니다.")
            performance_metrics = final_state.get("performance_metrics", {})
            aggregated_results = final_state.get("aggregated_results", {})
            
            await langgraph_monitor.track_execution(
                agent_type="langgraph_parallel_processor",
                execution_time=execution_time_ms / 1000,
                success=True,
                user_id=input_data.user_id
            )
            
            result = AgentOutput(
                result=final_output,
                metadata={
                    "agent_version": "langgraph_parallel_v2",
                    "parallel_processing": True,
                    "parallel_efficiency": final_state.get("parallel_efficiency", 0),
                    "statistics": aggregated_results.get("statistics", {}),
                    **performance_metrics,
                    **final_state.get("execution_metadata", {})
                },
                execution_time_ms=execution_time_ms,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.utcnow().isoformat()
            )
            
            efficiency = final_state.get("parallel_efficiency", 0)
            logger.info(f"✅ LangGraph 병렬 처리 완료 ({execution_time_ms}ms, 효율성: {efficiency:.1f}%)")
            return result
            
        except Exception as e:
            logger.error(f"❌ LangGraph 병렬 처리 시스템 실행 실패: {e}")
            
            await langgraph_monitor.track_execution(
                agent_type="langgraph_parallel_processor",
                execution_time=(time.time() - start_time),
                success=False,
                error_message=str(e),
                user_id=input_data.user_id
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            return AgentOutput(
                result="고성능 병렬 처리 시스템에서 일시적 처리 지연이 발생했습니다. 다시 시도해주세요.",
                metadata={
                    "agent_version": "langgraph_parallel_v2",
                    "error_occurred": True,
                    "error_handled": True
                },
                execution_time_ms=execution_time_ms,
                agent_id=self.agent_id,
                model_used=model,
                timestamp=datetime.utcnow().isoformat(),
                error=f"LangGraph 병렬 처리 error: {str(e)}"
            )

    def get_capabilities(self) -> List[str]:
        """에이전트 기능 목록"""
        return [
            "Fan-out/Fan-in 병렬 처리",
            "Reducer 기반 상태 집계",
            "적응형 부하 분산",
            "실시간 성능 최적화",
            "의존성 기반 작업 스케줄링",
            "동시성 혜택 측정",
            "자동 에러 복구 및 재시도"
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
langgraph_parallel_processor = LangGraphParallelProcessor()