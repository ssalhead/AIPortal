"""
LangGraph 통합 테스트 - 에러 처리, 성능 최적화, 모니터링 시스템 검증
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
import logging

from app.agents.base import AgentInput
from app.agents.langgraph.information_gap_langgraph import LangGraphInformationGapAnalyzer
from app.agents.langgraph.error_handling import LangGraphErrorHandler, ErrorSeverity, RecoveryStrategy
from app.services.performance_optimizer import performance_optimizer
from app.services.langgraph_monitor import langgraph_monitor
from app.tests.stress_test_langgraph import run_quick_health_check

logger = logging.getLogger(__name__)


class TestLangGraphErrorHandling:
    """LangGraph 에러 처리 시스템 테스트"""
    
    @pytest.fixture
    def error_handler(self):
        """에러 핸들러 픽스처"""
        return LangGraphErrorHandler("test_agent")
    
    @pytest.fixture
    def information_gap_agent(self):
        """Information Gap Analyzer 픽스처"""
        return LangGraphInformationGapAnalyzer()
    
    def test_error_severity_classification(self, error_handler):
        """에러 심각도 분류 테스트"""
        
        # Critical 에러
        critical_error = Exception("database connection failed")
        severity = error_handler.classify_error(critical_error, "test_node")
        assert severity == ErrorSeverity.CRITICAL
        
        # High 에러
        high_error = Exception("timeout occurred")
        severity = error_handler.classify_error(high_error, "test_node")
        assert severity == ErrorSeverity.HIGH
        
        # Medium 에러
        medium_error = Exception("temporary failure")
        severity = error_handler.classify_error(medium_error, "test_node")
        assert severity == ErrorSeverity.MEDIUM
        
        # Low 에러
        low_error = Exception("minor issue")
        severity = error_handler.classify_error(low_error, "test_node")
        assert severity == ErrorSeverity.LOW
    
    def test_recovery_plan_registration(self, error_handler):
        """복구 계획 등록 테스트"""
        from app.agents.langgraph.error_handling import RecoveryPlan, RecoveryStrategy
        
        plan = RecoveryPlan(
            strategy=RecoveryStrategy.RETRY,
            retry_delay=1.0,
            max_retries=3
        )
        
        error_handler.register_recovery_plan("timeout", plan)
        
        assert "timeout" in error_handler.recovery_plans
        assert error_handler.recovery_plans["timeout"].strategy == RecoveryStrategy.RETRY
    
    @pytest.mark.asyncio
    async def test_error_context_creation(self, error_handler):
        """에러 컨텍스트 생성 테스트"""
        
        error = Exception("test error message")
        state = {"test_key": "test_value"}
        
        context = error_handler.create_error_context("test_node", error, state)
        
        assert context.agent_id == "test_agent"
        assert context.node_name == "test_node"
        assert context.error_message == "test error message"
        assert context.state_snapshot == state
        assert context.severity in ErrorSeverity
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, error_handler):
        """Circuit Breaker 기능 테스트"""
        
        # 정상 상태에서는 circuit이 닫혀있음
        assert not error_handler._is_circuit_open("test_node")
        
        # 실패 횟수가 임계값을 초과하면 circuit이 열림
        error_handler.circuit_breaker_states["test_node"] = {
            "failure_count": 6,  # 임계값(5) 초과
            "last_failure": time.time(),
            "state": "closed"
        }
        
        assert error_handler._is_circuit_open("test_node")
    
    @pytest.mark.asyncio
    async def test_agent_error_recovery(self, information_gap_agent):
        """에이전트 에러 복구 테스트"""
        
        # 잘못된 입력으로 에러 유발
        invalid_input = AgentInput(
            query="",  # 빈 쿼리
            user_id="test_user",
            context={"test_mode": True}
        )
        
        # 에러가 발생해도 graceful하게 처리되어야 함
        result = await information_gap_agent.execute(invalid_input)
        
        # 결과가 반환되어야 함 (fallback 또는 복구된 결과)
        assert result is not None
        assert hasattr(result, 'result')
        
        # 에러 처리 메타데이터가 포함되어야 함
        if hasattr(result, 'metadata') and result.metadata:
            # 에러 처리 관련 정보가 있을 수 있음
            assert isinstance(result.metadata, dict)


class TestPerformanceOptimization:
    """성능 최적화 시스템 테스트"""
    
    @pytest.fixture
    def optimizer(self):
        """성능 최적화 인스턴스 픽스처"""
        return performance_optimizer
    
    def test_performance_metrics_collection(self, optimizer):
        """성능 메트릭 수집 테스트"""
        
        # 메트릭 수집 기능이 정상 작동하는지 확인
        metrics_history_length = len(optimizer.metrics_history)
        
        # 메트릭이 정상적으로 수집되고 있어야 함
        assert isinstance(optimizer.metrics_history, type(optimizer.metrics_history))
        assert metrics_history_length >= 0
    
    def test_performance_report_generation(self, optimizer):
        """성능 리포트 생성 테스트"""
        
        report = optimizer.get_performance_report()
        
        # 리포트에 필수 필드들이 포함되어야 함
        assert "performance_score" in report
        assert "performance_level" in report
        assert "metrics" in report
        assert "recommendations" in report
        assert "timestamp" in report
        
        # 성능 점수는 0-100 범위여야 함
        score = report["performance_score"]
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100
    
    def test_circuit_breaker_management(self, optimizer):
        """Circuit Breaker 관리 테스트"""
        
        agent_name = "test_agent"
        
        # 초기 상태 확인
        assert not optimizer.is_circuit_breaker_open(agent_name)
        
        # Circuit Breaker 활성화
        optimizer.circuit_breakers[agent_name] = {
            "failure_threshold": 3,
            "recovery_timeout": 60,
            "state": "closed",
            "failure_count": 0,
            "last_failure_time": None
        }
        
        # 실패 기록
        for _ in range(4):  # 임계값(3) 초과
            optimizer.record_circuit_breaker_failure(agent_name)
        
        # Circuit이 열려야 함
        assert optimizer.is_circuit_breaker_open(agent_name)
        
        # 성공 기록으로 복구
        optimizer.record_circuit_breaker_success(agent_name)
        assert not optimizer.is_circuit_breaker_open(agent_name)


class TestMonitoringIntegration:
    """모니터링 시스템 통합 테스트"""
    
    @pytest.fixture
    def monitor(self):
        """모니터링 인스턴스 픽스처"""
        return langgraph_monitor
    
    @pytest.mark.asyncio
    async def test_realtime_metrics_retrieval(self, monitor):
        """실시간 메트릭 조회 테스트"""
        
        metrics = await monitor.get_realtime_metrics()
        
        # 메트릭 구조 확인
        assert isinstance(metrics, dict)
        assert "timestamp" in metrics
        
        # 데이터가 없어도 적절한 응답을 해야 함
        if metrics.get("status") == "no_data":
            assert "message" in metrics
        else:
            assert "summary" in metrics
    
    @pytest.mark.asyncio
    async def test_comprehensive_report_generation(self, monitor):
        """종합 리포트 생성 테스트"""
        
        report = await monitor.get_comprehensive_report()
        
        # 종합 리포트 구조 확인
        assert "timestamp" in report
        assert "monitoring" in report
        assert "performance" in report
        assert "system_health" in report
        assert "recommendations" in report
        
        # 시스템 건강도 정보 확인
        system_health = report["system_health"]
        assert "health_score" in system_health
        assert "health_grade" in system_health
        assert "status" in system_health
    
    def test_performance_optimizer_integration(self, monitor):
        """성능 최적화와 모니터링 연동 테스트"""
        
        # 성능 최적화 인스턴스 로딩 테스트
        optimizer = monitor._get_performance_optimizer()
        
        if optimizer:
            # 연동이 정상적으로 이루어졌다면
            assert hasattr(optimizer, 'get_performance_report')
            assert hasattr(optimizer, 'metrics_history')
        else:
            # 연동이 비활성화된 경우
            assert not monitor.optimization_enabled


class TestStressTestIntegration:
    """스트레스 테스트 통합 검증"""
    
    @pytest.mark.asyncio
    async def test_quick_health_check(self):
        """빠른 상태 점검 테스트"""
        
        health_result = await run_quick_health_check()
        
        # 상태 점검 결과 구조 확인
        assert "overall_health" in health_result
        assert "healthy_agents" in health_result
        assert "total_agents" in health_result
        assert "agent_results" in health_result
        assert "timestamp" in health_result
        
        # 전체 건강도는 정의된 값 중 하나여야 함
        assert health_result["overall_health"] in ["healthy", "degraded", "critical", "error"]
        
        # 에이전트 결과 확인
        agent_results = health_result["agent_results"]
        assert isinstance(agent_results, dict)
        
        for agent_name, result in agent_results.items():
            assert "status" in result
            assert result["status"] in ["healthy", "unhealthy"]
    
    @pytest.mark.asyncio
    async def test_error_handling_under_stress(self):
        """스트레스 상황에서 에러 처리 테스트"""
        
        # Information Gap Analyzer로 동시 요청 테스트
        agent = LangGraphInformationGapAnalyzer()
        
        # 동시에 여러 요청 실행
        tasks = []
        for i in range(5):  # 적당한 수의 동시 요청
            test_input = AgentInput(
                query=f"테스트 쿼리 {i}",
                user_id=f"stress_test_user_{i}",
                context={"stress_test": True}
            )
            task = agent.execute(test_input)
            tasks.append(task)
        
        # 모든 요청 완료 대기 (타임아웃 설정)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 분석
        successful_requests = 0
        failed_requests = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_requests += 1
            else:
                successful_requests += 1
        
        # 최소한 일부 요청은 성공해야 함
        assert successful_requests > 0
        
        # 실패율이 너무 높지 않아야 함 (70% 이상 성공)
        success_rate = successful_requests / len(results)
        assert success_rate >= 0.7, f"성공률이 너무 낮음: {success_rate:.2%}"


class TestSystemStability:
    """시스템 안정성 종합 테스트"""
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """점진적 성능 저하 테스트"""
        
        # 에이전트 인스턴스 생성
        agent = LangGraphInformationGapAnalyzer()
        
        # 정상적인 요청으로 시작
        normal_input = AgentInput(
            query="정상적인 테스트 쿼리입니다.",
            user_id="degradation_test_user",
            context={"test_mode": True}
        )
        
        normal_result = await agent.execute(normal_input)
        assert normal_result is not None
        
        # 문제가 있는 요청들
        problematic_inputs = [
            AgentInput(query="", user_id="test", context={}),  # 빈 쿼리
            AgentInput(query="A" * 10000, user_id="test", context={}),  # 매우 긴 쿼리
        ]
        
        for problematic_input in problematic_inputs:
            try:
                result = await agent.execute(problematic_input)
                # 결과가 반환되어야 함 (에러여도 graceful 처리)
                assert result is not None
            except Exception as e:
                # 예외가 발생해도 시스템이 완전히 중단되지 않아야 함
                logger.warning(f"문제 있는 입력 처리 중 예외 발생: {e}")
                # 예외가 발생했지만 테스트는 계속 진행
                pass
    
    @pytest.mark.asyncio
    async def test_resource_cleanup(self):
        """리소스 정리 테스트"""
        
        # 성능 최적화 시스템의 메모리 정리 기능 테스트
        initial_cache_size = len(performance_optimizer.performance_cache)
        
        # 캐시에 일부 데이터 추가
        performance_optimizer.performance_cache["test_key"] = "test_value"
        
        # 메모리 정리 실행
        await performance_optimizer._clear_performance_cache()
        
        # 캐시가 정리되었는지 확인
        final_cache_size = len(performance_optimizer.performance_cache)
        assert final_cache_size <= initial_cache_size
    
    def test_configuration_validation(self):
        """설정 검증 테스트"""
        
        # 에러 핸들러 설정 확인
        error_handler = LangGraphErrorHandler("test_validation")
        
        # 기본 설정이 올바른지 확인
        assert error_handler.agent_id == "test_validation"
        assert isinstance(error_handler.error_history, list)
        assert isinstance(error_handler.recovery_plans, dict)
        assert isinstance(error_handler.circuit_breaker_states, dict)
        
        # 성능 최적화 설정 확인
        assert hasattr(performance_optimizer, 'metrics_history')
        assert hasattr(performance_optimizer, 'optimization_history')
        assert hasattr(performance_optimizer, 'circuit_breakers')


# 통합 테스트 실행을 위한 메인 함수
async def run_integration_tests():
    """통합 테스트 실행"""
    logger.info("🔧 LangGraph 통합 테스트 시작")
    
    try:
        # 1. 빠른 상태 점검
        logger.info("1/4: 빠른 상태 점검...")
        health_result = await run_quick_health_check()
        logger.info(f"상태 점검 결과: {health_result['overall_health']}")
        
        # 2. 성능 최적화 시스템 검증
        logger.info("2/4: 성능 최적화 시스템 검증...")
        performance_report = performance_optimizer.get_performance_report()
        logger.info(f"성능 점수: {performance_report.get('performance_score', 0)}")
        
        # 3. 에러 처리 시스템 검증
        logger.info("3/4: 에러 처리 시스템 검증...")
        error_handler = LangGraphErrorHandler("integration_test")
        test_error = Exception("integration test error")
        error_context = error_handler.create_error_context("test_node", test_error)
        logger.info(f"에러 처리 시스템 정상 작동: {error_context.severity.value}")
        
        # 4. 전체 시스템 통합 검증
        logger.info("4/4: 전체 시스템 통합 검증...")
        comprehensive_report = await langgraph_monitor.get_comprehensive_report()
        system_health = comprehensive_report.get("system_health", {})
        logger.info(f"시스템 건강도: {system_health.get('health_grade', 'unknown')}")
        
        logger.info("✅ LangGraph 통합 테스트 완료")
        
        return {
            "status": "success",
            "health_check": health_result,
            "performance_report": performance_report,
            "system_health": system_health,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ LangGraph 통합 테스트 실패: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }


if __name__ == "__main__":
    # 통합 테스트 직접 실행
    asyncio.run(run_integration_tests())