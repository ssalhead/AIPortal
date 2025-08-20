# 차세대 AI 포탈 개발 명세서
## SYGenai 검증 패턴 기반 통합 시스템

## 1. 프로젝트 개요

### 프로젝트명
차세대 지능형 내부 자동화 플랫폼 (Next-Gen AI Portal)

### 프로젝트 목표
**기존 SYGenai의 검증된 엔터프라이즈급 아키텍처**를 기반으로, 혁신적인 **인터랙티브 워크스페이스**와 **확장 가능한 AI 에이전트 생태계**를 구축하여, 사용자가 AI와 협업하여 실질적인 결과물을 생성하는 차세대 플랫폼을 개발

### 핵심 가치 제안
1. **검증된 안정성**: 운영 중인 SYGenai의 성숙한 아키텍처 패턴 활용
2. **혁신적 경험**: Canvas/Artifacts 스타일 인터랙티브 워크스페이스
3. **확장 가능성**: 모듈화된 에이전트 시스템으로 무한 확장
4. **엔터프라이즈 레디**: 보안, 성능, 확장성이 검증된 프로덕션 아키텍처

### 개발 철학 - 검증된 혁신 (Proven Innovation)
- **기존 검증 패턴 최대 활용**: SYGenai의 안정적 아키텍처 패턴 재사용
- **점진적 혁신 도입**: 안정적 기반 위에 새로운 기능을 단계별로 추가
- **품질 우선**: 검증된 코드 품질과 보안 수준 유지
- **사용자 중심**: 실제 사용 패턴을 기반으로 한 UI/UX 개선

## 2. 통합 시스템 아키텍처

### 2.1 하이브리드 아키텍처 (SYGenai + Innovation)
```
┌─────────────────────────────────────────────────────────────────┐
│  React UI (기존 채팅 + 새로운 워크스페이스)                        │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Gateway (SYGenai 검증 미들웨어 + 새로운 워크스페이스 API)  │
├─────────────────────┬───────────────────┬───────────────────────┤
│  AI Agent Service   │  MCP Bridge       │  Workspace Service    │
│  (LangChain 체인)   │  (검증된 프로토콜)  │  (새로운 협업 엔진)     │
├─────────────────────┼───────────────────┼───────────────────────┤
│  Vector Store       │  Cache Layer      │  Artifact Store       │
│  (OpenSearch)       │  (Redis)          │  (S3 + PostgreSQL)    │
└─────────────────────┴───────────────────┴───────────────────────┘
```

### 2.2 레이어별 기술 스택
#### 프론트엔드 (검증된 스택 + 새로운 도구)
- **React 18+** + TypeScript (SYGenai 검증)
- **Vite** (빌드 최적화)
- **Zustand** + SWR (상태 관리, SYGenai 패턴)
- **TailwindCSS** (일관된 디자인 시스템)
- **Monaco Editor** (코드 편집, 새로운 기능)
- **React Beautiful DnD** (인터랙티브 UI)
- **Lucide React** (아이콘 시스템)

#### 백엔드 (SYGenai 검증 스택 확장)
- **Python 3.11+**
- **FastAPI** (SYGenai 검증 미들웨어 포함)
- **LangChain 0.3+ / LangGraph** (기존 체인 + 새로운 Supervisor)
- **SQLAlchemy** + Alembic (데이터 모델링)
- **Pydantic** (타입 안전성)
- **Anthropic SDK** + **Google GenAI** (멀티 모델)

#### AI 에이전트 시스템 (하이브리드 접근)
- **기존 검증 에이전트**: 회계, 법무, 세무, 인사 (SYGenai 체인)
- **새로운 범용 에이전트**: Web Search, Deep Research, RAG (Supervisor-Worker)
- **통합 라우터**: 의도 분석 기반 에이전트 선택

## 3. AI 에이전트 생태계 설계

### 3.1 통합 에이전트 아키텍처

#### 하이브리드 패턴 (검증 + 혁신)
```python
class UnifiedAgentSystem:
    def __init__(self):
        # 기존 검증된 도메인 에이전트 (SYGenai 패턴)
        self.domain_agents = {
            'hr_manager': HRManagerAgent(),      # MCP 프로토콜 기반
            'accounting': AccountingAgent(),     # OpenSearch 체인
            'legal': LegalAgent(),              # Google Gemini 최적화
            'tax': TaxAgent(),                  # 세무 전문 체인
        }
        
        # 새로운 범용 에이전트 (Supervisor-Worker)
        self.universal_agents = {
            'web_search': WebSearchAgent(),
            'deep_research': DeepResearchAgent(),
            'multimodal_rag': MultimodalRAGAgent(),
            'code_assistant': CodeAssistantAgent(),
        }
        
        self.supervisor = HybridSupervisor()  # 통합 의도 분석
        self.llm_router = EnhancedLLMRouter()  # 멀티 모델 라우팅
```

