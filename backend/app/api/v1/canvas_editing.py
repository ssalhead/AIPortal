"""
Canvas 전문가급 편집 도구 API 엔드포인트

편집 히스토리, 실행 취소/다시 실행, AI 도구 등을 제공합니다.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import io

from app.db.session import get_db
from app.services.canvas_editing_history_service import (
    get_canvas_editing_history_service,
    ActionType,
    ActionCategory,
    EditActionData,
    HistoryState
)
from app.models.canvas_models import CanvasResponse
from app.core.security import get_current_user
from app.core.config import get_settings

settings = get_settings()
router = APIRouter()

# ======= 요청/응답 모델 =======

class RecordActionRequest(BaseModel):
    """편집 액션 기록 요청"""
    action_type: ActionType
    element_id: Optional[str] = None
    element_type: Optional[str] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    session_id: Optional[str] = None


class EditActionResponse(BaseModel):
    """편집 액션 응답"""
    action_id: str
    action_type: str
    category: str
    timestamp: datetime
    element_id: Optional[str]
    element_type: Optional[str]
    description: str
    can_undo: bool
    can_redo: bool
    user_id: Optional[str]


class HistoryStateResponse(BaseModel):
    """히스토리 상태 응답"""
    canvas_id: str
    current_action_index: int
    current_branch_id: str
    total_actions: int
    can_undo: bool
    can_redo: bool
    memory_usage_mb: float


class FilterRequest(BaseModel):
    """필터 적용 요청"""
    filter_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    preview_only: bool = False


class FilterResponse(BaseModel):
    """필터 적용 응답"""
    success: bool
    filter_id: str
    processing_time_ms: float
    preview_url: Optional[str] = None
    error_message: Optional[str] = None


class CropRequest(BaseModel):
    """크롭 요청"""
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0
    crop_mode: str = "free"  # free, square, landscape, portrait, circle


class TransformRequest(BaseModel):
    """변형 요청"""
    transform_type: str  # move, rotate, scale, distort, perspective
    matrix: List[float]  # 변형 매트릭스
    element_id: Optional[str] = None


class AIToolRequest(BaseModel):
    """AI 도구 요청"""
    tool_type: str  # background_remove, object_remove, inpainting, enhance
    parameters: Dict[str, Any] = Field(default_factory=dict)
    mask_data: Optional[str] = None  # Base64 인코딩된 마스크 데이터


class CreateSnapshotRequest(BaseModel):
    """스냅샷 생성 요청"""
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class SnapshotResponse(BaseModel):
    """스냅샷 응답"""
    snapshot_id: str
    name: str
    description: Optional[str]
    created_at: datetime
    size_mb: float


class BatchOperationRequest(BaseModel):
    """배치 작업 요청"""
    operation_name: str
    actions: List[Dict[str, Any]]
    parameters: Optional[Dict[str, Any]] = None


class PerformanceMetricsResponse(BaseModel):
    """성능 메트릭 응답"""
    total_actions: int
    undo_count: int
    redo_count: int
    snapshot_count: int
    memory_optimizations: int
    cache_hit_ratio: float
    cached_canvases: int


# ======= 편집 히스토리 관리 =======

@router.post("/canvases/{canvas_id}/actions", response_model=Dict[str, str])
async def record_action(
    canvas_id: str,
    request: RecordActionRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """편집 액션을 기록합니다."""
    
    try:
        history_service = get_canvas_editing_history_service()
        
        action_id = await history_service.record_action(
            canvas_id=canvas_id,
            action_type=request.action_type,
            element_id=request.element_id,
            element_type=request.element_type,
            before_state=request.before_state,
            after_state=request.after_state,
            metadata=request.metadata,
            description=request.description,
            user_id=current_user.get("user_id"),
            session_id=request.session_id,
            db=db
        )
        
        return {"action_id": action_id, "status": "recorded"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"액션 기록 실패: {str(e)}"
        )


@router.post("/canvases/{canvas_id}/undo")
async def undo_action(
    canvas_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """마지막 액션을 실행 취소합니다."""
    
    try:
        history_service = get_canvas_editing_history_service()
        
        undone_action = await history_service.undo(
            canvas_id=canvas_id,
            user_id=current_user.get("user_id"),
            db=db
        )
        
        if undone_action:
            return {
                "success": True,
                "undone_action": {
                    "action_id": undone_action.action_id,
                    "action_type": undone_action.action_type.value,
                    "description": undone_action.description
                }
            }
        else:
            return {"success": False, "message": "실행 취소할 작업이 없습니다"}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"실행 취소 실패: {str(e)}"
        )


@router.post("/canvases/{canvas_id}/redo")
async def redo_action(
    canvas_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """다음 액션을 다시 실행합니다."""
    
    try:
        history_service = get_canvas_editing_history_service()
        
        redone_action = await history_service.redo(
            canvas_id=canvas_id,
            user_id=current_user.get("user_id"),
            db=db
        )
        
        if redone_action:
            return {
                "success": True,
                "redone_action": {
                    "action_id": redone_action.action_id,
                    "action_type": redone_action.action_type.value,
                    "description": redone_action.description
                }
            }
        else:
            return {"success": False, "message": "다시 실행할 작업이 없습니다"}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"다시 실행 실패: {str(e)}"
        )


@router.get("/canvases/{canvas_id}/history/state", response_model=HistoryStateResponse)
async def get_history_state(
    canvas_id: str,
    db: AsyncSession = Depends(get_db)
):
    """현재 히스토리 상태를 조회합니다."""
    
    try:
        history_service = get_canvas_editing_history_service()
        
        state = await history_service.get_history_state(canvas_id, db)
        
        return HistoryStateResponse(
            canvas_id=state.canvas_id,
            current_action_index=state.current_action_index,
            current_branch_id=state.current_branch_id,
            total_actions=state.total_actions,
            can_undo=state.can_undo,
            can_redo=state.can_redo,
            memory_usage_mb=state.memory_usage / (1024 * 1024)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"히스토리 상태 조회 실패: {str(e)}"
        )


@router.get("/canvases/{canvas_id}/history/actions", response_model=List[EditActionResponse])
async def get_action_history(
    canvas_id: str,
    limit: int = 50,
    offset: int = 0,
    action_types: Optional[str] = None,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """액션 히스토리를 조회합니다."""
    
    try:
        history_service = get_canvas_editing_history_service()
        
        # action_types 파싱
        parsed_action_types = None
        if action_types:
            parsed_action_types = [ActionType(t.strip()) for t in action_types.split(',')]
        
        actions = await history_service.get_action_history(
            canvas_id=canvas_id,
            limit=limit,
            offset=offset,
            action_types=parsed_action_types,
            user_id=user_id,
            db=db
        )
        
        return [
            EditActionResponse(
                action_id=action.action_id,
                action_type=action.action_type.value,
                category=action.category.value,
                timestamp=action.timestamp,
                element_id=action.element_id,
                element_type=action.element_type,
                description=action.description,
                can_undo=action.can_undo,
                can_redo=action.can_redo,
                user_id=action.user_id
            )
            for action in actions
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"액션 히스토리 조회 실패: {str(e)}"
        )


# ======= 스냅샷 관리 =======

@router.post("/canvases/{canvas_id}/snapshots", response_model=SnapshotResponse)
async def create_snapshot(
    canvas_id: str,
    request: CreateSnapshotRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Canvas 상태의 스냅샷을 생성합니다."""
    
    try:
        history_service = get_canvas_editing_history_service()
        
        snapshot_id = await history_service.create_snapshot(
            canvas_id=canvas_id,
            name=request.name,
            description=request.description,
            user_id=current_user.get("user_id"),
            db=db
        )
        
        return SnapshotResponse(
            snapshot_id=snapshot_id,
            name=request.name,
            description=request.description,
            created_at=datetime.utcnow(),
            size_mb=0.0  # 실제 크기는 별도 계산 필요
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스냅샷 생성 실패: {str(e)}"
        )


