"""
백엔드 로깅 유틸리티 - 환경별 로그 레벨 제어
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import json


class StructuredFormatter(logging.Formatter):
    """구조화된 JSON 로그 포맷터"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 추가 컨텍스트가 있으면 포함
        if hasattr(record, 'context'):
            log_data['context'] = record.context
            
        # 에러 정보가 있으면 포함
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)


class OptimizedLogger:
    """최적화된 로거 래퍼 클래스"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.is_development = self._is_development()
        self.is_performance_debug = os.getenv('DEBUG_PERFORMANCE', 'false').lower() == 'true'
        self.is_streaming_debug = os.getenv('DEBUG_STREAMING', 'false').lower() == 'true'
        
    @staticmethod
    def _is_development() -> bool:
        """개발 환경 여부 확인"""
        return os.getenv('ENVIRONMENT', 'development') == 'development'
    
    def error(self, message: str, exc_info: Optional[Exception] = None, context: Optional[Dict[str, Any]] = None):
        """에러 로그 - 항상 출력"""
        extra = {'context': context} if context else {}
        self.logger.error(message, exc_info=exc_info, extra=extra)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        """경고 로그 - 항상 출력"""
        extra = {'context': context} if context else {}
        self.logger.warning(message, extra=extra)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """정보 로그 - INFO 레벨 이상에서 출력"""
        extra = {'context': context} if context else {}
        self.logger.info(message, extra=extra)
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """디버그 로그 - 개발 환경에서만 출력"""
        if not self.is_development:
            return
        extra = {'context': context} if context else {}
        self.logger.debug(message, extra=extra)
    
    def debug_performance(self, message: str, context: Optional[Dict[str, Any]] = None):
        """성능 디버깅용 로그 - 성능 디버그 모드에서만 출력"""
        if not self.is_performance_debug:
            return
        extra = {'context': context} if context else {}
        self.logger.debug(f"[PERF] {message}", extra=extra)
    
    def debug_streaming(self, message: str, context: Optional[Dict[str, Any]] = None):
        """스트리밍 디버깅용 로그 - 스트리밍 디버그 모드에서만 출력"""
        if not self.is_streaming_debug:
            return
        extra = {'context': context} if context else {}
        self.logger.debug(f"[STREAM] {message}", extra=extra)


def setup_logging():
    """로깅 시스템 초기 설정"""
    # 환경에 따른 로그 레벨 설정
    environment = os.getenv('ENVIRONMENT', 'development')
    
    if environment == 'production':
        log_level = logging.WARNING
    elif environment == 'staging':
        log_level = logging.INFO
    else:  # development
        log_level = logging.DEBUG
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # 프로덕션 환경에서는 구조화된 로깅 사용
    if environment == 'production':
        formatter = StructuredFormatter()
    else:
        # 개발 환경에서는 읽기 쉬운 포맷 사용
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 특정 로거의 로그 레벨 조정 (노이지한 라이브러리들)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> OptimizedLogger:
    """최적화된 로거 인스턴스 반환"""
    return OptimizedLogger(name)


# 모듈 로드 시 로깅 설정
setup_logging()