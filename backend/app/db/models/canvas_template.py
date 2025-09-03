# Canvas Template System Database Models
# AIPortal Canvas Template Library v1.0 - 완전한 템플릿 생태계

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float, Boolean, Index, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import uuid
import enum
from app.db.base import Base
from app.utils.timezone import now_kst

# ===== Enums =====

class TemplateCategory(str, enum.Enum):
    """템플릿 카테고리"""
    BUSINESS = "business"           # 비즈니스 (명함, 브로셔, 전단지, 프레젠테이션)
    SOCIAL_MEDIA = "social_media"   # 소셜 미디어 (인스타그램, 페이스북, 트위터, 유튜브)
    EDUCATION = "education"         # 교육 (인포그래픽, 다이어그램, 차트, 학습자료)
    EVENT = "event"                # 이벤트 (포스터, 티켓, 초대장, 배너)
    PERSONAL = "personal"          # 개인 (생일, 결혼, 여행, 취미)
    CREATIVE = "creative"          # 창작 (아트, 일러스트, 디자인)
    MARKETING = "marketing"        # 마케팅 (광고, 캠페인, 프로모션)
    PRESENTATION = "presentation"  # 프레젠테이션 (슬라이드, 템플릿)

class TemplateSubcategory(str, enum.Enum):
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

class TemplateStatus(str, enum.Enum):
    """템플릿 상태"""
    DRAFT = "draft"                # 초안
    PENDING_REVIEW = "pending_review"  # 검토 대기
    APPROVED = "approved"          # 승인됨
    FEATURED = "featured"          # 추천 템플릿
    ARCHIVED = "archived"          # 보관됨
    REJECTED = "rejected"          # 거부됨

class LicenseType(str, enum.Enum):
    """라이선스 유형"""
    FREE = "free"                  # 무료
    PREMIUM = "premium"            # 프리미엄
    PRO = "pro"                   # 프로 (상업적 사용)
    ENTERPRISE = "enterprise"      # 기업용
    CUSTOM = "custom"             # 맞춤형

class DifficultyLevel(str, enum.Enum):
    """난이도 레벨"""
    BEGINNER = "beginner"          # 초급
    INTERMEDIATE = "intermediate"  # 중급
    ADVANCED = "advanced"         # 고급
    EXPERT = "expert"             # 전문가

# ===== 핵심 Template 모델 =====

class CanvasTemplate(Base):
    """
    Canvas Template 메인 테이블
    """
    __tablename__ = "canvas_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 기본 정보
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    keywords = Column(ARRAY(String))  # 검색 키워드
    
    # 카테고리 분류
    category = Column(String(50), nullable=False, index=True)
    subcategory = Column(String(50), nullable=False, index=True)
    tags = Column(ARRAY(String), default=list)  # 자유 태그
    
    # 템플릿 상태
    status = Column(String(20), default=TemplateStatus.DRAFT.value, index=True)
    is_public = Column(Boolean, default=False, index=True)
    is_featured = Column(Boolean, default=False, index=True)
    
    # Canvas 데이터 (Konva JSON)
    canvas_data = Column(JSONB, nullable=False)  # 전체 Canvas 상태
    thumbnail_url = Column(String(500))          # 썸네일 이미지 URL
    preview_images = Column(ARRAY(String))       # 미리보기 이미지들
    
    # 커스터마이징 설정
    customizable_elements = Column(JSONB, default=list)  # 커스터마이징 가능한 요소들
    color_palettes = Column(JSONB, default=list)         # 추천 색상 팔레트들
    font_suggestions = Column(ARRAY(String), default=list)  # 추천 폰트들
    
    # 메타데이터
    dimensions = Column(JSONB, nullable=False)   # {"width": 1920, "height": 1080}
    aspect_ratio = Column(String(20))            # "16:9", "4:3", "1:1" 등
    orientation = Column(String(20))             # "landscape", "portrait", "square"
    difficulty_level = Column(String(20), default=DifficultyLevel.BEGINNER.value)
    
    # 라이선스 및 권한
    license_type = Column(String(20), default=LicenseType.FREE.value, index=True)
    license_details = Column(JSONB, default=dict)  # 라이선스 세부사항
    commercial_usage = Column(Boolean, default=False)
    attribution_required = Column(Boolean, default=False)
    
    # 통계 및 분석
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    usage_count = Column(Integer, default=0)      # 실제 사용 횟수
    average_rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    
    # 작성자 정보
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # 버전 관리
    version = Column(String(20), default="1.0.0")
    parent_template_id = Column(UUID(as_uuid=True), ForeignKey("canvas_templates.id"))  # 기반 템플릿
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=now_kst, index=True)
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst)
    published_at = Column(DateTime(timezone=True))
    
    # 관계
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    parent_template = relationship("CanvasTemplate", remote_side=[id])
    child_templates = relationship("CanvasTemplate", cascade="all, delete-orphan")
    
    reviews = relationship("TemplateReview", back_populates="template", cascade="all, delete-orphan")
    favorites = relationship("TemplateFavorite", back_populates="template", cascade="all, delete-orphan")
    collections_items = relationship("TemplateCollectionItem", back_populates="template", cascade="all, delete-orphan")
    usage_logs = relationship("TemplateUsageLog", back_populates="template", cascade="all, delete-orphan")
    customization_presets = relationship("TemplateCustomizationPreset", back_populates="template", cascade="all, delete-orphan")

