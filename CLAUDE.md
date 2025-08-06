# CLAUDE.md

차세대 AI 포탈 개발을 위한 Claude Code 가이드라인입니다.

## 📋 프로젝트 개요

**차세대 지능형 내부 자동화 플랫폼 (Next-Gen AI Portal)**

SYGenai의 검증된 엔터프라이즈급 아키텍처를 기반으로, 혁신적인 인터랙티브 워크스페이스와 확장 가능한 AI 에이전트 생태계를 구축하는 프로젝트입니다.

### 핵심 특징
- **검증된 안정성**: 운영 중인 SYGenai의 성숙한 아키텍처 패턴 활용
- **혁신적 경험**: Canvas/Artifacts 스타일 인터랙티브 워크스페이스
- **확장 가능성**: 모듈화된 에이전트 시스템으로 무한 확장
- **엔터프라이즈 레디**: 보안, 성능, 확장성이 검증된 프로덕션 아키텍처

### 기술 스택
```
Frontend:  React 18+ • TypeScript • TailwindCSS • Zustand • SWR
Backend:   FastAPI • Pydantic • LangGraph • PostgreSQL
AI Layer:  Claude (Bedrock) • Gemini (GenerativeAI) • OpenSearch
Infra:     Docker • Kubernetes • GitHub Actions • AWS/GCP
```

## 📁 프로젝트 구조

```
AIPortal/
├── .claude/
│   └── settings.local.json       # Claude CLI 권한 설정
├── CLAUDE.md                      # 이 파일 - 개발 메타 가이드
├── develop.md                     # 개발 명세서 (v2.1)
├── dev_plan.md                    # 4단계 10주 실행 계획
├── ARCHITECTURE.md                # 시스템 아키텍처 설계서
├── IMPLEMENTATION_GUIDE.md        # 실전 구현 가이드라인
├── backend/                       # FastAPI 백엔드
│   ├── app/
│   │   ├── agents/               # AI 에이전트 시스템
│   │   ├── api/                  # REST API 엔드포인트
│   │   ├── core/                 # 핵심 설정 및 보안
│   │   ├── db/                   # 데이터베이스 모델
│   │   └── services/             # 비즈니스 로직
│   └── requirements.txt
├── frontend/                      # React 프론트엔드
│   ├── src/
│   │   ├── components/           # React 컴포넌트
│   │   ├── hooks/                # 커스텀 훅
│   │   ├── pages/                # 페이지 컴포넌트
│   │   ├── stores/               # Zustand 상태 관리
│   │   └── services/             # API 클라이언트
│   └── package.json
├── docker-compose.yml             # 개발 환경 구성
└── scripts/                      # 개발 스크립트
    ├── setup.sh
    └── start-dev.sh
```

## 📚 개발 문서 가이드

### 문서 참조 순서
개발 시 다음 순서로 문서를 참조하여 진행합니다:

1. **develop.md** (개발 명세서) - *필수 참조*
   - 전체 시스템 설계 및 기술적 방향성
   - AI 에이전트 아키텍처 및 LLM 라우팅 전략
   - 데이터 아키텍처 및 API 설계 명세
   - 모든 개발은 이 명세를 기준으로 진행

2. **ARCHITECTURE.md** (아키텍처 설계서) - *구현 전 필수*
   - 시스템 아키텍처 다이어그램 및 데이터 플로우
   - PostgreSQL 스키마 및 Redis 대체 캐싱 시스템
   - 보안 아키텍처 및 성능 최적화 전략
   - 배포 및 운영 아키텍처

3. **IMPLEMENTATION_GUIDE.md** (구현 가이드라인) - *코딩 시 참조*
   - Vibe Coding 실천법 및 코드 품질 기준
   - 백엔드/프론트엔드 실제 구현 예제
   - 개발 환경 설정 및 도구 사용법
   - 테스트 및 디버깅 가이드라인

4. **dev_plan.md** (실행 계획) - *진행 관리*
   - 4단계 10주 Sprint 계획
   - 주차별 세부 작업 및 완료 기준
   - 리스크 관리 및 품질 보증 계획

### 문서 업데이트 규칙
- **개발 중 발견사항 즉시 반영**: 명세와 다른 최적 구현 방향 발견 시
- **완료 상태 업데이트**: dev_plan.md의 체크리스트 ([ ] → [x])
- **버전 관리**: 주요 변경사항은 문서 하단에 버전 기록

## 🛠️ 개발 방식: Vibe Coding

### 핵심 원칙
1. **명세는 나침반**: develop.md는 방향성 제시, 세부사항은 개발 중 최적화
2. **단계적 완성**: 매 커밋마다 동작하는 기능 단위로 구현
3. **품질 우선**: 빠른 구현보다 견고하고 테스트 가능한 구현
4. **사용자 중심**: 기술적 완성도보다 사용자 가치 창출 우선

