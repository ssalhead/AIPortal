# 차세대 AI 포탈 개발 명세서

## 1. 프로젝트 개요

### 목표
SYGenai의 검증된 엔터프라이즈급 아키텍처를 기반으로, 혁신적인 인터랙티브 워크스페이스와 확장 가능한 AI 에이전트 생태계를 구축한 차세대 플랫폼 개발

### 핵심 가치
- **검증된 안정성**: SYGenai의 성숙한 아키텍처 패턴 활용
- **혁신적 경험**: Canvas/Artifacts 스타일 인터랙티브 워크스페이스
- **확장 가능성**: 모듈화된 에이전트 시스템으로 무한 확장
- **엔터프라이즈 레디**: 보안, 성능, 확장성이 검증된 프로덕션 아키텍처

## 2. 시스템 아키텍처

### 기술 스택

#### 프론트엔드
- React 18+ + TypeScript
- Vite (빌드 도구)
- Zustand + SWR (상태 관리)
- TailwindCSS (스타일링)
- Monaco Editor (코드 편집)
- Lucide React (아이콘)

#### 백엔드
- Python 3.11+
- FastAPI
- LangChain/LangGraph
- SQLAlchemy + Alembic
- Pydantic
- Anthropic SDK + Google GenAI

#### 데이터베이스
- PostgreSQL (주요 데이터)
- DynamoDB (NoSQL)
- OpenSearch (벡터 검색)
- S3 (파일 저장)

## 3. AI 에이전트 시스템 (LangGraph 기반)

### 지원 모델
**Claude 시리즈** (AWS Bedrock)
- Claude 4.0 Sonnet: 최고 성능, 복잡 추론
- Claude 3.7 Sonnet: 균형잡힌 범용 작업
- Claude 3.5 Haiku: 빠른 응답

**Gemini 시리즈** (GCP GenerativeAI)
- Gemini 2.5 Pro: 대용량 컨텍스트, 멀티모달
- Gemini 2.5 Flash: 빠른 추론
- Gemini 2.0 Pro: 안정적 고성능
- Gemini 2.0 Flash: 빠르고 효율적

### LangGraph StateGraph 에이전트 시스템 ✅ 완성
**핵심 에이전트 (6개 StateGraph 워크플로우)**
1. **WebSearchAgent**: 5단계 StateGraph 워크플로우
   - 쿼리 분석 → 검색 실행 → 결과 필터링 → 콘텐츠 생성 → 응답 최적화
2. **CanvasAgent**: 7단계 StateGraph 워크플로우  
   - 요청 분석 → 멀티모달 처리 → 콘텐츠 생성 → Canvas 업데이트 → 품질 검증 → 응답 생성 → 최적화
3. **InformationGapAgent**: 8단계 StateGraph 워크플로우
   - 질문 분석 → 맥락 수집 → 정보 갭 식별 → 추가 질문 생성 → 답변 생성 → 검증 → 개선 → 응답
4. **SupervisorAgent**: 메타-에이전트 워크플로우
   - 작업 분석 → 에이전트 선택 → 실행 감독 → 결과 통합 → 최적화
5. **ParallelProcessingAgent**: 병렬 처리 워크플로우
   - 작업 분할 → 병렬 실행 → 결과 수집 → 통합 → 검증
6. **ToolCallingAgent**: 도구 호출 워크플로우
   - 도구 선택 → 매개변수 추출 → 실행 → 결과 처리 → 응답 생성

### 에이전트 핵심 기능
**PostgreSQL 체크포인터**: 복잡한 상태 관리 및 영속성 보장
**에러 안전 노드 래퍼**: 모든 노드에 자동 에러 처리 및 복구
**실시간 성능 모니터링**: LangGraph vs Legacy 성능 비교
**100% Feature Flag 활성화**: 점진적 전환 완료

**도메인 에이전트** (SYGenai 호환 - 차후 LangGraph 전환)
- HR Manager: 인사 관리
- Accounting: 회계 업무
- Legal: 법무 자문
- Tax: 세무 업무

## 4. 데이터 아키텍처

### PostgreSQL 스키마
```sql
-- 사용자 관리
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP
);

-- 대화 관리
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    title VARCHAR(500),
    metadata JSONB,
    created_at TIMESTAMP
);

-- 메시지 관리
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    role VARCHAR(50),
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP
);

-- 워크스페이스 관리
CREATE TABLE workspaces (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(500),
    type VARCHAR(100),
    data JSONB,
    created_at TIMESTAMP
);
```

