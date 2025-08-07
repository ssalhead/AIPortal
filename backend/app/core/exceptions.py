"""
사용자 정의 예외 클래스들
"""

from typing import Any, Dict, Optional


class AIPortalException(Exception):
    """AI 포탈 기본 예외 클래스"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "GENERAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(AIPortalException):
    """입력 검증 실패"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details={"field": field} if field else {},
            **kwargs
        )


class AuthenticationError(AIPortalException):
    """인증 실패"""
    
    def __init__(self, message: str = "인증이 필요합니다", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_REQUIRED",
            status_code=401,
            **kwargs
        )


class AuthorizationError(AIPortalException):
    """권한 부족"""
    
    def __init__(self, message: str = "권한이 부족합니다", **kwargs):
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_PERMISSIONS",
            status_code=403,
            **kwargs
        )


class ResourceNotFoundError(AIPortalException):
    """리소스를 찾을 수 없음"""
    
    def __init__(self, resource: str, resource_id: Optional[str] = None, **kwargs):
        message = f"{resource}을(를) 찾을 수 없습니다"
        if resource_id:
            message += f": {resource_id}"
        
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource": resource, "resource_id": resource_id},
            **kwargs
        )


class ConflictError(AIPortalException):
    """리소스 충돌"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="RESOURCE_CONFLICT",
            status_code=409,
            **kwargs
        )


class RateLimitError(AIPortalException):
    """요청 속도 제한"""
    
    def __init__(self, message: str = "요청 속도 제한에 걸렸습니다", retry_after: Optional[int] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after} if retry_after else {},
            **kwargs
        )


class AIModelError(AIPortalException):
    """AI 모델 관련 오류"""
    
    def __init__(self, message: str, model_name: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="AI_MODEL_ERROR",
            status_code=502,  # Bad Gateway - 외부 서비스 문제
            details={"model_name": model_name} if model_name else {},
            **kwargs
        )


class DatabaseError(AIPortalException):
    """데이터베이스 관련 오류"""
    
    def __init__(self, message: str = "데이터베이스 오류가 발생했습니다", **kwargs):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            **kwargs
        )


class ExternalServiceError(AIPortalException):
    """외부 서비스 오류"""
    
    def __init__(self, service_name: str, message: str = None, **kwargs):
        if not message:
            message = f"{service_name} 서비스에 일시적인 문제가 발생했습니다"
        
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=503,  # Service Unavailable
            details={"service_name": service_name},
            **kwargs
        )


class FileProcessingError(AIPortalException):
    """파일 처리 오류"""
    
    def __init__(self, message: str, filename: Optional[str] = None, **kwargs):
        super().__init__(
            message=message,
            error_code="FILE_PROCESSING_ERROR",
            status_code=422,
            details={"filename": filename} if filename else {},
            **kwargs
        )


class ConfigurationError(AIPortalException):
    """설정 오류"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            **kwargs
        )