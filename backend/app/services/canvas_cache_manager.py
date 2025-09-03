# Canvas Cache Manager - 2-Tier 캐싱 시스템
# AIPortal Canvas v5.0 - 통합 데이터 아키텍처

import asyncio
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text, func

from app.models.canvas_models import (
    CanvasData, CanvasSyncState, CanvasEventData
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

class CanvasCacheManager:
    """
    Canvas 2-Tier 캐싱 시스템
    
    캐싱 계층:
    1. L1 Cache (메모리): 빠른 접근, 제한된 용량
    2. L2 Cache (PostgreSQL): 영속적, 대용량
    
    주요 역할:
    1. 고성능 Canvas 데이터 캐싱
    2. 동기화 상태 캐싱
    3. 이벤트 스트림 캐싱
    4. 자동 만료 및 무효화
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
        # L1 캐시 (메모리)
        self._canvas_cache: Dict[str, Dict[str, Any]] = {}  # canvas_id -> canvas_data
        self._sync_state_cache: Dict[str, Dict[str, Any]] = {}  # "canvas_id:client_id" -> sync_state
        self._event_cache: Dict[str, List[Dict[str, Any]]] = {}  # canvas_id -> events
        
        # 캐시 메타데이터
        self._cache_timestamps: Dict[str, datetime] = {}
        self._access_counts: Dict[str, int] = {}
        self._cache_sizes: Dict[str, int] = {}
        
        # 캐시 설정
        self._l1_ttl = 300  # L1 캐시 5분
        self._l2_ttl = 3600  # L2 캐시 1시간  
        self._max_l1_size = 1000  # L1 캐시 최대 항목 수
        self._max_canvas_size = 10 * 1024 * 1024  # Canvas 최대 크기 10MB
        
        # 통계
        self._hit_counts = {'l1': 0, 'l2': 0, 'miss': 0}
        self._operation_counts = {'get': 0, 'set': 0, 'invalidate': 0}
        
        # 비동기 락
        self._cache_locks: Dict[str, asyncio.Lock] = {}
    
    async def get_canvas(self, canvas_id: UUID) -> Optional[CanvasData]:
        """
        Canvas 데이터 조회 (2-Tier 캐싱)
        
        순서:
        1. L1 캐시 확인
        2. L2 캐시 확인  
        3. 원본 소스 로드 (현재는 생략)
        """
        canvas_key = str(canvas_id)
        self._operation_counts['get'] += 1
        
        try:
            # L1 캐시 확인
            l1_data = await self._get_from_l1_canvas(canvas_key)
            if l1_data:
                self._hit_counts['l1'] += 1
                self._access_counts[canvas_key] = self._access_counts.get(canvas_key, 0) + 1
                logger.debug(f"Canvas L1 캐시 히트: {canvas_id}")
                return CanvasData(**l1_data)
            
            # L2 캐시 확인
            l2_data = await self._get_from_l2_canvas(canvas_key)
            if l2_data:
                self._hit_counts['l2'] += 1
                # L1 캐시에 저장
                await self._set_to_l1_canvas(canvas_key, l2_data)
                logger.debug(f"Canvas L2 캐시 히트: {canvas_id}")
                return CanvasData(**l2_data)
            
            # 캐시 미스
            self._hit_counts['miss'] += 1
            logger.debug(f"Canvas 캐시 미스: {canvas_id}")
            return None
            
        except Exception as e:
            logger.error(f"Canvas 캐시 조회 실패 {canvas_id}: {str(e)}")
            return None
    
    async def set_canvas(
        self, 
        canvas_id: UUID, 
        canvas_data: CanvasData,
        ttl_override: Optional[int] = None
    ) -> bool:
        """
        Canvas 데이터 저장 (2-Tier 캐싱)
        """
        canvas_key = str(canvas_id)
        self._operation_counts['set'] += 1
        
        try:
            # 데이터 직렬화
            data_dict = canvas_data.model_dump()
            
            # 크기 확인
            data_size = len(json.dumps(data_dict).encode())
            if data_size > self._max_canvas_size:
                logger.warning(f"Canvas 데이터 크기 초과: {canvas_id} - {data_size} bytes")
                return False
            
            # L1 캐시에 저장
            await self._set_to_l1_canvas(canvas_key, data_dict)
            
            # L2 캐시에 저장
            await self._set_to_l2_canvas(canvas_key, data_dict, ttl_override or self._l2_ttl)
            
            # 메타데이터 업데이트
            self._cache_sizes[canvas_key] = data_size
            
            logger.debug(f"Canvas 캐시 저장: {canvas_id} ({data_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Canvas 캐시 저장 실패 {canvas_id}: {str(e)}")
            return False
    
    async def get_sync_state(
        self, 
        canvas_id: UUID, 
        client_id: str
    ) -> Optional[CanvasSyncState]:
        """동기화 상태 조회"""
        sync_key = f"{canvas_id}:{client_id}"
        
        try:
            # L1 캐시 확인
            l1_data = await self._get_from_l1_sync(sync_key)
            if l1_data:
                return CanvasSyncState(**l1_data)
            
            # L2 캐시 확인
            l2_data = await self._get_from_l2_sync(sync_key)
            if l2_data:
                await self._set_to_l1_sync(sync_key, l2_data)
                return CanvasSyncState(**l2_data)
            
            return None
            
        except Exception as e:
            logger.error(f"동기화 상태 조회 실패 {sync_key}: {str(e)}")
            return None
    
    async def set_sync_state(
        self,
        canvas_id: UUID,
        client_id: str,
        sync_state: CanvasSyncState
    ) -> bool:
        """동기화 상태 저장"""
        sync_key = f"{canvas_id}:{client_id}"
        
        try:
            data_dict = sync_state.model_dump()
            
            # L1 캐시에 저장
            await self._set_to_l1_sync(sync_key, data_dict)
            
            # L2 캐시에 저장
            await self._set_to_l2_sync(sync_key, data_dict)
            
            logger.debug(f"동기화 상태 저장: {sync_key}")
            return True
            
        except Exception as e:
            logger.error(f"동기화 상태 저장 실패 {sync_key}: {str(e)}")
            return False
    
    async def get_events(
        self, 
        canvas_id: UUID, 
        limit: int = 100
    ) -> List[CanvasEventData]:
        """이벤트 캐시 조회"""
        event_key = f"events:{canvas_id}"
        
        try:
            # L1 캐시 확인
            l1_events = await self._get_from_l1_events(event_key)
            if l1_events:
                # 제한 적용
                events = l1_events[:limit]
                return [CanvasEventData(**event_dict) for event_dict in events]
            
            # L2 캐시 확인
            l2_events = await self._get_from_l2_events(event_key, limit)
            if l2_events:
                await self._set_to_l1_events(event_key, l2_events)
                return [CanvasEventData(**event_dict) for event_dict in l2_events]
            
            return []
            
        except Exception as e:
            logger.error(f"이벤트 캐시 조회 실패 {canvas_id}: {str(e)}")
            return []
    
    async def add_event(self, event: CanvasEventData) -> bool:
        """이벤트 캐시에 추가"""
        event_key = f"events:{event.canvas_id}"
        
        try:
            event_dict = event.model_dump()
            
            # L1 캐시 업데이트
            if event_key in self._event_cache:
                self._event_cache[event_key].insert(0, event_dict)
                # 캐시 크기 제한
                if len(self._event_cache[event_key]) > 1000:
                    self._event_cache[event_key] = self._event_cache[event_key][:1000]
            else:
                self._event_cache[event_key] = [event_dict]
            
            self._cache_timestamps[event_key] = datetime.utcnow()
            
            # L2 캐시 업데이트
            await self._add_to_l2_events(event_key, event_dict)
            
            logger.debug(f"이벤트 캐시 추가: {event.event_id}")
            return True
            
        except Exception as e:
            logger.error(f"이벤트 캐시 추가 실패: {str(e)}")
            return False
    
    async def invalidate_canvas(self, canvas_id: UUID) -> bool:
        """Canvas 캐시 무효화"""
        canvas_key = str(canvas_id)
        self._operation_counts['invalidate'] += 1
        
        try:
            # L1 캐시에서 제거
            if canvas_key in self._canvas_cache:
                del self._canvas_cache[canvas_key]
            
            if canvas_key in self._cache_timestamps:
                del self._cache_timestamps[canvas_key]
            
            if canvas_key in self._access_counts:
                del self._access_counts[canvas_key]
            
            if canvas_key in self._cache_sizes:
                del self._cache_sizes[canvas_key]
            
            # L2 캐시에서 제거
            await self._invalidate_l2_canvas(canvas_key)
            
            # 관련 동기화 상태도 무효화
            await self._invalidate_related_sync_states(canvas_id)
            
            # 이벤트 캐시 무효화
            event_key = f"events:{canvas_id}"
            if event_key in self._event_cache:
                del self._event_cache[event_key]
            
            logger.info(f"Canvas 캐시 무효화: {canvas_id}")
            return True
            
        except Exception as e:
            logger.error(f"Canvas 캐시 무효화 실패 {canvas_id}: {str(e)}")
            return False
    
    async def warm_up_cache(self, canvas_ids: List[UUID]) -> Dict[str, int]:
        """캐시 워밍업 (사전 로딩)"""
        try:
            warmed_count = 0
            failed_count = 0
            
            for canvas_id in canvas_ids:
                try:
                    # 캐시가 없는 경우에만 로드 시도
                    existing_data = await self.get_canvas(canvas_id)
                    if not existing_data:
                        # 실제로는 DB에서 로드해야 하지만
                        # 현재는 스킵
                        failed_count += 1
                    else:
                        warmed_count += 1
                        
                except Exception as e:
                    logger.warning(f"캐시 워밍업 실패 {canvas_id}: {str(e)}")
                    failed_count += 1
            
            result = {'warmed': warmed_count, 'failed': failed_count}
            logger.info(f"캐시 워밍업 완료: {result}")
            return result
            
        except Exception as e:
            logger.error(f"캐시 워밍업 실패: {str(e)}")
            return {'error': str(e)}
    
    async def cleanup_expired_cache(self) -> Dict[str, int]:
        """만료된 캐시 항목 정리"""
        try:
            current_time = datetime.utcnow()
            
            # L1 캐시 정리
            l1_cleaned = 0
            expired_canvas_keys = []
            expired_sync_keys = []
            expired_event_keys = []
            
            # Canvas 캐시 만료 확인
            for key, timestamp in self._cache_timestamps.items():
                if (current_time - timestamp).seconds > self._l1_ttl:
                    if key.startswith('events:'):
                        expired_event_keys.append(key)
                    elif ':' in key:  # sync state key
                        expired_sync_keys.append(key)
                    else:  # canvas key
                        expired_canvas_keys.append(key)
            
            # 만료된 항목들 제거
            for key in expired_canvas_keys:
                if key in self._canvas_cache:
                    del self._canvas_cache[key]
                    l1_cleaned += 1
                self._cleanup_cache_metadata(key)
            
            for key in expired_sync_keys:
                if key in self._sync_state_cache:
                    del self._sync_state_cache[key]
                    l1_cleaned += 1
                self._cleanup_cache_metadata(key)
            
            for key in expired_event_keys:
                if key in self._event_cache:
                    del self._event_cache[key]
                    l1_cleaned += 1
                self._cleanup_cache_metadata(key)
            
            # L2 캐시 정리
            l2_cleaned = await self._cleanup_l2_cache()
            
            # LRU 기반 캐시 크기 제한
            lru_cleaned = await self._enforce_cache_size_limits()
            
            result = {
                'l1_cleaned': l1_cleaned,
                'l2_cleaned': l2_cleaned,
                'lru_cleaned': lru_cleaned,
                'total_l1_size': len(self._canvas_cache) + len(self._sync_state_cache) + len(self._event_cache)
            }
            
            if l1_cleaned > 0 or l2_cleaned > 0:
                logger.info(f"캐시 정리 완료: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"캐시 정리 실패: {str(e)}")
            return {'error': str(e)}
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        try:
            total_hits = sum(self._hit_counts.values())
            hit_ratio = self._hit_counts['l1'] / total_hits if total_hits > 0 else 0
            
            l1_memory_usage = sum(
                len(json.dumps(data).encode()) 
                for data in self._canvas_cache.values()
            )
            
            return {
                'hit_counts': self._hit_counts.copy(),
                'operation_counts': self._operation_counts.copy(),
                'hit_ratio': hit_ratio,
                'l1_cache_sizes': {
                    'canvas': len(self._canvas_cache),
                    'sync_state': len(self._sync_state_cache),
                    'events': len(self._event_cache)
                },
                'l1_memory_usage': l1_memory_usage,
                'most_accessed': self._get_most_accessed_items(),
                'cache_efficiency': self._calculate_cache_efficiency(),
                'average_item_size': sum(self._cache_sizes.values()) / len(self._cache_sizes) if self._cache_sizes else 0
            }
            
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {str(e)}")
            return {'error': str(e)}
    
    # ===== L1 캐시 (메모리) 메서드 =====
    
    async def _get_from_l1_canvas(self, key: str) -> Optional[Dict[str, Any]]:
        """L1 Canvas 캐시에서 조회"""
        if key not in self._canvas_cache:
            return None
        
        # TTL 확인
        timestamp = self._cache_timestamps.get(key)
        if timestamp and (datetime.utcnow() - timestamp).seconds > self._l1_ttl:
            # 만료된 항목 제거
            del self._canvas_cache[key]
            self._cleanup_cache_metadata(key)
            return None
        
        return self._canvas_cache[key]
    
    async def _set_to_l1_canvas(self, key: str, data: Dict[str, Any]) -> None:
        """L1 Canvas 캐시에 저장"""
        self._canvas_cache[key] = data
        self._cache_timestamps[key] = datetime.utcnow()
    
    async def _get_from_l1_sync(self, key: str) -> Optional[Dict[str, Any]]:
        """L1 동기화 상태 캐시에서 조회"""
        if key not in self._sync_state_cache:
            return None
        
        timestamp = self._cache_timestamps.get(key)
        if timestamp and (datetime.utcnow() - timestamp).seconds > self._l1_ttl:
            del self._sync_state_cache[key]
            self._cleanup_cache_metadata(key)
            return None
        
        return self._sync_state_cache[key]
    
    async def _set_to_l1_sync(self, key: str, data: Dict[str, Any]) -> None:
        """L1 동기화 상태 캐시에 저장"""
        self._sync_state_cache[key] = data
        self._cache_timestamps[key] = datetime.utcnow()
    
    async def _get_from_l1_events(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """L1 이벤트 캐시에서 조회"""
        if key not in self._event_cache:
            return None
        
        timestamp = self._cache_timestamps.get(key)
        if timestamp and (datetime.utcnow() - timestamp).seconds > self._l1_ttl:
            del self._event_cache[key]
            self._cleanup_cache_metadata(key)
            return None
        
        return self._event_cache[key]
    
    async def _set_to_l1_events(self, key: str, events: List[Dict[str, Any]]) -> None:
        """L1 이벤트 캐시에 저장"""
        self._event_cache[key] = events
        self._cache_timestamps[key] = datetime.utcnow()
    
    # ===== L2 캐시 (PostgreSQL) 메서드 =====
    
    async def _get_from_l2_canvas(self, key: str) -> Optional[Dict[str, Any]]:
        """L2 Canvas 캐시에서 조회"""
        try:
            # 실제 구현 시 canvas_cache 테이블에서 조회
            logger.debug(f"L2 Canvas 캐시 조회: {key}")
            return None  # 현재는 None 반환
            
        except Exception as e:
            logger.error(f"L2 Canvas 캐시 조회 실패 {key}: {str(e)}")
            return None
    
    async def _set_to_l2_canvas(
        self, 
        key: str, 
        data: Dict[str, Any], 
        ttl: int
    ) -> bool:
        """L2 Canvas 캐시에 저장"""
        try:
            # 실제 구현 시 canvas_cache 테이블에 UPSERT
            logger.debug(f"L2 Canvas 캐시 저장: {key}")
            return True
            
        except Exception as e:
            logger.error(f"L2 Canvas 캐시 저장 실패 {key}: {str(e)}")
            return False
    
    async def _get_from_l2_sync(self, key: str) -> Optional[Dict[str, Any]]:
        """L2 동기화 상태 캐시에서 조회"""
        try:
            logger.debug(f"L2 동기화 캐시 조회: {key}")
            return None
            
        except Exception as e:
            logger.error(f"L2 동기화 캐시 조회 실패 {key}: {str(e)}")
            return None
    
    async def _set_to_l2_sync(self, key: str, data: Dict[str, Any]) -> bool:
        """L2 동기화 상태 캐시에 저장"""
        try:
            logger.debug(f"L2 동기화 캐시 저장: {key}")
            return True
            
        except Exception as e:
            logger.error(f"L2 동기화 캐시 저장 실패 {key}: {str(e)}")
            return False
    
    async def _get_from_l2_events(
        self, 
        key: str, 
        limit: int
    ) -> Optional[List[Dict[str, Any]]]:
        """L2 이벤트 캐시에서 조회"""
        try:
            logger.debug(f"L2 이벤트 캐시 조회: {key}")
            return None
            
        except Exception as e:
            logger.error(f"L2 이벤트 캐시 조회 실패 {key}: {str(e)}")
            return None
    
    async def _add_to_l2_events(self, key: str, event_dict: Dict[str, Any]) -> bool:
        """L2 이벤트 캐시에 추가"""
        try:
            logger.debug(f"L2 이벤트 캐시 추가: {key}")
            return True
            
        except Exception as e:
            logger.error(f"L2 이벤트 캐시 추가 실패 {key}: {str(e)}")
            return False
    
    async def _invalidate_l2_canvas(self, key: str) -> bool:
        """L2 Canvas 캐시 무효화"""
        try:
            logger.debug(f"L2 Canvas 캐시 무효화: {key}")
            return True
            
        except Exception as e:
            logger.error(f"L2 Canvas 캐시 무효화 실패 {key}: {str(e)}")
            return False
    
    async def _cleanup_l2_cache(self) -> int:
        """L2 캐시 정리"""
        try:
            logger.debug("L2 캐시 정리")
            return 0  # 정리된 항목 수
            
        except Exception as e:
            logger.error(f"L2 캐시 정리 실패: {str(e)}")
            return 0
    
    # ===== 유틸리티 메서드 =====
    
    def _cleanup_cache_metadata(self, key: str) -> None:
        """캐시 메타데이터 정리"""
        if key in self._cache_timestamps:
            del self._cache_timestamps[key]
        if key in self._access_counts:
            del self._access_counts[key]
        if key in self._cache_sizes:
            del self._cache_sizes[key]
    
    async def _invalidate_related_sync_states(self, canvas_id: UUID) -> None:
        """관련된 동기화 상태 무효화"""
        canvas_prefix = f"{canvas_id}:"
        expired_keys = [
            key for key in self._sync_state_cache.keys() 
            if key.startswith(canvas_prefix)
        ]
        
        for key in expired_keys:
            del self._sync_state_cache[key]
            self._cleanup_cache_metadata(key)
    
    async def _enforce_cache_size_limits(self) -> int:
        """캐시 크기 제한 강제 적용 (LRU)"""
        cleaned_count = 0
        
        # Canvas 캐시 크기 제한
        if len(self._canvas_cache) > self._max_l1_size:
            # 접근 빈도 기반 정렬
            sorted_items = sorted(
                self._access_counts.items(),
                key=lambda x: x[1]
            )
            
            remove_count = len(self._canvas_cache) - self._max_l1_size
            for key, _ in sorted_items[:remove_count]:
                if key in self._canvas_cache:
                    del self._canvas_cache[key]
                    cleaned_count += 1
                self._cleanup_cache_metadata(key)
        
        return cleaned_count
    
    def _get_most_accessed_items(self, limit: int = 10) -> List[Dict[str, Any]]:
        """가장 많이 접근된 항목들"""
        if not self._access_counts:
            return []
        
        sorted_items = sorted(
            self._access_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {'key': key, 'access_count': count}
            for key, count in sorted_items[:limit]
        ]
    
    def _calculate_cache_efficiency(self) -> float:
        """캐시 효율성 계산"""
        total_operations = sum(self._operation_counts.values())
        if total_operations == 0:
            return 0.0
        
        # 히트 비율과 작업 비율을 종합
        total_hits = self._hit_counts['l1'] + self._hit_counts['l2']
        total_requests = total_hits + self._hit_counts['miss']
        
        hit_ratio = total_hits / total_requests if total_requests > 0 else 0
        
        # L1 히트가 더 효율적이므로 가중치 적용
        l1_weight = 1.0
        l2_weight = 0.7
        
        if total_requests > 0:
            weighted_efficiency = (
                (self._hit_counts['l1'] * l1_weight + 
                 self._hit_counts['l2'] * l2_weight) / total_requests
            )
        else:
            weighted_efficiency = 0.0
        
        return min(1.0, weighted_efficiency)