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

## 🤖 LangGraph Multi-Agent 아키텍처 (v3.0)

### StateGraph 기반 워크플로우 시스템 ✅ 완성
```python
class LangGraphAgent:
    """LangGraph StateGraph 기반 에이전트"""
    
    def __init__(self):
        # PostgreSQL 체크포인터로 상태 영속성 보장
        self.checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
        self.graph = self.build_graph()
    
    def build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        
        # 노드 추가 (에러 안전 래퍼 적용)
        workflow.add_node("analyze", self.analyze_node)
        workflow.add_node("execute", self.execute_node) 
        workflow.add_node("validate", self.validate_node)
        
        # 조건부 라우팅
        workflow.add_conditional_edges(
            "analyze",
            self.should_continue,
            {"continue": "execute", "end": END}
        )
        
        return workflow.compile(checkpointer=self.checkpointer)
```

### 6개 StateGraph 에이전트 완전 구현
1. **WebSearchAgent**: 5단계 StateGraph
   ```
   쿼리분석 → 검색실행 → 결과필터링 → 콘텐츠생성 → 응답최적화
   ```

2. **CanvasAgent**: 7단계 StateGraph  
   ```
   요청분석 → 멀티모달처리 → 콘텐츠생성 → Canvas업데이트 → 품질검증 → 응답생성 → 최적화
   ```

3. **InformationGapAgent**: 8단계 StateGraph
   ```
   질문분석 → 맥락수집 → 갭식별 → 추가질문 → 답변생성 → 검증 → 개선 → 응답
   ```

4. **SupervisorAgent**: 메타-에이전트 워크플로우
   ```
   작업분석 → 에이전트선택 → 실행감독 → 결과통합 → 최적화
   ```

5. **ParallelProcessingAgent**: 병렬 처리 워크플로우
   ```
   작업분할 → 병렬실행 → 결과수집 → 통합 → 검증
   ```

6. **ToolCallingAgent**: 도구 호출 워크플로우
   ```
   도구선택 → 매개변수추출 → 실행 → 결과처리 → 응답생성
   ```

### 에러 안전 노드 래퍼 시스템
```python
def create_error_safe_node(agent_name: str, node_name: str, node_func):
    """모든 노드를 에러 안전하게 만드는 래퍼"""
    async def error_safe_wrapper(state):
        try:
            result = await node_func(state)
            return result
        except Exception as e:
            logger.error(f"[{agent_name}:{node_name}] Error: {e}")
            # Graceful fallback 처리
            return {"error": str(e), "fallback_executed": True}
    
    return error_safe_wrapper
```

### Feature Flag 100% 활성화 시스템
```python
class LangGraphFeatureFlags:
    def __init__(self):
        # 🚀 대담한 전면 활성화 설정
        self.flag_configs = {
            self.LANGGRAPH_WEB_SEARCH: {
                "enabled": True,
                "percentage": 100,  # 100% 전면 활성화
            },
            self.LANGGRAPH_CANVAS: {
                "enabled": True, 
                "percentage": 100,  # 전면 전환
            },
            # 모든 LangGraph 기능 100% 활성화
        }
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

### 🚀 LangGraph 성능 모니터링 시스템
```python
class LangGraphMonitor:
    """실시간 성능 모니터링 및 비교 시스템"""
    
    def __init__(self):
        self.performance_metrics = {}
        self.comparison_data = defaultdict(list)
    
    async def track_execution(self, agent_name: str, method: str, func, *args, **kwargs):
        """LangGraph vs Legacy 성능 비교"""
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # 성능 메트릭 수집
            self.record_metric(agent_name, method, execution_time, True)
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            self.record_metric(agent_name, method, execution_time, False)
            raise
```

### PostgreSQL 체크포인터 통합
```sql
-- LangGraph 체크포인터 테이블
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE INDEX idx_checkpoints_thread_id ON checkpoints(thread_id);
CREATE INDEX idx_checkpoints_parent_id ON checkpoints(parent_checkpoint_id);
```

---

**업데이트**: 2025-09-10  
**버전**: v3.0 (LangGraph Edition)  
**상태**: LangGraph Multi-Agent 아키텍처 완성 - 엔터프라이즈급 StateGraph 시스템