#### 최적화된 LLM 라우팅 전략 (사용자 지정 모델 한정)
**지원 모델 목록**:
- **Claude 4.0 Sonnet** (AWS Bedrock): 최고 성능 복잡한 추론 및 분석
- **Claude 3.7 Sonnet** (AWS Bedrock): 균형잡힌 성능의 범용 작업
- **Claude 3.5 Haiku** (AWS Bedrock): 빠른 응답이 필요한 간단한 작업
- **Gemini 2.5 Pro** (GCP GenerativeAI): 대용량 컨텍스트 처리 및 멀티모달
- **Gemini 2.5 Flash** (GCP GenerativeAI): 빠른 추론 및 실시간 처리  
- **Gemini 2.0 Pro** (GCP GenerativeAI): 안정적인 고성능 모델
- **Gemini 2.0 Flash** (GCP GenerativeAI): 빠르고 효율적인 모델

**라우팅 전략**:
```python
class OptimizedLLMRouter:
    def __init__(self):
        self.claude_client = BedrockClient()  # AWS Bedrock
        self.gemini_client = GenerativeAIClient()  # GCP GenerativeAI
        
    def route_request(self, task_type: str, context_length: int) -> str:
        # 작업 유형별 최적 모델 선택
        if task_type == "complex_analysis":
            return "claude-4.0-sonnet"
        elif task_type == "balanced_reasoning":
            return "claude-3.7-sonnet"
        elif task_type == "quick_response":
            return "claude-3.5-haiku" if context_length < 4000 else "gemini-2.0-flash"
        elif task_type == "multimodal":
            return "gemini-2.5-pro"
        elif context_length > 100000:
            return "gemini-2.5-pro"  # 대용량 컨텍스트
        else:
            return "gemini-2.5-flash"  # 기본 고속 처리
```

#### 에이전트 분류 및 역할

**1. Tier1 도메인 전문 에이전트** (관리자 설정 가능한 MCP 기반)
- **Regulations Agent**: 규정 해석 및 컴플라이언스 지원
- **Legal Agent**: 법무 자문 및 계약 검토
- **Accounting Agent**: 회계 처리 및 재무 분석
- **Tax Agent**: 세무 신고 및 세법 해석

**MCP 설정 시스템**:
```python
class Tier1AgentMCPConfig:
    def __init__(self):
        self.config_store = PostgreSQLConfigStore()
    
    async def get_agent_config(self, agent_type: str, user_id: str) -> Dict:
        # 관리자가 설정한 MCP 서버 정보 조회
        base_config = await self.config_store.get_base_config(agent_type)
        user_permissions = await self.config_store.get_user_permissions(user_id, agent_type)
        
        return {
            "mcp_server_url": base_config["server_url"],
            "available_tools": user_permissions["allowed_tools"],
            "data_sources": user_permissions["accessible_sources"],
            "output_format": base_config["default_format"]
        }
    
    async def update_agent_config(self, agent_type: str, config: Dict, admin_user: str):
        # 관리자 권한 확인 후 MCP 설정 업데이트
        if not await self.verify_admin_permissions(admin_user, agent_type):
            raise PermissionError("Admin access required")
        
        await self.config_store.update_config(agent_type, config)
```

**2. 새미 GPT (범용 AI 에이전트)** - 사용자 토글 기능 제공

**핵심 기능** (사용자가 개별 토글 가능):
- **Deep Research** 🔬: 다단계 심화 연구 및 구조화된 보고서 생성
- **Web Search** 🌐: 실시간 웹 검색 및 최신 정보 통합
- **Canvas Mode** 🎨: 인터랙티브 워크스페이스 및 협업 도구

