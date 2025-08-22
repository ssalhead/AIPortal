"""
AI 이미지 생성 API
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import os
import aiofiles
import base64
import io
from datetime import datetime
from pathlib import Path
import logging

from app.api.deps import get_db, get_current_active_user
from app.core.config import settings
from app.services.image_generation_service import image_generation_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ImageGenerationRequest(BaseModel):
    """이미지 생성 요청 (Imagen 4 전용)"""
    prompt: str = Field(..., description="이미지 생성 프롬프트", min_length=1, max_length=1000)
    style: str = Field(default="realistic", description="이미지 스타일")
    sample_image_size: str = Field(default="1K", description="이미지 해상도 (1K, 2K)")
    aspect_ratio: str = Field(default="1:1", description="종횡비 (1:1, 4:3, 3:4, 16:9, 9:16)")
    num_images: int = Field(default=1, description="생성할 이미지 수", ge=1, le=4)


class ImageGenerationResponse(BaseModel):
    """이미지 생성 응답 (Imagen 4 전용)"""
    job_id: str
    status: str  # 'processing', 'completed', 'failed'
    images: List[str] = []  # 이미지 URL 목록
    prompt: str
    revised_prompt: Optional[str] = None  # AI가 수정한 프롬프트
    metadata: Dict[str, Any] = {}
    created_at: str
    estimated_completion_time: Optional[str] = None


class ImageGenerationJob(BaseModel):
    """이미지 생성 작업"""
    job_id: str
    user_id: str
    prompt: str
    negative_prompt: Optional[str]
    style: str
    size: str
    quality: str
    num_images: int
    model: str
    status: str
    images: List[str] = []
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> ImageGenerationResponse:
    """
    AI 이미지 생성
    
    Args:
        request: 이미지 생성 요청
        db: 데이터베이스 세션
        current_user: 현재 사용자
        
    Returns:
        이미지 생성 응답
    """
    
    try:
        user_id = current_user.get('id', str(uuid.uuid4()))
        
        # 요청 유효성 검증
        if not await _validate_generation_request(request, user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미지 생성 요청이 유효하지 않습니다."
            )
        
        # 이미지 생성 작업 시작
        job_id = str(uuid.uuid4())
        
        logger.info(f"이미지 생성 시작: job_id={job_id}, user_id={user_id}")
        
        # Imagen 4 이미지 생성 서비스 호출
        result = await image_generation_service.generate_image(
            job_id=job_id,
            user_id=user_id,
            prompt=request.prompt,
            style=request.style,
            size=f"{request.sample_image_size}_{request.aspect_ratio.replace(':', 'x')}",  # 크기 형식 변환
            num_images=request.num_images,
            model="imagen-4"
        )
        
        return ImageGenerationResponse(
            job_id=job_id,
            status=result.get('status', 'processing'),
            images=result.get('images', []),
            prompt=request.prompt,
            metadata=result.get('metadata', {}),
            created_at=datetime.utcnow().isoformat(),
            estimated_completion_time=result.get('estimated_completion_time')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 생성 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 생성 중 오류가 발생했습니다."
        )


@router.get("/job/{job_id}", response_model=ImageGenerationResponse)
async def get_generation_status(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> ImageGenerationResponse:
    """
    이미지 생성 작업 상태 조회
    
    Args:
        job_id: 작업 ID
        current_user: 현재 사용자
        
    Returns:
        작업 상태 정보
    """
    
    try:
        user_id = current_user.get('id', str(uuid.uuid4()))
        
        # 작업 상태 조회
        job_status = await image_generation_service.get_job_status(job_id, user_id)
        
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="작업을 찾을 수 없습니다."
            )
        
        return ImageGenerationResponse(
            job_id=job_id,
            status=job_status.get('status', 'unknown'),
            images=job_status.get('images', []),
            prompt=job_status.get('prompt', ''),
            revised_prompt=job_status.get('revised_prompt'),
            metadata=job_status.get('metadata', {}),
            created_at=job_status.get('created_at', ''),
            estimated_completion_time=job_status.get('estimated_completion_time')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"작업 상태 조회 실패 - job_id={job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="작업 상태 조회 중 오류가 발생했습니다."
        )


@router.get("/history")
async def get_generation_history(
    limit: int = 20,
    skip: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    사용자 이미지 생성 히스토리 조회
    
    Args:
        limit: 조회할 항목 수
        skip: 건너뛸 항목 수
        current_user: 현재 사용자
        
    Returns:
        생성 히스토리
    """
    
    try:
        user_id = current_user.get('id', str(uuid.uuid4()))
        
        history = await image_generation_service.get_user_history(
            user_id=user_id,
            limit=limit,
            skip=skip
        )
        
        return {
            "history": history.get('jobs', []),
            "total": history.get('total', 0),
            "limit": limit,
            "skip": skip
        }
        
    except Exception as e:
        logger.error(f"히스토리 조회 실패 - user_id={user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="히스토리 조회 중 오류가 발생했습니다."
        )


