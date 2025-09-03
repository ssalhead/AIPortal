"""
Canvas 내보내기 시스템 모델
다양한 포맷과 옵션을 지원하는 전문가급 내보내기 시스템
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Literal, Any, Union
from enum import Enum
import uuid


class ExportFormat(str, Enum):
    """지원되는 내보내기 포맷"""
    PNG = "png"
    JPEG = "jpeg"
    SVG = "svg"
    PDF = "pdf"
    WEBP = "webp"


class ResolutionMultiplier(str, Enum):
    """해상도 배수"""
    X1 = "1x"
    X2 = "2x"
    X4 = "4x"


class CompressionLevel(str, Enum):
    """압축 레벨"""
    LOW = "low"      # 높은 품질, 큰 파일
    MEDIUM = "medium"  # 균형잡힌 품질과 크기
    HIGH = "high"    # 낮은 품질, 작은 파일


class SocialMediaPreset(str, Enum):
    """소셜 미디어 사전 설정"""
    INSTAGRAM_POST = "instagram_post"      # 1080x1080
    INSTAGRAM_STORY = "instagram_story"    # 1080x1920
    TWITTER_POST = "twitter_post"          # 1200x675
    FACEBOOK_POST = "facebook_post"        # 1200x630
    LINKEDIN_POST = "linkedin_post"        # 1200x627
    YOUTUBE_THUMBNAIL = "youtube_thumbnail"  # 1280x720
    PINTEREST_PIN = "pinterest_pin"        # 1000x1500
    CUSTOM = "custom"


class PDFTemplate(str, Enum):
    """PDF 템플릿 유형"""
    PORTFOLIO = "portfolio"        # 포트폴리오 레이아웃
    PRESENTATION = "presentation"  # 프레젠테이션 형식
    CATALOG = "catalog"           # 카탈로그 형식
    GALLERY = "gallery"           # 갤러리 형식
    DOCUMENT = "document"         # 문서 형식
    CUSTOM = "custom"


class CloudProvider(str, Enum):
    """클라우드 제공업체"""
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    AWS_S3 = "aws_s3"
    NONE = "none"


class ExportOptions(BaseModel):
    """기본 내보내기 옵션"""
    format: ExportFormat
    resolution_multiplier: ResolutionMultiplier = ResolutionMultiplier.X1
    transparent_background: bool = False
    compression_level: CompressionLevel = CompressionLevel.MEDIUM
    include_watermark: bool = False
    watermark_text: Optional[str] = None
    watermark_position: Literal["top-left", "top-right", "bottom-left", "bottom-right", "center"] = "bottom-right"
    
    # 사전 설정 또는 커스텀 크기
    social_preset: SocialMediaPreset = SocialMediaPreset.CUSTOM
    custom_width: Optional[int] = None
    custom_height: Optional[int] = None
    
    @validator('custom_width', 'custom_height')
    def validate_custom_dimensions(cls, v, values):
        if values.get('social_preset') == SocialMediaPreset.CUSTOM and v is None:
            raise ValueError("커스텀 크기 선택 시 가로/세로 크기를 지정해야 합니다")
        return v


class JPEGOptions(BaseModel):
    """JPEG 전용 옵션"""
    quality: int = Field(85, ge=1, le=100, description="JPEG 품질 (1-100)")
    progressive: bool = False
    optimize: bool = True


class PNGOptions(BaseModel):
    """PNG 전용 옵션"""
    compression_level: int = Field(6, ge=0, le=9, description="PNG 압축 레벨 (0-9)")
    interlaced: bool = False


class SVGOptions(BaseModel):
    """SVG 전용 옵션"""
    embed_fonts: bool = True
    embed_images: bool = True
    minimize: bool = False
    preserve_aspect_ratio: bool = True


class WebPOptions(BaseModel):
    """WebP 전용 옵션"""
    quality: int = Field(80, ge=1, le=100, description="WebP 품질 (1-100)")
    lossless: bool = False
    method: int = Field(4, ge=0, le=6, description="압축 방법 (0-6)")


class PDFMetadata(BaseModel):
    """PDF 메타데이터"""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = []
    creator: str = "AIPortal Canvas Export"
    producer: str = "AIPortal v4.0"


class PDFOptions(BaseModel):
    """PDF 전용 옵션"""
    template: PDFTemplate = PDFTemplate.GALLERY
    metadata: Optional[PDFMetadata] = None
    page_size: Literal["A4", "A3", "A5", "Letter", "Legal", "Custom"] = "A4"
    orientation: Literal["portrait", "landscape"] = "portrait"
    margin_mm: int = Field(20, ge=5, le=50, description="여백 (mm)")
    
    # 다중 페이지 옵션
    images_per_page: int = Field(1, ge=1, le=9, description="페이지당 이미지 수")
    add_page_numbers: bool = True
    add_table_of_contents: bool = False
    add_bookmarks: bool = True
    
    # 인쇄 최적화
    print_optimized: bool = False
    embed_fonts: bool = True
    compress_images: bool = True


class BatchExportOptions(BaseModel):
    """일괄 내보내기 옵션"""
    enabled: bool = False
    filename_pattern: str = Field(
        "canvas_{index}_{timestamp}", 
        description="파일명 패턴 (지원 변수: {index}, {timestamp}, {canvas_id}, {format})"
    )
    folder_structure: Literal["flat", "by_date", "by_type", "by_conversation"] = "flat"
    create_manifest: bool = True  # 내보내기 정보를 담은 manifest.json 생성


class CloudExportOptions(BaseModel):
    """클라우드 내보내기 옵션"""
    provider: CloudProvider = CloudProvider.NONE
    folder_path: Optional[str] = None
    generate_share_link: bool = False
    share_permissions: Literal["view", "edit", "comment"] = "view"
    
    # 제공업체별 설정
    google_drive_folder_id: Optional[str] = None
    dropbox_folder_path: Optional[str] = None
    s3_bucket_name: Optional[str] = None
    s3_object_prefix: Optional[str] = None


class ExportRequest(BaseModel):
    """내보내기 요청 모델"""
    canvas_id: str = Field(..., description="Canvas ID")
    user_id: str = Field(..., description="사용자 ID")
    conversation_id: Optional[str] = Field(None, description="대화 ID")
    
    # 기본 옵션
    export_options: ExportOptions
    
    # 포맷별 세부 옵션
    jpeg_options: Optional[JPEGOptions] = None
    png_options: Optional[PNGOptions] = None
    svg_options: Optional[SVGOptions] = None
    webp_options: Optional[WebPOptions] = None
    pdf_options: Optional[PDFOptions] = None
    
    # 고급 옵션
    batch_options: Optional[BatchExportOptions] = None
    cloud_options: Optional[CloudExportOptions] = None
    
    # 메타데이터
    export_name: Optional[str] = None
    export_description: Optional[str] = None
    tags: List[str] = []


class ExportProgress(BaseModel):
    """내보내기 진행 상황"""
    export_id: str
    status: Literal["pending", "processing", "uploading", "completed", "failed"] = "pending"
    progress_percentage: int = Field(0, ge=0, le=100)
    current_step: str = ""
    total_steps: int = 1
    completed_steps: int = 0
    
    # 결과 정보
    file_size: Optional[int] = None
    download_url: Optional[str] = None
    cloud_url: Optional[str] = None
    error_message: Optional[str] = None
    
    # 메타데이터
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_completion: Optional[str] = None


class ExportResult(BaseModel):
    """내보내기 결과"""
    export_id: str
    success: bool
    
    # 파일 정보
    file_path: Optional[str] = None
    file_size: int = 0
    file_format: ExportFormat
    download_url: Optional[str] = None
    
    # 클라우드 정보 (업로드된 경우)
    cloud_provider: Optional[CloudProvider] = None
    cloud_url: Optional[str] = None
    share_link: Optional[str] = None
    
    # 일괄 내보내기 정보
    batch_files: List[Dict[str, Any]] = []
    manifest_file: Optional[str] = None
    
    # 메타데이터
    export_options: ExportOptions
    processing_time: Optional[float] = None
    created_at: str
    expires_at: Optional[str] = None  # 다운로드 링크 만료 시간
    
    # 오류 정보
    error_message: Optional[str] = None
    warnings: List[str] = []


class BatchExportRequest(BaseModel):
    """시리즈 일괄 내보내기 요청"""
    conversation_id: str = Field(..., description="대화 ID")
    user_id: str = Field(..., description="사용자 ID")
    canvas_ids: List[str] = Field(..., min_items=1, description="Canvas ID 목록")
    
    # 내보내기 설정
    export_options: ExportOptions
    batch_options: BatchExportOptions
    cloud_options: Optional[CloudExportOptions] = None
    
    # 포맷별 옵션들
    jpeg_options: Optional[JPEGOptions] = None
    png_options: Optional[PNGOptions] = None
    pdf_options: Optional[PDFOptions] = None
    
    # PDF 다중 페이지 옵션 (시리즈를 하나의 PDF로)
    create_single_pdf: bool = False
    pdf_title: Optional[str] = None


class SocialMediaOptimization(BaseModel):
    """소셜 미디어 최적화 설정"""
    
    @staticmethod
    def get_preset_dimensions(preset: SocialMediaPreset) -> tuple[int, int]:
        """사전 설정에 따른 크기 반환"""
        dimensions = {
            SocialMediaPreset.INSTAGRAM_POST: (1080, 1080),
            SocialMediaPreset.INSTAGRAM_STORY: (1080, 1920),
            SocialMediaPreset.TWITTER_POST: (1200, 675),
            SocialMediaPreset.FACEBOOK_POST: (1200, 630),
            SocialMediaPreset.LINKEDIN_POST: (1200, 627),
            SocialMediaPreset.YOUTUBE_THUMBNAIL: (1280, 720),
            SocialMediaPreset.PINTEREST_PIN: (1000, 1500),
        }
        return dimensions.get(preset, (1080, 1080))
    
    @staticmethod
    def get_recommended_format(preset: SocialMediaPreset) -> ExportFormat:
        """사전 설정에 따른 권장 포맷"""
        if preset in [SocialMediaPreset.INSTAGRAM_POST, SocialMediaPreset.INSTAGRAM_STORY]:
            return ExportFormat.JPEG
        elif preset == SocialMediaPreset.PINTEREST_PIN:
            return ExportFormat.PNG
        else:
            return ExportFormat.WEBP


# 상수 정의
SUPPORTED_FORMATS = {
    ExportFormat.PNG: {
        "mime_type": "image/png",
        "extension": ".png",
        "supports_transparency": True,
        "max_dimensions": (32767, 32767)
    },
    ExportFormat.JPEG: {
        "mime_type": "image/jpeg",
        "extension": ".jpg",
        "supports_transparency": False,
        "max_dimensions": (65535, 65535)
    },
    ExportFormat.WEBP: {
        "mime_type": "image/webp",
        "extension": ".webp",
        "supports_transparency": True,
        "max_dimensions": (16383, 16383)
    },
    ExportFormat.SVG: {
        "mime_type": "image/svg+xml",
        "extension": ".svg",
        "supports_transparency": True,
        "max_dimensions": (None, None)  # 벡터 포맷
    },
    ExportFormat.PDF: {
        "mime_type": "application/pdf",
        "extension": ".pdf",
        "supports_transparency": True,
        "max_dimensions": (None, None)  # 문서 포맷
    }
}

MAX_EXPORT_SIZE_MB = 100  # 최대 내보내기 파일 크기
MAX_BATCH_SIZE = 50      # 최대 일괄 내보내기 개수
EXPORT_EXPIRY_HOURS = 24 # 다운로드 링크 유효 시간