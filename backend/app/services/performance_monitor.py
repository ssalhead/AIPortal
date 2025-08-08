"""
성능 모니터링 및 메트릭 수집 시스템
"""

import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import psutil
import json

import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricEntry:
    """메트릭 엔트리"""
    timestamp: datetime
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryMetrics:
    """데이터베이스 쿼리 메트릭"""
    query_type: str
    duration_ms: float
    rows_affected: int
    timestamp: datetime
    success: bool
    error: Optional[str] = None


@dataclass
class APIMetrics:
    """API 요청 메트릭"""
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: datetime
    user_id: Optional[str] = None
    error: Optional[str] = None


class PerformanceMonitor:
    """성능 모니터링 시스템"""
    
    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        
        # 메트릭 저장소 (메모리 기반 순환 큐)
        self.metrics: deque = deque(maxlen=max_entries)
        self.query_metrics: deque = deque(maxlen=max_entries)
        self.api_metrics: deque = deque(maxlen=max_entries)
        
        # 실시간 집계 데이터
        self.current_stats = {
            'api_requests_per_minute': defaultdict(int),
            'query_counts_per_minute': defaultdict(int),
            'cache_hit_rates': defaultdict(list),
            'error_counts': defaultdict(int),
            'response_times': defaultdict(list)
        }
        
        # 시스템 메트릭 수집 태스크
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
    
    def start_monitoring(self):
        """모니터링 시작"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitoring_task = asyncio.create_task(self._collect_system_metrics())
            logger.info("성능 모니터링 시작됨")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            logger.info("성능 모니터링 중지됨")
    
    async def _collect_system_metrics(self):
        """시스템 메트릭 주기적 수집"""
        while self.is_monitoring:
            try:
                # CPU 사용률
                cpu_percent = psutil.cpu_percent(interval=1)
                self.record_metric("system_cpu_percent", cpu_percent)
                
                # 메모리 사용률
                memory = psutil.virtual_memory()
                self.record_metric("system_memory_percent", memory.percent)
                self.record_metric("system_memory_used_mb", memory.used / 1024 / 1024)
                
                # 디스크 사용률
                disk = psutil.disk_usage('/')
                self.record_metric("system_disk_percent", disk.percent)
                
                # 네트워크 I/O
                net_io = psutil.net_io_counters()
                self.record_metric("system_network_bytes_sent", net_io.bytes_sent)
                self.record_metric("system_network_bytes_recv", net_io.bytes_recv)
                
                await asyncio.sleep(30)  # 30초마다 수집
                
            except Exception as e:
                logger.error(f"시스템 메트릭 수집 오류: {str(e)}")
                await asyncio.sleep(30)
    
    def record_metric(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """메트릭 기록"""
        metric = MetricEntry(
            timestamp=datetime.utcnow(),
            name=name,
            value=value,
            labels=labels or {},
            metadata=metadata or {}
        )
        self.metrics.append(metric)
        
        # 실시간 집계 업데이트
        minute_key = metric.timestamp.strftime("%Y-%m-%d %H:%M")
        
        if name.endswith("_response_time"):
            self.current_stats['response_times'][minute_key].append(value)
        elif name.endswith("_error_count"):
            self.current_stats['error_counts'][minute_key] += value
    
    def record_query_metrics(
        self,
        query_type: str,
        duration_ms: float,
        rows_affected: int = 0,
        success: bool = True,
        error: Optional[str] = None
    ):
        """데이터베이스 쿼리 메트릭 기록"""
        metrics = QueryMetrics(
            query_type=query_type,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            timestamp=datetime.utcnow(),
            success=success,
            error=error
        )
        self.query_metrics.append(metrics)
        
        # 실시간 집계
        minute_key = metrics.timestamp.strftime("%Y-%m-%d %H:%M")
        self.current_stats['query_counts_per_minute'][minute_key] += 1
        self.current_stats['response_times'][f"db_{query_type}"].append(duration_ms)
        
        if not success:
            self.current_stats['error_counts'][f"db_{query_type}"] += 1
    
    def record_api_metrics(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """API 요청 메트릭 기록"""
        metrics = APIMetrics(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            error=error
        )
        self.api_metrics.append(metrics)
        
        # 실시간 집계
        minute_key = metrics.timestamp.strftime("%Y-%m-%d %H:%M")
        endpoint_key = f"{method}_{endpoint.replace('/', '_')}"
        
        self.current_stats['api_requests_per_minute'][minute_key] += 1
        self.current_stats['response_times'][endpoint_key].append(duration_ms)
        
        if status_code >= 400:
            self.current_stats['error_counts'][endpoint_key] += 1
    
    def record_cache_metrics(
        self,
        cache_type: str,
        operation: str,
        hit: bool,
        duration_ms: float = 0
    ):
        """캐시 메트릭 기록"""
        minute_key = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        cache_key = f"{cache_type}_{operation}"
        
        # 캐시 적중률 계산
        if cache_key not in self.current_stats['cache_hit_rates']:
            self.current_stats['cache_hit_rates'][cache_key] = []
        
        self.current_stats['cache_hit_rates'][cache_key].append(1 if hit else 0)
        
        # 최근 100개 기록만 유지
        if len(self.current_stats['cache_hit_rates'][cache_key]) > 100:
            self.current_stats['cache_hit_rates'][cache_key] = \
                self.current_stats['cache_hit_rates'][cache_key][-100:]
        
        self.record_metric(
            f"cache_{cache_type}_{operation}_duration",
            duration_ms,
            labels={"hit": str(hit)}
        )
    
    @asynccontextmanager
    async def track_query(self, query_type: str):
        """쿼리 실행 시간 추적 컨텍스트 매니저"""
        start_time = time.time()
        success = True
        error = None
        rows_affected = 0
        
        try:
            yield
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.record_query_metrics(
                query_type=query_type,
                duration_ms=duration_ms,
                rows_affected=rows_affected,
                success=success,
                error=error
            )
    
    @asynccontextmanager
    async def track_api_request(
        self, 
        endpoint: str, 
        method: str, 
        user_id: Optional[str] = None
    ):
        """API 요청 시간 추적 컨텍스트 매니저"""
        start_time = time.time()
        status_code = 200
        error = None
        
        try:
            yield
        except Exception as e:
            status_code = 500
            error = str(e)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.record_api_metrics(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                duration_ms=duration_ms,
                user_id=user_id,
                error=error
            )
    
    def get_performance_summary(self, minutes: int = 30) -> Dict[str, Any]:
        """성능 요약 조회"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        # 최근 메트릭 필터링
        recent_query_metrics = [
            m for m in self.query_metrics 
            if m.timestamp >= cutoff_time
        ]
        
        recent_api_metrics = [
            m for m in self.api_metrics 
            if m.timestamp >= cutoff_time
        ]
        
        # 통계 계산
        query_stats = self._calculate_query_stats(recent_query_metrics)
        api_stats = self._calculate_api_stats(recent_api_metrics)
        cache_stats = self._calculate_cache_stats()
        system_stats = self._get_latest_system_stats()
        
        return {
            'time_window_minutes': minutes,
            'timestamp': datetime.utcnow().isoformat(),
            'database': query_stats,
            'api': api_stats,
            'cache': cache_stats,
            'system': system_stats
        }
    
    def _calculate_query_stats(self, metrics: List[QueryMetrics]) -> Dict[str, Any]:
        """쿼리 통계 계산"""
        if not metrics:
            return {}
        
        total_queries = len(metrics)
        successful_queries = sum(1 for m in metrics if m.success)
        avg_duration = sum(m.duration_ms for m in metrics) / total_queries
        
        # 쿼리 타입별 통계
        by_type = defaultdict(list)
        for m in metrics:
            by_type[m.query_type].append(m)
        
        type_stats = {}
        for query_type, type_metrics in by_type.items():
            type_stats[query_type] = {
                'count': len(type_metrics),
                'avg_duration_ms': sum(m.duration_ms for m in type_metrics) / len(type_metrics),
                'max_duration_ms': max(m.duration_ms for m in type_metrics),
                'success_rate': sum(1 for m in type_metrics if m.success) / len(type_metrics) * 100
            }
        
        return {
            'total_queries': total_queries,
            'success_rate': (successful_queries / total_queries * 100) if total_queries > 0 else 0,
            'avg_duration_ms': avg_duration,
            'by_type': type_stats
        }
    
    def _calculate_api_stats(self, metrics: List[APIMetrics]) -> Dict[str, Any]:
        """API 통계 계산"""
        if not metrics:
            return {}
        
        total_requests = len(metrics)
        successful_requests = sum(1 for m in metrics if m.status_code < 400)
        avg_duration = sum(m.duration_ms for m in metrics) / total_requests
        
        # 엔드포인트별 통계
        by_endpoint = defaultdict(list)
        for m in metrics:
            endpoint_key = f"{m.method} {m.endpoint}"
            by_endpoint[endpoint_key].append(m)
        
        endpoint_stats = {}
        for endpoint, endpoint_metrics in by_endpoint.items():
            endpoint_stats[endpoint] = {
                'count': len(endpoint_metrics),
                'avg_duration_ms': sum(m.duration_ms for m in endpoint_metrics) / len(endpoint_metrics),
                'max_duration_ms': max(m.duration_ms for m in endpoint_metrics),
                'success_rate': sum(1 for m in endpoint_metrics if m.status_code < 400) / len(endpoint_metrics) * 100
            }
        
        # 상태 코드별 분포
        status_codes = defaultdict(int)
        for m in metrics:
            status_codes[str(m.status_code)] += 1
        
        return {
            'total_requests': total_requests,
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'avg_duration_ms': avg_duration,
            'by_endpoint': endpoint_stats,
            'status_codes': dict(status_codes)
        }
    
    def _calculate_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 계산"""
        cache_stats = {}
        
        for cache_key, hit_history in self.current_stats['cache_hit_rates'].items():
            if hit_history:
                hit_rate = sum(hit_history) / len(hit_history) * 100
                cache_stats[cache_key] = {
                    'hit_rate': hit_rate,
                    'total_operations': len(hit_history)
                }
        
        return cache_stats
    
    def _get_latest_system_stats(self) -> Dict[str, Any]:
        """최신 시스템 통계 조회"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        
        recent_metrics = [
            m for m in self.metrics 
            if m.timestamp >= cutoff_time and m.name.startswith('system_')
        ]
        
        if not recent_metrics:
            return {}
        
        # 최신 값 추출
        latest_values = {}
        for metric in recent_metrics:
            if metric.name not in latest_values or metric.timestamp > latest_values[metric.name]['timestamp']:
                latest_values[metric.name] = {
                    'value': metric.value,
                    'timestamp': metric.timestamp
                }
        
        return {
            name: data['value'] 
            for name, data in latest_values.items()
        }
    
    async def get_database_performance(self, session: AsyncSession) -> Dict[str, Any]:
        """데이터베이스 성능 상세 조회"""
        try:
            # PostgreSQL 통계 쿼리
            stats_query = text("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
            """)
            
            result = await session.execute(stats_query)
            table_stats = []
            
            for row in result:
                table_stats.append({
                    'table_name': row.tablename,
                    'inserts': row.inserts,
                    'updates': row.updates,
                    'deletes': row.deletes,
                    'live_tuples': row.live_tuples,
                    'dead_tuples': row.dead_tuples,
                    'last_vacuum': row.last_vacuum.isoformat() if row.last_vacuum else None,
                    'last_analyze': row.last_analyze.isoformat() if row.last_analyze else None
                })
            
            # 인덱스 사용 통계
            index_query = text("""
                SELECT 
                    indexrelname as index_name,
                    relname as table_name,
                    idx_scan as scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
                LIMIT 20
            """)
            
            index_result = await session.execute(index_query)
            index_stats = []
            
            for row in index_result:
                index_stats.append({
                    'index_name': row.index_name,
                    'table_name': row.table_name,
                    'scans': row.scans,
                    'tuples_read': row.tuples_read,
                    'tuples_fetched': row.tuples_fetched
                })
            
            return {
                'table_statistics': table_stats,
                'index_statistics': index_stats,
                'query_metrics': self._calculate_query_stats(list(self.query_metrics)[-100:])  # 최근 100개
            }
            
        except Exception as e:
            logger.error(f"데이터베이스 성능 조회 실패: {str(e)}")
            return {'error': str(e)}


# 전역 성능 모니터 인스턴스
performance_monitor = PerformanceMonitor()


# 데코레이터들
def track_query_performance(query_type: str):
    """쿼리 성능 추적 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with performance_monitor.track_query(query_type):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def track_api_performance(endpoint: str, method: str):
    """API 성능 추적 데코레이터"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # user_id 추출 시도
            user_id = None
            for arg in args:
                if hasattr(arg, 'id'):
                    user_id = str(arg.id)
                    break
            
            async with performance_monitor.track_api_request(endpoint, method, user_id):
                return await func(*args, **kwargs)
        return wrapper
    return decorator