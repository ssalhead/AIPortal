"""
검색 서비스 - 웹 검색 및 결과 캐싱
"""

import asyncio
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from urllib.parse import quote_plus
from dataclasses import dataclass, field
from enum import Enum
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.cache import CacheRepository
from app.services.cache_manager import cache_manager
from app.agents.llm_router import llm_router


class SearchType(Enum):
    """검색 타입"""
    WEB = "web"
    NEWS = "news" 
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    GOVERNMENT = "government"
    SHOPPING = "shopping"


class SearchIntent(Enum):
    """검색 의도"""
    INFORMATION = "information"  # 정보 검색
    RECENT = "recent"           # 최신 정보
    COMPARISON = "comparison"    # 비교
    TUTORIAL = "tutorial"       # 사용법/방법
    DEFINITION = "definition"    # 정의
    NEWS = "news"              # 뉴스
    ACADEMIC = "academic"       # 학술


@dataclass
class GoogleSearchParameters:
    """Google Custom Search API 고급 파라미터"""
    
    # 기본 파라미터
    query: str
    num: int = 10
    start: int = 1
    hl: str = "ko"  # 인터페이스 언어
    
    # 지역/언어 설정
    gl: Optional[str] = "KR"  # 지역 설정 (KR=한국)
    cr: Optional[str] = "countryKR"  # 국가 제한
    lr: Optional[str] = "lang_ko"  # 언어 제한
    
    # 시간 기반 필터링
    dateRestrict: Optional[str] = None  # d[1-365], w[1-52], m[1-12], y[1-10]
    sort: Optional[str] = None  # date, date-sdate:d:w, date-sdate:d:s
    
    # 정밀 검색
    exactTerms: Optional[str] = None  # 정확한 구문
    excludeTerms: Optional[str] = None  # 제외할 단어
    orTerms: Optional[str] = None  # OR 검색
    
    # 사이트/URL 필터링
    siteSearch: Optional[str] = None  # 특정 사이트 검색
    siteSearchFilter: Optional[str] = "i"  # i=포함, e=제외
    
    # 콘텐츠 타입
    fileType: Optional[str] = None  # pdf, doc, ppt 등
    searchType: Optional[str] = None  # image, news
    
    # 권한/라이선스
    rights: Optional[str] = None  # cc_publicdomain, cc_attribute 등
    
    # 고급 검색
    linkSite: Optional[str] = None  # 링크하는 사이트
    relatedSite: Optional[str] = None  # 관련 사이트
    
    # 안전 검색
    safe: str = "medium"  # off, medium, high
    
    def to_params(self) -> Dict[str, str]:
        """API 파라미터로 변환"""
        params = {
            "q": self.query,
            "num": str(self.num),
            "start": str(self.start),
            "hl": self.hl,
            "safe": self.safe
        }
        
        # 옵셔널 파라미터 추가
        optional_fields = [
            "gl", "cr", "lr", "dateRestrict", "sort", 
            "exactTerms", "excludeTerms", "orTerms",
            "siteSearch", "siteSearchFilter", "fileType", 
            "searchType", "rights", "linkSite", "relatedSite"
        ]
        
        for field in optional_fields:
            value = getattr(self, field)
            if value is not None:
                params[field] = str(value)
        
        return params


