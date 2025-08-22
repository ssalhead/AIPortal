"""
웹 검색 에이전트
"""

import time
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import quote_plus, urlparse
import json
import re
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.llm_router import llm_router
from app.services.search_service import search_service
from app.services.web_crawler import web_crawler
from app.db.session import AsyncSessionLocal
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SearchQuery:
    """검색어 정보"""
    query: str
    priority: int  # 1: 핵심, 2: 보조, 3: 관련
    intent_type: str  # "정보형", "추천형", "비교형", "방법형"
    language: str  # "ko", "en"
    max_results: int = 5
    search_type: str = "general"  # "general", "site_specific", "url_crawl"
    target_url: Optional[str] = None  # 특정 사이트/URL 검색용
    search_operators: List[str] = None  # Google search operators


@dataclass
class EnhancedSearchResult:
    """향상된 검색 결과"""
    search_query: SearchQuery
    results: List[Dict[str, Any]]
    relevance_score: float
    success: bool


class WebSearchAgent(BaseAgent):
    """웹 검색 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_id="web_search",
            name="웹 검색 에이전트",
            description="웹에서 정보를 검색하고 요약합니다"
        )
    
    def _extract_url_info(self, user_query: str) -> Dict[str, Any]:
        """사용자 질문에서 URL 정보 추출 및 분석"""
        url_info = {
            "has_url": False,
            "urls": [],
            "domains": [],
            "search_type": "general",
            "site_hints": []
        }
        
        # URL 패턴 매칭 (http, https, www 포함)
        url_patterns = [
            r'https?://[^\s]+',  # http://... 또는 https://...
            r'www\.[^\s]+',      # www.example.com
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'  # domain.com 형태
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, user_query, re.IGNORECASE)
            for match in matches:
                # 기본 처리
                clean_url = match.strip('.,!?')
                if not clean_url.startswith(('http://', 'https://')):
                    if clean_url.startswith('www.'):
                        clean_url = 'https://' + clean_url
                    else:
                        clean_url = 'https://' + clean_url
                
                try:
                    parsed = urlparse(clean_url)
                    if parsed.netloc:
                        url_info["urls"].append(clean_url)
                        url_info["domains"].append(parsed.netloc)
                        url_info["has_url"] = True
                except:
                    continue
        
        # 사이트 이름 힌트 감지 (한국어 + 영어)
        site_hints = {
            # 주요 한국 사이트
            "네이버": "naver.com",
            "다음": "daum.net", 
            "구글": "google.com",
            "유튜브": "youtube.com",
            "깃허브": "github.com",
            "스택오버플로우": "stackoverflow.com",
            "위키피디아": "wikipedia.org",
            "아마존": "amazon.com",
            "페이스북": "facebook.com",
            "트위터": "twitter.com",
            "링크드인": "linkedin.com",
            "레딧": "reddit.com",
            "인스타그램": "instagram.com",
            
            # 영어 사이트명
            "naver": "naver.com",
            "google": "google.com", 
            "youtube": "youtube.com",
            "github": "github.com",
            "stackoverflow": "stackoverflow.com",
            "wikipedia": "wikipedia.org",
            "reddit": "reddit.com",
            "medium": "medium.com",
            "aws": "aws.amazon.com",
            "microsoft": "microsoft.com",
            "openai": "openai.com",
            "anthropic": "anthropic.com"
        }
        
        for hint, domain in site_hints.items():
            if hint in user_query.lower():
                url_info["site_hints"].append(domain)
                url_info["has_url"] = True
        
        # 검색 타입 결정
        if url_info["urls"] or url_info["site_hints"]:
            # 특정 URL이 있으면 사이트별 검색
            url_info["search_type"] = "site_specific"
            
            # 완전한 URL(경로 포함)이 있으면 크롤링 검색도 고려
            for url in url_info["urls"]:
                parsed = urlparse(url)
                if parsed.path and parsed.path != '/':
                    url_info["search_type"] = "url_crawl"
                    break
        
        # 검색 명령어 감지
        search_commands = [
            "에서 검색", "에서 찾아", "사이트에서", "홈페이지에서", 
            "에서 찾아줘", "에서 검색해줘", "에서 알아봐",
            "site:", "inurl:", "intitle:"
        ]
        
        for command in search_commands:
            if command in user_query.lower():
                if url_info["search_type"] == "general":
                    url_info["search_type"] = "site_specific"
                break
        
        return url_info
    
    async def execute(self, input_data: AgentInput, model: str = "gemini", progress_callback=None) -> AgentOutput:
        """다중 검색어 기반 지능형 웹 검색 실행"""
        start_time = time.time()
        
        # 원본 쿼리 및 대화 맥락 정보 저장
        original_query = input_data.query
        conversation_context = input_data.conversation_context
        
        if not self.validate_input(input_data):
            raise ValueError("유효하지 않은 입력 데이터")
        
        async with AsyncSessionLocal() as session:
            try:
                # 0단계: URL 정보 분석 (5%)
                if progress_callback:
                    progress_callback("사용자 요청 분석 중...", 5, {
                        "step_id": "query_analysis",
                        "step_name": "검색어 분석",
                        "description": "사용자 질문을 분석하고 검색 키워드를 추출합니다"
                    })
                url_info = self._extract_url_info(input_data.query)
                
                # 1단계: 다중 검색어 생성 (15%)
                if progress_callback:
                    search_type_msg = {
                        "general": "일반 검색어 분석 및 생성 중...",
                        "site_specific": "사이트별 검색어 분석 및 생성 중...",
                        "url_crawl": "URL 크롤링 검색어 분석 및 생성 중..."
                    }
                    progress_callback(search_type_msg.get(url_info["search_type"], "검색어 분석 및 생성 중..."), 15, {
                        "step_id": "query_generation",
                        "step_name": "검색 쿼리 생성",
                        "description": "최적화된 검색 쿼리를 생성합니다"
                    })
                search_queries = await self._generate_multiple_search_queries(input_data.query, model, url_info, input_data.conversation_context)
                
                # 2단계: 병렬 웹 검색 실행 (60%)
                if progress_callback:
                    progress_callback(f"다중 검색 실행 중... ({len(search_queries)}개 검색어)", 60, {
                        "step_id": "parallel_search",
                        "step_name": "병렬 웹 검색",
                        "description": "여러 검색 엔진에서 동시에 검색을 수행합니다",
                        "search_queries": [q.query for q in search_queries]
                    })
                all_search_results = await self._execute_parallel_searches(search_queries, session, progress_callback, conversation_context, original_query)
                
                # 3단계: 결과 통합 및 중복 제거 (75%)
                if progress_callback:
                    progress_callback("검색 결과 통합 및 필터링 중...", 75, {
                        "step_id": "result_filtering",
                        "step_name": "결과 필터링",
                        "description": "검색 결과의 품질을 평가하고 필터링합니다"
                    })
                integrated_results = await self._integrate_and_deduplicate_results(all_search_results, input_data.query)
                
                # 4단계: 지능형 랭킹 적용 (85%)
                if progress_callback:
                    progress_callback("검색 결과 품질 평가 및 랭킹 중...", 85, {
                        "step_id": "result_ranking",
                        "step_name": "결과 순위화",
                        "description": "관련성과 신뢰도에 따라 결과를 순위화합니다"
                    })
                ranked_results = await self._apply_intelligent_ranking(integrated_results, input_data.query, model)
                
                # 5단계: LLM 기반 통합 답변 생성 (95%)
                if progress_callback:
                    progress_callback("AI 분석 및 통합 답변 생성 중...", 95, {
                        "step_id": "response_generation",
                        "step_name": "AI 답변 생성",
                        "description": "검색 결과를 바탕으로 종합적인 답변을 생성합니다"
                    })
                enhanced_summary = await self._generate_enhanced_response(
                    original_query=input_data.query,
                    search_queries=search_queries,
                    search_results=ranked_results,
                    model=model
                )
                
                execution_time = int((time.time() - start_time) * 1000)
                
                # 최종 결과를 citations와 sources로 변환
                citations, sources = self._convert_to_citations_and_sources(ranked_results[:8])
                
                metadata = {
                    "search_queries": [q.query for q in search_queries],
                    "search_queries_count": len(search_queries),
                    "total_results_found": sum(len(r.results) for r in all_search_results if r.success),
                    "final_results_count": len(ranked_results),
                    "search_method": "multi_query_intelligent_search",
                    "query_types": list(set(q.intent_type for q in search_queries)),
                    "languages_used": list(set(q.language for q in search_queries)),
                    "search_types": list(set(q.search_type for q in search_queries)),
                    "target_sites": list(set(filter(None, [q.target_url for q in search_queries]))),
                    "used_operators": list(set(filter(None, [op for q in search_queries if q.search_operators for op in q.search_operators]))),
                    "url_analysis": url_info,
                    "top_sources": [r.get('title', '')[:50] for r in ranked_results[:3]],
                    # 맥락 통합 검색어 정보 추가
                    "original_query": original_query,
                    "context_integrated_queries": conversation_context.optimal_search_queries if conversation_context else [],
                    "has_conversation_context": bool(conversation_context and conversation_context.optimal_search_queries)
                }
                
                return AgentOutput(
                    result=enhanced_summary,
                    metadata=metadata,
                    execution_time_ms=execution_time,
                    agent_id=self.agent_id,
                    model_used=model,
                    timestamp=datetime.now().isoformat(),
                    citations=citations,
                    sources=sources
                )
                
            except Exception as e:
                self.logger.error(f"다중 검색어 웹 검색 실행 중 오류: {e}")
                execution_time = int((time.time() - start_time) * 1000)
                
                return AgentOutput(
                    result=f"죄송합니다. 웹 검색 중 오류가 발생했습니다: {str(e)}",
                    metadata={"error": True, "error_message": str(e)},
                    execution_time_ms=execution_time,
                    agent_id=self.agent_id,
                    model_used=model,
                    timestamp=datetime.now().isoformat(),
                    error=str(e)
                )
    
    async def _generate_multiple_search_queries(self, user_query: str, model: str, url_info: Dict[str, Any], conversation_context=None) -> List[SearchQuery]:
        """사용자 질문을 분석하여 다중 검색어 생성 (URL 정보 포함)"""
        try:
            # URL 정보를 활용한 프롬프트 생성
            url_context = ""
            search_type = url_info.get("search_type", "general")
            
            if search_type == "site_specific":
                # 특정 사이트 검색
                target_sites = url_info.get("domains", []) + url_info.get("site_hints", [])
                if target_sites:
                    url_context = f"""