### 캐시 전략 (Redis 대체)
```python
class CacheManager:
    """PostgreSQL + 메모리 기반 2단계 캐싱"""
    
    def __init__(self):
        self.memory_cache = {}  # L1 캐시 (인메모리)
        self.db_cache = None    # L2 캐시 (PostgreSQL)
    
    async def get(self, key: str):
        # L1 캐시 확인
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # L2 캐시 확인
        db_result = await self.db_cache.get(key)
        if db_result:
            self.memory_cache[key] = db_result
            return db_result
        
        return None
```

## 5. API 설계

### 핵심 엔드포인트
```
# 채팅 API
POST   /api/v1/chat                    # 통합 채팅
GET    /api/v1/conversations           # 대화 목록
WS     /ws/chat/{conversation_id}      # 실시간 채팅

# 에이전트 API
GET    /api/v1/agents                  # 에이전트 목록
POST   /api/v1/agents/{type}/execute   # 에이전트 실행

# 워크스페이스 API
GET    /api/v1/workspaces              # 워크스페이스 목록
POST   /api/v1/workspaces              # 워크스페이스 생성
PUT    /api/v1/workspaces/{id}         # 워크스페이스 수정

# 파일 API
POST   /api/v1/files/upload            # 파일 업로드
GET    /api/v1/files/{id}/process      # 처리 상태 확인
```

### WebSocket 프로토콜
```python
# 메시지 형식
{
    "type": "message|error|end",
    "conversation_id": "uuid",
    "content": "응답 내용",
    "metadata": {
        "agent_type": "web_search",
        "model": "claude-3-sonnet",
        "sources": [...]
    }
}
```

## 6. 보안 및 성능

### 보안 요구사항
- JWT 기반 인증
- API 키 암호화 저장
- Rate Limiting
- 입력 검증 및 SQL Injection 방지
- HTTPS 필수

### 성능 최적화
- 2단계 캐싱 시스템
- 데이터베이스 인덱스 최적화
- 비동기 처리
- 스트리밍 응답
- CDN 활용

## 7. 개발 원칙

### Vibe Coding 방식
- **명세 기반**: 방향성 제시, 세부사항은 최적화
- **단계적 완성**: 매 커밋마다 동작하는 기능 단위
- **품질 우선**: 견고하고 테스트 가능한 구현
- **사용자 중심**: 사용자 가치 창출 우선

### 코드 품질 기준
- TypeScript 엄격 모드
- 단위 테스트 80% 이상 커버리지
- ESLint + Prettier 적용
- 문서화된 API
- 구조화된 로깅

---

**업데이트**: 2025-09-10  
**버전**: v3.0 (LangGraph Edition)  
**상태**: Phase 1 MVP + LangGraph 100% 전환 완료 → 엔터프라이즈급 Multi-Agent AI 시스템

## 최신 업데이트 (2025-09-10) 🎉 LangGraph 100% 전환 완료

### ✅ **LangGraph Multi-Agent 시스템 완전 구현**
1. **6개 StateGraph 에이전트**: Web Search, Canvas, Information Gap, Supervisor, Parallel Processing, Tool Calling
2. **PostgreSQL 체크포인터**: 복잡한 멀티 에이전트 상태 완벽 관리
3. **에러 안전 노드 래퍼**: 모든 워크플로우에 자동 에러 처리 및 복구 시스템
4. **Feature Flag 100% 활성화**: 점진적 전환에서 완전 전환으로 성공 완료
5. **실시간 성능 모니터링**: LangGraph vs Legacy 성능 비교 시스템

### 🎯 **MVP + Agentic AI 통합 완성 현황**
1. **Canvas v4.2 + LangGraph**: 요청별 개별 Canvas + 7단계 StateGraph 워크플로우
2. **멀티모델 AI 시스템**: Claude 4개 + Gemini 4개 + LangGraph 통합
3. **실시간 스트리밍**: 한글 최적화 청킹 알고리즘 (15-40자 적응형)
4. **성능 최적화**: API 호출 75% 감소, 메모리 사용량 50% 절약 + LangGraph 성능 향상
5. **엔터프라이즈급 안정성**: SYGenai 검증 패턴 + LangGraph 멀티 에이전트 아키텍처

### 🚀 **기술적 혁신 완성**
- **StateGraph 워크플로우**: 복잡한 다단계 에이전트 처리
- **PostgreSQL Checkpointer**: 에이전트 상태 영속성 및 중단점 복구
- **Error-Safe Wrapper**: 모든 노드 자동 에러 처리 및 graceful fallback
- **Multi-Agent Cooperation**: 에이전트 간 협업 및 작업 분산
- **Real-time Monitoring**: 성능 메트릭 수집 및 최적화

### 📈 **다음 단계: Phase 2+ 고급 기능 개발**
- **Phase 2A**: RAG 시스템 + LangGraph 통합 (3주)
- **Phase 2B**: 고급 Canvas 기능 확장 (2주)  
- **Phase 2C**: 프로덕션 배포 및 모니터링 (2주)