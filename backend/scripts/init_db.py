#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
Docker PostgreSQL 컨테이너가 실행 중이어야 함
"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from app.db.base import Base
from app.core.config import settings


async def init_db():
    """데이터베이스 테이블 생성"""
    print("데이터베이스 초기화 시작...")
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    
    try:
        # 엔진 생성
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=True,
        )
        
        # 모든 테이블 생성
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ 데이터베이스 테이블 생성 완료")
        
        # 엔진 종료
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_db())