**특별 지시사항**: 사용자가 특정 사이트 검색을 요청했습니다.
- 대상 사이트: {', '.join(target_sites)}
- 검색어에 "site:{target_sites[0]}" 형태의 Google 검색 연산자를 포함해주세요.
- 해당 사이트에 특화된 검색어로 생성해주세요.
"""
            elif search_type == "url_crawl":
                # 특정 URL 크롤링
                target_urls = url_info.get("urls", [])
                if target_urls:
                    url_context = f"""
**특별 지시사항**: 사용자가 특정 URL에서 정보를 찾고자 합니다.
- 대상 URL: {', '.join(target_urls)}
- 해당 URL의 내용을 크롤링하여 관련 정보를 찾을 예정입니다.
- URL 크롤링과 병행할 보조 검색어도 생성해주세요.
"""
            
            # 위치 기반 검색 컨텍스트 감지
            location_context = ""
            weather_keywords = ["날씨", "기온", "강수", "습도", "미세먼지", "weather", "temperature", "rain"]
            location_keywords = ["오늘", "현재", "지금", "여기", "내 위치", "근처"]
            
            has_weather_query = any(keyword in user_query.lower() for keyword in weather_keywords)
            has_location_query = any(keyword in user_query.lower() for keyword in location_keywords)
            
            if has_weather_query and has_location_query:
                from datetime import datetime
                today_date = datetime.now().strftime("%Y년 %m월 %d일")
                location_context = f"""
