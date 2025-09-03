"""
Canvas Telemetry API v1.0 - OpenTelemetry 분산 트레이싱 API
실시간 성능 모니터링 및 분석 대시보드를 위한 RESTful API
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timezone

from app.services.canvas_telemetry import canvas_tracer, get_canvas_performance_summary, CanvasTraceType
from app.api.deps import get_current_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Router 생성
router = APIRouter(prefix="/canvas/telemetry", tags=["canvas-telemetry"])

# ======= Pydantic 모델들 =======

class TraceSpanResponse(BaseModel):
    """트레이스 스팬 응답 모델"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    trace_type: str
    start_time: float
    end_time: Optional[float]
    duration_ms: Optional[float]
    status: str
    tags: Dict[str, Any]
    logs: List[Dict[str, Any]]
    error: Optional[str]

class CanvasTraceResponse(BaseModel):
    """Canvas 트레이스 응답 모델"""
    trace_id: str
    conversation_id: str
    user_id: Optional[str]
    root_operation: str
    start_time: float
    end_time: Optional[float]
    total_duration_ms: Optional[float]
    spans: Dict[str, TraceSpanResponse]
    metrics: Dict[str, Any]

class PerformanceSummaryResponse(BaseModel):
    """성능 요약 응답 모델"""
    time_window_minutes: int
    total_traces: int
    avg_duration_ms: float
    error_rate: float
    operation_breakdown: Dict[str, Any]
    span_type_metrics: Dict[str, Any]
    timestamp: str

