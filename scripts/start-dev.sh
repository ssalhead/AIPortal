#!/bin/bash

# AI 포탈 개발 서버 시작 스크립트

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 AI 포탈 개발 서버를 시작합니다...${NC}"

# Docker 컨테이너 확인 및 시작
echo "Docker 컨테이너 상태 확인 중..."
if ! docker-compose ps | grep -q "Up"; then
    echo "Docker 컨테이너 시작 중..."
    docker-compose up -d
    echo "컨테이너가 준비될 때까지 대기 중..."
    sleep 10
fi

# 새 터미널에서 백엔드 서버 시작
echo -e "${YELLOW}백엔드 서버를 새 터미널에서 시작합니다...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"'
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal -- bash -c "cd $(pwd)/backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -e "cd $(pwd)/backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; bash" &
    else
        echo -e "${RED}새 터미널을 열 수 없습니다. 수동으로 백엔드를 시작해주세요:${NC}"
        echo "cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows
    start cmd //c "cd backend && venv\\Scripts\\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
fi

# 새 터미널에서 프론트엔드 서버 시작
echo -e "${YELLOW}프론트엔드 서버를 새 터미널에서 시작합니다...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/frontend && pnpm dev"'
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal -- bash -c "cd $(pwd)/frontend && pnpm dev; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -e "cd $(pwd)/frontend && pnpm dev; bash" &
    else
        echo -e "${RED}새 터미널을 열 수 없습니다. 수동으로 프론트엔드를 시작해주세요:${NC}"
        echo "cd frontend && pnpm dev"
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows
    start cmd //c "cd frontend && pnpm dev"
fi

echo ""
echo -e "${GREEN}✨ 개발 서버가 시작되었습니다!${NC}"
echo ""
echo "서비스 URL:"
echo "- 프론트엔드: http://localhost:5173"
echo "- 백엔드 API: http://localhost:8000"
echo "- API 문서: http://localhost:8000/docs"
echo "- OpenSearch: http://localhost:9200"
echo "- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo "Docker 컨테이너 상태 확인: docker-compose ps"
echo "로그 확인: docker-compose logs -f [서비스명]"