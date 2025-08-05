# AI 포탈 (AI Portal)

차세대 지능형 내부 자동화 플랫폼

## 프로젝트 개요

AI 포탈은 회사 내부 사용자를 위한 통합 AI 솔루션입니다. 다양한 AI 에이전트 서비스를 제공하고, 사용자가 AI와 협업하여 실질적인 결과물을 생성할 수 있는 확장 가능한 생태계를 구축합니다.

## 주요 기능

- 🤖 **다양한 AI 에이전트**: Web Search, Deep Research, Multimodal RAG 등
- 🎨 **인터랙티브 워크스페이스**: Canvas/Artifacts 스타일의 협업 공간
- 🔍 **하이브리드 검색**: 키워드 + 시맨틱 검색 결합
- 🚀 **실시간 스트리밍**: WebSocket 기반 실시간 응답
- 📊 **다중 LLM 지원**: Gemini, Claude 모델 동적 라우팅

## 기술 스택

### 백엔드
- Python 3.11+
- FastAPI
- LangChain / LangGraph
- PostgreSQL, DynamoDB, OpenSearch
- Redis

### 프론트엔드
- React 18+
- TypeScript
- Vite
- Tailwind CSS

## 시작하기

### 사전 요구사항

- Python 3.11 이상
- Node.js 18 이상
- Docker & Docker Compose
- Git

### 설치 방법

1. 저장소 클론
```bash
git clone <repository-url>
cd ai-portal
```

2. 환경변수 설정
```bash
cp .env.example .env
# .env 파일을 편집하여 필요한 값 설정
```

3. 개발 환경 실행
```bash
# Docker 컨테이너 시작
docker-compose up -d

# 백엔드 서버 실행
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 프론트엔드 서버 실행
cd frontend
pnpm install
pnpm dev
```

4. 브라우저에서 http://localhost:5173 접속

## 프로젝트 구조

```
ai-portal/
├── backend/          # FastAPI 백엔드
├── frontend/         # React 프론트엔드
├── docker/          # Docker 설정 파일
├── docs/            # 프로젝트 문서
├── scripts/         # 유틸리티 스크립트
├── tests/           # 테스트 파일
├── develop.md       # 개발 명세서
├── dev_plan.md      # 개발 실행 계획
└── CLAUDE.md        # Claude Code 가이드
```

## 개발 문서

- [개발 명세서](./develop.md) - 상세한 기술 명세
- [개발 계획](./dev_plan.md) - 단계별 개발 계획
- [API 문서](http://localhost:8000/docs) - FastAPI 자동 생성 문서

## 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m '기능: 놀라운 기능 추가'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 라이선스

이 프로젝트는 내부 사용 목적으로 개발되었습니다.

## 문의

프로젝트 관련 문의사항은 개발팀에 연락주세요.