"""
Canvas OpenTelemetry 분산 트레이싱 시스템 v1.0
실시간 협업 Canvas 시스템의 완전한 가시성과 성능 모니터링
"""

import time
import uuid
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, asdict
from enum import Enum
import json
from functools import wraps
import traceback

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ======= 트레이싱 레벨 및 타입 정의 =======

class TraceLevel(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"  
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"

class CanvasTraceType(str, Enum):
    # Canvas 작업
    CANVAS_OPERATION = "canvas_operation"
    CANVAS_RENDER = "canvas_render"
    CANVAS_FILTER = "canvas_filter"
    
    # WebSocket 통신
    WEBSOCKET_CONNECT = "websocket_connect"
    WEBSOCKET_MESSAGE = "websocket_message"
    WEBSOCKET_BROADCAST = "websocket_broadcast"
    
    # OT 시스템
    OT_TRANSFORM = "ot_transform"
    OT_INTEGRATE = "ot_integrate"
    OT_CONFLICT_RESOLVE = "ot_conflict_resolve"
    
    # 데이터베이스
    DB_QUERY = "db_query"
    DB_TRANSACTION = "db_transaction"
    
    # 캐싱 시스템
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_SET = "cache_set"
    
    # 성능 메트릭
    PERFORMANCE_MONITOR = "performance_monitor"
    MEMORY_USAGE = "memory_usage"
    
    # 사용자 상호작용
    USER_ACTION = "user_action"
    USER_SESSION = "user_session"

@dataclass
class TraceSpan:
    """분산 트레이싱 스팬"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    trace_type: CanvasTraceType
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "STARTED"  # STARTED, SUCCESS, ERROR
    tags: Dict[str, Any] = None
    logs: List[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.logs is None:
            self.logs = []
    
    def finish(self, error: Optional[str] = None):
        """스팬 종료"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = "ERROR" if error else "SUCCESS"
        self.error = error
    
    def add_tag(self, key: str, value: Any):
        """태그 추가"""
        self.tags[key] = value
    
    def log_event(self, message: str, level: TraceLevel = TraceLevel.INFO, data: Optional[Dict[str, Any]] = None):
        """이벤트 로깅"""
        log_entry = {
            "timestamp": time.time(),
            "level": level.value,
            "message": message,
            "data": data or {}
        }
        self.logs.append(log_entry)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return asdict(self)

@dataclass
class CanvasTrace:
    """Canvas 작업 트레이스 전체"""
    trace_id: str
    conversation_id: str
    user_id: Optional[str]
    root_operation: str
    start_time: float
    end_time: Optional[float] = None
    total_duration_ms: Optional[float] = None
    spans: Dict[str, TraceSpan] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.spans is None:
            self.spans = {}
        if self.metrics is None:
            self.metrics = {}
    
    def finish(self):
        """트레이스 완료"""
        self.end_time = time.time()
        self.total_duration_ms = (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        result = asdict(self)
        result['spans'] = {k: v.to_dict() for k, v in self.spans.items()}
        return result

# ======= OpenTelemetry Canvas 트레이서 =======

class CanvasTracer:
    """Canvas 전용 분산 트레이싱 시스템"""
    
    def __init__(self):
        self.active_traces: Dict[str, CanvasTrace] = {}
        self.active_spans: Dict[str, TraceSpan] = {}
        self.trace_storage: List[CanvasTrace] = []  # 완료된 트레이스 저장
        self.max_traces = 1000  # 메모리 관리
        self.metrics_collector = CanvasMetricsCollector()
        
    # ======= 트레이스 생성 및 관리 =======
    
    def start_trace(
        self, 
        operation_name: str, 
        conversation_id: str,
        user_id: Optional[str] = None,
        trace_type: CanvasTraceType = CanvasTraceType.USER_ACTION
    ) -> str:
        """새로운 트레이스 시작"""
        trace_id = f"trace_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        canvas_trace = CanvasTrace(
            trace_id=trace_id,
            conversation_id=conversation_id,
            user_id=user_id,
            root_operation=operation_name,
            start_time=time.time()
        )
        
        # 루트 스팬 생성
        root_span = self.start_span(
            operation_name=operation_name,
            trace_type=trace_type,
            trace_id=trace_id
        )
        
        root_span.add_tag("conversation_id", conversation_id)
        if user_id:
            root_span.add_tag("user_id", user_id)
        
        canvas_trace.spans[root_span.span_id] = root_span
        self.active_traces[trace_id] = canvas_trace
        
        logger.debug(f"🔍 새 트레이스 시작: {trace_id} - {operation_name}")
        return trace_id
    
    def start_span(
        self,
        operation_name: str,
        trace_type: CanvasTraceType,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ) -> TraceSpan:
        """새로운 스팬 시작"""
        span_id = f"span_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        if not trace_id and parent_span_id:
            # 부모 스팬에서 trace_id 추출
            parent_span = self.active_spans.get(parent_span_id)
            trace_id = parent_span.trace_id if parent_span else None
        
        if not trace_id:
            trace_id = f"orphan_{int(time.time())}"
        
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            trace_type=trace_type,
            start_time=time.time()
        )
        
        self.active_spans[span_id] = span
        
        # 트레이스에 스팬 추가
        if trace_id in self.active_traces:
            self.active_traces[trace_id].spans[span_id] = span
        
        return span
    
    def finish_span(self, span_id: str, error: Optional[str] = None):
        """스팬 완료"""
        if span_id not in self.active_spans:
            return
        
        span = self.active_spans[span_id]
        span.finish(error)
        
        # 메트릭 수집
        self.metrics_collector.record_span_duration(
            span.trace_type, 
            span.duration_ms or 0
        )
        
        # 활성 스팬에서 제거
        del self.active_spans[span_id]
        
        logger.debug(f"⏱️ 스팬 완료: {span.operation_name} ({span.duration_ms:.2f}ms)")
    
    def finish_trace(self, trace_id: str):
        """트레이스 완료"""
        if trace_id not in self.active_traces:
            return
        
        trace = self.active_traces[trace_id]
        trace.finish()
        
        # 메트릭 계산
        trace.metrics = self._calculate_trace_metrics(trace)
        
        # 저장소로 이동
        self.trace_storage.append(trace)
        del self.active_traces[trace_id]
        
        # 메모리 관리
        if len(self.trace_storage) > self.max_traces:
            self.trace_storage = self.trace_storage[-self.max_traces:]
        
        logger.info(f"✅ 트레이스 완료: {trace.root_operation} ({trace.total_duration_ms:.2f}ms)")
    
    # ======= 컨텍스트 매니저 =======
    
    @contextmanager
    def trace_operation(
        self, 
        operation_name: str, 
        trace_type: CanvasTraceType,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ):
        """동기 작업 트레이싱"""
        if conversation_id and not parent_span_id:
            # 새 트레이스 시작
            trace_id = self.start_trace(operation_name, conversation_id, user_id, trace_type)
            span = list(self.active_traces[trace_id].spans.values())[0]  # 루트 스팬
        else:
            # 기존 트레이스에 스팬 추가
            span = self.start_span(operation_name, trace_type, parent_span_id=parent_span_id)
        
        try:
            yield span
            self.finish_span(span.span_id)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            span.log_event(f"Error occurred: {error_msg}", TraceLevel.ERROR)
            self.finish_span(span.span_id, error_msg)
            raise
    
    @asynccontextmanager
    async def trace_async_operation(
        self,
        operation_name: str,
        trace_type: CanvasTraceType,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ):
        """비동기 작업 트레이싱"""
        if conversation_id and not parent_span_id:
            # 새 트레이스 시작
            trace_id = self.start_trace(operation_name, conversation_id, user_id, trace_type)
            span = list(self.active_traces[trace_id].spans.values())[0]  # 루트 스팬
        else:
            # 기존 트레이스에 스팬 추가
            span = self.start_span(operation_name, trace_type, parent_span_id=parent_span_id)
        
        try:
            yield span
            self.finish_span(span.span_id)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            span.log_event(f"Error occurred: {error_msg}", TraceLevel.ERROR)
            self.finish_span(span.span_id, error_msg)
            raise
    
    # ======= 메트릭 계산 =======
    
    def _calculate_trace_metrics(self, trace: CanvasTrace) -> Dict[str, Any]:
        """트레이스 메트릭 계산"""
        spans = list(trace.spans.values())
        
        if not spans:
            return {}
        
        durations = [s.duration_ms for s in spans if s.duration_ms is not None]
        
        return {
            "total_spans": len(spans),
            "successful_spans": len([s for s in spans if s.status == "SUCCESS"]),
            "error_spans": len([s for s in spans if s.status == "ERROR"]),
            "avg_span_duration": sum(durations) / len(durations) if durations else 0,
            "max_span_duration": max(durations) if durations else 0,
            "min_span_duration": min(durations) if durations else 0,
            "span_types": dict([
                (trace_type.value, len([s for s in spans if s.trace_type == trace_type]))
                for trace_type in set(s.trace_type for s in spans)
            ])
        }
    
    # ======= 조회 및 분석 =======
    
    def get_trace(self, trace_id: str) -> Optional[CanvasTrace]:
        """트레이스 조회"""
        # 활성 트레이스 확인
        if trace_id in self.active_traces:
            return self.active_traces[trace_id]
        
        # 완료된 트레이스 확인
        for trace in self.trace_storage:
            if trace.trace_id == trace_id:
                return trace
        
        return None
    
    def get_conversation_traces(self, conversation_id: str, limit: int = 50) -> List[CanvasTrace]:
        """대화별 트레이스 조회"""
        traces = []
        
        # 활성 트레이스
        for trace in self.active_traces.values():
            if trace.conversation_id == conversation_id:
                traces.append(trace)
        
        # 완료된 트레이스  
        for trace in self.trace_storage:
            if trace.conversation_id == conversation_id:
                traces.append(trace)
        
        # 최신순 정렬
        traces.sort(key=lambda t: t.start_time, reverse=True)
        return traces[:limit]
    
    def get_performance_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """성능 요약 통계"""
        cutoff_time = time.time() - (time_window_minutes * 60)
        recent_traces = [
            t for t in self.trace_storage 
            if t.start_time >= cutoff_time
        ]
        
        if not recent_traces:
            return {"message": "No recent traces"}
        
        return {
            "time_window_minutes": time_window_minutes,
            "total_traces": len(recent_traces),
            "avg_duration_ms": sum(t.total_duration_ms or 0 for t in recent_traces) / len(recent_traces),
            "error_rate": len([t for t in recent_traces if any(s.status == "ERROR" for s in t.spans.values())]) / len(recent_traces),
            "operation_breakdown": self._get_operation_breakdown(recent_traces),
            "span_type_metrics": self.metrics_collector.get_summary()
        }
    
    def _get_operation_breakdown(self, traces: List[CanvasTrace]) -> Dict[str, Any]:
        """작업별 성능 분석"""
        breakdown = {}
        
        for trace in traces:
            op_name = trace.root_operation
            if op_name not in breakdown:
                breakdown[op_name] = {
                    "count": 0,
                    "total_duration": 0,
                    "avg_duration": 0,
                    "errors": 0
                }
            
            breakdown[op_name]["count"] += 1
            breakdown[op_name]["total_duration"] += trace.total_duration_ms or 0
            breakdown[op_name]["avg_duration"] = breakdown[op_name]["total_duration"] / breakdown[op_name]["count"]
            
            if any(s.status == "ERROR" for s in trace.spans.values()):
                breakdown[op_name]["errors"] += 1
        
        return breakdown

