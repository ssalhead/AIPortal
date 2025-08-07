#!/bin/bash
# 프론트엔드 서버 실행 스크립트

echo "╔══════════════════════════════════════════╗"
echo "║      AI 포탈 프론트엔드 서버 시작        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 스크립트 디렉토리 기준으로 프로젝트 루트 찾기
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "프로젝트 경로: $PROJECT_ROOT"
echo "프론트엔드 경로: $FRONTEND_DIR"
echo ""

# 프론트엔드 디렉토리로 이동
cd "$FRONTEND_DIR"

# node_modules 확인
if [ ! -d "node_modules" ]; then
    echo "⚠️  node_modules가 없습니다. 패키지 설치 중..."
    echo ""
    npm install
    echo ""
fi

echo "🚀 프론트엔드 서버 시작 중..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "서버 주소:"
echo "  - 프론트엔드: http://localhost:5173"
echo "  - 백엔드 API: http://localhost:8000"
echo ""
echo "종료하려면 Ctrl+C를 누르세요."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 개발 서버 실행
npm run dev