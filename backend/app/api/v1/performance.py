"""
성능 모니터링 및 최적화 API 엔드포인트
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
import logging

from app.api.deps import get_current_active_user
from app.services.langgraph_monitor import langgraph_monitor
from app.services.performance_optimizer import performance_optimizer

logger = logging.getLogger(__name__)
router = APIRouter()


class PerformanceReportResponse(BaseModel):
    """성능 리포트 응답 모델"""
    timestamp: str
    monitoring: Dict[str, Any]
    performance: Dict[str, Any]
    system_health: Dict[str, Any]
    recommendations: List[str]


class OptimizationRequest(BaseModel):
    """최적화 요청 모델"""
    force_optimization: bool = False
    optimization_strategies: Optional[List[str]] = None


class OptimizationResponse(BaseModel):
    """최적화 응답 모델"""
    success: bool
    optimizations_applied: List[str]
    performance_improvement: Optional[float]
    message: str


@router.get("/health", response_model=Dict[str, Any])
async def get_system_health(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    시스템 전체 건강도 조회
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        시스템 건강도 정보
    """
    try:
        comprehensive_report = await langgraph_monitor.get_comprehensive_report()
        return comprehensive_report["system_health"]
        
    except Exception as e:
        logger.error(f"시스템 건강도 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="시스템 건강도 조회 중 오류가 발생했습니다."
        )


