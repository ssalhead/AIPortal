"""
Canvas 편집 히스토리 데이터베이스 모델

편집 작업 추적, 실행 취소/다시 실행, 스냅샷 관리를 위한 모델들
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, BYTEA
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.base_class import Base

class CanvasHistory(Base):
    """Canvas 히스토리 메인 테이블"""
    __tablename__ = "canvas_histories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    canvas_id = Column(String, ForeignKey("canvases.id"), nullable=False, unique=True)
    current_action_index = Column(Integer, default=-1)  # 현재 액션 인덱스
    current_branch_id = Column(String, default="main")   # 현재 브랜치 ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 관계
    canvas = relationship("Canvas", back_populates="history")
    actions = relationship("EditAction", back_populates="canvas_history", cascade="all, delete-orphan")
    snapshots = relationship("HistorySnapshot", back_populates="canvas_history", cascade="all, delete-orphan")
    branches = relationship("HistoryBranch", back_populates="canvas_history", cascade="all, delete-orphan")
    
    # 인덱스
    __table_args__ = (
        Index('ix_canvas_histories_canvas_id', 'canvas_id'),
        Index('ix_canvas_histories_updated_at', 'updated_at'),
    )


class EditAction(Base):
    """개별 편집 액션"""
    __tablename__ = "edit_actions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    canvas_id = Column(String, ForeignKey("canvas_histories.canvas_id"), nullable=False)
    
    # 액션 정보
    action_type = Column(String, nullable=False)        # ActionType enum 값
    category = Column(String, nullable=False)           # ActionCategory enum 값
    sequence_number = Column(Integer, nullable=False)   # 순서 번호
    branch_id = Column(String, default="main")          # 브랜치 ID
    
    # 요소 정보
    element_id = Column(String)         # 편집된 요소 ID
    element_type = Column(String)       # 요소 타입 (text, image, shape 등)
    
    # 상태 데이터
    before_state = Column(JSON)         # 편집 전 상태
    after_state = Column(JSON)          # 편집 후 상태
    metadata = Column(JSON)             # 추가 메타데이터
    
    # 액션 속성
    can_undo = Column(Boolean, default=True)
    can_redo = Column(Boolean, default=True)
    description = Column(Text)
    
    # 사용자 정보
    user_id = Column(String)
    session_id = Column(String)
    
    # 시간 정보
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    canvas_history = relationship("CanvasHistory", back_populates="actions")
    
    # 인덱스
    __table_args__ = (
        Index('ix_edit_actions_canvas_id', 'canvas_id'),
        Index('ix_edit_actions_timestamp', 'timestamp'),
        Index('ix_edit_actions_sequence', 'canvas_id', 'sequence_number'),
        Index('ix_edit_actions_type', 'action_type'),
        Index('ix_edit_actions_user', 'user_id'),
        Index('ix_edit_actions_session', 'session_id'),
        Index('ix_edit_actions_branch', 'branch_id'),
    )


class HistorySnapshot(Base):
    """Canvas 상태 스냅샷"""
    __tablename__ = "history_snapshots"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    canvas_id = Column(String, ForeignKey("canvas_histories.canvas_id"), nullable=False)
    
    # 스냅샷 정보
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # 상태 데이터 (압축된 JSON)
    state_data = Column(BYTEA)          # 압축된 Canvas 상태
    compressed_size = Column(Integer)    # 압축된 크기
    original_size = Column(Integer)      # 원본 크기
    
    # 연관된 액션
    action_id = Column(String, ForeignKey("edit_actions.id"))
    action_sequence = Column(Integer)    # 스냅샷 생성 시점의 액션 시퀀스
    
    # 메타데이터
    metadata = Column(JSON)
    tags = Column(JSON)                  # 태그 목록
    
    # 사용자 정보
    created_by = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    accessed_at = Column(DateTime(timezone=True))  # 마지막 접근 시간
    access_count = Column(Integer, default=0)      # 접근 횟수
    
    # 관계
    canvas_history = relationship("CanvasHistory", back_populates="snapshots")
    action = relationship("EditAction")
    
    # 인덱스
    __table_args__ = (
        Index('ix_history_snapshots_canvas_id', 'canvas_id'),
        Index('ix_history_snapshots_created_at', 'created_at'),
        Index('ix_history_snapshots_action_sequence', 'action_sequence'),
        Index('ix_history_snapshots_created_by', 'created_by'),
        Index('ix_history_snapshots_accessed_at', 'accessed_at'),
    )


class HistoryBranch(Base):
    """히스토리 브랜치"""
    __tablename__ = "history_branches"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    canvas_id = Column(String, ForeignKey("canvas_histories.canvas_id"), nullable=False)
    
    # 브랜치 정보
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # 브랜치 구조
    parent_branch_id = Column(String, ForeignKey("history_branches.id"))  # 부모 브랜치
    parent_action_id = Column(String, ForeignKey("edit_actions.id"))      # 분기 시작점
    
    # 상태 정보
    is_active = Column(Boolean, default=False)
    is_merged = Column(Boolean, default=False)
    merged_at = Column(DateTime(timezone=True))
    merged_by = Column(String)
    
    # 통계
    action_count = Column(Integer, default=0)
    
    # 사용자 정보
    created_by = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 관계
    canvas_history = relationship("CanvasHistory", back_populates="branches")
    parent_branch = relationship("HistoryBranch", remote_side=[id])
    child_branches = relationship("HistoryBranch")
    parent_action = relationship("EditAction")
    
    # 인덱스
    __table_args__ = (
        Index('ix_history_branches_canvas_id', 'canvas_id'),
        Index('ix_history_branches_parent', 'parent_branch_id'),
        Index('ix_history_branches_active', 'is_active'),
        Index('ix_history_branches_created_by', 'created_by'),
    )


class ActionBatch(Base):
    """배치 작업"""
    __tablename__ = "action_batches"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    canvas_id = Column(String, ForeignKey("canvas_histories.canvas_id"), nullable=False)
    
    # 배치 정보
    name = Column(String, nullable=False)
    description = Column(Text)
    operation_type = Column(String)      # 배치 작업 유형
    
    # 상태 정보
    status = Column(String, default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)       # 진행률 (0-100)
    
    # 액션 정보
    start_action_id = Column(String, ForeignKey("edit_actions.id"))
    end_action_id = Column(String, ForeignKey("edit_actions.id"))
    action_count = Column(Integer, default=0)
    
    # 결과 정보
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    error_details = Column(JSON)
    
    # 메타데이터
    parameters = Column(JSON)    # 배치 작업 파라미터
    results = Column(JSON)       # 작업 결과
    
    # 시간 정보
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    estimated_duration = Column(Integer)  # 예상 소요 시간 (초)
    
    # 사용자 정보
    created_by = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    start_action = relationship("EditAction", foreign_keys=[start_action_id])
    end_action = relationship("EditAction", foreign_keys=[end_action_id])
    
    # 인덱스
    __table_args__ = (
        Index('ix_action_batches_canvas_id', 'canvas_id'),
        Index('ix_action_batches_status', 'status'),
        Index('ix_action_batches_created_by', 'created_by'),
        Index('ix_action_batches_started_at', 'started_at'),
    )


class PerformanceMetrics(Base):
    """성능 메트릭"""
    __tablename__ = "performance_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    canvas_id = Column(String, ForeignKey("canvas_histories.canvas_id"), nullable=False)
    
    # 메트릭 타입
    metric_type = Column(String, nullable=False)  # action_time, memory_usage, cache_performance 등
    
    # 메트릭 데이터
    value = Column(JSON, nullable=False)
    
    # 컨텍스트 정보
    action_id = Column(String, ForeignKey("edit_actions.id"))
    session_id = Column(String)
    user_id = Column(String)
    
    # 환경 정보
    client_info = Column(JSON)    # 클라이언트 환경 정보
    server_info = Column(JSON)    # 서버 환경 정보
    
    # 시간 정보
    measured_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    action = relationship("EditAction")
    
    # 인덱스
    __table_args__ = (
        Index('ix_performance_metrics_canvas_id', 'canvas_id'),
        Index('ix_performance_metrics_type', 'metric_type'),
        Index('ix_performance_metrics_measured_at', 'measured_at'),
        Index('ix_performance_metrics_action_id', 'action_id'),
    )


class CollaborationEvent(Base):
    """협업 이벤트"""
    __tablename__ = "collaboration_events"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    canvas_id = Column(String, ForeignKey("canvas_histories.canvas_id"), nullable=False)
    
    # 이벤트 정보
    event_type = Column(String, nullable=False)  # join, leave, edit, comment, cursor_move 등
    
    # 액션 연관
    action_id = Column(String, ForeignKey("edit_actions.id"))
    
    # 이벤트 데이터
    data = Column(JSON)
    
    # 사용자 정보
    user_id = Column(String, nullable=False)
    session_id = Column(String)
    
    # 실시간 정보
    cursor_position = Column(JSON)    # 커서 위치
    selection_area = Column(JSON)     # 선택 영역
    
    # 시간 정보
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계
    action = relationship("EditAction")
    
    # 인덱스
    __table_args__ = (
        Index('ix_collaboration_events_canvas_id', 'canvas_id'),
        Index('ix_collaboration_events_user_id', 'user_id'),
        Index('ix_collaboration_events_timestamp', 'timestamp'),
        Index('ix_collaboration_events_type', 'event_type'),
    )


# Canvas 모델에 history 관계 추가 (별도 파일에서 import 시)
def add_history_relationship_to_canvas():
    """Canvas 모델에 히스토리 관계를 추가합니다."""
    try:
        from app.db.models.canvas import Canvas
        if not hasattr(Canvas, 'history'):
            Canvas.history = relationship("CanvasHistory", back_populates="canvas", uselist=False)
            print("✅ Canvas 모델에 히스토리 관계 추가 완료")
    except ImportError:
        print("⚠️ Canvas 모델을 찾을 수 없습니다.")