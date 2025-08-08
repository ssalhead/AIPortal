"""
웹 검색 에이전트
"""

import time
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus
import json
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.llm_router import llm_router
from app.services.search_service import search_service
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


class WebSearchAgent(BaseAgent):
    """웹 검색 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_id="web_search",
            name="웹 검색 에이전트",
            description="웹에서 정보를 검색하고 요약합니다"
        )
    
    async def execute(self, input_data: AgentInput, model: str = "gemini", progress_callback=None) -> AgentOutput:
        """웹 검색 실행 (개선된 버전 - 캐싱 지원)"""
        start_time = time.time()
        
        if not self.validate_input(input_data):
            raise ValueError("유효하지 않은 입력 데이터")
        
        async with AsyncSessionLocal() as session:
            try:
                # 1단계: 검색어 추출 및 정제 (10%)
                if progress_callback:
                    progress_callback("검색어 분석 중...", 10)
                search_query = await self._extract_search_query(input_data.query, model)
                
                # 2단계: 웹 검색 실행 (40%)
                if progress_callback:
                    progress_callback(f"'{search_query}' 검색 중...", 40)
                search_results = await search_service.search_web(
                    query=search_query,
                    max_results=5,
                    use_cache=True,
                    session=session
                )
                
                # 3단계: 검색 결과 요약 (70%)
                if progress_callback:
                    progress_callback("검색 결과 분석 중...", 70)
                summary = await search_service.summarize_results(
                    query=input_data.query,
                    results=search_results,
                    session=session
                )
                
                # 4단계: LLM을 사용한 추가 분석 (90%)
                if progress_callback:
                    progress_callback("AI 분석 및 답변 생성 중...", 90)
                enhanced_summary = await self._enhance_summary(
                    original_query=input_data.query,
                    search_summary=summary,
                    model=model
                )
                
                execution_time = int((time.time() - start_time) * 1000)
                
                # 검색 결과를 citations와 sources로 변환
                citations = []
                sources = []
                
                for i, result in enumerate(search_results[:5]):
                    citation = {
                        "id": f"search_{i+1}",
                        "title": result.title,
                        "url": result.url,
                        "snippet": result.snippet[:200] + "..." if len(result.snippet) > 200 else result.snippet,
                        "source": result.source,
                        "score": result.score
                    }
                    citations.append(citation)
                    
                    source = {
                        "title": result.title,
                        "url": result.url,
                        "type": "web_search",
                        "provider": result.source.split('_')[0] if '_' in result.source else result.source
                    }
                    sources.append(source)
                
                metadata = {
                    "search_query": search_query,
                    "results_count": len(search_results),
                    "search_method": "enhanced_web_search",
                    "cache_used": len(search_results) > 0,
                    "top_sources": [s["title"] for s in sources[:3]]
                }
                
                # AgentOutput 직접 생성 (citations, sources 포함)
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
                self.logger.error(f"웹 검색 실행 중 오류: {e}")
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
    
    async def _extract_search_query(self, user_query: str, model: str) -> str:
        """사용자 질문에서 검색어 추출"""
        try:
            prompt = f"""
사용자 질문을 분석하여 웹 검색에 적합한 검색어를 추출해주세요.

사용자 질문: "{user_query}"

다음 규칙을 따라주세요:
1. 핵심 키워드만 추출
2. 불필요한 조사나 어미 제거
3. 영어로 번역이 필요한 경우 영어 키워드도 포함
4. 최대 5개 단어 이내로 구성

검색어만 반환해주세요.
"""
            
            response, _ = await llm_router.generate_response(model, prompt)
            return response.strip()
            
        except Exception as e:
            self.logger.warning(f"검색어 추출 실패, 원본 쿼리 사용: {e}")
            return user_query
    
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
    
    async def _perform_web_search(self, query: str) -> List[Dict[str, Any]]:
        """웹 검색 수행 (Mock 구현)"""
        # 실제 구현에서는 Google Search API, Bing API, SerpAPI 등을 사용
        # 현재는 Mock 데이터 반환
        
        await asyncio.sleep(0.5)  # 검색 시뮬레이션
        
        mock_results = [
            {
                "title": f"{query}에 대한 최신 정보",
                "url": f"https://example.com/search?q={quote_plus(query)}",
                "snippet": f"{query}에 대한 상세한 정보를 제공합니다. 최신 업데이트된 내용으로 신뢰할 수 있는 정보입니다.",
                "date": "2024-01-01"
            },
            {
                "title": f"{query} 가이드 및 튜토리얼",
                "url": f"https://tutorial.com/{query.replace(' ', '-')}",
                "snippet": f"{query}에 대한 완전한 가이드입니다. 단계별 설명과 실용적인 예제를 포함하고 있습니다.",
                "date": "2024-01-02"
            },
            {
                "title": f"{query} 관련 뉴스 및 업데이트",
                "url": f"https://news.com/latest/{query.replace(' ', '-')}",
                "snippet": f"{query}와 관련된 최신 뉴스와 업데이트 정보입니다. 전문가 분석과 의견을 제공합니다.",
                "date": "2024-01-03"
            }
        ]
        
        self.logger.info(f"Mock 검색 완료: {query}, 결과 {len(mock_results)}개")
        return mock_results
    
    async def _summarize_results(
        self, 
        original_query: str, 
        search_results: List[Dict[str, Any]], 
        model: str
    ) -> str:
        """검색 결과 요약"""
        if not search_results:
            return "검색 결과를 찾을 수 없습니다."
        
        try:
            # 검색 결과를 텍스트로 구성
            results_text = ""
            for i, result in enumerate(search_results[:5], 1):
                results_text += f"""
{i}. {result.get('title', '제목 없음')}
   URL: {result.get('url', '')}
   내용: {result.get('snippet', '설명 없음')}
   날짜: {result.get('date', '날짜 없음')}
"""
            
            prompt = f"""
사용자 질문: "{original_query}"

다음은 웹 검색 결과입니다:
{results_text}

위 검색 결과를 바탕으로 사용자 질문에 대한 종합적이고 유용한 답변을 작성해주세요.

답변 작성 규칙:
1. 사용자 질문에 직접적으로 답변
2. 검색 결과의 핵심 정보를 종합하여 설명
3. 가능한 한 구체적이고 실용적인 정보 제공
4. 출처 정보 포함 (URL 참조)
5. 한국어로 자연스럽게 작성

답변:
"""
            
            response, _ = await llm_router.generate_response(model, prompt)
            return response
            
        except Exception as e:
            self.logger.error(f"검색 결과 요약 실패: {e}")
            # Fallback: 간단한 결과 나열
            summary = f"'{original_query}'에 대한 검색 결과입니다:\n\n"
            for i, result in enumerate(search_results[:3], 1):
                summary += f"{i}. {result.get('title', '제목 없음')}\n"
                summary += f"   {result.get('snippet', '설명 없음')}\n\n"
            return summary
    
    def get_capabilities(self) -> List[str]:
        """에이전트 기능 목록"""
        return [
            "웹 검색",
            "정보 요약", 
            "실시간 정보 조회",
            "검색어 최적화",
            "다중 소스 종합"
        ]
    
    def get_supported_models(self) -> List[str]:
        """지원하는 모델 목록"""
        return ["gemini", "claude", "openai"]


# 에이전트 인스턴스
web_search_agent = WebSearchAgent()