@router.get("/report", response_model=PerformanceReportResponse)
async def get_performance_report(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> PerformanceReportResponse:
    """
    통합 성능 리포트 조회
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        통합 성능 리포트
    """
    try:
        comprehensive_report = await langgraph_monitor.get_comprehensive_report()
        
        return PerformanceReportResponse(**comprehensive_report)
        
    except Exception as e:
        logger.error(f"성능 리포트 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="성능 리포트 조회 중 오류가 발생했습니다."
        )


@router.get("/metrics/realtime")
async def get_realtime_metrics(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    실시간 성능 메트릭 조회
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        실시간 메트릭 데이터
    """
    try:
        realtime_metrics = await langgraph_monitor.get_realtime_metrics()
        return realtime_metrics
        
    except Exception as e:
        logger.error(f"실시간 메트릭 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="실시간 메트릭 조회 중 오류가 발생했습니다."
        )


@router.get("/performance-score")
async def get_performance_score(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    현재 성능 점수 조회
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        성능 점수 및 등급
    """
    try:
        performance_report = performance_optimizer.get_performance_report()
        
        return {
            "performance_score": performance_report.get("performance_score", 0),
            "performance_level": performance_report.get("performance_level", "unknown"),
            "metrics": performance_report.get("metrics", {}),
            "timestamp": performance_report.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"성능 점수 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="성능 점수 조회 중 오류가 발생했습니다."
        )


@router.post("/optimize", response_model=OptimizationResponse)
async def trigger_optimization(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> OptimizationResponse:
    """
    성능 최적화 트리거
    
    Args:
        request: 최적화 요청 데이터
        background_tasks: 백그라운드 작업 큐
        current_user: 현재 사용자 정보
        
    Returns:
        최적화 결과
    """
    try:
        # 현재 성능 점수 측정
        current_performance = performance_optimizer.get_performance_report()
        current_score = current_performance.get("performance_score", 0)
        
        optimizations_applied = []
        
        if request.force_optimization or current_score < 70:
            logger.info(f"성능 최적화 시작 - 현재 점수: {current_score}")
            
            # 백그라운드에서 최적화 실행
            if current_score < 30:  # Critical
                background_tasks.add_task(_run_emergency_optimization)
                optimizations_applied.append("emergency_optimization")
            elif current_score < 50:  # Poor
                background_tasks.add_task(_run_proactive_optimization)  
                optimizations_applied.append("proactive_optimization")
            else:
                background_tasks.add_task(_run_maintenance_optimization)
                optimizations_applied.append("maintenance_optimization")
            
            return OptimizationResponse(
                success=True,
                optimizations_applied=optimizations_applied,
                performance_improvement=None,  # 백그라운드 실행이므로 미확정
                message="성능 최적화가 백그라운드에서 실행 중입니다."
            )
        else:
            return OptimizationResponse(
                success=True,
                optimizations_applied=[],
                performance_improvement=0.0,
                message=f"현재 성능이 양호합니다 (점수: {current_score}). 최적화가 필요하지 않습니다."
            )
            
    except Exception as e:
        logger.error(f"성능 최적화 트리거 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="성능 최적화 실행 중 오류가 발생했습니다."
        )


@router.get("/circuit-breakers")
async def get_circuit_breaker_status(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Circuit Breaker 상태 조회
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        Circuit Breaker 상태 정보
    """
    try:
        performance_report = performance_optimizer.get_performance_report()
        circuit_breaker_status = performance_report.get("circuit_breaker_status", {})
        
        return {
            "circuit_breakers": circuit_breaker_status,
            "total_breakers": len(circuit_breaker_status),
            "open_breakers": len([
                name for name, status in circuit_breaker_status.items() 
                if status.get("state") == "open"
            ]),
            "timestamp": performance_report.get("timestamp")
        }
        
    except Exception as e:
        logger.error(f"Circuit Breaker 상태 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Circuit Breaker 상태 조회 중 오류가 발생했습니다."
        )


@router.get("/optimization-history")
async def get_optimization_history(
    limit: int = 10,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    최적화 이력 조회
    
    Args:
        limit: 조회할 이력 수
        current_user: 현재 사용자 정보
        
    Returns:
        최적화 이력
    """
    try:
        optimization_history = performance_optimizer.optimization_history[-limit:]
        
        return {
            "optimization_history": optimization_history,
            "total_optimizations": len(performance_optimizer.optimization_history),
            "recent_count": len(optimization_history)
        }
        
    except Exception as e:
        logger.error(f"최적화 이력 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="최적화 이력 조회 중 오류가 발생했습니다."
        )


@router.post("/monitoring/start")
async def start_monitoring(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    실시간 모니터링 시작
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        시작 확인 메시지
    """
    try:
        await performance_optimizer.start_monitoring()
        return {"message": "실시간 성능 모니터링이 시작되었습니다."}
        
    except Exception as e:
        logger.error(f"모니터링 시작 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="모니터링 시작 중 오류가 발생했습니다."
        )


@router.post("/monitoring/stop")
async def stop_monitoring(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    실시간 모니터링 중지
    
    Args:
        current_user: 현재 사용자 정보
        
    Returns:
        중지 확인 메시지
    """
    try:
        await performance_optimizer.stop_monitoring()
        return {"message": "실시간 성능 모니터링이 중지되었습니다."}
        
    except Exception as e:
        logger.error(f"모니터링 중지 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="모니터링 중지 중 오류가 발생했습니다."
        )


# 백그라운드 최적화 함수들
async def _run_emergency_optimization():
    """긴급 최적화 실행"""
    try:
        logger.info("긴급 최적화 실행 시작")
        
        # 현재 메트릭 수집
        metrics = await performance_optimizer._collect_metrics()
        
        # 긴급 최적화 실행
        await performance_optimizer._emergency_optimization(metrics)
        
        logger.info("긴급 최적화 완료")
        
    except Exception as e:
        logger.error(f"긴급 최적화 실행 실패: {e}")


async def _run_proactive_optimization():
    """사전 예방적 최적화 실행"""
    try:
        logger.info("사전 예방적 최적화 실행 시작")
        
        # 현재 메트릭 수집
        metrics = await performance_optimizer._collect_metrics()
        
        # 사전 예방적 최적화 실행
        await performance_optimizer._proactive_optimization(metrics)
        
        logger.info("사전 예방적 최적화 완료")
        
    except Exception as e:
        logger.error(f"사전 예방적 최적화 실행 실패: {e}")


async def _run_maintenance_optimization():
    """유지보수 최적화 실행"""
    try:
        logger.info("유지보수 최적화 실행 시작")
        
        # 기본적인 정리 작업
        await performance_optimizer._force_garbage_collection()
        await performance_optimizer._clear_performance_cache()
        
        logger.info("유지보수 최적화 완료")
        
    except Exception as e:
        logger.error(f"유지보수 최적화 실행 실패: {e}")