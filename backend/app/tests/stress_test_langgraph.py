"""
LangGraph 에이전트 종합 스트레스 테스트 및 안정성 검증 시스템
"""

import asyncio
import time
import random
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import traceback

from app.agents.base import AgentInput
from app.agents.langgraph.information_gap_langgraph import LangGraphInformationGapAnalyzer
from app.agents.langgraph.supervisor_langgraph import LangGraphSupervisorAgent
from app.agents.langgraph.multimodal_rag_langgraph import LangGraphMultimodalRAGAgent
from app.services.langgraph_monitor import langgraph_monitor
from app.services.performance_optimizer import performance_optimizer
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StressTestResult:
    """스트레스 테스트 결과"""
    agent_name: str
    test_type: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    throughput: float  # requests per second
    error_rate: float
    memory_usage_peak: float
    errors: List[str]
    test_duration: float
    timestamp: datetime


@dataclass
class TestScenario:
    """테스트 시나리오"""
    name: str
    description: str
    agent_class: Any
    test_queries: List[str]
    concurrent_users: int
    total_requests: int
    request_interval: float  # seconds
    timeout: float


class LangGraphStressTester:
    """LangGraph 에이전트 스트레스 테스터"""
    
    def __init__(self):
        self.test_results: List[StressTestResult] = []
        self.agents = self._initialize_agents()
        self.test_scenarios = self._create_test_scenarios()
        
        logger.info("LangGraph 스트레스 테스터 초기화 완료")
    
    def _initialize_agents(self) -> Dict[str, Any]:
        """테스트 대상 에이전트 초기화"""
        return {
            "information_gap": LangGraphInformationGapAnalyzer(),
            "supervisor": LangGraphSupervisorAgent(),
            "multimodal_rag": LangGraphMultimodalRAGAgent()
        }
    
    def _create_test_scenarios(self) -> List[TestScenario]:
        """테스트 시나리오 생성"""
        
        # 다양한 복잡도의 테스트 쿼리
        simple_queries = [
            "안녕하세요",
            "오늘 날씨가 어때요?",
            "파이썬이 뭔가요?",
            "AI가 무엇인가요?",
            "간단한 질문입니다"
        ]
        
        complex_queries = [
            "머신러닝과 딥러닝의 차이점을 설명하고, 각각의 장단점과 실제 응용 사례를 비교 분석해주세요.",
            "블록체인 기술의 작동 원리와 암호화폐, DeFi, NFT 등 다양한 응용 분야에서의 활용 방안을 종합적으로 분석해주세요.",
            "기후 변화가 글로벌 경제에 미치는 영향을 분석하고, 탄소 중립 달성을 위한 정책과 기술적 해결책을 제시해주세요.",
            "양자 컴퓨팅의 현재 기술 수준과 향후 발전 전망, 그리고 기존 컴퓨터와의 차이점 및 보안에 미칠 영향을 설명해주세요.",
            "인공지능의 윤리적 문제점과 편향성 해결 방안, 그리고 AI 거버넌스 체계 구축의 필요성에 대해 논의해주세요."
        ]
        
        edge_case_queries = [
            "🚀🌟💡" * 100,  # 특수문자 반복
            "A" * 1000,       # 긴 단일 문자
            "",               # 빈 문자열
            "한글과 English와 日本語를 混在시킨 multilingual query です",
            "SELECT * FROM users WHERE password = ''; DROP TABLE users; --"  # SQL Injection 시도
        ]
        
        return [
            TestScenario(
                name="light_load",
                description="가벼운 부하 테스트 - 간단한 쿼리",
                agent_class=LangGraphInformationGapAnalyzer,
                test_queries=simple_queries,
                concurrent_users=5,
                total_requests=50,
                request_interval=1.0,
                timeout=30.0
            ),
            TestScenario(
                name="moderate_load",
                description="중간 부하 테스트 - 복합 쿼리",
                agent_class=LangGraphSupervisorAgent,
                test_queries=complex_queries,
                concurrent_users=10,
                total_requests=100,
                request_interval=0.5,
                timeout=60.0
            ),
            TestScenario(
                name="heavy_load",
                description="고부하 테스트 - 대량 동시 요청",
                agent_class=LangGraphMultimodalRAGAgent,
                test_queries=simple_queries + complex_queries,
                concurrent_users=20,
                total_requests=200,
                request_interval=0.1,
                timeout=90.0
            ),
            TestScenario(
                name="edge_cases",
                description="엣지 케이스 테스트 - 예외 상황",
                agent_class=LangGraphInformationGapAnalyzer,
                test_queries=edge_case_queries,
                concurrent_users=5,
                total_requests=25,
                request_interval=2.0,
                timeout=45.0
            ),
            TestScenario(
                name="sustained_load",
                description="지속 부하 테스트 - 장시간 실행",
                agent_class=LangGraphSupervisorAgent,
                test_queries=simple_queries + complex_queries,
                concurrent_users=8,
                total_requests=500,
                request_interval=0.2,
                timeout=120.0
            )
        ]
    
    async def run_comprehensive_stress_test(self) -> Dict[str, Any]:
        """종합 스트레스 테스트 실행"""
        logger.info("🚀 LangGraph 종합 스트레스 테스트 시작")
        
        start_time = time.time()
        all_results = []
        
        # 성능 모니터링 시작
        await performance_optimizer.start_monitoring()
        
        try:
            for scenario in self.test_scenarios:
                logger.info(f"📋 시나리오 실행: {scenario.name} - {scenario.description}")
                
                result = await self._run_scenario(scenario)
                all_results.append(result)
                
                # 시나리오 간 쿨다운
                await asyncio.sleep(5)
            
            # 전체 테스트 분석
            total_duration = time.time() - start_time
            analysis = self._analyze_test_results(all_results, total_duration)
            
            logger.info(f"✅ 종합 스트레스 테스트 완료 ({total_duration:.2f}초)")
            
            return {
                "test_summary": {
                    "total_scenarios": len(self.test_scenarios),
                    "total_duration": total_duration,
                    "timestamp": datetime.now().isoformat()
                },
                "scenario_results": [asdict(result) for result in all_results],
                "analysis": analysis,
                "system_performance": await self._get_system_performance_summary()
            }
            
        except Exception as e:
            logger.error(f"스트레스 테스트 실행 실패: {e}")
            return {
                "error": str(e),
                "partial_results": [asdict(result) for result in all_results]
            }
        
        finally:
            await performance_optimizer.stop_monitoring()
    
    async def _run_scenario(self, scenario: TestScenario) -> StressTestResult:
        """개별 시나리오 실행"""
        start_time = time.time()
        
        # 에이전트 인스턴스 생성
        agent = scenario.agent_class()
        
        # 결과 수집용 리스트
        response_times = []
        errors = []
        successful_requests = 0
        failed_requests = 0
        
        # 동시 요청 실행
        semaphore = asyncio.Semaphore(scenario.concurrent_users)
        
        async def execute_request(query: str, request_id: int):
            async with semaphore:
                try:
                    request_start = time.time()
                    
                    # 테스트 입력 생성
                    test_input = AgentInput(
                        query=query,
                        user_id=f"stress_test_user_{request_id}",
                        session_id=f"stress_test_session_{request_id}",
                        context={"test_mode": True, "stress_test": True}
                    )
                    
                    # 에이전트 실행 (타임아웃 적용)
                    result = await asyncio.wait_for(
                        agent.execute(test_input),
                        timeout=scenario.timeout
                    )
                    
                    request_time = time.time() - request_start
                    response_times.append(request_time)
                    
                    return True, request_time, None
                    
                except asyncio.TimeoutError:
                    error_msg = f"Timeout after {scenario.timeout}s"
                    errors.append(error_msg)
                    return False, scenario.timeout, error_msg
                    
                except Exception as e:
                    error_msg = f"Request {request_id}: {str(e)}"
                    errors.append(error_msg)
                    return False, time.time() - request_start, error_msg
        
        # 모든 요청 실행
        tasks = []
        for i in range(scenario.total_requests):
            query = random.choice(scenario.test_queries)
            task = execute_request(query, i)
            tasks.append(task)
            
            # 요청 간격 조절
            if scenario.request_interval > 0:
                await asyncio.sleep(scenario.request_interval)
        
        # 모든 요청 완료 대기
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 집계
        for result in results:
            if isinstance(result, Exception):
                failed_requests += 1
                errors.append(str(result))
            else:
                success, response_time, error = result
                if success:
                    successful_requests += 1
                else:
                    failed_requests += 1
                    if error:
                        errors.append(error)
        
        test_duration = time.time() - start_time
        
        # 통계 계산
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = min_response_time = max_response_time = 0
        
        throughput = successful_requests / test_duration if test_duration > 0 else 0
        error_rate = failed_requests / scenario.total_requests if scenario.total_requests > 0 else 0
        
        return StressTestResult(
            agent_name=agent.__class__.__name__,
            test_type=scenario.name,
            total_requests=scenario.total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            throughput=throughput,
            error_rate=error_rate,
            memory_usage_peak=0,  # TODO: 실제 메모리 사용량 측정
            errors=errors[:10],  # 상위 10개 에러만 저장
            test_duration=test_duration,
            timestamp=datetime.now()
        )
    
    def _analyze_test_results(self, results: List[StressTestResult], total_duration: float) -> Dict[str, Any]:
        """테스트 결과 종합 분석"""
        
        if not results:
            return {"error": "분석할 결과가 없습니다"}
        
        # 전체 통계
        total_requests = sum(r.total_requests for r in results)
        total_successful = sum(r.successful_requests for r in results)
        total_failed = sum(r.failed_requests for r in results)
        
        overall_success_rate = total_successful / total_requests * 100 if total_requests > 0 else 0
        overall_error_rate = total_failed / total_requests * 100 if total_requests > 0 else 0
        
        # 성능 메트릭
        avg_response_times = [r.avg_response_time for r in results if r.avg_response_time > 0]
        overall_avg_response_time = statistics.mean(avg_response_times) if avg_response_times else 0
        
        throughputs = [r.throughput for r in results if r.throughput > 0]
        overall_throughput = statistics.mean(throughputs) if throughputs else 0
        
        # 시나리오별 성능 순위
        scenario_rankings = sorted(results, key=lambda x: (x.error_rate, x.avg_response_time))
        
        # 문제 시나리오 식별
        problematic_scenarios = [
            r for r in results 
            if r.error_rate > 0.1 or r.avg_response_time > 30
        ]
        
        # 성능 등급 결정
        if overall_error_rate < 1 and overall_avg_response_time < 5:
            performance_grade = "excellent"
        elif overall_error_rate < 5 and overall_avg_response_time < 10:
            performance_grade = "good"
        elif overall_error_rate < 10 and overall_avg_response_time < 20:
            performance_grade = "moderate"
        elif overall_error_rate < 20 and overall_avg_response_time < 30:
            performance_grade = "poor"
        else:
            performance_grade = "critical"
        
        # 권장사항 생성
        recommendations = self._generate_performance_recommendations(results, performance_grade)
        
        return {
            "overall_statistics": {
                "total_requests": total_requests,
                "successful_requests": total_successful,
                "failed_requests": total_failed,
                "success_rate": round(overall_success_rate, 2),
                "error_rate": round(overall_error_rate, 2),
                "avg_response_time": round(overall_avg_response_time, 3),
                "throughput": round(overall_throughput, 2),
                "test_duration": round(total_duration, 2)
            },
            "performance_grade": performance_grade,
            "best_performing_scenario": asdict(scenario_rankings[0]) if scenario_rankings else None,
            "worst_performing_scenario": asdict(scenario_rankings[-1]) if scenario_rankings else None,
            "problematic_scenarios": [asdict(s) for s in problematic_scenarios],
            "recommendations": recommendations,
            "detailed_analysis": {
                "response_time_distribution": {
                    "min": min([r.min_response_time for r in results]) if results else 0,
                    "max": max([r.max_response_time for r in results]) if results else 0,
                    "avg": overall_avg_response_time,
                    "median": statistics.median(avg_response_times) if avg_response_times else 0
                },
                "error_patterns": self._analyze_error_patterns(results),
                "throughput_analysis": {
                    "peak_throughput": max(throughputs) if throughputs else 0,
                    "avg_throughput": overall_throughput,
                    "min_throughput": min(throughputs) if throughputs else 0
                }
            }
        }
    
    def _analyze_error_patterns(self, results: List[StressTestResult]) -> Dict[str, Any]:
        """에러 패턴 분석"""
        all_errors = []
        for result in results:
            all_errors.extend(result.errors)
        
        if not all_errors:
            return {"message": "에러가 발생하지 않았습니다"}
        
        # 에러 유형별 집계
        error_types = {}
        for error in all_errors:
            error_type = error.split(':')[0] if ':' in error else error
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # 가장 빈번한 에러 식별
        most_common_error = max(error_types.items(), key=lambda x: x[1])
        
        return {
            "total_unique_errors": len(error_types),
            "most_common_error": {
                "type": most_common_error[0],
                "count": most_common_error[1]
            },
            "error_frequency": error_types,
            "sample_errors": all_errors[:5]  # 샘플 에러 5개
        }
    
    def _generate_performance_recommendations(self, results: List[StressTestResult], grade: str) -> List[str]:
        """성능 기반 권장사항 생성"""
        recommendations = []
        
        # 성능 등급 기반 권장사항
        if grade == "critical":
            recommendations.extend([
                "시스템 성능이 심각한 상태입니다. 즉시 점검이 필요합니다.",
                "에러율이 높습니다. 로그를 확인하고 근본 원인을 파악하세요.",
                "응답 시간이 과도하게 깁니다. 시스템 리소스를 확인하세요."
            ])
        elif grade == "poor":
            recommendations.extend([
                "성능 최적화가 필요합니다.",
                "동시 요청 처리 능력을 개선하세요.",
                "에러 처리 메커니즘을 강화하세요."
            ])
        elif grade == "moderate":
            recommendations.extend([
                "일부 시나리오에서 성능 개선 여지가 있습니다.",
                "응답 시간 최적화를 고려하세요."
            ])
        
        # 시나리오별 세부 권장사항
        high_error_scenarios = [r for r in results if r.error_rate > 0.05]
        if high_error_scenarios:
            recommendations.append(f"에러율이 높은 시나리오: {', '.join([s.test_type for s in high_error_scenarios])}")
        
        slow_scenarios = [r for r in results if r.avg_response_time > 10]
        if slow_scenarios:
            recommendations.append(f"응답 시간이 느린 시나리오: {', '.join([s.test_type for s in slow_scenarios])}")
        
        return recommendations
    
    async def _get_system_performance_summary(self) -> Dict[str, Any]:
        """시스템 성능 요약 조회"""
        try:
            performance_report = performance_optimizer.get_performance_report()
            monitoring_metrics = await langgraph_monitor.get_realtime_metrics()
            
            return {
                "performance_score": performance_report.get("performance_score", 0),
                "performance_level": performance_report.get("performance_level", "unknown"),
                "monitoring_summary": {
                    "total_executions": monitoring_metrics.get("summary", {}).get("total_executions", 0),
                    "langgraph_adoption_rate": monitoring_metrics.get("summary", {}).get("langgraph_adoption_rate", 0)
                },
                "optimization_status": {
                    "total_optimizations": len(performance_optimizer.optimization_history),
                    "recent_optimizations": performance_optimizer.optimization_history[-3:] if performance_optimizer.optimization_history else []
                }
            }
        except Exception as e:
            logger.error(f"시스템 성능 요약 조회 실패: {e}")
            return {"error": str(e)}
    
    async def run_single_agent_test(self, agent_name: str, test_type: str = "moderate_load") -> Dict[str, Any]:
        """단일 에이전트 테스트"""
        if agent_name not in self.agents:
            return {"error": f"Agent '{agent_name}' not found"}
        
        scenario = next((s for s in self.test_scenarios if s.name == test_type), None)
        if not scenario:
            return {"error": f"Test type '{test_type}' not found"}
        
        # 시나리오의 에이전트 클래스를 지정된 에이전트로 변경
        scenario.agent_class = self.agents[agent_name].__class__
        
        result = await self._run_scenario(scenario)
        
        return {
            "agent_name": agent_name,
            "test_result": asdict(result),
            "analysis": self._analyze_test_results([result], result.test_duration)
        }


