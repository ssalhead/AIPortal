# AI 포탈 구현 가이드라인
## 개발자를 위한 실전 구현 가이드

---

## 🎯 구현 철학

### Vibe Coding 실천법
- **명세서는 나침반**: 방향성을 제시하되, 최적 구현은 개발 중 결정
- **단계적 완성**: 매 커밋마다 동작하는 기능 단위로 구현
- **품질 우선**: 빠른 구현보다 견고한 구현에 집중
- **사용자 중심**: 기술적 완성도보다 사용자 가치 우선

### 코드 품질 기준
```python
# 좋은 예: 명확하고 테스트 가능한 구현
class WebSearchAgent:
    """웹 검색을 담당하는 에이전트
    
    Args:
        llm_router: LLM 라우팅 시스템
        cache_manager: 캐시 관리자
        
    Example:
        >>> agent = WebSearchAgent(llm_router, cache_manager)
        >>> result = await agent.execute("최신 AI 트렌드")
        >>> assert result.sources is not None
    """
    
    def __init__(self, llm_router: LLMRouter, cache_manager: CacheManager):
        self.llm_router = llm_router
        self.cache_manager = cache_manager
        self.search_client = None  # 지연 초기화
    
    async def execute(self, query: str, context: Dict = None) -> SearchResult:
        """검색 실행 및 결과 반환"""
        
        # 입력 검증
        if not query or len(query.strip()) == 0:
            raise ValueError("검색어는 비어있을 수 없습니다")
        
        # 캐시 확인
        cache_key = f"search:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
        cached_result = await self.cache_manager.get(cache_key)
        if cached_result:
            return SearchResult.from_dict(cached_result)
        
        try:
            # 실제 검색 실행
            result = await self._perform_search(query, context)
            
            # 결과 캐싱
            await self.cache_manager.set(
                cache_key, 
                result.to_dict(), 
                ttl=1800,  # 30분
                tags=['search', f'user:{context.get("user_id")}']
            )
            
            return result
            
        except Exception as e:
            # 구조화된 에러 처리
            logger.error(f"검색 실행 실패: {query}", exc_info=True)
            raise AgentExecutionError(f"검색을 수행할 수 없습니다: {str(e)}")

# 나쁜 예: 불분명하고 테스트하기 어려운 구현
def search(q, u=None):
    if not q: return None
    # 무엇을 하는지 알기 어려움
    r = requests.get(f"https://api.search.com?q={q}&u={u}")
    return r.json() if r.status_code == 200 else None
```

---

## 🔧 개발 환경 설정

### 1. 개발 환경 초기 설정
```bash
# 프로젝트 클론 및 기본 설정
git clone <repository-url>
cd AIPortal

# 백엔드 환경 설정
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 프론트엔드 환경 설정
cd ../frontend
npm install

# 개발 데이터베이스 설정
cd ..
docker-compose -f docker-compose.dev.yml up -d postgres

# 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 실제 값 설정
```

### 2. 로컬 개발 스크립트 실행
```bash
# 통합 개발 서버 실행
./scripts/start-dev.sh

# 또는 개별 실행
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

### 3. 개발 도구 설정
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./backend/venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "typescript.preferences.importModuleSpecifier": "relative",
    "eslint.validate": ["javascript", "typescript", "typescriptreact"]
}

// .vscode/extensions.json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.black-formatter", 
        "bradlc.vscode-tailwindcss",
        "esbenp.prettier-vscode",
        "ms-vscode.vscode-typescript-next"
    ]
}
```

---

## 🏗️ 백엔드 구현 가이드

### FastAPI 프로젝트 구조
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # 앱 진입점
│   ├── core/
│   │   ├── config.py          # 설정 관리
│   │   ├── security.py        # 보안 관련
│   │   └── exceptions.py      # 커스텀 예외
│   ├── api/
│   │   ├── deps.py            # 의존성 주입
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── chat.py        # 채팅 API
│   │       ├── agents.py      # 에이전트 API
│   │       ├── workspaces.py  # 워크스페이스 API
│   │       └── files.py       # 파일 관리 API
│   ├── agents/
│   │   ├── base.py           # 기본 에이전트 클래스
│   │   ├── supervisor.py     # 중앙 조정 에이전트
│   │   ├── llm_router.py     # LLM 라우팅
│   │   └── workers/          # Worker 에이전트들
│   ├── db/
│   │   ├── base.py           # DB 기본 설정
│   │   ├── session.py        # DB 세션 관리
│   │   └── models/           # SQLAlchemy 모델
│   ├── schemas/              # Pydantic 스키마
│   ├── services/            # 비즈니스 로직
│   └── utils/               # 유틸리티 함수
├── tests/                   # 테스트 코드
├── alembic/                # DB 마이그레이션
└── requirements.txt
```

### 핵심 클래스 구현 예제

#### 1. 기본 에이전트 인터페이스
```python
# app/agents/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
import asyncio
import time
from dataclasses import dataclass

@dataclass
class AgentResult:
    """에이전트 실행 결과"""
    content: str
    metadata: Dict[str, Any]
    success: bool
    execution_time: float
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    sources: Optional[list] = None

