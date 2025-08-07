#!/bin/bash
# AI 포탈 빠른 설정 스크립트

echo "╔══════════════════════════════════════════╗"
echo "║        AI 포탈 빠른 설정                 ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 현재 디렉토리 확인
if [ ! -f "backend/app/main.py" ]; then
    echo "❌ 올바른 프로젝트 디렉토리에서 실행해주세요."
    echo "   현재 위치에서 backend/app/main.py 파일을 찾을 수 없습니다."
    exit 1
fi

echo "✅ 프로젝트 디렉토리 확인 완료"

# Python 가상환경 설정
echo ""
echo "🐍 Python 환경 설정..."

cd backend

# 기존 가상환경 확인
if [ -d "venv" ]; then
    echo "✅ 기존 가상환경 발견"
else
    echo "📦 새 가상환경 생성 중..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ 가상환경 생성 실패"
        echo "   python3-venv 패키지를 설치해주세요:"
        echo "   sudo apt install python3-venv  # Ubuntu/Debian"
        exit 1
    fi
fi

# 가상환경 활성화
source venv/bin/activate
echo "✅ 가상환경 활성화 완료"

# pip 업그레이드
echo ""
echo "📦 pip 업그레이드..."
python3 -m pip install --upgrade pip

# 필수 패키지 설치
echo ""
echo "📦 필수 패키지 설치..."
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv aiosqlite

# 추가 패키지 (선택사항)
echo ""
echo "📦 추가 패키지 설치..."
pip install sqlalchemy alembic websockets

# 개발 도구 (선택사항)
echo ""
echo "📦 개발 도구 설치..."
pip install pytest black ruff

echo ""
echo "✅ 패키지 설치 완료!"

# 환경 변수 파일 확인
echo ""
echo "⚙️ 환경 설정 확인..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ .env 파일 생성 완료"
    else
        echo "⚠️  .env.example 파일이 없습니다"
    fi
else
    echo "✅ .env 파일 존재"
fi

# 시스템 테스트 실행
echo ""
echo "🧪 시스템 테스트 실행..."
python3 test_full_system.py

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║        🎉 설정 완료!                    ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "다음 단계:"
echo "1. 백엔드 서버 실행:"
echo "   ./scripts/run_backend.sh"
echo ""
echo "2. 새 터미널에서 프론트엔드 실행:"
echo "   ./scripts/run_frontend.sh"
echo ""
echo "3. API 문서 확인:"
echo "   http://localhost:8000/api/v1/docs"
echo ""
echo "4. WebSocket 테스트:"
echo "   test_websocket.html 파일을 브라우저에서 열기"
echo ""
echo "💡 실제 LLM API 사용하려면:"
echo "   cd backend && python3 setup_api_keys.py"