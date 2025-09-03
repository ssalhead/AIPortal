# Canvas System Database Models
# AIPortal Canvas v5.0 - Konva 전용 최적화 스키마

from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum
from app.db.base import Base
from app.utils.timezone import now_kst

class CanvasType(str, enum.Enum):
    """Canvas 유형"""
    FREEFORM = "freeform"         # 자유형 캔버스
    STRUCTURED = "structured"     # 구조화된 캔버스  
    TEMPLATE = "template"         # 템플릿 기반
    COLLABORATIVE = "collaborative"  # 협업 캔버스

class KonvaNodeType(str, enum.Enum):
    """Konva 노드 타입"""
    STAGE = "stage"
    LAYER = "layer"
    GROUP = "group"
    RECT = "rect"
    CIRCLE = "circle"
    TEXT = "text"
    IMAGE = "image"
    LINE = "line"
    PATH = "path"
    SHAPE = "shape"

class PermissionLevel(str, enum.Enum):
    """권한 레벨"""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    COMMENTER = "commenter"

# ===== 핵심 Canvas 모델 =====

class Canvas(Base):
    """
    Canvas 메인 테이블 - Konva Stage와 1:1 매핑
    """
    __tablename__ = "canvases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    canvas_type = Column(String(20), default=CanvasType.FREEFORM.value)
    
    # Konva Stage 설정
    stage_config = Column(JSONB, nullable=False, default={
        'width': 1920,
        'height': 1080,
        'scale_x': 1.0,
        'scale_y': 1.0,
        'x': 0.0,
        'y': 0.0
    })
    
    # 버전 관리 및 락킹 (낙관적 잠금)
    version_number = Column(Integer, default=1, nullable=False)
    locked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    
    # 메타데이터 및 설정
    metadata_ = Column(JSONB, default=dict)
    
    # 상태 관리
    is_template = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=now_kst)
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst)
    
    # 관계 설정
    workspace = relationship("Workspace")
    conversation = relationship("Conversation")
    locker = relationship("User", foreign_keys=[locked_by])
    
    layers = relationship("KonvaLayer", back_populates="canvas", cascade="all, delete-orphan")
    events = relationship("CanvasEvent", back_populates="canvas", cascade="all, delete-orphan")
    versions = relationship("CanvasVersion", back_populates="canvas", cascade="all, delete-orphan")
    collaborators = relationship("CanvasCollaborator", back_populates="canvas", cascade="all, delete-orphan")
    cache_entries = relationship("CanvasCache", back_populates="canvas", cascade="all, delete-orphan")

class KonvaLayer(Base):
    """
    Konva Layer 테이블
    """
    __tablename__ = "konva_layers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canvas_id = Column(UUID(as_uuid=True), ForeignKey("canvases.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False)
    layer_index = Column(Integer, nullable=False, default=0)
    
    # Layer 기본 속성
    visible = Column(Boolean, default=True)
    listening = Column(Boolean, default=True)
    opacity = Column(Float, default=1.0)
    
    # 변환 속성
    x = Column(Float, default=0.0)
    y = Column(Float, default=0.0)
    scale_x = Column(Float, default=1.0)
    scale_y = Column(Float, default=1.0)
    rotation = Column(Float, default=0.0)
    
    # Konva 전용 속성 (완전 유연성)
    konva_attrs = Column(JSONB, default=dict)
    
    # 메타데이터
    metadata_ = Column(JSONB, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=now_kst)
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst)
    
    # 관계
    canvas = relationship("Canvas", back_populates="layers")
    nodes = relationship("KonvaNode", back_populates="layer", cascade="all, delete-orphan")

class KonvaNode(Base):
    """
    Konva Node 테이블 - 모든 Konva 객체 (텍스트, 이미지, 도형 등)
    """
    __tablename__ = "konva_nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    layer_id = Column(UUID(as_uuid=True), ForeignKey("konva_layers.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("konva_nodes.id"), nullable=True)  # 그룹화용
    
    # 노드 식별 정보
    node_type = Column(String(20), nullable=False)  # KonvaNodeType enum 값
    class_name = Column(String(100), nullable=False)  # Konva 클래스명 (Text, Rect, Circle 등)
    
    # 공통 변환 속성
    x = Column(Float, default=0.0)
    y = Column(Float, default=0.0)
    width = Column(Float)
    height = Column(Float)
    scale_x = Column(Float, default=1.0)
    scale_y = Column(Float, default=1.0)
    rotation = Column(Float, default=0.0)
    skew_x = Column(Float, default=0.0)
    skew_y = Column(Float, default=0.0)
    
    # 공통 시각 속성
    opacity = Column(Float, default=1.0)
    visible = Column(Boolean, default=True)
    listening = Column(Boolean, default=True)
    
    # z-index 및 순서
    z_index = Column(Integer, default=0)
    
    # Konva 특화 속성 (JSONB로 완전 유연성)
    konva_attrs = Column(JSONB, default=dict)  # fill, stroke, strokeWidth, text, fontSize 등
    
    # 메타데이터
    metadata_ = Column(JSONB, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=now_kst)
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst)
    
    # 관계
    layer = relationship("KonvaLayer", back_populates="nodes")
    parent = relationship("KonvaNode", remote_side=[id])
    children = relationship("KonvaNode", cascade="all, delete-orphan")