**위치 기반 검색 특별 지시사항**:
- 사용자가 현재 위치나 "오늘" 관련 날씨 정보를 요청했습니다.
- 오늘 날짜: {today_date}
- 한국 주요 도시(서울, 부산, 대구, 인천, 광주, 대전, 울산) 기준 검색어를 포함해주세요.
- "site:weather.go.kr" 또는 "site:kma.go.kr" 기상청 사이트 검색을 우선 포함해주세요.
- 구체적인 날짜와 지역명을 포함한 검색어를 생성해주세요.
- 예: "{today_date} 서울 날씨", "site:weather.go.kr 오늘 날씨"
"""
            
            # 범용 대화 맥락 기반 검색 컨텍스트 생성
            conversation_context_prompt = ""
            logger.debug("대화 맥락 수신 여부", {"has_context": conversation_context is not None})
            if conversation_context:
                logger.info(f"🎯 대화 맥락 정보 - 도메인: {conversation_context.domain}, 최적 검색어: {conversation_context.optimal_search_queries}")
                
                # LLM이 이미 생성한 최적 검색어가 있는지 확인
                if conversation_context.optimal_search_queries:
                    # LLM이 생성한 최적 검색어 우선 사용
                    logger.info(f"🎯 LLM 최적 검색어 사용: {conversation_context.optimal_search_queries}")
                    conversation_context_prompt = f"""
**🎯 LLM 분석 기반 최적 검색어 활용**:
LLM이 전체 대화 맥락을 분석하여 생성한 최적 검색어들:
{chr(10).join([f'- {query}' for query in conversation_context.optimal_search_queries])}

**대화 맥락 정보**:
- 도메인: {conversation_context.domain}
- 주제 진화: {' → '.join(conversation_context.topic_evolution)}
- 사용자 의도: {conversation_context.user_intent}
- 맥락 연결: {conversation_context.context_connection}
- 검색 포커스: {conversation_context.search_focus}

**최적화된 검색 전략**:
1. LLM이 제안한 최적 검색어들을 기반으로 검색어 생성
2. 전체 대화 맥락을 반영한 구체적이고 의미있는 검색어 구성
3. 사용자의 진짜 검색 의도에 부합하는 다각도 검색어 생성
"""
                else:
                    # LLM 검색어가 없으면 기존 맥락 정보 활용
                    conversation_context_prompt = f"""
