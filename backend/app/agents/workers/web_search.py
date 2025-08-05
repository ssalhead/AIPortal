"""
웹 검색 에이전트
"""

import time
import asyncio
import httpx
from typing import Dict, Any, List
from urllib.parse import quote_plus
import json
import logging

from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.llm_router import llm_router

logger = logging.getLogger(__name__)


class WebSearchAgent(BaseAgent):
    """웹 검색 에이전트"""
    
    def __init__(self):
        super().__init__(
            agent_id="web_search",
            name="웹 검색 에이전트",
            description="웹에서 정보를 검색하고 요약합니다"
        )
    
    async def execute(self, input_data: AgentInput, model: str = "gemini") -> AgentOutput:
        """웹 검색 실행"""
        start_time = time.time()
        
        if not self.validate_input(input_data):
            raise ValueError("유효하지 않은 입력 데이터")
        
        try:
            # 검색어 추출 및 정제
            search_query = await self._extract_search_query(input_data.query, model)
            
            # 웹 검색 수행
            search_results = await self._perform_web_search(search_query)
            
            # 검색 결과 요약
            summary = await self._summarize_results(
                input_data.query,
                search_results,
                model
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            metadata = {
                "search_query": search_query,
                "results_count": len(search_results),
                "sources": [result.get("url", "") for result in search_results[:3]],
                "search_method": "mock_search"  # 실제 구현에서는 실제 검색 API 사용
            }
            
            return self.create_output(
                result=summary,
                metadata=metadata,
                execution_time_ms=execution_time,
                model_used=model
            )
            
        except Exception as e:
            self.logger.error(f"웹 검색 실행 중 오류: {e}")
            execution_time = int((time.time() - start_time) * 1000)
            
            return self.create_output(
                result=f"죄송합니다. 웹 검색 중 오류가 발생했습니다: {str(e)}",
                metadata={"error": str(e)},
                execution_time_ms=execution_time,
                model_used=model
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