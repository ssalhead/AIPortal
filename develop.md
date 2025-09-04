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

## 3. AI 에이전트 시스템

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

### 에이전트 유형
**범용 에이전트**
- Web Search: 실시간 웹 검색
- Deep Research: 종합적 분석
- Multimodal RAG: 다중 모달 검색
- Canvas: 인터랙티브 워크스페이스

**도메인 에이전트** (SYGenai 호환)
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

**업데이트**: 2025-09-03  
**버전**: v2.3  
**상태**: Canvas 이미지 편집 시스템 안정화 완성

## 최신 업데이트 (2025-09-03)

### Canvas 이미지 편집 버그 수정 완료
1. **UUID 직렬화 오류 해결**: `safe_uuid_to_str()` 메서드로 재귀적 UUID-문자열 변환 구현
2. **Placeholder URL 404 해결**: SVG 데이터 URL 기반 fallback 시스템으로 교체
3. **날짜 포맷팅 오류 해결**: null 체크 및 기본값 처리 로직 추가
4. **이미지 표시 문제 해결**: 편집 후 새로고침 없이 즉시 이미지 표시되도록 캐시 버스팅 및 접근성 확인 구현
5. **Critical Error 수정**: `undefined.includes()` 오류로 인한 화면 화이트아웃 문제 해결

### 기술적 개선사항
- **이미지 접근성 확인**: 백엔드/프론트엔드 양쪽에서 파일 접근 가능성 검증 시스템
- **캐시 버스팅**: 타임스탬프 기반 이미지 URL 갱신으로 브라우저 캐시 문제 해결
- **React 컴포넌트 강제 리렌더링**: key 속성을 이용한 컴포넌트 업데이트 보장
- **옵셔널 체이닝**: TypeScript 안전 연산자로 null/undefined 참조 오류 방지