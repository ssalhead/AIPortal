#!/usr/bin/env python3
"""
AI 포탈 전체 시스템 테스트
Mock 및 실제 API 모드 지원
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent))

async def test_system_status():
    """시스템 상태 종합 확인"""
    print("\n🔍 시스템 상태 확인")
    print("=" * 50)
    
    # 패키지 로드 테스트
    try:
        from app.core.config import settings
        print(f"✅ 설정 로드 성공")
        print(f"   - 프로젝트: {settings.PROJECT_NAME}")
        print(f"   - 버전: {settings.VERSION}")
        print(f"   - 환경: {settings.ENVIRONMENT}")
        print(f"   - Mock 인증: {settings.MOCK_AUTH_ENABLED}")
    except Exception as e:
        print(f"❌ 설정 로드 실패: {e}")
        return False
    
    # 데이터베이스 연결 테스트 (SQLite)
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.db.base import Base
        
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()
        
        print("✅ 데이터베이스 스키마 검증 완료")
    except Exception as e:
        print(f"❌ 데이터베이스 스키마 오류: {e}")
        return False
    
    # LLM 라우터 테스트
    try:
        from app.agents.llm_router import llm_router
        is_mock = llm_router.is_mock_mode()
        available_models = llm_router.get_available_models()
        
        print(f"✅ LLM 라우터 초기화 완료")
        print(f"   - Mock 모드: {'예' if is_mock else '아니오'}")
        print(f"   - 사용 가능 모델: {len(available_models)}개")
        if available_models:
            print(f"   - 모델 목록: {', '.join(available_models)}")
    except Exception as e:
        print(f"❌ LLM 라우터 오류: {e}")
        return False
    
    # 에이전트 서비스 테스트
    try:
        from app.services.agent_service import agent_service
        agents = agent_service.get_agent_info()
        
        print(f"✅ 에이전트 서비스 초기화 완료")
        print(f"   - 등록된 에이전트: {len(agents)}개")
        for agent in agents[:3]:  # 상위 3개만 표시
            status = "활성" if agent['is_enabled'] else "비활성"
            print(f"   - {agent['name']}: {status}")
    except Exception as e:
        print(f"❌ 에이전트 서비스 오류: {e}")
        return False
    
    return True

async def test_llm_responses():
    """LLM 응답 테스트"""
    print("\n🤖 LLM 응답 테스트")
    print("=" * 50)
    
    try:
        from app.agents.llm_router import llm_router
        
        test_queries = [
            ("안녕하세요", "gemini", "인사 테스트"),
            ("Python으로 웹 크롤링하는 방법을 알려주세요", "claude", "기술 질문"),
            ("AI 포탈의 기능을 설명해주세요", "gemini", "제품 설명"),
        ]
        
        for query, model, description in test_queries:
            print(f"\n📝 {description}")
            print(f"   쿼리: {query}")
            print(f"   모델: {model}")
            
            start_time = time.time()
            try:
                response, used_model = await llm_router.generate_response(model, query)
                end_time = time.time()
                
                print(f"   ✅ 응답 생성 완료 ({end_time - start_time:.2f}초)")
                print(f"   📄 사용된 모델: {used_model}")
                print(f"   📄 응답 길이: {len(response)} 문자")
                print(f"   📄 응답 미리보기: {response[:100]}...")
                
            except Exception as e:
                print(f"   ❌ 응답 생성 실패: {e}")
    
    except Exception as e:
        print(f"❌ LLM 테스트 초기화 실패: {e}")

async def test_streaming_responses():
    """스트리밍 응답 테스트"""
    print("\n🌊 스트리밍 응답 테스트")
    print("=" * 50)
    
    try:
        from app.services.agent_service import agent_service
        
        test_cases = [
            {
                "query": "AI 기술의 최근 발전에 대해 설명해주세요",
                "model": "claude-3-haiku",
                "agent_type": "general"
            },
            {
                "query": "Python 웹 프레임워크 비교",
                "model": "gemini",
                "agent_type": "technical"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔄 스트리밍 테스트 {i}")
            print(f"   쿼리: {test_case['query']}")
            print(f"   모델: {test_case['model']}")
            print(f"   에이전트: {test_case['agent_type']}")
            print(f"   응답: ", end="", flush=True)
            
            start_time = time.time()
            total_chunks = 0
            total_chars = 0
            
            try:
                async for chunk in agent_service.stream_response(**test_case):
                    print(chunk, end="", flush=True)
                    total_chunks += 1
                    total_chars += len(chunk)
                
                end_time = time.time()
                print(f"\n   ✅ 스트리밍 완료")
                print(f"   📊 총 {total_chunks}개 청크, {total_chars}자, {end_time - start_time:.2f}초")
                
            except Exception as e:
                print(f"\n   ❌ 스트리밍 실패: {e}")
    
    except Exception as e:
        print(f"❌ 스트리밍 테스트 초기화 실패: {e}")

async def test_database_operations():
    """데이터베이스 작업 테스트"""
    print("\n🗄️ 데이터베이스 작업 테스트")
    print("=" * 50)
    
    try:
        # SQLite 메모리 DB 사용
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from app.db.base import Base
        from app.repositories.user import UserRepository
        from app.repositories.conversation import ConversationRepository, MessageRepository
        from app.repositories.cache import CacheRepository
        from app.db.models.conversation import MessageRole
        
        # 데이터베이스 설정
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with AsyncSessionLocal() as session:
            # 1. 사용자 생성
            user_repo = UserRepository(session)
            user = await user_repo.create_user(
                email="test@aiportal.com",
                username="testuser",
                hashed_password="hashed123",
                full_name="테스트 사용자"
            )
            print(f"✅ 사용자 생성: {user.username}")
            
            # 2. 대화 생성
            conv_repo = ConversationRepository(session)
            conversation = await conv_repo.create_conversation(
                user_id=str(user.id),
                title="테스트 대화",
                model="claude-3-haiku"
            )
            print(f"✅ 대화 생성: {conversation.title}")
            
            # 3. 메시지 추가
            msg_repo = MessageRepository(session)
            messages = [
                ("안녕하세요, AI 포탈을 테스트하고 있습니다.", MessageRole.USER),
                ("안녕하세요! AI 포탈에 오신 것을 환영합니다. 테스트를 도와드리겠습니다.", MessageRole.ASSISTANT)
            ]
            
            for content, role in messages:
                message = await msg_repo.create_message(
                    conversation_id=str(conversation.id),
                    role=role,
                    content=content
                )
                print(f"✅ 메시지 추가: {role.value} - {content[:30]}...")
            
            # 4. 캐시 테스트
            cache_repo = CacheRepository(session)
            await cache_repo.set_value("test:key", {"status": "ok", "timestamp": "2024-01-01"})
            cached_value = await cache_repo.get_value("test:key")
            print(f"✅ 캐시 테스트: {cached_value}")
        
        await engine.dispose()
        print("✅ 데이터베이스 테스트 완료")
        
    except Exception as e:
        print(f"❌ 데이터베이스 테스트 실패: {e}")

async def test_websocket_simulation():
    """WebSocket 시뮬레이션 테스트"""
    print("\n🌐 WebSocket 시뮬레이션 테스트")
    print("=" * 50)
    
    try:
        from app.services.agent_service import agent_service
        
        # WebSocket 메시지 시뮬레이션
        websocket_messages = [
            {
                "type": "chat",
                "content": "안녕하세요, WebSocket 테스트입니다",
                "model": "claude-3-haiku",
                "agent_type": "general"
            },
            {
                "type": "chat",
                "content": "AI 포탈의 기능을 설명해주세요",
                "model": "gemini",
                "agent_type": "general"
            }
        ]
        
        for i, msg in enumerate(websocket_messages, 1):
            print(f"\n📨 WebSocket 메시지 {i} 처리")
            print(f"   내용: {msg['content']}")
            
            # 메시지 수신 시뮬레이션
            print(f"   → 메시지 수신 확인")
            
            # AI 응답 스트리밍 시뮬레이션
            print(f"   → AI 응답 스트리밍 시작...")
            print(f"   → ", end="", flush=True)
            
            chunk_count = 0
            async for chunk in agent_service.stream_response(
                query=msg["content"],
                model=msg["model"],
                agent_type=msg["agent_type"],
                conversation_id=f"test-conv-{i}"
            ):
                print(chunk, end="", flush=True)
                chunk_count += 1
            
            print(f"\n   ✅ 스트리밍 완료 ({chunk_count} 청크)")
        
    except Exception as e:
        print(f"❌ WebSocket 시뮬레이션 실패: {e}")

async def test_api_key_status():
    """API 키 상태 확인"""
    print("\n🔑 API 키 상태 확인")
    print("=" * 50)
    
    try:
        from app.core.config import settings
        
        api_keys = {
            "OpenAI": settings.OPENAI_API_KEY,
            "Anthropic": settings.ANTHROPIC_API_KEY,
            "Google": settings.GOOGLE_API_KEY
        }
        
        for provider, key in api_keys.items():
            if key and key.strip():
                masked_key = f"{key[:10]}...{key[-4:]}" if len(key) > 14 else "***"
                print(f"   ✅ {provider}: 설정됨 ({masked_key})")
            else:
                print(f"   ❌ {provider}: 미설정")
        
        # Mock 모드 상태
        from app.agents.llm_router import llm_router
        mock_mode = llm_router.is_mock_mode()
        print(f"\n   🎭 Mock 모드: {'활성' if mock_mode else '비활성'}")
        
        if mock_mode:
            print("   💡 실제 LLM API 키를 설정하면 진짜 AI 응답을 받을 수 있습니다.")
            print("   💡 설정 방법: python3 setup_api_keys.py")
    
    except Exception as e:
        print(f"❌ API 키 상태 확인 실패: {e}")

async def main():
    """메인 테스트 실행"""
    print("""
