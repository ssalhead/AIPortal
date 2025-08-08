"""
성능 모니터링 API 엔드포인트
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.services.performance_monitor import performance_monitor
from app.services.conversation_cache_manager import conversation_cache_manager
from app.services.intelligent_cache_manager import intelligent_cache_manager
from app.db.models.user import User

router = APIRouter()


@router.get("/summary")
async def get_performance_summary(
    minutes: int = Query(30, ge=1, le=1440, description="시간 범위 (분)"),
    current_user: User = Depends(get_current_user)
):
    """성능 요약 조회"""
    try:
        summary = performance_monitor.get_performance_summary(minutes=minutes)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database")
async def get_database_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """데이터베이스 성능 상세 조회"""
    try:
        db_stats = await performance_monitor.get_database_performance(db)
        return db_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache")
async def get_cache_performance(
    current_user: User = Depends(get_current_user)
):
    """캐시 성능 조회"""
    try:
        # 전역 캐시 통계
        base_cache_stats = performance_monitor.current_stats.get('cache_hit_rates', {})
        
        # 대화 캐시 통계
        conversation_cache_stats = conversation_cache_manager.get_cache_stats()
        
        # 지능형 캐시 통계
        intelligent_cache_stats = intelligent_cache_manager.get_intelligent_stats()
        
        return {
            'base_cache': base_cache_stats,
            'conversation_cache': conversation_cache_stats,
            'intelligent_cache': intelligent_cache_stats,
            'cache_metrics': {
                cache_key: {
                    'hit_rate': sum(hit_history) / len(hit_history) * 100 if hit_history else 0,
                    'total_operations': len(hit_history)
                }
                for cache_key, hit_history in base_cache_stats.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api")
async def get_api_performance(
    minutes: int = Query(30, ge=1, le=1440),
    current_user: User = Depends(get_current_user)
):
    """API 성능 조회"""
    try:
        # 최근 API 메트릭 필터링
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_api_metrics = [
            m for m in performance_monitor.api_metrics 
            if m.timestamp >= cutoff_time
        ]
        
        # API 통계 계산
        api_stats = performance_monitor._calculate_api_stats(recent_api_metrics)
        
        # 추가적인 분석
        if recent_api_metrics:
            # 시간대별 요청 분포
            hourly_distribution = {}
            for metric in recent_api_metrics:
                hour_key = metric.timestamp.strftime("%H:00")
                if hour_key not in hourly_distribution:
                    hourly_distribution[hour_key] = 0
                hourly_distribution[hour_key] += 1
            
            # 가장 느린 요청들
            slowest_requests = sorted(
                recent_api_metrics, 
                key=lambda x: x.duration_ms, 
                reverse=True
            )[:10]
            
            slowest_requests_data = [
                {
                    'endpoint': f"{m.method} {m.endpoint}",
                    'duration_ms': m.duration_ms,
                    'status_code': m.status_code,
                    'timestamp': m.timestamp.isoformat()
                }
                for m in slowest_requests
            ]
            
            api_stats.update({
                'hourly_distribution': hourly_distribution,
                'slowest_requests': slowest_requests_data
            })
        
        return api_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system")
async def get_system_performance(
    current_user: User = Depends(get_current_user)
):
    """시스템 성능 조회"""
    try:
        system_stats = performance_monitor._get_latest_system_stats()
        
        # 추가 시스템 정보
        import psutil
        
        # 프로세스 정보
        process = psutil.Process()
        
        additional_stats = {
            'process_memory_mb': process.memory_info().rss / 1024 / 1024,
            'process_cpu_percent': process.cpu_percent(),
            'open_files': len(process.open_files()),
            'threads': process.num_threads(),
            'connections': len(process.connections())
        }
        
        system_stats.update(additional_stats)
        
        return {
            'current_metrics': system_stats,
            'monitoring_active': performance_monitor.is_monitoring
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/export")
async def export_metrics(
    format: str = Query("json", regex="^(json|prometheus)$"),
    minutes: int = Query(60, ge=1, le=1440),
    current_user: User = Depends(get_current_user)
):
    """메트릭 데이터 내보내기"""
    try:
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        # 메트릭 데이터 수집
        recent_metrics = [
            m for m in performance_monitor.metrics 
            if m.timestamp >= cutoff_time
        ]
        
        if format == "json":
            return {
                'export_format': 'json',
                'time_range_minutes': minutes,
                'exported_at': datetime.utcnow().isoformat(),
                'metrics': [
                    {
                        'timestamp': m.timestamp.isoformat(),
                        'name': m.name,
                        'value': m.value,
                        'labels': m.labels,
                        'metadata': m.metadata
                    }
                    for m in recent_metrics
                ]
            }
        
        elif format == "prometheus":
            # Prometheus 형식으로 내보내기
            prometheus_lines = []
            
            for metric in recent_metrics:
                # 라벨 문자열 생성
                labels_str = ""
                if metric.labels:
                    labels_list = [f'{k}="{v}"' for k, v in metric.labels.items()]
                    labels_str = "{" + ",".join(labels_list) + "}"
                
                # 메트릭 라인 생성
                prometheus_lines.append(
                    f'{metric.name.replace("-", "_")}{labels_str} {metric.value} '
                    f'{int(metric.timestamp.timestamp() * 1000)}'
                )
            
            return {
                'export_format': 'prometheus',
                'content': '\n'.join(prometheus_lines)
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/start")
async def start_monitoring(
    current_user: User = Depends(get_current_user)
):
    """성능 모니터링 시작"""
    try:
        if not performance_monitor.is_monitoring:
            performance_monitor.start_monitoring()
            return {"message": "성능 모니터링이 시작되었습니다.", "status": "started"}
        else:
            return {"message": "성능 모니터링이 이미 실행 중입니다.", "status": "already_running"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/stop")
async def stop_monitoring(
    current_user: User = Depends(get_current_user)
):
    """성능 모니터링 중지"""
    try:
        if performance_monitor.is_monitoring:
            performance_monitor.stop_monitoring()
            return {"message": "성능 모니터링이 중지되었습니다.", "status": "stopped"}
        else:
            return {"message": "성능 모니터링이 실행되고 있지 않습니다.", "status": "not_running"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_performance_health():
    """성능 건강 상태 체크 (인증 불필요)"""
    try:
        import psutil
        
        # 기본 건강 상태 지표
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 건강 상태 판정
        health_status = "healthy"
        issues = []
        
        if cpu_percent > 80:
            health_status = "warning"
            issues.append(f"높은 CPU 사용률: {cpu_percent:.1f}%")
        
        if memory.percent > 85:
            health_status = "warning"
            issues.append(f"높은 메모리 사용률: {memory.percent:.1f}%")
        
        if disk.percent > 90:
            health_status = "critical"
            issues.append(f"디스크 공간 부족: {disk.percent:.1f}%")
        
        # 최근 에러 확인
        recent_errors = sum(performance_monitor.current_stats['error_counts'].values())
        if recent_errors > 10:
            health_status = "warning"
            issues.append(f"최근 에러 증가: {recent_errors}개")
        
        return {
            'status': health_status,
            'timestamp': datetime.utcnow().isoformat(),
            'issues': issues,
            'metrics': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'recent_errors': recent_errors
            },
            'monitoring_active': performance_monitor.is_monitoring
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@router.get("/cache/intelligent")
async def get_intelligent_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """지능형 캐시 상세 통계"""
    try:
        stats = intelligent_cache_manager.get_intelligent_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/optimize")
async def optimize_cache_configuration(
    current_user: User = Depends(get_current_user)
):
    """캐시 설정 자동 최적화"""
    try:
        optimization = await intelligent_cache_manager.optimize_cache_configuration()
        return optimization
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/intelligent/start")
async def start_intelligent_cache(
    current_user: User = Depends(get_current_user)
):
    """지능형 캐시 시스템 시작"""
    try:
        await intelligent_cache_manager.start()
        return {"message": "지능형 캐시 시스템이 시작되었습니다.", "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/intelligent/stop")
async def stop_intelligent_cache(
    current_user: User = Depends(get_current_user)
):
    """지능형 캐시 시스템 중지"""
    try:
        await intelligent_cache_manager.stop()
        return {"message": "지능형 캐시 시스템이 중지되었습니다.", "status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))