class BaseAgent(ABC):
    """모든 에이전트의 기본 클래스"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.execution_count = 0
        self.total_execution_time = 0.0
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> AgentResult:
        """에이전트 핵심 로직 실행"""
        pass
    
    async def _execute_with_metrics(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> AgentResult:
        """메트릭과 함께 실행"""
        start_time = time.time()
        self.execution_count += 1
        
        try:
            result = await self.execute(input_data, context)
            result.execution_time = time.time() - start_time
            self.total_execution_time += result.execution_time
            
            # 메트릭 업데이트
            AGENT_EXECUTIONS.labels(
                agent_type=self.name,
                status='success'
            ).inc()
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            
            AGENT_EXECUTIONS.labels(
                agent_type=self.name,
                status='error'
            ).inc()
            
            raise AgentExecutionError(f"{self.name} 실행 실패: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """에이전트 통계 정보"""
        avg_time = self.total_execution_time / max(self.execution_count, 1)
        return {
            'name': self.name,
            'execution_count': self.execution_count,
            'total_execution_time': self.total_execution_time,
            'average_execution_time': avg_time
        }

class AgentExecutionError(Exception):
    """에이전트 실행 중 발생하는 에러"""
    pass
```

#### 2. 실제 Worker 에이전트 구현
```python
# app/agents/workers/web_search.py
from app.agents.base import BaseAgent, AgentResult
from app.core.config import settings
import aiohttp
import asyncio
from typing import Dict, Any, List

class WebSearchAgent(BaseAgent):
    """웹 검색 전문 에이전트"""
    
    def __init__(self, llm_router, cache_manager):
        super().__init__("WebSearchAgent", "실시간 웹 검색 및 정보 수집")
        self.llm_router = llm_router
        self.cache_manager = cache_manager
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """HTTP 세션 지연 초기화"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={'User-Agent': 'AI-Portal/1.0'}
            )
        return self.session
    
    async def execute(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> AgentResult:
        """웹 검색 실행"""
        query = input_data.get('query')
        if not query:
            raise ValueError("검색어가 필요합니다")
        
        # 캐시 확인
        cache_key = f"websearch:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
        cached = await self.cache_manager.get(cache_key)
        if cached:
            return AgentResult(**cached)
        
        try:
            # 1. 웹 검색 실행
            search_results = await self._perform_web_search(query)
            
            # 2. 결과 분석 및 요약
            summary = await self._summarize_results(query, search_results, context)
            
            # 3. 결과 구조화
            result = AgentResult(
                content=summary,
                metadata={
                    'query': query,
                    'search_engine': 'multiple',
                    'results_count': len(search_results)
                },
                success=True,
                execution_time=0,  # 메트릭에서 계산됨
                sources=search_results
            )
            
            # 캐시 저장
            await self.cache_manager.set(
                cache_key,
                result.__dict__,
                ttl=1800,  # 30분
                tags=['websearch', f'user:{context.get("user_id", "anonymous")}']
            )
            
            return result
            
        except Exception as e:
            return AgentResult(
                content=f"검색 중 오류가 발생했습니다: {str(e)}",
                metadata={'error': str(e)},
                success=False,
                execution_time=0
            )
    
    async def _perform_web_search(self, query: str) -> List[Dict[str, Any]]:
        """실제 웹 검색 수행 (여러 검색 엔진 통합)"""
        session = await self._get_session()
        
        # 여러 검색 소스를 병렬로 실행
        tasks = [
            self._search_serper(session, query),
            self._search_tavily(session, query),
            # 추가 검색 소스들...
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 통합 및 중복 제거
        all_results = []
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
        
        return self._deduplicate_results(all_results)
    
    async def _search_serper(self, session: aiohttp.ClientSession, query: str) -> List[Dict]:
        """Serper API를 통한 Google 검색"""
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": settings.SERPER_API_KEY}
        payload = {"q": query, "num": 10}
        
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return [
                        {
                            'title': item['title'],
                            'url': item['link'],
                            'snippet': item['snippet'],
                            'source': 'google'
                        }
                        for item in data.get('organic', [])
                    ]
        except Exception as e:
            print(f"Serper 검색 실패: {e}")
        
        return []
    
    async def _summarize_results(self, query: str, results: List[Dict], context: Dict) -> str:
        """검색 결과를 LLM으로 요약"""
        if not results:
            return "검색 결과를 찾을 수 없습니다."
        
        # 결과를 텍스트로 구성
        results_text = "\n\n".join([
            f"제목: {r['title']}\n출처: {r['url']}\n내용: {r['snippet']}"
            for r in results[:10]  # 상위 10개만 사용
        ])
        
        # 요약 프롬프트
        prompt = f"""
다음 검색 결과를 바탕으로 '{query}'에 대한 포괄적이고 정확한 답변을 작성해주세요.

검색 결과:
{results_text}

요구사항:
1. 정확하고 최신 정보를 바탕으로 답변
2. 출처를 명확히 표시
3. 한국어로 자연스럽게 작성
4. 중요한 정보는 구체적인 수치나 사실 포함

답변:
        """
        
        # 최적 모델 선택 및 요약 생성
        model = await self.llm_router.get_optimal_model(
            task_type="balanced_reasoning",
            context_length=len(prompt)
        )
        
        try:
            response = await model.ainvoke(prompt)
            return response.content
        except Exception as e:
            # 폴백: 간단한 결과 정리
            return self._create_simple_summary(query, results)
    
    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """중복 결과 제거"""
        seen_urls = set()
        unique_results = []
        
        for result in results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        return unique_results[:15]  # 최대 15개 결과
    
    async def cleanup(self):
        """리소스 정리"""
        if self.session and not self.session.closed:
            await self.session.close()
```

#### 3. API 엔드포인트 구현
```python
# app/api/v1/chat.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.agent_service import AgentService
from app.core.security import get_current_user
from app.db.session import get_db
import json
import asyncio

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends()
):
    """채팅 API - 에이전트와의 대화"""
    
    try:
        # 요청 검증
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="메시지가 비어있습니다")
        
        # 사용자 컨텍스트 구성
        context = {
            'user_id': current_user['empno'],
            'user_profile': current_user.get('profile_data', {}),
            'workspace_id': request.workspace_id,
            'preferences': current_user.get('preferences', {})
        }
        
        # 에이전트 실행
        result = await agent_service.execute_agent(
            message=request.message,
            agent_type=request.agent_type,
            context=context,
            model_preference=request.model_preference
        )
        
        # 백그라운드 작업: 대화 기록 저장, 프로파일 업데이트
        background_tasks.add_task(
            _save_conversation,
            db, current_user['empno'], request, result
        )
        
        return ChatResponse(
            message=result.content,
            agent_type=request.agent_type,
            model_used=result.model_used,
            sources=result.sources,
            metadata=result.metadata,
            success=result.success
        )
        
    except Exception as e:
        # 구조화된 에러 응답
        logger.error(f"채팅 처리 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"요청을 처리할 수 없습니다: {str(e)}"
        )

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    agent_service: AgentService = Depends()
):
    """스트리밍 채팅 API"""
    
    async def generate_response():
        try:
            context = {
                'user_id': current_user['empno'],
                'user_profile': current_user.get('profile_data', {}),
                'streaming': True
            }
            
            # 스트리밍 에이전트 실행
            async for chunk in agent_service.execute_agent_stream(
                message=request.message,
                agent_type=request.agent_type,
                context=context
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            error_chunk = {
                'type': 'error',
                'content': f'오류 발생: {str(e)}',
                'finished': True
            }
            yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

async def _save_conversation(db: AsyncSession, user_id: str, request: ChatRequest, result):
    """대화 기록 저장 (백그라운드 작업)"""
    try:
        # 대화 저장 로직
        conversation = await db.execute(
            """
            INSERT INTO conversations (user_empno, workspace_id, context)
            VALUES ($1, $2, $3) ON CONFLICT DO NOTHING
            RETURNING id
            """,
            user_id, request.workspace_id, {}
        )
        
        # 메시지 저장
        await db.execute(
            """
            INSERT INTO messages (conversation_id, role, content, metadata, agent_type, model_used)
            VALUES ($1, 'user', $2, '{}', NULL, NULL),
                   ($1, 'assistant', $3, $4, $5, $6)
            """,
            conversation['id'],
            request.message,
            result.content,
            json.dumps(result.metadata),
            request.agent_type,
            result.model_used
        )
        
        await db.commit()
        
    except Exception as e:
        logger.error(f"대화 저장 실패: {e}")
        await db.rollback()
```

---

## ⚛️ 프론트엔드 구현 가이드

### React 프로젝트 구조
```
frontend/
├── src/
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatMessage.tsx      # 메시지 컴포넌트
│   │   │   ├── ChatInput.tsx        # 입력 컴포넌트
│   │   │   ├── ModelSelector.tsx    # 모델 선택
│   │   │   └── index.ts
│   │   ├── workspace/
│   │   │   ├── WorkspaceEditor.tsx  # 워크스페이스 편집기
│   │   │   ├── ArtifactRenderer.tsx # 아티팩트 렌더러
│   │   │   └── index.ts
│   │   ├── common/
│   │   │   ├── Loading.tsx          # 로딩 컴포넌트
│   │   │   ├── ErrorBoundary.tsx    # 에러 경계
│   │   │   └── index.ts
│   │   └── ui/                      # 재사용 가능한 UI 컴포넌트
│   ├── pages/
│   │   ├── ChatPage.tsx            # 채팅 페이지
│   │   ├── WorkspacePage.tsx       # 워크스페이스 페이지
│   │   └── SettingsPage.tsx        # 설정 페이지
│   ├── hooks/
│   │   ├── useChat.ts              # 채팅 관련 훅
│   │   ├── useWebSocket.ts         # WebSocket 훅
│   │   └── useAgent.ts             # 에이전트 관련 훅
│   ├── services/
│   │   ├── api.ts                  # API 클라이언트
│   │   ├── websocket.ts            # WebSocket 관리
│   │   └── storage.ts              # 로컬 저장소
│   ├── stores/
│   │   ├── chatStore.ts            # 채팅 상태
│   │   ├── workspaceStore.ts       # 워크스페이스 상태
│   │   └── userStore.ts            # 사용자 상태
│   ├── types/
│   │   └── index.ts                # 타입 정의
│   ├── utils/
│   │   └── index.ts                # 유틸리티 함수
│   └── App.tsx
├── public/
└── package.json
```

### 핵심 컴포넌트 구현

#### 1. 채팅 메시지 컴포넌트
```typescript
// src/components/chat/ChatMessage.tsx
import React, { memo } from 'react';
import { Message, MessageSource } from '@/types';
import { cn } from '@/utils';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { ExternalLink, Copy, ChevronDown } from 'lucide-react';
import { useState } from 'react';

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
  onSourceClick?: (source: MessageSource) => void;
}

