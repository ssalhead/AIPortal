# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

차세대 지능형 내부 자동화 플랫폼 (AI 포탈) 프로젝트입니다. `/mnt/f/genai/sami_v2` 위치에서 개발 중입니다.

- **프로젝트 타입**: AI 통합 웹 애플리케이션
- **기술 스택**: React (프론트엔드) + FastAPI (백엔드) + LangGraph (AI 에이전트)
- **개발 방식**: Vibe Coding - 명세의 방향성을 바탕으로 창의적이고 최적화된 구현

## Current Structure

```
sami_v2/
├── .claude/
│   └── settings.local.json    # Claude CLI permissions configuration
├── CLAUDE.md                   # This file
├── develop.md                  # 개발 명세서
├── dev_plan.md                 # 개발 실행 계획
├── backend/                    # FastAPI 백엔드 (예정)
└── frontend/                   # React 프론트엔드 (예정)
```

## 개발 진행 가이드라인

### 명세서 참조 및 업데이트
1. **develop.md 참조**:
   - 모든 개발은 `develop.md` 파일의 명세를 기준으로 진행합니다
   - 명세서는 방향성을 제시하며, 세부 구현은 개발 중 최적화합니다
   - 개발 진행 중 명세와 다른 방향으로 진행되는 경우, `develop.md`를 업데이트합니다

2. **dev_plan.md 진행 관리**:
   - `dev_plan.md`의 작업 목록을 순서대로 진행합니다
   - 각 작업 완료 시 진행 상태를 파일에 업데이트합니다 ([ ] → [x])
   - 계획이 변경되거나 수정이 필요한 경우, 해당 내용을 반영하여 업데이트합니다
   - 예상 일정과 실제 진행 일정을 함께 기록합니다

### 개발 우선순위
1. **Phase 1 (1-2주)**: MVP - Web Search Agent 구현
2. **Phase 2 (2-3주)**: 파일 처리 및 RAG 기능
3. **Phase 3 (3-4주)**: 인터랙티브 워크스페이스
4. **Phase 4 (2-3주)**: 고급 기능 및 최적화
5. **Phase 5 (1-2주)**: 프로덕션 준비

## Development Guidelines

AI 포탈 개발 시 다음 원칙을 따릅니다:

1. **아키텍처 원칙**: 프론트엔드와 백엔드의 완전한 분리
2. **확장성**: 새로운 AI 에이전트 추가가 용이한 구조
3. **사용자 경험**: 직관적이고 반응성 있는 UI/UX
4. **코드 품질**: 테스트 커버리지 80% 이상 유지
5. **문서화**: 코드 변경사항은 즉시 관련 문서에 반영

## Claude CLI Configuration

The `.claude/settings.local.json` file currently allows basic file system operations:
- `ls` commands for directory listing
- `find` commands for file searching

Additional permissions may need to be added as the project develops.

## Language and Communication

- **모든 설명과 출력은 한글로 작성**
- 사용자와의 모든 커뮤니케이션은 한글을 사용합니다
- 코드 주석은 프로젝트 규칙에 따르되, 기본적으로 한글 사용

## Git Commit Guidelines

커밋 메시지는 다음 형식을 따릅니다:

```
[한글 커밋 메시지]

[English commit message]

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

예시:
```
기능: 사용자 인증 기능 추가

feat: Add user authentication feature

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

## Notes

- This is not a git repository yet
- No existing code conventions to follow
- No build/test commands configured yet
- Platform: Linux (WSL2)