# ===== 이벤트 소싱 모델 =====

class CanvasEvent(Base):
    """
    Canvas 이벤트 스토어 (Event Sourcing)
    """
    __tablename__ = "canvas_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canvas_id = Column(UUID(as_uuid=True), ForeignKey("canvases.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 이벤트 메타데이터
    event_type = Column(String(50), nullable=False)  # create, update, delete, move, resize, rotate
    target_type = Column(String(50), nullable=False)  # stage, layer, node
    target_id = Column(String(255), nullable=False)   # 대상 객체 ID
    
    # 이벤트 페이로드
    event_data = Column(JSONB, nullable=False)       # 새로운 데이터
    previous_data = Column(JSONB)                     # 이전 상태 (undo용)
    
    # 버전 관리
    version_number = Column(Integer, nullable=False)
    
    # 멱등성 키
    idempotency_key = Column(String(255))
    
    # 협업 메타데이터
    client_id = Column(String(255))                   # 클라이언트 식별자
    session_id = Column(String(255))                  # 세션 식별자
    timestamp_client = Column(DateTime(timezone=True)) # 클라이언트 타임스탬프
    
    created_at = Column(DateTime(timezone=True), default=now_kst, index=True)
    
    # 관계
    canvas = relationship("Canvas", back_populates="events")
    user = relationship("User")

class CanvasVersion(Base):
    """
    Canvas 버전 스냅샷 (버전 관리)
    """
    __tablename__ = "canvas_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canvas_id = Column(UUID(as_uuid=True), ForeignKey("canvases.id", ondelete="CASCADE"), nullable=False)
    
    version_number = Column(Integer, nullable=False)
    version_name = Column(String(255))
    version_type = Column(String(20), default="auto")  # auto, manual, backup
    
    # 전체 Canvas 상태 스냅샷
    canvas_snapshot = Column(JSONB, nullable=False)  # 전체 Konva 상태 JSON
    diff_from_previous = Column(JSONB)               # 이전 버전과의 차이점
    
    # 압축 및 최적화
    is_compressed = Column(Boolean, default=False)
    compression_algo = Column(String(20))  # gzip, lz4 등
    
    # 메타데이터
    snapshot_size = Column(Integer)  # 바이트 크기
    event_count = Column(Integer, default=0)  # 포함된 이벤트 수
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_kst)
    
    # 관계
    canvas = relationship("Canvas", back_populates="versions")
    creator = relationship("User")

