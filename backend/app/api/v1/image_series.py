"""
이미지 시리즈 API 엔드포인트

연속성 있는 이미지 시리즈 생성 및 관리를 위한 RESTful API
"""

import uuid
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.services.image_series_service import ImageSeriesService
from app.db.models.image_series import ImageSeries, SeriesTemplate
from app.db.models.user import User

router = APIRouter()
series_service = ImageSeriesService()


# ======= Pydantic 모델 =======

class SeriesCreateRequest(BaseModel):
    """시리즈 생성 요청"""
    title: str = Field(..., min_length=1, max_length=255, description="시리즈 제목")
    series_type: str = Field(..., description="시리즈 타입 (webtoon, instagram, brand, educational, story)")
    target_count: int = Field(4, ge=1, le=50, description="목표 이미지 개수")
    base_style: str = Field("realistic", description="기본 이미지 스타일")
    consistency_prompt: Optional[str] = Field(None, description="일관성 유지용 공통 프롬프트")
    template_id: Optional[uuid.UUID] = Field(None, description="사용할 템플릿 ID")
    custom_config: Optional[Dict[str, Any]] = Field(None, description="커스텀 설정")
    base_prompts: List[str] = Field(..., min_items=1, max_items=50, description="기본 프롬프트 리스트")
    character_descriptions: Optional[Dict[str, str]] = Field(None, description="캐릭터 설명 딕셔너리")

class SeriesBatchGenerateRequest(BaseModel):
    """시리즈 일괄 생성 요청"""
    series_id: uuid.UUID
    batch_size: int = Field(4, ge=1, le=10, description="한 번에 생성할 이미지 개수")

class SeriesResponse(BaseModel):
    """시리즈 응답"""
    id: uuid.UUID
    title: str
    series_type: str
    current_count: int
    target_count: int
    progress_percentage: float
    completion_status: str
    created_at: str
    updated_at: str

class SeriesImageResponse(BaseModel):
    """시리즈 이미지 응답"""
    id: uuid.UUID
    image_url: str
    series_index: int
    prompt: str
    status: str
    created_at: str
    metadata: Optional[Dict[str, Any]] = None

class TemplateCreateRequest(BaseModel):
    """템플릿 생성 요청"""
    name: str = Field(..., min_length=1, max_length=255)
    series_type: str
    description: Optional[str] = None
    template_config: Dict[str, Any]
    prompt_templates: List[str]
    category: Optional[str] = None
    tags: Optional[List[str]] = None

class TemplateResponse(BaseModel):
    """템플릿 응답"""
    id: uuid.UUID
    name: str
    series_type: str
    description: Optional[str]
    category: Optional[str]
    default_target_count: int
    recommended_style: str
    rating: int
    usage_count: int
    tags: List[str]


# ======= 의존성 함수 =======

def get_current_user() -> User:
    """현재 사용자 가져오기 (임시 구현)"""
    # TODO: 실제 인증 시스템 연동
    return User(id=uuid.uuid4(), username="test_user", email="test@example.com")


# ======= API 엔드포인트 =======

