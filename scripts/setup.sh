#!/bin/bash

# AI 포탈 개발 환경 설정 스크립트

set -e

echo "🚀 AI 포탈 개발 환경 설정을 시작합니다..."

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 함수: 성공 메시지
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# 함수: 경고 메시지
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# 함수: 에러 메시지
error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

# Python 버전 확인
echo "Python 버전 확인 중..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1,2)
    if (( $(echo "$PYTHON_VERSION >= 3.11" | bc -l) )); then
        success "Python $PYTHON_VERSION 확인됨"
    else
        error "Python 3.11 이상이 필요합니다. 현재 버전: $PYTHON_VERSION"
    fi
else
    error "Python이 설치되어 있지 않습니다."
fi

# Node.js 버전 확인
echo "Node.js 버전 확인 중..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d "v" -f 2 | cut -d "." -f 1)
    if (( $NODE_VERSION >= 18 )); then
        success "Node.js v$NODE_VERSION 확인됨"
    else
        error "Node.js 18 이상이 필요합니다."
    fi
else
    error "Node.js가 설치되어 있지 않습니다."
fi

# pnpm 설치 확인
echo "pnpm 확인 중..."
if ! command -v pnpm &> /dev/null; then
    warning "pnpm이 설치되어 있지 않습니다. 설치를 진행합니다..."
    npm install -g pnpm
    success "pnpm 설치 완료"
else
    success "pnpm 확인됨"
fi

# Docker 확인
echo "Docker 확인 중..."
if command -v docker &> /dev/null; then
    success "Docker 확인됨"
else
    warning "Docker가 설치되어 있지 않습니다. Docker Desktop을 설치해주세요."
fi

# 환경 변수 파일 생성
if [ ! -f .env ]; then
    echo "환경 변수 파일 생성 중..."
    cp .env.example .env
    success ".env 파일 생성 완료"
    warning ".env 파일을 편집하여 필요한 API 키를 설정해주세요."
else
    success ".env 파일이 이미 존재합니다."
fi

# Python 가상환경 생성
if [ ! -d "backend/venv" ]; then
    echo "Python 가상환경 생성 중..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    cd ..
    success "Python 가상환경 생성 완료"
else
    success "Python 가상환경이 이미 존재합니다."
fi

# Docker 컨테이너 시작
echo "Docker 컨테이너를 시작하시겠습니까? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Docker 컨테이너 시작 중..."
    docker-compose up -d
    success "Docker 컨테이너 시작 완료"
else
    warning "Docker 컨테이너를 나중에 시작하려면 'docker-compose up -d'를 실행하세요."
fi

echo ""
echo "✨ 설정이 완료되었습니다!"
echo ""
echo "다음 단계:"
echo "1. .env 파일을 편집하여 필요한 API 키를 설정하세요."
echo "2. 백엔드 서버 시작: cd backend && source venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload"
echo "3. 프론트엔드 서버 시작: cd frontend && pnpm install && pnpm dev"
echo ""
success "Happy coding! 🎉"