@router.delete("/job/{job_id}")
async def delete_generation_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    이미지 생성 작업 삭제
    
    Args:
        job_id: 작업 ID
        current_user: 현재 사용자
        
    Returns:
        삭제 결과
    """
    
    try:
        user_id = current_user.get('id', str(uuid.uuid4()))
        
        result = await image_generation_service.delete_job(job_id, user_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="작업을 찾을 수 없습니다."
            )
        
        return {
            "message": "이미지 생성 작업이 삭제되었습니다.",
            "job_id": job_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"작업 삭제 실패 - job_id={job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="작업 삭제 중 오류가 발생했습니다."
        )


@router.get("/styles")
async def get_available_styles():
    """사용 가능한 이미지 스타일 목록 조회 (Imagen 4 전용)"""
    return {
        "styles": [
            {"id": "realistic", "name": "사실적", "description": "photorealistic, professional photography", "template": "A highly detailed, photorealistic {prompt}, professional photography, sharp focus, natural lighting"},
            {"id": "artistic", "name": "예술적", "description": "oil painting, fine art", "template": "An artistic interpretation of {prompt}, oil painting style, masterpiece, fine art, gallery quality"},
            {"id": "cartoon", "name": "만화", "description": "animated, Disney-like", "template": "A cartoon-style illustration of {prompt}, animated, colorful, stylized, Disney-like animation"},
            {"id": "abstract", "name": "추상적", "description": "modern art, conceptual", "template": "An abstract artistic representation of {prompt}, modern art, conceptual, geometric shapes, vibrant colors"},
            {"id": "3d", "name": "3D", "description": "CGI, digital art", "template": "A 3D rendered image of {prompt}, CGI, digital art, realistic materials, professional lighting"},
            {"id": "anime", "name": "애니메이션", "description": "Japanese animation, manga", "template": "An anime-style illustration of {prompt}, Japanese animation, manga style, vibrant colors, detailed"}
        ]
    }


@router.get("/models")
async def get_available_models():
    """사용 가능한 이미지 생성 모델 목록 조회 (Imagen 4 전용)"""
    return {
        "models": [
            {
                "id": "imagen-4.0-generate-001",
                "name": "Imagen 4",
                "description": "Google의 최신 이미지 생성 모델",
                "max_images": 4,
                "supports_resolutions": ["1K", "2K"],
                "supports_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
                "max_prompt_length": 1000,
                "supports_negative_prompt": False,
                "includes_synthid_watermark": True
            }
        ]
    }


@router.get("/sizes")
async def get_available_sizes():
    """사용 가능한 이미지 크기 및 종횡비 조회 (Imagen 4 전용)"""
    return {
        "resolutions": [
            {"id": "1K", "name": "1K 해상도", "description": "빠른 생성, 일반적인 사용에 적합"},
            {"id": "2K", "name": "2K 해상도", "description": "고품질, 상세한 이미지에 적합"}
        ],
        "aspect_ratios": [
            {"id": "1:1", "name": "정사각형", "description": "1:1 비율, 소셜 미디어에 적합"},
            {"id": "4:3", "name": "가로형 4:3", "description": "전통적인 가로형 비율"},
            {"id": "3:4", "name": "세로형 3:4", "description": "전통적인 세로형 비율"},
            {"id": "16:9", "name": "와이드 16:9", "description": "와이드스크린, 영상에 적합"},
            {"id": "9:16", "name": "모바일 9:16", "description": "모바일 화면, 스토리에 적합"}
        ]
    }


async def _validate_generation_request(request: ImageGenerationRequest, user_id: str) -> bool:
    """이미지 생성 요청 유효성 검증"""
    
    try:
        # 프롬프트 길이 검증
        if len(request.prompt.strip()) < 1:
            return False
        
        # 이미지 해상도 검증
        valid_sizes = ["1K", "2K"]
        if request.sample_image_size not in valid_sizes:
            return False
        
        # 종횡비 검증
        valid_ratios = ["1:1", "4:3", "3:4", "16:9", "9:16"]
        if request.aspect_ratio not in valid_ratios:
            return False
        
        # 스타일 검증
        valid_styles = ["realistic", "artistic", "cartoon", "abstract", "3d", "anime"]
        if request.style not in valid_styles:
            return False
        
        # 사용자별 제한 확인 (일일 생성 제한 등)
        daily_limit = await image_generation_service.check_daily_limit(user_id)
        if not daily_limit:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"요청 검증 실패: {e}")
        return False