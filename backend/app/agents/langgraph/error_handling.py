"""
LangGraph 에이전트 에러 처리 및 복구 시스템
"""

import asyncio
import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from contextlib import asynccontextmanager

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """에러 심각도 분류"""
    LOW = "low"           # 경고 수준, 계속 진행 가능
    MEDIUM = "medium"     # 중간 수준, 재시도 필요
    HIGH = "high"         # 높음 수준, fallback 필요
    CRITICAL = "critical" # 임계 수준, 전체 중단 필요


class RecoveryStrategy(Enum):
    """복구 전략 타입"""
    RETRY = "retry"                    # 재시도
    FALLBACK = "fallback"             # 대체 방법 사용
    SKIP = "skip"                     # 해당 단계 건너뛰기
    ABORT = "abort"                   # 전체 중단
    GRACEFUL_DEGRADATION = "graceful" # 점진적 성능 저하


@dataclass
class ErrorContext:
    """에러 컨텍스트 정보"""
    agent_id: str
    node_name: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    timestamp: datetime
    stack_trace: Optional[str] = None
    state_snapshot: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class RecoveryPlan:
    """복구 계획"""
    strategy: RecoveryStrategy
    fallback_function: Optional[Callable] = None
    retry_delay: float = 1.0
    max_retries: int = 3
    skip_to_node: Optional[str] = None
    error_response: Optional[Dict[str, Any]] = None


