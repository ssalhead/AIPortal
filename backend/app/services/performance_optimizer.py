"""
LangGraph 성능 최적화 및 모니터링 시스템
"""

import asyncio
import time
import psutil
import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import asynccontextmanager
from collections import defaultdict, deque
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor
import gc

from app.utils.logger import get_logger
from app.services.langgraph_monitor import monitor

logger = get_logger(__name__)


class PerformanceLevel(Enum):
    """성능 수준"""
    EXCELLENT = "excellent"    # 90-100%
    GOOD = "good"             # 70-89%
    MODERATE = "moderate"     # 50-69%
    POOR = "poor"            # 30-49%
    CRITICAL = "critical"    # 0-29%


class OptimizationStrategy(Enum):
    """최적화 전략"""
    CACHE_OPTIMIZATION = "cache_optimization"
    MEMORY_CLEANUP = "memory_cleanup"
    CONCURRENCY_TUNING = "concurrency_tuning"
    MODEL_SWITCHING = "model_switching"
    BATCHING = "batching"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class PerformanceMetrics:
    """성능 메트릭"""
    cpu_usage: float
    memory_usage: float
    memory_available: float
    response_time: float
    throughput: float
    error_rate: float
    cache_hit_rate: float
    concurrent_requests: int
    timestamp: datetime
    
    def get_performance_score(self) -> float:
        """전체 성능 점수 계산 (0-100)"""
        # CPU 점수 (낮을수록 좋음)
        cpu_score = max(0, 100 - self.cpu_usage)
        
        # 메모리 점수 (사용률 낮을수록 좋음)
        memory_score = max(0, 100 - self.memory_usage)
        
        # 응답시간 점수 (2초 이하면 만점)
        response_score = max(0, 100 - (self.response_time / 2.0) * 100)
        
        # 에러율 점수 (에러가 없으면 만점)
        error_score = max(0, 100 - (self.error_rate * 100))
        
        # 캐시 적중률 점수
        cache_score = self.cache_hit_rate * 100
        
        # 가중 평균 계산
        return (
            cpu_score * 0.2 +
            memory_score * 0.2 +
            response_score * 0.3 +
            error_score * 0.2 +
            cache_score * 0.1
        )


@dataclass
class OptimizationAction:
    """최적화 액션"""
    strategy: OptimizationStrategy
    description: str
    priority: int  # 1-10 (높을수록 우선순위)
    estimated_improvement: float  # 예상 개선도 (%)
    implementation_cost: int  # 구현 비용 (1-5)
    action_function: Optional[Callable] = None


