"""
로깅 미들웨어
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.logging_service import logging_service


class LoggingMiddleware(BaseHTTPMiddleware):
    """HTTP 요청/응답 로깅 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 요청 ID 생성
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 요청 시작 시간 기록
        start_time = time.time()
        
        # 클라이언트 정보 추출
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        user_id = getattr(request.state, "user_id", None)
        
        # 요청 로깅
        logging_service.log_request(
            method=request.method,
            url=str(request.url),
            user_id=user_id,
            ip_address=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            path=request.url.path,
            query_params=dict(request.query_params),
            headers=dict(request.headers) if request.url.path.startswith("/api/") else {}
        )
        
        try:
            # 요청 처리
            response = await call_next(request)
            
            # 응답 시간 계산
            response_time_ms = (time.time() - start_time) * 1000
            
            # 응답 로깅
            logging_service.log_response(
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                user_id=user_id,
                request_id=request_id,
                path=request.url.path
            )
            
            # 성능 메트릭 로깅 (느린 요청 감지)
            if response_time_ms > 1000:  # 1초 이상
                logging_service.log_performance_metric(
                    metric_name="slow_request",
                    value=response_time_ms,
                    unit="ms",
                    context={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code
                    },
                    request_id=request_id
                )
            
            # 응답 헤더에 요청 ID 추가
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # 에러 시 응답 시간 계산
            response_time_ms = (time.time() - start_time) * 1000
            
            # 에러 로깅
            logging_service.log_error(
                error=e,
                context="HTTP 요청 처리 중 에러 발생",
                user_id=user_id,
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                response_time_ms=response_time_ms,
                client_ip=client_ip
            )
            
            # 에러 응답 로깅
            logging_service.log_response(
                method=request.method,
                url=str(request.url),
                status_code=500,
                response_time_ms=response_time_ms,
                user_id=user_id,
                request_id=request_id,
                path=request.url.path,
                error=str(e)
            )
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출"""
        # X-Forwarded-For 헤더 확인 (프록시/로드밸런서 뒤에 있는 경우)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # X-Real-IP 헤더 확인
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 직접 연결된 클라이언트 IP
        if request.client:
            return request.client.host
        
        return "unknown"


class SecurityMiddleware(BaseHTTPMiddleware):
    """보안 이벤트 로깅 미들웨어"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        user_id = getattr(request.state, "user_id", None)
        
        # 의심스러운 요청 패턴 감지
        self._detect_suspicious_patterns(request, client_ip, user_id)
        
        try:
            response = await call_next(request)
            
            # 인증 실패 감지 (401, 403 상태코드)
            if response.status_code in [401, 403]:
                logging_service.log_security_event(
                    event_type="authentication_failure",
                    description=f"인증 실패 - {request.method} {request.url.path}",
                    user_id=user_id,
                    ip_address=client_ip,
                    severity="MEDIUM",
                    status_code=response.status_code,
                    path=request.url.path
                )
            
            return response
            
        except Exception as e:
            # 예외 발생 시 보안 이벤트로 기록
            logging_service.log_security_event(
                event_type="system_error",
                description=f"시스템 에러 발생 - {str(e)[:100]}",
                user_id=user_id,
                ip_address=client_ip,
                severity="HIGH",
                path=request.url.path,
                error_type=type(e).__name__
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _detect_suspicious_patterns(
        self, 
        request: Request, 
        client_ip: str, 
        user_id: str | None
    ):
        """의심스러운 요청 패턴 감지"""
        url_path = request.url.path.lower()
        query_string = str(request.query_params).lower()
        
        # SQL Injection 패턴 감지
        sql_patterns = [
            "union select", "drop table", "delete from", 
            "insert into", "update set", "' or '1'='1",
            "' or 1=1", "; drop", "' union", "' or '1'"
        ]
        
        for pattern in sql_patterns:
            if pattern in url_path or pattern in query_string:
                logging_service.log_security_event(
                    event_type="sql_injection_attempt",
                    description=f"SQL Injection 시도 감지: {pattern}",
                    user_id=user_id,
                    ip_address=client_ip,
                    severity="HIGH",
                    path=request.url.path,
                    pattern=pattern
                )
                break
        
        # XSS 패턴 감지
        xss_patterns = [
            "<script", "javascript:", "onerror=", "onload=",
            "alert(", "document.cookie", "window.location"
        ]
        
        for pattern in xss_patterns:
            if pattern in url_path or pattern in query_string:
                logging_service.log_security_event(
                    event_type="xss_attempt",
                    description=f"XSS 시도 감지: {pattern}",
                    user_id=user_id,
                    ip_address=client_ip,
                    severity="HIGH",
                    path=request.url.path,
                    pattern=pattern
                )
                break
        
        # Path Traversal 패턴 감지
        if "../" in url_path or "..%2f" in url_path or "..%5c" in url_path:
            logging_service.log_security_event(
                event_type="path_traversal_attempt",
                description="Path Traversal 시도 감지",
                user_id=user_id,
                ip_address=client_ip,
                severity="HIGH",
                path=request.url.path
            )