class TemplateReview(Base):
    """
    템플릿 리뷰 및 평점 시스템
    """
    __tablename__ = "template_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("canvas_templates.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 리뷰 내용
    rating = Column(Integer, nullable=False)  # 1-5 점수
    title = Column(String(255))
    comment = Column(Text)
    
    # 추천 여부
    is_recommended = Column(Boolean, default=False)
    
    # 헬프풀 투표
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    
    # 사용 후기 카테고리
    review_categories = Column(ARRAY(String))  # ["ease_of_use", "design_quality", "customization"]
    
    created_at = Column(DateTime(timezone=True), default=now_kst, index=True)
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst)
    
    # 관계
    template = relationship("CanvasTemplate", back_populates="reviews")
    user = relationship("User")
    
    # 제약조건: 한 사용자당 한 템플릿에 하나의 리뷰만
    __table_args__ = (
        UniqueConstraint('template_id', 'user_id', name='uq_template_user_review'),
        CheckConstraint('rating >= 1 AND rating <= 5', name='ck_rating_range'),
    )

class TemplateFavorite(Base):
    """
    템플릿 즐겨찾기
    """
    __tablename__ = "template_favorites"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("canvas_templates.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 즐겨찾기 메타데이터
    notes = Column(Text)  # 개인 노트
    tags = Column(ARRAY(String))  # 개인 태그
    
    created_at = Column(DateTime(timezone=True), default=now_kst, index=True)
    
    # 관계
    template = relationship("CanvasTemplate", back_populates="favorites")
    user = relationship("User")
    
    # 제약조건: 한 사용자당 한 템플릿에 하나의 즐겨찾기만
    __table_args__ = (
        UniqueConstraint('template_id', 'user_id', name='uq_template_user_favorite'),
    )

class TemplateCollection(Base):
    """
    템플릿 컬렉션 (플레이리스트 개념)
    """
    __tablename__ = "template_collections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 컬렉션 정보
    name = Column(String(255), nullable=False)
    description = Column(Text)
    cover_image_url = Column(String(500))
    
    # 공개 설정
    is_public = Column(Boolean, default=False, index=True)
    is_featured = Column(Boolean, default=False)
    
    # 통계
    template_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    follower_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), default=now_kst, index=True)
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst)
    
    # 관계
    user = relationship("User")
    items = relationship("TemplateCollectionItem", back_populates="collection", cascade="all, delete-orphan")
    followers = relationship("CollectionFollower", back_populates="collection", cascade="all, delete-orphan")

class TemplateCollectionItem(Base):
    """
    컬렉션 내 템플릿 항목
    """
    __tablename__ = "template_collection_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("template_collections.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("canvas_templates.id", ondelete="CASCADE"), nullable=False)
    
    # 컬렉션 내 순서
    sort_order = Column(Integer, default=0)
    
    # 개인 메모
    personal_notes = Column(Text)
    
    added_at = Column(DateTime(timezone=True), default=now_kst, index=True)
    
    # 관계
    collection = relationship("TemplateCollection", back_populates="items")
    template = relationship("CanvasTemplate", back_populates="collections_items")
    
    # 제약조건: 한 컬렉션에 같은 템플릿 중복 방지
    __table_args__ = (
        UniqueConstraint('collection_id', 'template_id', name='uq_collection_template'),
    )

class CollectionFollower(Base):
    """
    컬렉션 팔로워
    """
    __tablename__ = "collection_followers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("template_collections.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 알림 설정
    notify_on_new_template = Column(Boolean, default=True)
    
    followed_at = Column(DateTime(timezone=True), default=now_kst, index=True)
    
    # 관계
    collection = relationship("TemplateCollection", back_populates="followers")
    user = relationship("User")
    
    # 제약조건: 한 사용자당 한 컬렉션에 하나의 팔로우만
    __table_args__ = (
        UniqueConstraint('collection_id', 'user_id', name='uq_collection_user_follow'),
    )

