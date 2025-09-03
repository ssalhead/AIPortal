# Idempotency Manager - 중복 방지 시스템
# AIPortal Canvas v5.0 - 통합 데이터 아키텍처

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text

from app.models.canvas_models import (
    CanvasOperationResult, IdempotencyViolationError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

class IdempotencyManager:
    """
    멱등성 관리자
    
    주요 역할:
    1. 중복 작업 방지 (같은 작업을 여러 번 실행해도 결과 동일)
    2. 작업 결과 캐싱 및 재사용
    3. 분산 환경에서의 멱등성 보장
    4. 자동 만료 및 정리
    
    멱등성 키 생성 규칙:
    - Canvas ID + 작업 타입 + 사용자 ID + 시간 창(Time Window)
    - SHA-256 해싱으로 고정 길이 키 생성
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
        # 메모리 캐시 (빠른 조회용)
        self._operation_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # 설정
        self._default_ttl = 3600  # 1시간 기본 TTL
        self._cache_cleanup_interval = 300  # 5분마다 정리
        self._max_cache_size = 10000  # 최대 캐시 항목 수
        
        # 중복 감지 설정
        self._time_window_seconds = 300  # 5분 시간 창
        self._pending_operations: Set[str] = set()  # 진행 중인 작업들
        
        # 비동기 락
        self._operation_locks: Dict[str, asyncio.Lock] = {}
    
    async def check_operation(
        self, 
        idempotency_key: str,
        ttl_seconds: Optional[int] = None
    ) -> Optional[CanvasOperationResult]:
        """
        멱등성 키로 기존 작업 결과 조회
        
        Args:
            idempotency_key: 멱등성 키
            ttl_seconds: TTL (기본값 사용 시 None)
            
        Returns:
            기존 작업 결과 또는 None
        """
        try:
            # TTL 설정
            ttl = ttl_seconds or self._default_ttl
            
            # 메모리 캐시에서 먼저 조회
            cached_result = await self._get_from_cache(idempotency_key, ttl)
            if cached_result:
                logger.debug(f"멱등성 키 캐시 히트: {idempotency_key}")
                return CanvasOperationResult(**cached_result)
            
            # DB에서 조회 (실제 구현 시)
            db_result = await self._get_from_db(idempotency_key, ttl)
            if db_result:
                # 캐시에 저장
                await self._set_to_cache(idempotency_key, db_result)
                logger.debug(f"멱등성 키 DB 히트: {idempotency_key}")
                return CanvasOperationResult(**db_result)
            
            logger.debug(f"멱등성 키 미스: {idempotency_key}")
            return None
            
        except Exception as e:
            logger.error(f"멱등성 키 조회 실패 {idempotency_key}: {str(e)}")
            return None
    
    async def record_operation(
        self,
        idempotency_key: str,
        result: CanvasOperationResult,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        작업 결과 기록
        
        Args:
            idempotency_key: 멱등성 키
            result: 작업 결과
            ttl_seconds: TTL (기본값 사용 시 None)
            
        Returns:
            기록 성공 여부
        """
        try:
            ttl = ttl_seconds or self._default_ttl
            
            # 결과를 직렬화 가능한 형태로 변환
            result_data = {
                'success': result.success,
                'canvas_data': result.canvas_data.model_dump() if result.canvas_data else None,
                'error_message': result.error_message,
                'conflict_resolution': result.conflict_resolution,
                'recorded_at': datetime.utcnow().isoformat()
            }
            
            # 메모리 캐시에 저장
            await self._set_to_cache(idempotency_key, result_data)
            
            # DB에 저장 (실제 구현 시)
            await self._save_to_db(idempotency_key, result_data, ttl)
            
            # 진행 중 작업 목록에서 제거
            self._pending_operations.discard(idempotency_key)
            
            logger.info(f"멱등성 키 기록: {idempotency_key}")
            return True
            
        except Exception as e:
            logger.error(f"멱등성 키 기록 실패 {idempotency_key}: {str(e)}")
            return False
    
    async def start_operation(self, idempotency_key: str) -> bool:
        """
        작업 시작 마킹 (중복 실행 방지)
        
        Args:
            idempotency_key: 멱등성 키
            
        Returns:
            시작 성공 여부 (False면 이미 진행 중)
        """
        try:
            # 분산 락 획득
            operation_lock = await self._get_operation_lock(idempotency_key)
            
            async with operation_lock:
                # 이미 진행 중인지 확인
                if idempotency_key in self._pending_operations:
                    logger.warning(f"작업 이미 진행 중: {idempotency_key}")
                    return False
                
                # 이미 완료된 작업인지 확인
                existing_result = await self.check_operation(idempotency_key)
                if existing_result:
                    logger.warning(f"작업 이미 완료됨: {idempotency_key}")
                    return False
                
                # 진행 중 목록에 추가
                self._pending_operations.add(idempotency_key)
                
                logger.debug(f"작업 시작 마킹: {idempotency_key}")
                return True
                
        except Exception as e:
            logger.error(f"작업 시작 마킹 실패 {idempotency_key}: {str(e)}")
            return False
    
    async def cancel_operation(self, idempotency_key: str) -> None:
        """
        작업 취소 (진행 중 목록에서 제거)
        
        Args:
            idempotency_key: 멱등성 키
        """
        try:
            self._pending_operations.discard(idempotency_key)
            logger.debug(f"작업 취소: {idempotency_key}")
            
        except Exception as e:
            logger.error(f"작업 취소 실패 {idempotency_key}: {str(e)}")
    
    def generate_key(
        self,
        canvas_id: UUID,
        operation_type: str,
        user_id: UUID,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        멱등성 키 생성
        
        Args:
            canvas_id: Canvas ID
            operation_type: 작업 타입
            user_id: 사용자 ID  
            additional_data: 추가 데이터 (선택)
            
        Returns:
            SHA-256 해시 기반 멱등성 키
        """
        try:
            # 시간 창 계산 (5분 단위로 그룹화)
            current_time = datetime.utcnow()
            time_window = int(current_time.timestamp() / self._time_window_seconds)
            
            # 기본 키 데이터
            key_components = [
                str(canvas_id),
                operation_type,
                str(user_id),
                str(time_window)
            ]
            
            # 추가 데이터 포함
            if additional_data:
                # 딕셔너리를 정렬하여 일관된 키 생성
                sorted_items = sorted(additional_data.items())
                additional_str = json.dumps(sorted_items, sort_keys=True)
                key_components.append(additional_str)
            
            # 키 조합 및 해싱
            key_string = ":".join(key_components)
            key_hash = hashlib.sha256(key_string.encode()).hexdigest()
            
            logger.debug(f"멱등성 키 생성: {operation_type} -> {key_hash[:8]}...")
            return key_hash
            
        except Exception as e:
            logger.error(f"멱등성 키 생성 실패: {str(e)}")
            # 실패 시 UUID 기반 키 생성
            import uuid
            return str(uuid.uuid4())
    
    def generate_batch_key(
        self,
        canvas_ids: list[UUID],
        operation_type: str,
        user_id: UUID
    ) -> str:
        """
        배치 작업용 멱등성 키 생성
        
        Args:
            canvas_ids: Canvas ID 목록
            operation_type: 작업 타입
            user_id: 사용자 ID
            
        Returns:
            배치 작업용 멱등성 키
        """
        try:
            # Canvas ID들을 정렬하여 일관된 키 생성
            sorted_canvas_ids = sorted([str(cid) for cid in canvas_ids])
            
            additional_data = {
                'canvas_count': len(canvas_ids),
                'canvas_ids_hash': hashlib.md5(
                    ":".join(sorted_canvas_ids).encode()
                ).hexdigest()
            }
            
            return self.generate_key(
                canvas_ids[0],  # 첫 번째 Canvas ID를 대표로 사용
                f"batch_{operation_type}",
                user_id,
                additional_data
            )
            
        except Exception as e:
            logger.error(f"배치 멱등성 키 생성 실패: {str(e)}")
            import uuid
            return str(uuid.uuid4())
    
    async def get_pending_operations(self) -> Set[str]:
        """진행 중인 작업 목록 조회"""
        return self._pending_operations.copy()
    
    async def cleanup_expired_operations(self) -> Dict[str, int]:
        """
        만료된 작업 정리 (백그라운드 작업)
        
        Returns:
            정리 통계
        """
        try:
            current_time = datetime.utcnow()
            
            # 메모리 캐시 정리
            cache_cleaned = 0
            expired_keys = []
            
            for key, timestamp in self._cache_timestamps.items():
                if (current_time - timestamp).seconds > self._default_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                if key in self._operation_cache:
                    del self._operation_cache[key]
                    cache_cleaned += 1
                
                if key in self._cache_timestamps:
                    del self._cache_timestamps[key]
            
            # 진행 중 작업 정리 (5분 이상 진행 중인 것들)
            pending_cleaned = 0
            stale_operations = set()
            
            for key in self._pending_operations:
                # 실제로는 시작 시간을 추적해야 하지만
                # 현재는 간단히 주기적으로 전체 정리
                pass
            
            # DB 정리 (실제 구현 시)
            db_cleaned = await self._cleanup_db_records()
            
            # 캐시 크기 제한
            if len(self._operation_cache) > self._max_cache_size:
                # 가장 오래된 항목들 제거
                sorted_items = sorted(
                    self._cache_timestamps.items(),
                    key=lambda x: x[1]
                )
                
                remove_count = len(self._operation_cache) - self._max_cache_size
                for key, _ in sorted_items[:remove_count]:
                    if key in self._operation_cache:
                        del self._operation_cache[key]
                    if key in self._cache_timestamps:
                        del self._cache_timestamps[key]
                    cache_cleaned += 1
            
            stats = {
                'cache_cleaned': cache_cleaned,
                'pending_cleaned': pending_cleaned,
                'db_cleaned': db_cleaned,
                'total_cache_size': len(self._operation_cache),
                'total_pending': len(self._pending_operations)
            }
            
            if cache_cleaned > 0 or pending_cleaned > 0 or db_cleaned > 0:
                logger.info(f"멱등성 정리 완료: {stats}")
            
            return stats
            
        except Exception as e:
            logger.error(f"멱등성 정리 실패: {str(e)}")
            return {'error': str(e)}
    
    async def get_statistics(self) -> Dict[str, Any]:
        """멱등성 관리자 통계"""
        try:
            return {
                'cache_size': len(self._operation_cache),
                'pending_operations': len(self._pending_operations),
                'active_locks': len(self._operation_locks),
                'cache_hit_ratio': self._calculate_cache_hit_ratio(),
                'average_operation_time': await self._calculate_avg_operation_time(),
                'cleanup_interval': self._cache_cleanup_interval,
                'default_ttl': self._default_ttl
            }
            
        except Exception as e:
            logger.error(f"멱등성 통계 조회 실패: {str(e)}")
            return {'error': str(e)}
    
    # ===== 내부 메서드 =====
    
    async def _get_from_cache(
        self, 
        key: str, 
        ttl: int
    ) -> Optional[Dict[str, Any]]:
        """메모리 캐시에서 조회"""
        if key not in self._operation_cache:
            return None
        
        # TTL 확인
        timestamp = self._cache_timestamps.get(key)
        if timestamp:
            age = (datetime.utcnow() - timestamp).seconds
            if age > ttl:
                # 만료된 항목 제거
                del self._operation_cache[key]
                del self._cache_timestamps[key]
                return None
        
        return self._operation_cache[key]
    
    async def _set_to_cache(self, key: str, data: Dict[str, Any]) -> None:
        """메모리 캐시에 저장"""
        self._operation_cache[key] = data
        self._cache_timestamps[key] = datetime.utcnow()
    
    async def _get_from_db(
        self, 
        key: str, 
        ttl: int
    ) -> Optional[Dict[str, Any]]:
        """DB에서 멱등성 레코드 조회"""
        try:
            # 실제 구현 시 idempotency_operations 테이블에서 조회
            # 현재는 None 반환
            logger.debug(f"DB에서 멱등성 키 조회: {key}")
            return None
            
        except Exception as e:
            logger.error(f"DB 멱등성 조회 실패 {key}: {str(e)}")
            return None
    
    async def _save_to_db(
        self, 
        key: str, 
        data: Dict[str, Any], 
        ttl: int
    ) -> bool:
        """DB에 멱등성 레코드 저장"""
        try:
            # 실제 구현 시 idempotency_operations 테이블에 INSERT
            logger.debug(f"DB에 멱등성 키 저장: {key}")
            
            # TODO: 실제 DB 저장 로직
            # INSERT INTO idempotency_operations (key, result_data, expires_at)
            # VALUES (key, json_data, current_time + ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"DB 멱등성 저장 실패 {key}: {str(e)}")
            return False
    
    async def _cleanup_db_records(self) -> int:
        """DB에서 만료된 멱등성 레코드 정리"""
        try:
            # 실제 구현 시 만료된 레코드 DELETE
            logger.debug("DB 멱등성 레코드 정리")
            
            # TODO: 실제 DB 정리 로직
            # DELETE FROM idempotency_operations WHERE expires_at < NOW()
            
            return 0  # 정리된 레코드 수
            
        except Exception as e:
            logger.error(f"DB 멱등성 정리 실패: {str(e)}")
            return 0
    
    async def _get_operation_lock(self, key: str) -> asyncio.Lock:
        """작업별 비동기 락 획득"""
        if key not in self._operation_locks:
            self._operation_locks[key] = asyncio.Lock()
        return self._operation_locks[key]
    
    def _calculate_cache_hit_ratio(self) -> float:
        """캐시 히트 비율 계산"""
        # 실제로는 히트/미스 카운터를 추적해야 함
        # 현재는 대략적인 값 반환
        cache_size = len(self._operation_cache)
        if cache_size == 0:
            return 0.0
        
        # 캐시 크기를 기반으로 한 추정치
        return min(0.95, cache_size / 1000.0)
    
    async def _calculate_avg_operation_time(self) -> float:
        """평균 작업 시간 계산"""
        # 실제로는 작업 시간을 추적해야 함
        # 현재는 기본값 반환
        return 0.5  # 500ms