**범용 대화 맥락 기반 검색 지시사항**:
- 도메인 분류: {conversation_context.domain}
- 대화 주제: {', '.join(conversation_context.conversation_topics)}
- 주제 진화: {' → '.join(conversation_context.topic_evolution) if conversation_context.topic_evolution else '단일 주제'}
- 핵심 엔티티: {', '.join(conversation_context.mentioned_entities)}
- 사용자 의도: {conversation_context.user_intent}
- 맥락 연결: {conversation_context.context_connection}
- 검색 포커스: {conversation_context.search_focus}
- 이전 검색어: {', '.join(conversation_context.previous_search_queries[-3:])}

**범용 맥락 활용 규칙**:
1. 도메인에 맞는 전문 용어와 키워드 활용 ({conversation_context.domain} 분야)
2. 주제 진화 과정을 반영한 통합적 검색어 생성
3. 사용자 의도({conversation_context.user_intent})에 맞는 검색 방향성 설정
4. 맥락 연결성을 고려한 구체적이고 명확한 검색어 구성
5. 중복 방지 및 새로운 관점의 정보 탐색
"""

            prompt = f"""
사용자 질문을 분석하여 웹 검색에 최적화된 다중 검색어를 생성해주세요.

사용자 질문: "{user_query}"
검색 타입: {search_type}
{url_context}
{location_context}
{conversation_context_prompt}

다음 규칙에 따라 3-5개의 검색어를 생성하세요:

1. **핵심 검색어** (우선순위 1): 정확한 매칭을 위한 가장 중요한 검색어
2. **지역 특화 검색어** (우선순위 1): 위치/날씨 관련 질문인 경우 지역명 포함
3. **보조 검색어** (우선순위 2): 관련 정보를 찾기 위한 확장 검색어
4. **영어 검색어** (우선순위 2): 영어로 번역한 검색어 (필요시)
5. **구체적 검색어** (우선순위 1): 더 구체적이고 세부적인 검색어
6. **관련 검색어** (우선순위 3): 연관된 주제의 검색어

각 검색어에 대해 다음 정보를 포함한 JSON 형태로 응답해주세요:
{{
  "search_queries": [
    {{
      "query": "검색어",
      "priority": 1,  // 1: 핵심, 2: 보조, 3: 관련
      "intent_type": "정보형",  // "정보형", "추천형", "비교형", "방법형"
      "language": "ko",  // "ko" 또는 "en"
      "max_results": 5,
      "search_type": "{search_type}",  // "general", "site_specific", "url_crawl"
      "target_url": null  // 특정 URL이 있는 경우
    }}
  ]
}}