class QueryAnalyzer:
    """검색 쿼리 분석기 - 키워드 기반 파라미터 자동 설정"""
    
    def __init__(self):
        # 시간 키워드 매핑
        self.time_keywords = {
            "오늘": "d1",
            "어제": "d2", 
            "이번주": "w1",
            "지난주": "w2",
            "이번달": "m1",
            "지난달": "m2",
            "올해": "y1",
            "작년": "y2",
            "최신": "m1",
            "recent": "m1",
            "latest": "d7",
            "today": "d1",
            "yesterday": "d2",
            "week": "w1",
            "month": "m1"
        }
        
        # 파일 타입 키워드
        self.filetype_keywords = {
            "pdf": "pdf",
            "문서": "pdf",
            "논문": "pdf", 
            "보고서": "pdf",
            "ppt": "ppt",
            "프레젠테이션": "ppt",
            "슬라이드": "ppt",
            "엑셀": "xls",
            "spreadsheet": "xls"
        }
        
        # 도메인별 사이트
        self.domain_sites = {
            "뉴스": "news.naver.com OR news.daum.net OR news.joins.com",
            "위키피디아": "wikipedia.org",
            "깃허브": "github.com", 
            "스택오버플로": "stackoverflow.com",
            "정부": ".go.kr",
            "대학": ".ac.kr",
            "논문": "scholar.google.com OR arxiv.org"
        }
        
        # 언어 감지 패턴
        self.korean_pattern = re.compile(r'[가-힣]')
        self.english_pattern = re.compile(r'[a-zA-Z]')
    
    def analyze_query(self, query: str, search_type: SearchType = SearchType.WEB) -> GoogleSearchParameters:
        """쿼리 분석하여 최적 파라미터 생성"""
        
        params = GoogleSearchParameters(query=query)
        query_lower = query.lower()
        
        # 1. 시간 기반 분석
        date_restrict = self._analyze_time_keywords(query_lower)
        if date_restrict:
            params.dateRestrict = date_restrict
            if any(word in query_lower for word in ["뉴스", "news", "최신", "latest"]):
                params.sort = "date"
        
        # 2. 파일 타입 분석
        file_type = self._analyze_filetype_keywords(query_lower)
        if file_type:
            params.fileType = file_type
        
        # 3. 도메인 분석
        site_search = self._analyze_domain_keywords(query_lower)
        if site_search:
            params.siteSearch = site_search
        
        # 4. 검색 타입별 최적화
        self._optimize_by_search_type(params, search_type, query_lower)
        
        # 5. 언어/지역 최적화
        self._optimize_language_region(params, query)
        
        # 6. 현재 연도 자동 추가 (하드코딩 문제 해결)
        current_year = datetime.now().year
        if any(word in query_lower for word in ["최신", "현재", "오늘", "이번년", str(current_year-1)]):
            # 작년 키워드가 있으면 현재 연도를 exactTerms에 추가
            if params.exactTerms:
                params.exactTerms += f" {current_year}"
            else:
                params.exactTerms = str(current_year)
        
        return params
    
    def _analyze_time_keywords(self, query: str) -> Optional[str]:
        """시간 키워드 분석"""
        for keyword, date_restrict in self.time_keywords.items():
            if keyword in query:
                return date_restrict
        return None
    
    def _analyze_filetype_keywords(self, query: str) -> Optional[str]:
        """파일 타입 키워드 분석"""
        for keyword, filetype in self.filetype_keywords.items():
            if keyword in query:
                return filetype
        return None
    
    def _analyze_domain_keywords(self, query: str) -> Optional[str]:
        """도메인 키워드 분석"""
        for keyword, sites in self.domain_sites.items():
            if keyword in query:
                return sites
        return None
    
    def _optimize_by_search_type(self, params: GoogleSearchParameters, search_type: SearchType, query: str):
        """검색 타입별 최적화"""
        
        if search_type == SearchType.NEWS:
            params.searchType = "news"
            params.sort = "date"
            params.dateRestrict = params.dateRestrict or "m1"
            
        elif search_type == SearchType.ACADEMIC:
            params.siteSearch = "scholar.google.com OR arxiv.org OR researchgate.net"
            params.fileType = "pdf"
            params.rights = "cc_publicdomain"
            
        elif search_type == SearchType.TECHNICAL:
            params.siteSearch = "github.com OR stackoverflow.com OR docs.python.org"
            
        elif search_type == SearchType.GOVERNMENT:
            params.siteSearch = ".go.kr OR .gov"
            params.cr = "countryKR"
            
        elif search_type == SearchType.SHOPPING:
            params.siteSearch = "shopping.naver.com OR gmarket.co.kr OR coupang.com"
            params.dateRestrict = "m3"  # 3개월 이내
    
    def _optimize_language_region(self, params: GoogleSearchParameters, query: str):
        """언어/지역 최적화"""
        
        korean_chars = len(self.korean_pattern.findall(query))
        english_chars = len(self.english_pattern.findall(query))
        
        if korean_chars > english_chars:
            # 한국어 중심 검색
            params.gl = "KR"
            params.cr = "countryKR" 
            params.lr = "lang_ko"
        elif english_chars > korean_chars * 2:
            # 영어 중심 검색
            params.gl = "US"
            params.cr = None
            params.lr = "lang_en"
        else:
            # 혼합 검색 - 한국어 우선
            params.gl = "KR"
            params.lr = None  # 언어 제한 해제


@dataclass
class CandidateSite:
    """메타 검색 후보 사이트"""
    domain: str
    reason: str
    confidence: float
    search_method: str  # "api", "site_operator", "crawling"
    specific_pages: List[str] = field(default_factory=list)
    has_search_api: bool = False
    has_search_url: bool = True


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


