# AI 포탈 테스트 가이드

## 🚀 빠른 시작

### 1. 환경 설정

#### 필수 소프트웨어
- Python 3.8+ 
- Node.js 18+
- Docker (선택사항)

#### Python 패키지 설치
```bash
# 백엔드 디렉토리에서
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
python3 -m ensurepip --upgrade
pip install -r requirements.txt
```

#### Node.js 패키지 설치
```bash
# 프론트엔드 디렉토리에서
cd frontend
npm install
```

### 2. 서버 실행

#### 옵션 1: 스크립트 사용 (권장)
```bash
# 터미널 1 - 백엔드
./scripts/run_backend.sh

# 터미널 2 - 프론트엔드
./scripts/run_frontend.sh
```

#### 옵션 2: 수동 실행
```bash
# 터미널 1 - 백엔드
cd backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 터미널 2 - 프론트엔드
cd frontend
npm run dev
```

### 3. Docker 실행 (선택사항)
```bash
# PostgreSQL, Redis 등 인프라 서비스
docker-compose up -d postgres redis opensearch minio
```

## 🧪 테스트 방법

### 1. 시스템 상태 확인
```bash
cd backend
python3 simple_test.py
```

### 2. API 테스트

#### 헬스 체크
```bash
curl http://localhost:8000/health
```

#### API 문서 (Swagger UI)
브라우저에서: http://localhost:8000/api/v1/docs

#### 에이전트 목록
```bash
curl http://localhost:8000/api/v1/agents
```

### 3. WebSocket 테스트

#### 브라우저 테스트
1. `test_websocket.html` 파일을 브라우저에서 열기
2. "연결" 버튼 클릭
3. 메시지 전송 테스트

#### JavaScript 콘솔 테스트
```javascript
// 브라우저 개발자 도구 콘솔에서
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/chat/test-123?user_id=test_user');

ws.onopen = () => {
    console.log('Connected!');
    ws.send(JSON.stringify({
        type: 'chat',
        content: '안녕하세요',
        model: 'claude-3-haiku',
        agent_type: 'general'
    }));
};

ws.onmessage = (event) => {
    console.log('Received:', JSON.parse(event.data));
};
```

### 4. 통합 테스트
```bash
cd backend
python3 test_integration.py  # SQLite 메모리 DB 사용
```

## 📊 현재 구현 상태

### ✅ 완료된 기능
- **백엔드 코어**
  - FastAPI 서버 및 미들웨어
  - PostgreSQL 스키마 (users, conversations, messages, workspaces, artifacts, cache)
  - SQLAlchemy ORM 모델
  - Repository 패턴 CRUD
  
- **캐싱 시스템**
  - L1 메모리 캐시 (LRU)
  - L2 PostgreSQL 캐시
  - 2-tier 캐시 매니저
  
- **인증 시스템**
  - Mock 인증 (개발용)
  - JWT 토큰 지원
  
- **실시간 통신**
  - WebSocket 엔드포인트
  - 메시지 스트리밍
  - 연결 관리
  
- **AI 에이전트**
  - LLM 라우팅 (Claude/Gemini)
  - Web Search Agent
  - Supervisor Agent
  
- **프론트엔드 기초**
  - React + TypeScript + Vite
  - TailwindCSS
  - 기본 채팅 UI

### 🔄 진행 중
- E2E 테스트
- 프론트엔드 WebSocket 통합
- 검색 결과 구조화

### ⏳ 예정
- 파일 업로드 시스템
- 멀티모달 RAG
- 인터랙티브 워크스페이스

## 🔍 문제 해결

### Python 패키지 설치 오류
```bash
# pip 업그레이드
python3 -m ensurepip --upgrade
python3 -m pip install --upgrade pip

# 가상환경 재생성
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Node.js 패키지 오류
```bash
# node_modules 재설치
rm -rf node_modules package-lock.json
npm install
```

### 포트 충돌
```bash
# 사용 중인 포트 확인
lsof -i :8000  # 백엔드
lsof -i :5173  # 프론트엔드

# 프로세스 종료
kill -9 <PID>
```

### WebSocket 연결 실패
- CORS 설정 확인 (.env 파일)
- 방화벽/프록시 설정 확인
- 브라우저 콘솔 에러 메시지 확인

## 📁 프로젝트 구조
```
sami_v2/
├── backend/
│   ├── app/
│   │   ├── agents/         # AI 에이전트
│   │   ├── api/            # API 엔드포인트
│   │   ├── core/           # 핵심 설정
│   │   ├── db/             # 데이터베이스
│   │   ├── repositories/   # 데이터 접근
│   │   └── services/       # 비즈니스 로직
│   ├── alembic/            # DB 마이그레이션
│   ├── tests/              # 테스트
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # React 컴포넌트
│   │   ├── pages/          # 페이지
│   │   └── services/       # API 클라이언트
│   └── package.json
├── scripts/                # 실행 스크립트
├── docker-compose.yml      # Docker 설정
└── test_websocket.html     # WebSocket 테스트 페이지
```

## 🎯 다음 단계

1. **환경 변수 설정**
   - `.env` 파일에 LLM API 키 추가
   - 데이터베이스 연결 정보 확인

2. **Docker 설정**
   - PostgreSQL 실제 사용
   - Redis 캐싱 활성화

3. **프로덕션 준비**
   - HTTPS 설정
   - 로드 밸런싱
   - 모니터링 설정

## 📚 참고 문서
- [develop.md](develop.md) - 개발 명세서
- [ARCHITECTURE.md](ARCHITECTURE.md) - 시스템 아키텍처
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - 구현 가이드
- [dev_plan.md](dev_plan.md) - 개발 계획

---

**문의사항**: GitHub Issues에 등록해주세요.