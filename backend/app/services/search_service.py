"""
검색 서비스 - 웹 검색 및 결과 캐싱
"""

import asyncio
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.cache import CacheRepository
from app.services.cache_manager import cache_manager


class SearchResult:
    """검색 결과 데이터 클래스"""
    
    def __init__(
        self,
        title: str,
        url: str,
        snippet: str,
        source: str = "web",
        score: float = 0.0,
        timestamp: str = None
    ):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
        self.score = score
        self.timestamp = timestamp or datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "score": self.score,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchResult":
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            snippet=data.get("snippet", ""),
            source=data.get("source", "web"),
            score=data.get("score", 0.0),
            timestamp=data.get("timestamp")
        )


class SearchService:
    """검색 서비스 클래스"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        self.cache_ttl = 3600  # 1시간 캐시
    
    def _generate_cache_key(self, query: str, **kwargs) -> str:
        """캐시 키 생성"""
        # 쿼리와 추가 파라미터를 조합하여 고유 키 생성
        key_data = {
            "query": query.lower().strip(),
            "source": kwargs.get("source", "web"),
            "max_results": kwargs.get("max_results", 5),
            "language": kwargs.get("language", "ko")
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        hash_key = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        return f"search:{hash_key}"
    
    async def search_web_mock(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[SearchResult]:
        """Mock 웹 검색 (API 키 없이 테스트용)"""
        
        # 다양한 쿼리별 Mock 결과
        mock_results = {
            "ai": [
                SearchResult(
                    title="인공지능(AI) 기술 동향 2024",
                    url="https://example.com/ai-trends-2024",
                    snippet="2024년 인공지능 기술의 주요 동향과 발전 방향을 살펴봅니다. 생성형 AI, 멀티모달 AI, 그리고 AI의 실용적 활용 사례들을 소개합니다.",
                    source="tech_blog",
                    score=0.95
                ),
                SearchResult(
                    title="ChatGPT와 Claude AI 성능 비교",
                    url="https://example.com/llm-comparison",
                    snippet="주요 대형 언어 모델들의 성능을 다양한 측면에서 비교 분석한 결과를 공개합니다. 각 모델의 장단점과 적용 분야별 추천을 확인해보세요.",
                    source="research_paper",
                    score=0.92
                )
            ],
            "python": [
                SearchResult(
                    title="Python 3.12 새로운 기능 완벽 가이드",
                    url="https://example.com/python-3-12-features",
                    snippet="Python 3.12에서 새롭게 추가된 기능들을 상세히 설명합니다. 성능 개선사항, 새로운 문법, 그리고 개발자들이 알아야 할 변경점들을 다룹니다.",
                    source="official_docs",
                    score=0.98
                ),
                SearchResult(
                    title="FastAPI vs Django 2024년 성능 비교",
                    url="https://example.com/fastapi-django-comparison",
                    snippet="최신 Python 웹 프레임워크인 FastAPI와 전통적인 Django의 성능을 실제 프로젝트를 통해 비교 분석했습니다.",
                    source="dev_community",
                    score=0.87
                )
            ],
            "웹개발": [
                SearchResult(
                    title="2024 웹 개발 트렌드와 전망",
                    url="https://example.com/web-dev-trends-2024",
                    snippet="2024년 웹 개발 분야의 주요 트렌드를 분석합니다. React 18, Next.js 14, 그리고 새로운 웹 기술들의 발전 방향을 살펴봅니다.",
                    source="tech_magazine",
                    score=0.91
                )
            ]
        }
        
        # 키워드 매칭을 통한 결과 반환
        results = []
        query_lower = query.lower()
        
        for keyword, search_results in mock_results.items():
            if keyword in query_lower or any(k in query_lower for k in keyword.split()):
                results.extend(search_results)
        
        # 기본 결과가 없으면 일반적인 Mock 결과 생성
        if not results:
            results = [
                SearchResult(
                    title=f"'{query}' 관련 최신 정보",
                    url=f"https://example.com/search?q={quote_plus(query)}",
                    snippet=f"'{query}'에 대한 상세한 정보와 분석을 제공합니다. 최신 동향과 실용적인 활용 방법을 확인해보세요.",
                    source="search_engine",
                    score=0.85
                ),
                SearchResult(
                    title=f"{query} - 종합 가이드",
                    url=f"https://example.com/guide/{quote_plus(query)}",
                    snippet=f"{query}에 대한 포괄적인 가이드입니다. 기초부터 고급 활용법까지 단계별로 설명합니다.",
                    source="documentation",
                    score=0.78
                )
            ]
        
        # max_results 제한 적용
        return results[:max_results]
    
    async def search_duckduckgo(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[SearchResult]:
        """DuckDuckGo 검색 (API 키 불필요)"""
        try:
            # DuckDuckGo Instant Answer API 사용
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Abstract 정보
            if data.get("Abstract"):
                results.append(SearchResult(
                    title=data.get("Heading", query),
                    url=data.get("AbstractURL", ""),
                    snippet=data["Abstract"],
                    source="duckduckgo_abstract",
                    score=0.95
                ))
            
            # Definition 정보 (존재하는 경우)
            if data.get("Definition"):
                results.append(SearchResult(
                    title=data.get("Definition", {}).get("Source", query),
                    url=data.get("Definition", {}).get("FirstURL", ""),
                    snippet=data.get("Definition", {}).get("Text", ""),
                    source="duckduckgo_definition",
                    score=0.93
                ))
            
            # Related topics
            for topic in data.get("RelatedTopics", [])[:max_results-len(results)]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append(SearchResult(
                        title=topic.get("Result", "").split(" - ")[0] if " - " in topic.get("Result", "") else query,
                        url=topic.get("FirstURL", ""),
                        snippet=topic["Text"],
                        source="duckduckgo_topic",
                        score=0.80
                    ))
            
            return results[:max_results]
            
        except Exception as e:
            print(f"DuckDuckGo 검색 오류: {e}")
            return []
    
    async def search_google(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> List[SearchResult]:
        """Google Custom Search API를 사용한 웹 검색"""
        
        if not settings.GOOGLE_API_KEY or not settings.GOOGLE_CSE_ID:
            print("Google API 키 또는 CSE ID가 설정되지 않음")
            return []
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": settings.GOOGLE_API_KEY,
                "cx": settings.GOOGLE_CSE_ID,
                "q": query,
                "num": min(max_results, 10),  # Google API는 최대 10개까지
                "hl": kwargs.get("language", "ko"),  # 한국어 인터페이스
                "safe": "medium"  # SafeSearch 중간 수준
                # searchType 제거 - 기본값이 웹 검색
            }
            
            response = await self.client.get(url, params=params, timeout=10.0)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # 검색 결과가 없는 경우 조기 반환
            if "items" not in data:
                print(f"Google 검색 결과 없음: {query}")
                return []
            
            # 검색 결과 파싱
            items = data.get("items", [])
            for item in items[:max_results]:
                # URL 검증 (유효한 HTTP/HTTPS URL인지 확인)
                link = item.get("link", "")
                if not link.startswith(("http://", "https://")):
                    continue
                
                result = SearchResult(
                    title=item.get("title", "").strip(),
                    url=link,
                    snippet=item.get("snippet", "").strip(),
                    source=f"google_{item.get('displayLink', 'unknown')}",
                    score=0.9 - (len(results) * 0.05)  # 순서에 따른 점수
                )
                
                # 빈 제목이나 스니펫이 있는 결과 필터링
                if result.title and result.snippet:
                    results.append(result)
            
            print(f"Google 검색 완료: {query} -> {len(results)}개 결과")
            return results
            
        except httpx.TimeoutException:
            print(f"Google 검색 타임아웃: {query}")
            return []
        except httpx.HTTPStatusError as e:
            print(f"Google 검색 HTTP 오류: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            print(f"Google 검색 오류: {e}")
            return []
    
    async def search_web(
        self,
        query: str,
        max_results: int = 5,
        use_cache: bool = True,
        session: Optional[AsyncSession] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        웹 검색 실행 (캐시 지원)
        
        Args:
            query: 검색 쿼리
            max_results: 최대 결과 수
            use_cache: 캐시 사용 여부
            session: 데이터베이스 세션
            **kwargs: 추가 검색 옵션
            
        Returns:
            검색 결과 리스트
        """
        cache_key = self._generate_cache_key(query, max_results=max_results, **kwargs)
        
        # 캐시 확인
        if use_cache:
            cached_results = await cache_manager.get(cache_key, session)
            if cached_results:
                print(f"캐시에서 검색 결과 조회: {query}")
                return [SearchResult.from_dict(result) for result in cached_results]
        
        # 실제 검색 수행
        results = []
        
        try:
            # 1. DuckDuckGo를 메인 검색 엔진으로 사용 (안정적이고 무료)
            duckduckgo_results = await self.search_duckduckgo(query, max_results, **kwargs)
            results.extend(duckduckgo_results)
            print(f"DuckDuckGo 검색 결과: {len(duckduckgo_results)}개")
            
            # 2. Google Custom Search로 추가 결과 보완 (설정된 경우에만)
            if len(results) < max_results and settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID:
                remaining = max_results - len(results)
                try:
                    google_results = await self.search_google(query, remaining, **kwargs)
                    results.extend(google_results)
                    print(f"Google 검색 추가 결과: {len(google_results)}개")
                except Exception as google_error:
                    print(f"Google 검색 실패 (무시하고 계속): {google_error}")
            
        except Exception as e:
            print(f"실제 검색 오류: {e}")
            # Google과 DuckDuckGo 모두 실패하면 Mock 검색 시도
            try:
                mock_results = await self.search_web_mock(query, max_results, **kwargs)
                results.extend(mock_results)
                print(f"Mock 검색 결과로 대체: {len(mock_results)}개")
            except Exception as mock_error:
                print(f"Mock 검색도 실패: {mock_error}")
        
        # 2. 모든 실제 검색이 실패했을 때만 Mock 결과 사용
        if not results:
            print("모든 실제 검색 실패 - Mock 검색 결과 사용")
            mock_results = await self.search_web_mock(query, max_results, **kwargs)
            results.extend(mock_results)
        
        # 3. 결과가 있으면 캐시에 저장
        if results and use_cache and session:
            cache_data = [result.to_dict() for result in results]
            await cache_manager.set(cache_key, cache_data, session, ttl_seconds=self.cache_ttl)
            print(f"검색 결과 캐시에 저장: {query} ({len(results)}개 결과)")
        
        return results[:max_results]
    
    async def get_search_suggestions(self, query: str) -> List[str]:
        """검색 제안어 생성"""
        suggestions = []
        
        # 쿼리 기반 제안어 생성
        base_suggestions = [
            f"{query} 사용법",
            f"{query} 예제",
            f"{query} 튜토리얼",
            f"{query} 최신 동향",
            f"{query} vs"
        ]
        
        # 프로그래밍 관련 키워드 감지
        programming_keywords = ["python", "javascript", "react", "api", "database", "웹개발", "앱개발"]
        if any(keyword in query.lower() for keyword in programming_keywords):
            suggestions.extend([
                f"{query} 라이브러리",
                f"{query} 프레임워크",
                f"{query} 에러 해결",
                f"{query} 성능 최적화"
            ])
        
        # AI 관련 키워드 감지
        ai_keywords = ["ai", "머신러닝", "딥러닝", "llm", "chatgpt", "claude"]
        if any(keyword in query.lower() for keyword in ai_keywords):
            suggestions.extend([
                f"{query} 모델",
                f"{query} 활용 사례",
                f"{query} 프롬프트",
                f"{query} 한계"
            ])
        
        return suggestions[:5]
    
    async def summarize_results(
        self,
        query: str,
        results: List[SearchResult],
        session: Optional[AsyncSession] = None
    ) -> str:
        """검색 결과 요약"""
        if not results:
            return f"'{query}'에 대한 검색 결과를 찾을 수 없습니다."
        
        # 결과 요약 생성
        summary_parts = [
            f"🔍 '{query}' 검색 결과 ({len(results)}개):\n"
        ]
        
        for i, result in enumerate(results, 1):
            summary_parts.append(
                f"{i}. **{result.title}**\n"
                f"   {result.snippet[:150]}{'...' if len(result.snippet) > 150 else ''}\n"
                f"   🔗 {result.url}\n"
                f"   📊 출처: {result.source} | 신뢰도: {result.score:.0%}\n"
            )
        
        summary = "\n".join(summary_parts)
        
        # 요약도 캐시에 저장
        if session:
            cache_key = f"summary:{self._generate_cache_key(query)}"
            await cache_manager.set(cache_key, summary, session, ttl_seconds=self.cache_ttl)
        
        return summary
    
    async def close(self):
        """클라이언트 정리"""
        await self.client.aclose()


# 전역 검색 서비스 인스턴스
search_service = SearchService()