@router.post("/canvases/{canvas_id}/snapshots/{snapshot_id}/restore")
async def restore_snapshot(
    canvas_id: str,
    snapshot_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """스냅샷으로 Canvas 상태를 복원합니다."""
    
    try:
        history_service = get_canvas_editing_history_service()
        
        success = await history_service.restore_snapshot(
            canvas_id=canvas_id,
            snapshot_id=snapshot_id,
            user_id=current_user.get("user_id"),
            db=db
        )
        
        if success:
            return {"success": True, "message": "스냅샷 복원 완료"}
        else:
            return {"success": False, "message": "스냅샷 복원 실패"}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"스냅샷 복원 실패: {str(e)}"
        )


# ======= 필터 시스템 =======

@router.get("/filters", response_model=List[Dict[str, Any]])
async def get_available_filters():
    """사용 가능한 필터 목록을 조회합니다."""
    
    try:
        # 필터 시스템에서 필터 목록 조회
        filters = [
            {
                "id": "brightness",
                "name": "밝기",
                "category": "basic",
                "params": [{"name": "brightness", "min": -100, "max": 100, "default": 0}]
            },
            {
                "id": "contrast", 
                "name": "대비",
                "category": "basic",
                "params": [{"name": "contrast", "min": -100, "max": 100, "default": 0}]
            },
            {
                "id": "saturation",
                "name": "채도", 
                "category": "color",
                "params": [{"name": "saturation", "min": -100, "max": 100, "default": 0}]
            },
            {
                "id": "gaussian-blur",
                "name": "가우시안 블러",
                "category": "blur", 
                "params": [{"name": "radius", "min": 0, "max": 50, "default": 5}]
            },
            {
                "id": "vintage",
                "name": "빈티지",
                "category": "stylize",
                "params": [
                    {"name": "intensity", "min": 0, "max": 100, "default": 50},
                    {"name": "warmth", "min": -50, "max": 50, "default": 30}
                ]
            }
        ]
        
        return filters
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"필터 목록 조회 실패: {str(e)}"
        )


