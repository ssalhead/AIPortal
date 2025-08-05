# AI 포탈 개발 명세서

## 1. 프로젝트 개요

### 프로젝트명
차세대 지능형 내부 자동화 플랫폼 (AI 포탈)

### 프로젝트 목표
회사 내부 사용자를 위한 통합 AI 솔루션 개발. 단순한 도구를 넘어, 다양한 AI 에이전트 서비스를 제공하고, 사용자가 직접 에이전트를 생성하며, 데이터와 상호작용하는 확장 가능한 생태계를 구축

### 개발 철학 - Vibe Coding
- 엄격한 명세보다 아키텍처 원칙과 핵심 기능의 "Vibe"를 이해하고 최적의 코드를 창의적으로 구현
- 각 단계별로 핵심 기능을 구현하고 피드백을 통해 반복적으로 개선
- 애자일 접근 방식을 통한 점진적 시스템 완성

## 2. 핵심 아키텍처

### 2.1 분리형 아키텍처 (Decoupled Architecture)
- **프론트엔드**: React 기반 단일 페이지 애플리케이션(SPA)
- **백엔드**: Python 기반 API 서버
- **통신**: RESTful API를 통한 통신, 독립적 개발/배포/확장 가능

### 2.2 기술 스택
#### 프론트엔드
- React 18+
- TypeScript
- Vite (빌드 도구)
- React Query (상태 관리)
- Tailwind CSS 또는 Material-UI
- Monaco Editor (코드 편집기)

#### 백엔드
- Python 3.11+
- FastAPI
- LangChain / LangGraph
- SQLAlchemy
- Pydantic

#### AI 에이전트 프레임워크
- LangChain & LangGraph
- Supervisor-Worker 패턴

## 3. 백엔드 개발 명세

### 3.1 AI 에이전트 서비스 (LangGraph 기반)

#### 아키텍처 패턴
- **Supervisor-Worker 패턴**: 중앙 Supervisor 에이전트가 사용자 요청을 분석하고 전문화된 Worker 에이전트에게 분배

#### LLM 모델 라우터
- GCP Gemini 모델군과 AWS Bedrock Claude 모델군 간 동적 선택
- 사용자 요청 유형 또는 명시적 선택에 따른 최적 모델 라우팅

#### 핵심 Worker 에이전트
1. **Deep Research Agent**
   - 특정 주제에 대한 심층 웹 리서치
   - 구조화된 보고서 생성
   
2. **Web Search Agent**
   - 빠른 웹 검색 수행
   - 간단한 정보 조회
   
3. **Multimodal RAG Agent**
   - PDF 등 첨부 파일 내용 이해
   - 이미지 분석 및 답변 생성
   - 하이브리드 검색 (키워드 + 시맨틱)

### 3.2 데이터 영속성

#### 벡터 저장소
- **AWS OpenSearch** 사용
- RAG를 위한 벡터 인덱스 관리
- 하이브리드 검색 구현 (키워드 + 시맨틱 검색)

#### 관계형 데이터베이스
- **AWS PostgreSQL** 사용
- 저장 데이터:
  - 사용자 정보 및 권한
  - 에이전트 설정
  - 커뮤니티 게시물
  - 구조화된 메타데이터

#### NoSQL 데이터베이스
- **AWS DynamoDB** 사용
- 저장 데이터:
  - 대화 기록
  - 에이전트 실시간 상태
  - 비정형 고용량 데이터

### 3.3 API 설계

#### 주요 엔드포인트
```
POST   /api/v1/chat          # 채팅 메시지 전송
GET    /api/v1/agents         # 사용 가능한 에이전트 목록
POST   /api/v1/agents/execute # 특정 에이전트 실행
POST   /api/v1/files/upload   # 파일 업로드
GET    /api/v1/workspace/{id} # 워크스페이스 조회
PUT    /api/v1/workspace/{id} # 워크스페이스 업데이트
```

#### WebSocket 엔드포인트
```
WS     /ws/chat              # 실시간 채팅 스트리밍
WS     /ws/workspace/{id}    # 워크스페이스 실시간 협업
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

### 6.3 배포 환경

#### 컨테이너화
- Docker 이미지 빌드
- docker-compose 개발 환경
- Kubernetes 프로덕션 배포 준비

#### CI/CD
- GitHub Actions 워크플로우
- 자동화된 테스트
- 스테이징 환경 배포
- 블루-그린 배포 전략

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