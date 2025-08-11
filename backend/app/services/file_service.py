"""
파일 관리 서비스
"""

from typing import List, Dict, Any, Optional, BinaryIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from pathlib import Path
import uuid
import hashlib
import shutil
import mimetypes
import logging
from datetime import datetime

from app.db.models.file import File, FileProcessingJob, FileShare, FileVersion
from app.core.config import settings

logger = logging.getLogger(__name__)


class FileService:
    """파일 관리 서비스"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.upload_dir = Path(settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else './uploads')
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_file_metadata(
        self,
        file_id: str,
        user_id: str,
        original_name: str,
        file_size: int,
        mime_type: str,
        file_extension: str,
        upload_path: str,
        checksum: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> File:
        """파일 메타데이터를 데이터베이스에 저장"""
        
        file_record = File(
            file_id=file_id,
            user_id=user_id,
            original_name=original_name,
            file_size=file_size,
            mime_type=mime_type,
            file_extension=file_extension,
            upload_path=upload_path,
            checksum=checksum,
            status='uploaded',
            description=description,
            tags=tags or [],
            metadata_={}
        )
        
        self.db.add(file_record)
        await self.db.commit()
        await self.db.refresh(file_record)
        
        logger.info(f"파일 메타데이터 저장 완료: {file_id} ({original_name})")
        return file_record
    
    async def get_user_files(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        file_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> tuple[List[File], int]:
        """사용자 파일 목록 조회"""
        
        query = select(File).where(File.user_id == user_id)
        
        # 필터 적용
        if file_type:
            query = query.where(File.file_extension == f'.{file_type}')
        if status:
            query = query.where(File.status == status)
        
        # 정렬 및 페이지네이션
        query = query.order_by(desc(File.created_at)).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        files = result.scalars().all()
        
        # 전체 개수 조회
        count_query = select(File).where(File.user_id == user_id)
        if file_type:
            count_query = count_query.where(File.file_extension == f'.{file_type}')
        if status:
            count_query = count_query.where(File.status == status)
        
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())
        
        return files, total
    
    async def get_file_by_id(self, file_id: str, user_id: str) -> Optional[File]:
        """파일 ID로 파일 조회 (소유자 또는 공유받은 사용자만)"""
        
        # 직접 소유한 파일 확인
        query = select(File).where(
            and_(File.file_id == file_id, File.user_id == user_id)
        )
        result = await self.db.execute(query)
        file_record = result.scalar_one_or_none()
        
        if file_record:
            return file_record
        
        # 공유받은 파일 확인
        shared_query = select(File).join(FileShare).where(
            and_(
                File.file_id == file_id,
                FileShare.shared_with_user_id == user_id,
                FileShare.expires_at.is_(None) | (FileShare.expires_at > datetime.utcnow())
            )
        )
        shared_result = await self.db.execute(shared_query)
        return shared_result.scalar_one_or_none()
    
    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """파일 삭제 (메타데이터 + 실제 파일)"""
        
        file_record = await self.get_file_by_id(file_id, user_id)
        if not file_record:
            return False
        
        # 소유자만 삭제 가능
        if file_record.user_id != user_id:
            return False
        
        try:
            # 실제 파일 삭제
            file_path = Path(file_record.upload_path)
            if file_path.exists():
                file_path.unlink()
            
            # 데이터베이스에서 삭제
            await self.db.delete(file_record)
            await self.db.commit()
            
            logger.info(f"파일 삭제 완료: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"파일 삭제 실패 - {file_id}: {e}")
            await self.db.rollback()
            return False
    
    async def update_file_status(
        self,
        file_id: str,
        status: str,
        processing_result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """파일 상태 업데이트"""
        
        query = select(File).where(File.file_id == file_id)
        result = await self.db.execute(query)
        file_record = result.scalar_one_or_none()
        
        if not file_record:
            return False
        
        file_record.status = status
        file_record.updated_at = datetime.utcnow()
        
        if processing_result:
            file_record.processing_result = processing_result
        
        await self.db.commit()
        return True
    
    async def create_processing_job(
        self,
        file_id: str,
        user_id: str,
        processing_type: str = 'auto'
    ) -> FileProcessingJob:
        """파일 처리 작업 생성"""
        
        job = FileProcessingJob(
            job_id=str(uuid.uuid4()),
            file_id=file_id,
            user_id=user_id,
            processing_type=processing_type,
            status='pending'
        )
        
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        return job
    
    async def get_processing_job(self, job_id: str) -> Optional[FileProcessingJob]:
        """처리 작업 조회"""
        
        query = select(FileProcessingJob).where(FileProcessingJob.job_id == job_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_processing_job(
        self,
        job_id: str,
        status: str,
        progress: int = None,
        result: Dict[str, Any] = None,
        error_message: str = None
    ) -> bool:
        """처리 작업 상태 업데이트"""
        
        job = await self.get_processing_job(job_id)
        if not job:
            return False
        
        job.status = status
        if progress is not None:
            job.progress = progress
        if result:
            job.result = result
        if error_message:
            job.error_message = error_message
        
        if status == 'processing' and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in ['completed', 'failed']:
            job.completed_at = datetime.utcnow()
        
        await self.db.commit()
        return True
    
    async def share_file(
        self,
        file_id: str,
        owner_user_id: str,
        shared_with_user_id: str,
        permission: str = 'read',
        expires_at: Optional[datetime] = None
    ) -> bool:
        """파일 공유"""
        
        # 파일 소유권 확인
        file_record = await self.get_file_by_id(file_id, owner_user_id)
        if not file_record or file_record.user_id != owner_user_id:
            return False
        
        # 기존 공유 확인
        existing_query = select(FileShare).where(
            and_(
                FileShare.file_id == file_id,
                FileShare.shared_with_user_id == shared_with_user_id
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing_share = existing_result.scalar_one_or_none()
        
        if existing_share:
            # 기존 공유 업데이트
            existing_share.permission = permission
            existing_share.expires_at = expires_at
        else:
            # 새 공유 생성
            share = FileShare(
                file_id=file_id,
                owner_user_id=owner_user_id,
                shared_with_user_id=shared_with_user_id,
                permission=permission,
                expires_at=expires_at
            )
            self.db.add(share)
        
        await self.db.commit()
        return True
    
    def calculate_file_checksum(self, file_content: BinaryIO) -> str:
        """파일 체크섬 계산"""
        hash_md5 = hashlib.md5()
        for chunk in iter(lambda: file_content.read(4096), b""):
            hash_md5.update(chunk)
        file_content.seek(0)  # 파일 포인터 리셋
        return hash_md5.hexdigest()
    
    async def get_shared_files(self, user_id: str) -> List[Dict[str, Any]]:
        """사용자가 공유받은 파일 목록"""
        
        query = select(File, FileShare).join(FileShare).where(
            and_(
                FileShare.shared_with_user_id == user_id,
                FileShare.expires_at.is_(None) | (FileShare.expires_at > datetime.utcnow())
            )
        ).order_by(desc(FileShare.created_at))
        
        result = await self.db.execute(query)
        shared_items = result.all()
        
        shared_files = []
        for file_record, share_record in shared_items:
            shared_files.append({
                'file': file_record,
                'share_info': {
                    'permission': share_record.permission,
                    'shared_by': share_record.owner_user_id,
                    'shared_at': share_record.created_at,
                    'expires_at': share_record.expires_at
                }
            })
        
        return shared_files