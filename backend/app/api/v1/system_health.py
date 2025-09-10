"""
시스템 건강도 및 스트레스 테스트 API 엔드포인트
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
import logging

from app.api.deps import get_current_active_user
from app.tests.stress_test_langgraph import stress_tester, run_quick_health_check

logger = logging.getLogger(__name__)
router = APIRouter()


class StressTestRequest(BaseModel):
    """스트레스 테스트 요청 모델"""
    test_type: Optional[str] = "comprehensive"  # comprehensive, single_agent, quick
    agent_name: Optional[str] = None
    scenario_name: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """상태 점검 응답 모델"""
    overall_health: str
    healthy_agents: int
    total_agents: int
    agent_results: Dict[str, Any]
    timestamp: str


@router.get("/health-check", response_model=HealthCheckResponse)
async def quick_health_check(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> HealthCheckResponse:
    """
    빠른 시스템 상태 점검
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        시스템 건강도 정보
    """
    try:
        health_result = await run_quick_health_check()
        return HealthCheckResponse(**health_result)
        
    except Exception as e:
        logger.error(f"빠른 상태 점검 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시스템 상태 점검 중 오류가 발생했습니다."
        )


@router.post("/stress-test")
async def run_stress_test(
    request: StressTestRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    스트레스 테스트 실행
    
    Args:
        request: 스트레스 테스트 요청 데이터
        background_tasks: 백그라운드 작업 큐
        current_user: 현재 사용자 정보
        
    Returns:
        스트레스 테스트 결과 또는 시작 확인
    """
    try:
        if request.test_type == "quick":
            # 빠른 테스트는 즉시 실행
            result = await run_quick_health_check()
            return {
                "test_type": "quick",
                "status": "completed",
                "result": result
            }
        
        elif request.test_type == "single_agent" and request.agent_name:
            # 단일 에이전트 테스트
            scenario_name = request.scenario_name or "moderate_load"
            result = await stress_tester.run_single_agent_test(request.agent_name, scenario_name)
            return {
                "test_type": "single_agent",
                "agent_name": request.agent_name,
                "scenario": scenario_name,
                "status": "completed",
                "result": result
            }
        
        elif request.test_type == "comprehensive":
            # 종합 스트레스 테스트는 백그라운드에서 실행
            background_tasks.add_task(_run_comprehensive_stress_test, current_user["id"])
            return {
                "test_type": "comprehensive",
                "status": "started",
                "message": "종합 스트레스 테스트가 백그라운드에서 실행 중입니다. 결과는 로그에서 확인하실 수 있습니다."
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 테스트 요청입니다."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"스트레스 테스트 실행 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="스트레스 테스트 실행 중 오류가 발생했습니다."
        )