# ======= 메트릭 컬렉터 =======

class CanvasMetricsCollector:
    """Canvas 성능 메트릭 수집기"""
    
    def __init__(self):
        self.span_durations: Dict[CanvasTraceType, List[float]] = {}
        self.span_counts: Dict[CanvasTraceType, int] = {}
        self.error_counts: Dict[CanvasTraceType, int] = {}
    
    def record_span_duration(self, trace_type: CanvasTraceType, duration_ms: float):
        """스팬 지속시간 기록"""
        if trace_type not in self.span_durations:
            self.span_durations[trace_type] = []
            self.span_counts[trace_type] = 0
            self.error_counts[trace_type] = 0
        
        self.span_durations[trace_type].append(duration_ms)
        self.span_counts[trace_type] += 1
        
        # 메모리 관리 - 최근 1000개만 유지
        if len(self.span_durations[trace_type]) > 1000:
            self.span_durations[trace_type] = self.span_durations[trace_type][-1000:]
    
    def record_error(self, trace_type: CanvasTraceType):
        """에러 기록"""
        if trace_type not in self.error_counts:
            self.error_counts[trace_type] = 0
        self.error_counts[trace_type] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """메트릭 요약"""
        summary = {}
        
        for trace_type in self.span_durations:
            durations = self.span_durations[trace_type]
            if not durations:
                continue
                
            summary[trace_type.value] = {
                "total_count": self.span_counts[trace_type],
                "error_count": self.error_counts[trace_type],
                "error_rate": self.error_counts[trace_type] / self.span_counts[trace_type] if self.span_counts[trace_type] > 0 else 0,
                "avg_duration_ms": sum(durations) / len(durations),
                "p95_duration_ms": self._percentile(durations, 0.95),
                "p99_duration_ms": self._percentile(durations, 0.99),
                "max_duration_ms": max(durations),
                "min_duration_ms": min(durations)
            }
        
        return summary
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """백분위수 계산"""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]