JSON 형태로만 응답해주세요.
"""
            
            response, _ = await llm_router.generate_response(model, prompt)
            
            # JSON 파싱 시도 (```json 제거)
            try:
                import json
                # ```json으로 감싸진 경우 제거
                clean_response = response.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:]  # ```json 제거
                if clean_response.endswith('```'):
                    clean_response = clean_response[:-3]  # ``` 제거
                clean_response = clean_response.strip()
                
                data = json.loads(clean_response)
                search_queries = []
                
                for query_data in data.get("search_queries", []):
                    # URL 정보 처리
                    target_url = None
                    search_operators = []
                    query_search_type = query_data.get("search_type", search_type)
                    
                    # site: 연산자가 있는 검색어 처리
                    query_text = query_data["query"]
                    if "site:" in query_text:
                        search_operators.append("site")
                        query_search_type = "site_specific"
                    
                    # 특정 URL이 지정된 경우
                    if url_info.get("urls"):
                        target_url = url_info["urls"][0]
                    elif url_info.get("site_hints"):
                        target_url = f"https://{url_info['site_hints'][0]}"
                    
                    search_query = SearchQuery(
                        query=query_text,
                        priority=query_data.get("priority", 2),
                        intent_type=query_data.get("intent_type", "정보형"),
                        language=query_data.get("language", "ko"),
                        max_results=query_data.get("max_results", 5),
                        search_type=query_search_type,
                        target_url=target_url,
                        search_operators=search_operators if search_operators else None
                    )
                    search_queries.append(search_query)
                
                # 우선순위별로 정렬
                search_queries.sort(key=lambda x: x.priority)
                
                self.logger.info(f"다중 검색어 생성 완료: {len(search_queries)}개")
                for sq in search_queries:
                    self.logger.info(f"  - {sq.query} (우선순위: {sq.priority}, 타입: {sq.intent_type})")
                
                return search_queries[:5]  # 최대 5개로 제한
                
            except json.JSONDecodeError as je:
                self.logger.warning(f"JSON 파싱 실패: {je}, 원본 응답: {response[:100]}")
                raise
                
        except Exception as e:
            self.logger.warning(f"다중 검색어 생성 실패, 기본 검색어 생성: {e}")
            # fallback: 기본 검색어 생성 (URL 정보 포함)
            fallback_queries = []
            
            search_type = url_info.get("search_type", "general")
            target_url = None
            
            if url_info.get("urls"):
                target_url = url_info["urls"][0]
            elif url_info.get("site_hints"):
                target_url = f"https://{url_info['site_hints'][0]}"
            
            # 기본 검색어
            base_query = user_query.strip()
            if search_type == "site_specific" and url_info.get("site_hints"):
                base_query = f"site:{url_info['site_hints'][0]} {base_query}"
            
            fallback_queries.append(SearchQuery(
                query=base_query,
                priority=1,
                intent_type="정보형",
                language="ko",
                max_results=5,
                search_type=search_type,
                target_url=target_url
            ))
            
            # 보조 검색어 (최신 정보)
            aux_query = f"{user_query.strip()} 2024"
            if search_type == "site_specific" and url_info.get("site_hints"):
                aux_query = f"site:{url_info['site_hints'][0]} {aux_query}"
                
            fallback_queries.append(SearchQuery(
                query=aux_query,
                priority=2,
                intent_type="정보형",
                language="ko",
                max_results=3,
                search_type=search_type,
                target_url=target_url
            ))
            
            return fallback_queries
    
    async def _execute_parallel_searches(
        self, 
        search_queries: List[SearchQuery], 
        session: AsyncSession,
        progress_callback=None,
        conversation_context=None,
        original_query: str = None
    ) -> List[EnhancedSearchResult]:
        """병렬로 다중 검색어 실행"""
        search_tasks = []
        
        # 각 검색어에 대해 비동기 태스크 생성
        for i, query in enumerate(search_queries):
            task = self._execute_single_search(query, session, i, len(search_queries), progress_callback, conversation_context, original_query)
            search_tasks.append(task)
        
        # 모든 검색을 병렬로 실행
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 성공한 결과만 필터링
        enhanced_results = []
        for result in results:
            if isinstance(result, EnhancedSearchResult):
                enhanced_results.append(result)
            elif isinstance(result, Exception):
                self.logger.warning(f"검색 태스크 실패: {result}")
        
        self.logger.info(f"병렬 검색 완료: {len(enhanced_results)}/{len(search_queries)} 성공")
        return enhanced_results
    
    async def _execute_single_search(
        self,
        search_query: SearchQuery,
        session: AsyncSession,
        task_index: int,
        total_tasks: int,
        progress_callback=None,
        conversation_context=None,
        original_query: str = None
    ) -> EnhancedSearchResult:
        """단일 검색어 실행 (일반 검색 + URL 크롤링 지원)"""
        # 각 검색 태스크마다 독립적인 세션 사용 (동시성 문제 해결)
        async with AsyncSessionLocal() as independent_session:
            try:
                # 진행 상태 업데이트
                if progress_callback:
                    base_progress = 40 + (task_index / total_tasks) * 20  # 40-60% 범위
                    if search_query.search_type == "url_crawl":
                        progress_callback(f"'{search_query.target_url}' 크롤링 중...", base_progress)
                    else:
                        # 맥락 통합 검색어 표시
                        display_query = search_query.query
                        has_context = False
                        matching_optimal = None
                        
                        if conversation_context and conversation_context.optimal_search_queries:
                            # 맥락 통합 검색어가 있으면 그것을 표시
                            matching_optimal = next((q for q in conversation_context.optimal_search_queries if q in search_query.query), None)
                            if matching_optimal:
                                display_query = matching_optimal
                                has_context = True
                        
                        # 메타데이터 준비
                        metadata = {
                            'step_id': 'parallel_search',
                            'step_name': '병렬 웹 검색',
                            'description': f"'{display_query}' 검색을 수행중입니다",
                            'has_context': has_context,
                            'original_query': original_query if has_context else None,
                            'context_integrated_query': matching_optimal if has_context else None,
                            'current_search_query': display_query
                        }
                        
                        progress_callback(f"'{display_query}' 검색 중...", base_progress, metadata)
                
                results_dict = []
                
                # URL 크롤링 실행 (url_crawl 타입인 경우)
                if search_query.search_type == "url_crawl" and search_query.target_url:
                    crawl_result = await web_crawler.crawl_url(search_query.target_url)
                    
                    if not crawl_result.error:
                        # 크롤링된 콘텐츠에서 검색
                        search_result = await web_crawler.search_in_content(crawl_result, search_query.query)
                        
                        if search_result["found"]:
                            # 크롤링 결과를 검색 결과 형태로 변환
                            snippet = ""
                            if search_result["matches"]:
                                snippet = search_result["matches"][0]["context"]
                            elif crawl_result.summary:
                                snippet = crawl_result.summary
                            else:
                                snippet = crawl_result.content[:300] + "..."
                            
                            result_dict = {
                                "title": crawl_result.title or "크롤링된 페이지",
                                "url": crawl_result.url,
                                "snippet": snippet,
                                "source": f"crawled_{urlparse(crawl_result.url).netloc}",
                                "score": 0.95,  # 직접 크롤링된 결과는 높은 점수
                                "timestamp": crawl_result.timestamp,
                                "crawl_data": {
                                    "headings": crawl_result.headings,
                                    "matches_count": search_result["matches_count"],
                                    "title_match": search_result["title_match"],
                                    "heading_matches": search_result["heading_matches"]
                                }
                            }
                            results_dict.append(result_dict)
                        else:
                            # 검색어가 없어도 페이지 정보는 제공
                            result_dict = {
                                "title": crawl_result.title or "크롤링된 페이지",
                                "url": crawl_result.url,
                                "snippet": crawl_result.summary or crawl_result.content[:300] + "...",
                                "source": f"crawled_{urlparse(crawl_result.url).netloc}",
                                "score": 0.7,  # 관련성은 낮지만 유용한 정보
                                "timestamp": crawl_result.timestamp,
                                "crawl_data": {
                                    "headings": crawl_result.headings,
                                    "no_matches": True
                                }
                            }
                            results_dict.append(result_dict)
                    else:
                        # 크롤링 실패 시 오류 정보 포함
                        self.logger.warning(f"URL 크롤링 실패: {crawl_result.error}")
                
                # 일반 웹 검색도 함께 실행 (보완적 정보 제공)
                # SearchQuery의 search_type을 SearchService의 SearchType으로 매핑
                from app.services.search_service import SearchType
                
                service_search_type = SearchType.WEB  # 기본값
                if search_query.search_type == "general":
                    service_search_type = SearchType.WEB
                elif search_query.search_type == "site_specific":
                    service_search_type = SearchType.WEB  # 사이트별 검색도 일반 웹 검색으로 처리
                elif search_query.search_type == "url_crawl":
                    service_search_type = SearchType.WEB
                
                # 검색어에서 도메인이나 의도를 분석하여 더 정확한 SearchType 설정
                query_lower = search_query.query.lower()
                if any(word in query_lower for word in ["뉴스", "news", "최신 소식", "최근 소식"]):
                    service_search_type = SearchType.NEWS
                elif any(word in query_lower for word in ["논문", "연구", "학술", "academic", "scholar"]):
                    service_search_type = SearchType.ACADEMIC
                elif any(word in query_lower for word in ["github", "stackoverflow", "개발", "프로그래밍", "코딩"]):
                    service_search_type = SearchType.TECHNICAL
                elif any(word in query_lower for word in ["정부", "공식", "gov.kr", "go.kr", "government"]):
                    service_search_type = SearchType.GOVERNMENT
                elif any(word in query_lower for word in ["쇼핑", "구매", "가격", "shopping", "buy"]):
                    service_search_type = SearchType.SHOPPING
                
                search_results = await search_service.search_web(
                    query=search_query.query,
                    max_results=search_query.max_results,
                    use_cache=True,
                    session=independent_session,
                    search_type=service_search_type
                )
                
                # 일반 검색 결과 추가
                for result in search_results:
                    result_dict = {
                        "title": result.title,
                        "url": result.url,
                        "snippet": result.snippet,
                        "source": result.source,
                        "score": result.score,
                        "timestamp": getattr(result, 'timestamp', None)
                    }
                    results_dict.append(result_dict)
                
                # 관련성 점수 계산
                relevance_score = self._calculate_relevance_score(search_query, results_dict)
                
                return EnhancedSearchResult(
                    search_query=search_query,
                    results=results_dict,
                    relevance_score=relevance_score,
                    success=len(results_dict) > 0
                )
                
            except Exception as e:
                self.logger.error(f"단일 검색 실패 [{search_query.query}]: {e}")
                return EnhancedSearchResult(
                    search_query=search_query,
                    results=[],
                    relevance_score=0.0,
                    success=False
                )
    
    def _calculate_relevance_score(self, search_query: SearchQuery, results: List[Dict]) -> float:
        """검색 결과의 관련성 점수 계산"""
        if not results:
            return 0.0
        
        # 기본 점수
        base_score = 0.5
        
        # 우선순위에 따른 가중치
        priority_weight = {1: 1.0, 2: 0.8, 3: 0.6}.get(search_query.priority, 0.5)
        
        # 결과 개수에 따른 보너스
        result_count_bonus = min(len(results) / 5.0, 1.0) * 0.3
        
        # 평균 점수 계산
        avg_score = sum(r.get("score", 0.5) for r in results) / len(results)
        
        final_score = (base_score + result_count_bonus + avg_score) * priority_weight
        return min(final_score, 1.0)
    
    async def _integrate_and_deduplicate_results(
        self,
        all_results: List[EnhancedSearchResult],
        original_query: str
    ) -> List[Dict[str, Any]]:
        """검색 결과 통합 및 중복 제거"""
        all_unique_results = {}
        
        for enhanced_result in all_results:
            if not enhanced_result.success:
                continue
                
            for result in enhanced_result.results:
                url = result.get("url", "")
                title = result.get("title", "")
                
                # URL 기준 중복 제거
                if url and url not in all_unique_results:
                    # 검색어 정보 추가
                    result_with_context = result.copy()
                    result_with_context["search_query"] = enhanced_result.search_query.query
                    result_with_context["query_priority"] = enhanced_result.search_query.priority
                    result_with_context["query_type"] = enhanced_result.search_query.intent_type
                    result_with_context["relevance_score"] = enhanced_result.relevance_score
                    
                    all_unique_results[url] = result_with_context
                elif url in all_unique_results:
                    # 이미 있는 결과의 점수 향상 (다중 검색어에서 발견된 경우)
                    existing = all_unique_results[url]
                    existing["score"] = max(existing["score"], result.get("score", 0.5))
                    existing["relevance_score"] = max(existing["relevance_score"], enhanced_result.relevance_score)
        
        # 도메인별 결과 수 제한 (다양성 보장)
        domain_counts = {}
        filtered_results = []
        
        for result in all_unique_results.values():
            url = result.get("url", "")
            if url:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                
                if domain_counts.get(domain, 0) < 3:  # 도메인당 최대 3개
                    filtered_results.append(result)
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        self.logger.info(f"결과 통합 완료: {len(all_unique_results)} → {len(filtered_results)} (중복 제거 및 다양성 필터 적용)")
        return filtered_results
    
    async def _apply_intelligent_ranking(
        self,
        results: List[Dict[str, Any]],
        original_query: str,
        model: str
    ) -> List[Dict[str, Any]]:
        """지능형 랭킹 적용"""
        if not results:
            return results
        
        # 다차원 스코어링
        for result in results:
            score_components = {
                "relevance": result.get("relevance_score", 0.5),
                "authority": self._calculate_authority_score(result.get("url", "")),
                "freshness": self._calculate_freshness_score(result.get("timestamp")),
                "priority": self._get_priority_weight(result.get("query_priority", 2)),
                "diversity": 0.1  # 기본 다양성 점수
            }
            
            # 가중 평균 계산
            weights = {
                "relevance": 0.4,
                "authority": 0.25, 
                "freshness": 0.15,
                "priority": 0.15,
                "diversity": 0.05
            }
            
            final_score = sum(score_components[key] * weights[key] for key in weights)
            result["final_ranking_score"] = final_score
        
        # 최종 점수로 정렬
        ranked_results = sorted(results, key=lambda x: x.get("final_ranking_score", 0), reverse=True)
        
        top_scores = [round(r.get('final_ranking_score', 0), 3) for r in ranked_results[:3]]
        self.logger.info(f"지능형 랭킹 적용 완료: 상위 3개 점수 {top_scores}")
        return ranked_results
    
    def _calculate_authority_score(self, url: str) -> float:
        """도메인 권위도 점수 계산"""
        if not url:
            return 0.5
        
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        
        # 신뢰할 수 있는 도메인들
        high_authority_domains = {
            "wikipedia.org": 0.95,
            "github.com": 0.9,
            "stackoverflow.com": 0.9,
            "medium.com": 0.8,
            "google.com": 0.85,
            "microsoft.com": 0.85,
            "openai.com": 0.85,
            "arxiv.org": 0.95,
            "nature.com": 0.95,
            "sciencedirect.com": 0.9
        }
        
        for trusted_domain, score in high_authority_domains.items():
            if trusted_domain in domain:
                return score
        
        # 한국 주요 도메인들
        korean_domains = {
            "naver.com": 0.8,
            "daum.net": 0.75,
            "tistory.com": 0.7,
            "blog.naver.com": 0.65,
            "brunch.co.kr": 0.7
        }
        
        for korean_domain, score in korean_domains.items():
            if korean_domain in domain:
                return score
        
        # 기타 도메인
        return 0.6
    
    def _calculate_freshness_score(self, timestamp) -> float:
        """최신성 점수 계산"""
        if not timestamp:
            return 0.5
        
        try:
            from datetime import datetime, timedelta
            if isinstance(timestamp, str):
                # ISO 형식 파싱 시도
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            now = datetime.now()
            age_days = (now - timestamp).days
            
            if age_days <= 30:
                return 0.9
            elif age_days <= 90:
                return 0.8
            elif age_days <= 365:
                return 0.6
            else:
                return 0.4
                
        except:
            return 0.5
    
    def _get_priority_weight(self, priority: int) -> float:
        """우선순위 가중치 반환"""
        return {1: 1.0, 2: 0.8, 3: 0.6}.get(priority, 0.5)
    
    def _convert_to_citations_and_sources(self, results: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict]]:
        """결과를 citations와 sources 형태로 변환"""
        citations = []
        sources = []
        
        for i, result in enumerate(results):
            citation = {
                "id": f"search_{i+1}",
                "title": result.get("title", "제목 없음"),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", "")[:200] + ("..." if len(result.get("snippet", "")) > 200 else ""),
                "source": result.get("source", "unknown"),
                "score": result.get("final_ranking_score", result.get("score", 0.5))
            }
            citations.append(citation)
            
            source = {
                "title": result.get("title", "제목 없음"),
                "url": result.get("url", ""),
                "type": "web_search",
                "provider": result.get("source", "unknown").split('_')[0] if '_' in result.get("source", "") else result.get("source", "unknown"),
                "search_query": result.get("search_query", ""),
                "ranking_score": result.get("final_ranking_score", 0.5)
            }
            sources.append(source)
        
        return citations, sources
    
    async def _generate_enhanced_response(
        self,
        original_query: str,
        search_queries: List[SearchQuery],
        search_results: List[Dict[str, Any]],
        model: str
    ) -> str:
        """다중 검색 결과를 바탕으로 통합된 답변 생성"""
        if not search_results:
            return "죄송합니다. 관련된 검색 결과를 찾을 수 없습니다."
        
        try:
            # 검색 결과를 텍스트로 구성
            results_text = ""
            for i, result in enumerate(search_results[:8], 1):
                results_text += f"""
{i}. {result.get('title', '제목 없음')}
   URL: {result.get('url', '')}
   내용: {result.get('snippet', '설명 없음')[:300]}
   검색어: "{result.get('search_query', '')}"
   품질점수: {result.get('final_ranking_score', 0):.2f}
