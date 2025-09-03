# Template System Pydantic Models
# AIPortal Canvas Template Library - API 모델 정의

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum

# ===== Enums =====

class TemplateCategory(str, Enum):
    """템플릿 카테고리"""
    BUSINESS = "business"
    SOCIAL_MEDIA = "social_media"
    EDUCATION = "education"
    EVENT = "event"
    PERSONAL = "personal"
    CREATIVE = "creative"
    MARKETING = "marketing"
    PRESENTATION = "presentation"

class TemplateSubcategory(str, Enum):
    """템플릿 서브카테고리"""
    # Business
    BUSINESS_CARD = "business_card"
    BROCHURE = "brochure"
    FLYER = "flyer"
    PRESENTATION = "presentation"
    INVOICE = "invoice"
    LETTERHEAD = "letterhead"
    
    # Social Media
    INSTAGRAM_POST = "instagram_post"
    INSTAGRAM_STORY = "instagram_story"
    FACEBOOK_POST = "facebook_post"
    FACEBOOK_COVER = "facebook_cover"
    TWITTER_POST = "twitter_post"
    YOUTUBE_THUMBNAIL = "youtube_thumbnail"
    LINKEDIN_POST = "linkedin_post"
    
    # Education
    INFOGRAPHIC = "infographic"
    DIAGRAM = "diagram"
    CHART = "chart"
    WORKSHEET = "worksheet"
    CERTIFICATE = "certificate"
    PRESENTATION_SLIDE = "presentation_slide"
    
    # Event
    POSTER = "poster"
    TICKET = "ticket"
    INVITATION = "invitation"
    BANNER = "banner"
    PROGRAM = "program"
    BADGE = "badge"
    
    # Personal
    BIRTHDAY = "birthday"
    WEDDING = "wedding"
    TRAVEL = "travel"
    HOBBY = "hobby"
    FAMILY = "family"
    ANNIVERSARY = "anniversary"

class TemplateStatus(str, Enum):
    """템플릿 상태"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    FEATURED = "featured"
    ARCHIVED = "archived"
    REJECTED = "rejected"

class LicenseType(str, Enum):
    """라이선스 유형"""
    FREE = "free"
    PREMIUM = "premium"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

class DifficultyLevel(str, Enum):
    """난이도 레벨"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class SortBy(str, Enum):
    """정렬 기준"""
    CREATED_DESC = "created_desc"
    CREATED_ASC = "created_asc"
    UPDATED_DESC = "updated_desc"
    RATING_DESC = "rating_desc"
    USAGE_DESC = "usage_desc"
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"

# ===== 기본 모델 =====

class TemplateDimensions(BaseModel):
    """템플릿 치수"""
    width: int = Field(..., gt=0, description="너비 (픽셀)")
    height: int = Field(..., gt=0, description="높이 (픽셀)")

class ColorPalette(BaseModel):
    """색상 팔레트"""
    name: str = Field(..., description="팔레트 이름")
    colors: List[str] = Field(..., min_items=1, description="HEX 색상 코드 리스트")
    description: Optional[str] = Field(None, description="팔레트 설명")

class CustomizableElement(BaseModel):
    """커스터마이징 가능한 요소"""
    element_id: str = Field(..., description="요소 ID")
    element_type: str = Field(..., description="요소 타입 (text, image, shape)")
    customization_types: List[str] = Field(..., description="가능한 커스터마이징 타입")
    default_value: Optional[Any] = Field(None, description="기본값")
    constraints: Optional[Dict[str, Any]] = Field(None, description="제약조건")

class LicenseDetails(BaseModel):
    """라이선스 세부사항"""
    license_text: str = Field(..., description="라이선스 전문")
    commercial_usage: bool = Field(False, description="상업적 사용 허용")
    attribution_required: bool = Field(False, description="출처 표시 필요")
    redistribution_allowed: bool = Field(False, description="재배포 허용")
    usage_limit: Optional[int] = Field(None, description="사용 제한 횟수")
    expires_at: Optional[datetime] = Field(None, description="만료 시간")

# ===== 요청 모델 =====

class TemplateSearchRequest(BaseModel):
    """템플릿 검색 요청"""
    query: Optional[str] = Field(None, description="검색 키워드")
    category: Optional[TemplateCategory] = Field(None, description="카테고리 필터")
    subcategory: Optional[TemplateSubcategory] = Field(None, description="서브카테고리 필터")
    tags: Optional[List[str]] = Field(None, description="태그 필터")
    license_type: Optional[LicenseType] = Field(None, description="라이선스 타입 필터")
    difficulty_level: Optional[DifficultyLevel] = Field(None, description="난이도 필터")
    is_featured: Optional[bool] = Field(None, description="추천 템플릿 필터")
    min_rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="최소 평점")
    created_after: Optional[datetime] = Field(None, description="생성일 이후 필터")
    created_before: Optional[datetime] = Field(None, description="생성일 이전 필터")
    sort_by: SortBy = Field(SortBy.CREATED_DESC, description="정렬 기준")
    page: int = Field(1, ge=1, description="페이지 번호")
    page_size: int = Field(20, ge=1, le=100, description="페이지 크기")