# ======= 데코레이터 =======

def trace_canvas_operation(
    operation_name: Optional[str] = None,
    trace_type: CanvasTraceType = CanvasTraceType.CANVAS_OPERATION
):
    """Canvas 작업 트레이싱 데코레이터"""
    def decorator(func: Callable):
        op_name = operation_name or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with canvas_tracer.trace_async_operation(op_name, trace_type) as span:
                    span.add_tag("function", func.__name__)
                    span.add_tag("module", func.__module__)
                    
                    try:
                        result = await func(*args, **kwargs)
                        span.add_tag("result_type", type(result).__name__)
                        return result
                    except Exception as e:
                        span.log_event(f"Exception: {str(e)}", TraceLevel.ERROR)
                        raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with canvas_tracer.trace_operation(op_name, trace_type) as span:
                    span.add_tag("function", func.__name__)
                    span.add_tag("module", func.__module__)
                    
                    try:
                        result = func(*args, **kwargs)
                        span.add_tag("result_type", type(result).__name__)
                        return result
                    except Exception as e:
                        span.log_event(f"Exception: {str(e)}", TraceLevel.ERROR)
                        raise
            return sync_wrapper
    return decorator

# ======= 글로벌 인스턴스 =======

canvas_tracer = CanvasTracer()

# ======= 편의 함수들 =======

def start_canvas_trace(operation_name: str, conversation_id: str, user_id: Optional[str] = None) -> str:
    """Canvas 트레이스 시작 편의 함수"""
    return canvas_tracer.start_trace(operation_name, conversation_id, user_id)

def get_canvas_performance_summary(time_window_minutes: int = 60) -> Dict[str, Any]:
    """Canvas 성능 요약 조회"""
    return canvas_tracer.get_performance_summary(time_window_minutes)