**토글 시스템 설계**:
```python
class SamiGPTFeatureManager:
    def __init__(self):
        self.user_preferences = UserPreferenceStore()
    
    async def get_user_features(self, user_id: str) -> Dict[str, bool]:
        preferences = await self.user_preferences.get(user_id)
        return {
            "deep_research": preferences.get("enable_deep_research", True),
            "web_search": preferences.get("enable_web_search", True),
            "canvas_mode": preferences.get("enable_canvas_mode", True)
        }
    
    async def toggle_feature(self, user_id: str, feature: str, enabled: bool):
        await self.user_preferences.update(user_id, {f"enable_{feature}": enabled})
        
    async def create_agent_chain(self, user_id: str, request_type: str):
        features = await self.get_user_features(user_id)
        
        # 활성화된 기능에 따라 동적 체인 구성
        chain_components = []
        if features["deep_research"] and request_type == "research":
            chain_components.append(DeepResearchAgent())
        if features["web_search"] and request_type in ["search", "current_info"]:
            chain_components.append(WebSearchAgent())
        if features["canvas_mode"] and request_type == "collaborative":
            chain_components.append(CanvasAgent())
            
        return SupervisorAgent(components=chain_components)
```

### 3.2 최적화된 데이터 아키텍처

#### Redis 대체 최적화된 데이터 전략

**Redis 제약으로 인한 대체 솔루션**:
```
┌─────────────────┬─────────────────┬─────────────────┐
│   Hot Data      │   Warm Data     │   Cold Data     │
│   (실시간)       │   (세션)         │   (장기보관)     │
├─────────────────┼─────────────────┼─────────────────┤
│ PostgreSQL +    │ DynamoDB        │ PostgreSQL      │
│ Connection Pool │ - 대화 기록      │ - 사용자 정보    │
│ - 채팅 상태      │ - 에이전트 상태   │ - 워크스페이스   │
│ - 세션 캐시      │ - 임시 파일      │ - 권한 관리      │
│ - 실시간 협업    │ - 워크플로우 상태 │ - 설정 정보      │
└─────────────────┴─────────────────┴─────────────────┘
```

**Redis 대체 구현 전략**:
```python
class OptimizedCacheManager:
    """Redis 없이 PostgreSQL 기반 고성능 캐싱"""
    
    def __init__(self):
        # 연결 풀 최적화 - SYGenai 패턴 활용
        self.pg_pool = ConnectionPoolManager(
            min_connections=20,
            max_connections=100,
            connection_timeout=5.0
        )
        
        # 인메모리 L1 캐시 (애플리케이션 레벨)
        self.memory_cache = TTLCache(maxsize=10000, ttl=300)  # 5분 TTL
        
    async def get_cached_data(self, key: str) -> Optional[Any]:
        # L1: 메모리 캐시 확인
        if key in self.memory_cache:
            return self.memory_cache[key]
            
        # L2: PostgreSQL 캐시 테이블 확인
        async with self.pg_pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT data FROM cache_table WHERE key = $1 AND expires_at > NOW()",
                key
            )
            if result:
                data = json.loads(result['data'])
                self.memory_cache[key] = data  # L1 캐시에 저장
                return data
        
        return None
    
    async def set_cached_data(self, key: str, data: Any, ttl: int = 300):
        # L1: 메모리 캐시 저장
        self.memory_cache[key] = data
        
        # L2: PostgreSQL 영속 저장
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        async with self.pg_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO cache_table (key, data, expires_at) "
                "VALUES ($1, $2, $3) "
                "ON CONFLICT (key) DO UPDATE SET data = $2, expires_at = $3",
                key, json.dumps(data), expires_at
            )

# 실시간 협업을 위한 WebSocket 상태 관리
class WebSocketStateManager:
    def __init__(self, cache_manager: OptimizedCacheManager):
        self.cache = cache_manager
        self.active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
    
    async def join_workspace(self, workspace_id: str, websocket: WebSocket, user_id: str):
        self.active_connections[workspace_id].add(websocket)
        
        # 사용자 상태를 캐시에 저장 (Redis 대체)
        await self.cache.set_cached_data(
            f"ws_user:{workspace_id}:{user_id}",
            {"status": "active", "joined_at": time.time()},
            ttl=3600
        )
    
    async def broadcast_to_workspace(self, workspace_id: str, message: Dict):
        connections = self.active_connections.get(workspace_id, set())
        for websocket in connections.copy():
            try:
                await websocket.send_json(message)
            except Exception:
                connections.discard(websocket)
```

#### 벡터 저장소 (검증된 OpenSearch 활용)
- **AWS OpenSearch** (SYGenai 검증 구성)
- **하이브리드 검색**: BM25 + 시맨틱 유사도 (검증된 알고리즘)
- **도메인별 인덱스**: 회계, 법무, 세무, 일반 지식 분리
- **실시간 임베딩**: Sentence Transformers 최적화

#### 관계형 데이터베이스 (PostgreSQL) - 통합 스키마

