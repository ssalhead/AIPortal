# Canvas System 전용 데이터 모델
# AIPortal Canvas v5.0 - 통합 데이터 아키텍처

from datetime import datetime
from typing import Optional, Dict, List, Any, Union
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict
import json

# ===== Enum 정의 =====

class CanvasType(str, Enum):
    """Canvas 유형"""
    FREEFORM = "freeform"         # 자유형 캔버스
    STRUCTURED = "structured"     # 구조화된 캔버스  
    TEMPLATE = "template"         # 템플릿 기반
    COLLABORATIVE = "collaborative"  # 협업 캔버스

class KonvaNodeType(str, Enum):
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

class CanvasOperationType(str, Enum):
    """Canvas 작업 유형"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    RESIZE = "resize"
    ROTATE = "rotate"
    STYLE_CHANGE = "style_change"
    TEXT_EDIT = "text_edit"
    IMAGE_FILTER = "image_filter"

class SyncStatus(str, Enum):
    """동기화 상태"""
    IDLE = "idle"                 # 대기 중
    SYNCING = "syncing"          # 동기화 중
    CONFLICT = "conflict"         # 충돌 발생
    SUCCESS = "success"           # 성공
    FAILED = "failed"             # 실패

# ===== 핵심 데이터 모델 =====

class CanvasEventData(BaseModel):
    """Canvas 이벤트 데이터"""
    model_config = ConfigDict(
        extra="allow", 
        json_encoders={UUID: str, datetime: lambda dt: dt.isoformat()}
    )
    
    event_id: UUID = Field(default_factory=uuid4)
    canvas_id: UUID
    user_id: UUID
    event_type: CanvasOperationType
    
    # 대상 정보
    target_type: KonvaNodeType
    target_id: str
    
    # 변경 데이터
    new_data: Dict[str, Any] = Field(default_factory=dict)
    old_data: Optional[Dict[str, Any]] = None
    
    # 메타데이터
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    client_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # 동기화 정보
    version_number: int = 1
    idempotency_key: Optional[str] = None

class CanvasSyncState(BaseModel):
    """Canvas 동기화 상태"""
    model_config = ConfigDict(json_encoders={UUID: str, datetime: lambda dt: dt.isoformat()})
    
    canvas_id: UUID
    status: SyncStatus = SyncStatus.IDLE
    
    # 버전 정보
    local_version: int = 1
    server_version: int = 1
    last_sync_version: int = 1
    
    # 동기화 메타데이터
    last_sync_time: Optional[datetime] = None
    sync_in_progress: bool = False
    pending_events: List[CanvasEventData] = Field(default_factory=list)
    
    # 충돌 정보
    conflict_events: List[CanvasEventData] = Field(default_factory=list)
    resolution_strategy: Optional[str] = None

class KonvaNodeData(BaseModel):
    """Konva 노드 데이터"""
    model_config = ConfigDict(
        extra="allow", 
        json_encoders={UUID: str}
    )
    
    id: str
    node_type: KonvaNodeType
    class_name: str  # Konva 클래스명 (Text, Rect, Circle 등)
    
    # 계층 구조
    parent_id: Optional[str] = None
    layer_index: int = 0
    z_index: int = 0
    
    # 기본 변환 속성
    x: float = 0.0
    y: float = 0.0
    width: Optional[float] = None
    height: Optional[float] = None
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    skew_x: float = 0.0
    skew_y: float = 0.0
    
    # 시각적 속성
    opacity: float = 1.0
    visible: bool = True
    listening: bool = True
    
    # Konva 전용 속성 (완전 유연성)
    konva_attrs: Dict[str, Any] = Field(default_factory=dict)
    
    # 메타데이터
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class KonvaLayerData(BaseModel):
    """Konva 레이어 데이터"""
    model_config = ConfigDict(json_encoders={UUID: str})
    
    id: str
    name: str
    layer_index: int
    
    # Layer 속성
    visible: bool = True
    listening: bool = True
    opacity: float = 1.0
    
    # 변환 속성
    x: float = 0.0
    y: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    
    # 노드들
    nodes: List[KonvaNodeData] = Field(default_factory=list)
    
    # 메타데이터
    metadata: Dict[str, Any] = Field(default_factory=dict)

class KonvaStageData(BaseModel):
    """Konva Stage 데이터"""
    model_config = ConfigDict(json_encoders={UUID: str})
    
    width: int = 1920
    height: int = 1080
    scale_x: float = 1.0
    scale_y: float = 1.0
    x: float = 0.0
    y: float = 0.0
    
    # 레이어들
    layers: List[KonvaLayerData] = Field(default_factory=list)

class CanvasData(BaseModel):
    """통합 Canvas 데이터 모델"""
    model_config = ConfigDict(json_encoders={UUID: str, datetime: lambda dt: dt.isoformat()})
    
    # 기본 정보
    id: UUID = Field(default_factory=uuid4)
    workspace_id: UUID
    conversation_id: Optional[UUID] = None
    
    name: str
    description: Optional[str] = None
    canvas_type: CanvasType = CanvasType.FREEFORM
    
    # Konva Stage 데이터
    stage: KonvaStageData = Field(default_factory=KonvaStageData)
    
    # 버전 관리
    version_number: int = 1
    locked_by: Optional[UUID] = None
    locked_at: Optional[datetime] = None
    
    # 메타데이터
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 상태
    is_template: bool = False
    is_public: bool = False
    
    # 동기화 상태
    sync_state: CanvasSyncState = Field(init=False)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """초기화 후 동기화 상태 설정"""
        if not hasattr(self, 'sync_state'):
            self.sync_state = CanvasSyncState(canvas_id=self.id)

# ===== 요청/응답 모델 =====

class CreateCanvasRequest(BaseModel):
    """Canvas 생성 요청"""
    workspace_id: UUID
    conversation_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    canvas_type: CanvasType = CanvasType.FREEFORM
    template_id: Optional[UUID] = None

class UpdateCanvasRequest(BaseModel):
    """Canvas 업데이트 요청"""
    name: Optional[str] = None
    description: Optional[str] = None
    stage: Optional[KonvaStageData] = None
    metadata: Optional[Dict[str, Any]] = None
    expected_version: int  # 낙관적 잠금용

class CanvasOperationRequest(BaseModel):
    """Canvas 작업 요청"""
    canvas_id: UUID
    operation: CanvasEventData
    idempotency_key: str = Field(default_factory=lambda: str(uuid4()))

class CanvasSyncRequest(BaseModel):
    """Canvas 동기화 요청"""
    canvas_id: UUID
    local_version: int
    events_since_version: Optional[int] = None
    client_id: str

# ===== 응답 모델 =====

class CanvasOperationResult(BaseModel):
    """Canvas 작업 결과"""
    success: bool
    canvas_data: Optional[CanvasData] = None
    error_message: Optional[str] = None
    conflict_resolution: Optional[Dict[str, Any]] = None

class CanvasSyncResult(BaseModel):
    """Canvas 동기화 결과"""
    model_config = ConfigDict(json_encoders={UUID: str, datetime: lambda dt: dt.isoformat()})
    
    success: bool
    canvas_data: Optional[CanvasData] = None
    server_version: int
    
    # 동기화된 이벤트들
    applied_events: List[CanvasEventData] = Field(default_factory=list)
    conflicted_events: List[CanvasEventData] = Field(default_factory=list)
    
    # 메시지
    message: Optional[str] = None
    next_sync_version: int

class CanvasCollaborationStatus(BaseModel):
    """Canvas 협업 상태"""
    model_config = ConfigDict(json_encoders={UUID: str, datetime: lambda dt: dt.isoformat()})
    
    canvas_id: UUID
    active_users: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 실시간 상태
    concurrent_editors: int = 0
    last_activity: Optional[datetime] = None
    
    # 충돌 정보
    pending_conflicts: int = 0
    auto_resolved_conflicts: int = 0

# ===== 유틸리티 함수 =====

def generate_idempotency_key(canvas_id: UUID, operation_type: str, user_id: UUID) -> str:
    """멱등성 키 생성"""
    import hashlib
    key_data = f"{canvas_id}:{operation_type}:{user_id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    return hashlib.md5(key_data.encode()).hexdigest()

def validate_konva_node(node_data: Dict[str, Any]) -> bool:
    """Konva 노드 데이터 유효성 검증"""
    required_fields = ['id', 'node_type', 'class_name']
    return all(field in node_data for field in required_fields)

def sanitize_konva_attrs(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """Konva 속성 살균 처리 (보안)"""
    # 위험한 속성들 제거
    dangerous_attrs = ['innerHTML', 'outerHTML', 'javascript:', 'data:text/html']
    
    sanitized = {}
    for key, value in attrs.items():
        if isinstance(value, str):
            # XSS 방지
            if any(dangerous in value.lower() for dangerous in dangerous_attrs):
                continue
        
        sanitized[key] = value
    
    return sanitized

# ===== 예외 클래스 =====

class CanvasError(Exception):
    """Canvas 관련 기본 예외"""
    pass

class CanvasNotFoundError(CanvasError):
    """Canvas를 찾을 수 없음"""
    pass

class CanvasSyncError(CanvasError):
    """Canvas 동기화 오류"""
    pass

class CanvasConflictError(CanvasError):
    """Canvas 충돌 오류"""
    pass

class IdempotencyViolationError(CanvasError):
    """멱등성 위반 오류"""
    pass

class CanvasVersionMismatchError(CanvasError):
    """Canvas 버전 불일치"""
    def __init__(self, expected: int, actual: int):
        self.expected = expected
        self.actual = actual
        super().__init__(f"Version mismatch: expected {expected}, got {actual}")