export const ChatMessage = memo<ChatMessageProps>(({ 
  message, 
  isStreaming = false,
  onSourceClick 
}) => {
  const [showSources, setShowSources] = useState(false);
  const [copied, setCopied] = useState(false);

  const isUser = message.role === 'user';
  const hasError = !message.success && message.role === 'assistant';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('복사 실패:', error);
    }
  };

  const renderContent = () => {
    if (hasError) {
      return (
        <div className="text-red-600 bg-red-50 p-3 rounded-lg border border-red-200">
          <p className="font-medium">오류가 발생했습니다</p>
          <p className="text-sm mt-1">{message.content}</p>
        </div>
      );
    }

    return (
      <div className="prose prose-sm max-w-none">
        <ReactMarkdown
          components={{
            code: ({ node, inline, className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || '');
              return !inline && match ? (
                <SyntaxHighlighter
                  style={oneLight}
                  language={match[1]}
                  PreTag="div"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              ) : (
                <code className={cn("px-1 py-0.5 bg-gray-100 rounded text-sm", className)} {...props}>
                  {children}
                </code>
              );
            },
            a: ({ href, children }) => (
              <a 
                href={href} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline inline-flex items-center gap-1"
              >
                {children}
                <ExternalLink className="w-3 h-3" />
              </a>
            )
          }}
        >
          {message.content}
        </ReactMarkdown>
        {isStreaming && <span className="animate-pulse">▋</span>}
      </div>
    );
  };

  const renderSources = () => {
    if (!message.sources || message.sources.length === 0) return null;

    return (
      <div className="mt-3">
        <button
          onClick={() => setShowSources(!showSources)}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
        >
          <ChevronDown 
            className={cn("w-4 h-4 transition-transform", showSources && "rotate-180")}
          />
          출처 {message.sources.length}개
        </button>

        {showSources && (
          <div className="mt-2 space-y-2">
            {message.sources.map((source, index) => (
              <Card 
                key={index}
                className="p-3 hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => onSourceClick?.(source)}
              >
                <CardContent className="p-0">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-sm truncate">{source.title}</h4>
                      <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                        {source.snippet}
                      </p>
                      <div className="flex items-center gap-2 mt-2">
                        <Badge variant="secondary" className="text-xs">
                          {source.source}
                        </Badge>
                        <a 
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          원본 보기
                        </a>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className={cn(
      "flex gap-3 p-4",
      isUser ? "flex-row-reverse" : "flex-row"
    )}>
      {/* 아바타 */}
      <Avatar className={cn("w-8 h-8", isUser && "bg-blue-500")}>
        <AvatarFallback>
          {isUser ? "You" : "AI"}
        </AvatarFallback>
      </Avatar>

      {/* 메시지 내용 */}
      <div className={cn(
        "flex-1 max-w-3xl",
        isUser ? "text-right" : "text-left"
      )}>
        {/* 메타 정보 */}
        <div className={cn(
          "flex items-center gap-2 mb-2",
          isUser ? "justify-end" : "justify-start"
        )}>
          <span className="text-sm font-medium">
            {isUser ? "You" : "AI Assistant"}
          </span>
          
          {message.agent_type && !isUser && (
            <Badge variant="outline" className="text-xs">
              {message.agent_type}
            </Badge>
          )}
          
          {message.model_used && !isUser && (
            <Badge variant="secondary" className="text-xs">
              {message.model_used}
            </Badge>
          )}

          <button
            onClick={handleCopy}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
            title="복사"
          >
            <Copy className="w-3 h-3" />
          </button>
        </div>

        {/* 메시지 본문 */}
        <div className={cn(
          "rounded-lg px-4 py-3",
          isUser 
            ? "bg-blue-500 text-white ml-auto max-w-md" 
            : "bg-gray-100 text-gray-900"
        )}>
          {renderContent()}
        </div>

        {/* 출처 정보 */}
        {!isUser && renderSources()}

        {/* 복사 완료 알림 */}
        {copied && (
          <div className="text-xs text-green-600 mt-1">
            복사 완료!
          </div>
        )}
      </div>
    </div>
  );
});

ChatMessage.displayName = 'ChatMessage';
```

#### 2. 채팅 입력 컴포넌트
```typescript
// src/components/chat/ChatInput.tsx
import React, { useState, useRef, useCallback } from 'react';
import { Send, Paperclip, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useChat } from '@/hooks/useChat';
import { cn } from '@/utils';

interface ChatInputProps {
  onSendMessage: (message: string, files?: File[]) => void;
  isLoading?: boolean;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading = false,
  disabled = false,
  placeholder = "메시지를 입력하세요...",
  maxLength = 10000
}) => {
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const { stopGeneration } = useChat();

  // 자동 높이 조절
  const adjustTextareaHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!message.trim() && files.length === 0) return;
    if (isLoading || disabled) return;

    onSendMessage(message.trim(), files);
    setMessage('');
    setFiles([]);
    
    // 텍스트영역 높이 리셋
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles(prev => [...prev, ...selectedFiles]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    setFiles(prev => [...prev, ...droppedFiles]);
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const remainingChars = maxLength - message.length;
  const isNearLimit = remainingChars < 100;

  return (
    <div className="border-t bg-white">
      {/* 파일 미리보기 */}
      {files.length > 0 && (
        <div className="px-4 py-2 border-b bg-gray-50">
          <div className="flex flex-wrap gap-2">
            {files.map((file, index) => (
              <div 
                key={index}
                className="flex items-center gap-2 bg-white rounded px-3 py-1 text-sm border"
              >
                <Paperclip className="w-4 h-4" />
                <span className="max-w-32 truncate">{file.name}</span>
                <button
                  onClick={() => removeFile(index)}
                  className="text-red-500 hover:text-red-700"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 입력 영역 */}
      <form onSubmit={handleSubmit} className="p-4">
        <div 
          className={cn(
            "relative border rounded-lg focus-within:ring-2 focus-within:ring-blue-500 transition-colors",
            isDragging && "border-blue-500 bg-blue-50",
            disabled && "opacity-50"
          )}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => {
              setMessage(e.target.value);
              adjustTextareaHeight();
            }}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            maxLength={maxLength}
            className="resize-none border-0 focus:ring-0 pr-24 min-h-[3rem] max-h-40"
            rows={1}
          />

          {/* 우측 버튼들 */}
          <div className="absolute right-2 bottom-2 flex items-center gap-2">
            {/* 파일 업로드 버튼 */}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
              className="p-2"
            >
              <Paperclip className="w-4 h-4" />
            </Button>

            {/* 전송/중단 버튼 */}
            {isLoading ? (
              <Button
                type="button"
                onClick={stopGeneration}
                variant="destructive"
                size="sm"
                className="p-2"
              >
                <Square className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                type="submit"
                disabled={(!message.trim() && files.length === 0) || disabled}
                size="sm"
                className="p-2"
              >
                <Send className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>

        {/* 글자 수 표시 */}
        {isNearLimit && (
          <div className={cn(
            "text-xs mt-1 text-right",
            remainingChars < 0 ? "text-red-500" : "text-gray-500"
          )}>
            {remainingChars} 글자 남음
          </div>
        )}

        {/* 숨겨진 파일 입력 */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,.pdf,.txt,.doc,.docx,.xls,.xlsx"
          onChange={handleFileSelect}
          className="hidden"
        />
      </form>
    </div>
  );
};
```

#### 3. 채팅 관련 커스텀 훅
```typescript
// src/hooks/useChat.ts
import { useState, useCallback, useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/services/api';
import { useChatStore } from '@/stores/chatStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Message, ChatRequest } from '@/types';
import { toast } from 'sonner';

export const useChat = () => {
  const [isGenerating, setIsGenerating] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const queryClient = useQueryClient();
  
  const { 
    messages, 
    addMessage, 
    updateLastMessage, 
    clearMessages,
    currentWorkspaceId 
  } = useChatStore();

  // 메시지 전송 뮤테이션
  const sendMessageMutation = useMutation({
    mutationFn: async ({ message, agentType, files }: {
      message: string;
      agentType?: string;
      files?: File[];
    }) => {
      // 파일이 있는 경우 업로드 먼저
      let uploadedFiles = [];
      if (files && files.length > 0) {
        uploadedFiles = await uploadFiles(files);
      }

      const request: ChatRequest = {
        message,
        agent_type: agentType || 'general',
        workspace_id: currentWorkspaceId,
        files: uploadedFiles.map(f => f.id)
      };

      return apiClient.post('/chat', request);
    },
    onSuccess: (response, variables) => {
      // 사용자 메시지 추가
      addMessage({
        id: generateId(),
        role: 'user',
        content: variables.message,
        timestamp: new Date(),
        success: true
      });

      // AI 응답 추가
      addMessage({
        id: generateId(),
        role: 'assistant',
        content: response.data.message,
        timestamp: new Date(),
        success: response.data.success,
        agent_type: response.data.agent_type,
        model_used: response.data.model_used,
        sources: response.data.sources,
        metadata: response.data.metadata
      });

      // 관련 쿼리 무효화
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
    onError: (error) => {
      toast.error('메시지 전송에 실패했습니다.');
      console.error('Chat error:', error);
      
      // 에러 메시지 추가
      addMessage({
        id: generateId(),
        role: 'assistant',
        content: '죄송합니다. 요청을 처리하는 중에 오류가 발생했습니다.',
        timestamp: new Date(),
        success: false
      });
    }
  });

  // 스트리밍 메시지 전송
  const sendStreamingMessage = useCallback(async (
    message: string, 
    agentType?: string,
    files?: File[]
  ) => {
    if (isGenerating) return;
    
    try {
      setIsGenerating(true);
      abortControllerRef.current = new AbortController();

      // 사용자 메시지 먼저 추가
      const userMessage: Message = {
        id: generateId(),
        role: 'user',
        content: message,
        timestamp: new Date(),
        success: true
      };
      addMessage(userMessage);

      // 파일 업로드 (있는 경우)
      let uploadedFiles = [];
      if (files && files.length > 0) {
        uploadedFiles = await uploadFiles(files);
      }

      // AI 응답 메시지 초기화
      const aiMessageId = generateId();
      const aiMessage: Message = {
        id: aiMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        success: true
      };
      addMessage(aiMessage);

      // 스트리밍 요청
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({
          message,
          agent_type: agentType || 'general',
          workspace_id: currentWorkspaceId,
          files: uploadedFiles.map(f => f.id)
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error('스트리밍 요청 실패');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        let buffer = '';
        let accumulatedContent = '';

        while (true) {
          const { done, value } = await reader.read();
          
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          
          // 완료된 라인들 처리
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // 마지막 불완전한 라인은 버퍼에 남김

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.type === 'content') {
                  accumulatedContent += data.content;
                  updateLastMessage(aiMessageId, {
                    content: accumulatedContent,
                    metadata: data.metadata
                  });
                } else if (data.type === 'complete') {
                  updateLastMessage(aiMessageId, {
                    content: accumulatedContent,
                    sources: data.sources,
                    agent_type: data.agent_type,
                    model_used: data.model_used,
                    success: true
                  });
                } else if (data.type === 'error') {
                  updateLastMessage(aiMessageId, {
                    content: data.content,
                    success: false
                  });
                }
              } catch (e) {
                console.warn('스트림 데이터 파싱 실패:', line);
              }
            }
          }
        }
      }

    } catch (error: any) {
      if (error.name === 'AbortError') {
        updateLastMessage(aiMessage.id, {
          content: accumulatedContent + '\n\n*응답이 중단되었습니다.*',
          success: false
        });
      } else {
        toast.error('스트리밍 중 오류가 발생했습니다.');
        updateLastMessage(aiMessage.id, {
          content: '죄송합니다. 응답 생성 중 오류가 발생했습니다.',
          success: false
        });
      }
    } finally {
      setIsGenerating(false);
      abortControllerRef.current = null;
    }
  }, [isGenerating, addMessage, updateLastMessage, currentWorkspaceId]);

  // 생성 중단
  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsGenerating(false);
  }, []);

  // 파일 업로드
  const uploadFiles = async (files: File[]) => {
    const uploadPromises = files.map(async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await apiClient.post('/files/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      return response.data;
    });

    return Promise.all(uploadPromises);
  };

  return {
    messages,
    isGenerating,
    sendMessage: sendMessageMutation.mutate,
    sendStreamingMessage,
    stopGeneration,
    clearMessages,
    isLoading: sendMessageMutation.isPending
  };
};

// 유틸리티 함수
function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
```

---

## 🚀 **최신 구현 패턴 업데이트 (2025-08-19)**

### ✅ 인라인 UI 구현 패턴
```typescript
// 새로운 인라인 ChatInput 구현 패턴
interface InlineChatInputPattern {
  // 팝업 제거 → 인라인 통합
  architecture: {
    elimination: "PopupAISettings 컴포넌트 완전 제거",
    integration: "ChatInput 내부 통합 드롭다운",
    benefits: ["UX 단순화", "상태 관리 최적화", "접근성 향상"]
  },
  
  // 모델 선택 드롭다운 패턴
  model_dropdown: {
    positioning: "bottom-full mb-2 (상향 열림)",
    trigger: "Provider 아이콘 + 간소화된 모델명",
    providers: {
      claude: "Star 아이콘 (w-4 h-4 text-orange-500)",
      gemini: "Zap 아이콘 (w-4 h-4 text-blue-500)"
    },
    responsive: "isMobile ? 'px-2 py-1' : 'px-3 py-1.5'"
  },
  
  // 기능 토글 버튼 패턴
  feature_toggles: {
    layout: "flex space-x-1 (수평 배치)",
    position: "모델 드롭다운 다음, 파일 첨부 아이콘 앞",
    interaction: "단일 선택 + 재클릭 해제 로직",
    styling: {
      active: "bg-{color}-50 border-{color}-200 text-{color}-700",
      inactive: "bg-white border-slate-200 text-slate-600",
      hover: "hover:border-{color}-200 hover:bg-{color}-50"
    }
  }
}

// 구현 예시
const handleAgentToggle = (agentType: AgentType) => {
  if (selectedAgent === agentType) {
    onAgentChange('none'); // 같은 버튼 클릭시 해제
  } else {
    onAgentChange(agentType); // 다른 버튼 클릭시 변경
  }
};
```

### ✅ 메타 검색 시스템 구현 패턴
```python
# 2단계 메타 검색 구현 패턴
class MetaSearchImplementation:
    """메타 검색 시스템 구현 가이드"""
    
    # 1단계: 대화 맥락 분석 서비스
    conversation_context_service = """
    # backend/app/services/conversation_context_service.py
    
    class ConversationContextService:
        async def analyze_context(self, conversation_id: str, user_query: str):
            # 이전 대화 내용 분석
            previous_messages = await self.get_conversation_history(conversation_id)
            
            # 맥락 추출
            context = await self.extract_conversation_context(previous_messages)
            
            # 사용자 의도 분석
            intent = await self.analyze_user_intent(user_query, context)
            
            return ContextAnalysis(
                previous_context=context,
                user_intent=intent,
                contextual_keywords=self.extract_keywords(context, user_query),
                temporal_context=self.extract_temporal_info(previous_messages)
            )
    """
    
    # 2단계: 정보 부족 분석기
    information_gap_analyzer = """
    # backend/app/agents/workers/information_gap_analyzer.py
    
    class InformationGapAnalyzer:
        async def analyze(self, user_query: str, context: ContextAnalysis):
            gaps = []
            
            # 시간적 정보 부족 확인
            if self.needs_temporal_info(user_query):
                gaps.append(InformationGap(
                    type='temporal',
                    field='time_range',
                    description='구체적인 시간 범위가 필요합니다',
                    urgency='high',
                    question='언제부터 언제까지의 정보를 찾고 계신가요?'
                ))
            
            # 공간적 정보 부족 확인
            if self.needs_spatial_info(user_query):
                gaps.append(InformationGap(
                    type='spatial',
                    field='location',
                    description='지역 정보가 필요합니다',
                    urgency='medium',
                    question='어느 지역의 정보를 원하시나요?'
                ))
            
            return gaps
    """
    
    # 3단계: 에이전트 추천 시스템
    agent_suggestion_modal = """
    # frontend/src/components/ui/AgentSuggestionModal.tsx
    
    interface AgentSuggestion {
      agent_type: AgentType;
      confidence: number;
      reason: string;
      capabilities: string[];
    }
    
    export const AgentSuggestionModal: React.FC<Props> = ({ suggestions, onSelect, onDismiss }) => {
      return (
        <Modal>
          <div className="p-6">
            <h3 className="text-lg font-semibold mb-4">추천 AI 에이전트</h3>
            
            {suggestions.map((suggestion) => (
              <button
                key={suggestion.agent_type}
                onClick={() => onSelect(suggestion.agent_type)}
                className="w-full p-4 border rounded-lg hover:bg-gray-50 text-left mb-3"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">{AGENT_TYPE_MAP[suggestion.agent_type].name}</h4>
                    <p className="text-sm text-gray-600 mt-1">{suggestion.reason}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-sm text-green-600">{Math.round(suggestion.confidence * 100)}% 적합</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </Modal>
      );
    };
    """
```

### ✅ Gemini 2.x 모델 업그레이드 패턴
```typescript
// 업그레이드된 모델 타입 시스템 패턴
interface GeminiUpgradePattern {
  // 모델 타입 정의
  model_types: {
    'gemini-2.5-pro': {
      name: 'Gemini 2.5 Pro',
      description: '최신 고성능 멀티모달 모델',
      capabilities: ['reasoning', 'multimodal', 'analysis', 'creative'],
      speed: 'medium',
      isRecommended: true
    },
    'gemini-2.5-flash': {
      name: 'Gemini 2.5 Flash', 
      description: '최신 고속 멀티모달 모델',
      capabilities: ['reasoning', 'quick_tasks', 'multimodal'],
      speed: 'fast'
    },
    'gemini-2.0-pro': {
      name: 'Gemini 2.0 Pro',
      description: '안정적인 고성능 모델',
      capabilities: ['reasoning', 'analysis', 'multimodal'],
      speed: 'medium'
    },
    'gemini-2.0-flash': {
      name: 'Gemini 2.0 Flash',
      description: '빠르고 효율적인 모델',
      capabilities: ['reasoning', 'quick_tasks', 'multimodal'],
      speed: 'fast'
    }
  },
  
  // UI 표시 패턴
  dropdown_display: {
    provider_icon: '<Zap className="w-3 h-3 text-blue-500" />',
    model_name_format: 'model.name.replace("Gemini ", "")', // "2.5 Pro" 형태로 표시
    speed_indicator: 'model.speed === "fast" && <Zap className="w-3 h-3 text-green-500" />',
    recommended_badge: 'model.isRecommended && <Star className="w-3 h-3 text-amber-500" />'
  }
}
```

### 🔧 개발 모범 사례 업데이트
1. **컴포넌트 통합 원칙**: 관련 기능은 하나의 컴포넌트에서 관리
2. **상태 동기화 패턴**: Provider 변경 시 첫 번째 모델 자동 설정
3. **반응형 UI 패턴**: isMobile 기반 조건부 스타일링
4. **타입 안전성**: 모든 모델 및 에이전트 타입 완전 정의

---

## 📝 스트리밍 시스템 구현 가이드라인 (2025-08-20)

### 실시간 스트리밍 아키텍처

#### 백엔드 청킹 시스템
```python
def split_response_into_natural_chunks(response: str, chunk_size_range: tuple = (15, 40)) -> List[str]:
    """
    자연스러운 한글 텍스트 분할 알고리즘
    - 15-40자 크기 청크로 분할
    - 줄바꿈 > 문장 끝 > 단어 경계 우선 분할
    - 100% 원본 보존 보장 (재결합 검증)
    """
    if not response.strip():
        return []
    
    min_size, max_size = chunk_size_range
    chunks = []
    start = 0
    
    while start < len(response):
        chunk_end = start + max_size
        if chunk_end >= len(response):
            chunk_end = len(response)
        else:
            # 자연스러운 분할점 찾기
            text_segment = response[start:chunk_end + 20]
            
            # 1순위: 줄바꿈
            newline_pos = text_segment.rfind('\n', min_size - start, max_size - start + 1)
            if newline_pos != -1:
                chunk_end = start + newline_pos + 1
            else:
                # 2순위: 문장 끝 (.!?)
                sentence_pos = max(
                    text_segment.rfind('.', min_size - start, max_size - start + 1),
                    text_segment.rfind('!', min_size - start, max_size - start + 1),
                    text_segment.rfind('?', min_size - start, max_size - start + 1)
                )
                if sentence_pos != -1:
                    chunk_end = start + sentence_pos + 1
                else:
                    # 3순위: 공백 (단어 경계)
                    space_pos = text_segment.rfind(' ', min_size - start, max_size - start + 1)
                    if space_pos != -1:
                        chunk_end = start + space_pos
        
        chunk = response[start:chunk_end]
        if chunk:
            chunks.append(chunk)
        start = chunk_end
    
    # 재결합 검증 (100% 정확성 보장)
    recombined = ''.join(chunks)
    if recombined != response:
        return [response]  # 실패 시 전체 텍스트 반환
    
    return chunks
```

#### 프론트엔드 증분 파싱 시스템
```typescript
// ProgressiveMarkdown 컴포넌트 핵심 로직
const appendChunk = useCallback((chunk: string) => {
  // 새로 추가된 텍스트만 추출하여 처리
  const newText = chunk.slice(incrementalState.lastProcessedLength);
  if (newText.length === 0) return;
  
  // 줄바꿈 감지 및 완성된 줄과 진행 중인 줄 분리
  const hasLineBreak = newText.includes('\n');
  
  setIncrementalState(prevState => {
    const newCompletedLines = [...prevState.completedLines];
    let newCurrentLine = prevState.currentLine;
    
    if (hasLineBreak) {
      const combinedText = prevState.currentLine + newText;
      const lines = combinedText.split('\n');
      
      // 마지막 줄을 제외한 모든 줄은 완성된 것으로 처리
      for (let i = 0; i < lines.length - 1; i++) {
        const parsedLine: ParsedLine = {
          id: `line-${lineIdCounter.current++}`,
          element: parseMarkdownLine(lines[i], false),
          raw: lines[i],
          isComplete: true
        };
        newCompletedLines.push(parsedLine);
      }
      
      newCurrentLine = lines[lines.length - 1] || '';
    } else {
      newCurrentLine = prevState.currentLine + newText;
    }
    
    return {
      lastProcessedLength: chunk.length,
      completedLines: newCompletedLines,
      currentLine: newCurrentLine
    };
  });
}, []);
```

#### SSE 스트리밍 프로토콜
```typescript
// API 서비스 스트리밍 이벤트 처리
switch (eventData.type) {
  case 'chunk':
    // 청크 데이터 수신 - 타이핑 효과로 표시
    const chunkData = eventData.data;
    console.log('📝 청크 수신:', chunkData.text, '(인덱스:', chunkData.index, ')');
    onChunk(chunkData.text, chunkData.index === 0, chunkData.is_final);
    break;
    
  case 'result':
    console.log('🎯 스트리밍 완료 - 최종 결과 수신');
    onResult(eventData.data);
    break;
    
  case 'error':
    console.error('❌ 스트리밍 에러:', eventData.data);
    onError(eventData.data.message);
    break;
}
```

### 성능 최적화 패턴

#### React 렌더링 최적화
```typescript
// 개별 줄 렌더러 - React.memo로 불필요한 리렌더링 방지
const MemoizedLineRenderer = React.memo<MemoizedLineRendererProps>(({ line }) => {
  return <React.Fragment>{line.element}</React.Fragment>;
}, (prevProps, nextProps) => {
  // 줄의 내용이 동일하면 리렌더링 하지 않음
  return prevProps.line.id === nextProps.line.id && 
         prevProps.line.raw === nextProps.line.raw &&
         prevProps.line.isComplete === nextProps.line.isComplete;
});
```

#### 인라인 마크다운 파싱 캐시
```typescript
// 메모이제이션을 위한 캐시 시스템
const parseInlineMarkdown = useMemo(() => {
  const cache = new Map<string, React.ReactNode>();
  
  return (text: string): React.ReactNode => {
    const cached = cache.get(text);
    if (cached !== undefined) return cached;
    
    // 마크다운 파싱 로직...
    const result = /* 파싱 결과 */;
    
    // 캐시에 저장 (최대 100개 항목만 유지)
    if (cache.size > 100) {
      const firstKey = cache.keys().next().value;
      cache.delete(firstKey);
    }
    cache.set(text, result);
    
    return result;
  };
}, []);
```

---

**문서 버전**: v2.1  
**최종 업데이트**: 2025-08-20  
**작성자**: AI 포탈 개발팀  
**검토자**: 시니어 개발자

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "Context7\uc744 \ud1b5\ud55c \ucd5c\uc2e0 \uae30\uc220 \uc2a4\ud0dd \ubb38\uc11c \uc218\uc9d1 (React, FastAPI, LangGraph, WebSocket)", "status": "completed"}, {"id": "2", "content": "\uae30\uc874 SYGenai \uc2dc\uc2a4\ud15c \uad6c\uc870 \ubd84\uc11d \ubc0f \uc7ac\uc0ac\uc6a9 \uac00\ub2a5 \ud328\ud134 \uc2dd\ubcc4", "status": "completed"}, {"id": "3", "content": "\ud558\uc774\ube0c\ub9ac\ub4dc \uc544\ud0a4\ud14d\ucc98 \uc124\uacc4 - \uae30\uc874 \uc790\uc0b0 + \ud601\uc2e0 \uc694\uc18c \ud1b5\ud569", "status": "completed"}, {"id": "4", "content": "LLM \ub77c\uc6b0\ud305 \uc804\ub7b5 \uc218\uc815 - Claude/Gemini \ubaa8\ub378 \ud55c\uc815", "status": "completed"}, {"id": "5", "content": "Tier1 \ub3c4\uba54\uc778 \uc5d0\uc774\uc804\ud2b8 MCP \uc124\uc815 \uc2dc\uc2a4\ud15c \uc124\uacc4", "status": "completed"}, {"id": "6", "content": "\uc0c8\ubbf8 GPT \uae30\ub2a5 \ud1a0\uae00 \uc2dc\uc2a4\ud15c \uc124\uacc4", "status": "completed"}, {"id": "7", "content": "Redis \ub300\uccb4 \ubc29\uc548 \uac80\ud1a0 \ubc0f \uc124\uacc4", "status": "completed"}, {"id": "8", "content": "\uc0ac\uc6a9\uc790 \ud504\ub85c\ud30c\uc77c \uc790\ub3d9 \uc218\uc9d1 \uc2dc\uc2a4\ud15c \uc124\uacc4", "status": "completed"}, {"id": "9", "content": "develop.md \ucd5c\uc885 \uc5c5\ub370\uc774\ud2b8 - \ud1b5\ud569 \uac1c\ubc1c \uba85\uc138\uc11c \uc791\uc131", "status": "completed"}, {"id": "10", "content": "dev_plan.md \uc0c1\uc138 \uacc4\ud68d \uc218\ub9bd - 4\ub2e8\uacc4 10\uc8fc \uc2e4\ud589 \uacc4\ud68d", "status": "completed"}, {"id": "11", "content": "\uc544\ud0a4\ud14d\ucc98 \uc124\uacc4\uc11c \ubc0f \uad6c\ud604 \uac00\uc774\ub4dc\ub77c\uc778 \ubb38\uc11c\ud654", "status": "completed"}]