class LangGraphErrorHandler:
    """LangGraph 에이전트 통합 에러 핸들러"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.error_history: List[ErrorContext] = []
        self.recovery_plans: Dict[str, RecoveryPlan] = {}
        self.circuit_breaker_states: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger(f"ErrorHandler.{agent_id}")
    
    def register_recovery_plan(self, error_pattern: str, plan: RecoveryPlan):
        """특정 에러 패턴에 대한 복구 계획 등록"""
        self.recovery_plans[error_pattern] = plan
        self.logger.debug(f"복구 계획 등록: {error_pattern} -> {plan.strategy.value}")
    
    def classify_error(self, error: Exception, node_name: str) -> ErrorSeverity:
        """에러 심각도 자동 분류"""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Critical errors - 시스템 수준 문제
        if any(keyword in error_message for keyword in [
            "database connection", "memory", "disk space", "permission denied"
        ]):
            return ErrorSeverity.CRITICAL
        
        # High severity - 복구 필요한 중요 오류
        if any(keyword in error_message for keyword in [
            "timeout", "connection refused", "service unavailable", "rate limit"
        ]):
            return ErrorSeverity.HIGH
        
        # Medium severity - 재시도로 해결 가능
        if any(keyword in error_message for keyword in [
            "temporary", "retry", "busy", "locked"
        ]):
            return ErrorSeverity.MEDIUM
        
        # Low severity - 경고 수준
        return ErrorSeverity.LOW
    
    def create_error_context(
        self,
        node_name: str,
        error: Exception,
        state: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """에러 컨텍스트 생성"""
        severity = self.classify_error(error, node_name)
        
        return ErrorContext(
            agent_id=self.agent_id,
            node_name=node_name,
            error_type=type(error).__name__,
            error_message=str(error),
            severity=severity,
            timestamp=datetime.now(),
            stack_trace=traceback.format_exc(),
            state_snapshot=state.copy() if state else None
        )
    
    async def handle_error(
        self,
        error: Exception,
        node_name: str,
        state: Dict[str, Any],
        original_function: Callable
    ) -> Dict[str, Any]:
        """통합 에러 처리 메인 함수"""
        
        # 1. 에러 컨텍스트 생성
        error_context = self.create_error_context(node_name, error, state)
        self.error_history.append(error_context)
        
        # 2. 로깅
        self.logger.error(
            f"노드 '{node_name}'에서 에러 발생",
            error,
            {
                "severity": error_context.severity.value,
                "retry_count": error_context.retry_count,
                "agent_id": self.agent_id
            }
        )
        
        # 3. Circuit Breaker 확인
        if self._is_circuit_open(node_name):
            return await self._handle_circuit_open(state, error_context)
        
        # 4. 복구 전략 결정
        recovery_plan = self._determine_recovery_strategy(error_context)
        
        # 5. 복구 실행
        return await self._execute_recovery(
            recovery_plan, error_context, state, original_function
        )
    
    def _determine_recovery_strategy(self, error_context: ErrorContext) -> RecoveryPlan:
        """복구 전략 결정"""
        
        # 등록된 복구 계획 확인
        for pattern, plan in self.recovery_plans.items():
            if pattern.lower() in error_context.error_message.lower():
                return plan
        
        # 심각도 기반 기본 전략
        if error_context.severity == ErrorSeverity.CRITICAL:
            return RecoveryPlan(
                strategy=RecoveryStrategy.ABORT,
                error_response={
                    "error": "Critical system error occurred",
                    "agent_id": self.agent_id,
                    "node": error_context.node_name,
                    "timestamp": error_context.timestamp.isoformat()
                }
            )
        
        elif error_context.severity == ErrorSeverity.HIGH:
            return RecoveryPlan(
                strategy=RecoveryStrategy.FALLBACK,
                fallback_function=self._create_minimal_fallback(),
                max_retries=1
            )
        
        elif error_context.severity == ErrorSeverity.MEDIUM:
            return RecoveryPlan(
                strategy=RecoveryStrategy.RETRY,
                retry_delay=2.0,
                max_retries=3
            )
        
        else:  # LOW severity
            return RecoveryPlan(
                strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                fallback_function=self._create_graceful_response()
            )
    
    async def _execute_recovery(
        self,
        plan: RecoveryPlan,
        error_context: ErrorContext,
        state: Dict[str, Any],
        original_function: Callable
    ) -> Dict[str, Any]:
        """복구 계획 실행"""
        
        if plan.strategy == RecoveryStrategy.RETRY:
            return await self._execute_retry(plan, error_context, state, original_function)
        
        elif plan.strategy == RecoveryStrategy.FALLBACK:
            return await self._execute_fallback(plan, state, error_context)
        
        elif plan.strategy == RecoveryStrategy.SKIP:
            return await self._execute_skip(state, error_context)
        
        elif plan.strategy == RecoveryStrategy.ABORT:
            return await self._execute_abort(plan, state, error_context)
        
        elif plan.strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            return await self._execute_graceful_degradation(plan, state, error_context)
        
        else:
            # 기본 fallback
            return await self._execute_fallback(plan, state, error_context)
    
    async def _execute_retry(
        self,
        plan: RecoveryPlan,
        error_context: ErrorContext,
        state: Dict[str, Any],
        original_function: Callable
    ) -> Dict[str, Any]:
        """재시도 실행"""
        
        if error_context.retry_count >= plan.max_retries:
            self.logger.warning(f"최대 재시도 횟수 초과: {error_context.node_name}")
            # 재시도 실패 시 fallback으로 전환
            fallback_plan = RecoveryPlan(strategy=RecoveryStrategy.FALLBACK)
            return await self._execute_fallback(fallback_plan, state, error_context)
        
        # 재시도 지연
        await asyncio.sleep(plan.retry_delay * (error_context.retry_count + 1))
        
        try:
            self.logger.info(f"재시도 실행 ({error_context.retry_count + 1}/{plan.max_retries}): {error_context.node_name}")
            
            # 재시도 횟수 증가
            error_context.retry_count += 1
            
            # 원본 함수 재실행
            return await original_function(state)
            
        except Exception as retry_error:
            # 재시도도 실패한 경우
            return await self.handle_error(
                retry_error, error_context.node_name, state, original_function
            )
    
    async def _execute_fallback(
        self,
        plan: RecoveryPlan,
        state: Dict[str, Any],
        error_context: ErrorContext
    ) -> Dict[str, Any]:
        """Fallback 실행"""
        
        self.logger.info(f"Fallback 실행: {error_context.node_name}")
        
        if plan.fallback_function:
            try:
                return await plan.fallback_function(state, error_context)
            except Exception as fallback_error:
                self.logger.error(f"Fallback 함수도 실패: {fallback_error}")
        
        # 기본 fallback 응답
        state.setdefault("errors", []).append(f"Node '{error_context.node_name}' failed: {error_context.error_message}")
        state["should_fallback"] = True
        state.setdefault("fallback_responses", []).append({
            "node": error_context.node_name,
            "error": error_context.error_message,
            "timestamp": error_context.timestamp.isoformat(),
            "message": "시스템이 대체 방법으로 처리했습니다."
        })
        
        return state
    
    async def _execute_skip(
        self,
        state: Dict[str, Any],
        error_context: ErrorContext
    ) -> Dict[str, Any]:
        """노드 건너뛰기 실행"""
        
        self.logger.info(f"노드 건너뛰기: {error_context.node_name}")
        
        state.setdefault("skipped_nodes", []).append({
            "node": error_context.node_name,
            "reason": error_context.error_message,
            "timestamp": error_context.timestamp.isoformat()
        })
        
        return state
    
    async def _execute_abort(
        self,
        plan: RecoveryPlan,
        state: Dict[str, Any],
        error_context: ErrorContext
    ) -> Dict[str, Any]:
        """전체 중단 실행"""
        
        self.logger.critical(f"시스템 중단: {error_context.node_name}")
        
        state["should_abort"] = True
        state["abort_reason"] = error_context.error_message
        state["final_response"] = plan.error_response or {
            "error": "Critical system error - operation aborted",
            "details": error_context.error_message,
            "agent_id": self.agent_id,
            "timestamp": error_context.timestamp.isoformat()
        }
        
        return state
    
    async def _execute_graceful_degradation(
        self,
        plan: RecoveryPlan,
        state: Dict[str, Any],
        error_context: ErrorContext
    ) -> Dict[str, Any]:
        """점진적 성능 저하 실행"""
        
        self.logger.info(f"점진적 성능 저하 모드: {error_context.node_name}")
        
        if plan.fallback_function:
            return await plan.fallback_function(state, error_context)
        
        # 기본 점진적 성능 저하
        state.setdefault("degraded_features", []).append(error_context.node_name)
        state.setdefault("warnings", []).append(f"Feature '{error_context.node_name}' is running in degraded mode")
        
        return state
    
    def _is_circuit_open(self, node_name: str) -> bool:
        """Circuit Breaker 상태 확인"""
        
        circuit_state = self.circuit_breaker_states.get(node_name, {
            "failure_count": 0,
            "last_failure": None,
            "state": "closed"  # closed, open, half_open
        })
        
        # 실패 횟수가 임계값을 초과하면 circuit open
        if circuit_state["failure_count"] >= 5:
            circuit_state["state"] = "open"
            self.circuit_breaker_states[node_name] = circuit_state
            return True
        
        return False
    
    async def _handle_circuit_open(
        self,
        state: Dict[str, Any],
        error_context: ErrorContext
    ) -> Dict[str, Any]:
        """Circuit Open 상태 처리"""
        
        self.logger.warning(f"Circuit Breaker 열림: {error_context.node_name}")
        
        state.setdefault("circuit_breaker_triggered", []).append({
            "node": error_context.node_name,
            "timestamp": error_context.timestamp.isoformat(),
            "message": "Too many failures - circuit breaker activated"
        })
        
        # 즉시 fallback 응답 반환
        return await self._execute_fallback(
            RecoveryPlan(strategy=RecoveryStrategy.FALLBACK),
            state,
            error_context
        )
    
    def _create_minimal_fallback(self) -> Callable:
        """최소한의 fallback 함수 생성"""
        async def minimal_fallback(state: Dict[str, Any], error_context: ErrorContext):
            return {
                **state,
                "minimal_response": f"Agent {self.agent_id} encountered an error in {error_context.node_name} but continued processing",
                "processing_mode": "degraded"
            }
        return minimal_fallback
    
    def _create_graceful_response(self) -> Callable:
        """점진적 성능 저하 응답 생성"""
        async def graceful_response(state: Dict[str, Any], error_context: ErrorContext):
            return {
                **state,
                "graceful_degradation": True,
                "degraded_node": error_context.node_name,
                "alternative_processing": "기본 처리 방식으로 전환되었습니다."
            }
        return graceful_response
    
    def get_error_stats(self) -> Dict[str, Any]:
        """에러 통계 조회"""
        if not self.error_history:
            return {"total_errors": 0}
        
        severity_counts = {}
        for error in self.error_history:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_errors": len(self.error_history),
            "severity_breakdown": severity_counts,
            "most_recent_error": self.error_history[-1].timestamp.isoformat(),
            "circuit_breaker_states": self.circuit_breaker_states
        }


@asynccontextmanager
async def error_handler_context(agent_id: str, node_name: str):
    """에러 처리 컨텍스트 매니저"""
    handler = LangGraphErrorHandler(agent_id)
    try:
        yield handler
    except Exception as e:
        logger.error(f"Error handler context failed for {agent_id}.{node_name}: {e}")
        raise


def create_error_safe_node(agent_id: str, node_name: str, original_function: Callable):
    """에러 안전 노드 데코레이터"""
    
    async def error_safe_wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        handler = LangGraphErrorHandler(agent_id)
        
        try:
            return await original_function(state)
        except Exception as e:
            return await handler.handle_error(e, node_name, state, original_function)
    
    return error_safe_wrapper


# 공통 Recovery Plans
COMMON_RECOVERY_PLANS = {
    "timeout": RecoveryPlan(
        strategy=RecoveryStrategy.RETRY,
        retry_delay=2.0,
        max_retries=2
    ),
    "rate_limit": RecoveryPlan(
        strategy=RecoveryStrategy.RETRY,
        retry_delay=5.0,
        max_retries=3
    ),
    "connection": RecoveryPlan(
        strategy=RecoveryStrategy.FALLBACK,
        max_retries=1
    ),
    "memory": RecoveryPlan(
        strategy=RecoveryStrategy.ABORT
    )
}