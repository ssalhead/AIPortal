"""
전역 예외 처리기
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.encoders import jsonable_encoder

from app.core.exceptions import AIPortalException
from app.core.responses import (
    create_error_response, 
    create_validation_error_response,
    ValidationErrorDetail,
    StatusCode,
    ErrorCode
)
from app.services.logging_service import logging_service


async def aiportal_exception_handler(request: Request, exc: AIPortalException) -> JSONResponse:
    """AI Portal 사용자 정의 예외 처리기"""
    
    request_id = getattr(request.state, "request_id", None)
    user_id = getattr(request.state, "user_id", None)
    
    # 에러 로깅
    logging_service.log_error(
        error=exc,
        context="AI Portal 사용자 정의 예외",
        user_id=user_id,
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        error_code=exc.error_code,
        status_code=exc.status_code
    )
    
    # 보안 이벤트로도 기록 (권한/인증 에러의 경우)
    if exc.status_code in [401, 403]:
        logging_service.log_security_event(
            event_type="access_denied",
            description=f"접근 거부: {exc.message}",
            user_id=user_id,
            ip_address=request.client.host if request.client else "unknown",
            severity="MEDIUM",
            error_code=exc.error_code,
            path=request.url.path
        )
    
    response_data = create_error_response(
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(response_data)
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """FastAPI HTTPException 처리기"""
    
    request_id = getattr(request.state, "request_id", None)
    user_id = getattr(request.state, "user_id", None)
    
    # HTTP 에러를 우리의 에러 코드로 매핑
    error_code_mapping = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.AUTHENTICATION_REQUIRED,
        403: ErrorCode.INSUFFICIENT_PERMISSIONS,
        404: ErrorCode.RESOURCE_NOT_FOUND,
        409: ErrorCode.RESOURCE_CONFLICT,
        422: ErrorCode.VALIDATION_ERROR,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.INTERNAL_SERVER_ERROR,
        502: ErrorCode.EXTERNAL_SERVICE_ERROR,
        503: ErrorCode.EXTERNAL_SERVICE_ERROR,
    }
    
    error_code = error_code_mapping.get(exc.status_code, ErrorCode.GENERAL_ERROR)
    
    # 에러 로깅
    logging_service.log_error(
        error=Exception(exc.detail),
        context="HTTP 예외",
        user_id=user_id,
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        status_code=exc.status_code,
        error_code=error_code
    )
    
    response_data = create_error_response(
        message=str(exc.detail),
        error_code=error_code,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(response_data)
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic 검증 에러 처리기"""
    
    request_id = getattr(request.state, "request_id", None)
    user_id = getattr(request.state, "user_id", None)
    
    # 검증 에러 세부 정보 생성
    validation_errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:]) if len(error["loc"]) > 1 else str(error["loc"][0])
        validation_errors.append(
            ValidationErrorDetail(
                field=field,
                message=error["msg"],
                value=error.get("input")
            )
        )
    
    # 에러 로깅
    logging_service.log_error(
        error=exc,
        context="요청 검증 실패",
        user_id=user_id,
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        validation_errors=[err.dict() for err in validation_errors]
    )
    
    response_data = create_validation_error_response(
        validation_errors=validation_errors,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=StatusCode.UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(response_data)
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """일반 예외 처리기 (마지막 예외 처리기)"""
    
    request_id = getattr(request.state, "request_id", None)
    user_id = getattr(request.state, "user_id", None)
    
    # 예상치 못한 에러는 CRITICAL로 로깅
    logging_service.log_error(
        error=exc,
        context="예상치 못한 시스템 에러",
        user_id=user_id,
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        user_agent=request.headers.get("user-agent", "")
    )
    
    # 보안 이벤트로도 기록
    logging_service.log_security_event(
        event_type="system_error",
        description=f"예상치 못한 시스템 에러: {type(exc).__name__}",
        user_id=user_id,
        ip_address=request.client.host if request.client else "unknown",
        severity="HIGH",
        path=request.url.path,
        error_type=type(exc).__name__
    )
    
    # 개발 환경에서는 상세한 에러 정보 제공
    from app.core.config import settings
    
    if settings.DEBUG:
        response_data = create_error_response(
            message=f"서버 내부 오류: {str(exc)}",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            details={
                "error_type": type(exc).__name__,
                "error_message": str(exc)
            },
            request_id=request_id
        )
    else:
        # 프로덕션에서는 일반적인 에러 메시지만 제공
        response_data = create_error_response(
            message="서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            request_id=request_id
        )
    
    return JSONResponse(
        status_code=StatusCode.INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(response_data)
    )


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Starlette HTTPException 처리기"""
    
    request_id = getattr(request.state, "request_id", None)
    
    # 404, 405 등의 기본 HTTP 에러 처리
    if exc.status_code == 404:
        message = "요청한 리소스를 찾을 수 없습니다"
        error_code = ErrorCode.RESOURCE_NOT_FOUND
    elif exc.status_code == 405:
        message = "지원하지 않는 HTTP 메서드입니다"
        error_code = ErrorCode.GENERAL_ERROR
    else:
        message = exc.detail or "요청을 처리할 수 없습니다"
        error_code = ErrorCode.GENERAL_ERROR
    
    response_data = create_error_response(
        message=message,
        error_code=error_code,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(response_data)
    )