"""
단순화된 이미지 히스토리 API
conversationId 기반 통합 이미지 관리 REST API

기존 복잡한 image_sessions API를 대체하는 단순하고 직관적인 API
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from app.api.deps import get_current_active_user, get_db
from app.db.models.user import User
from app.db.models.image_history import ImageHistory
from app.services.simple_image_history_service import SimpleImageHistoryService
from app.services.image_generation_service import ImageGenerationService
from app.utils.logger import get_logger
# Rate limiting removed for simplicity - can be added later if needed

logger = get_logger(__name__)

# Router 설정
router = APIRouter(prefix="/images/history", tags=["simple-image-history"])
security = HTTPBearer()

# Service 인스턴스
image_history_service = SimpleImageHistoryService()
image_generation_service = ImageGenerationService()

# ======= Pydantic 모델들 =======

class ImageHistoryResponse(BaseModel):
    """이미지 히스토리 응답 모델"""
    id: uuid.UUID
    conversation_id: uuid.UUID
    prompt: str
    image_urls: List[str]
    primary_image_url: str
    style: str
    size: str
    parent_image_id: Optional[uuid.UUID] = None
    evolution_type: Optional[str] = None
    canvas_id: Optional[uuid.UUID] = None
    canvas_version: Optional[int] = None
    edit_mode: Optional[str] = None
    reference_image_id: Optional[uuid.UUID] = None
    is_selected: bool
    is_evolution: bool
    safety_score: float
    file_size_bytes: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None  # 업데이트 날짜 추가
    
    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str,
            datetime: lambda v: v.isoformat()
        }


class ImageGenerationRequest(BaseModel):
    """이미지 생성 요청 모델"""
    prompt: str = Field(..., min_length=1, max_length=2000, description="이미지 생성 프롬프트")
    style: str = Field("realistic", description="이미지 스타일")
    size: str = Field("1024x1024", description="이미지 크기")
    conversation_id: uuid.UUID = Field(..., description="대화 ID")


class ImageEvolutionRequest(BaseModel):
    """이미지 진화 생성 요청 모델"""
    parent_image_id: uuid.UUID = Field(..., description="기반 이미지 ID")
    new_prompt: str = Field(..., min_length=1, max_length=2000, description="새로운 요구사항")
    evolution_type: str = Field("modification", description="진화 타입")
    style: Optional[str] = Field(None, description="스타일 (기본: 부모 이미지 설정 상속)")
    size: Optional[str] = Field(None, description="크기 (기본: 부모 이미지 설정 상속)")


class ImageEditRequest(BaseModel):
    """이미지 편집 요청 모델 (Reference Images 기반)"""
    reference_image_id: uuid.UUID = Field(..., description="참조할 기존 이미지 ID")
    prompt: str = Field(..., min_length=1, max_length=2000, description="편집 프롬프트")
    edit_mode: str = Field("EDIT_MODE_DEFAULT", description="편집 모드")
    mask_mode: Optional[str] = Field(None, description="마스크 모드 (선택적)")
    style: Optional[str] = Field(None, description="스타일 (선택적)")
    size: Optional[str] = Field(None, description="크기 (선택적)")
    num_images: int = Field(1, ge=1, le=4, description="생성할 이미지 수")


class ImageSelectionRequest(BaseModel):
    """이미지 선택 요청 모델"""
    image_id: uuid.UUID = Field(..., description="선택할 이미지 ID")


class ConversationStatsResponse(BaseModel):
    """대화별 이미지 통계 응답"""
    conversation_id: uuid.UUID
    total_images: int
    original_images: int
    evolution_images: int
    avg_safety_score: float
    total_file_size_mb: float
    selected_image_id: Optional[uuid.UUID] = None


class ImageHistoryListResponse(BaseModel):
    """이미지 히스토리 목록 응답"""
    conversation_id: uuid.UUID
    images: List[ImageHistoryResponse]
    selected_image: Optional[ImageHistoryResponse] = None
    stats: ConversationStatsResponse
    total_count: int


# ======= API 엔드포인트들 =======

@router.get("/{conversation_id}", response_model=ImageHistoryListResponse)
async def get_conversation_image_history(
    conversation_id: uuid.UUID,
    include_deleted: bool = Query(False, description="삭제된 이미지 포함 여부"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """대화별 이미지 히스토리 조회"""
    
    try:
        # 1. 이미지 히스토리 조회
        images = await image_history_service.get_conversation_images(
            db, conversation_id, current_user["id"], include_deleted
        )
        
        # 2. 선택된 이미지 조회
        selected_image = await image_history_service.get_selected_image(
            db, conversation_id, current_user["id"]
        )
        
        # 3. 통계 조회
        stats_data = await image_history_service.get_conversation_stats(
            db, conversation_id, current_user["id"]
        )
        
        # 4. 응답 데이터 구성
        image_responses = [ImageHistoryResponse.from_orm(img) for img in images]
        selected_response = ImageHistoryResponse.from_orm(selected_image) if selected_image else None
        
        stats = ConversationStatsResponse(
            conversation_id=conversation_id,
            selected_image_id=selected_image.id if selected_image else None,
            **stats_data
        )
        
        response = ImageHistoryListResponse(
            conversation_id=conversation_id,
            images=image_responses,
            selected_image=selected_response,
            stats=stats,
            total_count=len(images)
        )
        
        logger.info(f"📋 대화 {conversation_id} 이미지 히스토리 조회: {len(images)}개")
        return response
        
    except Exception as e:
        logger.error(f"❌ 이미지 히스토리 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="이미지 히스토리 조회에 실패했습니다")


@router.post("/generate", response_model=ImageHistoryResponse)
async def generate_new_image(
    request: ImageGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """새로운 이미지 생성"""
    
    try:
        # 1. 중복 프롬프트 확인 (선택사항)
        duplicate_image = await image_history_service.check_duplicate_prompt(
            db, request.conversation_id, current_user["id"], 
            request.prompt, request.style, request.size
        )
        
        if duplicate_image:
            logger.warning(f"⚠️ 중복 프롬프트 감지: {duplicate_image.id}")
            # 중복이어도 새로 생성하되, 로그만 남김
        
        # 2. AI 이미지 생성
        generation_result = await image_generation_service.generate_image(
            prompt=request.prompt,
            style=request.style,
            size=request.size,
            num_images=1
        )
        
        if not generation_result.get("images"):
            raise HTTPException(status_code=500, detail="이미지 생성에 실패했습니다")
        
        # 3. 히스토리에 저장 (UUID 직렬화 안전 처리)
        safe_generation_params = image_history_service.safe_uuid_to_str({
            "api_response": generation_result,
            "user_request": request.dict()
        })
        
        new_image = await image_history_service.save_generated_image(
            db=db,
            conversation_id=request.conversation_id,
            user_id=current_user["id"],
            prompt=request.prompt,
            image_urls=generation_result["images"],
            style=request.style,
            size=request.size,
            safety_score=generation_result.get("safety_score", 1.0),
            generation_params=safe_generation_params
        )
        
        # 4. 백그라운드 작업: 파일 크기 계산
        background_tasks.add_task(
            _update_image_file_size,
            new_image.id,
            new_image.primary_image_url
        )
        
        logger.info(f"🎨 새 이미지 생성 완료: {new_image.id}")
        return ImageHistoryResponse.from_orm(new_image)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "user_id": current_user["id"],
            "conversation_id": request.conversation_id,
            "prompt": request.prompt[:100] if request.prompt else None,
            "style": request.style,
            "size": request.size
        }
        logger.error(f"❌ 이미지 생성 중 오류: {error_details}")
        logger.error(f"📍 전체 오류 스택:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"이미지 생성 중 오류가 발생했습니다: {type(e).__name__}")


@router.post("/evolve", response_model=ImageHistoryResponse)
async def evolve_image_from_selected(
    request: ImageEvolutionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """선택된 이미지 기반 진화 이미지 생성"""
    
    logger.info(f"🔄 Canvas 진화 요청 수신: parent={request.parent_image_id}, user={current_user['id']}")
    
    try:
        # 1. 새로운 진화 이미지 생성
        evolved_image = await image_history_service.generate_evolution_image(
            db=db,
            parent_image_id=request.parent_image_id,
            user_id=current_user["id"],
            new_prompt=request.new_prompt,
            evolution_type=request.evolution_type,
            style=request.style,
            size=request.size
        )
        
        if not evolved_image:
            logger.error(f"❌ 진화 이미지 생성 실패")
            raise HTTPException(status_code=500, detail="진화 이미지 생성에 실패했습니다")
        
        logger.info(f"✅ 진화 이미지 생성 성공: {evolved_image.id}")
        
        # 2. 백그라운드 작업: 파일 크기 계산
        background_tasks.add_task(
            _update_image_file_size,
            evolved_image.id,
            evolved_image.primary_image_url
        )
        
        logger.info(f"🎉 진화 이미지 생성 완료: {evolved_image.id} (부모: {request.parent_image_id})")
        return ImageHistoryResponse.from_orm(evolved_image)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "user_id": current_user["id"],
            "parent_image_id": request.parent_image_id,
            "new_prompt": request.new_prompt[:100] if request.new_prompt else None,
            "evolution_type": request.evolution_type,
            "style": request.style,
            "size": request.size
        }
        logger.error(f"❌ 진화 이미지 생성 중 오류: {error_details}")
        logger.error(f"💣 전체 오류 스택:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"진화 이미지 생성 중 오류가 발생했습니다: {type(e).__name__}")


@router.put("/select", response_model=ImageHistoryResponse)
async def select_image(
    request: ImageSelectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """특정 이미지를 선택된 상태로 설정"""
    
    try:
        selected_image = await image_history_service.select_image(
            db, request.image_id, current_user["id"]
        )
        
        if not selected_image:
            raise HTTPException(status_code=404, detail="선택할 이미지를 찾을 수 없습니다")
        
        logger.info(f"🎯 이미지 선택: {selected_image.id}")
        return ImageHistoryResponse.from_orm(selected_image)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 이미지 선택 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="이미지 선택 중 오류가 발생했습니다")


@router.delete("/{image_id}")
async def delete_image(
    image_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """이미지 삭제 (소프트 삭제)"""
    
    try:
        success = await image_history_service.delete_image(
            db, image_id, current_user["id"]
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="삭제할 이미지를 찾을 수 없습니다")
        
        logger.info(f"🗑️ 이미지 삭제: {image_id}")
        return {"message": "이미지가 성공적으로 삭제되었습니다", "deleted_id": str(image_id)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 이미지 삭제 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="이미지 삭제 중 오류가 발생했습니다")


@router.get("/{conversation_id}/stats", response_model=ConversationStatsResponse)
async def get_conversation_image_stats(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """대화별 이미지 생성 통계"""
    
    try:
        stats_data = await image_history_service.get_conversation_stats(
            db, conversation_id, current_user["id"]
        )
        
        selected_image = await image_history_service.get_selected_image(
            db, conversation_id, current_user["id"]
        )
        
        stats = ConversationStatsResponse(
            conversation_id=conversation_id,
            selected_image_id=selected_image.id if selected_image else None,
            **stats_data
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ 통계 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="통계 조회 중 오류가 발생했습니다")


@router.post("/edit", response_model=ImageHistoryResponse)
async def edit_image_with_reference(
    request: ImageEditRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Reference Images를 사용한 이미지 편집"""
    
    logger.info(f"✏️ 이미지 편집 요청 수신:")
    logger.info(f"   📝 reference_image_id: {request.reference_image_id} (타입: {type(request.reference_image_id)})")
    logger.info(f"   👤 user_id: {current_user['id']} (타입: {type(current_user['id'])})")
    logger.info(f"   💬 prompt: '{request.prompt}' (길이: {len(request.prompt)})")
    logger.info(f"   🎨 edit_mode: {request.edit_mode}")
    logger.info(f"   🎭 style: {request.style}")
    logger.info(f"   📏 size: {request.size}")
    logger.info(f"   🔢 num_images: {request.num_images}")
    
    try:
        # 1. 참조 이미지 존재 여부 및 권한 확인
        logger.debug(f"🔍 참조 이미지 조회 시작: reference_image_id={request.reference_image_id}")
        reference_image = await image_history_service.get_image_by_id(
            db, request.reference_image_id, current_user["id"]
        )
        logger.debug(f"🎯 참조 이미지 조회 결과: {'있음' if reference_image else '없음'}")
        
        if not reference_image:
            raise HTTPException(status_code=404, detail="참조할 이미지를 찾을 수 없습니다")
        
        # 2. 참조 이미지 URL 추출
        reference_image_url = reference_image.primary_image_url
        if not reference_image_url:
            raise HTTPException(status_code=400, detail="참조 이미지에 유효한 URL이 없습니다")
        
        logger.debug(f"📷 참조 이미지 URL: {reference_image_url[:50]}...")
        
        # 3. 이미지 편집 API 호출
        job_id = str(uuid.uuid4())
        logger.info(f"🎨 이미지 편집 API 호출 시작: job_id={job_id}")
        logger.debug(f"🔧 편집 파라미터: edit_mode={request.edit_mode}, style={request.style}, size={request.size}")
        
        edit_result = await image_generation_service.edit_image(
            job_id=job_id,
            user_id=str(current_user["id"]),
            prompt=request.prompt,
            reference_image_url=reference_image_url,
            edit_mode=request.edit_mode,
            mask_mode=request.mask_mode,
            style=request.style,
            size=request.size,
            num_images=request.num_images
        )
        
        logger.info(f"✅ 이미지 편집 API 호출 완료: 결과={'있음' if edit_result else '없음'}")
        if edit_result:
            logger.debug(f"🖼️ 편집 결과: images_count={len(edit_result.get('images', []))}")
        
        if not edit_result or not edit_result.get("images"):
            raise HTTPException(status_code=500, detail="이미지 편집에 실패했습니다")
        
        # 4. 편집된 이미지를 히스토리에 저장 (최적화된 Canvas ID 처리)
        # Canvas ID 상속: 참조 이미지와 동일한 Canvas로 그룹화
        canvas_id = reference_image.canvas_id or uuid.uuid4()  # 기존 Canvas ID 상속 또는 새로 생성
        canvas_version = (reference_image.canvas_version or 0) + 1  # 버전 증가
        
        logger.debug(f"🎨 Canvas 정보: canvas_id={canvas_id}, version={canvas_version}")
        
        edited_image = await image_history_service.save_generated_image(
            db=db,
            conversation_id=reference_image.conversation_id,  # 기존 이미지와 동일한 conversation
            user_id=current_user["id"],
            prompt=request.prompt,
            image_urls=edit_result["images"],
            style=request.style or reference_image.style,
            size=request.size or reference_image.size,
            parent_image_id=request.reference_image_id,
            evolution_type="reference_edit",  # 새로운 타입
            generation_params=image_history_service.safe_uuid_to_str({
                "edit_mode": request.edit_mode,
                "mask_mode": request.mask_mode,
                "reference_image_url": reference_image_url,
                "reference_prompt": reference_image.prompt,
                "api_response": edit_result,
                "user_request": request.dict(),
                "reference_image_id": request.reference_image_id,
                "canvas_workflow": "edit",
                "canvas_inheritance": True
            }),
            safety_score=edit_result.get("safety_score", 1.0),
            canvas_id=canvas_id,
            canvas_version=canvas_version,
            edit_mode="EDIT",
            reference_image_id=request.reference_image_id
        )
        
        # 5. 백그라운드 작업: 파일 크기 계산
        background_tasks.add_task(
            _update_image_file_size,
            edited_image.id,
            edited_image.primary_image_url
        )
        
        logger.info(f"🎉 이미지 편집 완료: {edited_image.id} (참조: {request.reference_image_id})")
        return ImageHistoryResponse.from_orm(edited_image)
        
    except HTTPException as he:
        logger.warning(f"⚠️ HTTP 예외: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ 이미지 편집 중 예외 발생:")
        logger.error(f"   예외 타입: {type(e).__name__}")
        logger.error(f"   예외 메시지: {str(e)}")
        
        # 상세 스택 트레이스 로깅
        import traceback
        stack_trace = traceback.format_exc()
        logger.error(f"💣 상세 스택 트레이스:\n{stack_trace}")
        
        # 특정 예외 타입별 추가 정보
        if hasattr(e, '__dict__'):
            logger.error(f"📋 예외 속성: {e.__dict__}")
        
        raise HTTPException(status_code=500, detail=f"이미지 편집 중 오류가 발생했습니다: {str(e)}")


# ======= 백그라운드 작업 함수 =======

async def _update_image_file_size(image_id: uuid.UUID, image_url: str):
    """백그라운드에서 이미지 파일 크기 업데이트"""
    try:
        # 실제 구현에서는 이미지 URL에서 파일 크기를 가져와 업데이트
        # 현재는 로그만 남김
        logger.debug(f"📊 이미지 파일 크기 업데이트 예약: {image_id}")
    except Exception as e:
        logger.error(f"❌ 파일 크기 업데이트 실패: {str(e)}")

# ======= 에러 핸들러 =======
# Exception handlers removed - error handling done directly in endpoints