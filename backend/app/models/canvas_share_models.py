"""
Canvas 공유 시스템 Pydantic 모델
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, ClassVar
from uuid import UUID
from pydantic import BaseModel, Field, validator, HttpUrl
from enum import Enum

from app.db.models.canvas_share import SharePermission, ShareVisibility, ShareDuration


# ===== 요청/응답 모델 =====

class CreateShareRequest(BaseModel):
    """공유 링크 생성 요청"""
    canvas_id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    permission: SharePermission = SharePermission.READ_ONLY
    visibility: ShareVisibility = ShareVisibility.PUBLIC
    duration: ShareDuration = ShareDuration.DAYS_7
    password: Optional[str] = None
    allowed_users: Optional[List[str]] = None
    max_views: Optional[int] = None


class UpdateShareRequest(BaseModel):
    """공유 링크 업데이트 요청"""
    title: Optional[str] = None
    description: Optional[str] = None
    permission: Optional[SharePermission] = None
    visibility: Optional[ShareVisibility] = None
    duration: Optional[ShareDuration] = None
    password: Optional[str] = None
    allowed_users: Optional[List[str]] = None
    max_views: Optional[int] = None
    is_active: Optional[bool] = None


class ShareResponse(BaseModel):
    """공유 링크 정보 응답"""
    id: UUID
    share_token: str
    canvas_id: UUID
    creator_id: str
    
    # 공유 설정
    title: Optional[str] = None
    description: Optional[str] = None
    permission: SharePermission
    visibility: ShareVisibility
    duration: ShareDuration
    
    # 통계
    view_count: int = 0
    download_count: int = 0
    
    # 메타데이터
    is_active: bool
    expires_at: Optional[datetime] = None
    og_image_url: Optional[str] = None
    preview_image_url: Optional[str] = None
    
    # 시간 정보
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime] = None
    
    # 계산된 필드
    share_url: str
    is_expired: bool = False
    is_view_limit_exceeded: bool = False
    can_access: bool = True

    class Config:
        from_attributes = True


class ShareAnalyticsResponse(BaseModel):
    """공유 분석 정보 응답"""
    share_id: UUID
    total_views: int
    total_downloads: int
    unique_visitors: int
    
    # 시간별 분석
    views_today: int
    views_this_week: int
    views_this_month: int
    
    # 지역별 분석
    top_countries: List[Dict[str, Any]]
    top_cities: List[Dict[str, Any]]
    
    # 디바이스별 분석
    device_breakdown: Dict[str, int]
    browser_breakdown: Dict[str, int]
    os_breakdown: Dict[str, int]
    
    # 트래픽 소스
    referrer_breakdown: Dict[str, int]
    
    # 시계열 데이터
    daily_views: List[Dict[str, Any]]
    hourly_views: List[Dict[str, Any]]

    class Config:
        from_attributes = True


class ShareAccessRequest(BaseModel):
    """공유 Canvas 접근 요청"""
    password: Optional[str] = None
    user_id: Optional[str] = None


class ShareAccessResponse(BaseModel):
    """공유 Canvas 접근 응답"""
    canvas_id: UUID
    canvas_data: Dict[str, Any]
    permission: SharePermission
    
    # Canvas 메타데이터
    title: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    last_updated_at: Optional[datetime] = None
    
    # 작성자 정보 (허용된 경우만)
    creator_info: Optional[Dict[str, Any]] = None
    
    # 렌더링 정보
    preview_image_url: Optional[str] = None
    layers_count: int = 0
    elements_count: int = 0
    
    class Config:
        from_attributes = True


class ShareReportRequest(BaseModel):
    """공유 신고 요청"""
    reason: str = Field(..., description="신고 사유")
    description: Optional[str] = None
    reporter_email: Optional[str] = None

    @validator('reason')
    def validate_reason(cls, v):
        allowed_reasons = [
            'inappropriate', 'copyright', 'spam', 'harassment', 
            'violence', 'illegal', 'misinformation', 'other'
        ]
        if v not in allowed_reasons:
            raise ValueError(f'Reason must be one of: {", ".join(allowed_reasons)}')
        return v


class ShareReportResponse(BaseModel):
    """공유 신고 응답"""
    id: UUID
    share_id: UUID
    reason: str
    description: Optional[str] = None
    status: str = "pending"
    created_at: datetime

    class Config:
        from_attributes = True


# ===== 소셜 미디어 모델 =====

class OpenGraphData(BaseModel):
    """Open Graph 메타데이터"""
    title: str
    description: Optional[str] = None
    image: Optional[HttpUrl] = None
    url: HttpUrl
    type: str = "website"
    site_name: str = "AI Portal"
    
    # 이미지 정보
    image_width: Optional[int] = 1200
    image_height: Optional[int] = 630
    image_type: Optional[str] = "image/png"


class TwitterCardData(BaseModel):
    """Twitter Card 메타데이터"""
    card: str = "summary_large_image"
    title: str
    description: Optional[str] = None
    image: Optional[HttpUrl] = None
    site: str = "@aiportal"
    creator: Optional[str] = None


class SocialShareData(BaseModel):
    """소셜 미디어 공유 데이터"""
    og: OpenGraphData
    twitter: TwitterCardData
    
    # 추가 플랫폼
    linkedin_title: Optional[str] = None
    linkedin_description: Optional[str] = None
    linkedin_image: Optional[HttpUrl] = None


# ===== Canvas 뷰어 모델 =====

class CanvasViewerConfig(BaseModel):
    """Canvas 뷰어 설정"""
    enable_zoom: bool = True
    enable_pan: bool = True
    enable_layer_toggle: bool = True
    enable_fullscreen: bool = True
    enable_download: bool = False  # 권한에 따라 설정
    enable_copy: bool = False      # 권한에 따라 설정
    enable_edit: bool = False      # 권한에 따라 설정
    
    # 뷰어 스타일
    background_color: str = "#ffffff"
    toolbar_position: str = "top"  # top, bottom, left, right
    show_metadata: bool = True
    show_creation_date: bool = True
    show_author_info: bool = False  # 권한에 따라 설정


class CanvasViewerData(BaseModel):
    """Canvas 뷰어 데이터"""
    canvas_id: UUID
    title: Optional[str] = None
    description: Optional[str] = None
    
    # Canvas 데이터
    stage_config: Dict[str, Any]
    layers: List[Dict[str, Any]]
    elements: List[Dict[str, Any]]
    
    # 뷰어 설정
    config: CanvasViewerConfig
    
    # 메타데이터
    created_at: datetime
    last_updated_at: Optional[datetime] = None
    author_name: Optional[str] = None
    
    class Config:
        from_attributes = True


# ===== 통계 및 분석 모델 =====

class ShareStatsDaily(BaseModel):
    """일별 공유 통계"""
    date: datetime
    views: int
    downloads: int
    unique_visitors: int


class ShareStatsHourly(BaseModel):
    """시간별 공유 통계"""
    hour: int
    views: int
    downloads: int


class ShareStatsGeo(BaseModel):
    """지역별 공유 통계"""
    country: str
    city: Optional[str] = None
    views: int
    percentage: float


class ShareStatsDevice(BaseModel):
    """디바이스별 공유 통계"""
    device_type: str  # desktop, mobile, tablet
    views: int
    percentage: float


class ShareStatsReferrer(BaseModel):
    """참조사이트별 공유 통계"""
    referrer: str
    views: int
    percentage: float


class ShareStatsBrowser(BaseModel):
    """브라우저별 공유 통계"""
    browser: str
    views: int
    percentage: float


class ShareStatsOS(BaseModel):
    """운영체제별 공유 통계"""
    os: str
    views: int
    percentage: float


# ===== 배치 작업 모델 =====

class ShareExportRequest(BaseModel):
    """공유 데이터 내보내기 요청"""
    share_ids: List[UUID]
    format: str = "json"  # json, csv, excel
    include_analytics: bool = True
    include_canvas_data: bool = False
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None


class ShareImportRequest(BaseModel):
    """공유 데이터 가져오기 요청"""
    data: List[Dict[str, Any]]
    format: str = "json"
    update_existing: bool = False
    validate_only: bool = False


# ===== 에러 응답 모델 =====

class ShareErrorResponse(BaseModel):
    """공유 관련 에러 응답"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    
    # 일반적인 에러 코드들
    SHARE_NOT_FOUND: ClassVar[str] = "SHARE_NOT_FOUND"
    SHARE_EXPIRED: ClassVar[str] = "SHARE_EXPIRED"
    SHARE_VIEW_LIMIT_EXCEEDED: ClassVar[str] = "SHARE_VIEW_LIMIT_EXCEEDED"
    SHARE_PERMISSION_DENIED: ClassVar[str] = "SHARE_PERMISSION_DENIED"
    SHARE_PASSWORD_REQUIRED: ClassVar[str] = "SHARE_PASSWORD_REQUIRED"
    SHARE_PASSWORD_INCORRECT: ClassVar[str] = "SHARE_PASSWORD_INCORRECT"
    SHARE_CANVAS_NOT_FOUND: ClassVar[str] = "SHARE_CANVAS_NOT_FOUND"
    SHARE_CREATION_FAILED: ClassVar[str] = "SHARE_CREATION_FAILED"
    SHARE_UPDATE_FAILED: ClassVar[str] = "SHARE_UPDATE_FAILED"