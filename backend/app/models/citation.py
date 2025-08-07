"""
인용 및 출처 표기 관련 데이터 모델
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """출처 타입"""
    WEB = "web"
    DOCUMENT = "document"
    API = "api"
    DATABASE = "database"
    BOOK = "book"
    ARTICLE = "article"
    RESEARCH_PAPER = "research_paper"
    OTHER = "other"


class Citation(BaseModel):
    """인용 정보"""
    id: str = Field(description="인용 고유 ID")
    text: str = Field(description="인용된 텍스트")
    source_id: str = Field(description="출처 ID")
    start_position: int = Field(description="원문에서 시작 위치")
    end_position: int = Field(description="원문에서 끝 위치")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="인용 정확도")
    context: Optional[str] = Field(default=None, description="인용 맥락")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Source(BaseModel):
    """출처 정보"""
    id: str = Field(description="출처 고유 ID")
    title: str = Field(description="출처 제목")
    url: Optional[HttpUrl] = Field(default=None, description="출처 URL")
    source_type: SourceType = Field(description="출처 타입")
    author: Optional[str] = Field(default=None, description="저자")
    published_date: Optional[datetime] = Field(default=None, description="발행일")
    accessed_date: datetime = Field(default_factory=datetime.utcnow, description="접근일")
    domain: Optional[str] = Field(default=None, description="도메인")
    description: Optional[str] = Field(default=None, description="출처 설명")
    thumbnail: Optional[str] = Field(default=None, description="썸네일 URL")
    language: Optional[str] = Field(default="ko", description="언어 코드")
    reliability_score: float = Field(default=0.5, ge=0.0, le=1.0, description="신뢰도 점수")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추가 메타데이터")


class CitedResponse(BaseModel):
    """인용 정보가 포함된 AI 응답"""
    response_text: str = Field(description="AI 응답 텍스트")
    citations: List[Citation] = Field(default_factory=list, description="인용 목록")
    sources: List[Source] = Field(default_factory=list, description="출처 목록")
    total_sources: int = Field(description="총 출처 개수")
    citation_count: int = Field(description="총 인용 개수")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CitationRequest(BaseModel):
    """인용 요청"""
    message: str = Field(description="사용자 메시지")
    model: str = Field(description="사용할 LLM 모델")
    agent_type: str = Field(description="에이전트 타입")
    include_sources: bool = Field(default=True, description="출처 포함 여부")
    max_sources: int = Field(default=10, ge=1, le=50, description="최대 출처 개수")
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="최소 신뢰도")


class CitationStats(BaseModel):
    """인용 통계"""
    total_citations: int = Field(description="총 인용 수")
    unique_sources: int = Field(description="고유 출처 수")
    avg_confidence: float = Field(description="평균 신뢰도")
    source_type_distribution: Dict[str, int] = Field(description="출처 타입별 분포")
    most_cited_sources: List[Source] = Field(description="가장 많이 인용된 출처")
    citation_trends: Optional[Dict[str, Any]] = Field(default=None, description="인용 트렌드")