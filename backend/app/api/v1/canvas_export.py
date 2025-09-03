"""
Canvas 내보내기 API 엔드포인트
전문가급 내보내기 기능을 제공하는 RESTful API
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    BackgroundTasks, 
    Response,
    UploadFile,
    File
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.user import User
from app.core.auth import get_current_active_user
from app.models.export_models import *
from app.services.canvas_export_engine import (
    CanvasRenderingEngine, 
    PDFExportEngine, 
    BatchExportEngine
)
from app.services.cloud_export_service import cloud_export_service
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# 내보내기 진행 상황 저장소 (실제 구현에서는 Redis 또는 DB 사용)
export_progress_store: Dict[str, ExportProgress] = {}
export_results_store: Dict[str, ExportResult] = {}


@router.post(
    "/export",
    response_model=ExportProgress,
    summary="Canvas 내보내기",
    description="Canvas를 지정된 형식으로 내보내기"
)
async def export_canvas(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Canvas를 다양한 형식으로 내보내기
    
    - **PNG, JPEG, WebP**: 고품질 래스터 이미지
    - **SVG**: 벡터 그래픽 (무손실 확대 가능)
    - **PDF**: 문서 형식 (인쇄 최적화)
    """
    
    try:
        # 권한 확인 (사용자가 해당 Canvas에 접근 권한이 있는지)
        canvas_uuid = UUID(request.canvas_id)
        user_uuid = UUID(request.user_id)
        
        if str(user_uuid) != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail="해당 Canvas에 대한 권한이 없습니다"
            )
        
        # 내보내기 ID 생성
        export_id = str(uuid4())
        
        # 진행 상황 초기화
        progress = ExportProgress(
            export_id=export_id,
            status="pending",
            progress_percentage=0,
            current_step="내보내기 준비 중...",
            total_steps=4,
            completed_steps=0,
            started_at=datetime.utcnow().isoformat()
        )
        
        export_progress_store[export_id] = progress
        
        # 백그라운드에서 내보내기 실행
        background_tasks.add_task(
            _execute_export,
            export_id,
            request,
            db,
            current_user
        )
        
        return progress
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 요청 파라미터: {str(e)}")
    except Exception as e:
        logger.error(f"내보내기 요청 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="내보내기 요청 처리에 실패했습니다")


@router.post(
    "/batch-export",
    response_model=ExportProgress,
    summary="일괄 내보내기",
    description="여러 Canvas를 한 번에 내보내기 (ZIP 패키징)"
)
async def batch_export_canvas(
    request: BatchExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    여러 Canvas를 일괄적으로 내보내기
    
    - **ZIP 패키징**: 모든 파일을 하나의 ZIP으로 묶음
    - **PDF 통합**: 시리즈를 하나의 PDF로 결합 가능
    - **Manifest 생성**: 내보내기 정보를 JSON으로 포함
    """
    
    try:
        user_uuid = UUID(request.user_id)
        if str(user_uuid) != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail="권한이 없습니다"
            )
        
        # 최대 개수 제한
        if len(request.canvas_ids) > MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"일괄 내보내기는 최대 {MAX_BATCH_SIZE}개까지 가능합니다"
            )
        
        export_id = str(uuid4())
        
        progress = ExportProgress(
            export_id=export_id,
            status="pending",
            progress_percentage=0,
            current_step="일괄 내보내기 준비 중...",
            total_steps=len(request.canvas_ids) + 2,  # Canvas 수 + ZIP 생성 + 업로드
            completed_steps=0,
            started_at=datetime.utcnow().isoformat()
        )
        
        export_progress_store[export_id] = progress
        
        # 백그라운드에서 일괄 내보내기 실행
        background_tasks.add_task(
            _execute_batch_export,
            export_id,
            request,
            db,
            current_user
        )
        
        return progress
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 요청 파라미터: {str(e)}")
    except Exception as e:
        logger.error(f"일괄 내보내기 요청 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="일괄 내보내기 요청 처리에 실패했습니다")


@router.get(
    "/progress/{export_id}",
    response_model=ExportProgress,
    summary="내보내기 진행 상황 조회",
    description="내보내기 작업의 실시간 진행 상황 확인"
)
async def get_export_progress(
    export_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """내보내기 진행 상황 조회"""
    
    progress = export_progress_store.get(export_id)
    if not progress:
        raise HTTPException(status_code=404, detail="내보내기 작업을 찾을 수 없습니다")
    
    return progress


@router.get(
    "/result/{export_id}",
    response_model=ExportResult,
    summary="내보내기 결과 조회",
    description="완료된 내보내기 작업의 결과 정보"
)
async def get_export_result(
    export_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """내보내기 결과 조회"""
    
    result = export_results_store.get(export_id)
    if not result:
        raise HTTPException(status_code=404, detail="내보내기 결과를 찾을 수 없습니다")
    
    return result


@router.get(
    "/download/{export_id}",
    summary="내보내기 파일 다운로드",
    description="내보낸 파일을 다운로드"
)
async def download_exported_file(
    export_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """내보낸 파일 다운로드"""
    
    result = export_results_store.get(export_id)
    if not result:
        raise HTTPException(status_code=404, detail="내보내기 결과를 찾을 수 없습니다")
    
    if not result.success or not result.file_path:
        raise HTTPException(status_code=400, detail="다운로드할 파일이 없습니다")
    
    if not os.path.exists(result.file_path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    
    # 파일 타입별 MIME 타입
    format_info = SUPPORTED_FORMATS.get(result.file_format)
    mime_type = format_info["mime_type"] if format_info else "application/octet-stream"
    
    # 파일명 생성
    filename = os.path.basename(result.file_path)
    
    def iterfile(file_path: str):
        with open(file_path, "rb") as file:
            yield from file
    
    return StreamingResponse(
        iterfile(result.file_path),
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get(
    "/formats",
    summary="지원되는 내보내기 포맷 정보",
    description="사용 가능한 내보내기 포맷과 옵션들"
)
async def get_supported_formats():
    """지원되는 내보내기 포맷 정보"""
    
    return {
        "formats": SUPPORTED_FORMATS,
        "social_presets": {
            preset.value: SocialMediaOptimization.get_preset_dimensions(preset)
            for preset in SocialMediaPreset if preset != SocialMediaPreset.CUSTOM
        },
        "pdf_templates": [template.value for template in PDFTemplate],
        "cloud_providers": [provider.value for provider in CloudProvider],
        "limits": {
            "max_export_size_mb": MAX_EXPORT_SIZE_MB,
            "max_batch_size": MAX_BATCH_SIZE,
            "export_expiry_hours": EXPORT_EXPIRY_HOURS
        }
    }


@router.delete(
    "/cleanup/{export_id}",
    summary="내보내기 파일 정리",
    description="완료된 내보내기 파일을 서버에서 삭제"
)
async def cleanup_export(
    export_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """내보내기 파일 정리"""
    
    result = export_results_store.get(export_id)
    if result and result.file_path and os.path.exists(result.file_path):
        try:
            os.remove(result.file_path)
            logger.info(f"내보내기 파일 삭제됨: {result.file_path}")
        except Exception as e:
            logger.error(f"파일 삭제 실패: {e}")
    
    # 메모리에서 제거
    export_progress_store.pop(export_id, None)
    export_results_store.pop(export_id, None)
    
    return {"message": "정리 완료"}


# ========== 백그라운드 작업 함수들 ==========

async def _execute_export(
    export_id: str,
    request: ExportRequest,
    db: AsyncSession,
    current_user: User
):
    """내보내기 실행 (백그라운드 작업)"""
    
    progress = export_progress_store[export_id]
    
    try:
        # 1단계: Canvas 데이터 검증
        progress.current_step = "Canvas 데이터 검증 중..."
        progress.progress_percentage = 10
        export_progress_store[export_id] = progress
        
        canvas_uuid = UUID(request.canvas_id)
        
        # 2단계: 렌더링 엔진 초기화
        progress.current_step = "렌더링 엔진 초기화..."
        progress.progress_percentage = 25
        progress.completed_steps = 1
        export_progress_store[export_id] = progress
        
        # 3단계: 내보내기 실행
        progress.current_step = f"{request.export_options.format.value.upper()} 형식으로 내보내는 중..."
        progress.progress_percentage = 50
        progress.completed_steps = 2
        export_progress_store[export_id] = progress
        
        # 렌더링 실행
        file_data, metadata = await _render_canvas(db, canvas_uuid, request)
        
        # 4단계: 파일 저장
        progress.current_step = "파일 저장 중..."
        progress.progress_percentage = 75
        progress.completed_steps = 3
        export_progress_store[export_id] = progress
        
        # 임시 파일 저장
        temp_dir = tempfile.gettempdir()
        file_extension = SUPPORTED_FORMATS[request.export_options.format]["extension"]
        filename = f"canvas_export_{export_id}{file_extension}"
        file_path = os.path.join(temp_dir, filename)
        
        if isinstance(file_data, str):  # SVG의 경우
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_data)
        else:  # 바이너리 데이터
            with open(file_path, 'wb') as f:
                f.write(file_data)
        
        # 클라우드 업로드 (옵션)
        cloud_result = None
        if request.cloud_options and request.cloud_options.provider != CloudProvider.NONE:
            progress.current_step = "클라우드 업로드 중..."
            progress.progress_percentage = 90
            export_progress_store[export_id] = progress
            
            # 사용자 클라우드 인증 정보 조회 (실제 구현에서는 DB에서 조회)
            user_credentials = {}  # TODO: DB에서 사용자 클라우드 인증 정보 조회
            
            format_info = SUPPORTED_FORMATS[request.export_options.format]
            cloud_result = await cloud_export_service.upload_to_cloud(
                file_data if isinstance(file_data, bytes) else file_data.encode('utf-8'),
                filename,
                format_info["mime_type"],
                request.cloud_options,
                user_credentials
            )
        
        # 완료
        progress.status = "completed"
        progress.current_step = "내보내기 완료"
        progress.progress_percentage = 100
        progress.completed_steps = 4
        progress.completed_at = datetime.utcnow().isoformat()
        progress.file_size = len(file_data) if isinstance(file_data, bytes) else len(file_data.encode('utf-8'))
        progress.download_url = f"/api/v1/canvas-export/download/{export_id}"
        
        if cloud_result and cloud_result.success:
            progress.cloud_url = cloud_result.share_url or cloud_result.file_url
        
        export_progress_store[export_id] = progress
        
        # 결과 저장
        result = ExportResult(
            export_id=export_id,
            success=True,
            file_path=file_path,
            file_size=progress.file_size,
            file_format=request.export_options.format,
            download_url=progress.download_url,
            cloud_provider=request.cloud_options.provider if request.cloud_options else None,
            cloud_url=progress.cloud_url,
            share_link=cloud_result.share_url if cloud_result and cloud_result.success else None,
            export_options=request.export_options,
            processing_time=0.0,  # TODO: 실제 처리 시간 계산
            created_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(hours=EXPORT_EXPIRY_HOURS)).isoformat()
        )
        
        export_results_store[export_id] = result
        
    except Exception as e:
        logger.error(f"내보내기 실행 실패 ({export_id}): {e}")
        
        progress.status = "failed"
        progress.error_message = str(e)
        progress.completed_at = datetime.utcnow().isoformat()
        export_progress_store[export_id] = progress
        
        # 실패 결과 저장
        result = ExportResult(
            export_id=export_id,
            success=False,
            file_format=request.export_options.format,
            export_options=request.export_options,
            created_at=datetime.utcnow().isoformat(),
            error_message=str(e)
        )
        
        export_results_store[export_id] = result


async def _execute_batch_export(
    export_id: str,
    request: BatchExportRequest,
    db: AsyncSession,
    current_user: User
):
    """일괄 내보내기 실행 (백그라운드 작업)"""
    
    progress = export_progress_store[export_id]
    
    try:
        progress.current_step = "일괄 내보내기 준비 중..."
        progress.progress_percentage = 5
        export_progress_store[export_id] = progress
        
        canvas_uuids = [UUID(cid) for cid in request.canvas_ids]
        
        if request.create_single_pdf and request.export_options.format == ExportFormat.PDF:
            # PDF 통합 모드
            progress.current_step = "다중 페이지 PDF 생성 중..."
            progress.progress_percentage = 50
            export_progress_store[export_id] = progress
            
            pdf_engine = PDFExportEngine()
            file_data, metadata = await pdf_engine.create_multi_page_pdf(
                db, canvas_uuids, request.export_options, request.pdf_options, request.batch_options
            )
            
            # 파일 저장
            temp_dir = tempfile.gettempdir()
            filename = f"batch_export_{export_id}.pdf"
            file_path = os.path.join(temp_dir, filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
                
        else:
            # ZIP 패키징 모드
            progress.current_step = "개별 Canvas 내보내기 중..."
            export_progress_store[export_id] = progress
            
            batch_engine = BatchExportEngine()
            
            # 포맷별 옵션 준비
            format_options = {}
            if request.jpeg_options:
                format_options['jpeg'] = request.jpeg_options
            if request.png_options:
                format_options['png'] = request.png_options
            
            file_data, metadata = await batch_engine.create_batch_export(
                db, canvas_uuids, request.export_options, request.batch_options, format_options
            )
            
            # ZIP 파일 저장
            temp_dir = tempfile.gettempdir()
            filename = f"batch_export_{export_id}.zip"
            file_path = os.path.join(temp_dir, filename)
            
            with open(file_path, 'wb') as f:
                f.write(file_data)
        
        # 클라우드 업로드 (옵션)
        cloud_result = None
        if request.cloud_options and request.cloud_options.provider != CloudProvider.NONE:
            progress.current_step = "클라우드 업로드 중..."
            progress.progress_percentage = 90
            export_progress_store[export_id] = progress
            
            user_credentials = {}  # TODO: DB에서 사용자 클라우드 인증 정보 조회
            
            mime_type = "application/pdf" if request.create_single_pdf else "application/zip"
            cloud_result = await cloud_export_service.upload_to_cloud(
                file_data, filename, mime_type, request.cloud_options, user_credentials
            )
        
        # 완료
        progress.status = "completed"
        progress.current_step = "일괄 내보내기 완료"
        progress.progress_percentage = 100
        progress.completed_steps = progress.total_steps
        progress.completed_at = datetime.utcnow().isoformat()
        progress.file_size = len(file_data)
        progress.download_url = f"/api/v1/canvas-export/download/{export_id}"
        
        if cloud_result and cloud_result.success:
            progress.cloud_url = cloud_result.share_url or cloud_result.file_url
        
        export_progress_store[export_id] = progress
        
        # 결과 저장
        result = ExportResult(
            export_id=export_id,
            success=True,
            file_path=file_path,
            file_size=progress.file_size,
            file_format=request.export_options.format,
            download_url=progress.download_url,
            cloud_provider=request.cloud_options.provider if request.cloud_options else None,
            cloud_url=progress.cloud_url,
            export_options=request.export_options,
            created_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(hours=EXPORT_EXPIRY_HOURS)).isoformat()
        )
        
        export_results_store[export_id] = result
        
    except Exception as e:
        logger.error(f"일괄 내보내기 실행 실패 ({export_id}): {e}")
        
        progress.status = "failed"
        progress.error_message = str(e)
        progress.completed_at = datetime.utcnow().isoformat()
        export_progress_store[export_id] = progress


async def _render_canvas(
    db: AsyncSession,
    canvas_id: UUID,
    request: ExportRequest
) -> tuple[bytes | str, Dict[str, Any]]:
    """Canvas 렌더링 실행"""
    
    if request.export_options.format == ExportFormat.SVG:
        renderer = CanvasRenderingEngine()
        return await renderer.render_canvas_to_svg(
            db, canvas_id, request.export_options, request.svg_options
        )
    elif request.export_options.format == ExportFormat.PDF:
        pdf_engine = PDFExportEngine()
        return await pdf_engine.create_pdf_from_canvas(
            db, canvas_id, request.export_options, request.pdf_options
        )
    else:
        # PNG, JPEG, WebP
        renderer = CanvasRenderingEngine()
        format_options = None
        
        if request.export_options.format == ExportFormat.JPEG:
            format_options = request.jpeg_options
        elif request.export_options.format == ExportFormat.PNG:
            format_options = request.png_options
        elif request.export_options.format == ExportFormat.WEBP:
            format_options = request.webp_options
        
        return await renderer.render_canvas_to_image(
            db, canvas_id, request.export_options, format_options
        )