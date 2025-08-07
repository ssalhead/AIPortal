#!/usr/bin/env python3
"""
PostgreSQL 테이블 생성 스크립트
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 데이터베이스 모델들 import
from app.db.base import Base
from app.db.models.user import User
from app.db.models.conversation import Conversation, Message
from app.db.models.workspace import Workspace, Artifact
from app.db.models.cache import CacheEntry
from app.core.config import settings

async def create_tables():
    """PostgreSQL에 모든 테이블 생성"""
    
    # 비동기 데이터베이스 엔진 생성
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True  # SQL 로그 출력
    )
    
    print("🚀 PostgreSQL 테이블을 생성하는 중...")
    print(f"데이터베이스 URL: {settings.DATABASE_URL}")
    
    try:
        # 모든 테이블 생성
        async with engine.begin() as conn:
            # 기존 테이블이 있다면 삭제 (주의: 프로덕션에서는 사용 금지)
            print("기존 테이블 삭제 중...")
            await conn.run_sync(Base.metadata.drop_all)
            
            print("새 테이블 생성 중...")
            await conn.run_sync(Base.metadata.create_all)
            
        print("✅ 모든 테이블이 성공적으로 생성되었습니다!")
        print("\n생성된 테이블들:")
        print("- users (사용자)")
        print("- conversations (대화방)")
        print("- messages (메시지)")
        print("- workspaces (워크스페이스)")
        print("- artifacts (아티팩트)")
        print("- cache_entries (캐시)")
        
        # 테스트 데이터 추가
        await insert_test_data(engine)
        
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        raise
    finally:
        await engine.dispose()

async def insert_test_data(engine):
    """테스트용 기본 데이터 삽입"""
    print("\n📝 테스트 데이터 생성 중...")
    
    # 세션 팩토리 생성
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # 테스트 사용자 생성
            from werkzeug.security import generate_password_hash
            
            test_user = User(
                email="test@aiportal.com",
                username="testuser",
                full_name="Test User",
                hashed_password=generate_password_hash("testpassword"),
                is_active=True,
                is_superuser=False,
                preferences={
                    "theme": "light",
                    "language": "ko",
                    "notifications": True
                }
            )
            
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
            
            # 테스트 대화방 생성
            test_conversation = Conversation(
                user_id=test_user.id,
                title="첫 번째 대화",
                description="AI 포탈 테스트 대화",
                model="gemini",
                agent_type="web_search",
                metadata_={
                    "created_by": "system",
                    "test": True
                }
            )
            
            session.add(test_conversation)
            await session.commit()
            await session.refresh(test_conversation)
            
            # 테스트 메시지들 생성
            messages = [
                Message(
                    conversation_id=test_conversation.id,
                    role="user",
                    content="안녕하세요! AI 포탈을 테스트하고 있습니다.",
                    metadata_={"test": True}
                ),
                Message(
                    conversation_id=test_conversation.id,
                    role="assistant",
                    content="안녕하세요! 무엇을 도와드릴까요?",
                    model="gemini",
                    tokens_input=20,
                    tokens_output=15,
                    latency_ms=1200,
                    metadata_={"test": True}
                )
            ]
            
            for message in messages:
                session.add(message)
            
            await session.commit()
            
            print("✅ 테스트 데이터가 성공적으로 생성되었습니다!")
            print(f"- 테스트 사용자: {test_user.email}")
            print(f"- 테스트 대화방: {test_conversation.title}")
            print(f"- 테스트 메시지: {len(messages)}개")
            
        except Exception as e:
            print(f"❌ 테스트 데이터 생성 실패: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    print("=" * 60)
    print("        AI 포탈 PostgreSQL 데이터베이스 초기화")
    print("=" * 60)
    
    # 비동기 실행
    asyncio.run(create_tables())
    
    print("\n" + "=" * 60)
    print("        데이터베이스 초기화 완료! 🎉")
    print("=" * 60)
    print("\n다음 명령으로 서버를 시작하세요:")
    print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")