**핵심 스키마 설계**:
```sql
-- 사용자 및 인증 (SYGenai 호환 확장)
CREATE TABLE users (
    empno VARCHAR(20) PRIMARY KEY,
    name_ko VARCHAR(100) NOT NULL,
    company VARCHAR(100),
    company_code VARCHAR(10),
    roles JSONB DEFAULT '[]',
    permissions JSONB DEFAULT '{}',
    profile_data JSONB DEFAULT '{}',  -- 자동 수집된 프로파일
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 캐시 테이블 (Redis 대체)
CREATE TABLE cache_table (
    key VARCHAR(255) PRIMARY KEY,
    data JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_cache_expires ON cache_table(expires_at);

-- 워크스페이스 및 협업
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_empno VARCHAR(20) REFERENCES users(empno),
    title VARCHAR(200) NOT NULL,
    settings JSONB DEFAULT '{}',
    collaborators JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 아티팩트 (워크스페이스 결과물)
CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id),
    type VARCHAR(50) NOT NULL,  -- 'document', 'code', 'chart', etc.
    title VARCHAR(200),
    content JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    created_by VARCHAR(20) REFERENCES users(empno),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tier1 에이전트 MCP 설정
CREATE TABLE agent_mcp_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL,  -- 'regulations', 'legal', 'accounting', 'tax'
    config_data JSONB NOT NULL,
    created_by VARCHAR(20) REFERENCES users(empno),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(agent_type)
);

-- 사용자별 에이전트 권한
CREATE TABLE user_agent_permissions (
    empno VARCHAR(20) REFERENCES users(empno),
    agent_type VARCHAR(50),
    permissions JSONB DEFAULT '{}',
    granted_by VARCHAR(20) REFERENCES users(empno),
    granted_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (empno, agent_type)
);

-- 새미 GPT 기능 설정
CREATE TABLE user_feature_preferences (
    empno VARCHAR(20) PRIMARY KEY REFERENCES users(empno),
    enable_deep_research BOOLEAN DEFAULT true,
    enable_web_search BOOLEAN DEFAULT true,
    enable_canvas_mode BOOLEAN DEFAULT true,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 사용자 프로파일 자동 수집 로그
CREATE TABLE profile_collection_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empno VARCHAR(20) REFERENCES users(empno),
    data_source VARCHAR(100),  -- 'chat_interaction', 'file_upload', 'workspace_activity'
    collected_data JSONB,
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 활동 로그 (협업 추적)
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empno VARCHAR(20) REFERENCES users(empno),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT NOW()
);

-- 성능 최적화 인덱스
CREATE INDEX idx_workspaces_owner ON workspaces(owner_empno);
CREATE INDEX idx_artifacts_workspace ON artifacts(workspace_id);
CREATE INDEX idx_artifacts_created_by ON artifacts(created_by);
CREATE INDEX idx_activity_logs_user ON activity_logs(empno, timestamp);
CREATE INDEX idx_profile_logs_user ON profile_collection_logs(empno, created_at);
```

