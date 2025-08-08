"""
웹 크롤링 서비스 - 특정 URL 직접 접근 및 콘텐츠 추출
"""

import asyncio
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WebCrawlResult:
    """웹 크롤링 결과 데이터 클래스"""
    
    def __init__(
        self,
        url: str,
        title: str = "",
        content: str = "",
        summary: str = "",
        headings: List[str] = None,
        links: List[str] = None,
        error: str = None,
        status_code: int = 200,
        content_type: str = "",
        last_modified: str = None
    ):
        self.url = url
        self.title = title
        self.content = content
        self.summary = summary
        self.headings = headings or []
        self.links = links or []
        self.error = error
        self.status_code = status_code
        self.content_type = content_type
        self.last_modified = last_modified
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "headings": self.headings,
            "links": self.links,
            "error": self.error,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "last_modified": self.last_modified,
            "timestamp": self.timestamp
        }


class WebCrawlerService:
    """웹 크롤링 서비스 클래스"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            follow_redirects=True
        )
        
        # 크롤링 제외 도메인 (로봇 차단, 저작권 등)
        self.excluded_domains = {
            "facebook.com", "instagram.com", "twitter.com", "x.com",
            "linkedin.com", "youtube.com", "tiktok.com", "pinterest.com"
        }
    
    def _is_crawlable_url(self, url: str) -> bool:
        """URL이 크롤링 가능한지 확인"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 제외 도메인 확인
            for excluded in self.excluded_domains:
                if excluded in domain:
                    return False
            
            # 지원하는 스키마 확인
            if parsed.scheme not in ('http', 'https'):
                return False
                
            return True
        except:
            return False
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """HTML에서 텍스트 내용 추출"""
        # 불필요한 태그 제거
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # 메인 콘텐츠 영역 찾기
        content_selectors = [
            'main', 'article', '.content', '.post', '.entry',
            '#content', '#main', '.main-content', '.article-content'
        ]
        
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # 메인 콘텐츠가 없으면 body 전체 사용
        if not main_content:
            main_content = soup.find('body') or soup
        
        # 텍스트 추출
        text = main_content.get_text(separator=' ', strip=True)
        
        # 여러 공백을 하나로 정리
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[str]:
        """제목 태그 (h1-h6) 추출"""
        headings = []
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                text = heading.get_text(strip=True)
                if text and len(text) <= 200:  # 너무 긴 제목 제외
                    headings.append(text)
        return headings
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """링크 추출 (최대 20개)"""
        links = []
        for link in soup.find_all('a', href=True)[:20]:
            href = link['href']
            if href.startswith(('http://', 'https://')):
                links.append(href)
            elif href.startswith('/'):
                links.append(urljoin(base_url, href))
        return links
    
    def _generate_summary(self, content: str, max_length: int = 500) -> str:
        """콘텐츠 요약 생성 (간단한 문장 기반)"""
        if not content:
            return ""
        
        # 문장 단위로 분할
        sentences = re.split(r'[.!?]\s+', content)
        
        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) <= max_length:
                summary += sentence + ". "
            else:
                break
        
        return summary.strip()
    
    async def crawl_url(self, url: str, extract_links: bool = False) -> WebCrawlResult:
        """특정 URL 크롤링"""
        if not self._is_crawlable_url(url):
            return WebCrawlResult(
                url=url,
                error="크롤링이 허용되지 않는 URL입니다"
            )
        
        try:
            logger.info(f"웹 크롤링 시작: {url}")
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            # 콘텐츠 타입 확인
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                return WebCrawlResult(
                    url=url,
                    error=f"지원하지 않는 콘텐츠 타입: {content_type}",
                    content_type=content_type,
                    status_code=response.status_code
                )
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 제목 추출
            title_element = soup.find('title')
            title = title_element.get_text(strip=True) if title_element else ""
            
            # 메타 태그에서 추가 정보 추출
            if not title:
                h1 = soup.find('h1')
                title = h1.get_text(strip=True) if h1 else "제목 없음"
            
            # 텍스트 콘텐츠 추출
            content = self._extract_text_content(soup)
            
            # 제목들 추출
            headings = self._extract_headings(soup)
            
            # 링크 추출 (선택적)
            links = self._extract_links(soup, url) if extract_links else []
            
            # 요약 생성
            summary = self._generate_summary(content)
            
            # Last-Modified 헤더 확인
            last_modified = response.headers.get('last-modified')
            
            logger.info(f"웹 크롤링 완료: {url} (제목: {title[:50]}, 콘텐츠: {len(content)}자)")
            
            return WebCrawlResult(
                url=url,
                title=title,
                content=content,
                summary=summary,
                headings=headings,
                links=links,
                status_code=response.status_code,
                content_type=content_type,
                last_modified=last_modified
            )
            
        except httpx.TimeoutException:
            logger.warning(f"웹 크롤링 타임아웃: {url}")
            return WebCrawlResult(url=url, error="페이지 로딩 시간 초과")
            
        except httpx.HTTPStatusError as e:
            logger.warning(f"웹 크롤링 HTTP 오류: {url} - {e.response.status_code}")
            return WebCrawlResult(
                url=url, 
                error=f"HTTP {e.response.status_code} 오류",
                status_code=e.response.status_code
            )
            
        except Exception as e:
            logger.error(f"웹 크롤링 오류: {url} - {e}")
            return WebCrawlResult(url=url, error=f"크롤링 실패: {str(e)}")
    
    async def search_in_content(self, crawl_result: WebCrawlResult, query: str) -> Dict[str, Any]:
        """크롤링된 콘텐츠에서 검색"""
        if crawl_result.error:
            return {
                "found": False,
                "error": crawl_result.error,
                "matches": []
            }
        
        content = crawl_result.content.lower()
        query_lower = query.lower()
        
        # 단순 키워드 매칭
        matches = []
        if query_lower in content:
            # 키워드 주변 텍스트 추출 (컨텍스트)
            import re
            pattern = re.compile(f'.{{0,100}}{re.escape(query_lower)}.{{0,100}}', re.IGNORECASE)
            for match in pattern.finditer(crawl_result.content):
                context = match.group().strip()
                matches.append({
                    "context": context,
                    "position": match.start()
                })
                
                if len(matches) >= 5:  # 최대 5개 매치
                    break
        
        # 제목에서도 검색
        title_match = query_lower in crawl_result.title.lower() if crawl_result.title else False
        
        # 헤딩에서도 검색
        heading_matches = [h for h in crawl_result.headings if query_lower in h.lower()]
        
        return {
            "found": len(matches) > 0 or title_match or len(heading_matches) > 0,
            "query": query,
            "matches_count": len(matches),
            "matches": matches,
            "title_match": title_match,
            "heading_matches": heading_matches,
            "summary": crawl_result.summary if matches else ""
        }
    
    async def close(self):
        """클라이언트 정리"""
        await self.client.aclose()


# 전역 웹 크롤러 인스턴스
web_crawler = WebCrawlerService()