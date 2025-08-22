"""
파일 업로드 및 처리 API
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
import os
import shutil
from pathlib import Path
import mimetypes
import hashlib
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.db.models import File as FileModel
from app.db.session import AsyncSessionLocal
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi.responses import FileResponse, StreamingResponse
import aiofiles

router = APIRouter()

# 지원하는 파일 형식
SUPPORTED_MIME_TYPES = {
    'text/plain': '.txt',
    'application/pdf': '.pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.ms-excel': '.xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    'text/csv': '.csv',
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'application/json': '.json',
    'text/markdown': '.md',
    'text/html': '.html',
    'application/zip': '.zip',
    'application/x-python': '.py',
    'text/x-python': '.py',
    'application/javascript': '.js',
    'text/javascript': '.js',
    'application/typescript': '.ts',
    'text/x-typescript': '.ts',
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES_PER_REQUEST = 10


class FileUploadResponse(BaseModel):
    """파일 업로드 응답 모델"""
    file_id: str
    original_name: str
    file_size: int
    mime_type: str
    file_extension: str
    upload_path: str
    status: str  # 'uploaded', 'processing', 'completed', 'error'
    checksum: str
    created_at: str


class FileMetadata(BaseModel):
    """파일 메타데이터 모델"""
    file_id: str
    original_name: str
    file_size: int
    mime_type: str
    file_extension: str
    upload_path: str
    status: str
    checksum: str
    processing_result: Optional[Dict[str, Any]] = None
    user_id: str
    created_at: str
    updated_at: str


class FileListResponse(BaseModel):
    """파일 목록 응답 모델"""
    files: List[FileMetadata]
    total: int
    skip: int
    limit: int


def get_file_checksum(file_path: str) -> str:
    """파일의 MD5 체크섬 계산"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_upload_directory() -> Path:
    """업로드 디렉토리 경로 반환"""
    upload_dir = Path(settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else './uploads')
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def validate_file(file: UploadFile) -> tuple[bool, str]:
    """파일 유효성 검증"""
    
    # 파일 크기 검증
    if file.size and file.size > MAX_FILE_SIZE:
        return False, f"파일 크기가 너무 큽니다. 최대 {MAX_FILE_SIZE // (1024*1024)}MB까지 허용됩니다."
    
    # MIME 타입 검증
    if file.content_type not in SUPPORTED_MIME_TYPES:
        supported_types = ', '.join(SUPPORTED_MIME_TYPES.values())
        return False, f"지원하지 않는 파일 형식입니다. 지원 형식: {supported_types}"
    
    # 파일명 검증
    if not file.filename or len(file.filename) > 255:
        return False, "올바르지 않은 파일명입니다."
    
    return True, "유효한 파일입니다."


@router.post("/upload", response_model=List[FileUploadResponse])
async def upload_files(
    files: List[UploadFile] = File(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # 쉼표로 구분된 태그
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> List[FileUploadResponse]:
    """
    파일 업로드 (다중 파일 지원)
    
    Args:
        files: 업로드할 파일들
        description: 파일 설명 (선택사항)
        tags: 쉼표로 구분된 태그 (선택사항)
        current_user: 현재 사용자 정보
        
    Returns:
        업로드된 파일들의 정보
    """
    
    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"한 번에 최대 {MAX_FILES_PER_REQUEST}개 파일까지 업로드 가능합니다."
        )
    
    upload_dir = get_upload_directory()
    user_id = current_user["id"]
    uploaded_files = []
    
    # 사용자별 하위 디렉토리 생성
    user_upload_dir = upload_dir / user_id
    user_upload_dir.mkdir(exist_ok=True)
    
    for file in files:
        try:
            # 파일 유효성 검증
            is_valid, message = validate_file(file)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"파일 '{file.filename}': {message}"
                )
            
            # 고유한 파일 ID 생성
            file_id = str(uuid.uuid4())
            file_extension = SUPPORTED_MIME_TYPES[file.content_type]
            
            # 파일 저장 경로 생성
            safe_filename = f"{file_id}{file_extension}"
            file_path = user_upload_dir / safe_filename
            
            # 파일 저장
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # 체크섬 계산
            checksum = get_file_checksum(str(file_path))
            
            # 파일 정보 생성
            file_info = FileUploadResponse(
                file_id=file_id,
                original_name=file.filename,
                file_size=file_path.stat().st_size,
                mime_type=file.content_type,
                file_extension=file_extension,
                upload_path=str(file_path),
                status='uploaded',
                checksum=checksum,
                created_at=datetime.utcnow().isoformat()
            )
            
            uploaded_files.append(file_info)
            
            # 메타데이터를 PostgreSQL에 저장
            async with AsyncSessionLocal() as session:
                file_record = FileModel(
                    file_id=file_id,
                    user_id=user_id,
                    original_name=file.filename,
                    file_size=file_path.stat().st_size,
                    mime_type=file.content_type or 'application/octet-stream',
                    file_extension=file_extension,
                    upload_path=str(file_path),
                    checksum=checksum,
                    status='uploaded',
                    description=description,
                    tags=tags.split(',') if tags else [],
                    metadata_={'original_filename': file.filename, 'upload_time': datetime.utcnow().isoformat()}
                )
                session.add(file_record)
                await session.commit()
                logger.info(f"파일 메타데이터 저장 완료: {file_id}")
            
            logger.info(f"파일 업로드 성공: {file.filename} -> {file_id}")
            
        except HTTPException:
            # 이미 HTTPException인 경우 재발생
            raise
        except Exception as e:
            logger.error(f"파일 업로드 실패 - {file.filename}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"파일 '{file.filename}' 업로드 중 오류가 발생했습니다."
            )
    
    return uploaded_files