**사용자 프로파일 자동 수집 시스템**:
```python
class UserProfileCollector:
    """사용자 상호작용을 통한 자동 프로파일 수집"""
    
    def __init__(self, db_pool, cache_manager):
        self.db = db_pool
        self.cache = cache_manager
        self.ml_analyzer = ProfileMLAnalyzer()
    
    async def collect_from_chat(self, empno: str, message: str, response: str):
        """채팅 상호작용에서 프로파일 정보 추출"""
        # ML 기반 의도 및 선호도 분석
        analysis = await self.ml_analyzer.analyze_interaction(message, response)
        
        if analysis['confidence'] > 0.7:
            await self.store_profile_data(empno, 'chat_interaction', analysis)
    
    async def collect_from_file_upload(self, empno: str, file_metadata: Dict):
        """파일 업로드 패턴에서 업무 도메인 추출"""
        domain_hints = {
            'xlsx': 'accounting',
            'pdf': 'legal_documents',
            'py': 'development',
            'sql': 'data_analysis'
        }
        
        file_ext = file_metadata.get('extension', '').lower()
        if file_ext in domain_hints:
            profile_data = {
                'work_domain': domain_hints[file_ext],
                'technical_level': 'advanced' if file_ext in ['py', 'sql'] else 'basic'
            }
            
            await self.store_profile_data(empno, 'file_upload', profile_data)
    
    async def collect_from_workspace_activity(self, empno: str, activity_type: str, details: Dict):
        """워크스페이스 활동에서 협업 패턴 추출"""
        collaboration_patterns = await self.ml_analyzer.analyze_collaboration(activity_type, details)
        
        if collaboration_patterns:
            await self.store_profile_data(empno, 'workspace_activity', collaboration_patterns)
    
    async def store_profile_data(self, empno: str, source: str, data: Dict):
        """프로파일 데이터 저장 및 사용자 프로파일 업데이트"""
        confidence = data.pop('confidence', 0.8)
        
        # 수집 로그 저장
        async with self.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO profile_collection_logs (empno, data_source, collected_data, confidence_score) "
                "VALUES ($1, $2, $3, $4)",
                empno, source, json.dumps(data), confidence
            )
        
        # 사용자 프로파일 업데이트 (높은 신뢰도만)
        if confidence > 0.8:
            await self.update_user_profile(empno, data)
    
    async def update_user_profile(self, empno: str, new_data: Dict):
        """누적된 데이터로 사용자 프로파일 업데이트"""
        async with self.db.acquire() as conn:
            # 기존 프로파일 조회
            current = await conn.fetchrow(
                "SELECT profile_data FROM users WHERE empno = $1", empno
            )
            
            if current and current['profile_data']:
                profile = dict(current['profile_data'])
            else:
                profile = {}
            
            # 새로운 데이터 병합 (가중 평균 적용)
            profile = self._merge_profile_data(profile, new_data)
            
            # 프로파일 업데이트
            await conn.execute(
                "UPDATE users SET profile_data = $1, updated_at = NOW() WHERE empno = $2",
                json.dumps(profile), empno
            )
            
            # 캐시 무효화
            await self.cache.invalidate_key(f"user_profile:{empno}")
    
    def _merge_profile_data(self, existing: Dict, new: Dict) -> Dict:
        """가중 평균을 사용한 프로파일 데이터 병합"""
        # 구현 로직: 빈도, 최신성, 신뢰도 기반 가중치 적용
        merged = existing.copy()
        
        for key, value in new.items():
            if key in merged:
                # 기존 값과 새 값의 가중 평균 계산
                if isinstance(value, (int, float)):
                    merged[key] = (merged[key] * 0.7 + value * 0.3)
                elif isinstance(value, str):
                    # 문자열은 최신 값 우선 또는 빈도 기반 선택
                    merged[key] = value  # 단순화
            else:
                merged[key] = value
        
        merged['last_updated'] = datetime.utcnow().isoformat()
        return merged
```

#### NoSQL 데이터베이스 (DynamoDB 최적화)
- **대화 기록**: 세션별 파티셔닝으로 성능 최적화
- **에이전트 상태**: 실행 컨텍스트 및 중간 결과 저장
- **파일 메타데이터**: S3 객체와 연결된 처리 상태
- **실시간 협업**: WebSocket 세션 상태 관리

### 3.3 통합 API 설계

#### 핵심 API 구조 (SYGenai 패턴 확장)
```
# 채팅 및 에이전트 API (검증된 패턴)
POST   /api/v1/chat                    # 통합 채팅 (기존 + 새로운)
GET    /api/v1/agents                  # 에이전트 목록 (도메인 + 범용)
POST   /api/v1/agents/{type}/execute   # 에이전트 실행

# 파일 및 RAG API
POST   /api/v1/files/upload            # 멀티파트 업로드
GET    /api/v1/files/{id}/process      # 처리 상태 확인
POST   /api/v1/rag/search             # 하이브리드 검색

# 워크스페이스 API (새로운 기능)
GET    /api/v1/workspaces              # 워크스페이스 목록
POST   /api/v1/workspaces              # 새 워크스페이스 생성
GET    /api/v1/workspaces/{id}         # 워크스페이스 조회
PUT    /api/v1/workspaces/{id}         # 워크스페이스 수정

# 아티팩트 관리 API
GET    /api/v1/workspaces/{id}/artifacts     # 아티팩트 목록
POST   /api/v1/workspaces/{id}/artifacts     # 아티팩트 생성
PUT    /api/v1/workspaces/{id}/artifacts/{aid} # 아티팩트 수정

# MCP 통합 API (기존 패턴)
GET    /api/v1/mcp/servers             # MCP 서버 목록
POST   /api/v1/mcp/tools/call          # MCP 도구 호출
```

#### WebSocket 엔드포인트 (검증된 스트리밍)
```
# 채팅 스트리밍 (SYGenai 검증 프로토콜)
WS     /ws/chat/{conversation_id}      # 실시간 채팅 및 에이전트 응답

# 워크스페이스 협업 (새로운 실시간 기능)
WS     /ws/workspace/{id}              # 실시간 협업 및 동시 편집
WS     /ws/workspace/{id}/cursor       # 커서 및 선택 영역 동기화
```

