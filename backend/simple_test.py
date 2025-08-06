#!/usr/bin/env python3
"""
간단한 FastAPI 서버 테스트
최소한의 의존성으로 동작 확인
"""

print("""
╔══════════════════════════════════════════╗
║        AI 포탈 서버 테스트               ║
╚══════════════════════════════════════════╝

현재 시스템 상태:
""")

# Python 버전 확인
import sys
print(f"✅ Python 버전: {sys.version}")

# 필수 모듈 확인
modules_to_check = [
    ("fastapi", "FastAPI 웹 프레임워크"),
    ("uvicorn", "ASGI 서버"),
    ("sqlalchemy", "ORM"),
    ("pydantic", "데이터 검증"),
    ("langchain", "LangChain AI 프레임워크"),
    ("websockets", "WebSocket 지원"),
]

print("\n패키지 설치 상태:")
installed = []
missing = []

for module_name, description in modules_to_check:
    try:
        __import__(module_name)
        print(f"  ✅ {module_name:15} - {description}")
        installed.append(module_name)
    except ImportError:
        print(f"  ❌ {module_name:15} - {description}")
        missing.append(module_name)

if missing:
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  필수 패키지가 설치되지 않았습니다.

다음 명령으로 패키지를 설치하세요:

1. 가상환경 생성 및 활성화:
   python3 -m venv venv
   source venv/bin/activate

2. pip 업그레이드:
   python3 -m ensurepip --upgrade
   python3 -m pip install --upgrade pip

3. 필수 패키지 설치:
   pip install -r requirements.txt

또는 개별 설치:
   pip install {' '.join(missing)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
else:
    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 모든 필수 패키지가 설치되었습니다!

서버를 시작하려면:
   python3 -m uvicorn app.main:app --reload

또는 스크립트 사용:
   ./scripts/run_backend.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

# 프로젝트 구조 확인
import os
print("\n프로젝트 구조:")
if os.path.exists("app"):
    for root, dirs, files in os.walk("app"):
        level = root.replace("app", "").count(os.sep)
        indent = " " * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = " " * 2 * (level + 1)
        for file in files[:5]:  # 각 디렉토리당 최대 5개 파일만 표시
            if file.endswith('.py'):
                print(f"{sub_indent}{file}")
        if len(files) > 5:
            print(f"{sub_indent}... ({len(files)-5} more files)")

print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 다음 단계:

1. Docker 설치 및 실행 (선택사항)
   - PostgreSQL, Redis 등 인프라 서비스

2. 환경 변수 설정
   - .env 파일에 LLM API 키 추가

3. 서버 실행
   - 백엔드: http://localhost:8000
   - 프론트엔드: http://localhost:5173

4. API 문서 확인
   - http://localhost:8000/api/v1/docs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")