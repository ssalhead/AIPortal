from typing import Optional, Any
from datetime import datetime, timedelta
import json
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.db.models.cache import CacheEntry


class CacheRepository(BaseRepository[CacheEntry]):
    """캐시 Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(CacheEntry, session)
    
    async def get_value(self, key: str) -> Optional[Any]:
        """캐시 값 조회"""
        result = await self.session.execute(
            select(CacheEntry).where(
                and_(
                    CacheEntry.key == key,
                    CacheEntry.expires_at > datetime.utcnow()
                )
            )
        )
        entry = result.scalar_one_or_none()
        
        if entry:
            # 히트 카운트 증가
            entry.increment_hit()
            await self.session.commit()
            
            try:
                return json.loads(entry.value)
            except json.JSONDecodeError:
                return entry.value
        
        return None
    
    async def set_value(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600
    ) -> CacheEntry:
        """캐시 값 설정"""
        # 기존 엔트리 확인
        result = await self.session.execute(
            select(CacheEntry).where(CacheEntry.key == key)
        )
        entry = result.scalar_one_or_none()
        
        # JSON으로 직렬화
        if not isinstance(value, str):
            value = json.dumps(value)
        
        if entry:
            # 기존 엔트리 업데이트
            entry.value = value
            entry.ttl_seconds = ttl_seconds
            entry.update_expiry(ttl_seconds)
            await self.session.commit()
            await self.session.refresh(entry)
            return entry
        else:
            # 새 엔트리 생성
            return await self.create(
                key=key,
                value=value,
                ttl_seconds=ttl_seconds,
                expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
                hit_count=0
            )
    
    async def delete_value(self, key: str) -> bool:
        """캐시 값 삭제"""
        result = await self.session.execute(
            delete(CacheEntry).where(CacheEntry.key == key)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def clear_expired(self) -> int:
        """만료된 캐시 엔트리 삭제"""
        result = await self.session.execute(
            delete(CacheEntry).where(CacheEntry.expires_at <= datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount
    
    async def clear_all(self) -> int:
        """모든 캐시 엔트리 삭제"""
        result = await self.session.execute(delete(CacheEntry))
        await self.session.commit()
        return result.rowcount