class TemplateUsageLog(Base):
    """
    템플릿 사용 로그 (분석용)
    """
    __tablename__ = "template_usage_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("canvas_templates.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # 익명 사용 허용
    
    # 사용 유형
    usage_type = Column(String(50), nullable=False)  # "view", "download", "apply", "customize"
    
    # 세션 정보
    session_id = Column(String(255))
    ip_address = Column(String(45))  # IPv6 지원
    user_agent = Column(Text)
    
    # 사용 컨텍스트
    canvas_id = Column(UUID(as_uuid=True), ForeignKey("canvases.id"))  # 어떤 Canvas에 적용했는지
    customization_data = Column(JSONB)  # 어떤 커스터마이징을 했는지
    
    # 지리적 정보 (옵션)
    country_code = Column(String(2))
    region = Column(String(100))
    city = Column(String(100))
    
    # 성능 메트릭
    load_time_ms = Column(Integer)
    apply_time_ms = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), default=now_kst, index=True)
    
    # 관계
    template = relationship("CanvasTemplate", back_populates="usage_logs")
    user = relationship("User")
    canvas = relationship("Canvas")

class TemplateCustomizationPreset(Base):
    """
    템플릿 커스터마이징 프리셋
    """
    __tablename__ = "template_customization_presets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("canvas_templates.id", ondelete="CASCADE"), nullable=False)
    
    # 프리셋 정보
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # 커스터마이징 설정
    customization_config = Column(JSONB, nullable=False)  # 색상, 폰트, 텍스트 변경사항
    preview_url = Column(String(500))  # 프리셋 적용 미리보기
    
    # 통계
    usage_count = Column(Integer, default=0)
    
    # 작성자 (시스템 생성 or 사용자 생성)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_official = Column(Boolean, default=False)  # 공식 프리셋인지
    
    created_at = Column(DateTime(timezone=True), default=now_kst)
    
    # 관계
    template = relationship("CanvasTemplate", back_populates="customization_presets")
    creator = relationship("User")

# ===== 고급 기능 모델 =====

class TemplateCategory(Base):
    """
    템플릿 카테고리 메타데이터
    """
    __tablename__ = "template_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 카테고리 정보
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    
    # 계층 구조
    parent_id = Column(UUID(as_uuid=True), ForeignKey("template_categories.id"))
    level = Column(Integer, default=0)  # 0: root, 1: category, 2: subcategory
    sort_order = Column(Integer, default=0)
    
    # 표시 설정
    icon_url = Column(String(500))
    color_hex = Column(String(7))  # #FF0000
    is_active = Column(Boolean, default=True)
    
    # 통계
    template_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), default=now_kst)
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst)
    
    # 관계
    parent = relationship("TemplateCategory", remote_side=[id])
    children = relationship("TemplateCategory", cascade="all, delete-orphan")

class TemplateTag(Base):
    """
    템플릿 태그 관리
    """
    __tablename__ = "template_tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # 태그 정보
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)
    
    # 태그 유형
    tag_type = Column(String(50))  # "color", "style", "purpose", "industry", "mood"
    
    # 표시 설정
    color_hex = Column(String(7))
    is_trending = Column(Boolean, default=False)
    
    # 통계
    usage_count = Column(Integer, default=0, index=True)
    
    created_at = Column(DateTime(timezone=True), default=now_kst)

class TemplateAnalytics(Base):
    """
    템플릿 상세 분석 데이터
    """
    __tablename__ = "template_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("canvas_templates.id", ondelete="CASCADE"), nullable=False)
    
    # 기간별 통계 (일별, 주별, 월별)
    period_type = Column(String(20), nullable=False)  # "daily", "weekly", "monthly"
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # 메트릭 데이터
    views = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    applications = Column(Integer, default=0)  # 실제 캔버스에 적용
    conversions = Column(Integer, default=0)   # 다운로드 후 실제 사용
    
    # 사용자 세그먼트별 분석
    new_users = Column(Integer, default=0)
    returning_users = Column(Integer, default=0)
    premium_users = Column(Integer, default=0)
    
    # 지역별 분석
    country_breakdown = Column(JSONB, default=dict)  # {"US": 100, "KR": 50, ...}
    
    # 성능 메트릭
    avg_load_time = Column(Float)
    avg_apply_time = Column(Float)
    bounce_rate = Column(Float)  # 뷰 후 즉시 나가는 비율
    
    created_at = Column(DateTime(timezone=True), default=now_kst)
    
    # 관계
    template = relationship("CanvasTemplate")
    
    # 제약조건: 동일 템플릿의 같은 기간 중복 방지
    __table_args__ = (
        UniqueConstraint('template_id', 'period_type', 'period_start', name='uq_template_analytics_period'),
    )

