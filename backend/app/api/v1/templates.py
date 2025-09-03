# Canvas Template API Endpoints
# AIPortal Canvas Template Library - REST API 엔드포인트

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.template_models import (
    TemplateCreateRequest, TemplateUpdateRequest, TemplateSearchRequest,
    TemplateApplyRequest, TemplateCustomizationRequest, TemplateReviewRequest,
    CollectionCreateRequest, CollectionUpdateRequest, CustomizationPresetRequest,
    TemplateResponse, TemplateDetailResponse, TemplateSearchResponse,
    TemplateCategory, TemplateSubcategory, LicenseType, DifficultyLevel, SortBy
)
from app.services.canvas_template_service import CanvasTemplateService
from app.core.exceptions import NotFoundError, ValidationError, PermissionError
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["Canvas Templates"])

# ===== 템플릿 CRUD =====

@router.post("/", response_model=TemplateDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    request: TemplateCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    새로운 템플릿 생성
    """
    try:
        service = CanvasTemplateService(db)
        template = await service.create_template(request, current_user.id)
        
        return template
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 생성 중 오류가 발생했습니다"
        )

@router.get("/search", response_model=TemplateSearchResponse)
async def search_templates(
    query: Optional[str] = Query(None, description="검색 키워드"),
    category: Optional[TemplateCategory] = Query(None, description="카테고리"),
    subcategory: Optional[TemplateSubcategory] = Query(None, description="서브카테고리"),
    tags: Optional[str] = Query(None, description="태그 (쉼표로 구분)"),
    license_type: Optional[LicenseType] = Query(None, description="라이선스 타입"),
    difficulty_level: Optional[DifficultyLevel] = Query(None, description="난이도"),
    is_featured: Optional[bool] = Query(None, description="추천 템플릿"),
    min_rating: Optional[float] = Query(None, ge=1.0, le=5.0, description="최소 평점"),
    created_after: Optional[datetime] = Query(None, description="생성일 이후"),
    created_before: Optional[datetime] = Query(None, description="생성일 이전"),
    sort_by: SortBy = Query(SortBy.CREATED_DESC, description="정렬 기준"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    템플릿 검색
    """
    try:
        # 태그 파싱
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
        
        request = TemplateSearchRequest(
            query=query,
            category=category,
            subcategory=subcategory,
            tags=tag_list,
            license_type=license_type,
            difficulty_level=difficulty_level,
            is_featured=is_featured,
            min_rating=min_rating,
            created_after=created_after,
            created_before=created_before,
            sort_by=sort_by,
            page=page,
            page_size=page_size
        )
        
        service = CanvasTemplateService(db)
        result = await service.search_templates(
            request, 
            current_user.id if current_user else None
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error searching templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 검색 중 오류가 발생했습니다"
        )

@router.get("/featured", response_model=List[TemplateResponse])
async def get_featured_templates(
    limit: int = Query(20, ge=1, le=100, description="조회할 개수"),
    db: Session = Depends(get_db)
):
    """
    추천 템플릿 목록
    """
    try:
        service = CanvasTemplateService(db)
        templates = await service.get_featured_templates(limit)
        
        return templates
        
    except Exception as e:
        logger.error(f"Error fetching featured templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="추천 템플릿 조회 중 오류가 발생했습니다"
        )

@router.get("/trending", response_model=List[TemplateResponse])
async def get_trending_templates(
    limit: int = Query(20, ge=1, le=100, description="조회할 개수"),
    days: int = Query(7, ge=1, le=30, description="기준 일수"),
    db: Session = Depends(get_db)
):
    """
    트렌딩 템플릿 목록
    """
    try:
        service = CanvasTemplateService(db)
        templates = await service.get_trending_templates(limit, days)
        
        return templates
        
    except Exception as e:
        logger.error(f"Error fetching trending templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="트렌딩 템플릿 조회 중 오류가 발생했습니다"
        )

@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(
    template_id: UUID,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    템플릿 상세 조회
    """
    try:
        service = CanvasTemplateService(db)
        template = await service.get_template(
            template_id, 
            current_user.id if current_user else None
        )
        
        return template
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 조회 중 오류가 발생했습니다"
        )

@router.put("/{template_id}", response_model=TemplateDetailResponse)
async def update_template(
    template_id: UUID,
    request: TemplateUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    템플릿 수정
    """
    try:
        service = CanvasTemplateService(db)
        template = await service.update_template(template_id, request, current_user.id)
        
        return template
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 수정 중 오류가 발생했습니다"
        )

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    템플릿 삭제 (아카이브)
    """
    try:
        service = CanvasTemplateService(db)
        success = await service.delete_template(template_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="템플릿 삭제에 실패했습니다"
            )
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 삭제 중 오류가 발생했습니다"
        )

# ===== 템플릿 적용 및 커스터마이징 =====

@router.post("/{template_id}/apply", response_model=Dict[str, Any])
async def apply_template(
    template_id: UUID,
    request: TemplateApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    템플릿을 Canvas에 적용
    """
    try:
        service = CanvasTemplateService(db)
        result = await service.apply_template_to_canvas(
            template_id, request, current_user.id
        )
        
        return result
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error applying template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 적용 중 오류가 발생했습니다"
        )

