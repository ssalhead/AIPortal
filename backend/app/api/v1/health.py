"""
헬스 체크 API
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    헬스 체크 엔드포인트
    
    Returns:
        서버 상태 정보
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "project": settings.PROJECT_NAME,
        "mock_auth_enabled": settings.MOCK_AUTH_ENABLED
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    상세 헬스 체크 엔드포인트
    
    Returns:
        상세한 서버 상태 정보
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "project": settings.PROJECT_NAME,
        "configuration": {
            "mock_auth_enabled": settings.MOCK_AUTH_ENABLED,
            "cors_origins": [str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            "debug": settings.DEBUG,
            "log_level": settings.LOG_LEVEL
        },
        "services": {
            "database": "not_configured",  # 추후 실제 DB 연결 상태 확인
            "redis": "not_configured",     # 추후 실제 Redis 연결 상태 확인
            "opensearch": "not_configured" # 추후 실제 OpenSearch 연결 상태 확인
        }
    }