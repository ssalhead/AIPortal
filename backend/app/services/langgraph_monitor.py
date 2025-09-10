"""
LangGraph 모니터링 시스템 - Legacy vs LangGraph 성능 비교 및 추적
"""

import time
import json
import asyncio
import statistics
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """에이전트 유형"""
    LEGACY = "legacy"
    LANGGRAPH = "langgraph"


class ExecutionStatus(Enum):
    """실행 상태"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    FALLBACK = "fallback"


@dataclass
class ExecutionMetric:
    """실행 메트릭 데이터 클래스"""
    agent_type: AgentType
    agent_name: str
    execution_time: float
    memory_usage: Optional[float]
    status: ExecutionStatus
    user_id: Optional[str]
    query: str
    response_length: int
    timestamp: datetime
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PerformanceReport:
    """성능 리포트 데이터 클래스"""
    period_start: datetime
    period_end: datetime
    legacy_metrics: Dict[str, Any]
    langgraph_metrics: Dict[str, Any]
    comparison: Dict[str, Any]
    recommendations: List[str]


class LangGraphMonitor:
    """LangGraph vs Legacy 성능 모니터링 시스템"""
    
    def __init__(self):
        """모니터링 시스템 초기화"""
        
        # 메트릭 저장소 (메모리 기반, 실제 환경에서는 DB 저장 권장)
        self.execution_metrics: List[ExecutionMetric] = []
        
        # 성능 임계값 설정
        self.performance_thresholds = {
            "response_time_warning": 5.0,     # 5초 이상 경고
            "response_time_critical": 10.0,   # 10초 이상 심각
            "error_rate_warning": 0.05,       # 5% 이상 경고
            "error_rate_critical": 0.10,      # 10% 이상 심각
            "memory_usage_warning": 512,      # 512MB 이상 경고
            "fallback_rate_warning": 0.02     # 2% 이상 fallback 경고
        }
        
        # 실시간 메트릭 (최근 1시간)
        self.realtime_window = timedelta(hours=1)
        
        # 성능 비교 리포트 캐시
        self.report_cache = {}
        self.cache_ttl = timedelta(minutes=5)
        
        # 성능 최적화 연동
        self.optimization_enabled = True
        self.performance_optimizer = None  # 순환 import 방지를 위해 지연 로딩
        
        logger.info("🔍 LangGraph 모니터링 시스템 초기화 완료")
    
    async def start_execution(self, agent_name: str) -> Dict[str, Any]:
        """
        에이전트 실행 시작 추적
        
        Args:
            agent_name: 에이전트 이름
            
        Returns:
            시작 컨텍스트 정보
        """
        start_time = time.time()
        context = {
            "agent_name": agent_name,
            "start_time": start_time,
            "timestamp": datetime.now()
        }
        logger.debug(f"🚀 {agent_name} 실행 시작 추적")
        return context
    
    async def track_execution(
        self,
        agent_type: AgentType,
        agent_name: str,
        execution_time: float,
        status: ExecutionStatus,
        query: str,
        response_length: int,
        user_id: Optional[str] = None,
        memory_usage: Optional[float] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs  # 호환성을 위한 추가 인수 지원
    ) -> None:
        """
        에이전트 실행 메트릭 추적
        
        Args:
            agent_type: 에이전트 유형 (Legacy/LangGraph)
            agent_name: 에이전트 이름
            execution_time: 실행 시간 (초)
            status: 실행 상태
            query: 사용자 쿼리
            response_length: 응답 길이
            user_id: 사용자 ID
            memory_usage: 메모리 사용량 (MB)
            error_message: 에러 메시지
            metadata: 추가 메타데이터
        """
        
        metric = ExecutionMetric(
            agent_type=agent_type,
            agent_name=agent_name,
            execution_time=execution_time,
            memory_usage=memory_usage,
            status=status,
            user_id=user_id,
            query=query[:100],  # 쿼리는 100자까지만 저장
            response_length=response_length,
            timestamp=datetime.now(),
            error_message=error_message,
            metadata=metadata or {}
        )
        
        # 메트릭 저장
        self.execution_metrics.append(metric)
        
        # 임계값 확인 및 알람
        await self._check_thresholds(metric)
        
        # 메모리 관리 (최근 24시간 데이터만 유지)
        self._cleanup_old_metrics()
        
        logger.debug(f"📊 메트릭 추가: {agent_type.value} {agent_name} - {execution_time:.2f}s ({status.value})")
    
    async def _check_thresholds(self, metric: ExecutionMetric) -> None:
        """성능 임계값 확인 및 알람"""
        
        alerts = []
        
        # 응답 시간 확인
        if metric.execution_time > self.performance_thresholds["response_time_critical"]:
            alerts.append(f"🚨 CRITICAL: {metric.agent_name} 응답 시간 {metric.execution_time:.2f}s (임계값: {self.performance_thresholds['response_time_critical']}s)")
        elif metric.execution_time > self.performance_thresholds["response_time_warning"]:
            alerts.append(f"⚠️ WARNING: {metric.agent_name} 응답 시간 {metric.execution_time:.2f}s (경고값: {self.performance_thresholds['response_time_warning']}s)")
        
        # 메모리 사용량 확인
        if metric.memory_usage and metric.memory_usage > self.performance_thresholds["memory_usage_warning"]:
            alerts.append(f"⚠️ WARNING: {metric.agent_name} 메모리 사용량 {metric.memory_usage:.1f}MB")
        
        # 에러 상태 확인
        if metric.status == ExecutionStatus.ERROR:
            alerts.append(f"❌ ERROR: {metric.agent_name} 실행 실패 - {metric.error_message}")
        elif metric.status == ExecutionStatus.FALLBACK:
            alerts.append(f"🔄 FALLBACK: {metric.agent_name} Legacy로 fallback")
        
        # 알람 발송
        for alert in alerts:
            logger.warning(alert)
            # 실제 환경에서는 Slack, 이메일 등으로 알람 발송
    
    def _cleanup_old_metrics(self) -> None:
        """오래된 메트릭 데이터 정리 (24시간 이상)"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        original_count = len(self.execution_metrics)
        
        self.execution_metrics = [
            metric for metric in self.execution_metrics
            if metric.timestamp > cutoff_time
        ]
        
        removed_count = original_count - len(self.execution_metrics)
        if removed_count > 0:
            logger.debug(f"🧹 오래된 메트릭 {removed_count}개 정리 완료")
    
    async def get_realtime_metrics(self) -> Dict[str, Any]:
        """실시간 성능 메트릭 조회 (최근 1시간)"""
        
        cutoff_time = datetime.now() - self.realtime_window
        recent_metrics = [
            metric for metric in self.execution_metrics
            if metric.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {
                "status": "no_data",
                "message": "최근 1시간 내 실행 데이터가 없습니다",
                "timestamp": datetime.now().isoformat()
            }
        
        # Legacy vs LangGraph 분리
        legacy_metrics = [m for m in recent_metrics if m.agent_type == AgentType.LEGACY]
        langgraph_metrics = [m for m in recent_metrics if m.agent_type == AgentType.LANGGRAPH]
        
        return {
            "period": {
                "start": cutoff_time.isoformat(),
                "end": datetime.now().isoformat(),
                "duration_minutes": 60
            },
            "summary": {
                "total_executions": len(recent_metrics),
                "legacy_executions": len(legacy_metrics),
                "langgraph_executions": len(langgraph_metrics),
                "langgraph_adoption_rate": len(langgraph_metrics) / len(recent_metrics) * 100 if recent_metrics else 0
            },
            "legacy": self._calculate_agent_metrics(legacy_metrics),
            "langgraph": self._calculate_agent_metrics(langgraph_metrics),
            "comparison": self._compare_metrics(legacy_metrics, langgraph_metrics),
            "timestamp": datetime.now().isoformat()
        }
    
    def _calculate_agent_metrics(self, metrics: List[ExecutionMetric]) -> Dict[str, Any]:
        """특정 에이전트 유형의 메트릭 계산"""
        
        if not metrics:
            return {
                "execution_count": 0,
                "avg_response_time": 0,
                "success_rate": 0,
                "error_rate": 0,
                "fallback_rate": 0
            }
        
        # 실행 시간 통계
        execution_times = [m.execution_time for m in metrics]
        
        # 상태별 카운트
        success_count = len([m for m in metrics if m.status == ExecutionStatus.SUCCESS])
        error_count = len([m for m in metrics if m.status == ExecutionStatus.ERROR])
        fallback_count = len([m for m in metrics if m.status == ExecutionStatus.FALLBACK])
        
        # 메모리 사용량 통계
        memory_usages = [m.memory_usage for m in metrics if m.memory_usage is not None]
        
        return {
            "execution_count": len(metrics),
            "avg_response_time": statistics.mean(execution_times),
            "median_response_time": statistics.median(execution_times),
            "p95_response_time": self._percentile(execution_times, 95),
            "min_response_time": min(execution_times),
            "max_response_time": max(execution_times),
            "success_rate": success_count / len(metrics) * 100,
            "error_rate": error_count / len(metrics) * 100,
            "fallback_rate": fallback_count / len(metrics) * 100,
            "avg_memory_usage": statistics.mean(memory_usages) if memory_usages else None,
            "avg_response_length": statistics.mean([m.response_length for m in metrics])
        }
    
    def _compare_metrics(self, legacy_metrics: List[ExecutionMetric], langgraph_metrics: List[ExecutionMetric]) -> Dict[str, Any]:
        """Legacy vs LangGraph 메트릭 비교"""
        
        if not legacy_metrics or not langgraph_metrics:
            return {"status": "insufficient_data"}
        
        legacy_stats = self._calculate_agent_metrics(legacy_metrics)
        langgraph_stats = self._calculate_agent_metrics(langgraph_metrics)
        
        # 성능 개선율 계산
        response_time_improvement = self._calculate_improvement(
            legacy_stats["avg_response_time"],
            langgraph_stats["avg_response_time"],
            lower_is_better=True
        )
        
        success_rate_improvement = self._calculate_improvement(
            legacy_stats["success_rate"],
            langgraph_stats["success_rate"],
            lower_is_better=False
        )
        
        return {
            "response_time": {
                "legacy_avg": legacy_stats["avg_response_time"],
                "langgraph_avg": langgraph_stats["avg_response_time"],
                "improvement_percent": response_time_improvement,
                "winner": "langgraph" if response_time_improvement > 0 else "legacy"
            },
            "success_rate": {
                "legacy": legacy_stats["success_rate"],
                "langgraph": langgraph_stats["success_rate"],
                "improvement_percent": success_rate_improvement,
                "winner": "langgraph" if success_rate_improvement > 0 else "legacy"
            },
            "error_rate": {
                "legacy": legacy_stats["error_rate"],
                "langgraph": langgraph_stats["error_rate"],
                "winner": "langgraph" if langgraph_stats["error_rate"] < legacy_stats["error_rate"] else "legacy"
            },
            "overall_recommendation": self._get_overall_recommendation(legacy_stats, langgraph_stats)
        }
    
    def _calculate_improvement(self, baseline: float, new_value: float, lower_is_better: bool = True) -> float:
        """성능 개선율 계산"""
        
        if baseline == 0:
            return 0
        
        if lower_is_better:
            # 낮을수록 좋은 지표 (응답 시간, 에러율 등)
            improvement = (baseline - new_value) / baseline * 100
        else:
            # 높을수록 좋은 지표 (성공률 등)
            improvement = (new_value - baseline) / baseline * 100
        
        return round(improvement, 2)
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """백분위수 계산"""
        if not data:
            return 0
        
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _get_overall_recommendation(self, legacy_stats: Dict[str, Any], langgraph_stats: Dict[str, Any]) -> str:
        """전반적인 권장사항 생성"""
        
        recommendations = []
        
        # 응답 시간 비교
        if langgraph_stats["avg_response_time"] < legacy_stats["avg_response_time"]:
            improvement = self._calculate_improvement(
                legacy_stats["avg_response_time"],
                langgraph_stats["avg_response_time"],
                lower_is_better=True
            )
            recommendations.append(f"LangGraph가 응답 시간 {improvement:.1f}% 개선")
        
        # 성공률 비교
        if langgraph_stats["success_rate"] > legacy_stats["success_rate"]:
            recommendations.append("LangGraph의 성공률이 더 높음")
        
        # 에러율 비교
        if langgraph_stats["error_rate"] < legacy_stats["error_rate"]:
            recommendations.append("LangGraph의 에러율이 더 낮음")
        
        # Fallback 비율 확인
        if langgraph_stats["fallback_rate"] > 5:
            recommendations.append("⚠️ LangGraph fallback 비율이 높음 - 안정성 점검 필요")
        
        if not recommendations:
            return "성능상 큰 차이 없음 - 추가 데이터 수집 필요"
        
        return " | ".join(recommendations)
    
    async def get_daily_report(self, date: Optional[datetime] = None) -> PerformanceReport:
        """일일 성능 리포트 생성"""
        
        if date is None:
            date = datetime.now().date()
        
        # 캐시 확인
        cache_key = f"daily_report_{date.isoformat()}"
        if cache_key in self.report_cache:
            cached_report, cache_time = self.report_cache[cache_key]
            if datetime.now() - cache_time < self.cache_ttl:
                return cached_report
        
        # 해당 날짜의 메트릭 필터링
        start_time = datetime.combine(date, datetime.min.time())
        end_time = start_time + timedelta(days=1)
        
        daily_metrics = [
            metric for metric in self.execution_metrics
            if start_time <= metric.timestamp < end_time
        ]
        
        if not daily_metrics:
            return PerformanceReport(
                period_start=start_time,
                period_end=end_time,
                legacy_metrics={},
                langgraph_metrics={},
                comparison={},
                recommendations=["해당 날짜에 실행 데이터가 없습니다"]
            )
        
        # Legacy vs LangGraph 분리
        legacy_metrics = [m for m in daily_metrics if m.agent_type == AgentType.LEGACY]
        langgraph_metrics = [m for m in daily_metrics if m.agent_type == AgentType.LANGGRAPH]
        
        # 리포트 생성
        report = PerformanceReport(
            period_start=start_time,
            period_end=end_time,
            legacy_metrics=self._calculate_agent_metrics(legacy_metrics),
            langgraph_metrics=self._calculate_agent_metrics(langgraph_metrics),
            comparison=self._compare_metrics(legacy_metrics, langgraph_metrics),
            recommendations=self._generate_recommendations(legacy_metrics, langgraph_metrics)
        )
        
        # 캐시 저장
        self.report_cache[cache_key] = (report, datetime.now())
        
        return report
    
    def _generate_recommendations(self, legacy_metrics: List[ExecutionMetric], langgraph_metrics: List[ExecutionMetric]) -> List[str]:
        """개선 권장사항 생성"""
        
        recommendations = []
        
        if not langgraph_metrics:
            recommendations.append("LangGraph 활용률이 낮습니다. Feature Flag 비율을 높여보세요.")
            return recommendations
        
        if not legacy_metrics:
            recommendations.append("Legacy 메트릭이 없어 비교가 어렵습니다.")
            return recommendations
        
        legacy_stats = self._calculate_agent_metrics(legacy_metrics)
        langgraph_stats = self._calculate_agent_metrics(langgraph_metrics)
        
        # 성능 기반 권장사항
        if langgraph_stats["avg_response_time"] < legacy_stats["avg_response_time"]:
            improvement = self._calculate_improvement(
                legacy_stats["avg_response_time"],
                langgraph_stats["avg_response_time"],
                lower_is_better=True
            )
            if improvement > 20:
                recommendations.append(f"🚀 LangGraph 성능이 {improvement:.1f}% 우수함 - Feature Flag 비율 증가 권장")
            else:
                recommendations.append(f"✅ LangGraph 성능이 {improvement:.1f}% 개선됨")
        
        # 안정성 기반 권장사항
        if langgraph_stats["error_rate"] > legacy_stats["error_rate"]:
            recommendations.append("⚠️ LangGraph 에러율이 높음 - 안정성 개선 필요")
        
        if langgraph_stats["fallback_rate"] > 5:
            recommendations.append("🔄 Fallback 비율이 높음 - LangGraph 안정성 점검 필요")
        
        # 트래픽 기반 권장사항
        total_executions = len(legacy_metrics) + len(langgraph_metrics)
        langgraph_ratio = len(langgraph_metrics) / total_executions * 100
        
        if langgraph_ratio < 10:
            recommendations.append("📈 LangGraph 트래픽 비율이 낮음 - 점진적 증가 고려")
        elif langgraph_ratio > 50:
            recommendations.append("🎯 LangGraph 활용률이 높음 - 완전 전환 준비 검토")
        
        return recommendations
    
    async def export_metrics(self, format: str = "json", period_hours: int = 24) -> str:
        """메트릭 데이터 내보내기"""
        
        cutoff_time = datetime.now() - timedelta(hours=period_hours)
        export_metrics = [
            metric for metric in self.execution_metrics
            if metric.timestamp > cutoff_time
        ]
        
        if format == "json":
            return json.dumps([asdict(metric) for metric in export_metrics], default=str, indent=2)
        elif format == "csv":
            # CSV 형태로 변환 (간단 구현)
            lines = ["timestamp,agent_type,agent_name,execution_time,status,response_length"]
            for metric in export_metrics:
                lines.append(f"{metric.timestamp},{metric.agent_type.value},{metric.agent_name},{metric.execution_time},{metric.status.value},{metric.response_length}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _get_performance_optimizer(self):
        """성능 최적화 인스턴스 지연 로딩"""
        if self.performance_optimizer is None and self.optimization_enabled:
            try:
                from app.services.performance_optimizer import performance_optimizer
                self.performance_optimizer = performance_optimizer
            except ImportError:
                logger.warning("성능 최적화 모듈을 찾을 수 없음")
                self.optimization_enabled = False
        return self.performance_optimizer
    
    async def trigger_performance_analysis(self):
        """성능 분석 트리거"""
        optimizer = self._get_performance_optimizer()
        if optimizer:
            try:
                report = optimizer.get_performance_report()
                
                # 심각한 성능 문제 감지 시 알림
                if report.get("performance_level") in ["critical", "poor"]:
                    logger.warning(f"성능 문제 감지: {report.get('performance_level')} - 점수: {report.get('performance_score')}")
                    
                    # 자동 최적화 권장사항 생성
                    recommendations = report.get("recommendations", [])
                    if recommendations:
                        logger.info(f"자동 최적화 권장사항: {', '.join(recommendations)}")
                
                return report
            except Exception as e:
                logger.error(f"성능 분석 실행 실패: {e}")
        return None
    
    async def get_comprehensive_report(self) -> Dict[str, Any]:
        """LangGraph 모니터링 + 성능 최적화 통합 리포트"""
        
        # 기본 모니터링 데이터
        monitoring_report = await self.get_realtime_metrics()
        
        # 성능 최적화 데이터
        performance_report = await self.trigger_performance_analysis()
        
        # 통합 리포트 구성
        comprehensive_report = {
            "timestamp": datetime.now().isoformat(),
            "monitoring": monitoring_report,
            "performance": performance_report or {"status": "optimizer_unavailable"},
            "system_health": self._assess_system_health(monitoring_report, performance_report),
            "recommendations": self._generate_comprehensive_recommendations(monitoring_report, performance_report)
        }
        
        return comprehensive_report
    
    def _assess_system_health(self, monitoring_report: Dict[str, Any], performance_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """시스템 전체 건강도 평가"""
        
        health_score = 100
        issues = []
        
        # 모니터링 데이터 기반 평가
        if monitoring_report.get("status") != "no_data":
            langgraph_metrics = monitoring_report.get("langgraph", {})
            
            # 에러율 확인
            error_rate = langgraph_metrics.get("error_rate", 0)
            if error_rate > 0.1:  # 10% 이상
                health_score -= 30
                issues.append("높은 에러율 감지")
            elif error_rate > 0.05:  # 5% 이상
                health_score -= 15
                issues.append("에러율 주의 필요")
            
            # 응답시간 확인
            avg_response_time = langgraph_metrics.get("avg_response_time", 0)
            if avg_response_time > 10:  # 10초 이상
                health_score -= 25
                issues.append("응답시간 심각")
            elif avg_response_time > 5:  # 5초 이상
                health_score -= 10
                issues.append("응답시간 느림")
        
        # 성능 최적화 데이터 기반 평가
        if performance_report:
            performance_level = performance_report.get("performance_level")
            if performance_level == "critical":
                health_score -= 40
                issues.append("시스템 성능 위험")
            elif performance_level == "poor":
                health_score -= 20
                issues.append("시스템 성능 저하")
            elif performance_level == "moderate":
                health_score -= 10
                issues.append("성능 개선 여지")
        
        # 건강도 등급 결정
        if health_score >= 90:
            health_grade = "excellent"
        elif health_score >= 70:
            health_grade = "good"
        elif health_score >= 50:
            health_grade = "moderate"
        elif health_score >= 30:
            health_grade = "poor"
        else:
            health_grade = "critical"
        
        return {
            "health_score": max(0, health_score),
            "health_grade": health_grade,
            "issues": issues,
            "status": "healthy" if health_score >= 70 else "attention_needed"
        }
    
    def _generate_comprehensive_recommendations(self, monitoring_report: Dict[str, Any], performance_report: Optional[Dict[str, Any]]) -> List[str]:
        """통합 권장사항 생성"""
        
        recommendations = []
        
        # 모니터링 기반 권장사항
        if monitoring_report.get("status") != "no_data":
            comparison = monitoring_report.get("comparison", {})
            if comparison.get("performance_improvement", 0) < 0:
                recommendations.append("LangGraph 성능이 Legacy보다 낮음 - 최적화 필요")
            
            langgraph_metrics = monitoring_report.get("langgraph", {})
            if langgraph_metrics.get("error_rate", 0) > 0.05:
                recommendations.append("LangGraph 에러율 개선 필요")
        
        # 성능 최적화 기반 권장사항
        if performance_report:
            perf_recommendations = performance_report.get("recommendations", [])
            recommendations.extend(perf_recommendations)
        
        # 기본 권장사항
        if not recommendations:
            recommendations.append("현재 시스템이 안정적으로 운영 중입니다")
        
        return recommendations


# 전역 모니터링 인스턴스
langgraph_monitor = LangGraphMonitor()


# 편의 함수들
async def track_legacy_execution(agent_name: str, execution_time: float, status: ExecutionStatus, query: str, response_length: int, **kwargs):
    """Legacy 에이전트 실행 추적"""
    await langgraph_monitor.track_execution(
        agent_type=AgentType.LEGACY,
        agent_name=agent_name,
        execution_time=execution_time,
        status=status,
        query=query,
        response_length=response_length,
        **kwargs
    )


async def track_langgraph_execution(agent_name: str, execution_time: float, status: ExecutionStatus, query: str, response_length: int, **kwargs):
    """LangGraph 에이전트 실행 추적"""
    await langgraph_monitor.track_execution(
        agent_type=AgentType.LANGGRAPH,
        agent_name=agent_name,
        execution_time=execution_time,
        status=status,
        query=query,
        response_length=response_length,
        **kwargs
    )


class PerformanceTracker:
    """성능 추적을 위한 컨텍스트 매니저"""
    
    def __init__(self, agent_type: AgentType, agent_name: str, query: str, user_id: Optional[str] = None):
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.query = query
        self.user_id = user_id
        self.start_time = None
        self.response_length = 0
        self.error_message = None
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        execution_time = time.time() - self.start_time
        
        if exc_type is None:
            status = ExecutionStatus.SUCCESS
        else:
            status = ExecutionStatus.ERROR
            self.error_message = str(exc_val)
        
        await langgraph_monitor.track_execution(
            agent_type=self.agent_type,
            agent_name=self.agent_name,
            execution_time=execution_time,
            status=status,
            query=self.query,
            response_length=self.response_length,
            user_id=self.user_id,
            error_message=self.error_message
        )
    
    def set_response_length(self, length: int):
        """응답 길이 설정"""
        self.response_length = length