class CanvasCollaborator(Base):
    """
    Canvas 실시간 협업자
    """
    __tablename__ = "canvas_collaborators"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canvas_id = Column(UUID(as_uuid=True), ForeignKey("canvases.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 협업 상태
    is_online = Column(Boolean, default=True)
    is_editing = Column(Boolean, default=False)
    
    # 커서 위치 (실시간 협업)
    cursor_x = Column(Float)
    cursor_y = Column(Float)
    cursor_color = Column(String(7))  # HEX 색상
    
    # 권한
    permission_level = Column(String(20), default=PermissionLevel.VIEWER.value)
    
    # 세션 정보
    client_id = Column(String(255))
    websocket_session_id = Column(String(255))
    
    # 활동 추적
    last_activity = Column(DateTime(timezone=True), default=now_kst)
    join_time = Column(DateTime(timezone=True), default=now_kst)
    
    created_at = Column(DateTime(timezone=True), default=now_kst)
    
    # 관계
    canvas = relationship("Canvas", back_populates="collaborators")
    user = relationship("User")

# ===== 캐싱 및 최적화 모델 =====

class CanvasCache(Base):
    """
    Canvas L2 캐시 (PostgreSQL 기반)
    """
    __tablename__ = "canvas_cache"
    
    cache_key = Column(String(255), primary_key=True)
    canvas_id = Column(UUID(as_uuid=True), ForeignKey("canvases.id", ondelete="CASCADE"), nullable=True)
    
    # 캐시 데이터
    cache_type = Column(String(50), nullable=False)  # canvas, sync_state, events
    cache_data = Column(JSONB, nullable=False)
    
    # 압축 지원
    is_compressed = Column(Boolean, default=False)
    compression_algo = Column(String(20))
    
    # 메타데이터
    data_size = Column(Integer)  # 바이트 크기
    hit_count = Column(Integer, default=0)
    last_hit = Column(DateTime(timezone=True))
    
    # TTL 및 만료
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=now_kst)
    updated_at = Column(DateTime(timezone=True), default=now_kst, onupdate=now_kst)
    
    # 관계
    canvas = relationship("Canvas", back_populates="cache_entries")

class IdempotencyOperation(Base):
    """
    멱등성 작업 기록
    """
    __tablename__ = "idempotency_operations"
    
    idempotency_key = Column(String(255), primary_key=True)
    
    # 작업 메타데이터
    canvas_id = Column(UUID(as_uuid=True), ForeignKey("canvases.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    operation_type = Column(String(50), nullable=False)
    
    # 결과 데이터
    result_data = Column(JSONB, nullable=False)
    is_success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    
    # TTL
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=now_kst)
    
    # 관계
    canvas = relationship("Canvas")
    user = relationship("User")

# ===== 성능 최적화 인덱스 =====

# Canvas 조회 최적화
Index('ix_canvas_workspace_conversation', Canvas.workspace_id, Canvas.conversation_id)
Index('ix_canvas_type_created', Canvas.canvas_type, Canvas.created_at.desc())
Index('ix_canvas_updated_desc', Canvas.updated_at.desc())

# Layer 및 Node 조회 최적화
Index('ix_konva_layer_canvas_index', KonvaLayer.canvas_id, KonvaLayer.layer_index)
Index('ix_konva_node_layer_type', KonvaNode.layer_id, KonvaNode.node_type)
Index('ix_konva_node_parent_zindex', KonvaNode.parent_id, KonvaNode.z_index)

# 이벤트 스토어 최적화
Index('ix_canvas_event_canvas_created', CanvasEvent.canvas_id, CanvasEvent.created_at.desc())
Index('ix_canvas_event_version', CanvasEvent.canvas_id, CanvasEvent.version_number)
Index('ix_canvas_event_idempotency', CanvasEvent.idempotency_key)
Index('ix_canvas_event_target', CanvasEvent.target_type, CanvasEvent.target_id)

# 버전 관리 최적화
Index('ix_canvas_version_canvas_version', CanvasVersion.canvas_id, CanvasVersion.version_number.desc())

# 협업 최적화
Index('ix_canvas_collaborator_canvas_active', CanvasCollaborator.canvas_id, CanvasCollaborator.is_online)
Index('ix_canvas_collaborator_user_activity', CanvasCollaborator.user_id, CanvasCollaborator.last_activity.desc())

# 캐시 최적화
Index('ix_canvas_cache_type_expires', CanvasCache.cache_type, CanvasCache.expires_at)
Index('ix_canvas_cache_canvas_type', CanvasCache.canvas_id, CanvasCache.cache_type)

# 멱등성 최적화
Index('ix_idempotency_expires', IdempotencyOperation.expires_at)
Index('ix_idempotency_canvas_user', IdempotencyOperation.canvas_id, IdempotencyOperation.user_id)

# ===== JSONB GIN 인덱스 (PostgreSQL 전용) =====
# 실제 마이그레이션에서 SQL로 생성:
# CREATE INDEX idx_konva_node_attrs_gin ON konva_nodes USING GIN (konva_attrs);
# CREATE INDEX idx_canvas_metadata_gin ON canvases USING GIN (metadata_);
# CREATE INDEX idx_canvas_event_data_gin ON canvas_events USING GIN (event_data);
# CREATE INDEX idx_canvas_cache_data_gin ON canvas_cache USING GIN (cache_data);

# ===== 제약조건 및 트리거 =====
# 실제 마이그레이션에서 추가할 제약조건들:

# 1. Canvas 버전 번호 자동 증가 트리거
# 2. 이벤트 생성 시 버전 번호 동기화 트리거  
# 3. 캐시 TTL 자동 정리 트리거
# 4. 협업자 세션 타임아웃 트리거

# ===== 파티셔닝 전략 (대용량 처리용) =====
# 향후 확장을 위한 파티셔닝 고려사항:

# 1. canvas_events 테이블: created_at 기준 월별 파티셔닝
# 2. canvas_cache 테이블: cache_type 기준 해시 파티셔닝
# 3. idempotency_operations: expires_at 기준 시간 파티셔닝

# ===== 백업 및 아카이빙 =====
# 정책:
# 1. 활성 Canvas: 실시간 복제
# 2. 보관용 Canvas: 압축 후 아카이브 스토리지
# 3. 이벤트 로그: 3개월 후 콜드 스토리지
# 4. 캐시 데이터: 휘발성 (백업 불필요)