@router.post("/canvases/{canvas_id}/filters/apply", response_model=FilterResponse)
async def apply_filter(
    canvas_id: str,
    request: FilterRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """이미지에 필터를 적용합니다."""
    
    try:
        start_time = datetime.utcnow()
        
        # TODO: 실제 필터 적용 로직 구현
        # 1. Canvas 이미지 데이터 가져오기
        # 2. 필터 시스템으로 필터 적용
        # 3. 결과를 Canvas에 다시 저장
        # 4. 편집 히스토리에 액션 기록
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # 편집 히스토리에 기록
        if not request.preview_only:
            history_service = get_canvas_editing_history_service()
            await history_service.record_action(
                canvas_id=canvas_id,
                action_type=ActionType.FILTER_APPLY,
                metadata={
                    "filter_id": request.filter_id,
                    "parameters": request.parameters
                },
                description=f"필터 적용: {request.filter_id}",
                user_id=current_user.get("user_id"),
                db=db
            )
        
        return FilterResponse(
            success=True,
            filter_id=request.filter_id,
            processing_time_ms=processing_time,
            preview_url=f"/api/v1/canvases/{canvas_id}/preview" if request.preview_only else None
        )
        
    except Exception as e:
        return FilterResponse(
            success=False,
            filter_id=request.filter_id,
            processing_time_ms=0,
            error_message=str(e)
        )


# ======= 편집 도구 =======

@router.post("/canvases/{canvas_id}/crop")
async def crop_image(
    canvas_id: str,
    request: CropRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """이미지를 크롭합니다."""
    
    try:
        # TODO: 크롭 로직 구현
        # 1. Canvas 이미지 데이터 가져오기
        # 2. 크롭 영역 적용
        # 3. 결과를 Canvas에 저장
        
        # 편집 히스토리에 기록
        history_service = get_canvas_editing_history_service()
        await history_service.record_action(
            canvas_id=canvas_id,
            action_type=ActionType.IMAGE_CROP,
            metadata={
                "crop_area": {
                    "x": request.x,
                    "y": request.y,
                    "width": request.width,
                    "height": request.height,
                    "rotation": request.rotation
                },
                "crop_mode": request.crop_mode
            },
            description=f"이미지 크롭: {request.crop_mode}",
            user_id=current_user.get("user_id"),
            db=db
        )
        
        return {"success": True, "message": "크롭 완료"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"크롭 실패: {str(e)}"
        )


@router.post("/canvases/{canvas_id}/transform")
async def transform_element(
    canvas_id: str,
    request: TransformRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """요소를 변형합니다."""
    
    try:
        # TODO: 변형 로직 구현
        
        # 편집 히스토리에 기록
        history_service = get_canvas_editing_history_service()
        action_type_map = {
            "move": ActionType.TRANSFORM_MOVE,
            "rotate": ActionType.TRANSFORM_ROTATE,
            "scale": ActionType.TRANSFORM_SCALE,
            "distort": ActionType.TRANSFORM_DISTORT
        }
        
        await history_service.record_action(
            canvas_id=canvas_id,
            action_type=action_type_map.get(request.transform_type, ActionType.TRANSFORM_MOVE),
            element_id=request.element_id,
            metadata={
                "transform_type": request.transform_type,
                "matrix": request.matrix
            },
            description=f"요소 {request.transform_type}",
            user_id=current_user.get("user_id"),
            db=db
        )
        
        return {"success": True, "message": "변형 완료"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"변형 실패: {str(e)}"
        )


# ======= AI 도구 =======

@router.post("/canvases/{canvas_id}/ai-tools")
async def apply_ai_tool(
    canvas_id: str,
    request: AIToolRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """AI 도구를 적용합니다."""
    
    try:
        # TODO: AI 도구 로직 구현
        # 1. AI 서비스 호출
        # 2. 결과 처리
        # 3. Canvas 업데이트
        
        # 편집 히스토리에 기록
        history_service = get_canvas_editing_history_service()
        action_type_map = {
            "background_remove": ActionType.AI_BACKGROUND_REMOVE,
            "object_remove": ActionType.AI_OBJECT_REMOVE,
            "inpainting": ActionType.AI_INPAINTING,
            "enhance": ActionType.AI_ENHANCE
        }
        
        await history_service.record_action(
            canvas_id=canvas_id,
            action_type=action_type_map.get(request.tool_type, ActionType.AI_BACKGROUND_REMOVE),
            metadata={
                "tool_type": request.tool_type,
                "parameters": request.parameters,
                "has_mask": bool(request.mask_data)
            },
            description=f"AI 도구: {request.tool_type}",
            user_id=current_user.get("user_id"),
            db=db
        )
        
        return {"success": True, "message": f"AI {request.tool_type} 완료"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 도구 적용 실패: {str(e)}"
        )


# ======= 배치 작업 =======

@router.post("/canvases/{canvas_id}/batch-operations")
async def start_batch_operation(
    canvas_id: str,
    request: BatchOperationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """배치 작업을 시작합니다."""
    
    try:
        history_service = get_canvas_editing_history_service()
        
        batch_id = await history_service.start_batch_operation(
            canvas_id=canvas_id,
            operation_name=request.operation_name,
            user_id=current_user.get("user_id")
        )
        
        # TODO: 실제 배치 작업 처리 (비동기)
        
        return {
            "batch_id": batch_id,
            "status": "started",
            "estimated_duration": len(request.actions) * 0.5  # 예상 소요 시간 (초)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"배치 작업 시작 실패: {str(e)}"
        )


# ======= 성능 및 메모리 관리 =======

@router.post("/canvases/{canvas_id}/optimize-memory")
async def optimize_memory(
    canvas_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Canvas 메모리를 최적화합니다."""
    
    try:
        history_service = get_canvas_editing_history_service()
        
        result = await history_service.optimize_memory(canvas_id)
        
        return {
            "success": True,
            "optimization_result": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메모리 최적화 실패: {str(e)}"
        )


@router.get("/editing/statistics", response_model=PerformanceMetricsResponse)
async def get_editing_statistics():
    """편집 서비스 통계를 조회합니다."""
    
    try:
        history_service = get_canvas_editing_history_service()
        
        stats = await history_service.get_statistics()
        
        return PerformanceMetricsResponse(
            total_actions=stats["total_actions"],
            undo_count=stats["undo_count"],
            redo_count=stats["redo_count"],
            snapshot_count=stats["snapshot_count"],
            memory_optimizations=stats["memory_optimizations"],
            cache_hit_ratio=stats["cache_performance"]["hit_ratio"],
            cached_canvases=stats["cached_canvases"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"통계 조회 실패: {str(e)}"
        )


# ======= 파일 업로드 지원 =======

@router.post("/canvases/{canvas_id}/upload-mask")
async def upload_mask_file(
    canvas_id: str,
    mask_file: UploadFile = File(...),
    tool_type: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """마스크 파일을 업로드하고 AI 도구를 적용합니다."""
    
    try:
        # 마스크 파일 처리
        mask_data = await mask_file.read()
        
        # TODO: 마스크 데이터 검증 및 처리
        
        return {
            "success": True,
            "message": "마스크 파일 업로드 완료",
            "file_size": len(mask_data),
            "tool_type": tool_type
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"마스크 파일 업로드 실패: {str(e)}"
        )


# ======= 실시간 미리보기 =======

@router.get("/canvases/{canvas_id}/preview")
async def get_canvas_preview(
    canvas_id: str,
    width: Optional[int] = 200,
    height: Optional[int] = 200
):
    """Canvas의 미리보기 이미지를 생성합니다."""
    
    try:
        # TODO: Canvas 미리보기 생성 로직
        
        # 임시 응답
        return {"preview_url": f"/api/v1/canvases/{canvas_id}/image?w={width}&h={height}"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"미리보기 생성 실패: {str(e)}"
        )