## 4. 프론트엔드 개발 명세

### 4.1 UI/UX 전략
- **반응형 웹 디자인**: 데스크톱 우선, 모바일/태블릿 지원
- **접근성**: WCAG 2.1 AA 준수
- **다크 모드**: 시스템 설정 연동 및 수동 전환 지원

### 4.2 핵심 UI 기능

#### 메인 인터페이스
- 채팅 기반 상호작용 UI
- 메시지 스트리밍 표시
- 타이핑 인디케이터

#### 모델 선택
- Gemini/Claude 모델 선택 드롭다운
- 모델별 특성 표시
- 사용자 선호 모델 저장

#### 파일/이미지 처리
- 드래그 앤 드롭 업로드
- 업로드 진행률 표시
- 파일 미리보기
- 다중 파일 선택

#### 인터랙티브 워크스페이스
- Canvas/Artifacts 스타일 UI
- 분할 화면 레이아웃
- 실시간 편집 및 협업

### 4.3 컴포넌트 구조

```
src/
├── components/
│   ├── chat/
│   │   ├── ChatMessage.tsx
│   │   ├── ChatInput.tsx
│   │   └── ModelSelector.tsx
│   ├── workspace/
│   │   ├── WorkspaceEditor.tsx
│   │   ├── ArtifactRenderer.tsx
│   │   └── VersionHistory.tsx
│   └── common/
│       ├── FileUploader.tsx
│       └── LoadingStates.tsx
├── pages/
│   ├── ChatPage.tsx
│   ├── WorkspacePage.tsx
│   └── SettingsPage.tsx
└── services/
    ├── api.ts
    ├── websocket.ts
    └── auth.ts
```

## 5. 주요 서비스 기능 명세

### 5.1 인터랙티브 워크스페이스

#### 개념
- Gemini Canvas / Claude Artifacts와 유사한 작업 공간
- AI와 함께 구체적인 결과물 생성 및 편집

#### 핵심 기능
1. **결과물 생성**
   - 텍스트 문서
   - 코드 스니펫
   - HTML 페이지
   - 다이어그램
   - 데이터 시각화

2. **편집 기능**
   - 실시간 편집
   - AI 수정 요청
   - 버전 관리
   - 변경 사항 추적

3. **협업 기능**
   - 결과물 공유
   - 권한 관리
   - 댓글 및 피드백

### 5.2 하이브리드 검색

#### 구현 방식
- 키워드 검색 (BM25)
- 시맨틱 검색 (벡터 유사도)
- 결과 병합 및 재순위화

#### 검색 대상
- 대화 기록
- 생성된 결과물
- 업로드된 문서
- 외부 지식 베이스

## 6. 초기 개발 및 운영 환경

### 6.1 인증 시스템

#### 초기 단계 - Mock Authentication
- 실제 SSO 연동 대신 모의 인증 방식 적용
- 백엔드: FastAPI 의존성 주입으로 고정 사용자 정보 반환
- 프론트엔드: Context API로 항상 인증 완료 상태 유지

#### 향후 확장
- 실제 SSO/SAML 연동 준비
- JWT 토큰 관리 구조
- 역할 기반 접근 제어 (RBAC)

### 6.2 모니터링 및 관찰가능성

#### Langsmith
- LangGraph 에이전트 동작 추적
- LLM 호출 모니터링
- 에이전트 상태 변화 디버깅
- 프롬프트 및 응답 로깅

#### APM (Application Performance Monitoring)
- API 서버 성능 모니터링
- 데이터베이스 쿼리 분석
- 에러 추적 및 알림
- 사용자 경험 메트릭

### 6.3 클라우드 네이티브 배포 전략

#### 컨테이너 퍼스트 전략
```yaml
# Docker 멀티스테이지 빌드 최적화
FROM node:18-alpine AS frontend-build
# React 빌드 최적화 레이어

FROM python:3.11-slim AS backend-build  
# FastAPI + AI 라이브러리 최적화

FROM nginx:alpine AS production
# 프로덕션 웹서버 및 리버스 프록시
```

#### 마이크로서비스 전환 준비
- **API Gateway**: FastAPI 기반 마이크로서비스 라우팅
- **서비스 분리**: 채팅, 워크스페이스, 에이전트, 파일처리 서비스
- **데이터베이스 샤드**: 사용자별, 도메인별 데이터 분리
- **로드 밸런싱**: 에이전트별 동적 스케일링