class BalancedSearchStrategy:
    """균형잡힌 검색 전략 클래스"""
    
    def __init__(self, search_service):
        self.search_service = search_service
        self.category_weight = 0.4      # 카테고리별 검색 비중
        self.general_weight = 0.6       # 일반 검색 비중
        self.max_category_results = 4   # 카테고리별 최대 결과
        self.max_general_results = 6    # 일반 검색 최대 결과
        self.confidence_threshold = 0.3 # 카테고리 감지 임계값
        
        # 카테고리별 전문 사이트 매핑
        self.category_sites = {
            "business": {
                "채용": "saramin.co.kr OR jobkorea.co.kr OR wanted.co.kr OR rocketpunch.com",
                "기업정보": "jobplanet.co.kr OR dart.fss.or.kr OR crunchbase.com OR kind.or.kr", 
                "스타트업": "rocketpunch.com OR platum.kr OR venturesquare.net OR thevc.kr",
                "B2B솔루션": "gobizkorea.com OR kotra.or.kr OR kita.net",
                "프리랜싱": "kmong.com OR soomgo.com OR wishket.com OR taling.me"
            },
            "research": {
                "논문": "scholar.google.com OR arxiv.org OR riss.kr OR dbpia.co.kr OR kiss.kstudy.com",
                "특허": "kipris.or.kr OR patents.google.com OR wipo.int",
                "연구과제": "ntis.go.kr OR kistep.re.kr OR nrf.re.kr",
                "기술정보": "kosen21.org OR keit.re.kr OR kist.re.kr OR etri.re.kr",
                "표준": "kats.go.kr OR ks.go.kr OR iso.org OR iec.ch",
                "연구기관": "kist.re.kr OR etri.re.kr OR kaist.ac.kr OR kriss.re.kr"
            },
            "trade": {
                "수출입": "kotra.or.kr OR kita.net OR unipass.go.kr OR ktdb.go.kr",
                "관세": "customs.go.kr OR unipass.go.kr OR ktdb.go.kr",
                "무역통계": "kita.net OR kotis.net OR trademap.org",
                "FTA": "fta.go.kr OR kotra.or.kr",
                "해외진출": "kotra.or.kr OR koreaexim.go.kr OR k-sure.or.kr",
                "원산지": "fta.go.kr OR customs.go.kr"
            }
        }
        
        # 카테고리별 키워드 매핑
        self.category_keywords = {
            "research": ["논문", "연구", "특허", "기술개발", "R&D", "표준", "개발", "실험", "분석", "학술"],
            "trade": ["수출", "수입", "무역", "관세", "FTA", "원산지", "해외진출", "국제", "통관", "수출입"],
            "business": ["회사", "기업", "채용", "취업", "비즈니스", "스타트업", "면접", "연봉", "이력서", "구인"]
        }
    
    def detect_category_with_confidence(self, query: str) -> Tuple[Optional[str], float]:
        """카테고리 감지 (보수적 접근)"""
        category_scores = {}
        query_lower = query.lower()
        
        for category, keywords in self.category_keywords.items():
            # 키워드 매칭 점수 계산
            matches = sum(1 for kw in keywords if kw in query_lower)
            if matches > 0:
                # 매칭된 키워드 수 / 전체 키워드 수의 비율로 점수 계산
                category_scores[category] = min(matches / 3, 1.0)  # 최대 1.0으로 제한
        
        # 최고 점수 카테고리 반환 (임계값 이상일 때만)
        if category_scores and max(category_scores.values()) >= self.confidence_threshold:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            return best_category
        else:
            return None, 0.0
    
    def _get_category_sites(self, category: str, query: str) -> str:
        """카테고리에 맞는 사이트 선택"""
        if category not in self.category_sites:
            return ""
        
        # 쿼리에 가장 적합한 서브카테고리 찾기
        query_lower = query.lower()
        category_mapping = self.category_sites[category]
        
        for subcategory, sites in category_mapping.items():
            subcategory_keywords = {
                "채용": ["채용", "구인", "취업", "면접", "이력서", "job"],
                "기업정보": ["회사", "기업", "정보", "소개", "연혁"],
                "논문": ["논문", "연구", "학술", "저널", "paper"],
                "특허": ["특허", "patent", "발명", "지식재산"],
                "수출입": ["수출", "수입", "export", "import"],
                "관세": ["관세", "세금", "tax", "duty"]
            }
            
            if subcategory in subcategory_keywords:
                keywords = subcategory_keywords[subcategory]
                if any(keyword in query_lower for keyword in keywords):
                    return sites
        
        # 기본적으로 첫 번째 카테고리 반환
        return list(category_mapping.values())[0]
    
    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인 추출"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return url
    
    def _ensure_diversity(self, results: List[SearchResult]) -> List[SearchResult]:
        """도메인 다양성 보장 (같은 도메인 3개 이상 방지)"""
        domain_counts = {}
        diverse_results = []
        
        for result in results:
            domain = self._extract_domain(result.url)
            if domain_counts.get(domain, 0) < 3:  # 도메인당 최대 3개
                diverse_results.append(result)
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        return diverse_results
    
    async def execute_balanced_search(
        self, 
        query: str, 
        category: str, 
        max_results: int = 10,
        session = None
    ) -> List[SearchResult]:
        """균형잡힌 검색 실행"""
        
        # 1. 병렬 검색 실행
        general_task = asyncio.create_task(
            self.search_service._execute_general_search(
                query, self.max_general_results, session
            )
        )
        
        category_task = asyncio.create_task(
            self._execute_category_search(
                query, category, self.max_category_results, session
            )
        )
        
        try:
            general_results, category_results = await asyncio.gather(
                general_task, category_task, return_exceptions=True
            )
            
            # 예외 처리
            if isinstance(general_results, Exception):
                print(f"일반 검색 실패: {general_results}")
                general_results = []
            if isinstance(category_results, Exception):
                print(f"카테고리 검색 실패: {category_results}")
                category_results = []
                
        except Exception as e:
            print(f"병렬 검색 실행 중 오류: {e}")
            # Fallback: 일반 검색만 실행
            general_results = await self.search_service._execute_general_search(
                query, max_results, session
            )
            category_results = []
        
        # 2. 결과 통합 및 균형 조정
        balanced_results = self._merge_and_balance(
            general_results, category_results, query
        )
        
        return balanced_results[:max_results]
    
    async def _execute_category_search(
        self, 
        query: str, 
        category: str, 
        max_results: int,
        session = None
    ) -> List[SearchResult]:
        """카테고리별 전문 검색 실행"""
        
        # 카테고리에 맞는 사이트 검색
        category_sites = self._get_category_sites(category, query)
        if not category_sites:
            return []
        
        # 사이트 제한 검색 실행
        search_params = GoogleSearchParameters(
            query=query,
            num=max_results,
            siteSearch=category_sites
        )
        
        return await self.search_service.search_google(
            query=query,
            max_results=max_results,
            search_type=SearchType.WEB,
            session=session,
            **{"custom_params": search_params}
        )
    
    def _merge_and_balance(
        self, 
        general_results: List[SearchResult], 
        category_results: List[SearchResult], 
        query: str
    ) -> List[SearchResult]:
        """일반 검색과 카테고리 검색 결과를 균형있게 통합"""
        
        # 1. 중복 URL 제거 (도메인 기준)
        all_results = {}
        
        # 2. 일반 검색 결과 우선 추가 (기본 다양성 확보)
        for result in general_results[:self.max_general_results]:
            domain = self._extract_domain(result.url)
            if domain not in all_results:
                # SearchResult 객체에 추가 속성 설정
                result.source_type = "general"
                result.boost_score = 1.0  # 기본 점수
                all_results[domain] = result
        
        # 3. 카테고리 검색 결과 추가 (전문성 강화)
        category_boost = 1.2  # 카테고리 결과에 약간의 부스트
        added_category_count = 0
        
        for result in category_results:
            domain = self._extract_domain(result.url)
            if domain not in all_results and added_category_count < self.max_category_results:
                result.source_type = "category"
                result.boost_score = category_boost
                all_results[domain] = result
                added_category_count += 1
            elif domain in all_results:
                # 이미 있는 결과면 카테고리 점수로 업그레이드
                existing = all_results[domain]
                existing.boost_score = max(getattr(existing, 'boost_score', 1.0), category_boost)
                existing.source_type = "mixed"
        
        # 4. 최종 점수로 정렬
        final_results = list(all_results.values())
        for result in final_results:
            boost_score = getattr(result, 'boost_score', 1.0)
            result.final_score = result.score * boost_score
        
        final_results.sort(key=lambda x: getattr(x, 'final_score', x.score), reverse=True)
        
        # 5. 다양성 검증
        return self._ensure_diversity(final_results)