@router.post("/series", response_model=SeriesResponse)
async def create_series(
    request: SeriesCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """새 이미지 시리즈 생성"""
    
    try:
        # 가상 conversation_id 생성 (실제로는 현재 대화에서 가져와야 함)
        conversation_id = uuid.uuid4()
        
        # 시리즈 생성
        series = await series_service.create_series(
            db=db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            title=request.title,
            series_type=request.series_type,
            target_count=request.target_count,
            base_style=request.base_style,
            consistency_prompt=request.consistency_prompt,
            template_id=request.template_id,
            custom_config=request.custom_config
        )
        
        # 프롬프트 생성
        await series_service.generate_series_prompts(
            series=series,
            base_prompts=request.base_prompts,
            character_descriptions=request.character_descriptions
        )
        
        # 백그라운드에서 시리즈 생성 시작
        background_tasks.add_task(
            auto_generate_series,
            db,
            series.id
        )
        
        return SeriesResponse(
            id=series.id,
            title=series.title,
            series_type=series.series_type,
            current_count=series.current_count,
            target_count=series.target_count,
            progress_percentage=series.progress_percentage,
            completion_status=series.completion_status,
            created_at=series.created_at.isoformat(),
            updated_at=series.updated_at.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Series creation failed: {str(e)}")


@router.post("/series/{series_id}/generate")
async def generate_series_batch(
    series_id: uuid.UUID,
    request: SeriesBatchGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """시리즈 일괄 생성 (스트리밍)"""
    
    try:
        async def generate_stream():
            async for progress in series_service.generate_series_batch(
                db=db,
                series_id=request.series_id,
                batch_size=request.batch_size
            ):
                yield f"data: {progress}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.get("/series/{series_id}", response_model=SeriesResponse)
async def get_series(
    series_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """시리즈 정보 조회"""
    
    try:
        progress = await series_service.get_series_progress(db, series_id)
        return SeriesResponse(**progress)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/series/{series_id}/images", response_model=List[SeriesImageResponse])
async def get_series_images(
    series_id: uuid.UUID,
    include_metadata: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """시리즈 이미지 목록 조회"""
    
    try:
        images = await series_service.get_series_images(
            db=db,
            series_id=series_id,
            include_metadata=include_metadata
        )
        
        return [SeriesImageResponse(**img) for img in images]
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/series/{series_id}")
async def delete_series(
    series_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """시리즈 삭제"""
    
    try:
        success = await series_service.delete_series(
            db=db,
            series_id=series_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Series not found")
        
        return {"message": "Series deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=List[TemplateResponse])
async def get_templates(
    series_type: Optional[str] = None,
    featured_only: bool = False,
    db: Session = Depends(get_db)
):
    """사용 가능한 시리즈 템플릿 목록"""
    
    try:
        templates = await series_service.get_available_templates(
            db=db,
            series_type=series_type,
            featured_only=featured_only
        )
        
        return [TemplateResponse(**tmpl) for tmpl in templates]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    request: TemplateCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """새 시리즈 템플릿 생성"""
    
    try:
        template = await series_service.create_series_template(
            db=db,
            name=request.name,
            series_type=request.series_type,
            template_config=request.template_config,
            prompt_templates=request.prompt_templates,
            created_by=current_user.id,
            description=request.description
        )
        
        if request.tags:
            template.tags = request.tags
            db.commit()
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            series_type=template.series_type,
            description=template.description,
            category=template.category,
            default_target_count=template.default_target_count,
            recommended_style=template.recommended_style,
            rating=template.rating,
            usage_count=template.usage_count,
            tags=template.tags or []
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/series/{series_id}/template")
async def duplicate_as_template(
    series_id: uuid.UUID,
    template_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """완성된 시리즈를 템플릿으로 복제"""
    
    try:
        template = await series_service.duplicate_series_as_template(
            db=db,
            series_id=series_id,
            template_name=template_name,
            created_by=current_user.id
        )
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            series_type=template.series_type,
            description=template.description,
            category=template.category,
            default_target_count=template.default_target_count,
            recommended_style=template.recommended_style,
            rating=template.rating,
            usage_count=template.usage_count,
            tags=template.tags or []
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======= 백그라운드 작업 함수 =======

async def auto_generate_series(db: Session, series_id: uuid.UUID):
    """자동 시리즈 생성 백그라운드 작업"""
    
    try:
        async for progress in series_service.generate_series_batch(
            db=db,
            series_id=series_id,
            batch_size=4
        ):
            # 진행 상황 로깅
            print(f"Series generation progress: {progress}")
            
    except Exception as e:
        print(f"Auto generation failed for series {series_id}: {str(e)}")


# ======= 시리즈 타입별 미리 정의된 설정 =======

@router.get("/series-types")
async def get_series_types():
    """지원하는 시리즈 타입 목록"""
    
    return {
        "webtoon": {
            "name": "웹툰 페이지",
            "description": "세로형 패널 구성의 웹툰 페이지 시리즈",
            "recommended_count": [4, 6, 8],
            "aspect_ratios": ["3:4", "2:3"],
            "features": ["character_consistency", "panel_layout", "story_flow"]
        },
        "instagram": {
            "name": "인스타그램 캐러셀",
            "description": "소셜 미디어용 정사각형 이미지 시리즈",
            "recommended_count": [3, 4, 5, 6],
            "aspect_ratios": ["1:1"],
            "features": ["brand_consistency", "social_optimized", "swipe_friendly"]
        },
        "brand": {
            "name": "브랜드 시리즈",
            "description": "일관된 브랜드 아이덴티티를 가진 마케팅 자료",
            "recommended_count": [3, 4, 5],
            "aspect_ratios": ["1:1", "16:9", "4:3"],
            "features": ["brand_colors", "logo_integration", "professional_style"]
        },
        "educational": {
            "name": "교육용 단계별",
            "description": "학습을 위한 단계별 설명 이미지",
            "recommended_count": [3, 4, 5, 6],
            "aspect_ratios": ["16:9", "4:3"],
            "features": ["step_indicators", "clear_diagrams", "instructional_design"]
        },
        "story": {
            "name": "스토리보드",
            "description": "영화나 애니메이션용 스토리보드",
            "recommended_count": [4, 6, 8, 12],
            "aspect_ratios": ["16:9", "21:9"],
            "features": ["cinematic_style", "scene_continuity", "character_consistency"]
        }
    }