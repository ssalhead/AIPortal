"""
단순화된 이미지 히스토리 데이터 모델
conversationId 기반 통합 이미지 관리 시스템
"""

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from app.db.base import Base


class ImageHistory(Base):
    """
    단순화된 이미지 히스토리 모델
    
    기존 복잡한 ImageGenerationSession + ImageGenerationVersion + GeneratedImage를
    하나의 통합 테이블로 단순화
    """
    __tablename__ = "image_history"
    
    # ======= 기본 식별자 =======
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # ======= 이미지 콘텐츠 정보 =======
    prompt = Column(Text, nullable=False, comment="사용자가 입력한 원본 프롬프트")
    image_urls = Column(JSON, nullable=False, comment="생성된 이미지 URL 배열 (보통 1개)")
    primary_image_url = Column(Text, nullable=False, comment="메인 표시용 이미지 URL")
    
    # ======= 생성 파라미터 =======
    style = Column(String(50), nullable=False, default="realistic", comment="이미지 스타일")
    size = Column(String(20), nullable=False, default="1024x1024", comment="이미지 크기")
    generation_params = Column(JSON, default=dict, comment="Imagen API 파라미터")
    
    # ======= 이미지 진화 관계 (단순화) =======
    parent_image_id = Column(UUID(as_uuid=True), ForeignKey("image_history.id", ondelete="SET NULL"), nullable=True)
    evolution_type = Column(String(30), nullable=True, comment="기반/변형/확장/reference_edit 등")
    
    # ======= Request-Based Canvas 시스템 =======
    canvas_id = Column(UUID(as_uuid=True), nullable=True, index=True, comment="Canvas 요청별 고유 ID")
    request_canvas_id = Column(UUID(as_uuid=True), nullable=True, index=True, comment="개별 요청별 Canvas 고유 ID")
    canvas_version = Column(Integer, default=1, comment="Canvas 내 버전 번호")
    edit_mode = Column(String(20), default="CREATE", comment="생성 모드 (CREATE/EDIT)")
    reference_image_id = Column(UUID(as_uuid=True), ForeignKey("image_history.id", ondelete="SET NULL"), nullable=True, comment="편집 시 참조 이미지 ID")
    
    # ======= 이미지 시리즈 시스템 =======
    series_id = Column(UUID(as_uuid=True), ForeignKey("image_series.id", ondelete="SET NULL"), nullable=True, index=True, comment="시리즈 그룹 ID")
    series_index = Column(Integer, nullable=True, comment="시리즈 내 순서 번호 (1부터 시작)")
    series_type = Column(String(30), nullable=True, comment="시리즈 타입 (webtoon, instagram, brand, educational, story)")
    series_metadata = Column(JSON, default=dict, comment="시리즈별 메타데이터")
    
    # ======= 보안 메타데이터 =======
    prompt_hash = Column(String(64), nullable=False, comment="중복 방지용 프롬프트 해시")
    content_filter_passed = Column(Boolean, default=False, comment="콘텐츠 필터 통과 여부")
    safety_score = Column(Float, default=0.0, comment="안전성 점수 (0.0-1.0)")
    
    # ======= 파일 정보 =======
    file_size_bytes = Column(Integer, default=0, comment="이미지 파일 크기")
    mime_type = Column(String(50), default="image/png", comment="이미지 MIME 타입")
    
    # ======= 상태 관리 =======
    status = Column(String(20), nullable=False, default="completed", comment="생성 상태")
    is_deleted = Column(Boolean, default=False, comment="소프트 삭제 여부")
    is_selected = Column(Boolean, default=False, comment="대화 내에서 선택된 이미지 여부")
    
    # ======= 타임스탬프 =======
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # ======= 관계 정의 =======
    parent_image = relationship("ImageHistory", remote_side=[id], backref="child_images", foreign_keys=[parent_image_id])
    reference_image = relationship("ImageHistory", remote_side=[id], backref="referenced_by_images", foreign_keys=[reference_image_id])
    conversation = relationship("Conversation", back_populates="image_history")
    user = relationship("User")
    
    # ======= 제약조건 =======
    __table_args__ = (
        CheckConstraint('safety_score >= 0.0 AND safety_score <= 1.0', name='valid_safety_score'),
        CheckConstraint('file_size_bytes >= 0', name='valid_file_size'),
        CheckConstraint("primary_image_url ~ '^(https?://|data:image/)'", name='valid_image_url'),
        CheckConstraint("status IN ('generating', 'completed', 'failed')", name='valid_status'),
        CheckConstraint("evolution_type IS NULL OR evolution_type IN ('based_on', 'variation', 'extension', 'modification', 'reference_edit')", name='valid_evolution_type'),
        CheckConstraint("edit_mode IN ('CREATE', 'EDIT')", name='valid_edit_mode'),
        CheckConstraint("canvas_version >= 1", name='valid_canvas_version'),
        CheckConstraint("series_type IS NULL OR series_type IN ('webtoon', 'instagram', 'brand', 'educational', 'story', 'custom')", name='valid_series_type'),
        CheckConstraint("series_index IS NULL OR series_index >= 1", name='valid_series_index'),
    )
    
    def __repr__(self) -> str:
        return f"<ImageHistory(id={self.id}, conversation_id={self.conversation_id}, prompt='{self.prompt[:50]}...')>"
    
    # ======= 비즈니스 로직 메서드 =======
    
    @property 
    def is_active(self) -> bool:
        """삭제되지 않은 활성 이미지인지 확인"""
        return not self.is_deleted and self.deleted_at is None
    
    @property
    def is_evolution(self) -> bool:
        """다른 이미지를 기반으로 생성된 진화 이미지인지 확인"""
        return self.parent_image_id is not None
    
    @property
    def is_canvas_edit(self) -> bool:
        """Canvas에서 편집된 이미지인지 확인"""
        return self.edit_mode == "EDIT" and self.reference_image_id is not None
    
    @property
    def is_canvas_create(self) -> bool:
        """Canvas에서 새로 생성된 이미지인지 확인"""
        return self.edit_mode == "CREATE"
    
    @property
    def is_series_member(self) -> bool:
        """시리즈의 멤버인지 확인"""
        return self.series_id is not None
    
    @property
    def is_series_first(self) -> bool:
        """시리즈의 첫 번째 이미지인지 확인"""
        return self.series_id is not None and self.series_index == 1
    
    @property
    def is_series_last(self) -> bool:
        """시리즈의 마지막 이미지인지 확인 (세션 정보 필요)"""
        # 구현 시 세션에서 시리즈 정보 확인 필요
        return False
    
    @property
    def generation_metadata(self) -> Dict[str, Any]:
        """생성 관련 메타데이터 반환"""
        return {
            "id": str(self.id),
            "prompt": self.prompt,
            "style": self.style,
            "size": self.size,
            "evolution_type": self.evolution_type,
            "parent_id": str(self.parent_image_id) if self.parent_image_id else None,
            "canvas_id": str(self.canvas_id) if self.canvas_id else None,
            "request_canvas_id": str(self.request_canvas_id) if self.request_canvas_id else None,
            "canvas_version": self.canvas_version,
            "edit_mode": self.edit_mode,
            "reference_image_id": str(self.reference_image_id) if self.reference_image_id else None,
            "series_id": str(self.series_id) if self.series_id else None,
            "series_index": self.series_index,
            "series_type": self.series_type,
            "series_metadata": self.series_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "safety_score": self.safety_score,
            "file_size": self.file_size_bytes
        }
    
    def mark_as_selected(self) -> None:
        """이 이미지를 선택된 상태로 설정 (트리거가 나머지 해제 처리)"""
        self.is_selected = True
        self.updated_at = func.now()
    
    def soft_delete(self) -> None:
        """소프트 삭제 처리"""
        self.is_deleted = True
        self.is_selected = False  # 선택 해제
        self.deleted_at = func.now()
        self.updated_at = func.now()
    
    def restore(self) -> None:
        """삭제된 이미지 복원"""
        self.is_deleted = False
        self.deleted_at = None
        self.updated_at = func.now()
    
    @classmethod
    def create_from_generation(
        cls,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        prompt: str,
        image_urls: List[str],
        style: str = "realistic",
        size: str = "1024x1024",
        parent_image_id: Optional[uuid.UUID] = None,
        evolution_type: Optional[str] = None,
        generation_params: Optional[Dict] = None,
        safety_score: float = 1.0,
        canvas_id: Optional[uuid.UUID] = None,
        request_canvas_id: Optional[uuid.UUID] = None,
        canvas_version: int = 1,
        edit_mode: str = "CREATE",
        reference_image_id: Optional[uuid.UUID] = None,
        series_id: Optional[uuid.UUID] = None,
        series_index: Optional[int] = None,
        series_type: Optional[str] = None,
        series_metadata: Optional[Dict] = None
    ) -> "ImageHistory":
        """이미지 생성 결과로부터 새 히스토리 엔트리 생성"""
        
        import hashlib
        prompt_hash = hashlib.sha256(f"{prompt}_{style}_{size}".encode()).hexdigest()
        
        return cls(
            conversation_id=conversation_id,
            user_id=user_id,
            prompt=prompt,
            image_urls=image_urls,
            primary_image_url=image_urls[0] if image_urls else "",
            style=style,
            size=size,
            parent_image_id=parent_image_id,
            evolution_type=evolution_type,
            prompt_hash=prompt_hash,
            generation_params=generation_params or {},
            safety_score=safety_score,
            canvas_id=canvas_id,
            request_canvas_id=request_canvas_id,
            canvas_version=canvas_version,
            edit_mode=edit_mode,
            reference_image_id=reference_image_id,
            series_id=series_id,
            series_index=series_index,
            series_type=series_type,
            series_metadata=series_metadata or {},
            content_filter_passed=True,
            status="completed",
            is_selected=True  # 새로 생성된 이미지는 기본 선택
        )