class TemplateCreateRequest(BaseModel):
    """템플릿 생성 요청"""
    name: str = Field(..., min_length=1, max_length=255, description="템플릿 이름")
    description: Optional[str] = Field(None, description="템플릿 설명")
    keywords: Optional[List[str]] = Field(None, description="검색 키워드")
    category: TemplateCategory = Field(..., description="카테고리")
    subcategory: TemplateSubcategory = Field(..., description="서브카테고리")
    tags: Optional[List[str]] = Field(None, description="태그")
    canvas_data: Dict[str, Any] = Field(..., description="Canvas 데이터 (Konva JSON)")
    thumbnail_url: Optional[str] = Field(None, description="썸네일 URL")
    preview_images: Optional[List[str]] = Field(None, description="미리보기 이미지들")
    customizable_elements: Optional[List[CustomizableElement]] = Field(None, description="커스터마이징 요소")
    color_palettes: Optional[List[ColorPalette]] = Field(None, description="색상 팔레트")
    font_suggestions: Optional[List[str]] = Field(None, description="추천 폰트")
    dimensions: TemplateDimensions = Field(..., description="템플릿 치수")
    aspect_ratio: Optional[str] = Field(None, description="화면비")
    orientation: Optional[str] = Field(None, description="방향")
    difficulty_level: DifficultyLevel = Field(DifficultyLevel.BEGINNER, description="난이도")
    license_type: LicenseType = Field(LicenseType.FREE, description="라이선스 타입")
    license_details: Optional[LicenseDetails] = Field(None, description="라이선스 세부사항")
    is_public: bool = Field(True, description="공개 여부")

