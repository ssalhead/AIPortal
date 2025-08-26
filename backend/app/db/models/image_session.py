"""
진화형 이미지 생성 세션을 위한 데이터베이스 모델
하나의 대화 = 하나의 Canvas = 하나의 이미지 테마 + 순차적 버전 개선
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class ImageGenerationSession(Base):
    """이미지 생성 세션 - 하나의 대화/Canvas에 대한 이미지 테마"""
    __tablename__ = "image_generation_sessions"
    
    # 기본 필드
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 대화/Canvas 연결
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    
    # 세션 정보
    theme = Column(String(255), nullable=False)          # "강아지", "수영장" 등 추출된 주제
    base_prompt = Column(Text, nullable=False)           # 최초 프롬프트
    evolution_history = Column(JSON, nullable=True)      # 프롬프트 변화 히스토리 (배열)
    
    # 현재 선택된 버전 (circular reference 문제로 인해 임시 제거)
    # selected_version_id = Column(UUID(as_uuid=True), ForeignKey("image_generation_versions.id"), nullable=True)
    
    # 상태
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # 관계 (임시 비활성화)
    # user = relationship("User", back_populates="image_sessions")
    # conversation = relationship("Conversation", back_populates="image_sessions")
    # versions = relationship("ImageGenerationVersion", back_populates="session", order_by="ImageGenerationVersion.version_number", foreign_keys="ImageGenerationVersion.session_id")
    
    def __repr__(self):
        return f"<ImageGenerationSession(id={self.id}, conversation_id={self.conversation_id}, theme='{self.theme}')>"
    
    def to_dict(self) -> dict:
        """모델을 딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "theme": self.theme,
            "base_prompt": self.base_prompt,
            "evolution_history": self.evolution_history or [],
            "selected_version_id": None,  # Temporarily removed due to circular reference
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "versions": [version.to_dict() for version in self.versions] if self.versions else []
        }


class ImageGenerationVersion(Base):
    """이미지 생성 버전 - 세션 내의 개별 이미지 버전"""
    __tablename__ = "image_generation_versions"
    
    # 기본 필드
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("image_generation_sessions.id"), nullable=False, index=True)
    
    # 버전 정보
    version_number = Column(Integer, nullable=False)      # 1, 2, 3, 4...
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey("image_generation_versions.id"), nullable=True)  # 브랜치 추적용
    
    # 생성 정보
    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True, default="")
    style = Column(String(50), nullable=False)
    size = Column(String(20), nullable=False)             # "1K_1:1", "2K_16:9" 등
    
    # 이미지 결과
    image_url = Column(String(500), nullable=True)        # 생성된 이미지 URL
    generated_image_id = Column(UUID(as_uuid=True), ForeignKey("generated_images.id"), nullable=True)  # 연결된 생성 이미지
    
    # 상태
    status = Column(String(20), default="generating")     # generating, completed, failed
    is_selected = Column(Boolean, default=False)          # 현재 선택된 버전인지
    is_deleted = Column(Boolean, default=False)
    
    # 추가 메타데이터
    generation_metadata = Column(JSON, nullable=True)     # 생성 관련 추가 정보
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # 관계 (임시 비활성화)
    # session = relationship("ImageGenerationSession", back_populates="versions")
    # generated_image = relationship("GeneratedImage", backref="versions")
    # parent_version = relationship("ImageGenerationVersion", remote_side=[id])
    # child_versions = relationship("ImageGenerationVersion", back_populates="parent_version")
    
    def __repr__(self):
        return f"<ImageGenerationVersion(id={self.id}, session_id={self.session_id}, version_number={self.version_number})>"
    
    def to_dict(self) -> dict:
        """모델을 딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "version_number": self.version_number,
            "parent_version_id": str(self.parent_version_id) if self.parent_version_id else None,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "style": self.style,
            "size": self.size,
            "image_url": self.image_url,
            "status": self.status,
            "is_selected": self.is_selected,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "generation_metadata": self.generation_metadata
        }