class MetaSearchStrategy:
    """2단계 메타 검색 전략 클래스"""
    
    def __init__(self, search_service):
        self.search_service = search_service
        self.meta_weight = 0.5      # 메타 검색 비중 50%
        self.general_weight = 0.5   # 일반 검색 비중 50%
        self.max_meta_results = 5   # 메타 검색 최대 결과
        self.max_general_results = 5 # 일반 검색 최대 결과
        
        # 카테고리별 기본 추천 사이트
        self.category_default_sites = {
            "programming": [
                CandidateSite("stackoverflow.com", "프로그래밍 Q&A 전문", 0.9, "site_operator"),
                CandidateSite("github.com", "오픈소스 코드 저장소", 0.9, "site_operator"),
                CandidateSite("dev.to", "개발자 커뮤니티", 0.8, "site_operator"),
                CandidateSite("medium.com", "기술 블로그 플랫폼", 0.7, "site_operator")
            ],
            "business": [
                CandidateSite("linkedin.com", "비즈니스 네트워크", 0.8, "site_operator"),
                CandidateSite("harvard.edu", "하버드 비즈니스 리뷰", 0.9, "site_operator"),
                CandidateSite("mckinsey.com", "경영 컨설팅", 0.8, "site_operator")
            ],
            "research": [
                CandidateSite("scholar.google.com", "학술 검색", 0.9, "site_operator"),
                CandidateSite("arxiv.org", "논문 저장소", 0.9, "site_operator"),
                CandidateSite("researchgate.net", "연구자 네트워크", 0.8, "site_operator")
            ],
            "news": [
                CandidateSite("bbc.com", "국제 뉴스", 0.8, "site_operator"),
                CandidateSite("reuters.com", "통신사", 0.9, "site_operator"),
                CandidateSite("news.naver.com", "한국 뉴스", 0.8, "site_operator")
            ]
        }
    
    async def execute_meta_search(
        self, 
        query: str, 
        max_results: int = 10,
        session = None
    ) -> List[SearchResult]:
        """2단계 메타 검색 실행"""
        
        print(f"🎯 메타 검색 시작: '{query}'")
        
        # 1단계: 적합한 사이트 발견
        candidate_sites = await self._discover_relevant_sites(query)
        print(f"🔍 후보 사이트 발견: {len(candidate_sites)}개")
        
        # 2단계: 각 사이트에서 검색 실행
        meta_results = await self._search_within_sites(query, candidate_sites, session)
        print(f"🎯 메타 검색 결과: {len(meta_results)}개")
        
        # 3단계: 일반 검색 결과도 가져오기
        general_results = await self.search_service._execute_general_search(
            query, self.max_general_results, session
        )
        print(f"📊 일반 검색 결과: {len(general_results)}개")
        
        # 4단계: 결과 통합 및 순위화
        final_results = self._merge_meta_results(meta_results, general_results, query)
        
        print(f"🔀 최종 통합 결과: {len(final_results)}개")
        return final_results[:max_results]
    
    async def _discover_relevant_sites(self, query: str) -> List[CandidateSite]:
        """검색어에 적합한 사이트 발견"""
        all_candidates = []
        
        # 방법 1: LLM 기반 사이트 추천
        try:
            llm_recommendations = await self._get_llm_site_recommendations(query)
            all_candidates.extend(llm_recommendations)
            print(f"💡 LLM 추천 사이트: {len(llm_recommendations)}개")
        except Exception as e:
            print(f"❌ LLM 추천 실패: {e}")
        
        # 방법 2: 카테고리 기반 기본 사이트
        category_sites = self._get_category_default_sites(query)
        all_candidates.extend(category_sites)
        print(f"📂 카테고리 기본 사이트: {len(category_sites)}개")
        
        # 방법 3: 사이트 발견 검색 (향후 구현)
        # discovery_sites = await self._search_for_sites(query)
        # all_candidates.extend(discovery_sites)
        
        # 중복 제거 및 신뢰도 기준 정렬
        unique_sites = self._deduplicate_sites(all_candidates)
        return sorted(unique_sites, key=lambda x: x.confidence, reverse=True)[:8]
    
    async def _get_llm_site_recommendations(self, query: str) -> List[CandidateSite]:
        """LLM을 활용한 적합한 사이트 추천"""
        
        prompt = f"""
다음 검색어에 가장 적합한 웹사이트 5개를 추천해주세요: "{query}"

고려사항:
1. 검색어의 주제와 성격 분석
2. 해당 주제에 전문화된 사이트
3. 신뢰할 수 있는 정보원
4. 한국어/영어 사이트 모두 고려

JSON 형태로만 응답해주세요:
{{
  "recommended_sites": [
    {{
      "domain": "example.com",
      "reason": "추천 이유 (한 줄로)",
      "confidence": 0.9,
      "search_method": "site_operator"
    }}
  ]
}}
"""
        
        try:
            response, _ = await llm_router.generate_response("gemini", prompt)
            return self._parse_llm_recommendations(response)
        except Exception as e:
            print(f"LLM 사이트 추천 오류: {e}")
            return []
    
    def _parse_llm_recommendations(self, response: str) -> List[CandidateSite]:
        """LLM 응답에서 사이트 추천 파싱"""
        try:
            # JSON 형태로 파싱
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            data = json.loads(clean_response)
            candidates = []
            
            for site_data in data.get("recommended_sites", []):
                candidate = CandidateSite(
                    domain=site_data.get("domain", ""),
                    reason=site_data.get("reason", ""),
                    confidence=site_data.get("confidence", 0.5),
                    search_method=site_data.get("search_method", "site_operator"),
                    specific_pages=site_data.get("specific_pages", [])
                )
                candidates.append(candidate)
            
            return candidates
            
        except json.JSONDecodeError as e:
            print(f"LLM 응답 JSON 파싱 실패: {e}")
            return []
        except Exception as e:
            print(f"LLM 응답 처리 오류: {e}")
            return []
    
    def _get_category_default_sites(self, query: str) -> List[CandidateSite]:
        """카테고리 기반 기본 사이트 선택"""
        query_lower = query.lower()
        selected_sites = []
        
        # 프로그래밍 관련
        programming_keywords = ["python", "javascript", "react", "코딩", "프로그래밍", "개발", "api"]
        if any(keyword in query_lower for keyword in programming_keywords):
            selected_sites.extend(self.category_default_sites.get("programming", []))
        
        # 비즈니스 관련
        business_keywords = ["비즈니스", "경영", "마케팅", "전략", "business", "startup", "회사"]
        if any(keyword in query_lower for keyword in business_keywords):
            selected_sites.extend(self.category_default_sites.get("business", []))
        
        # 연구 관련
        research_keywords = ["논문", "연구", "학술", "research", "study", "academic"]
        if any(keyword in query_lower for keyword in research_keywords):
            selected_sites.extend(self.category_default_sites.get("research", []))
        
        # 뉴스 관련
        news_keywords = ["뉴스", "소식", "현재", "최근", "news", "latest"]
        if any(keyword in query_lower for keyword in news_keywords):
            selected_sites.extend(self.category_default_sites.get("news", []))
        
        return selected_sites
    
    def _deduplicate_sites(self, sites: List[CandidateSite]) -> List[CandidateSite]:
        """사이트 중복 제거"""
        seen_domains = set()
        unique_sites = []
        
        for site in sites:
            if site.domain not in seen_domains:
                seen_domains.add(site.domain)
                unique_sites.append(site)
        
        return unique_sites
    
    async def _search_within_sites(
        self, 
        query: str, 
        sites: List[CandidateSite],
        session = None
    ) -> List[SearchResult]:
        """각 사이트에서 검색 실행"""
        
        search_tasks = []
        for site in sites[:5]:  # 최대 5개 사이트
            if site.search_method == "site_operator":
                task = self._search_via_site_operator(query, site, session)
            elif site.search_method == "crawling":
                task = self._search_via_crawling(query, site, session)
            else:
                task = self._search_via_site_operator(query, site, session)  # 기본값
            
            search_tasks.append(task)
        
        # 병렬 실행
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # 성공한 결과만 수집
        all_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ 사이트 검색 실패 [{sites[i].domain}]: {result}")
            elif isinstance(result, list):
                all_results.extend(result)
                print(f"✅ 사이트 검색 성공 [{sites[i].domain}]: {len(result)}개 결과")
        
        return all_results
    
    async def _search_via_site_operator(
        self, 
        query: str, 
        site: CandidateSite,
        session = None
    ) -> List[SearchResult]:
        """Google site: 연산자 활용 검색"""
        
        site_query = f"site:{site.domain} {query}"
        
        try:
            results = await self.search_service.search_google(
                site_query, 
                max_results=3, 
                search_type=SearchType.WEB,
                session=session
            )
            
            # 메타데이터 추가
            for result in results:
                result.source = f"meta_{site.domain}"
                result.meta_site = site.domain
                result.meta_confidence = site.confidence
                result.meta_reason = site.reason
            
            return results
            
        except Exception as e:
            print(f"사이트 연산자 검색 실패 [{site.domain}]: {e}")
            return []
    
    async def _search_via_crawling(
        self, 
        query: str, 
        site: CandidateSite,
        session = None
    ) -> List[SearchResult]:
        """크롤링 기반 검색 (향후 구현)"""
        # 현재는 사이트 연산자로 대체
        return await self._search_via_site_operator(query, site, session)
    
    def _merge_meta_results(
        self, 
        meta_results: List[SearchResult], 
        general_results: List[SearchResult],
        query: str
    ) -> List[SearchResult]:
        """메타 검색과 일반 검색 결과 통합"""
        
        all_results = {}
        
        # 1. 메타 검색 결과 추가 (높은 부스트)
        for result in meta_results:
            domain = self._extract_domain(result.url)
            if domain not in all_results:
                result.source_type = "meta_search"
                result.boost_score = 1.4  # 메타 검색 높은 보너스
                all_results[domain] = result
        
        # 2. 일반 검색 결과 보완
        added_general = 0
        max_general = max(len(meta_results), 3)  # 최소 3개는 보장
        
        for result in general_results:
            domain = self._extract_domain(result.url)
            if domain not in all_results and added_general < max_general:
                result.source_type = "general"
                result.boost_score = 1.0
                all_results[domain] = result
                added_general += 1
        
        # 3. 최종 점수 계산 및 정렬
        final_results = list(all_results.values())
        for result in final_results:
            boost_score = getattr(result, 'boost_score', 1.0)
            meta_confidence = getattr(result, 'meta_confidence', 0.5)
            
            # 메타 검색의 경우 사이트 신뢰도도 반영
            if hasattr(result, 'meta_confidence'):
                result.final_score = result.score * boost_score * (0.5 + meta_confidence * 0.5)
            else:
                result.final_score = result.score * boost_score
        
        final_results.sort(key=lambda x: getattr(x, 'final_score', x.score), reverse=True)
        
        return final_results
    
    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인 추출"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return url


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
        self.query_analyzer = QueryAnalyzer()  # 쿼리 분석기 추가
        self.balanced_strategy = BalancedSearchStrategy(self)  # 균형 검색 전략 추가
        self.meta_strategy = MetaSearchStrategy(self)  # 메타 검색 전략 추가
    
    def _generate_cache_key(self, query: str, **kwargs) -> str:
        """캐시 키 생성"""
        # 쿼리와 추가 파라미터를 조합하여 고유 키 생성
        key_data = {
            "query": query.lower().strip(),
            "source": kwargs.get("source", "web"),
            "max_results": kwargs.get("max_results", 5),
            "language": kwargs.get("language", "ko"),
            "search_type": kwargs.get("search_type", "web"),
            "category": kwargs.get("category", "none"),
            "meta_search": kwargs.get("meta_search", False)
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        hash_key = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        return f"search:{hash_key}"
    
    def _get_dynamic_cache_ttl(self, search_type: SearchType, query: str) -> int:
        """검색 타입과 쿼리에 따른 동적 TTL 계산"""
        base_ttl = self.cache_ttl  # 기본 1시간
        
        # 시간 민감도에 따른 TTL 조정
        time_sensitive_keywords = ["오늘", "최신", "latest", "recent", "지금", "현재", "today"]
        if any(keyword in query.lower() for keyword in time_sensitive_keywords):
            return int(base_ttl * 0.1)  # 6분 - 시간 민감 정보
        
        # 검색 타입별 TTL 전략
        if search_type == SearchType.NEWS:
            return int(base_ttl * 0.25)  # 15분 - 뉴스는 빠르게 변함
        elif search_type == SearchType.ACADEMIC:
            return int(base_ttl * 4)     # 4시간 - 학술 정보는 안정적
        elif search_type == SearchType.GOVERNMENT:
            return int(base_ttl * 2)     # 2시간 - 공식 정보는 비교적 안정적
        elif search_type == SearchType.TECHNICAL:
            return int(base_ttl * 3)     # 3시간 - 기술 문서는 상대적으로 안정적
        elif search_type == SearchType.SHOPPING:
            return int(base_ttl * 0.5)   # 30분 - 쇼핑 정보는 자주 변함
        else:
            return base_ttl              # 1시간 - 일반 웹 검색
    
    
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
    
    def _process_search_operators(self, query: str) -> Tuple[str, Dict[str, str]]:
        """Google 검색 연산자 처리"""
        processed_query = query
        operators = {}
        
        # site: 연산자 처리
        site_pattern = r'site:([^\s]+)'
        site_match = re.search(site_pattern, query, re.IGNORECASE)
        if site_match:
            site_domain = site_match.group(1)
            operators['site'] = site_domain
            processed_query = re.sub(site_pattern, '', query, flags=re.IGNORECASE).strip()
        
        # inurl: 연산자 처리
        inurl_pattern = r'inurl:([^\s]+)'
        inurl_match = re.search(inurl_pattern, query, re.IGNORECASE)
        if inurl_match:
            url_part = inurl_match.group(1)
            operators['inurl'] = url_part
            processed_query = re.sub(inurl_pattern, '', query, flags=re.IGNORECASE).strip()
        
        # intitle: 연산자 처리  
        intitle_pattern = r'intitle:([^\s]+)'
        intitle_match = re.search(intitle_pattern, query, re.IGNORECASE)
        if intitle_match:
            title_part = intitle_match.group(1)
            operators['intitle'] = title_part
            processed_query = re.sub(intitle_pattern, '', query, flags=re.IGNORECASE).strip()
        
        return processed_query, operators

    async def search_google(
        self,
        query: str,
        max_results: int = 5,
        search_type: SearchType = SearchType.WEB,
        **kwargs
    ) -> List[SearchResult]:
        """Google Custom Search API를 사용한 고급 웹 검색"""
        
        print(f"🔍 Google 검색 시도: '{query}' (타입: {search_type.value})")
        print(f"🔑 API 키 상태: GOOGLE_API_KEY={'있음' if settings.GOOGLE_API_KEY else '없음'}")
        print(f"🔑 CSE ID 상태: GOOGLE_CSE_ID={'있음' if settings.GOOGLE_CSE_ID else '없음'}")
        
        if not settings.GOOGLE_API_KEY or not settings.GOOGLE_CSE_ID:
            print("❌ Google API 키 또는 CSE ID가 설정되지 않음")
            return []
        
        try:
            # 1. 커스텀 파라미터가 있는지 확인 (균형 검색용)
            if "custom_params" in kwargs and kwargs["custom_params"]:
                search_params = kwargs["custom_params"]
                search_params.num = min(max_results, 10)
                print(f"🎯 커스텀 파라미터 사용: 사이트제한={search_params.siteSearch}")
            else:
                # 2. 지능형 쿼리 분석으로 최적 파라미터 생성
                search_params = self.query_analyzer.analyze_query(query, search_type)
                search_params.num = min(max_results, 10)  # Google API는 최대 10개까지
            
            # 3. 기존 검색 연산자 처리도 유지 (하위 호환성)
            processed_query, operators = self._process_search_operators(query)
            if operators:
                # 기존 연산자가 있으면 쿼리 분석 결과와 병합
                if 'site' in operators and not search_params.siteSearch:
                    search_params.siteSearch = operators['site']
                # 원본 쿼리 사용 (Google이 직접 처리)
                search_params.query = query
            
            # 4. API 파라미터 생성
            url = "https://www.googleapis.com/customsearch/v1"
            api_params = {
                "key": settings.GOOGLE_API_KEY,
                "cx": settings.GOOGLE_CSE_ID,
                **search_params.to_params()
            }
            
            # 4. 검색 최적화 로깅
            optimizations = []
            if search_params.dateRestrict:
                optimizations.append(f"시간필터: {search_params.dateRestrict}")
            if search_params.siteSearch:
                optimizations.append(f"사이트제한: {search_params.siteSearch}")
            if search_params.fileType:
                optimizations.append(f"파일타입: {search_params.fileType}")
            if search_params.exactTerms:
                optimizations.append(f"정확한구문: {search_params.exactTerms}")
            if search_params.sort:
                optimizations.append(f"정렬: {search_params.sort}")
            
            if optimizations:
                print(f"🎯 Google 검색 최적화 적용: {', '.join(optimizations)}")
            
            print(f"📋 API 파라미터: {len(api_params)}개 설정됨")
            for key, value in api_params.items():
                if key not in ["key", "cx"]:  # 민감 정보 제외
                    print(f"   {key}: {value}")
            
            # 5. API 호출
            response = await self.client.get(url, params=api_params, timeout=15.0)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # 6. 검색 결과가 없는 경우 조기 반환
            if "items" not in data:
                print(f"❌ Google 검색 결과 없음: {query}")
                # 너무 제한적인 경우 fallback 검색 시도
                if search_params.dateRestrict or search_params.siteSearch:
                    print("🔄 제한 조건 완화하여 재검색 시도")
                    fallback_params = GoogleSearchParameters(query=query, num=search_params.num)
                    fallback_api_params = {
                        "key": settings.GOOGLE_API_KEY,
                        "cx": settings.GOOGLE_CSE_ID,
                        **fallback_params.to_params()
                    }
                    response = await self.client.get(url, params=fallback_api_params, timeout=10.0)
                    data = response.json()
                    if "items" not in data:
                        return []
                else:
                    return []
            
            # 7. 검색 결과 파싱 및 스코어링
            items = data.get("items", [])
            for item in items[:max_results]:
                # URL 검증 (유효한 HTTP/HTTPS URL인지 확인)
                link = item.get("link", "")
                if not link.startswith(("http://", "https://")):
                    continue
                
                # 도메인 추출
                domain = item.get('displayLink', 'unknown')
                
                # 향상된 source 정보
                source_info = f"google_{domain}"
                if search_params.searchType:
                    source_info += f"_{search_params.searchType}"
                if search_params.dateRestrict:
                    source_info += f"_recent"
                
                # 한국 도메인 보너스 점수
                korea_bonus = 0.1 if any(tld in domain for tld in ['.co.kr', '.go.kr', '.ac.kr', '.or.kr']) else 0
                
                # 시간 기반 보너스 점수
                time_bonus = 0.15 if search_params.dateRestrict else 0
                
                # 최종 스코어 계산
                base_score = 0.95 - (len(results) * 0.03)  # 순서에 따른 점수 (더 세밀하게)
                final_score = min(1.0, base_score + korea_bonus + time_bonus)
                
                result = SearchResult(
                    title=item.get("title", "").strip(),
                    url=link,
                    snippet=item.get("snippet", "").strip(),
                    source=source_info,
                    score=final_score,
                    timestamp=datetime.now().isoformat()  # 검색 시점 기록
                )
                
                # 빈 제목이나 스니펫이 있는 결과 필터링
                if result.title and result.snippet:
                    results.append(result)
            
            # 8. 결과 품질 평가
            avg_score = sum(r.score for r in results) / len(results) if results else 0
            quality_level = "높음" if avg_score > 0.8 else "보통" if avg_score > 0.6 else "낮음"
            
            print(f"✅ Google 검색 완료: {query} -> {len(results)}개 결과 (품질: {quality_level}, 평균 점수: {avg_score:.2f})")
            return results
            
        except httpx.TimeoutException:
            print(f"⏱️ Google 검색 타임아웃: {query}")
            return []
        except httpx.HTTPStatusError as e:
            print(f"🚫 Google 검색 HTTP 오류: {e.response.status_code}")
            if e.response.status_code == 429:
                print("   API 할당량 초과 - 잠시 후 재시도 필요")
            elif e.response.status_code == 403:
                print("   API 키 권한 문제 - 설정 확인 필요")
            return []
        except Exception as e:
            print(f"❌ Google 검색 오류: {e}")
            return []
    
    async def _execute_general_search(
        self,
        query: str,
        max_results: int = 5,
        session: Optional[AsyncSession] = None,
        **kwargs
    ) -> List[SearchResult]:
        """일반 검색 실행 (균형 검색용)"""
        results = []
        
        try:
            # 1. Google Custom Search를 메인 검색 엔진으로 사용
            if settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID:
                try:
                    google_results = await self.search_google(
                        query, max_results, SearchType.WEB, session=session, **kwargs
                    )
                    results.extend(google_results)
                except Exception as google_error:
                    print(f"❌ 일반 Google 검색 실패: {google_error}")
            
            # 2. DuckDuckGo로 추가 결과 보완
            if len(results) < max_results:
                remaining = max_results - len(results)
                try:
                    duckduckgo_results = await self.search_duckduckgo(query, remaining, **kwargs)
                    results.extend(duckduckgo_results)
                except Exception as duckduckgo_error:
                    print(f"❌ DuckDuckGo 보완 검색 실패: {duckduckgo_error}")
        
        except Exception as e:
            print(f"💥 일반 검색 전체 오류: {e}")
        
        return results[:max_results]

    async def search_web(
        self,
        query: str,
        max_results: int = 5,
        use_cache: bool = True,
        session: Optional[AsyncSession] = None,
        search_type: SearchType = SearchType.WEB,
        enable_meta_search: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """
        웹 검색 실행 (균형잡힌 검색 + 메타 검색 지원)
        
        Args:
            query: 검색 쿼리
            max_results: 최대 결과 수
            use_cache: 캐시 사용 여부
            session: 데이터베이스 세션
            search_type: 검색 타입 (WEB, NEWS, ACADEMIC 등)
            enable_meta_search: 메타 검색 활성화 여부
            **kwargs: 추가 검색 옵션
            
        Returns:
            검색 결과 리스트
        """
        # 검색 타입에 따른 지능형 캐시 TTL 설정
        dynamic_ttl = self._get_dynamic_cache_ttl(search_type, query)
        
        # 1. 카테고리 감지 (보수적 접근)
        category, confidence = self.balanced_strategy.detect_category_with_confidence(query)
        
        # 2. 메타 검색 적용 여부 판단
        should_use_meta_search = (
            enable_meta_search and 
            self._should_use_meta_search(query, category, confidence)
        )
        
        # 캐시 키 생성 (카테고리 및 메타 검색 정보 포함)
        cache_key = self._generate_cache_key(
            query, 
            max_results=max_results, 
            search_type=search_type.value,
            category=category if category else "none",
            meta_search=should_use_meta_search,
            **kwargs
        )
        
        # 캐시 확인
        if use_cache:
            cached_results = await cache_manager.get(cache_key, session)
            if cached_results:
                search_method = "메타 검색" if should_use_meta_search else "균형 검색" if category else "일반 검색"
                print(f"📦 캐시에서 검색 결과 조회: {query} ({search_method})")
                return [SearchResult.from_dict(result) for result in cached_results]
        
        # 3. 검색 실행
        if should_use_meta_search:
            # 메타 검색 실행 (LLM 기반 사이트 발견 + 사이트별 검색)
            print(f"🎯 메타 검색 실행: '{query}' (전문 사이트 발견 후 검색)")
            results = await self.meta_strategy.execute_meta_search(
                query, max_results, session
            )
            
            # 결과에 메타데이터 추가
            for result in results:
                if not hasattr(result, 'source_type'):
                    result.source_type = "meta_search"
                result.search_method = "meta"
                result.category_detected = category
                result.category_confidence = confidence
                
        elif category and confidence >= self.balanced_strategy.confidence_threshold:
            # 균형잡힌 검색 실행
            print(f"⚖️ 균형 검색 실행: '{query}' (카테고리: {category}, 신뢰도: {confidence:.2f})")
            results = await self.balanced_strategy.execute_balanced_search(
                query, category, max_results, session
            )
            
            # 결과에 메타데이터 추가
            for result in results:
                if not hasattr(result, 'source_type'):
                    result.source_type = "balanced"
                result.search_method = "balanced"
                result.category_detected = category
                result.category_confidence = confidence
        else:
            # 일반 검색만 실행
            print(f"📊 일반 검색 실행: '{query}' (카테고리 감지 안됨 또는 신뢰도 낮음)")
            results = await self._execute_general_search(query, max_results, session, **kwargs)
            
            # 결과에 메타데이터 추가
            for result in results:
                result.source_type = "general"
                result.search_method = "general"
                result.category_detected = None
                result.category_confidence = 0.0
        
        # 4. 결과가 있으면 지능형 TTL로 캐시에 저장
        if results and use_cache and session:
            cache_data = [result.to_dict() for result in results]
            await cache_manager.set(cache_key, cache_data, session, ttl_seconds=dynamic_ttl)
            print(f"💾 검색 결과 캐시에 저장: {query} ({len(results)}개 결과, TTL: {dynamic_ttl}초)")
        
        return results[:max_results]
    
    def _should_use_meta_search(self, query: str, category: Optional[str], confidence: float) -> bool:
        """메타 검색 사용 여부 판단"""
        
        # 1. 특정 키워드가 있는 경우 메타 검색 활성화
        meta_search_keywords = [
            "how to", "tutorial", "guide", "best practices", "example", "documentation",
            "사용법", "방법", "가이드", "튜토리얼", "예제", "문서", "공식", "설명서"
        ]
        
        query_lower = query.lower()
        has_meta_keywords = any(keyword in query_lower for keyword in meta_search_keywords)
        
        # 2. 카테고리 신뢰도가 높은 경우
        has_strong_category = category and confidence >= 0.5
        
        # 3. 기술적 질문인 경우
        technical_keywords = [
            "error", "bug", "fix", "install", "config", "setup", "deploy",
            "에러", "오류", "설치", "설정", "배포", "문제", "해결"
        ]
        is_technical = any(keyword in query_lower for keyword in technical_keywords)
        
        # 메타 검색 사용 조건
        return has_meta_keywords or has_strong_category or is_technical
    
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