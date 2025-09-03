# Canvas v4.0 다중 이미지 편집 레이어 시스템 데이터베이스 모델
# 기존 Canvas 시스템과 호환되는 확장형 레이어 아키텍처

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float, Boolean, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, backref
import uuid
import enum
from app.db.base import Base
from app.utils.timezone import now_kst

# ============= 열거형 정의 =============

class LayerType(str, enum.Enum):
    """레이어 타입"""
    BACKGROUND = "background"
    IMAGE = "image"
    TEXT = "text"
    SHAPE = "shape"
    EFFECT = "effect"
    MASK = "mask"
    GROUP = "group"

class BlendMode(str, enum.Enum):
    """블렌드 모드"""
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"
    HARD_LIGHT = "hard_light"
    COLOR_DODGE = "color_dodge"
    COLOR_BURN = "color_burn"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"

class EditTool(str, enum.Enum):
    """편집 도구 타입"""
    SELECT = "select"
    MOVE = "move"
    ROTATE = "rotate"
    SCALE = "scale"
    CROP = "crop"
    BRUSH = "brush"
    ERASER = "eraser"
    TEXT = "text"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    LINE = "line"
    PEN = "pen"

# ============= 핵심 모델 =============

class LayerContainer(Base):
    """
    레이어 컨테이너 - Canvas v4.0와 연결된 다중 레이어 관리
    """
    __tablename__ = "layer_containers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canvas_id = Column(UUID(as_uuid=True), ForeignKey("canvases.id"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # 캔버스 설정
    canvas_config = Column(JSONB, nullable=False, default={
        'width': 1920,
        'height': 1080,
        'backgroundColor': '#ffffff',
        'dpi': 72
    })
    
    # 뷰포트 설정
    viewport_config = Column(JSONB, nullable=False, default={
        'zoom': 1.0,
        'panX': 0.0,
        'panY': 0.0,
        'rotation': 0.0
    })
    
    # 렌더링 설정
    render_settings = Column(JSONB, nullable=False, default={
        'quality': 'normal',
        'useWebGL': True,
        'enableCache': True,
        'maxCacheSize': 100 * 1024 * 1024,  # 100MB
        'enableAntiAlias': True,
        'enableBilinearFiltering': True,
        'maxTextureSize': 4096
    })
    
    # 레이어 순서 (zIndex 순서)
    layer_order = Column(ARRAY(UUID(as_uuid=True)), default=list)
    selected_layer_ids = Column(ARRAY(UUID(as_uuid=True)), default=list)
    
    # 버전 관리 (동시성 제어)
    version = Column(Integer, default=1, nullable=False)
    
    # 상태 플래그
    is_locked = Column(Boolean, default=False)
    locked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    
    # 메타데이터
    metadata_ = Column(JSONB, default=dict)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=now_kst, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst, nullable=False)
    
    # 관계 설정
    layers = relationship("CanvasLayer", back_populates="container", cascade="all, delete-orphan", order_by="CanvasLayer.z_index")
    canvas = relationship("Canvas", backref="layer_containers")
    
    # 인덱스
    __table_args__ = (
        Index('idx_layer_containers_canvas_id', 'canvas_id'),
        Index('idx_layer_containers_conversation_id', 'conversation_id'),
        Index('idx_layer_containers_updated_at', 'updated_at'),
    )


class CanvasLayer(Base):
    """
    캔버스 레이어 - 개별 레이어 정보 관리
    """
    __tablename__ = "canvas_layers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey("layer_containers.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    layer_type = Column(String(20), nullable=False)  # LayerType enum
    
    # 계층 구조
    parent_id = Column(UUID(as_uuid=True), ForeignKey("canvas_layers.id"), nullable=True)
    z_index = Column(Integer, nullable=False, default=0)
    
    # 변형 정보 (Transform)
    transform_data = Column(JSONB, nullable=False, default={
        'x': 0.0,
        'y': 0.0,
        'scaleX': 1.0,
        'scaleY': 1.0,
        'rotation': 0.0,
        'skewX': 0.0,
        'skewY': 0.0,
        'offsetX': 0.0,
        'offsetY': 0.0
    })
    
    # 경계 박스
    bounding_box = Column(JSONB, nullable=False, default={
        'x': 0.0,
        'y': 0.0,
        'width': 100.0,
        'height': 100.0
    })
    
    # 레이어 상태
    state_data = Column(JSONB, nullable=False, default={
        'visible': True,
        'locked': False,
        'selected': False,
        'collapsed': False,
        'opacity': 1.0,
        'blendMode': 'normal'
    })
    
    # 스타일 정보
    style_data = Column(JSONB, default={})
    
    # 마스크 정보
    mask_data = Column(JSONB, default={})
    
    # 레이어별 컨텐츠 데이터
    content_data = Column(JSONB, nullable=False, default={})
    
    # 메타데이터
    metadata_ = Column(JSONB, default={
        'source': 'user',  # 'user' | 'ai' | 'import'
        'tags': []
    })
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=now_kst, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst, nullable=False)
    
    # 관계 설정
    container = relationship("LayerContainer", back_populates="layers")
    parent = relationship("CanvasLayer", remote_side=[id], backref="children")
    
    # 인덱스
    __table_args__ = (
        Index('idx_canvas_layers_container_id', 'container_id'),
        Index('idx_canvas_layers_parent_id', 'parent_id'),
        Index('idx_canvas_layers_z_index', 'z_index'),
        Index('idx_canvas_layers_type', 'layer_type'),
        Index('idx_canvas_layers_updated_at', 'updated_at'),
    )


