"""
인용 및 출처 표기 서비스
"""

import re
import uuid
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from datetime import datetime, timezone

from app.models.citation import (
    Citation, Source, CitedResponse, SourceType, CitationStats
)
from app.services.logging_service import LoggingService


class CitationService:
    """인용 및 출처 처리 서비스"""
    
    def __init__(self, logging_service: LoggingService):
        self.logging_service = logging_service
        self.source_cache: Dict[str, Source] = {}
        
    async def extract_citations_from_response(
        self,
        response_text: str,
        search_results: List[Dict[str, Any]],
        min_confidence: float = 0.7
    ) -> CitedResponse:
        """
        AI 응답에서 인용 정보를 추출하고 출처를 매핑합니다.
        
        Args:
            response_text: AI 응답 텍스트
            search_results: 검색 결과 (웹 검색 등)
            min_confidence: 최소 신뢰도
            
        Returns:
            CitedResponse: 인용 정보가 포함된 응답
        """
        try:
            # 출처 정보 처리
            sources = await self._process_search_results(search_results)
            
            # 인용 추출 (URL, 도메인, 제목 기반)
            citations = await self._extract_citations(response_text, sources, min_confidence)
            
            # 결과 생성
            cited_response = CitedResponse(
                response_text=response_text,
                citations=citations,
                sources=sources,
                total_sources=len(sources),
                citation_count=len(citations)
            )
            
            # 로깅
            await self.logging_service.log_citation_extraction(
                response_length=len(response_text),
                citations_found=len(citations),
                sources_processed=len(sources),
                min_confidence=min_confidence
            )
            
            return cited_response
            
        except Exception as e:
            await self.logging_service.log_error(
                "인용 정보 추출 실패",
                error=str(e),
                extra_data={
                    "response_length": len(response_text),
                    "search_results_count": len(search_results)
                }
            )
            raise
    
    async def _process_search_results(self, search_results: List[Dict[str, Any]]) -> List[Source]:
        """검색 결과를 Source 객체로 변환"""
        sources = []
        
        for idx, result in enumerate(search_results):
            try:
                # URL 파싱
                url = result.get('url', '')
                parsed_url = urlparse(url) if url else None
                domain = parsed_url.netloc if parsed_url else None
                
                # 출처 타입 결정
                source_type = await self._determine_source_type(result, domain)
                
                # 신뢰도 점수 계산
                reliability_score = await self._calculate_reliability_score(result, domain)
                
                source = Source(
                    id=f"source_{uuid.uuid4().hex[:8]}",
                    title=result.get('title', f'출처 {idx + 1}'),
                    url=url if url else None,
                    source_type=source_type,
                    author=result.get('author'),
                    published_date=self._parse_date(result.get('published_date')),
                    domain=domain,
                    description=result.get('description') or result.get('snippet', ''),
                    thumbnail=result.get('thumbnail'),
                    language=result.get('language', 'ko'),
                    reliability_score=reliability_score,
                    metadata={
                        'search_rank': idx + 1,
                        'search_score': result.get('score', 0),
                        'page_rank': result.get('page_rank'),
                        'content_length': len(result.get('content', ''))
                    }
                )
                
                sources.append(source)
                self.source_cache[source.id] = source
                
            except Exception as e:
                await self.logging_service.log_error(
                    f"출처 처리 실패 (인덱스: {idx})",
                    error=str(e),
                    extra_data={"result": result}
                )
                continue
        
        return sources
    
    async def _extract_citations(
        self,
        response_text: str,
        sources: List[Source],
        min_confidence: float
    ) -> List[Citation]:
        """응답 텍스트에서 인용 정보 추출"""
        citations = []
        
        for source in sources:
            # 제목 기반 인용 찾기
            title_citations = await self._find_title_citations(
                response_text, source, min_confidence
            )
            citations.extend(title_citations)
            
            # 도메인 기반 인용 찾기
            domain_citations = await self._find_domain_citations(
                response_text, source, min_confidence
            )
            citations.extend(domain_citations)
            
            # URL 기반 인용 찾기 (직접 링크가 포함된 경우)
            url_citations = await self._find_url_citations(
                response_text, source, min_confidence
            )
            citations.extend(url_citations)
        
        # 중복 제거 및 정렬
        unique_citations = await self._deduplicate_citations(citations)
        return sorted(unique_citations, key=lambda x: x.start_position)
    
    async def _find_title_citations(
        self,
        text: str,
        source: Source,
        min_confidence: float
    ) -> List[Citation]:
        """제목 기반 인용 찾기"""
        citations = []
        
        # 제목의 주요 키워드 추출 (3글자 이상)
        title_keywords = [word for word in source.title.split() if len(word) >= 3]
        
        for keyword in title_keywords[:5]:  # 상위 5개 키워드만 사용
            pattern = re.escape(keyword)
            for match in re.finditer(pattern, text, re.IGNORECASE):
                confidence = await self._calculate_citation_confidence(
                    keyword, source, "title_match"
                )
                
                if confidence >= min_confidence:
                    citation = Citation(
                        id=f"cite_{uuid.uuid4().hex[:8]}",
                        text=keyword,
                        source_id=source.id,
                        start_position=match.start(),
                        end_position=match.end(),
                        confidence=confidence,
                        context=self._extract_context(text, match.start(), match.end())
                    )
                    citations.append(citation)
        
        return citations
    
    async def _find_domain_citations(
        self,
        text: str,
        source: Source,
        min_confidence: float
    ) -> List[Citation]:
        """도메인 기반 인용 찾기"""
        citations = []
        
        if not source.domain:
            return citations
        
        # 도메인에서 회사/기관명 추출
        domain_parts = source.domain.replace('www.', '').split('.')
        main_domain = domain_parts[0] if domain_parts else ''
        
        if len(main_domain) >= 3:
            pattern = re.escape(main_domain)
            for match in re.finditer(pattern, text, re.IGNORECASE):
                confidence = await self._calculate_citation_confidence(
                    main_domain, source, "domain_match"
                )
                
                if confidence >= min_confidence:
                    citation = Citation(
                        id=f"cite_{uuid.uuid4().hex[:8]}",
                        text=main_domain,
                        source_id=source.id,
                        start_position=match.start(),
                        end_position=match.end(),
                        confidence=confidence,
                        context=self._extract_context(text, match.start(), match.end())
                    )
                    citations.append(citation)
        
        return citations
    
    async def _find_url_citations(
        self,
        text: str,
        source: Source,
        min_confidence: float
    ) -> List[Citation]:
        """URL 기반 인용 찾기"""
        citations = []
        
        if not source.url:
            return citations
        
        url_str = str(source.url)
        if url_str in text:
            start_pos = text.find(url_str)
            citation = Citation(
                id=f"cite_{uuid.uuid4().hex[:8]}",
                text=url_str,
                source_id=source.id,
                start_position=start_pos,
                end_position=start_pos + len(url_str),
                confidence=1.0,  # URL 매치는 100% 신뢰도
                context=self._extract_context(text, start_pos, start_pos + len(url_str))
            )
            citations.append(citation)
        
        return citations
    
    async def _determine_source_type(self, result: Dict, domain: Optional[str]) -> SourceType:
        """결과에서 출처 타입 결정"""
        if not domain:
            return SourceType.OTHER
        
        # 도메인 기반 타입 분류
        domain_lower = domain.lower()
        
        if any(edu in domain_lower for edu in ['edu', 'ac.', 'university']):
            return SourceType.RESEARCH_PAPER
        elif any(news in domain_lower for news in ['news', 'press', 'media', 'journal']):
            return SourceType.ARTICLE
        elif any(doc in domain_lower for doc in ['docs', 'documentation', 'manual']):
            return SourceType.DOCUMENT
        elif any(api in domain_lower for api in ['api', 'developer', 'dev']):
            return SourceType.API
        elif 'wikipedia' in domain_lower:
            return SourceType.WEB
        else:
            return SourceType.WEB
    
    async def _calculate_reliability_score(self, result: Dict, domain: Optional[str]) -> float:
        """출처의 신뢰도 점수 계산"""
        score = 0.5  # 기본 점수
        
        if not domain:
            return score
        
        domain_lower = domain.lower()
        
        # 신뢰할 수 있는 도메인 점수 증가
        if any(trusted in domain_lower for trusted in [
            'edu', 'gov', 'org', 'ac.', 'wikipedia', 'naver', 'google'
        ]):
            score += 0.3
        
        # 뉴스 사이트
        if any(news in domain_lower for news in ['news', 'press', 'media']):
            score += 0.2
        
        # 페이지 랭크 고려 (있다면)
        page_rank = result.get('page_rank', 0)
        if page_rank > 0:
            score += min(page_rank / 10, 0.2)
        
        return min(score, 1.0)
    
    async def _calculate_citation_confidence(
        self,
        matched_text: str,
        source: Source,
        match_type: str
    ) -> float:
        """인용 신뢰도 계산"""
        base_confidence = 0.5
        
        # 매치 타입별 가중치
        type_weights = {
            "url_match": 1.0,
            "title_match": 0.8,
            "domain_match": 0.6
        }
        
        confidence = base_confidence * type_weights.get(match_type, 0.5)
        
        # 텍스트 길이 고려 (더 긴 매치가 더 신뢰할만함)
        if len(matched_text) >= 5:
            confidence += 0.2
        
        # 출처 신뢰도 반영
        confidence *= source.reliability_score
        
        return min(confidence, 1.0)
    
    def _extract_context(self, text: str, start: int, end: int, context_length: int = 100) -> str:
        """인용 주변 맥락 추출"""
        context_start = max(0, start - context_length // 2)
        context_end = min(len(text), end + context_length // 2)
        
        context = text[context_start:context_end]
        
        # 시작과 끝에 생략 표시 추가
        if context_start > 0:
            context = "..." + context
        if context_end < len(text):
            context = context + "..."
        
        return context
    
    async def _deduplicate_citations(self, citations: List[Citation]) -> List[Citation]:
        """중복 인용 제거"""
        seen = set()
        unique_citations = []
        
        for citation in citations:
            # 같은 위치의 같은 소스는 중복으로 간주
            key = (citation.source_id, citation.start_position, citation.end_position)
            if key not in seen:
                seen.add(key)
                unique_citations.append(citation)
        
        return unique_citations
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """날짜 문자열 파싱"""
        if not date_str:
            return None
        
        try:
            # 다양한 날짜 형식 지원
            from dateutil import parser
            return parser.parse(date_str)
        except:
            return None
    
    async def get_citation_stats(self, citations: List[Citation], sources: List[Source]) -> CitationStats:
        """인용 통계 생성"""
        if not citations:
            return CitationStats(
                total_citations=0,
                unique_sources=0,
                avg_confidence=0,
                source_type_distribution={},
                most_cited_sources=[]
            )
        
        # 기본 통계
        total_citations = len(citations)
        unique_sources = len(set(c.source_id for c in citations))
        avg_confidence = sum(c.confidence for c in citations) / total_citations
        
        # 출처 타입별 분포
        source_type_dist = {}
        for source in sources:
            source_type = source.source_type.value
            source_type_dist[source_type] = source_type_dist.get(source_type, 0) + 1
        
        # 가장 많이 인용된 출처
        source_citation_count = {}
        for citation in citations:
            source_citation_count[citation.source_id] = source_citation_count.get(citation.source_id, 0) + 1
        
        most_cited_source_ids = sorted(
            source_citation_count.keys(),
            key=lambda x: source_citation_count[x],
            reverse=True
        )[:5]
        
        most_cited_sources = [
            source for source in sources 
            if source.id in most_cited_source_ids
        ]
        
        return CitationStats(
            total_citations=total_citations,
            unique_sources=unique_sources,
            avg_confidence=avg_confidence,
            source_type_distribution=source_type_dist,
            most_cited_sources=most_cited_sources
        )