class PerformanceOptimizer:
    """LangGraph 성능 최적화 엔진"""
    
    def __init__(self):
        self.metrics_history: deque = deque(maxlen=1000)
        self.optimization_history: List[Dict[str, Any]] = []
        self.performance_cache: Dict[str, Any] = {}
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.optimization_executor = ThreadPoolExecutor(max_workers=2)
        
        # 실시간 모니터링 시작
        self._monitoring_active = True
        self._monitoring_task = None
        
        logger.info("성능 최적화 엔진 초기화 완료")
    
    async def start_monitoring(self):
        """실시간 모니터링 시작"""
        self._monitoring_task = asyncio.create_task(self._monitor_performance())
        logger.info("실시간 성능 모니터링 시작")
    
    async def stop_monitoring(self):
        """모니터링 중지"""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
        logger.info("성능 모니터링 중지")
    
    async def _monitor_performance(self):
        """실시간 성능 모니터링 루프"""
        while self._monitoring_active:
            try:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # 성능 문제 감지 및 자동 최적화
                performance_score = metrics.get_performance_score()
                
                if performance_score < 30:  # Critical
                    logger.critical(f"치명적 성능 저하 감지: {performance_score:.1f}%")
                    await self._emergency_optimization(metrics)
                elif performance_score < 50:  # Poor
                    logger.warning(f"성능 저하 감지: {performance_score:.1f}%")
                    await self._proactive_optimization(metrics)
                
                await asyncio.sleep(10)  # 10초 간격 모니터링
                
            except Exception as e:
                logger.error(f"성능 모니터링 중 오류: {e}")
                await asyncio.sleep(30)  # 오류 시 더 긴 간격
    
    async def _collect_metrics(self) -> PerformanceMetrics:
        """현재 시스템 메트릭 수집"""
        
        # 시스템 메트릭
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # 애플리케이션 메트릭
        response_times = self._get_recent_response_times()
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        error_count = self._get_recent_error_count()
        request_count = self._get_recent_request_count()
        error_rate = error_count / max(request_count, 1)
        
        cache_stats = self._get_cache_stats()
        cache_hit_rate = cache_stats.get('hit_rate', 0)
        
        concurrent_requests = self._get_concurrent_request_count()
        
        return PerformanceMetrics(
            cpu_usage=cpu_percent,
            memory_usage=memory.percent,
            memory_available=memory.available / (1024**3),  # GB
            response_time=avg_response_time,
            throughput=request_count / 60.0,  # requests per second
            error_rate=error_rate,
            cache_hit_rate=cache_hit_rate,
            concurrent_requests=concurrent_requests,
            timestamp=datetime.now()
        )
    
    def _get_recent_response_times(self) -> List[float]:
        """최근 응답 시간 가져오기"""
        # 실제 구현에서는 메트릭 저장소에서 데이터 조회
        return [m.response_time for m in list(self.metrics_history)[-10:]]
    
    def _get_recent_error_count(self) -> int:
        """최근 에러 수 가져오기"""
        # LangGraph 모니터에서 에러 통계 조회
        return 0  # 임시값
    
    def _get_recent_request_count(self) -> int:
        """최근 요청 수 가져오기"""
        return max(1, len(self.metrics_history))
    
    def _get_cache_stats(self) -> Dict[str, float]:
        """캐시 통계 가져오기"""
        return {"hit_rate": 0.8}  # 임시값
    
    def _get_concurrent_request_count(self) -> int:
        """동시 요청 수 가져오기"""
        return 1  # 임시값
    
    async def _emergency_optimization(self, metrics: PerformanceMetrics):
        """긴급 최적화 (Critical 상태)"""
        logger.critical("긴급 최적화 모드 활성화")
        
        optimizations = [
            self._force_garbage_collection,
            self._clear_performance_cache,
            self._enable_circuit_breakers,
            self._reduce_concurrency,
            self._switch_to_lightweight_models
        ]
        
        for optimization in optimizations:
            try:
                await optimization()
                await asyncio.sleep(1)  # 최적화 간 간격
            except Exception as e:
                logger.error(f"긴급 최적화 실패: {optimization.__name__}: {e}")
    
    async def _proactive_optimization(self, metrics: PerformanceMetrics):
        """사전 예방적 최적화 (Poor 상태)"""
        logger.warning("사전 예방적 최적화 시작")
        
        # 최적화 액션 우선순위 결정
        actions = self._analyze_optimization_opportunities(metrics)
        
        # 상위 3개 액션 실행
        for action in actions[:3]:
            try:
                if action.action_function:
                    await action.action_function()
                    logger.info(f"최적화 적용: {action.description}")
                    
                    # 적용 결과 추적
                    self.optimization_history.append({
                        "strategy": action.strategy.value,
                        "description": action.description,
                        "timestamp": datetime.now().isoformat(),
                        "estimated_improvement": action.estimated_improvement
                    })
                    
            except Exception as e:
                logger.error(f"최적화 적용 실패: {action.description}: {e}")
    
    def _analyze_optimization_opportunities(self, metrics: PerformanceMetrics) -> List[OptimizationAction]:
        """최적화 기회 분석 및 우선순위 결정"""
        actions = []
        
        # CPU 사용률이 높은 경우
        if metrics.cpu_usage > 80:
            actions.append(OptimizationAction(
                strategy=OptimizationStrategy.CONCURRENCY_TUNING,
                description="동시 처리 수 제한으로 CPU 부하 감소",
                priority=8,
                estimated_improvement=20,
                implementation_cost=2,
                action_function=self._reduce_concurrency
            ))
        
        # 메모리 사용률이 높은 경우
        if metrics.memory_usage > 85:
            actions.append(OptimizationAction(
                strategy=OptimizationStrategy.MEMORY_CLEANUP,
                description="메모리 정리 및 가비지 컬렉션",
                priority=9,
                estimated_improvement=25,
                implementation_cost=1,
                action_function=self._force_garbage_collection
            ))
        
        # 응답 시간이 느린 경우
        if metrics.response_time > 3.0:
            actions.append(OptimizationAction(
                strategy=OptimizationStrategy.CACHE_OPTIMIZATION,
                description="캐싱 최적화로 응답 시간 개선",
                priority=7,
                estimated_improvement=30,
                implementation_cost=3,
                action_function=self._optimize_caching
            ))
        
        # 에러율이 높은 경우
        if metrics.error_rate > 0.1:
            actions.append(OptimizationAction(
                strategy=OptimizationStrategy.CIRCUIT_BREAKER,
                description="Circuit Breaker 활성화로 안정성 확보",
                priority=9,
                estimated_improvement=15,
                implementation_cost=2,
                action_function=self._enable_circuit_breakers
            ))
        
        # 캐시 적중률이 낮은 경우
        if metrics.cache_hit_rate < 0.5:
            actions.append(OptimizationAction(
                strategy=OptimizationStrategy.CACHE_OPTIMIZATION,
                description="캐시 전략 개선",
                priority=6,
                estimated_improvement=20,
                implementation_cost=3,
                action_function=self._improve_cache_strategy
            ))
        
        # 우선순위로 정렬
        actions.sort(key=lambda x: x.priority, reverse=True)
        return actions
    
    async def _force_garbage_collection(self):
        """강제 가비지 컬렉션"""
        logger.info("강제 가비지 컬렉션 실행")
        gc.collect()
        await asyncio.sleep(0.1)  # GC 완료 대기
    
    async def _clear_performance_cache(self):
        """성능 캐시 정리"""
        logger.info("성능 캐시 정리")
        self.performance_cache.clear()
    
    async def _enable_circuit_breakers(self):
        """Circuit Breaker 활성화"""
        logger.info("Circuit Breaker 활성화")
        
        # 주요 에이전트들에 대한 Circuit Breaker 설정
        agents = ["langgraph_information_gap", "langgraph_supervisor", "langgraph_multimodal_rag"]
        
        for agent in agents:
            self.circuit_breakers[agent] = {
                "failure_threshold": 3,
                "recovery_timeout": 60,
                "half_open_max_calls": 5,
                "state": "closed",
                "failure_count": 0,
                "last_failure_time": None
            }
    
    async def _reduce_concurrency(self):
        """동시 처리 수 감소"""
        logger.info("동시 처리 수 감소")
        # 실제 구현에서는 세마포어나 스레드풀 크기 조정
        pass
    
    async def _switch_to_lightweight_models(self):
        """가벼운 모델로 전환"""
        logger.info("가벼운 모델로 전환")
        # Claude Haiku나 Gemini Flash 등 빠른 모델 우선 사용
        pass
    
    async def _optimize_caching(self):
        """캐싱 최적화"""
        logger.info("캐싱 최적화 적용")
        # 캐시 크기 조정, TTL 최적화 등
        pass
    
    async def _improve_cache_strategy(self):
        """캐시 전략 개선"""
        logger.info("캐시 전략 개선")
        # 더 효율적인 캐시 키 생성, 프리로딩 등
        pass
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 생성"""
        if not self.metrics_history:
            return {"message": "메트릭 데이터 없음"}
        
        recent_metrics = list(self.metrics_history)[-10:]
        
        avg_performance = statistics.mean([m.get_performance_score() for m in recent_metrics])
        avg_response_time = statistics.mean([m.response_time for m in recent_metrics])
        avg_cpu = statistics.mean([m.cpu_usage for m in recent_metrics])
        avg_memory = statistics.mean([m.memory_usage for m in recent_metrics])
        
        # 성능 등급 결정
        if avg_performance >= 90:
            performance_level = PerformanceLevel.EXCELLENT
        elif avg_performance >= 70:
            performance_level = PerformanceLevel.GOOD
        elif avg_performance >= 50:
            performance_level = PerformanceLevel.MODERATE
        elif avg_performance >= 30:
            performance_level = PerformanceLevel.POOR
        else:
            performance_level = PerformanceLevel.CRITICAL
        
        return {
            "performance_score": round(avg_performance, 1),
            "performance_level": performance_level.value,
            "metrics": {
                "avg_response_time": round(avg_response_time, 3),
                "avg_cpu_usage": round(avg_cpu, 1),
                "avg_memory_usage": round(avg_memory, 1),
                "total_optimizations": len(self.optimization_history)
            },
            "recommendations": self._get_performance_recommendations(avg_performance),
            "recent_optimizations": self.optimization_history[-5:],
            "circuit_breaker_status": self.circuit_breakers,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_performance_recommendations(self, performance_score: float) -> List[str]:
        """성능 점수에 따른 권장사항"""
        recommendations = []
        
        if performance_score < 30:
            recommendations.extend([
                "즉시 시스템 점검이 필요합니다",
                "가벼운 모델(Haiku, Flash) 사용을 권장합니다",
                "동시 요청 수를 제한하세요"
            ])
        elif performance_score < 50:
            recommendations.extend([
                "메모리 사용량을 모니터링하세요",
                "캐싱 전략을 검토하세요",
                "에러 로그를 확인하세요"
            ])
        elif performance_score < 70:
            recommendations.extend([
                "정기적인 메모리 정리를 고려하세요",
                "캐시 적중률 개선 여지가 있습니다"
            ])
        else:
            recommendations.append("현재 성능이 양호합니다")
        
        return recommendations
    
    def is_circuit_breaker_open(self, agent_name: str) -> bool:
        """Circuit Breaker 상태 확인"""
        breaker = self.circuit_breakers.get(agent_name)
        if not breaker:
            return False
        
        if breaker["state"] == "open":
            # 복구 시간 확인
            if breaker["last_failure_time"]:
                elapsed = time.time() - breaker["last_failure_time"]
                if elapsed > breaker["recovery_timeout"]:
                    breaker["state"] = "half_open"
                    logger.info(f"Circuit Breaker {agent_name}: HALF_OPEN 상태로 전환")
                    return False
            return True
        
        return False
    
    def record_circuit_breaker_failure(self, agent_name: str):
        """Circuit Breaker 실패 기록"""
        breaker = self.circuit_breakers.get(agent_name)
        if not breaker:
            return
        
        breaker["failure_count"] += 1
        breaker["last_failure_time"] = time.time()
        
        if breaker["failure_count"] >= breaker["failure_threshold"]:
            breaker["state"] = "open"
            logger.warning(f"Circuit Breaker {agent_name}: OPEN 상태로 전환")
    
    def record_circuit_breaker_success(self, agent_name: str):
        """Circuit Breaker 성공 기록"""
        breaker = self.circuit_breakers.get(agent_name)
        if not breaker:
            return
        
        if breaker["state"] == "half_open":
            breaker["state"] = "closed"
            breaker["failure_count"] = 0
            logger.info(f"Circuit Breaker {agent_name}: CLOSED 상태로 복구")


# 전역 인스턴스
performance_optimizer = PerformanceOptimizer()


@asynccontextmanager
async def performance_monitoring_context(agent_name: str, operation: str):
    """성능 모니터링 컨텍스트 매니저"""
    start_time = time.time()
    
    try:
        # Circuit Breaker 확인
        if performance_optimizer.is_circuit_breaker_open(agent_name):
            raise Exception(f"Circuit Breaker OPEN: {agent_name}")
        
        yield
        
        # 성공 기록
        execution_time = time.time() - start_time
        performance_optimizer.record_circuit_breaker_success(agent_name)
        
        logger.debug(f"성능 모니터링: {agent_name}.{operation} 완료 ({execution_time:.3f}s)")
        
    except Exception as e:
        # 실패 기록
        performance_optimizer.record_circuit_breaker_failure(agent_name)
        logger.error(f"성능 모니터링: {agent_name}.{operation} 실패: {e}")
        raise


def monitor_performance(agent_name: str, operation: str = "execute"):
    """성능 모니터링 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with performance_monitoring_context(agent_name, operation):
                return await func(*args, **kwargs)
        return wrapper
    return decorator