"""
            
            # 사용된 검색어들
            search_queries_text = ", ".join([f'"{q.query}"' for q in search_queries])
            
            prompt = f"""
사용자 질문: "{original_query}"

다중 검색어를 사용한 포괄적인 웹 검색을 수행했습니다.
사용된 검색어: {search_queries_text}

다음은 품질 점수 기준으로 랭킹된 검색 결과입니다:
{results_text}

위 검색 결과를 바탕으로 사용자 질문에 대한 종합적이고 유용한 답변을 작성해주세요.

답변 작성 규칙:
1. 사용자 질문에 직접적이고 구체적으로 답변
2. 다양한 검색 결과의 핵심 정보를 종합하여 균형잡힌 시각 제공
3. 실용적이고 도움이 되는 정보 우선
4. 신뢰할 수 있는 출처의 정보 강조
5. 필요시 주의사항이나 추가 고려사항 포함
6. 한국어로 자연스럽고 읽기 쉽게 작성
7. 검색 결과의 다양성을 활용하여 포괄적인 답변 제공

답변:
"""
            
            response, _ = await llm_router.generate_response(model, prompt)
            return response
            
        except Exception as e:
            self.logger.error(f"통합 답변 생성 실패: {e}")
            # Fallback: 간단한 결과 요약
            summary = f"'{original_query}'에 대한 다중 검색 결과입니다:\n\n"
            for i, result in enumerate(search_results[:5], 1):
                summary += f"{i}. {result.get('title', '제목 없음')}\n"
                summary += f"   {result.get('snippet', '설명 없음')[:150]}...\n\n"
            return summary
    
    async def _enhance_summary(
        self,
        original_query: str,
        search_summary: str,
        model: str
    ) -> str:
        """검색 요약을 LLM으로 더욱 향상시킴"""
        try:
            prompt = f"""