@router.get("/system-status")
async def get_system_status(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    전체 시스템 상태 조회
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        시스템 상태 정보
    """
    try:
        # 빠른 상태 점검
        health_check = await run_quick_health_check()
        
        # 성능 정보 (이전 구현한 성능 API 활용)
        from app.services.langgraph_monitor import langgraph_monitor
        from app.services.performance_optimizer import performance_optimizer
        
        monitoring_report = await langgraph_monitor.get_comprehensive_report()
        performance_report = performance_optimizer.get_performance_report()
        
        return {
            "health_check": health_check,
            "performance": {
                "score": performance_report.get("performance_score", 0),
                "level": performance_report.get("performance_level", "unknown"),
                "monitoring_summary": monitoring_report.get("monitoring", {}).get("summary", {})
            },
            "system_health": monitoring_report.get("system_health", {}),
            "recommendations": monitoring_report.get("recommendations", [])
        }
        
    except Exception as e:
        logger.error(f"시스템 상태 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시스템 상태 조회 중 오류가 발생했습니다."
        )


@router.get("/test-scenarios")
async def get_available_test_scenarios(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    사용 가능한 테스트 시나리오 목록 조회
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        테스트 시나리오 목록
    """
    try:
        scenarios = []
        for scenario in stress_tester.test_scenarios:
            scenarios.append({
                "name": scenario.name,
                "description": scenario.description,
                "concurrent_users": scenario.concurrent_users,
                "total_requests": scenario.total_requests,
                "estimated_duration": scenario.total_requests * scenario.request_interval,
                "timeout": scenario.timeout
            })
        
        return {
            "available_scenarios": scenarios,
            "total_scenarios": len(scenarios),
            "available_agents": list(stress_tester.agents.keys())
        }
        
    except Exception as e:
        logger.error(f"테스트 시나리오 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="테스트 시나리오 조회 중 오류가 발생했습니다."
        )


@router.get("/performance-benchmark")
async def get_performance_benchmark(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    성능 벤치마크 기준 조회
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        성능 벤치마크 기준
    """
    return {
        "benchmarks": {
            "response_time": {
                "excellent": "< 2초",
                "good": "2-5초",
                "moderate": "5-10초",
                "poor": "10-20초",
                "critical": "> 20초"
            },
            "error_rate": {
                "excellent": "< 1%",
                "good": "1-3%",
                "moderate": "3-5%",
                "poor": "5-10%",
                "critical": "> 10%"
            },
            "throughput": {
                "excellent": "> 10 req/s",
                "good": "5-10 req/s",
                "moderate": "2-5 req/s",
                "poor": "1-2 req/s",
                "critical": "< 1 req/s"
            },
            "system_health": {
                "excellent": "90-100점",
                "good": "70-89점",
                "moderate": "50-69점",
                "poor": "30-49점",
                "critical": "< 30점"
            }
        },
        "recommended_thresholds": {
            "max_response_time": 10.0,
            "max_error_rate": 0.05,
            "min_throughput": 2.0,
            "min_health_score": 70
        },
        "test_guidelines": {
            "light_load": "일일 운영 부하 시뮬레이션",
            "moderate_load": "피크 시간 부하 시뮬레이션",
            "heavy_load": "최대 용량 테스트",
            "edge_cases": "예외 상황 안정성 테스트",
            "sustained_load": "장기간 안정성 테스트"
        }
    }


@router.post("/validate-system")
async def validate_entire_system(
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    전체 시스템 검증 실행
    
    Args:
        background_tasks: 백그라운드 작업 큐
        current_user: 현재 사용자 정보
        
    Returns:
        검증 시작 확인
    """
    try:
        # 종합 시스템 검증을 백그라운드에서 실행
        background_tasks.add_task(_run_complete_system_validation, current_user["id"])
        
        return {
            "validation_type": "complete_system",
            "status": "started",
            "estimated_duration": "10-15분",
            "message": "전체 시스템 검증이 시작되었습니다. 검증 중에는 시스템 성능에 영향을 줄 수 있습니다.",
            "includes": [
                "빠른 상태 점검",
                "종합 스트레스 테스트",
                "성능 최적화 분석",
                "에러 처리 검증",
                "모든 LangGraph 에이전트 테스트"
            ]
        }
        
    except Exception as e:
        logger.error(f"시스템 검증 시작 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시스템 검증 시작 중 오류가 발생했습니다."
        )


# 백그라운드 작업 함수들
async def _run_comprehensive_stress_test(user_id: str):
    """백그라운드에서 종합 스트레스 테스트 실행"""
    try:
        logger.info(f"종합 스트레스 테스트 시작 (사용자: {user_id})")
        
        result = await stress_tester.run_comprehensive_stress_test()
        
        # 결과 로깅
        if "error" in result:
            logger.error(f"종합 스트레스 테스트 실패: {result['error']}")
        else:
            analysis = result.get("analysis", {})
            overall_stats = analysis.get("overall_statistics", {})
            performance_grade = analysis.get("performance_grade", "unknown")
            
            logger.info(f"종합 스트레스 테스트 완료 - 성능 등급: {performance_grade}")
            logger.info(f"전체 요청: {overall_stats.get('total_requests', 0)}, "
                       f"성공률: {overall_stats.get('success_rate', 0)}%, "
                       f"평균 응답시간: {overall_stats.get('avg_response_time', 0)}초")
            
            # 권장사항 로깅
            recommendations = analysis.get("recommendations", [])
            if recommendations:
                logger.info(f"권장사항: {'; '.join(recommendations)}")
        
    except Exception as e:
        logger.error(f"종합 스트레스 테스트 백그라운드 실행 실패: {e}")


async def _run_complete_system_validation(user_id: str):
    """백그라운드에서 완전한 시스템 검증 실행"""
    try:
        logger.info(f"완전한 시스템 검증 시작 (사용자: {user_id})")
        
        validation_results = {}
        
        # 1. 빠른 상태 점검
        logger.info("1/4: 빠른 상태 점검 실행 중...")
        health_check = await run_quick_health_check()
        validation_results["health_check"] = health_check
        
        # 2. 성능 분석
        logger.info("2/4: 성능 분석 실행 중...")
        from app.services.performance_optimizer import performance_optimizer
        performance_report = performance_optimizer.get_performance_report()
        validation_results["performance"] = performance_report
        
        # 3. 각 에이전트별 개별 테스트
        logger.info("3/4: 에이전트별 개별 테스트 실행 중...")
        agent_tests = {}
        for agent_name in stress_tester.agents.keys():
            try:
                agent_result = await stress_tester.run_single_agent_test(agent_name, "light_load")
                agent_tests[agent_name] = agent_result
            except Exception as e:
                agent_tests[agent_name] = {"error": str(e)}
        validation_results["agent_tests"] = agent_tests
        
        # 4. 종합 스트레스 테스트
        logger.info("4/4: 종합 스트레스 테스트 실행 중...")
        stress_test_result = await stress_tester.run_comprehensive_stress_test()
        validation_results["stress_test"] = stress_test_result
        
        # 전체 검증 결과 분석
        overall_health = _analyze_complete_validation(validation_results)
        
        logger.info(f"완전한 시스템 검증 완료 - 전체 상태: {overall_health['overall_status']}")
        logger.info(f"검증 요약: {overall_health['summary']}")
        
        if overall_health["critical_issues"]:
            logger.warning(f"중요 문제 발견: {'; '.join(overall_health['critical_issues'])}")
        
        if overall_health["recommendations"]:
            logger.info(f"권장사항: {'; '.join(overall_health['recommendations'])}")
        
    except Exception as e:
        logger.error(f"완전한 시스템 검증 백그라운드 실행 실패: {e}")


def _analyze_complete_validation(results: Dict[str, Any]) -> Dict[str, Any]:
    """완전한 시스템 검증 결과 분석"""
    
    critical_issues = []
    warnings = []
    recommendations = []
    
    # 상태 점검 분석
    health_check = results.get("health_check", {})
    if health_check.get("overall_health") == "critical":
        critical_issues.append("시스템 상태가 위험합니다")
    elif health_check.get("overall_health") == "degraded":
        warnings.append("일부 에이전트가 정상 작동하지 않습니다")
    
    # 성능 분석
    performance = results.get("performance", {})
    performance_level = performance.get("performance_level", "unknown")
    if performance_level == "critical":
        critical_issues.append("시스템 성능이 심각한 수준입니다")
    elif performance_level == "poor":
        warnings.append("시스템 성능이 저하되었습니다")
    
    # 에이전트 테스트 분석
    agent_tests = results.get("agent_tests", {})
    failed_agents = [name for name, result in agent_tests.items() if "error" in result]
    if failed_agents:
        critical_issues.append(f"실패한 에이전트: {', '.join(failed_agents)}")
    
    # 스트레스 테스트 분석
    stress_test = results.get("stress_test", {})
    if "error" in stress_test:
        critical_issues.append("스트레스 테스트 실행 실패")
    else:
        analysis = stress_test.get("analysis", {})
        if analysis.get("performance_grade") in ["critical", "poor"]:
            warnings.append("스트레스 테스트에서 성능 문제 감지")
    
    # 전체 상태 결정
    if critical_issues:
        overall_status = "critical"
        recommendations.append("즉시 시스템 점검 및 수정이 필요합니다")
    elif warnings:
        overall_status = "warning"
        recommendations.append("시스템 최적화 및 모니터링 강화를 권장합니다")
    else:
        overall_status = "healthy"
        recommendations.append("시스템이 정상적으로 작동하고 있습니다")
    
    return {
        "overall_status": overall_status,
        "critical_issues": critical_issues,
        "warnings": warnings,
        "recommendations": recommendations,
        "summary": f"상태점검: {health_check.get('overall_health', 'unknown')}, "
                  f"성능: {performance_level}, "
                  f"에이전트: {len(agent_tests) - len(failed_agents)}/{len(agent_tests)} 정상"
    }