class TemplateUpdateRequest(BaseModel):
    """템플릿 수정 요청"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="템플릿 이름")
    description: Optional[str] = Field(None, description="템플릿 설명")
    keywords: Optional[List[str]] = Field(None, description="검색 키워드")
    category: Optional[TemplateCategory] = Field(None, description="카테고리")
    subcategory: Optional[TemplateSubcategory] = Field(None, description="서브카테고리")
    tags: Optional[List[str]] = Field(None, description="태그")
    canvas_data: Optional[Dict[str, Any]] = Field(None, description="Canvas 데이터")
    thumbnail_url: Optional[str] = Field(None, description="썸네일 URL")
    preview_images: Optional[List[str]] = Field(None, description="미리보기 이미지들")
    customizable_elements: Optional[List[CustomizableElement]] = Field(None, description="커스터마이징 요소")
    color_palettes: Optional[List[ColorPalette]] = Field(None, description="색상 팔레트")
    font_suggestions: Optional[List[str]] = Field(None, description="추천 폰트")
    dimensions: Optional[TemplateDimensions] = Field(None, description="템플릿 치수")
    aspect_ratio: Optional[str] = Field(None, description="화면비")
    orientation: Optional[str] = Field(None, description="방향")
    difficulty_level: Optional[DifficultyLevel] = Field(None, description="난이도")
    license_type: Optional[LicenseType] = Field(None, description="라이선스 타입")
    license_details: Optional[LicenseDetails] = Field(None, description="라이선스 세부사항")
    is_public: Optional[bool] = Field(None, description="공개 여부")

class TemplateApplyRequest(BaseModel):
    """템플릿 적용 요청"""
    canvas_id: UUID = Field(..., description="적용할 Canvas ID")
    customizations: Optional[Dict[str, Any]] = Field(None, description="커스터마이징 설정")
    preset_id: Optional[UUID] = Field(None, description="사용할 프리셋 ID")

class TemplateCustomizationRequest(BaseModel):
    """템플릿 커스터마이징 요청"""
    customizations: Dict[str, Any] = Field(..., description="커스터마이징 설정")
    
    @validator('customizations')
    def validate_customizations(cls, v):
        """커스터마이징 데이터 검증"""
        if not v:
            raise ValueError("커스터마이징 설정이 필요합니다")
        return v

# ===== 응답 모델 =====

class TemplateStats(BaseModel):
    """템플릿 통계"""
    view_count: int = Field(0, description="조회수")
    download_count: int = Field(0, description="다운로드 수")
    usage_count: int = Field(0, description="사용 횟수")
    average_rating: float = Field(0.0, description="평균 평점")
    rating_count: int = Field(0, description="평점 개수")

class TemplateCreator(BaseModel):
    """템플릿 작성자"""
    id: UUID = Field(..., description="사용자 ID")
    username: str = Field(..., description="사용자명")
    display_name: Optional[str] = Field(None, description="표시 이름")
    avatar_url: Optional[str] = Field(None, description="아바타 URL")
    is_verified: bool = Field(False, description="인증된 작성자")

class TemplateResponse(BaseModel):
    """템플릿 응답"""
    id: UUID = Field(..., description="템플릿 ID")
    name: str = Field(..., description="템플릿 이름")
    description: Optional[str] = Field(None, description="설명")
    keywords: Optional[List[str]] = Field(None, description="키워드")
    category: TemplateCategory = Field(..., description="카테고리")
    subcategory: TemplateSubcategory = Field(..., description="서브카테고리")
    tags: Optional[List[str]] = Field(None, description="태그")
    status: TemplateStatus = Field(..., description="상태")
    is_public: bool = Field(..., description="공개 여부")
    is_featured: bool = Field(..., description="추천 여부")
    thumbnail_url: Optional[str] = Field(None, description="썸네일 URL")
    preview_images: Optional[List[str]] = Field(None, description="미리보기 이미지들")
    dimensions: TemplateDimensions = Field(..., description="치수")
    aspect_ratio: Optional[str] = Field(None, description="화면비")
    orientation: Optional[str] = Field(None, description="방향")
    difficulty_level: DifficultyLevel = Field(..., description="난이도")
    license_type: LicenseType = Field(..., description="라이선스 타입")
    stats: TemplateStats = Field(..., description="통계")
    creator: TemplateCreator = Field(..., description="작성자")
    created_at: datetime = Field(..., description="생성 시간")
    updated_at: datetime = Field(..., description="수정 시간")
    published_at: Optional[datetime] = Field(None, description="게시 시간")

class TemplateDetailResponse(TemplateResponse):
    """템플릿 상세 응답"""
    canvas_data: Dict[str, Any] = Field(..., description="Canvas 데이터")
    customizable_elements: Optional[List[CustomizableElement]] = Field(None, description="커스터마이징 요소")
    color_palettes: Optional[List[ColorPalette]] = Field(None, description="색상 팔레트")
    font_suggestions: Optional[List[str]] = Field(None, description="추천 폰트")
    license_details: Optional[LicenseDetails] = Field(None, description="라이선스 세부사항")
    version: str = Field(..., description="버전")
    parent_template_id: Optional[UUID] = Field(None, description="기반 템플릿 ID")

class TemplateSearchResponse(BaseModel):
    """템플릿 검색 응답"""
    templates: List[TemplateResponse] = Field(..., description="템플릿 목록")
    total: int = Field(..., description="전체 개수")
    page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지 크기")
    total_pages: int = Field(..., description="전체 페이지 수")
    has_next: bool = Field(..., description="다음 페이지 존재 여부")
    has_prev: bool = Field(..., description="이전 페이지 존재 여부")

# ===== 리뷰 시스템 모델 =====

class TemplateReviewRequest(BaseModel):
    """템플릿 리뷰 작성 요청"""
    rating: int = Field(..., ge=1, le=5, description="평점 (1-5)")
    title: Optional[str] = Field(None, max_length=255, description="리뷰 제목")
    comment: Optional[str] = Field(None, description="리뷰 내용")
    is_recommended: bool = Field(False, description="추천 여부")
    review_categories: Optional[List[str]] = Field(None, description="리뷰 카테고리")

class TemplateReviewResponse(BaseModel):
    """템플릿 리뷰 응답"""
    id: UUID = Field(..., description="리뷰 ID")
    rating: int = Field(..., description="평점")
    title: Optional[str] = Field(None, description="제목")
    comment: Optional[str] = Field(None, description="내용")
    is_recommended: bool = Field(..., description="추천 여부")
    helpful_count: int = Field(..., description="도움됨 수")
    not_helpful_count: int = Field(..., description="도움안됨 수")
    review_categories: Optional[List[str]] = Field(None, description="카테고리")
    user_id: UUID = Field(..., description="작성자 ID")
    username: str = Field(..., description="작성자명")
    created_at: datetime = Field(..., description="작성 시간")
    updated_at: datetime = Field(..., description="수정 시간")

# ===== 컬렉션 시스템 모델 =====

class CollectionCreateRequest(BaseModel):
    """컬렉션 생성 요청"""
    name: str = Field(..., min_length=1, max_length=255, description="컬렉션 이름")
    description: Optional[str] = Field(None, description="설명")
    cover_image_url: Optional[str] = Field(None, description="커버 이미지 URL")
    is_public: bool = Field(False, description="공개 여부")

class CollectionUpdateRequest(BaseModel):
    """컬렉션 수정 요청"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="컬렉션 이름")
    description: Optional[str] = Field(None, description="설명")
    cover_image_url: Optional[str] = Field(None, description="커버 이미지 URL")
    is_public: Optional[bool] = Field(None, description="공개 여부")