사용자 질문: "{original_query}"

웹 검색 요약:
{search_summary}

위의 검색 요약을 바탕으로 사용자 질문에 더욱 직접적이고 유용한 답변을 작성해주세요.

개선 사항:
1. 사용자 의도에 맞는 핵심 정보 강조
2. 실용적인 조언이나 다음 단계 제안
3. 관련된 추가 정보나 주의사항
4. 더 읽기 쉬운 구조로 재구성

한국어로 자연스럽고 도움이 되는 답변을 작성해주세요.
"""
            
            response, _ = await llm_router.generate_response(model, prompt)
            return response
            
        except Exception as e:
            self.logger.warning(f"요약 향상 실패, 원본 요약 사용: {e}")
            return search_summary
    
    
    
    def get_capabilities(self) -> List[str]:
        """에이전트 기능 목록"""
        return [
            "다중 검색어 생성",
            "병렬 웹 검색",
            "지능형 결과 랭킹",
            "중복 제거 및 결과 통합", 
            "실시간 정보 조회",
            "도메인 권위도 평가",
            "최신성 기반 필터링",
            "다중 소스 종합 분석"
        ]
    
    def get_supported_models(self) -> List[str]:
        """지원하는 모델 목록"""
        return ["gemini", "claude", "openai"]


# 에이전트 인스턴스
web_search_agent = WebSearchAgent()