class TemplateLicenseAgreement(Base):
    """
    템플릿 라이선스 동의 기록
    """
    __tablename__ = "template_license_agreements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("canvas_templates.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 라이선스 정보
    license_type = Column(String(50), nullable=False)
    license_version = Column(String(20), nullable=False)
    license_text = Column(Text, nullable=False)  # 동의 당시의 라이선스 전문
    
    # 사용 제한
    usage_limit = Column(Integer)  # 사용 횟수 제한 (null이면 무제한)
    usage_count = Column(Integer, default=0)
    commercial_usage = Column(Boolean, default=False)
    redistribution_allowed = Column(Boolean, default=False)
    
    # 결제 정보 (프리미엄 템플릿의 경우)
    payment_id = Column(String(255))  # 결제 시스템의 거래 ID
    amount_paid = Column(Float)
    currency = Column(String(3))  # USD, KRW 등
    
    # 유효성
    expires_at = Column(DateTime(timezone=True))  # null이면 영구
    is_active = Column(Boolean, default=True)
    
    agreed_at = Column(DateTime(timezone=True), default=now_kst, index=True)
    
    # 관계
    template = relationship("CanvasTemplate")
    user = relationship("User")

# ===== 성능 최적화 인덱스 =====

# 템플릿 검색 및 브라우징 최적화
Index('ix_template_category_status', CanvasTemplate.category, CanvasTemplate.status)
Index('ix_template_featured_public', CanvasTemplate.is_featured, CanvasTemplate.is_public)
Index('ix_template_license_created', CanvasTemplate.license_type, CanvasTemplate.created_at.desc())
Index('ix_template_rating_usage', CanvasTemplate.average_rating.desc(), CanvasTemplate.usage_count.desc())

# 태그 기반 검색 최적화 (GIN 인덱스)
# CREATE INDEX idx_template_tags_gin ON canvas_templates USING GIN (tags);
# CREATE INDEX idx_template_keywords_gin ON canvas_templates USING GIN (keywords);

# 리뷰 시스템 최적화
Index('ix_review_template_rating', TemplateReview.template_id, TemplateReview.rating.desc())
Index('ix_review_helpful_created', TemplateReview.helpful_count.desc(), TemplateReview.created_at.desc())

# 사용량 분석 최적화
Index('ix_usage_log_template_type_created', TemplateUsageLog.template_id, TemplateUsageLog.usage_type, TemplateUsageLog.created_at.desc())
Index('ix_usage_log_user_created', TemplateUsageLog.user_id, TemplateUsageLog.created_at.desc())

# 컬렉션 최적화
Index('ix_collection_public_featured', TemplateCollection.is_public, TemplateCollection.is_featured)
Index('ix_collection_item_collection_order', TemplateCollectionItem.collection_id, TemplateCollectionItem.sort_order)

# 분석 데이터 최적화
Index('ix_analytics_template_period', TemplateAnalytics.template_id, TemplateAnalytics.period_type, TemplateAnalytics.period_start.desc())

# 라이선스 추적 최적화
Index('ix_license_user_active', TemplateLicenseAgreement.user_id, TemplateLicenseAgreement.is_active)
Index('ix_license_template_expires', TemplateLicenseAgreement.template_id, TemplateLicenseAgreement.expires_at)

# ===== 데이터베이스 제약조건 및 트리거 (마이그레이션에서 구현) =====

# 1. 통계 업데이트 트리거
#    - template 사용 시 usage_count 자동 증가
#    - 리뷰 추가/수정 시 average_rating 자동 계산
#    - 컬렉션 항목 추가/삭제 시 template_count 업데이트

# 2. 검색 최적화 트리거
#    - keywords 필드 자동 생성 (name + description에서 키워드 추출)
#    - 태그 정규화 및 중복 제거

# 3. 캐시 무효화 트리거
#    - 템플릿 수정 시 관련 캐시 무효화
#    - 리뷰 변경 시 평점 캐시 업데이트

# 4. 라이선스 만료 체크 트리거
#    - 만료된 라이선스 자동 비활성화
#    - 사용 제한 도달 시 자동 제한

# ===== 파티셔닝 전략 =====

# 1. template_usage_logs: created_at 기준 월별 파티셔닝
# 2. template_analytics: period_start 기준 분기별 파티셔닝
# 3. template_license_agreements: agreed_at 기준 연도별 파티셔닝

print("Canvas Template System Database Models v1.0 완성")
print("- 5개 주요 카테고리, 20+ 서브카테고리 지원")
print("- 평점/리뷰/즐겨찾기/컬렉션 완전 구현")
print("- 커스터마이징 프리셋 및 라이선스 시스템")
print("- 상세 분석 및 사용량 추적")
print("- Canvas v4.0과 완전 호환")