"""
Canvas 공유 시스템 데이터베이스 모델
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, ForeignKey, Enum as SQLEnum, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import uuid
from enum import Enum
from datetime import datetime, timedelta


class SharePermission(str, Enum):
    """공유 권한 타입"""
    READ_ONLY = "read_only"           # 읽기 전용
    COPY_ENABLED = "copy_enabled"     # 복사 가능
    EDIT_ENABLED = "edit_enabled"     # 편집 가능


class ShareVisibility(str, Enum):
    """공유 접근 권한"""
    PUBLIC = "public"                 # 누구나 접근 가능
    PRIVATE = "private"               # 링크 소유자만 접근 
    PASSWORD_PROTECTED = "password_protected"  # 비밀번호 필요
    USER_LIMITED = "user_limited"     # 특정 사용자만 접근


class ShareDuration(str, Enum):
    """공유 만료 시간"""
    HOURS_24 = "24_hours"            # 24시간
    DAYS_7 = "7_days"                # 7일
    DAYS_30 = "30_days"              # 30일
    UNLIMITED = "unlimited"          # 무제한


class CanvasShare(Base):
    """Canvas 공유 링크 정보"""
    __tablename__ = "canvas_shares"
    
    # 기본 정보
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    share_token = Column(String(32), unique=True, nullable=False, index=True)  # 공유 토큰
    canvas_id = Column(UUID(as_uuid=True), nullable=False)  # image_history의 canvas_id 필드와 매칭
    creator_id = Column(String(255), nullable=False)  # 공유 생성자
    
    # 공유 설정
    title = Column(String(500), nullable=True)  # 공유 제목
    description = Column(Text, nullable=True)   # 공유 설명
    permission = Column(SQLEnum(SharePermission), default=SharePermission.READ_ONLY, nullable=False)
    visibility = Column(SQLEnum(ShareVisibility), default=ShareVisibility.PUBLIC, nullable=False)
    duration = Column(SQLEnum(ShareDuration), default=ShareDuration.DAYS_7, nullable=False)
    
    # 보안 설정
    password_hash = Column(String(255), nullable=True)  # 비밀번호 해시 (비밀번호 보호 시)
    allowed_users = Column(JSON, nullable=True)  # 허용된 사용자 목록 (user_limited 시)
    max_views = Column(Integer, nullable=True)   # 최대 조회 수
    
    # 메타데이터
    is_active = Column(Boolean, default=True, nullable=False)
    view_count = Column(BigInteger, default=0, nullable=False)
    download_count = Column(BigInteger, default=0, nullable=False)
    
    # 만료 시간
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # 소셜 메타데이터
    og_image_url = Column(String(1000), nullable=True)  # Open Graph 이미지
    preview_image_url = Column(String(1000), nullable=True)  # 미리보기 이미지
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    
    # 관계
    analytics = relationship("CanvasShareAnalytics", back_populates="share", cascade="all, delete-orphan")
    
    def is_expired(self) -> bool:
        """공유 링크가 만료되었는지 확인"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_view_limit_exceeded(self) -> bool:
        """조회 수 제한이 초과되었는지 확인"""
        if not self.max_views:
            return False
        return self.view_count >= self.max_views
    
    def can_access(self) -> bool:
        """접근 가능한지 확인"""
        return (
            self.is_active and 
            not self.is_expired() and 
            not self.is_view_limit_exceeded()
        )
    
    @classmethod
    def calculate_expires_at(cls, duration: ShareDuration) -> datetime:
        """만료 시간 계산"""
        now = datetime.utcnow()
        if duration == ShareDuration.HOURS_24:
            return now + timedelta(hours=24)
        elif duration == ShareDuration.DAYS_7:
            return now + timedelta(days=7)
        elif duration == ShareDuration.DAYS_30:
            return now + timedelta(days=30)
        else:  # UNLIMITED
            return None


class CanvasShareAnalytics(Base):
    """Canvas 공유 분석 및 추적"""
    __tablename__ = "canvas_share_analytics"
    
    # 기본 정보
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    share_id = Column(UUID(as_uuid=True), ForeignKey("canvas_shares.id", ondelete="CASCADE"), nullable=False)
    
    # 방문자 정보
    visitor_ip = Column(String(45), nullable=True)  # IPv6 지원
    visitor_country = Column(String(10), nullable=True)  # 국가 코드
    visitor_city = Column(String(100), nullable=True)   # 도시
    visitor_user_agent = Column(Text, nullable=True)    # User Agent
    visitor_referrer = Column(String(1000), nullable=True)  # 참조 사이트
    
    # 방문 정보
    action_type = Column(String(50), nullable=False)  # view, download, copy 등
    session_id = Column(String(100), nullable=True)   # 세션 ID
    duration_seconds = Column(Integer, nullable=True) # 체류 시간
    
    # 디바이스 정보
    device_type = Column(String(50), nullable=True)   # desktop, mobile, tablet
    browser = Column(String(100), nullable=True)      # 브라우저
    os = Column(String(100), nullable=True)           # 운영체제
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # 관계
    share = relationship("CanvasShare", back_populates="analytics")


class CanvasShareReport(Base):
    """Canvas 공유 신고"""
    __tablename__ = "canvas_share_reports"
    
    # 기본 정보
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    share_id = Column(UUID(as_uuid=True), ForeignKey("canvas_shares.id", ondelete="CASCADE"), nullable=False)
    
    # 신고 정보
    reporter_ip = Column(String(45), nullable=True)
    reporter_email = Column(String(255), nullable=True)
    reason = Column(String(100), nullable=False)  # inappropriate, copyright, spam 등
    description = Column(Text, nullable=True)
    
    # 처리 정보
    status = Column(String(50), default="pending", nullable=False)  # pending, reviewed, resolved
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    resolution = Column(Text, nullable=True)
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)