class CollectionItemRequest(BaseModel):
    """컬렉션 항목 추가 요청"""
    template_id: UUID = Field(..., description="템플릿 ID")
    personal_notes: Optional[str] = Field(None, description="개인 메모")

class CollectionResponse(BaseModel):
    """컬렉션 응답"""
    id: UUID = Field(..., description="컬렉션 ID")
    name: str = Field(..., description="이름")
    description: Optional[str] = Field(None, description="설명")
    cover_image_url: Optional[str] = Field(None, description="커버 이미지")
    is_public: bool = Field(..., description="공개 여부")
    is_featured: bool = Field(..., description="추천 여부")
    template_count: int = Field(..., description="템플릿 개수")
    view_count: int = Field(..., description="조회수")
    follower_count: int = Field(..., description="팔로워 수")
    user_id: UUID = Field(..., description="소유자 ID")
    username: str = Field(..., description="소유자명")
    created_at: datetime = Field(..., description="생성 시간")
    updated_at: datetime = Field(..., description="수정 시간")

# ===== 커스터마이징 프리셋 모델 =====

class CustomizationPresetRequest(BaseModel):
    """커스터마이징 프리셋 요청"""
    name: str = Field(..., min_length=1, max_length=255, description="프리셋 이름")
    description: Optional[str] = Field(None, description="설명")
    customization_config: Dict[str, Any] = Field(..., description="커스터마이징 설정")

class CustomizationPresetResponse(BaseModel):
    """커스터마이징 프리셋 응답"""
    id: UUID = Field(..., description="프리셋 ID")
    name: str = Field(..., description="이름")
    description: Optional[str] = Field(None, description="설명")
    customization_config: Dict[str, Any] = Field(..., description="설정")
    preview_url: Optional[str] = Field(None, description="미리보기 URL")
    usage_count: int = Field(..., description="사용 횟수")
    is_official: bool = Field(..., description="공식 프리셋 여부")
    created_at: datetime = Field(..., description="생성 시간")

# ===== 분석 모델 =====

class TemplateAnalyticsResponse(BaseModel):
    """템플릿 분석 응답"""
    template_id: UUID = Field(..., description="템플릿 ID")
    period_type: str = Field(..., description="기간 타입")
    period_start: datetime = Field(..., description="기간 시작")
    period_end: datetime = Field(..., description="기간 종료")
    views: int = Field(..., description="조회수")
    downloads: int = Field(..., description="다운로드 수")
    applications: int = Field(..., description="적용 수")
    conversions: int = Field(..., description="전환 수")
    new_users: int = Field(..., description="신규 사용자")
    returning_users: int = Field(..., description="재방문 사용자")
    premium_users: int = Field(..., description="프리미엄 사용자")
    country_breakdown: Dict[str, int] = Field(..., description="국가별 분포")
    avg_load_time: Optional[float] = Field(None, description="평균 로딩 시간")
    avg_apply_time: Optional[float] = Field(None, description="평균 적용 시간")
    bounce_rate: Optional[float] = Field(None, description="이탈률")

# ===== 카테고리 관리 모델 =====

class CategoryResponse(BaseModel):
    """카테고리 응답"""
    id: UUID = Field(..., description="카테고리 ID")
    name: str = Field(..., description="이름")
    slug: str = Field(..., description="슬러그")
    description: Optional[str] = Field(None, description="설명")
    parent_id: Optional[UUID] = Field(None, description="부모 카테고리 ID")
    level: int = Field(..., description="계층 레벨")
    sort_order: int = Field(..., description="정렬 순서")
    icon_url: Optional[str] = Field(None, description="아이콘 URL")
    color_hex: Optional[str] = Field(None, description="색상")
    template_count: int = Field(..., description="템플릿 개수")
    is_active: bool = Field(..., description="활성 상태")

class TagResponse(BaseModel):
    """태그 응답"""
    id: UUID = Field(..., description="태그 ID")
    name: str = Field(..., description="이름")
    slug: str = Field(..., description="슬러그")
    description: Optional[str] = Field(None, description="설명")
    tag_type: Optional[str] = Field(None, description="태그 타입")
    color_hex: Optional[str] = Field(None, description="색상")
    usage_count: int = Field(..., description="사용 횟수")
    is_trending: bool = Field(..., description="트렌딩 여부")

print("Template System Pydantic Models v1.0 완성")
print("- 완전한 CRUD API 모델 정의")
print("- 검색/필터링/정렬 지원")
print("- 리뷰/컬렉션/분석 시스템")
print("- 커스터마이징 및 라이선스 관리")