"""
지능형 라우팅 시스템 성능 모니터링 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging

from app.agents.supervisor import supervisor_agent
from app.agents.routing.intent_classifier import dynamic_intent_classifier

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/performance/report", 
           summary="라우팅 성능 리포트",
           description="지능형 라우팅 시스템의 종합 성능 보고서를 제공합니다")
async def get_routing_performance_report() -> Dict[str, Any]:
    """
    지능형 라우팅 시스템의 성능 리포트를 반환합니다.
    
    Returns:
        - 분류 정확도
        - 응답 시간 통계  
        - 사용자 피드백 데이터
        - 에이전트별 사용 통계
        - 시스템 상태
    """
    try:
        # Supervisor 성능 리포트
        supervisor_report = supervisor_agent.get_performance_report()
        
        # Intent Classifier 성능 리포트  
        classifier_report = dynamic_intent_classifier.get_performance_report()
        
        # 통합 리포트 생성
        integrated_report = {
            "system_status": "active",
            "routing_version": "v2_intelligent",
            "timestamp": "2025-09-02T10:13:00Z",
            
            # 전체 시스템 메트릭
            "overall_metrics": {
                "total_classifications": classifier_report.get("total_classifications", 0),
                "accuracy_rate": classifier_report.get("accuracy", 0.0),
                "high_confidence_rate": classifier_report.get("high_confidence_rate", 0.0),
                "correction_count": classifier_report.get("correction_count", 0),
                "users_tracked": classifier_report.get("users_tracked", 0)
            },
            
            # 에이전트 성능
            "agent_performance": {
                "available_agents": supervisor_report.get("available_workers", 0),
                "supported_intents": supervisor_report.get("supported_intents", []),
                "current_strategy": classifier_report.get("current_strategy", "context_aware")
            },
            
            # 최근 활동
            "recent_activity": {
                "recent_classifications": classifier_report.get("recent_classifications", []),
                "system_capabilities": supervisor_report.get("capabilities", [])
            }
        }
        
        return integrated_report
        
    except Exception as e:
        logger.error(f"성능 리포트 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"성능 리포트 생성 중 오류: {str(e)}")


@router.get("/performance/classification-stats",
           summary="분류 통계",
           description="의도 분류기의 상세 통계를 제공합니다")
async def get_classification_statistics(
    limit: int = Query(default=50, ge=1, le=1000, description="최근 분류 기록 개수")
) -> Dict[str, Any]:
    """
    의도 분류기의 상세 통계를 반환합니다.
    
    Args:
        limit: 최근 분류 기록 조회 개수 (1-1000)
        
    Returns:
        분류 정확도, 신뢰도 분포, 패턴 분석 결과
    """
    try:
        # 분류기 통계 조회
        stats = dynamic_intent_classifier.get_performance_report()
        
        # 최근 분류 기록 필터링
        recent_classifications = stats.get("recent_classifications", [])
        if len(recent_classifications) > limit:
            recent_classifications = recent_classifications[-limit:]
        
        return {
            "classification_statistics": {
                "total_count": stats.get("total_classifications", 0),
                "accuracy_rate": stats.get("accuracy", 0.0),
                "high_confidence_rate": stats.get("high_confidence_rate", 0.0),
                "correction_count": stats.get("correction_count", 0),
            },
            "recent_classifications": recent_classifications,
            "strategy_info": {
                "current_strategy": stats.get("current_strategy", "context_aware"),
                "available_strategies": ["base", "context_aware", "pattern_enhanced"]
            }
        }
        
    except Exception as e:
        logger.error(f"분류 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류: {str(e)}")


@router.post("/feedback/correction", 
            summary="사용자 피드백 기록",
            description="잘못된 분류에 대한 사용자 수정 사항을 기록하여 시스템을 개선합니다")
async def record_classification_correction(
    user_id: str,
    query: str, 
    original_intent: str,
    correct_intent: str
) -> Dict[str, Any]:
    """
    사용자의 분류 수정 사항을 기록합니다.
    
    Args:
        user_id: 사용자 ID
        query: 원본 사용자 질문
        original_intent: 시스템이 분류한 의도
        correct_intent: 올바른 의도
        
    Returns:
        피드백 기록 완료 상태
    """
    try:
        # Supervisor에 피드백 기록
        await supervisor_agent.record_user_correction(
            user_id=user_id,
            original_intent=original_intent, 
            correct_intent=correct_intent,
            query=query
        )
        
        return {
            "status": "success",
            "message": "피드백이 성공적으로 기록되었습니다",
            "feedback_data": {
                "user_id": user_id,
                "original_intent": original_intent,
                "correct_intent": correct_intent,
                "query": query[:100] + "..." if len(query) > 100 else query
            }
        }
        
    except Exception as e:
        logger.error(f"피드백 기록 실패: {e}")
        raise HTTPException(status_code=500, detail=f"피드백 기록 중 오류: {str(e)}")


@router.get("/health",
           summary="라우팅 시스템 상태 확인", 
           description="라우팅 시스템의 기본 상태와 가용성을 확인합니다")
async def get_routing_health() -> Dict[str, Any]:
    """
    라우팅 시스템의 상태를 확인합니다.
    
    Returns:
        시스템 상태, 버전 정보, 기본 통계
    """
    try:
        # 기본 상태 확인
        supervisor_report = supervisor_agent.get_performance_report()
        
        is_healthy = (
            supervisor_report.get("status") == "active" and
            len(supervisor_report.get("supported_intents", [])) > 0
        )
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "version": "v2_intelligent", 
            "uptime": "running",
            "components": {
                "supervisor": supervisor_report.get("status", "unknown"),
                "intent_classifier": "active",
                "available_workers": supervisor_report.get("available_workers", 0)
            },
            "supported_intents": supervisor_report.get("supported_intents", []),
            "timestamp": "2025-09-02T10:13:00Z"
        }
        
    except Exception as e:
        logger.error(f"상태 확인 실패: {e}")
        return {
            "status": "error",
            "version": "v2_intelligent",
            "error": str(e),
            "timestamp": "2025-09-02T10:13:00Z"
        }


@router.get("/debug/classification-trace",
           summary="분류 과정 추적 (디버그용)",
           description="특정 질문에 대한 분류 과정을 상세히 추적합니다 (개발/디버그 전용)")
async def trace_classification_process(
    query: str = Query(..., description="분류를 테스트할 질문"),
    user_id: str = Query(default="debug-user", description="테스트 사용자 ID"),
    model: str = Query(default="claude-sonnet", description="사용할 LLM 모델")
) -> Dict[str, Any]:
    """
    특정 질문에 대한 분류 과정을 상세히 추적합니다.
    개발 및 디버깅 목적으로 사용됩니다.
    
    Args:
        query: 테스트할 사용자 질문
        user_id: 테스트 사용자 ID
        model: 사용할 LLM 모델명
        
    Returns:
        분류 과정의 상세한 추적 결과
    """
    try:
        from app.agents.base import AgentInput
        
        # 테스트용 입력 데이터 생성
        test_input = AgentInput(
            query=query,
            user_id=user_id,
            context={}
        )
        
        # Intent Classifier에서 분류 실행 (추적 모드)
        result = await dynamic_intent_classifier.execute(test_input, model)
        
        # 결과 파싱
        import json
        classification_data = json.loads(result.result)
        
        return {
            "debug_info": {
                "query": query,
                "user_id": user_id,
                "model_used": model,
                "timestamp": result.timestamp
            },
            "classification_result": classification_data,
            "metadata": result.metadata,
            "execution_time_ms": result.execution_time_ms
        }
        
    except Exception as e:
        logger.error(f"분류 추적 실패: {e}")
        raise HTTPException(status_code=500, detail=f"분류 추적 중 오류: {str(e)}")


# 라우터를 메인 API에 포함시킬 때 사용할 태그
router.tags = ["Intelligent Routing"]