@router.get("/", response_model=FileListResponse)
async def list_files(
    skip: int = 0,
    limit: int = 50,
    file_type: Optional[str] = None,  # 파일 확장자 필터
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> FileListResponse:
    """
    사용자 파일 목록 조회
    
    Args:
        skip: 건너뛸 항목 수
        limit: 조회할 항목 수
        file_type: 파일 타입 필터 (예: 'pdf', 'image')
        current_user: 현재 사용자 정보
        
    Returns:
        파일 목록
    """
    
    # PostgreSQL에서 사용자 파일 목록 조회
    try:
        async with AsyncSessionLocal() as session:
            # 기본 쿼리 구성
            query = select(FileModel).where(
                FileModel.user_id == (current_user.id if hasattr(current_user, 'id') else 'unknown')
            )
            
            # 파일 타입 필터 적용
            if file_type:
                query = query.where(FileModel.file_extension.like(f'%{file_type}%'))
            
            # 정렬 및 페이지네이션
            query = query.order_by(FileModel.created_at.desc()).offset(skip).limit(limit)
            
            result = await session.execute(query)
            files = result.scalars().all()
            
            # 전체 개수 조회
            count_query = select(func.count(FileModel.id)).where(
                FileModel.user_id == (current_user.id if hasattr(current_user, 'id') else 'unknown')
            )
            if file_type:
                count_query = count_query.where(FileModel.file_extension.like(f'%{file_type}%'))
            
            count_result = await session.execute(count_query)
            total_count = count_result.scalar()
            
            # 응답 생성
            file_list = []
            for file_record in files:
                file_list.append(FileMetadata(
                    file_id=file_record.file_id,
                    original_name=file_record.original_name,
                    file_size=file_record.file_size,
                    mime_type=file_record.mime_type,
                    file_extension=file_record.file_extension,
                    upload_path=file_record.upload_path,
                    status=file_record.status,
                    checksum=file_record.checksum,
                    processing_result=file_record.processing_result,
                    user_id=file_record.user_id,
                    created_at=file_record.created_at.isoformat(),
                    updated_at=file_record.updated_at.isoformat()
                ))
            
            return FileListResponse(
                files=file_list,
                total=total_count,
                skip=skip,
                limit=limit
            )
            
    except Exception as e:
        logger.error(f"파일 목록 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="파일 목록 조회 중 오류가 발생했습니다."
        )


@router.get("/{file_id}", response_model=FileMetadata)
async def get_file_info(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> FileMetadata:
    """
    파일 정보 조회
    
    Args:
        file_id: 파일 ID
        current_user: 현재 사용자 정보
        
    Returns:
        파일 정보
    """
    
    try:
        # PostgreSQL에서 파일 정보 조회
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FileModel).where(
                    FileModel.file_id == file_id,
                    FileModel.user_id == (current_user.get('id') if isinstance(current_user, dict) else current_user.id)
                )
            )
            file_record = result.scalar_one_or_none()
            
            if not file_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="파일을 찾을 수 없습니다."
                )
            
            return FileMetadata(
                file_id=file_record.file_id,
                original_name=file_record.original_name,
                file_size=file_record.file_size,
                mime_type=file_record.mime_type,
                file_extension=file_record.file_extension,
                upload_path=file_record.upload_path,
                status=file_record.status,
                checksum=file_record.checksum,
                processing_result=file_record.processing_result,
                user_id=file_record.user_id,
                created_at=file_record.created_at.isoformat(),
                updated_at=file_record.updated_at.isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 정보 조회 실패 - {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="파일 정보 조회 중 오류가 발생했습니다."
        )


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    파일 다운로드
    
    Args:
        file_id: 파일 ID
        current_user: 현재 사용자 정보
        
    Returns:
        파일 스트림
    """
    
    try:
        # PostgreSQL에서 파일 정보 조회
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FileModel).where(
                    FileModel.file_id == file_id,
                    FileModel.user_id == (current_user.get('id') if isinstance(current_user, dict) else current_user.id)
                )
            )
            file_record = result.scalar_one_or_none()
            
            if not file_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="파일을 찾을 수 없습니다."
                )
            
            file_path = Path(file_record.upload_path)
            
            # 실제 파일 존재 확인
            if not file_path.exists():
                logger.error(f"파일 시스템에서 파일을 찾을 수 없습니다: {file_path}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="파일이 존재하지 않습니다."
                )
            
            # 파일 다운로드 응답
            return FileResponse(
                path=str(file_path),
                filename=file_record.original_name,
                media_type=file_record.mime_type
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 다운로드 실패 - {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="파일 다운로드 중 오류가 발생했습니다."
        )


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    파일 삭제
    
    Args:
        file_id: 파일 ID
        current_user: 현재 사용자 정보
        
    Returns:
        삭제 결과
    """
    
    try:
        # PostgreSQL에서 파일 정보 조회
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FileModel).where(
                    FileModel.file_id == file_id,
                    FileModel.user_id == (current_user.get('id') if isinstance(current_user, dict) else current_user.id)
                )
            )
            file_record = result.scalar_one_or_none()
            
            if not file_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="파일을 찾을 수 없습니다."
                )
            
            file_path = Path(file_record.upload_path)
            
            # 실제 파일 삭제
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"파일 시스템에서 파일 삭제 완료: {file_path}")
            except Exception as fs_error:
                logger.warning(f"파일 시스템 삭제 실패 (계속 진행): {fs_error}")
            
            # 데이터베이스에서 파일 레코드 삭제
            await session.delete(file_record)
            await session.commit()
            
            logger.info(f"파일 삭제 완료: {file_id}")
            
            return {
                "message": "파일이 성공적으로 삭제되었습니다.",
                "file_id": file_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 삭제 실패 - {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="파일 삭제 중 오류가 발생했습니다."
        )


@router.post("/{file_id}/process")
async def process_file(
    file_id: str,
    processing_type: str = 'auto',  # 'auto', 'text_extraction', 'ocr', 'embedding'
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    파일 처리 (텍스트 추출, OCR, 임베딩 등)
    
    Args:
        file_id: 파일 ID
        processing_type: 처리 유형
        current_user: 현재 사용자 정보
        
    Returns:
        처리 상태 및 결과
    """
    
    try:
        # PostgreSQL에서 파일 정보 조회
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FileModel).where(
                    FileModel.file_id == file_id,
                    FileModel.user_id == (current_user.get('id') if isinstance(current_user, dict) else current_user.id)
                )
            )
            file_record = result.scalar_one_or_none()
            
            if not file_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="파일을 찾을 수 없습니다."
                )
            
            # 이미 처리 중인지 확인
            if file_record.status == 'processing':
                return {
                    "file_id": file_id,
                    "processing_type": processing_type,
                    "status": "processing",
                    "message": "이미 처리 중입니다."
                }
            
            # 처리 상태로 업데이트
            file_record.status = 'processing'
            file_record.metadata_ = file_record.metadata_ or {}
            file_record.metadata_['processing_type'] = processing_type
            file_record.metadata_['processing_started'] = datetime.utcnow().isoformat()
            
            await session.commit()
            
            logger.info(f"파일 처리 시작: {file_id} (타입: {processing_type})")
            
            # 파일 처리 작업 큐에 추가 (백그라운드 처리를 위해)
            # 현재는 기본 응답만 반환
            
            return {
                "file_id": file_id,
                "processing_type": processing_type,
                "status": "processing",
                "message": "파일 처리가 시작되었습니다.",
                "estimated_completion": "수 분 내 예상"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 처리 시작 실패 - {file_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="파일 처리 시작 중 오류가 발생했습니다."
        )