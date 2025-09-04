# AI 포탈 아키텍처 설계서

## 📊 시스템 개요

### 설계 원칙
- **검증된 안정성**: SYGenai 운영 환경 검증 패턴 활용
- **확장 가능성**: 모듈화된 설계로 새 기능 추가 용이
- **성능 최적화**: Redis 없이도 고성능 보장하는 캐싱 전략
- **사용자 중심**: 직관적이고 반응성 있는 사용자 경험

### 기술 스택
```
┌─ Frontend ─────────────────────────────────────────────────┐
│ React 18+ • TypeScript • TailwindCSS • Zustand • SWR      │
├─ API Gateway ──────────────────────────────────────────────┤
│ FastAPI • Pydantic • Uvicorn • WebSocket                  │
├─ AI Agents ────────────────────────────────────────────────┤
│ LangGraph • Claude (Bedrock) • Gemini (GenerativeAI)      │
├─ Data Layer ───────────────────────────────────────────────┤
│ PostgreSQL • DynamoDB • OpenSearch • S3                   │
└─ Infrastructure ──────────────────────────────────────────┘
│ Docker • Kubernetes • GitHub Actions • AWS/GCP           │
```

---

## 🏗️ 시스템 아키텍처

### 전체 구조
```
┌─────────────────────────────────────────────────────────┐
│                   React Frontend                       │
│  ┌─────────────┬─────────────┬─────────────────────────┐  │
│  │   Sidebar   │    Chat     │       Canvas           │  │
│  └─────────────┴─────────────┴─────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                FastAPI Gateway                          │
│  WebSocket Server │ REST API │ Auth Middleware        │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                AI Agent Layer                           │
│ Supervisor → LLM Router → [Web Search|Canvas|RAG]      │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                Data & Storage                           │
│ PostgreSQL │ DynamoDB │ OpenSearch │ S3 │ Cache         │
└─────────────────────────────────────────────────────────┘
```

### 데이터 플로우
1. **사용자 요청** → Frontend (React)
2. **의도 분석** → Supervisor Agent
3. **모델 라우팅** → LLM Router (Claude/Gemini)
4. **에이전트 실행** → Worker Agent
5. **결과 반환** → WebSocket 스트리밍
6. **데이터 저장** → PostgreSQL + 캐시

---

## 💾 데이터베이스 설계

### PostgreSQL 스키마
```sql
-- 사용자
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 대화
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    title VARCHAR(500),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 메시지
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    role VARCHAR(50),
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 워크스페이스
CREATE TABLE workspaces (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(500),
    type VARCHAR(100),
    data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 캐시 테이블
CREATE TABLE cache_entries (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB,
    expires_at TIMESTAMP,
    tags TEXT[]
);
```

### 캐시 시스템 (2-tier)
```python
class CacheManager:
    """PostgreSQL + 메모리 기반 캐싱"""
    
    def __init__(self):
        self.memory_cache = {}  # L1: 빠른 메모리 캐시
        self.db = PostgreSQLCache()  # L2: 영구 DB 캐시
    
    async def get(self, key: str):
        # L1 캐시 확인
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # L2 캐시 확인
        value = await self.db.get(key)
        if value:
            self.memory_cache[key] = value
        
        return value
```

---

## 🤖 AI 에이전트 아키텍처

### Supervisor-Worker 패턴
```python
class SupervisorAgent:
    """의도 분석 및 에이전트 라우팅"""
    
    async def analyze_intent(self, message: str) -> AgentType:
        # LLM을 사용한 의도 분석
        analysis = await self.llm_router.analyze(message)
        return self.classify_agent_type(analysis)

class WorkerAgent:
    """실제 작업 수행 에이전트"""
    
    async def execute(self, task: Task) -> Result:
        # 구체적 작업 실행
        pass
```

### LLM 라우팅 전략
```python
class LLMRouter:
    """모델별 최적화된 라우팅"""
    
    def select_model(self, task_type: str, complexity: int):
        if task_type == "image_generation":
            return "gemini-2.0-pro"
        elif complexity > 8:
            return "claude-4-sonnet"
        elif task_type == "search":
            return "claude-3.5-haiku"
        else:
            return "gemini-2.0-flash"
```

---

## 🔒 보안 아키텍처

### 인증 & 권한
- **JWT 토큰**: 상태없는 인증
- **API 키 관리**: 환경변수 + 암호화 저장
- **Rate Limiting**: 사용자별 요청 제한
- **CORS 설정**: 허용된 도메인만 접근

### 데이터 보호
- **HTTPS 필수**: 모든 통신 암호화
- **입력 검증**: SQL Injection 등 방지
- **민감정보 마스킹**: 로그에서 API 키 등 제거
- **접근 로그**: 모든 API 요청 기록

---

## ⚡ 성능 최적화

### 캐싱 전략
1. **L1 메모리 캐시**: 자주 사용되는 데이터 (TTL: 5분)
2. **L2 DB 캐시**: 중간 결과 저장 (TTL: 30분)  
3. **CDN 캐싱**: 정적 파일 및 이미지

### 데이터베이스 최적화
```sql
-- 인덱스 최적화
CREATE INDEX idx_conversations_user_created 
ON conversations(user_id, created_at DESC);

CREATE INDEX idx_messages_conversation 
ON messages(conversation_id, created_at);

CREATE INDEX idx_cache_expires 
ON cache_entries(expires_at) 
WHERE expires_at IS NOT NULL;
```

### 프론트엔드 최적화
- **React.memo**: 불필요한 리렌더링 방지
- **Zustand**: 효율적인 상태 관리
- **SWR**: 데이터 페칭 최적화
- **코드 스플리팅**: 필요한 부분만 로드

---

## 🚀 배포 아키텍처

### 개발 환경
```yaml
version: '3.8'
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
  
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://...
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=aiportal
```

### 프로덕션 환경
- **컨테이너화**: Docker + Kubernetes
- **로드 밸런서**: NGINX 또는 ALB
- **데이터베이스**: 관리형 PostgreSQL (RDS)
- **모니터링**: Grafana + Prometheus
- **로깅**: ELK Stack 또는 CloudWatch

---

## 📊 모니터링 & 운영

### 핵심 메트릭
- **응답 시간**: API 엔드포인트별 평균/P95
- **에러율**: HTTP 4xx/5xx 비율
- **처리량**: 초당 요청 수 (RPS)
- **리소스 사용률**: CPU/메모리/디스크

### 알람 기준
- API 응답 시간 > 2초
- 에러율 > 5%
- CPU 사용률 > 80%
- 디스크 사용률 > 90%

---

**업데이트**: 2025-09-01  
**버전**: v2.0  
**상태**: 프로덕션 아키텍처 설계 완성