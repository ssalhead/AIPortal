"""
AI 포탈 메인 FastAPI 애플리케이션
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging
import sys
import time

from app.core.config import settings
from app.core.exceptions import AIPortalException
from app.core.exception_handlers import (
    aiportal_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    starlette_http_exception_handler
)
from app.core.responses import create_health_response
from app.middleware.logging_middleware import LoggingMiddleware, SecurityMiddleware
from app.services.logging_service import logging_service

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 서버 시작 시간 기록
server_start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 애플리케이션 시작 시
    logger.info("🚀 AI 포탈 백엔드 서버가 시작됩니다...")
    logger.info(f"환경: {settings.ENVIRONMENT}")
    logger.info(f"디버그 모드: {settings.DEBUG}")
    logger.info(f"Mock 인증: {settings.MOCK_AUTH_ENABLED}")
    
    # 서버 시작 이벤트 로깅
    logging_service.log_security_event(
        event_type="server_startup",
        description="AI 포탈 서버 시작",
        severity="INFO",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT
    )
    
    yield
    
    # 애플리케이션 종료 시
    logger.info("🛑 AI 포탈 백엔드 서버가 종료됩니다...")
    
    # 서버 종료 이벤트 로깅
    uptime = time.time() - server_start_time
    logging_service.log_security_event(
        event_type="server_shutdown",
        description="AI 포탈 서버 종료",
        severity="INFO",
        uptime=uptime
    )


# FastAPI 애플리케이션 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="차세대 지능형 내부 자동화 플랫폼",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# 미들웨어 추가 (순서 중요!)
# 1. 로깅 미들웨어 (가장 먼저)
app.add_middleware(LoggingMiddleware)

# 2. 보안 미들웨어
app.add_middleware(SecurityMiddleware)

# 3. CORS 미들웨어 (마지막)
# 개발 환경에서는 모든 origin 허용
cors_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 예외 처리기 등록 (순서 중요!)
app.add_exception_handler(AIPortalException, aiportal_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


# 기본 라우터들
@app.get("/")
async def root():
    """루트 엔드포인트"""
    from app.core.responses import create_success_response
    return create_success_response(
        message="AI 포탈 백엔드 API에 오신 것을 환영합니다",
        data={
            "service": "AI Portal Backend",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "status": "healthy"
        }
    )


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    uptime = time.time() - server_start_time
    
    # 각 서비스 상태 체크
    services_status = {}
    
    # 데이터베이스 상태 체크 (간단한 체크)
    try:
        from app.agents.llm_router import LLMRouter
        router = LLMRouter()
        available_models = router.get_available_models()
        services_status["ai_models"] = f"healthy ({len(available_models)} models)"
    except Exception as e:
        services_status["ai_models"] = f"error: {str(e)[:50]}"
    
    # OpenSearch 상태 체크
    try:
        from app.services.opensearch_service import opensearch_service
        if opensearch_service.is_connected():
            services_status["opensearch"] = "healthy"
        else:
            services_status["opensearch"] = "disconnected"
    except Exception as e:
        services_status["opensearch"] = f"error: {str(e)[:50]}"
    
    # 전체 시스템 상태 결정
    all_healthy = all("healthy" in status for status in services_status.values())
    system_status = "healthy" if all_healthy else "degraded"
    
    return create_health_response(
        status=system_status,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        uptime=uptime,
        services=services_status
    )


# API v1 라우터 포함
from app.api.v1.api import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )