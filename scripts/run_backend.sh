#!/bin/bash
# 백엔드 서버 실행 스크립트

echo "╔══════════════════════════════════════════╗"
echo "║      AI 포탈 백엔드 서버 시작            ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 스크립트 디렉토리 기준으로 프로젝트 루트 찾기
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "프로젝트 경로: $PROJECT_ROOT"
echo "백엔드 경로: $BACKEND_DIR"
echo ""

# 백엔드 디렉토리로 이동
cd "$BACKEND_DIR"

# 가상환경 확인
if [ -d "venv" ]; then
    echo "✅ 가상환경 발견"
    source venv/bin/activate
else
    echo "⚠️  가상환경이 없습니다. 생성 중..."
    python3 -m venv venv
    source venv/bin/activate
    
    echo "📦 패키지 설치 중..."
    pip install --upgrade pip
    pip install aiosqlite  # SQLite 비동기 지원
    pip install -r requirements.txt
fi

# .env 파일 확인
if [ ! -f ".env" ]; then
    echo "⚠️  .env 파일이 없습니다. .env.example을 복사합니다."
    cp .env.example .env
fi

echo ""
echo "🚀 서버 시작 중..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "서버 주소:"
echo "  - API: http://localhost:8000"
echo "  - Docs: http://localhost:8000/api/v1/docs"
echo "  - WebSocket: ws://localhost:8000/api/v1/ws/chat/{conversation_id}"
echo ""
echo "종료하려면 Ctrl+C를 누르세요."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 서버 실행
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000