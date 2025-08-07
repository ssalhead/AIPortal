"""
통합 로깅 및 모니터링 서비스
"""

import asyncio
import json
import time
import traceback
from typing import Any, Dict, Optional, Union
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from functools import wraps

import structlog
from langsmith import Client as LangsmithClient
from langsmith.run_helpers import traceable
from langsmith.schemas import Run

from app.core.config import settings

# 구조화된 로거 설정
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class LoggingService:
    """통합 로깅 및 모니터링 서비스"""
    
    def __init__(self):
        self.langsmith_client = None
        self._initialize_langsmith()
    
    def _initialize_langsmith(self):
        """LangSmith 클라이언트 초기화"""
        try:
            if settings.LANGSMITH_API_KEY:
                self.langsmith_client = LangsmithClient(
                    api_key=settings.LANGSMITH_API_KEY,
                    api_url="https://api.smith.langchain.com"
                )
                logger.info("LangSmith 클라이언트 초기화 완료", project=settings.LANGSMITH_PROJECT)
            else:
                logger.warning("LANGSMITH_API_KEY가 설정되지 않음 - LangSmith 모니터링 비활성화")
        except Exception as e:
            logger.error("LangSmith 초기화 실패", error=str(e))
            self.langsmith_client = None
    
    def log_request(
        self, 
        method: str, 
        url: str, 
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **extra_data
    ):
        """HTTP 요청 로깅"""
        logger.info(
            "HTTP 요청",
            method=method,
            url=url,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc).isoformat(),
            **extra_data
        )
    
    def log_response(
        self,
        method: str,
        url: str,
        status_code: int,
        response_time_ms: float,
        user_id: Optional[str] = None,
        **extra_data
    ):
        """HTTP 응답 로깅"""
        logger.info(
            "HTTP 응답",
            method=method,
            url=url,
            status_code=status_code,
            response_time_ms=response_time_ms,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            **extra_data
        )
    
    def log_ai_model_usage(
        self,
        model_name: str,
        prompt: str,
        response: str,
        response_time_ms: float,
        tokens_used: Optional[int] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
        **extra_data
    ):
        """AI 모델 사용 로깅"""
        log_data = {
            "model_name": model_name,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "response_time_ms": response_time_ms,
            "tokens_used": tokens_used,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **extra_data
        }
        
        if error:
            log_data["error"] = error
            logger.error("AI 모델 사용 실패", **log_data)
        else:
            logger.info("AI 모델 사용", **log_data)
        
        # LangSmith에 전송 (비동기)
        if self.langsmith_client and success:
            asyncio.create_task(self._send_to_langsmith(
                model_name=model_name,
                prompt=prompt,
                response=response,
                response_time_ms=response_time_ms,
                user_id=user_id,
                conversation_id=conversation_id,
                **extra_data
            ))
    
    async def _send_to_langsmith(
        self,
        model_name: str,
        prompt: str,
        response: str,
        response_time_ms: float,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        **extra_data
    ):
        """LangSmith로 데이터 전송"""
        try:
            if not self.langsmith_client:
                return
            
            run_data = {
                "name": f"ai_portal_{model_name}",
                "run_type": "llm",
                "inputs": {"prompt": prompt},
                "outputs": {"response": response},
                "start_time": datetime.now(timezone.utc),
                "end_time": datetime.now(timezone.utc),
                "extra": {
                    "model_name": model_name,
                    "response_time_ms": response_time_ms,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    **extra_data
                },
                "tags": ["ai-portal", model_name, settings.ENVIRONMENT]
            }
            
            # 비동기적으로 LangSmith에 전송
            await asyncio.to_thread(
                self.langsmith_client.create_run,
                **run_data
            )
            
        except Exception as e:
            logger.error("LangSmith 전송 실패", error=str(e))
    
    def log_error(
        self,
        error: Exception,
        context: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **extra_data
    ):
        """에러 로깅"""
        logger.error(
            "시스템 에러",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            user_id=user_id,
            request_id=request_id,
            traceback=traceback.format_exc(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            **extra_data
        )
    
    def log_security_event(
        self,
        event_type: str,
        description: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: str = "INFO",
        **extra_data
    ):
        """보안 이벤트 로깅"""
        log_data = {
            "security_event_type": event_type,
            "description": description,
            "user_id": user_id,
            "ip_address": ip_address,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **extra_data
        }
        
        if severity in ["CRITICAL", "HIGH"]:
            logger.error("보안 이벤트 발생", **log_data)
        elif severity == "MEDIUM":
            logger.warning("보안 이벤트 발생", **log_data)
        else:
            logger.info("보안 이벤트 발생", **log_data)
    
    def log_performance_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        unit: str = "ms",
        context: Optional[Dict[str, Any]] = None,
        **extra_data
    ):
        """성능 메트릭 로깅"""
        logger.info(
            "성능 메트릭",
            metric_name=metric_name,
            value=value,
            unit=unit,
            context=context or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
            **extra_data
        )
    
    def log_citation_extraction(
        self,
        response_length: int,
        citations_found: int,
        sources_processed: int,
        min_confidence: float,
        **extra_data
    ):
        """인용 정보 추출 로깅"""
        citation_data = {
            "response_length": response_length,
            "citations_found": citations_found,
            "sources_processed": sources_processed,
            "min_confidence": min_confidence,
            "citation_density": citations_found / max(response_length, 1) * 1000,  # 1000자당 인용 수
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **extra_data
        }
        
        logger.info("인용 정보 추출 완료", **citation_data)
    
    @asynccontextmanager
    async def trace_operation(
        self,
        operation_name: str,
        user_id: Optional[str] = None,
        **extra_data
    ):
        """작업 추적 컨텍스트 매니저"""
        start_time = time.time()
        operation_id = f"{operation_name}_{int(start_time * 1000)}"
        
        logger.info(
            "작업 시작",
            operation_id=operation_id,
            operation_name=operation_name,
            user_id=user_id,
            **extra_data
        )
        
        try:
            yield operation_id
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "작업 실패",
                operation_id=operation_id,
                operation_name=operation_name,
                duration_ms=duration_ms,
                error=str(e),
                user_id=user_id,
                **extra_data
            )
            raise
        else:
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "작업 완료",
                operation_id=operation_id,
                operation_name=operation_name,
                duration_ms=duration_ms,
                user_id=user_id,
                **extra_data
            )


# 싱글톤 인스턴스
logging_service = LoggingService()


# 데코레이터 함수들
def log_api_call(operation_name: str):
    """API 호출 로깅 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with logging_service.trace_operation(
                operation_name=operation_name,
                function_name=func.__name__
            ) as operation_id:
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def log_llm_usage(func):
    """LLM 사용 로깅 데코레이터"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        model_name = kwargs.get('model_name', 'unknown')
        prompt = kwargs.get('prompt', '')[:500]  # 처음 500자만
        
        try:
            result = await func(*args, **kwargs)
            response_time_ms = (time.time() - start_time) * 1000
            
            if isinstance(result, tuple) and len(result) == 2:
                response, used_model = result
            else:
                response = str(result)
                used_model = model_name
            
            logging_service.log_ai_model_usage(
                model_name=used_model,
                prompt=prompt,
                response=response[:500],  # 처음 500자만
                response_time_ms=response_time_ms,
                success=True
            )
            
            return result
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logging_service.log_ai_model_usage(
                model_name=model_name,
                prompt=prompt,
                response="",
                response_time_ms=response_time_ms,
                success=False,
                error=str(e)
            )
            raise
    
    return wrapper