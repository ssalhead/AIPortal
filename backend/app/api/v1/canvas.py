"""
Canvas 워크플로우 API 엔드포인트
Request-Based Canvas 시스템과 프론트엔드 통합
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.services.canvas_workflow_dispatcher import (
    CanvasWorkflowDispatcher, 
    ImageGenerationRequest,
    RequestSource,
    workflow_dispatcher
)
from app.services.canvas_lifecycle_service import CanvasLifecycleService
from app.db.models.user import User
from app.core.auth import get_current_active_user

router = APIRouter()
lifecycle_service = CanvasLifecycleService()


class CanvasImageRequestModel(BaseModel):
    """Canvas 이미지 요청 모델"""
    conversationId: str = Field(..., description="대화 ID")
    userId: str = Field(..., description="사용자 ID") 
    prompt: str = Field(..., min_length=3, max_length=2000, description="이미지 생성 프롬프트")
    source: str = Field(..., description="요청 소스 (chat/canvas/api)")
    
    # Canvas 관련 (Edit 모드용)
    canvasId: Optional[str] = Field(None, description="Canvas ID (Edit 모드)")
    referenceImageId: Optional[str] = Field(None, description="참조 이미지 ID (Edit 모드)")
    evolutionType: Optional[str] = Field("variation", description="진화 타입")
    editMode: Optional[str] = Field("EDIT_MODE_INPAINT_INSERTION", description="편집 모드")
    
    # 스타일 및 크기
    style: Optional[str] = Field("realistic", description="이미지 스타일")
    size: Optional[str] = Field("1024x1024", description="이미지 크기")


class CanvasImageResponseModel(BaseModel):
    """Canvas 이미지 응답 모델"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    workflow_mode: Optional[str] = None
    request_source: Optional[str] = None
    dispatch_timestamp: Optional[str] = None


class CanvasHistoryResponseModel(BaseModel):
    """Canvas 히스토리 응답 모델"""
    success: bool
    canvas_id: Optional[str] = None
    history: List[Dict[str, Any]] = []
    analysis: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post(
    "/dispatch-image-request", 
    response_model=CanvasImageResponseModel,
    summary="Canvas 이미지 요청 워크플로우 디스패치",
    description="CREATE/EDIT 모드를 자동 결정하고 적절한 워크플로우로 라우팅"
)
async def dispatch_image_request(
    request: CanvasImageRequestModel,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Canvas 이미지 요청을 워크플로우 디스패처로 전달
    
    - **Chat 요청**: 새 Canvas 생성 (CREATE 모드)
    - **Canvas 요청**: 이미지 진화 (EDIT 모드)
    - **API 요청**: 파라미터에 따라 자동 결정
    """
    try:
        # Request Source 검증 및 변환
        source_mapping = {
            "chat": RequestSource.CHAT,
            "canvas": RequestSource.CANVAS, 
            "api": RequestSource.API
        }
        
        if request.source not in source_mapping:
            raise HTTPException(
                status_code=400,
                detail=f"유효하지 않은 요청 소스: {request.source}"
            )
        
        # ImageGenerationRequest 생성
        image_request = ImageGenerationRequest(
            conversation_id=UUID(request.conversationId),
            user_id=UUID(request.userId),
            prompt=request.prompt,
            source=source_mapping[request.source],
            style=request.style,
            size=request.size,
            canvas_id=UUID(request.canvasId) if request.canvasId else None,
            reference_image_id=UUID(request.referenceImageId) if request.referenceImageId else None,
            evolution_type=request.evolutionType,
            edit_mode_type=request.editMode
        )
        
        # 워크플로우 디스패처로 요청 전달
        result = await workflow_dispatcher.dispatch_image_generation_request(
            db=db,
            request=image_request
        )
        
        return CanvasImageResponseModel(**result)
        
    except ValueError as e:
        # UUID 변환 실패 등
        raise HTTPException(status_code=400, detail=f"요청 파라미터 오류: {str(e)}")
    except Exception as e:
        # 기타 서버 오류
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


@router.get(
    "/history/{conversation_id}/{canvas_id}",
    response_model=CanvasHistoryResponseModel,
    summary="Canvas 상세 히스토리 조회",
    description="특정 Canvas의 전체 버전 히스토리 및 분석 정보 반환"
)
async def get_canvas_history(
    conversation_id: str,
    canvas_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Canvas의 상세 히스토리 조회
    
    - Canvas의 모든 버전 정보
    - 진화 체인 분석
    - 사용된 스타일/크기 통계
    - 편집 모드 분포
    """
    try:
        # UUID 변환
        conv_uuid = UUID(conversation_id)
        canvas_uuid = UUID(canvas_id)
        user_uuid = UUID(str(current_user.id))
        
        # Canvas 히스토리 조회
        result = await lifecycle_service.get_canvas_detailed_history(
            db=db,
            conversation_id=conv_uuid,
            canvas_id=canvas_uuid,
            user_id=user_uuid
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=404 if "찾을 수 없습니다" in result.get("error", "") else 500,
                detail=result.get("error", "Canvas 히스토리 조회 실패")
            )
        
        return CanvasHistoryResponseModel(
            success=True,
            canvas_id=result.get("canvas_id"),
            history=result.get("history", []),
            analysis=result.get("analysis")
        )
        
    except ValueError as e:
        # UUID 변환 실패
        raise HTTPException(status_code=400, detail=f"잘못된 ID 형식: {str(e)}")
    except HTTPException:
        # 이미 처리된 HTTP 예외는 그대로 전달
        raise
    except Exception as e:
        # 기타 서버 오류
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


@router.get(
    "/conversation/{conversation_id}/summary",
    summary="대화의 Canvas 활동 요약",
    description="대화 전체의 Canvas 생성/진화 활동 통계 및 요약"
)
async def get_conversation_canvas_summary(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    대화의 전체 Canvas 활동 요약
    
    - 생성된 Canvas 수
    - 총 이미지 버전 수
    - CREATE vs EDIT 모드 분포
    - 최근 활동 Canvas 정보
    """
    try:
        conv_uuid = UUID(conversation_id)
        user_uuid = UUID(str(current_user.id))
        
        result = await lifecycle_service.get_conversation_canvas_summary(
            db=db,
            conversation_id=conv_uuid,
            user_id=user_uuid
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Canvas 요약 조회 실패")
            )
        
        return result["summary"]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 대화 ID: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


# Canvas 상태 관리 엔드포인트들 (향후 확장용)

@router.post("/validate-evolution-request")
async def validate_canvas_evolution_request(
    conversation_id: str,
    canvas_id: str,
    reference_image_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Canvas 진화 요청 유효성 검증"""
    # TODO: 구현 예정
    return {"valid": True, "message": "검증 로직 구현 예정"}


@router.get("/canvas-configs")
async def get_canvas_configurations():
    """Canvas 설정 정보 조회 (스타일, 크기, 편집 모드 등)"""
    return {
        "styles": ["realistic", "artistic", "cartoon", "abstract", "photographic", "cinematic"],
        "sizes": ["1024x1024", "1024x768", "768x1024", "1280x720", "720x1280"],
        "edit_modes": [
            "EDIT_MODE_INPAINT_INSERTION",
            "EDIT_MODE_INPAINT_REMOVAL", 
            "EDIT_MODE_OUTPAINT",
            "EDIT_MODE_STYLE"
        ],
        "evolution_types": ["based_on", "variation", "extension", "modification", "reference_edit"]
    }