#### 인프라 자동화 (IaC)
```yaml
# Kubernetes 배포 전략
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-portal
spec:
  replicas: 3  # HA 구성
  strategy:
    type: RollingUpdate  # 무중단 배포
  template:
    spec:
      containers:
      - name: frontend
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi" 
            cpu: "500m"
      - name: backend
        resources:
          requests:
            memory: "2Gi"    # AI 라이브러리
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

#### GitOps 기반 CI/CD
- **GitHub Actions**: 다단계 빌드 및 테스트 자동화
- **ArgoCD**: Kubernetes 배포 자동화 및 상태 관리
- **카나리 배포**: A/B 테스트 및 점진적 롤아웃
- **자동 롤백**: 성능 임계치 초과 시 자동 이전 버전 복구

## 7. 보안 및 규정 준수

### 7.1 보안 요구사항
- API 레이트 리미팅
- 입력 검증 및 살균
- SQL 인젝션 방지
- XSS 방지
- CSRF 보호

### 7.2 데이터 보호
- 민감 정보 암호화
- PII 마스킹
- 감사 로그
- 데이터 보존 정책

### 7.3 규정 준수
- GDPR 준수 (해당 시)
- 접근 권한 관리
- 데이터 사용 동의
- 투명성 보고서

## 8. 성능 요구사항

### 8.1 응답 시간
- API 응답: < 200ms (P95)
- 검색 결과: < 500ms
- 파일 업로드: 네트워크 속도 의존
- WebSocket 지연: < 100ms

### 8.2 확장성
- 동시 사용자: 1,000+
- 일일 메시지: 100,000+
- 저장 용량: 자동 확장
- 부하 분산: 수평적 확장

### 8.3 가용성
- 목표 가동률: 99.9%
- 장애 복구: < 5분
- 데이터 백업: 일일
- 재해 복구 계획

## 9. 개발 접근 방식

### 9.1 Vibe Coding 원칙
- 명세서는 방향성 제시, 세부사항은 개발 중 결정
- 최적의 기술적 판단을 통한 구현
- 지속적인 테스트와 피드백
- 점진적 시스템 완성

### 9.2 우선순위
1. **1차**: End-to-End Web Search 워크플로우
2. **2차**: 파일 업로드 및 RAG
3. **3차**: 인터랙티브 워크스페이스
4. **4차**: 고급 에이전트 기능
5. **5차**: 성능 최적화 및 확장

### 9.3 품질 보증
- 단위 테스트 커버리지: 80%+
- 통합 테스트 자동화
- 코드 리뷰 필수
- 지속적 리팩토링

## 10. 기술적 혁신 요소

### 10.1 AI 에이전트 협업 패턴
- **멀티 에이전트 체인**: LangGraph 기반 복잡한 워크플로우
- **컨텍스트 전파**: 에이전트 간 정보 공유 최적화
- **동적 모델 선택**: 작업 유형별 최적 LLM 자동 선택
- **실시간 피드백**: 사용자 상호작용 기반 에이전트 성능 개선

### 10.2 멀티모달 정보 처리
- **통합 파일 처리**: 텍스트, 이미지, 코드, 구조화 데이터 동시 지원
- **지능형 컨텍스트 추출**: 파일 내용 기반 자동 태깅 및 분류
- **크로스 모달 검색**: 텍스트 질의로 이미지 검색, 이미지로 관련 문서 찾기
- **RAG 최적화**: 문서 청킹 전략 및 벡터 임베딩 개선

### 10.3 사용자 경험 혁신
- **인텐트 예측**: 사용자 입력 분석을 통한 의도 선제적 파악
- **컨텍스트 인식**: 이전 대화 및 워크스페이스 상태 기반 개인화
- **협업 인텔리전스**: 팀 워크플로우 패턴 학습 및 제안
- **프로그레시브 디스클로저**: 사용자 숙련도에 따른 적응적 인터페이스

## 11. 경쟁 우위 및 차별화 포인트

### 11.1 SYGenai 기반 안정성
- **검증된 엔터프라이즈 패턴**: 운영 환경에서 검증된 아키텍처
- **높은 신뢰성**: 기존 시스템의 99.9% 가용성 수준 유지
- **보안 강화**: 실제 업무 환경에서 검증된 보안 프레임워크
- **확장성 보장**: 대규모 사용자 환경에서의 성능 검증 완료

### 11.2 혁신적 기술 조합
- **하이브리드 에이전트**: 도메인 전문성 + 범용 AI의 최적 결합
- **Dynamic LLM 라우팅**: 작업별 최적 모델 자동 선택으로 성능/비용 최적화
- **Redis-less 아키텍처**: PostgreSQL 기반 고성능 캐싱으로 인프라 단순화
- **MCP 통합**: 표준 프로토콜 기반 에이전트 확장성

### 11.3 사용자 중심 설계
- **직관적 워크플로우**: 채팅에서 워크스페이스로의 자연스러운 전환
- **개인화 AI**: 자동 프로파일 수집을 통한 맞춤형 서비스
- **협업 중심**: 실시간 동시 편집 및 공유 기능
- **진입 장벽 최소화**: 별도 학습 없이 즉시 사용 가능한 인터페이스

## 12. 로드맵 및 확장 계획

### 12.1 단기 목표 (1-3개월)
- **MVP 완성**: Web Search + 기본 워크스페이스
- **사용자 피드백 수집**: 핵심 사용 패턴 분석
- **성능 최적화**: 응답 시간 및 안정성 개선
- **보안 강화**: 엔터프라이즈 보안 요구사항 충족

### 12.2 중기 목표 (3-6개월)
- **에이전트 생태계 확장**: 새로운 도메인 전문 에이전트 추가
- **고급 협업 기능**: 버전 관리, 승인 워크플로우, 템플릿 시스템
- **AI 성능 고도화**: 파인튜닝 및 커스텀 모델 통합
- **모바일 지원**: 반응형 웹 및 PWA 기능

### 12.3 장기 비전 (6-12개월)
- **AI 플랫폼 생태계**: 서드파티 에이전트 및 플러그인 지원
- **오픈소스 기여**: 핵심 컴포넌트의 커뮤니티 공개
- **글로벌 확장**: 다국어 지원 및 지역별 컴플라이언스
- **차세대 AI 기술**: 멀티모달 AI, 로보틱스 연동 등 실험적 기능

---

## 📈 **최신 개발 성과 (2025-08-20)**

### ✅ 실시간 스트리밍 시스템 완전 구현
- **진짜 LLM 스트리밍**: 기존 Mock 분할 방식을 완전히 제거하고 실제 LLM 응답을 실시간 스트리밍
- **자연스러운 청킹 알고리즘**: 15-40자 크기 청크로 자연스러운 한글 텍스트 분할 구현
- **ProgressiveMarkdown 컴포넌트**: 증분 기반 점진적 마크다운 렌더링으로 타이핑 효과 구현
- **스트리밍 에러 처리 강화**: 백엔드 변수명 오류 수정 및 프론트엔드 중복 처리 제거

### ✅ 메타 검색 시스템 혁신 (이전 세션)
- **2단계 메타 검색 체인**: 사용자 의도 파악 → 최적화된 검색 쿼리 생성
- **대화 맥락 분석 서비스**: 이전 대화 내용을 고려한 지능형 검색 컨텍스트 구성
- **정보 부족 분석 엔진**: 추가 질문이 필요한 영역 자동 식별 및 제안
- **에이전트 추천 시스템**: 사용자 질문 유형에 최적화된 AI 에이전트 자동 제안

### ✅ 인라인 UI 시스템 완전 구현 (이전 세션)
- **팝업 기반 → 인라인 통합**: ChatInput 컴포넌트에 모든 AI 설정 통합
- **8개 모델 통합 선택**: Claude 4개 + Gemini 2.x 4개 모델 드롭다운 선택
- **직관적 기능 토글**: 웹 검색, 심층 리서치, Canvas 모드 즉시 전환
- **반응형 최적화**: 모바일/데스크톱 환경별 최적화된 UI 제공

### ✅ Gemini 모델 생태계 업그레이드 (이전 세션)
- **Gemini 2.x 시리즈 통합**: 2.5 Pro/Flash, 2.0 Pro/Flash 최신 모델 지원
- **성능 특화 라우팅**: 각 모델별 최적 사용 시나리오 정의 및 자동 라우팅
- **타입 시스템 완성**: TypeScript 기반 완전한 모델 타입 안정성 구현

### 🔧 기술 아키텍처 혁신
- **스트리밍 청킹 엔진**: 완전히 새로운 자연어 분할 알고리즘으로 실시간 타이핑 효과
- **컴포넌트 성능 최적화**: React.memo 및 메모이제이션으로 렌더링 성능 개선
- **증분 파싱 시스템**: 새로 추가된 텍스트만 파싱하여 CPU 사용량 최적화
- **에러 핸들링 강화**: 백엔드/프론트엔드 전체 스트리밍 에러 처리 개선

---

**문서 버전**: v2.3  
**최종 업데이트**: 2025-08-20  
**작성자**: AI 포탈 개발팀  
**검토자**: SYGenai 아키텍처 팀