class TraceListResponse(BaseModel):
    """트레이스 목록 응답 모델"""
    traces: List[CanvasTraceResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool

# ======= API 엔드포인트들 =======

@router.get("/performance/summary", response_model=PerformanceSummaryResponse)
async def get_performance_summary(
    time_window_minutes: int = Query(60, ge=1, le=1440, description="성능 분석 시간 윈도우 (분)"),
    current_user = Depends(get_current_user)
):
    """
    Canvas 성능 요약 통계 조회
    
    - **time_window_minutes**: 분석할 시간 범위 (1분~24시간)
    - **returns**: 성능 메트릭, 에러율, 작업별 성능 분석
    """
    try:
        summary = get_canvas_performance_summary(time_window_minutes)
        
        if "message" in summary:  # No data case
            summary = {
                "time_window_minutes": time_window_minutes,
                "total_traces": 0,
                "avg_duration_ms": 0.0,
                "error_rate": 0.0,
                "operation_breakdown": {},
                "span_type_metrics": {}
            }
        
        return PerformanceSummaryResponse(
            **summary,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ 성능 요약 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Performance summary query failed: {str(e)}")

@router.get("/traces/{conversation_id}", response_model=TraceListResponse)
async def get_conversation_traces(
    conversation_id: str,
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    current_user = Depends(get_current_user)
):
    """
    특정 대화의 모든 트레이스 조회
    
    - **conversation_id**: 대화방 ID
    - **page**: 페이지 번호 (1부터 시작)  
    - **page_size**: 페이지당 항목 수
    - **returns**: 페이징된 트레이스 목록
    """
    try:
        # 전체 트레이스 조회
        all_traces = canvas_tracer.get_conversation_traces(conversation_id, limit=1000)
        total_count = len(all_traces)
        
        # 페이징 처리
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_traces = all_traces[start_index:end_index]
        
        # 응답 모델로 변환
        trace_responses = []
        for trace in paginated_traces:
            span_responses = {}
            for span_id, span in trace.spans.items():
                span_responses[span_id] = TraceSpanResponse(
                    span_id=span.span_id,
                    trace_id=span.trace_id,
                    parent_span_id=span.parent_span_id,
                    operation_name=span.operation_name,
                    trace_type=span.trace_type.value,
                    start_time=span.start_time,
                    end_time=span.end_time,
                    duration_ms=span.duration_ms,
                    status=span.status,
                    tags=span.tags,
                    logs=span.logs,
                    error=span.error
                )
            
            trace_responses.append(CanvasTraceResponse(
                trace_id=trace.trace_id,
                conversation_id=trace.conversation_id,
                user_id=trace.user_id,
                root_operation=trace.root_operation,
                start_time=trace.start_time,
                end_time=trace.end_time,
                total_duration_ms=trace.total_duration_ms,
                spans=span_responses,
                metrics=trace.metrics
            ))
        
        return TraceListResponse(
            traces=trace_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=end_index < total_count
        )
        
    except Exception as e:
        logger.error(f"❌ 대화 트레이스 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Conversation traces query failed: {str(e)}")

@router.get("/traces/detail/{trace_id}", response_model=CanvasTraceResponse)
async def get_trace_detail(
    trace_id: str,
    current_user = Depends(get_current_user)
):
    """
    특정 트레이스의 상세 정보 조회
    
    - **trace_id**: 조회할 트레이스 ID
    - **returns**: 트레이스 상세 정보 (모든 스팬과 메트릭 포함)
    """
    try:
        trace = canvas_tracer.get_trace(trace_id)
        
        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
        
        # 스팬들을 응답 모델로 변환
        span_responses = {}
        for span_id, span in trace.spans.items():
            span_responses[span_id] = TraceSpanResponse(
                span_id=span.span_id,
                trace_id=span.trace_id,
                parent_span_id=span.parent_span_id,
                operation_name=span.operation_name,
                trace_type=span.trace_type.value,
                start_time=span.start_time,
                end_time=span.end_time,
                duration_ms=span.duration_ms,
                status=span.status,
                tags=span.tags,
                logs=span.logs,
                error=span.error
            )
        
        return CanvasTraceResponse(
            trace_id=trace.trace_id,
            conversation_id=trace.conversation_id,
            user_id=trace.user_id,
            root_operation=trace.root_operation,
            start_time=trace.start_time,
            end_time=trace.end_time,
            total_duration_ms=trace.total_duration_ms,
            spans=span_responses,
            metrics=trace.metrics
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 트레이스 상세 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Trace detail query failed: {str(e)}")

@router.get("/metrics/realtime")
async def get_realtime_metrics(
    current_user = Depends(get_current_user)
):
    """
    실시간 Canvas 메트릭 조회
    
    - **returns**: 현재 활성 트레이스, 스팬, 연결 상태 등 실시간 지표
    """
    try:
        from app.services.canvas_websocket_manager import canvas_websocket_manager
        from app.services.canvas_operational_transform import canvas_ot_engine
        
        # 실시간 상태 수집
        active_traces = len(canvas_tracer.active_traces)
        active_spans = len(canvas_tracer.active_spans)
        total_connections = canvas_websocket_manager.get_total_connections()
        
        # OT 엔진 상태
        total_conversations = len(canvas_ot_engine.operation_history)
        pending_operations = sum(
            len(ops) for ops in canvas_ot_engine.pending_operations.values()
        )
        
        # 최근 1분간 트레이스 분석
        recent_summary = get_canvas_performance_summary(1)
        
        realtime_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_state": {
                "active_traces": active_traces,
                "active_spans": active_spans,
                "websocket_connections": total_connections,
                "ot_conversations": total_conversations,
                "pending_operations": pending_operations
            },
            "recent_activity": recent_summary if "message" not in recent_summary else {
                "total_traces": 0,
                "avg_duration_ms": 0.0,
                "error_rate": 0.0
            },
            "system_health": {
                "trace_storage_size": len(canvas_tracer.trace_storage),
                "max_trace_capacity": canvas_tracer.max_traces,
                "memory_usage_ratio": len(canvas_tracer.trace_storage) / canvas_tracer.max_traces
            }
        }
        
        return realtime_data
        
    except Exception as e:
        logger.error(f"❌ 실시간 메트릭 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Realtime metrics query failed: {str(e)}")

@router.get("/analytics/performance-trends")
async def get_performance_trends(
    time_windows: List[int] = Query([5, 15, 60], description="분석할 시간 윈도우들 (분)"),
    current_user = Depends(get_current_user)
):
    """
    Canvas 성능 트렌드 분석
    
    - **time_windows**: 분석할 시간 윈도우 목록 (예: [5, 15, 60]분)
    - **returns**: 시간대별 성능 트렌드 데이터
    """
    try:
        trends = {}
        
        for window in time_windows:
            if window < 1 or window > 1440:
                continue  # 1분~24시간 범위만 허용
                
            summary = get_canvas_performance_summary(window)
            trends[f"{window}_minutes"] = summary
        
        # 트렌드 분석
        if len(trends) > 1:
            windows = sorted([int(k.split('_')[0]) for k in trends.keys()])
            
            # 성능 변화 계산
            performance_change = {}
            for i in range(1, len(windows)):
                prev_window = f"{windows[i-1]}_minutes"
                curr_window = f"{windows[i]}_minutes"
                
                if trends[prev_window].get("avg_duration_ms", 0) > 0:
                    change_ratio = (
                        trends[curr_window].get("avg_duration_ms", 0) - 
                        trends[prev_window].get("avg_duration_ms", 0)
                    ) / trends[prev_window]["avg_duration_ms"]
                    
                    performance_change[f"{prev_window}_to_{curr_window}"] = {
                        "duration_change_percent": change_ratio * 100,
                        "error_rate_change": trends[curr_window].get("error_rate", 0) - trends[prev_window].get("error_rate", 0)
                    }
        else:
            performance_change = {}
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "time_window_data": trends,
            "trend_analysis": performance_change,
            "recommendations": _generate_performance_recommendations(trends)
        }
        
    except Exception as e:
        logger.error(f"❌ 성능 트렌드 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Performance trends analysis failed: {str(e)}")

