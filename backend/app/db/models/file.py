"""
파일 관리 데이터베이스 모델
"""

from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from datetime import datetime

from app.db.base import Base


class File(Base):
    """파일 메타데이터 모델"""
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(String(50), nullable=False, unique=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    original_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False, index=True)
    file_extension = Column(String(10), nullable=False)
    upload_path = Column(String(500), nullable=False)
    checksum = Column(String(32), nullable=False)  # MD5 해시
    status = Column(String(20), nullable=False, default='uploaded', index=True)
    description = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=True, default=list)
    processing_result = Column(JSONB, nullable=True)
    metadata_ = Column(JSONB, nullable=True, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_files_user_created', 'user_id', 'created_at'),
    )


class FileProcessingJob(Base):
    """파일 처리 작업 큐 모델"""
    __tablename__ = "file_processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String(50), nullable=False, unique=True, index=True)
    file_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    processing_type = Column(String(50), nullable=False)  # 'text_extraction', 'ocr', 'embedding', 'auto'
    status = Column(String(20), nullable=False, default='pending', index=True)  # 'pending', 'processing', 'completed', 'failed'
    progress = Column(Integer, nullable=False, default=0)  # 0-100
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class FileShare(Base):
    """파일 공유 및 권한 관리 모델"""
    __tablename__ = "file_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(String(50), nullable=False, index=True)
    owner_user_id = Column(String(50), nullable=False, index=True)
    shared_with_user_id = Column(String(50), nullable=False, index=True)
    permission = Column(String(20), nullable=False, default='read')  # 'read', 'write', 'admin'
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('file_id', 'shared_with_user_id', name='unique_file_share'),
    )


class FileVersion(Base):
    """파일 버전 관리 모델"""
    __tablename__ = "file_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(String(50), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    upload_path = Column(String(500), nullable=False)
    checksum = Column(String(32), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    created_by = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('file_id', 'version_number', name='unique_file_version'),
    )