# 전역 스트레스 테스터 인스턴스
stress_tester = LangGraphStressTester()


async def run_quick_health_check() -> Dict[str, Any]:
    """빠른 상태 점검"""
    logger.info("🏥 LangGraph 빠른 상태 점검 시작")
    
    try:
        # 각 에이전트별 간단한 테스트
        agents = {
            "information_gap": LangGraphInformationGapAnalyzer(),
            "supervisor": LangGraphSupervisorAgent(),
            "multimodal_rag": LangGraphMultimodalRAGAgent()
        }
        
        health_results = {}
        
        for agent_name, agent in agents.items():
            try:
                start_time = time.time()
                
                test_input = AgentInput(
                    query="안녕하세요, 간단한 테스트입니다.",
                    user_id="health_check_user",
                    context={"health_check": True}
                )
                
                result = await asyncio.wait_for(agent.execute(test_input), timeout=30)
                
                response_time = time.time() - start_time
                
                health_results[agent_name] = {
                    "status": "healthy",
                    "response_time": round(response_time, 3),
                    "result_length": len(str(result.result)) if result.result else 0
                }
                
            except Exception as e:
                health_results[agent_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "response_time": None
                }
        
        # 전체 건강도 평가
        healthy_agents = [name for name, status in health_results.items() if status["status"] == "healthy"]
        overall_health = "healthy" if len(healthy_agents) == len(agents) else "degraded" if healthy_agents else "critical"
        
        return {
            "overall_health": overall_health,
            "healthy_agents": len(healthy_agents),
            "total_agents": len(agents),
            "agent_results": health_results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"빠른 상태 점검 실패: {e}")
        return {
            "overall_health": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }