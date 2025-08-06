#!/usr/bin/env python3
"""
통합 테스트 - 메모리 DB를 사용한 기본 기능 테스트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))

# SQLite 메모리 DB 사용
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.db.base import Base
from app.repositories.user import UserRepository
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.repositories.cache import CacheRepository
from app.db.models.conversation import MessageRole
from app.services.cache_manager import CacheManager


async def test_database_operations():
    """데이터베이스 기본 작업 테스트"""
    print("\n=== 데이터베이스 작업 테스트 ===\n")
    
    # SQLite 메모리 DB 엔진 생성
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 세션 생성
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with AsyncSessionLocal() as session:
        # 1. 사용자 생성 테스트
        print("1. 사용자 생성 테스트")
        user_repo = UserRepository(session)
        
        user = await user_repo.create_user(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password_123",
            full_name="Test User"
        )
        print(f"   ✅ 사용자 생성: {user.username} ({user.email})")
        
        # 2. 대화 생성 테스트
        print("\n2. 대화 생성 테스트")
        conv_repo = ConversationRepository(session)
        
        conversation = await conv_repo.create_conversation(
            user_id=str(user.id),
            title="테스트 대화",
            model="claude-3-haiku",
            agent_type="web_search"
        )
        print(f"   ✅ 대화 생성: {conversation.title}")
        
        # 3. 메시지 추가 테스트
        print("\n3. 메시지 추가 테스트")
        msg_repo = MessageRepository(session)
        
        user_msg = await msg_repo.create_message(
            conversation_id=str(conversation.id),
            role=MessageRole.USER,
            content="안녕하세요, AI 포탈 테스트입니다."
        )
        print(f"   ✅ 사용자 메시지: {user_msg.content[:30]}...")
        
        assistant_msg = await msg_repo.create_message(
            conversation_id=str(conversation.id),
            role=MessageRole.ASSISTANT,
            content="안녕하세요! AI 포탈에 오신 것을 환영합니다.",
            model="claude-3-haiku"
        )
        print(f"   ✅ AI 메시지: {assistant_msg.content[:30]}...")
        
        # 4. 캐시 테스트
        print("\n4. 캐시 작업 테스트")
        cache_repo = CacheRepository(session)
        
        # 캐시 저장
        cache_entry = await cache_repo.set_value(
            key="test_key",
            value={"test": "data", "timestamp": datetime.now().isoformat()},
            ttl_seconds=3600
        )
        print(f"   ✅ 캐시 저장: key={cache_entry.key}")
        
        # 캐시 조회
        cached_value = await cache_repo.get_value("test_key")
        print(f"   ✅ 캐시 조회: {cached_value}")
        
        # 5. 대화 목록 조회
        print("\n5. 대화 목록 조회 테스트")
        conversations = await conv_repo.get_user_conversations(str(user.id))
        print(f"   ✅ 사용자 대화 수: {len(conversations)}")
        
        for conv in conversations:
            messages = await msg_repo.get_conversation_messages(str(conv.id))
            print(f"   - {conv.title}: {len(messages)} 메시지")
    
    await engine.dispose()
    print("\n✅ 데이터베이스 테스트 완료")


async def test_cache_manager():
    """캐시 매니저 테스트"""
    print("\n=== 캐시 매니저 테스트 ===\n")
    
    cache_manager = CacheManager(l1_max_size=10, l1_ttl_seconds=60)
    
    # L1 캐시 테스트
    print("1. L1 메모리 캐시 테스트")
    
    # 데이터 저장
    test_data = {"user_id": "123", "data": "test_value"}
    await cache_manager.set("test:123", test_data)
    print(f"   ✅ 데이터 저장: {test_data}")
    
    # 데이터 조회
    cached = await cache_manager.get("test:123")
    print(f"   ✅ 데이터 조회: {cached}")
    
    # 캐시 통계
    stats = cache_manager.get_stats()
    print(f"   ✅ 캐시 통계: {stats['l1']}")
    
    # 패턴 무효화
    await cache_manager.invalidate_pattern("test:")
    print(f"   ✅ 패턴 무효화: test:*")
    
    print("\n✅ 캐시 매니저 테스트 완료")


async def test_agent_service():
    """에이전트 서비스 테스트"""
    print("\n=== 에이전트 서비스 테스트 ===\n")
    
    from app.services.agent_service import agent_service
    
    # 1. 에이전트 목록 조회
    print("1. 에이전트 목록 조회")
    agents = agent_service.get_agent_info()
    print(f"   ✅ 등록된 에이전트: {len(agents)}개")
    for agent in agents:
        status = "✅ 활성" if agent['is_enabled'] else "⏸️  비활성"
        print(f"   - {agent['name']} ({agent['id']}): {status}")
    
    # 2. 채팅 실행 테스트 (Mock)
    print("\n2. 채팅 실행 테스트")
    try:
        result = await agent_service.execute_chat(
            message="안녕하세요",
            model="gemini",
            agent_type="auto",
            user_id="test_user"
        )
        print(f"   ✅ 응답: {result['response'][:50]}...")
        print(f"   ✅ 사용 에이전트: {result['agent_used']}")
        print(f"   ✅ 사용 모델: {result['model_used']}")
    except Exception as e:
        print(f"   ⚠️  채팅 실행 오류 (API 키 필요): {e}")
    
    # 3. 스트리밍 테스트
    print("\n3. 스트리밍 응답 테스트")
    try:
        response_text = ""
        async for chunk in agent_service.stream_response(
            query="테스트 메시지",
            model="claude-3-haiku",
            agent_type="general"
        ):
            response_text += chunk
        print(f"   ✅ 스트리밍 완료: {len(response_text)} 문자")
    except Exception as e:
        print(f"   ⚠️  스트리밍 오류 (API 키 필요): {e}")
    
    print("\n✅ 에이전트 서비스 테스트 완료")


async def main():
    """메인 테스트 실행"""
    print("""
╔══════════════════════════════════════════╗
║        AI 포탈 통합 테스트               ║
╚══════════════════════════════════════════╝
""")
    
    try:
        # 데이터베이스 테스트
        await test_database_operations()
        
        # 캐시 매니저 테스트
        await test_cache_manager()
        
        # 에이전트 서비스 테스트
        await test_agent_service()
        
        print("""
╔══════════════════════════════════════════╗
║        ✅ 모든 테스트 완료               ║
╚══════════════════════════════════════════╝

다음 단계:
1. PostgreSQL Docker 컨테이너 실행
2. 실제 LLM API 키 설정 (.env 파일)
3. 백엔드 서버 실행: python3 -m uvicorn app.main:app --reload
4. 프론트엔드 서버 실행: npm run dev
5. WebSocket 테스트: http://localhost:8000/api/v1/docs
""")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # aiosqlite 설치 확인
    try:
        import aiosqlite
    except ImportError:
        print("⚠️  aiosqlite 패키지가 필요합니다.")
        print("설치: pip install aiosqlite")
        sys.exit(1)
    
    asyncio.run(main())