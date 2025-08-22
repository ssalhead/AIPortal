"""
생성된 이미지 관리를 위한 데이터베이스 모델
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class GeneratedImage(Base):
    """생성된 AI 이미지 정보"""
    __tablename__ = "generated_images"
    
    # 기본 필드
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 이미지 생성 정보
    job_id = Column(String(255), unique=True, nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    enhanced_prompt = Column(Text, nullable=True)  # AI가 향상시킨 프롬프트
    
    # 이미지 메타데이터
    file_path = Column(String(500), nullable=False)  # 상대 경로
    file_url = Column(String(500), nullable=False)   # 접근 가능한 URL
    file_size = Column(Integer, nullable=False)      # 바이트 단위
    content_type = Column(String(100), default="image/png")
    
    # 생성 설정
    model_name = Column(String(100), default="imagen-4.0-generate-001")
    style = Column(String(50), nullable=False)
    sample_image_size = Column(String(10), nullable=False)  # 1K, 2K
    aspect_ratio = Column(String(10), nullable=False)       # 1:1, 16:9 등
    num_images = Column(Integer, default=1)
    
    # 품질 및 처리 정보
    generation_time_ms = Column(Integer, nullable=True)     # 생성 소요 시간
    status = Column(String(20), default="completed")        # processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    # 사용 추적
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    is_public = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    
    # 추가 메타데이터 (JSON)
    extra_metadata = Column(JSON, nullable=True)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # 관계
    user = relationship("User", back_populates="generated_images")
    
    def __repr__(self):
        return f"<GeneratedImage(id={self.id}, job_id={self.job_id}, prompt='{self.prompt[:50]}...')>"
    
    @property
    def is_expired(self) -> bool:
        """이미지가 만료되었는지 확인 (예: 30일 후)"""
        from datetime import datetime, timedelta
        if self.created_at:
            expiry_date = self.created_at + timedelta(days=30)
            return datetime.utcnow() > expiry_date
        return False
    
    def to_dict(self) -> dict:
        """모델을 딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "job_id": self.job_id,
            "prompt": self.prompt,
            "file_url": self.file_url,
            "file_size": self.file_size,
            "model_name": self.model_name,
            "style": self.style,
            "sample_image_size": self.sample_image_size,
            "aspect_ratio": self.aspect_ratio,
            "status": self.status,
            "view_count": self.view_count,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "extra_metadata": self.extra_metadata
        }