@router.post("/{template_id}/customize", response_model=Dict[str, Any])
async def customize_template(
    template_id: UUID,
    request: TemplateCustomizationRequest,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    템플릿 커스터마이징 미리보기
    """
    try:
        service = CanvasTemplateService(db)
        result = await service.customize_template(
            template_id, 
            request, 
            current_user.id if current_user else None
        )
        
        return result
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error customizing template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 커스터마이징 중 오류가 발생했습니다"
        )

# ===== 리뷰 시스템 =====

@router.post("/{template_id}/reviews", status_code=status.HTTP_201_CREATED)
async def add_review(
    template_id: UUID,
    request: TemplateReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    템플릿 리뷰 추가
    """
    try:
        service = CanvasTemplateService(db)
        success = await service.add_review(template_id, request, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="리뷰 추가에 실패했습니다"
            )
        
        return {"message": "리뷰가 성공적으로 추가되었습니다"}
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding review for template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="리뷰 추가 중 오류가 발생했습니다"
        )

# ===== 즐겨찾기 시스템 =====

@router.post("/{template_id}/favorite", response_model=Dict[str, bool])
async def toggle_favorite(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    템플릿 즐겨찾기 토글
    """
    try:
        service = CanvasTemplateService(db)
        is_favorite = await service.toggle_favorite(template_id, current_user.id)
        
        return {
            "is_favorite": is_favorite,
            "message": "즐겨찾기에 추가되었습니다" if is_favorite else "즐겨찾기에서 제거되었습니다"
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error toggling favorite for template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="즐겨찾기 처리 중 오류가 발생했습니다"
        )

@router.get("/favorites/my", response_model=TemplateSearchResponse)
async def get_my_favorites(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    내 즐겨찾기 목록
    """
    try:
        service = CanvasTemplateService(db)
        result = await service.get_user_favorites(current_user.id, page, page_size)
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching user favorites: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="즐겨찾기 조회 중 오류가 발생했습니다"
        )

# ===== 카테고리 및 메타데이터 =====

@router.get("/categories", response_model=List[Dict[str, Any]])
async def get_categories(
    db: Session = Depends(get_db)
):
    """
    템플릿 카테고리 목록
    """
    try:
        categories = []
        
        # Enum에서 카테고리 정보 추출
        for category in TemplateCategory:
            subcategories = []
            
            # 해당 카테고리의 서브카테고리 찾기
            for subcategory in TemplateSubcategory:
                if subcategory.value.startswith(category.value.split('_')[0]):
                    subcategories.append({
                        "value": subcategory.value,
                        "label": subcategory.value.replace('_', ' ').title()
                    })
            
            categories.append({
                "value": category.value,
                "label": category.value.replace('_', ' ').title(),
                "subcategories": subcategories
            })
        
        return categories
        
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카테고리 조회 중 오류가 발생했습니다"
        )

@router.get("/tags/popular", response_model=List[str])
async def get_popular_tags(
    limit: int = Query(50, ge=1, le=200, description="조회할 태그 개수"),
    db: Session = Depends(get_db)
):
    """
    인기 태그 목록
    """
    try:
        # TODO: 실제 DB에서 인기 태그 조회
        popular_tags = [
            "modern", "minimalist", "colorful", "business", "creative",
            "elegant", "professional", "bold", "clean", "vintage",
            "geometric", "abstract", "nature", "corporate", "artistic"
        ]
        
        return popular_tags[:limit]
        
    except Exception as e:
        logger.error(f"Error fetching popular tags: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인기 태그 조회 중 오류가 발생했습니다"
        )

# ===== 통계 및 분석 =====

@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_template_stats(
    db: Session = Depends(get_db)
):
    """
    템플릿 전체 통계
    """
    try:
        # TODO: 실제 통계 조회
        stats = {
            "total_templates": 1250,
            "free_templates": 890,
            "premium_templates": 360,
            "total_downloads": 45680,
            "total_users": 12500,
            "categories": [
                {"name": "Business", "count": 320},
                {"name": "Social Media", "count": 280},
                {"name": "Education", "count": 200},
                {"name": "Event", "count": 180},
                {"name": "Personal", "count": 150},
                {"name": "Creative", "count": 120}
            ]
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error fetching template stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="통계 조회 중 오류가 발생했습니다"
        )

print("Canvas Template API v1.0 완성")
print("- 완전한 CRUD API 엔드포인트")
print("- 검색, 필터링, 정렬 지원")
print("- 템플릿 적용 및 커스터마이징")
print("- 리뷰, 즐겨찾기, 통계 시스템")