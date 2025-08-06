"""
2-Tier 캐싱 시스템
L1: 메모리 캐시 (LRU)
L2: PostgreSQL 캐시 테이블
"""

from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import json
import hashlib
from collections import OrderedDict
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.cache import CacheRepository


class LRUCache:
    """메모리 기반 LRU 캐시"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[tuple[Any, datetime]]:
        """캐시에서 값 조회"""
        if key in self.cache:
            # LRU: 최근 사용된 항목을 끝으로 이동
            value, expires_at = self.cache.pop(key)
            
            # 만료 확인
            if expires_at > datetime.utcnow():
                self.cache[key] = (value, expires_at)
                self.hits += 1
                return value, expires_at
            else:
                # 만료된 항목은 제거
                self.misses += 1
                return None
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """캐시에 값 설정"""
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        # 기존 키가 있으면 제거
        if key in self.cache:
            self.cache.pop(key)
        
        # 새 항목 추가
        self.cache[key] = (value, expires_at)
        
        # 크기 제한 확인
        if len(self.cache) > self.max_size:
            # 가장 오래된 항목 제거 (LRU)
            self.cache.popitem(last=False)
    
    def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        if key in self.cache:
            self.cache.pop(key)
            return True
        return False
    
    def clear(self):
        """캐시 전체 삭제"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%"
        }


class CacheManager:
    """2-Tier 캐시 매니저"""
    
    def __init__(
        self,
        l1_max_size: int = 1000,
        l1_ttl_seconds: int = 300,  # 5분
        l2_ttl_seconds: int = 3600,  # 1시간
    ):
        self.l1_cache = LRUCache(max_size=l1_max_size)
        self.l1_ttl = l1_ttl_seconds
        self.l2_ttl = l2_ttl_seconds
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """캐시 키 생성"""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        
        key_string = ":".join(key_parts)
        
        # 키가 너무 길면 해시 사용
        if len(key_string) > 250:
            hash_value = hashlib.sha256(key_string.encode()).hexdigest()[:16]
            return f"{prefix}:{hash_value}"
        
        return key_string
    
    async def get(
        self,
        key: str,
        session: Optional[AsyncSession] = None
    ) -> Optional[Any]:
        """캐시에서 값 조회 (L1 → L2)"""
        
        # L1 캐시 확인
        l1_result = self.l1_cache.get(key)
        if l1_result:
            value, _ = l1_result
            return value
        
        # L2 캐시 확인 (PostgreSQL)
        if session:
            cache_repo = CacheRepository(session)
            l2_value = await cache_repo.get_value(key)
            
            if l2_value is not None:
                # L1 캐시에도 저장
                self.l1_cache.set(key, l2_value, self.l1_ttl)
                return l2_value
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        session: Optional[AsyncSession] = None,
        ttl_seconds: Optional[int] = None
    ):
        """캐시에 값 설정 (L1 + L2)"""
        l1_ttl = ttl_seconds or self.l1_ttl
        l2_ttl = ttl_seconds or self.l2_ttl
        
        # L1 캐시에 저장
        self.l1_cache.set(key, value, l1_ttl)
        
        # L2 캐시에 저장 (PostgreSQL)
        if session:
            cache_repo = CacheRepository(session)
            await cache_repo.set_value(key, value, l2_ttl)
    
    async def delete(
        self,
        key: str,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """캐시에서 값 삭제 (L1 + L2)"""
        l1_deleted = self.l1_cache.delete(key)
        l2_deleted = False
        
        if session:
            cache_repo = CacheRepository(session)
            l2_deleted = await cache_repo.delete_value(key)
        
        return l1_deleted or l2_deleted
    
    async def invalidate_pattern(
        self,
        pattern: str,
        session: Optional[AsyncSession] = None
    ):
        """패턴에 맞는 캐시 무효화"""
        # L1 캐시에서 패턴 매칭 키 삭제
        keys_to_delete = [
            key for key in self.l1_cache.cache.keys()
            if pattern in key
        ]
        for key in keys_to_delete:
            self.l1_cache.delete(key)
        
        # L2는 필요시 구현
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        return {
            "l1": self.l1_cache.stats(),
            "l2": "PostgreSQL cache (stats available via DB query)"
        }
    
    async def start_cleanup_task(self, session_factory):
        """주기적 정리 작업 시작"""
        async def cleanup():
            while True:
                try:
                    await asyncio.sleep(300)  # 5분마다
                    
                    # L2 캐시 만료 항목 정리
                    async with session_factory() as session:
                        cache_repo = CacheRepository(session)
                        deleted_count = await cache_repo.clear_expired()
                        if deleted_count > 0:
                            print(f"Cleaned up {deleted_count} expired cache entries")
                            
                except Exception as e:
                    print(f"Cache cleanup error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup())
    
    async def stop_cleanup_task(self):
        """정리 작업 중지"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass


# 전역 캐시 매니저 인스턴스
cache_manager = CacheManager()