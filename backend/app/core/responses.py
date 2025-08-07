"""
표준화된 API 응답 스키마 및 유틸리티
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """기본 API 응답 모델"""
    
    success: bool = Field(description="요청 성공 여부")
    message: str = Field(description="응답 메시지")
    data: Optional[Any] = Field(default=None, description="응답 데이터")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="응답 시간")
    request_id: Optional[str] = Field(default=None, description="요청 ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    
    success: bool = Field(default=False, description="요청 성공 여부 (항상 False)")
    error_code: str = Field(description="에러 코드")
    message: str = Field(description="에러 메시지")
    details: Optional[Dict[str, Any]] = Field(default=None, description="에러 세부 정보")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="에러 발생 시간")
    request_id: Optional[str] = Field(default=None, description="요청 ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ValidationErrorDetail(BaseModel):
    """검증 에러 세부 정보"""
    
    field: str = Field(description="에러가 발생한 필드")
    message: str = Field(description="에러 메시지")
    value: Optional[Any] = Field(default=None, description="잘못된 값")


class ValidationErrorResponse(ErrorResponse):
    """검증 에러 응답 모델"""
    
    error_code: str = Field(default="VALIDATION_ERROR", description="에러 코드")
    validation_errors: List[ValidationErrorDetail] = Field(description="검증 에러 목록")


class PaginationMeta(BaseModel):
    """페이지네이션 메타 정보"""
    
    page: int = Field(ge=1, description="현재 페이지")
    per_page: int = Field(ge=1, le=100, description="페이지당 항목 수")
    total: int = Field(ge=0, description="전체 항목 수")
    pages: int = Field(ge=0, description="전체 페이지 수")
    has_next: bool = Field(description="다음 페이지 존재 여부")
    has_prev: bool = Field(description="이전 페이지 존재 여부")


class PaginatedResponse(APIResponse):
    """페이지네이션된 응답 모델"""
    
    data: List[Any] = Field(description="응답 데이터 목록")
    meta: PaginationMeta = Field(description="페이지네이션 메타 정보")


class ChatResponse(APIResponse):
    """채팅 응답 모델"""
    
    class ChatData(BaseModel):
        response: str = Field(description="AI 응답")
        model_used: str = Field(description="사용된 AI 모델")
        response_time_ms: float = Field(description="응답 시간 (밀리초)")
        conversation_id: str = Field(description="대화 ID")
        message_id: str = Field(description="메시지 ID")
        metadata: Optional[Dict[str, Any]] = Field(default=None, description="추가 메타데이터")
    
    data: ChatData = Field(description="채팅 응답 데이터")


class FileUploadResponse(APIResponse):
    """파일 업로드 응답 모델"""
    
    class FileData(BaseModel):
        file_id: str = Field(description="파일 ID")
        filename: str = Field(description="파일명")
        file_size: int = Field(description="파일 크기 (바이트)")
        file_type: str = Field(description="파일 타입")
        upload_url: Optional[str] = Field(default=None, description="업로드된 파일 URL")
        processing_status: str = Field(description="처리 상태")
    
    data: FileData = Field(description="파일 업로드 데이터")


class HealthCheckResponse(APIResponse):
    """헬스 체크 응답 모델"""
    
    class HealthData(BaseModel):
        status: str = Field(description="서비스 상태")
        version: str = Field(description="서비스 버전")
        environment: str = Field(description="실행 환경")
        uptime: float = Field(description="서비스 실행 시간 (초)")
        services: Dict[str, str] = Field(description="각 서비스별 상태")
    
    data: HealthData = Field(description="헬스 체크 데이터")


# 응답 생성 유틸리티 함수들

def create_success_response(
    message: str = "요청이 성공적으로 처리되었습니다",
    data: Any = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """성공 응답 생성"""
    response = APIResponse(
        success=True,
        message=message,
        data=data,
        request_id=request_id
    )
    return response.dict()


def create_error_response(
    message: str,
    error_code: str = "GENERAL_ERROR",
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """에러 응답 생성"""
    response = ErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
        request_id=request_id
    )
    return response.dict()


def create_validation_error_response(
    message: str = "입력 데이터 검증에 실패했습니다",
    validation_errors: List[ValidationErrorDetail] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """검증 에러 응답 생성"""
    response = ValidationErrorResponse(
        message=message,
        validation_errors=validation_errors or [],
        request_id=request_id
    )
    return response.dict()


def create_paginated_response(
    data: List[Any],
    page: int,
    per_page: int,
    total: int,
    message: str = "데이터를 성공적으로 조회했습니다",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """페이지네이션된 응답 생성"""
    pages = (total + per_page - 1) // per_page  # 올림 계산
    
    response = PaginatedResponse(
        success=True,
        message=message,
        data=data,
        meta=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        ),
        request_id=request_id
    )
    return response.dict()


def create_chat_response(
    response: str,
    model_used: str,
    response_time_ms: float,
    conversation_id: str,
    message_id: str,
    metadata: Optional[Dict[str, Any]] = None,
    message: str = "AI 응답을 성공적으로 생성했습니다",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """채팅 응답 생성"""
    response_obj = ChatResponse(
        success=True,
        message=message,
        data=ChatResponse.ChatData(
            response=response,
            model_used=model_used,
            response_time_ms=response_time_ms,
            conversation_id=conversation_id,
            message_id=message_id,
            metadata=metadata
        ),
        request_id=request_id
    )
    return response_obj.dict()


def create_file_upload_response(
    file_id: str,
    filename: str,
    file_size: int,
    file_type: str,
    processing_status: str = "uploaded",
    upload_url: Optional[str] = None,
    message: str = "파일이 성공적으로 업로드되었습니다",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """파일 업로드 응답 생성"""
    response = FileUploadResponse(
        success=True,
        message=message,
        data=FileUploadResponse.FileData(
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            upload_url=upload_url,
            processing_status=processing_status
        ),
        request_id=request_id
    )
    return response.dict()


def create_health_response(
    status: str,
    version: str,
    environment: str,
    uptime: float,
    services: Dict[str, str],
    message: str = "시스템이 정상 작동 중입니다",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """헬스 체크 응답 생성"""
    response = HealthCheckResponse(
        success=True,
        message=message,
        data=HealthCheckResponse.HealthData(
            status=status,
            version=version,
            environment=environment,
            uptime=uptime,
            services=services
        ),
        request_id=request_id
    )
    return response.dict()


# HTTP 상태 코드 상수
class StatusCode:
    """HTTP 상태 코드 상수"""
    
    # 2xx 성공
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # 3xx 리다이렉션
    NOT_MODIFIED = 304
    
    # 4xx 클라이언트 에러
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # 5xx 서버 에러
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


# 에러 코드 상수
class ErrorCode:
    """에러 코드 상수"""
    
    # 일반적인 에러
    GENERAL_ERROR = "GENERAL_ERROR"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    
    # 인증/권한 에러
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # 검증 에러
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
    
    # 리소스 에러
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_LOCKED = "RESOURCE_LOCKED"
    
    # 외부 서비스 에러
    AI_MODEL_ERROR = "AI_MODEL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    
    # 제한/정책 에러
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"