### 구현 우선순위 (4단계)
1. **Phase 1 (3주)**: MVP Foundation - 기본 채팅 + Web Search Agent
2. **Phase 2 (2.5주)**: File Processing & RAG - 멀티모달 RAG 에이전트  
3. **Phase 3 (3주)**: Interactive Workspace - Canvas/Artifacts 협업
4. **Phase 4 (1.5주)**: Advanced Features - Tier1 에이전트 + 프로덕션 준비

### 기술적 가이드라인
- **아키텍처**: 모듈화된 마이크로서비스 지향 설계
- **확장성**: 새로운 AI 에이전트 추가가 용이한 플러그인 구조
- **성능**: Redis 없이도 고성능을 보장하는 2-tier 캐싱
- **보안**: 엔터프라이즈급 인증/권한 관리 시스템
- **품질**: 테스트 커버리지 80% 이상, 자동화된 CI/CD

## 🔧 개발 환경 및 도구

### Claude CLI 설정
`.claude/settings.local.json` 파일 권한 설정:
- 기본 파일 시스템 작업: `ls`, `find`, `mkdir`, `npm install` 등
- Git 작업: `git add`, `git commit`, `git checkout` 등  
- MCP 서버: `mcp__context7__*` (라이브러리 문서 조회)

### 개발 환경 요구사항
- **Platform**: Linux (WSL2)
- **Node.js**: 18+
- **Python**: 3.11+
- **Database**: PostgreSQL 15+, DynamoDB Local
- **Container**: Docker, Docker Compose

### 빠른 시작
```bash
# 1. 개발 환경 설정
./scripts/setup.sh

# 2. 통합 개발 서버 실행  
./scripts/start-dev.sh

# 3. 개별 서비스 실행
cd backend && uvicorn app.main:app --reload
cd frontend && npm run dev
```

## 💬 커뮤니케이션 및 문서화

### 언어 정책
- **한글 우선**: 모든 문서, 주석, 커뮤니케이션은 한글로 작성
- **코드는 영어**: 변수명, 함수명, 클래스명은 영어 사용
- **다국어 지원**: UI 텍스트는 i18n 준비

### Git 커밋 가이드라인
```
기능: [한글로 작성한 커밋 메시지]

feat: [English commit message]

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

**커밋 타입**:
- `기능` (feat): 새로운 기능 추가
- `수정` (fix): 버그 수정
- `개선` (refactor): 코드 리팩토링
- `스타일` (style): 코드 포맷팅, 세미콜론 누락 등
- `문서` (docs): 문서 수정
- `테스트` (test): 테스트 코드 추가/수정

## 🚀 개발 진행 방법

### 새로운 기능 개발 시
1. **문서 검토**: develop.md → ARCHITECTURE.md → IMPLEMENTATION_GUIDE.md 순서로 검토
2. **계획 확인**: dev_plan.md에서 해당 기능의 우선순위 및 요구사항 확인
3. **브랜치 생성**: `feature/[기능명]` 또는 `phase-[번호]/[작업명]` 
4. **구현**: IMPLEMENTATION_GUIDE.md의 패턴을 따라 구현
5. **테스트**: 단위 테스트 작성 및 통합 테스트 실행
6. **문서 업데이트**: 변경사항을 관련 문서에 반영
7. **PR 생성**: 코드 리뷰 및 병합

### 문제 해결 시
1. **ARCHITECTURE.md** 에서 관련 시스템 구조 확인
2. **IMPLEMENTATION_GUIDE.md** 에서 유사한 구현 패턴 참조
3. **develop.md** 에서 설계 의도 확인
4. **Stack Overflow**, **GitHub Issues** 등에서 추가 정보 수집

### 성능 최적화 시
1. **ARCHITECTURE.md** 성능 최적화 섹션 참조
2. 데이터베이스 쿼리 최적화 및 인덱스 전략 적용
3. 캐싱 전략 (L1 메모리 + L2 PostgreSQL) 활용
4. 메트릭 수집 및 모니터링 설정

## 📈 프로젝트 현황

### 완료된 문서
- ✅ **develop.md** v2.1 - 통합 개발 명세서
- ✅ **dev_plan.md** v1.0 - 4단계 10주 실행 계획  
- ✅ **ARCHITECTURE.md** v1.0 - 시스템 아키텍처 설계서
- ✅ **IMPLEMENTATION_GUIDE.md** v1.0 - 실전 구현 가이드라인

### 개발 상태  
- ✅ 프로젝트 초기 구조 설정 (2025-01-06)
- ✅ 기본 백엔드/프론트엔드 스켈레톤 코드
- 🔄 **Phase 1 진행 중**: MVP Foundation 구현

### 다음 단계
1. PostgreSQL 스키마 구현 및 마이그레이션 설정
2. FastAPI 서버 기본 설정 및 미들웨어 구성
3. LLM 라우팅 시스템 및 캐싱 시스템 구현
4. React 채팅 UI 컴포넌트 완성

---

**업데이트**: 2025-01-06  
**버전**: v2.0  
**상태**: Phase 1 진행 중 🚀