╔══════════════════════════════════════════╗
║       AI 포탈 전체 시스템 테스트         ║
╚══════════════════════════════════════════╝
""")
    
    start_time = time.time()
    
    try:
        # 시스템 상태 확인
        if not await test_system_status():
            print("\n❌ 시스템 상태 확인 실패. 테스트를 중단합니다.")
            return
        
        # API 키 상태
        await test_api_key_status()
        
        # 데이터베이스 테스트
        await test_database_operations()
        
        # LLM 응답 테스트
        await test_llm_responses()
        
        # 스트리밍 테스트
        await test_streaming_responses()
        
        # WebSocket 시뮬레이션
        await test_websocket_simulation()
        
        end_time = time.time()
        
        print(f"""
╔══════════════════════════════════════════╗
║        ✅ 전체 테스트 완료               ║
╚══════════════════════════════════════════╝

총 실행 시간: {end_time - start_time:.2f}초

🎯 다음 단계:
1. 백엔드 서버 실행: ./scripts/run_backend.sh
2. 프론트엔드 서버 실행: ./scripts/run_frontend.sh
3. WebSocket 테스트: test_websocket.html 브라우저에서 열기
4. API 문서 확인: http://localhost:8000/api/v1/docs

💡 실제 LLM API를 사용하려면:
   python3 setup_api_keys.py
""")
    
    except Exception as e:
        print(f"\n❌ 테스트 중 전체 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 비동기 테스트 실행
    asyncio.run(main())