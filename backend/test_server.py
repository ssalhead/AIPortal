#!/usr/bin/env python3
"""
백엔드 서버 간단 테스트
PostgreSQL 없이 기본 동작 확인
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent))

from app.main import app
from app.core.config import settings

# Mock 데이터베이스 세션을 위한 설정
settings.MOCK_AUTH_ENABLED = True
settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"  # 메모리 DB 사용

def test_basic_endpoints():
    """기본 엔드포인트 테스트"""
    import requests
    base_url = "http://localhost:8000"
    
    print("\n=== API 엔드포인트 테스트 ===\n")
    
    # 1. 헬스 체크
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Health Check: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health Check 실패: {e}")
    
    # 2. 루트 엔드포인트
    try:
        response = requests.get(f"{base_url}/")
        print(f"\n✅ Root Endpoint: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Root Endpoint 실패: {e}")
    
    # 3. API 문서
    try:
        response = requests.get(f"{base_url}/api/v1/docs")
        print(f"\n✅ API Documentation: {response.status_code}")
        print(f"   Swagger UI 접근 가능")
    except Exception as e:
        print(f"❌ API Documentation 실패: {e}")
    
    # 4. 에이전트 목록
    try:
        response = requests.get(f"{base_url}/api/v1/agents")
        print(f"\n✅ Agents List: {response.status_code}")
        print(f"   Available agents: {len(response.json())} agents")
    except Exception as e:
        print(f"❌ Agents List 실패: {e}")
    
    print("\n=== 테스트 완료 ===\n")

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════╗
║      AI 포탈 백엔드 서버 테스트          ║
╚══════════════════════════════════════════╝

환경 정보:
- Project: {settings.PROJECT_NAME}
- Version: {settings.VERSION}
- Environment: {settings.ENVIRONMENT}
- Mock Auth: {settings.MOCK_AUTH_ENABLED}
- API URL: http://localhost:8000

서버를 시작하려면 다른 터미널에서:
  cd backend
  python3 -m uvicorn app.main:app --reload

""")
    
    # 서버가 실행 중인지 확인
    import requests
    try:
        response = requests.get("http://localhost:8000/health", timeout=1)
        print("✅ 서버가 이미 실행 중입니다.")
        test_basic_endpoints()
    except:
        print("⚠️  서버가 실행되지 않았습니다.")
        print("다음 명령으로 서버를 시작하세요:")
        print("  cd backend && python3 -m uvicorn app.main:app --reload")