@router.get("/analytics/operation-insights/{operation_name}")
async def get_operation_insights(
    operation_name: str,
    time_window_minutes: int = Query(60, ge=1, le=1440),
    current_user = Depends(get_current_user)
):
    """
    특정 Canvas 작업의 성능 인사이트
    
    - **operation_name**: 분석할 작업명
    - **time_window_minutes**: 분석 시간 범위
    - **returns**: 작업별 상세 성능 분석
    """
    try:
        # 해당 작업의 모든 트레이스 수집
        all_traces = canvas_tracer.trace_storage
        cutoff_time = datetime.now().timestamp() - (time_window_minutes * 60)
        
        operation_traces = [
            trace for trace in all_traces
            if trace.root_operation == operation_name and trace.start_time >= cutoff_time
        ]
        
        if not operation_traces:
            return {
                "operation_name": operation_name,
                "time_window_minutes": time_window_minutes,
                "message": "No traces found for this operation"
            }
        
        # 성능 분석
        durations = [trace.total_duration_ms or 0 for trace in operation_traces]
        error_traces = [trace for trace in operation_traces if any(s.status == "ERROR" for s in trace.spans.values())]
        
        # 스팬별 분석
        span_analysis = {}
        for trace in operation_traces:
            for span in trace.spans.values():
                span_type = span.trace_type.value
                if span_type not in span_analysis:
                    span_analysis[span_type] = {
                        "count": 0,
                        "durations": [],
                        "errors": 0
                    }
                
                span_analysis[span_type]["count"] += 1
                if span.duration_ms:
                    span_analysis[span_type]["durations"].append(span.duration_ms)
                if span.status == "ERROR":
                    span_analysis[span_type]["errors"] += 1
        
        # 통계 계산
        for span_type in span_analysis:
            durations = span_analysis[span_type]["durations"]
            if durations:
                span_analysis[span_type]["avg_duration"] = sum(durations) / len(durations)
                span_analysis[span_type]["max_duration"] = max(durations)
                span_analysis[span_type]["min_duration"] = min(durations)
            else:
                span_analysis[span_type].update({
                    "avg_duration": 0,
                    "max_duration": 0, 
                    "min_duration": 0
                })
        
        insights = {
            "operation_name": operation_name,
            "time_window_minutes": time_window_minutes,
            "summary": {
                "total_executions": len(operation_traces),
                "avg_duration_ms": sum(durations) / len(durations),
                "max_duration_ms": max(durations),
                "min_duration_ms": min(durations),
                "error_count": len(error_traces),
                "error_rate": len(error_traces) / len(operation_traces),
                "success_rate": (len(operation_traces) - len(error_traces)) / len(operation_traces)
            },
            "span_breakdown": span_analysis,
            "top_errors": _extract_top_errors(error_traces),
            "performance_percentiles": {
                "p50": _percentile(durations, 0.5),
                "p90": _percentile(durations, 0.9),
                "p95": _percentile(durations, 0.95),
                "p99": _percentile(durations, 0.99)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return insights
        
    except Exception as e:
        logger.error(f"❌ 작업 인사이트 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Operation insights analysis failed: {str(e)}")

@router.delete("/traces/cleanup")
async def cleanup_old_traces(
    older_than_hours: int = Query(24, ge=1, le=168, description="이 시간보다 오래된 트레이스 삭제 (시간)"),
    current_user = Depends(get_current_user)
):
    """
    오래된 트레이스 데이터 정리
    
    - **older_than_hours**: 삭제할 트레이스의 기준 시간 (1시간~1주일)
    - **returns**: 정리 결과
    """
    try:
        cutoff_time = datetime.now().timestamp() - (older_than_hours * 3600)
        
        initial_count = len(canvas_tracer.trace_storage)
        canvas_tracer.trace_storage = [
            trace for trace in canvas_tracer.trace_storage
            if trace.start_time >= cutoff_time
        ]
        final_count = len(canvas_tracer.trace_storage)
        
        deleted_count = initial_count - final_count
        
        logger.info(f"🧹 트레이스 정리 완료: {deleted_count}개 삭제, {final_count}개 유지")
        
        return {
            "cleanup_completed": True,
            "older_than_hours": older_than_hours,
            "initial_trace_count": initial_count,
            "final_trace_count": final_count,
            "deleted_trace_count": deleted_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 트레이스 정리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Trace cleanup failed: {str(e)}")

# ======= 보조 함수들 =======

def _generate_performance_recommendations(trends: Dict[str, Any]) -> List[str]:
    """성능 개선 추천사항 생성"""
    recommendations = []
    
    # 평균 응답 시간 분석
    for window, data in trends.items():
        if data.get("avg_duration_ms", 0) > 1000:
            recommendations.append(f"High average response time ({data['avg_duration_ms']:.1f}ms) in {window} window - consider optimization")
    
    # 에러율 분석
    for window, data in trends.items():
        if data.get("error_rate", 0) > 0.05:  # 5% 이상
            recommendations.append(f"High error rate ({data['error_rate']:.1%}) in {window} window - investigate error causes")
    
    if not recommendations:
        recommendations.append("System performance is within normal parameters")
    
    return recommendations

def _extract_top_errors(error_traces: List[Any]) -> List[Dict[str, Any]]:
    """상위 에러 유형 추출"""
    error_counts = {}
    
    for trace in error_traces:
        for span in trace.spans.values():
            if span.status == "ERROR" and span.error:
                error_type = span.error.split(":")[0]  # Exception type
                if error_type not in error_counts:
                    error_counts[error_type] = {
                        "count": 0,
                        "examples": []
                    }
                error_counts[error_type]["count"] += 1
                if len(error_counts[error_type]["examples"]) < 3:
                    error_counts[error_type]["examples"].append({
                        "trace_id": trace.trace_id,
                        "error_message": span.error,
                        "timestamp": span.end_time or span.start_time
                    })
    
    # 상위 5개 에러 유형 반환
    top_errors = sorted(error_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
    
    return [
        {
            "error_type": error_type,
            "count": data["count"],
            "examples": data["examples"]
        }
        for error_type, data in top_errors
    ]

def _percentile(values: List[float], percentile: float) -> float:
    """백분위수 계산"""
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile)
    return sorted_values[min(index, len(sorted_values) - 1)]