class LayerCache(Base):
    """
    레이어 캐시 시스템 - 성능 최적화용
    """
    __tablename__ = "layer_caches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    layer_id = Column(UUID(as_uuid=True), ForeignKey("canvas_layers.id"), nullable=False)
    
    cache_key = Column(String(64), nullable=False, unique=True)  # SHA256 해시
    cache_type = Column(String(20), nullable=False)  # 'image' | 'webgl' | 'vector'
    
    # 캐시 데이터 (실제 데이터는 외부 스토리지)
    storage_path = Column(String(500))  # S3/GCS 경로
    local_path = Column(String(500))    # 로컬 캐시 경로
    
    # 캐시 메타데이터
    size_bytes = Column(Integer, default=0)
    format_type = Column(String(10))  # 'png' | 'jpg' | 'webp' | 'json'
    compression_ratio = Column(Float, default=1.0)
    
    # 상태 관리
    is_dirty = Column(Boolean, default=False)
    hit_count = Column(Integer, default=0)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=now_kst, nullable=False)
    last_accessed = Column(DateTime(timezone=True), default=now_kst, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # 관계 설정
    layer = relationship("CanvasLayer", backref="caches")
    
    # 인덱스
    __table_args__ = (
        Index('idx_layer_caches_layer_id', 'layer_id'),
        Index('idx_layer_caches_cache_key', 'cache_key'),
        Index('idx_layer_caches_last_accessed', 'last_accessed'),
        Index('idx_layer_caches_expires_at', 'expires_at'),
    )


class EditOperation(Base):
    """
    편집 작업 히스토리 - Undo/Redo 지원
    """
    __tablename__ = "edit_operations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey("layer_containers.id"), nullable=False)
    
    operation_type = Column(String(50), nullable=False)  # 'transform' | 'style' | 'content' 등
    affected_layer_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False)
    
    # Before/After 상태 저장
    before_state = Column(JSONB, nullable=False)
    after_state = Column(JSONB, nullable=False)
    
    # 작업 정보
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(String(128))  # 브라우저 세션 ID
    tool_used = Column(String(20))    # EditTool enum
    
    # 메타데이터
    operation_metadata = Column(JSONB, default={})
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=now_kst, nullable=False)
    
    # 관계 설정
    container = relationship("LayerContainer", backref="edit_operations")
    
    # 인덱스
    __table_args__ = (
        Index('idx_edit_operations_container_id', 'container_id'),
        Index('idx_edit_operations_created_at', 'created_at'),
        Index('idx_edit_operations_user_id', 'user_id'),
    )


class LayerAsset(Base):
    """
    레이어 에셋 관리 - 이미지, 폰트 등 외부 리소스
    """
    __tablename__ = "layer_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    layer_id = Column(UUID(as_uuid=True), ForeignKey("canvas_layers.id"), nullable=False)
    
    asset_type = Column(String(20), nullable=False)  # 'image' | 'font' | 'texture'
    asset_url = Column(String(1000), nullable=False)  # 원본 URL
    
    # 이미지 전용 메타데이터
    natural_width = Column(Integer)
    natural_height = Column(Integer)
    file_format = Column(String(10))  # 'jpeg' | 'png' | 'webp' | 'svg'
    file_size = Column(Integer)  # bytes
    
    # 썸네일/변형 버전
    thumbnail_url = Column(String(1000))
    compressed_url = Column(String(1000))
    webp_url = Column(String(1000))
    
    # AI 생성 이미지 메타데이터
    ai_metadata = Column(JSONB, default={})  # 프롬프트, 모델, 스타일 등
    
    # 상태 관리
    upload_status = Column(String(20), default='uploading')  # 'uploading' | 'ready' | 'error'
    processing_status = Column(String(20), default='pending')  # 'pending' | 'processing' | 'complete'
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=now_kst, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst, nullable=False)
    
    # 관계 설정
    layer = relationship("CanvasLayer", backref="assets")
    
    # 인덱스
    __table_args__ = (
        Index('idx_layer_assets_layer_id', 'layer_id'),
        Index('idx_layer_assets_asset_type', 'asset_type'),
        Index('idx_layer_assets_upload_status', 'upload_status'),
    )


# ============= Canvas v4.0 호환성 확장 =============

# 기존 Canvas 모델에 레이어 시스템 연결
# 이는 실제 Canvas 모델 파일에 추가되어야 함

"""
# Canvas 모델에 추가될 관계:
class Canvas(Base):  # 기존 모델 확장
    # ... 기존 필드들 ...
    
    # 레이어 시스템 연결
    has_layer_system = Column(Boolean, default=False)  # 레이어 시스템 사용 여부
    
    # 기본 레이어 컨테이너 (1:1 관계)
    default_layer_container = relationship(
        "LayerContainer", 
        uselist=False,
        backref="canvas_owner",
        cascade="all, delete-orphan"
    )
"""