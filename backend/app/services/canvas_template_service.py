# Canvas Template Service
# AIPortal Canvas Template Library - 핵심 비즈니스 로직

import uuid
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func, text
from sqlalchemy.dialects.postgresql import insert

from app.db.models.canvas_template import (
    CanvasTemplate, TemplateReview, TemplateFavorite, TemplateCollection,
    TemplateCollectionItem, TemplateUsageLog, TemplateCustomizationPreset,
    TemplateAnalytics, TemplateLicenseAgreement, TemplateCategory as DBTemplateCategory,
    TemplateTag
)
from app.models.template_models import (
    TemplateCreateRequest, TemplateUpdateRequest, TemplateSearchRequest,
    TemplateApplyRequest, TemplateCustomizationRequest, TemplateReviewRequest,
    CollectionCreateRequest, CollectionUpdateRequest, CustomizationPresetRequest,
    TemplateResponse, TemplateDetailResponse, TemplateSearchResponse,
    TemplateAnalyticsResponse, SortBy, TemplateStatus, LicenseType
)
from app.services.canvas_service import CanvasService
from app.core.exceptions import NotFoundError, ValidationError, PermissionError
import logging

logger = logging.getLogger(__name__)

class CanvasTemplateService:
    """Canvas Template 핵심 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.canvas_service = CanvasService(db)
    
    # ===== 템플릿 CRUD =====
    
    async def create_template(
        self, 
        request: TemplateCreateRequest, 
        user_id: UUID,
        canvas_id: Optional[UUID] = None
    ) -> TemplateDetailResponse:
        """
        새로운 템플릿 생성
        """
        try:
            # Canvas 데이터에서 자동으로 메타데이터 추출
            canvas_metadata = await self._extract_canvas_metadata(request.canvas_data)
            
            # 템플릿 생성
            template = CanvasTemplate(
                name=request.name,
                description=request.description,
                keywords=request.keywords or [],
                category=request.category.value,
                subcategory=request.subcategory.value,
                tags=request.tags or [],
                status=TemplateStatus.DRAFT.value,
                is_public=request.is_public,
                canvas_data=request.canvas_data,
                thumbnail_url=request.thumbnail_url,
                preview_images=request.preview_images or [],
                customizable_elements=[elem.dict() for elem in request.customizable_elements] if request.customizable_elements else [],
                color_palettes=[palette.dict() for palette in request.color_palettes] if request.color_palettes else [],
                font_suggestions=request.font_suggestions or [],
                dimensions=request.dimensions.dict(),
                aspect_ratio=request.aspect_ratio,
                orientation=request.orientation,
                difficulty_level=request.difficulty_level.value,
                license_type=request.license_type.value,
                license_details=request.license_details.dict() if request.license_details else {},
                commercial_usage=request.license_details.commercial_usage if request.license_details else False,
                attribution_required=request.license_details.attribution_required if request.license_details else False,
                created_by=user_id,
                **canvas_metadata
            )
            
            self.db.add(template)
            self.db.commit()
            self.db.refresh(template)
            
            # 자동 썸네일 생성 (백그라운드)
            if not request.thumbnail_url:
                asyncio.create_task(self._generate_thumbnail(template.id))
            
            # 사용 로그 기록
            await self._log_template_usage(template.id, user_id, "create")
            
            logger.info(f"Template created: {template.id} by user {user_id}")
            
            return await self._build_template_detail_response(template)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create template: {str(e)}")
            raise ValidationError(f"템플릿 생성에 실패했습니다: {str(e)}")
    
    async def get_template(self, template_id: UUID, user_id: Optional[UUID] = None) -> TemplateDetailResponse:
        """
        템플릿 상세 조회
        """
        template = self.db.query(CanvasTemplate).filter(
            CanvasTemplate.id == template_id,
            or_(
                CanvasTemplate.is_public == True,
                CanvasTemplate.created_by == user_id if user_id else False
            )
        ).first()
        
        if not template:
            raise NotFoundError("템플릿을 찾을 수 없습니다")
        
        # 조회수 증가 (백그라운드)
        asyncio.create_task(self._increment_view_count(template_id))
        
        # 사용 로그 기록 (백그라운드)
        if user_id:
            asyncio.create_task(self._log_template_usage(template_id, user_id, "view"))
        
        return await self._build_template_detail_response(template)
    
    async def update_template(
        self, 
        template_id: UUID, 
        request: TemplateUpdateRequest, 
        user_id: UUID
    ) -> TemplateDetailResponse:
        """
        템플릿 수정
        """
        template = self.db.query(CanvasTemplate).filter(
            CanvasTemplate.id == template_id,
            CanvasTemplate.created_by == user_id
        ).first()
        
        if not template:
            raise NotFoundError("템플릿을 찾을 수 없거나 수정 권한이 없습니다")
        
        try:
            # 업데이트할 필드만 선택적으로 적용
            update_data = request.dict(exclude_unset=True)
            
            for field, value in update_data.items():
                if field == "customizable_elements" and value:
                    value = [elem.dict() for elem in value]
                elif field == "color_palettes" and value:
                    value = [palette.dict() for palette in value]
                elif field == "dimensions" and value:
                    value = value.dict()
                elif field == "license_details" and value:
                    value = value.dict()
                
                setattr(template, field, value)
            
            # Canvas 데이터가 변경된 경우 메타데이터 재추출
            if "canvas_data" in update_data:
                canvas_metadata = await self._extract_canvas_metadata(template.canvas_data)
                for field, value in canvas_metadata.items():
                    setattr(template, field, value)
                
                # 썸네일 재생성 (백그라운드)
                asyncio.create_task(self._generate_thumbnail(template_id))
            
            template.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(template)
            
            logger.info(f"Template updated: {template_id} by user {user_id}")
            
            return await self._build_template_detail_response(template)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update template: {str(e)}")
            raise ValidationError(f"템플릿 수정에 실패했습니다: {str(e)}")
    
    async def delete_template(self, template_id: UUID, user_id: UUID) -> bool:
        """
        템플릿 삭제
        """
        template = self.db.query(CanvasTemplate).filter(
            CanvasTemplate.id == template_id,
            CanvasTemplate.created_by == user_id
        ).first()
        
        if not template:
            raise NotFoundError("템플릿을 찾을 수 없거나 삭제 권한이 없습니다")
        
        try:
            # 소프트 삭제 (아카이브)
            template.is_archived = True
            template.is_public = False
            template.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Template archived: {template_id} by user {user_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete template: {str(e)}")
            return False
    
    # ===== 템플릿 검색 및 브라우징 =====
    
    async def search_templates(
        self, 
        request: TemplateSearchRequest,
        user_id: Optional[UUID] = None
    ) -> TemplateSearchResponse:
        """
        템플릿 검색
        """
        query = self.db.query(CanvasTemplate).filter(
            CanvasTemplate.is_public == True,
            CanvasTemplate.is_archived == False,
            CanvasTemplate.status.in_([TemplateStatus.APPROVED.value, TemplateStatus.FEATURED.value])
        )
        
        # 검색 키워드 적용
        if request.query:
            search_filter = or_(
                CanvasTemplate.name.ilike(f"%{request.query}%"),
                CanvasTemplate.description.ilike(f"%{request.query}%"),
                CanvasTemplate.keywords.op('&&')(f'{{{request.query}}}')
            )
            query = query.filter(search_filter)
        
        # 필터링 적용
        if request.category:
            query = query.filter(CanvasTemplate.category == request.category.value)
        
        if request.subcategory:
            query = query.filter(CanvasTemplate.subcategory == request.subcategory.value)
        
        if request.tags:
            for tag in request.tags:
                query = query.filter(CanvasTemplate.tags.op('&&')(f'{{{tag}}}'))
        
        if request.license_type:
            query = query.filter(CanvasTemplate.license_type == request.license_type.value)
        
        if request.difficulty_level:
            query = query.filter(CanvasTemplate.difficulty_level == request.difficulty_level.value)
        
        if request.is_featured is not None:
            query = query.filter(CanvasTemplate.is_featured == request.is_featured)
        
        if request.min_rating:
            query = query.filter(CanvasTemplate.average_rating >= request.min_rating)
        
        if request.created_after:
            query = query.filter(CanvasTemplate.created_at >= request.created_after)
        
        if request.created_before:
            query = query.filter(CanvasTemplate.created_at <= request.created_before)
        
        # 정렬 적용
        if request.sort_by == SortBy.CREATED_DESC:
            query = query.order_by(desc(CanvasTemplate.created_at))
        elif request.sort_by == SortBy.CREATED_ASC:
            query = query.order_by(asc(CanvasTemplate.created_at))
        elif request.sort_by == SortBy.UPDATED_DESC:
            query = query.order_by(desc(CanvasTemplate.updated_at))
        elif request.sort_by == SortBy.RATING_DESC:
            query = query.order_by(desc(CanvasTemplate.average_rating))
        elif request.sort_by == SortBy.USAGE_DESC:
            query = query.order_by(desc(CanvasTemplate.usage_count))
        elif request.sort_by == SortBy.NAME_ASC:
            query = query.order_by(asc(CanvasTemplate.name))
        elif request.sort_by == SortBy.NAME_DESC:
            query = query.order_by(desc(CanvasTemplate.name))
        
        # 전체 개수 조회
        total = query.count()
        
        # 페이지네이션 적용
        offset = (request.page - 1) * request.page_size
        templates = query.offset(offset).limit(request.page_size).all()
        
        # 응답 빌드
        template_responses = []
        for template in templates:
            response = await self._build_template_response(template)
            template_responses.append(response)
        
        total_pages = (total + request.page_size - 1) // request.page_size
        
        return TemplateSearchResponse(
            templates=template_responses,
            total=total,
            page=request.page,
            page_size=request.page_size,
            total_pages=total_pages,
            has_next=request.page < total_pages,
            has_prev=request.page > 1
        )
    
    async def get_featured_templates(self, limit: int = 20) -> List[TemplateResponse]:
        """
        추천 템플릿 목록
        """
        templates = self.db.query(CanvasTemplate).filter(
            CanvasTemplate.is_public == True,
            CanvasTemplate.is_archived == False,
            CanvasTemplate.is_featured == True,
            CanvasTemplate.status == TemplateStatus.FEATURED.value
        ).order_by(desc(CanvasTemplate.average_rating)).limit(limit).all()
        
        responses = []
        for template in templates:
            response = await self._build_template_response(template)
            responses.append(response)
        
        return responses
    
    async def get_trending_templates(self, limit: int = 20, days: int = 7) -> List[TemplateResponse]:
        """
        트렌딩 템플릿 목록 (최근 N일 기준)
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # 최근 사용량 기준으로 트렌딩 계산
        trending_subquery = self.db.query(
            TemplateUsageLog.template_id,
            func.count(TemplateUsageLog.id).label('recent_usage')
        ).filter(
            TemplateUsageLog.created_at >= since_date,
            TemplateUsageLog.usage_type.in_(['view', 'download', 'apply'])
        ).group_by(TemplateUsageLog.template_id).subquery()
        
        templates = self.db.query(CanvasTemplate).join(
            trending_subquery,
            CanvasTemplate.id == trending_subquery.c.template_id
        ).filter(
            CanvasTemplate.is_public == True,
            CanvasTemplate.is_archived == False,
            CanvasTemplate.status.in_([TemplateStatus.APPROVED.value, TemplateStatus.FEATURED.value])
        ).order_by(desc(trending_subquery.c.recent_usage)).limit(limit).all()
        
        responses = []
        for template in templates:
            response = await self._build_template_response(template)
            responses.append(response)
        
        return responses
    
    # ===== 템플릿 적용 =====
    
    async def apply_template_to_canvas(
        self, 
        template_id: UUID, 
        request: TemplateApplyRequest,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        템플릿을 Canvas에 적용
        """
        # 템플릿 조회
        template = await self.get_template(template_id, user_id)
        
        # 라이선스 확인
        license_valid = await self._check_license(template_id, user_id)
        if not license_valid:
            raise PermissionError("템플릿 사용 권한이 없습니다")
        
        try:
            # Canvas 데이터 복사
            canvas_data = json.deepcopy(template.canvas_data)
            
            # 커스터마이징 적용
            if request.customizations:
                canvas_data = await self._apply_customizations(
                    canvas_data, 
                    request.customizations,
                    template.customizable_elements
                )
            
            # 프리셋 적용
            if request.preset_id:
                preset = self.db.query(TemplateCustomizationPreset).filter(
                    TemplateCustomizationPreset.id == request.preset_id,
                    TemplateCustomizationPreset.template_id == template_id
                ).first()
                
                if preset:
                    canvas_data = await self._apply_customizations(
                        canvas_data,
                        preset.customization_config,
                        template.customizable_elements
                    )
            
            # Canvas에 적용
            success = await self.canvas_service.update_canvas_data(
                request.canvas_id,
                canvas_data,
                user_id
            )
            
            if success:
                # 사용 로그 기록
                await self._log_template_usage(template_id, user_id, "apply", {
                    "canvas_id": str(request.canvas_id),
                    "customizations": request.customizations,
                    "preset_id": str(request.preset_id) if request.preset_id else None
                })
                
                # 사용량 통계 업데이트 (백그라운드)
                asyncio.create_task(self._increment_usage_count(template_id))
                
                logger.info(f"Template {template_id} applied to canvas {request.canvas_id} by user {user_id}")
                
                return {
                    "success": True,
                    "canvas_data": canvas_data,
                    "message": "템플릿이 성공적으로 적용되었습니다"
                }
            else:
                raise ValidationError("Canvas 적용에 실패했습니다")
                
        except Exception as e:
            logger.error(f"Failed to apply template: {str(e)}")
            raise ValidationError(f"템플릿 적용에 실패했습니다: {str(e)}")
    
    async def customize_template(
        self,
        template_id: UUID,
        request: TemplateCustomizationRequest,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        템플릿 커스터마이징 미리보기
        """
        template = await self.get_template(template_id, user_id)
        
        try:
            # Canvas 데이터 복사
            canvas_data = json.deepcopy(template.canvas_data)
            
            # 커스터마이징 적용
            canvas_data = await self._apply_customizations(
                canvas_data,
                request.customizations,
                template.customizable_elements
            )
            
            return {
                "success": True,
                "canvas_data": canvas_data,
                "customizations": request.customizations
            }
            
        except Exception as e:
            logger.error(f"Failed to customize template: {str(e)}")
            raise ValidationError(f"템플릿 커스터마이징에 실패했습니다: {str(e)}")
    
    # ===== 리뷰 시스템 =====
    
    async def add_review(
        self,
        template_id: UUID,
        request: TemplateReviewRequest,
        user_id: UUID
    ) -> bool:
        """
        템플릿 리뷰 추가
        """
        # 중복 리뷰 확인
        existing_review = self.db.query(TemplateReview).filter(
            TemplateReview.template_id == template_id,
            TemplateReview.user_id == user_id
        ).first()
        
        if existing_review:
            raise ValidationError("이미 이 템플릿에 리뷰를 작성했습니다")
        
        try:
            review = TemplateReview(
                template_id=template_id,
                user_id=user_id,
                rating=request.rating,
                title=request.title,
                comment=request.comment,
                is_recommended=request.is_recommended,
                review_categories=request.review_categories or []
            )
            
            self.db.add(review)
            self.db.commit()
            
            # 템플릿 평균 평점 업데이트 (백그라운드)
            asyncio.create_task(self._update_template_rating(template_id))
            
            logger.info(f"Review added for template {template_id} by user {user_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add review: {str(e)}")
            return False
    
    # ===== 즐겨찾기 시스템 =====
    
    async def toggle_favorite(self, template_id: UUID, user_id: UUID) -> bool:
        """
        템플릿 즐겨찾기 토글
        """
        existing_favorite = self.db.query(TemplateFavorite).filter(
            TemplateFavorite.template_id == template_id,
            TemplateFavorite.user_id == user_id
        ).first()
        
        try:
            if existing_favorite:
                # 즐겨찾기 해제
                self.db.delete(existing_favorite)
                self.db.commit()
                return False
            else:
                # 즐겨찾기 추가
                favorite = TemplateFavorite(
                    template_id=template_id,
                    user_id=user_id
                )
                self.db.add(favorite)
                self.db.commit()
                return True
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to toggle favorite: {str(e)}")
            raise ValidationError("즐겨찾기 처리에 실패했습니다")
    
    async def get_user_favorites(self, user_id: UUID, page: int = 1, page_size: int = 20) -> TemplateSearchResponse:
        """
        사용자 즐겨찾기 목록
        """
        query = self.db.query(CanvasTemplate).join(
            TemplateFavorite,
            CanvasTemplate.id == TemplateFavorite.template_id
        ).filter(
            TemplateFavorite.user_id == user_id
        ).order_by(desc(TemplateFavorite.created_at))
        
        total = query.count()
        offset = (page - 1) * page_size
        templates = query.offset(offset).limit(page_size).all()
        
        template_responses = []
        for template in templates:
            response = await self._build_template_response(template)
            template_responses.append(response)
        
        total_pages = (total + page_size - 1) // page_size
        
        return TemplateSearchResponse(
            templates=template_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    
    # ===== 내부 헬퍼 메서드 =====
    
    async def _extract_canvas_metadata(self, canvas_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Canvas 데이터에서 메타데이터 추출
        """
        metadata = {}
        
        # Stage 설정에서 치수 추출
        if 'stage' in canvas_data:
            stage = canvas_data['stage']
            if 'width' in stage and 'height' in stage:
                width = stage['width']
                height = stage['height']
                
                # 화면비 계산
                gcd_val = self._gcd(width, height)
                aspect_ratio = f"{width // gcd_val}:{height // gcd_val}"
                
                # 방향 결정
                if width > height:
                    orientation = "landscape"
                elif height > width:
                    orientation = "portrait"
                else:
                    orientation = "square"
                
                metadata.update({
                    'aspect_ratio': aspect_ratio,
                    'orientation': orientation
                })
        
        return metadata
    
    def _gcd(self, a: int, b: int) -> int:
        """최대공약수 계산"""
        while b:
            a, b = b, a % b
        return a
    
    async def _generate_thumbnail(self, template_id: UUID) -> None:
        """
        템플릿 썸네일 생성 (백그라운드 작업)
        """
        try:
            # TODO: Canvas 데이터를 이미지로 렌더링하여 썸네일 생성
            # Puppeteer 또는 유사한 도구 사용
            pass
        except Exception as e:
            logger.error(f"Failed to generate thumbnail for template {template_id}: {str(e)}")
    
    async def _apply_customizations(
        self,
        canvas_data: Dict[str, Any],
        customizations: Dict[str, Any],
        customizable_elements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Canvas 데이터에 커스터마이징 적용
        """
        try:
            for element in customizable_elements:
                element_id = element.get('element_id')
                element_type = element.get('element_type')
                
                if element_id in customizations:
                    custom_value = customizations[element_id]
                    
                    # Canvas 데이터에서 해당 요소 찾아서 업데이트
                    canvas_data = self._update_canvas_element(
                        canvas_data, 
                        element_id, 
                        custom_value,
                        element_type
                    )
            
            return canvas_data
            
        except Exception as e:
            logger.error(f"Failed to apply customizations: {str(e)}")
            raise ValidationError(f"커스터마이징 적용에 실패했습니다: {str(e)}")
    
    def _update_canvas_element(
        self,
        canvas_data: Dict[str, Any],
        element_id: str,
        new_value: Any,
        element_type: str
    ) -> Dict[str, Any]:
        """
        Canvas 데이터에서 특정 요소 업데이트
        """
        # TODO: Konva JSON 구조에서 특정 요소 찾아서 업데이트
        # 재귀적으로 layers -> nodes 탐색하여 element_id 매칭
        
        def update_recursive(obj, target_id, value):
            if isinstance(obj, dict):
                if obj.get('id') == target_id:
                    # 요소 타입에 따른 업데이트
                    if element_type == 'text':
                        obj['text'] = value
                    elif element_type == 'color':
                        obj['fill'] = value
                    elif element_type == 'image':
                        obj['src'] = value
                    # ... 더 많은 커스터마이징 타입
                    return True
                
                for key, val in obj.items():
                    if update_recursive(val, target_id, value):
                        return True
            
            elif isinstance(obj, list):
                for item in obj:
                    if update_recursive(item, target_id, value):
                        return True
            
            return False
        
        update_recursive(canvas_data, element_id, new_value)
        return canvas_data
    
    async def _log_template_usage(
        self,
        template_id: UUID,
        user_id: Optional[UUID],
        usage_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        템플릿 사용 로그 기록
        """
        try:
            log = TemplateUsageLog(
                template_id=template_id,
                user_id=user_id,
                usage_type=usage_type,
                customization_data=metadata or {},
                session_id=str(uuid.uuid4())  # 임시 세션 ID
            )
            
            self.db.add(log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log template usage: {str(e)}")
    
    async def _increment_view_count(self, template_id: UUID) -> None:
        """
        템플릿 조회수 증가
        """
        try:
            self.db.execute(
                text("UPDATE canvas_templates SET view_count = view_count + 1 WHERE id = :template_id"),
                {"template_id": str(template_id)}
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to increment view count: {str(e)}")
    
    async def _increment_usage_count(self, template_id: UUID) -> None:
        """
        템플릿 사용량 증가
        """
        try:
            self.db.execute(
                text("UPDATE canvas_templates SET usage_count = usage_count + 1 WHERE id = :template_id"),
                {"template_id": str(template_id)}
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to increment usage count: {str(e)}")
    
    async def _update_template_rating(self, template_id: UUID) -> None:
        """
        템플릿 평균 평점 업데이트
        """
        try:
            result = self.db.query(
                func.avg(TemplateReview.rating).label('avg_rating'),
                func.count(TemplateReview.id).label('rating_count')
            ).filter(
                TemplateReview.template_id == template_id
            ).first()
            
            if result and result.rating_count > 0:
                self.db.execute(
                    text("""
                        UPDATE canvas_templates 
                        SET average_rating = :avg_rating, rating_count = :rating_count 
                        WHERE id = :template_id
                    """),
                    {
                        "avg_rating": float(result.avg_rating),
                        "rating_count": result.rating_count,
                        "template_id": str(template_id)
                    }
                )
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Failed to update template rating: {str(e)}")
    
    async def _check_license(self, template_id: UUID, user_id: UUID) -> bool:
        """
        템플릿 라이선스 확인
        """
        template = self.db.query(CanvasTemplate).filter(
            CanvasTemplate.id == template_id
        ).first()
        
        if not template:
            return False
        
        # 무료 템플릿인 경우
        if template.license_type == LicenseType.FREE.value:
            return True
        
        # 프리미엄 템플릿인 경우 라이선스 동의 확인
        license_agreement = self.db.query(TemplateLicenseAgreement).filter(
            TemplateLicenseAgreement.template_id == template_id,
            TemplateLicenseAgreement.user_id == user_id,
            TemplateLicenseAgreement.is_active == True,
            or_(
                TemplateLicenseAgreement.expires_at.is_(None),
                TemplateLicenseAgreement.expires_at > datetime.utcnow()
            )
        ).first()
        
        return license_agreement is not None
    
    async def _build_template_response(self, template: CanvasTemplate) -> TemplateResponse:
        """
        템플릿 기본 응답 빌드
        """
        # TODO: 실제 사용자 정보 조회
        creator = {
            "id": template.created_by,
            "username": f"user_{str(template.created_by)[:8]}",
            "display_name": None,
            "avatar_url": None,
            "is_verified": False
        }
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            keywords=template.keywords,
            category=template.category,
            subcategory=template.subcategory,
            tags=template.tags,
            status=template.status,
            is_public=template.is_public,
            is_featured=template.is_featured,
            thumbnail_url=template.thumbnail_url,
            preview_images=template.preview_images,
            dimensions=template.dimensions,
            aspect_ratio=template.aspect_ratio,
            orientation=template.orientation,
            difficulty_level=template.difficulty_level,
            license_type=template.license_type,
            stats={
                "view_count": template.view_count,
                "download_count": template.download_count,
                "usage_count": template.usage_count,
                "average_rating": template.average_rating,
                "rating_count": template.rating_count
            },
            creator=creator,
            created_at=template.created_at,
            updated_at=template.updated_at,
            published_at=template.published_at
        )
    
    async def _build_template_detail_response(self, template: CanvasTemplate) -> TemplateDetailResponse:
        """
        템플릿 상세 응답 빌드
        """
        base_response = await self._build_template_response(template)
        
        return TemplateDetailResponse(
            **base_response.dict(),
            canvas_data=template.canvas_data,
            customizable_elements=template.customizable_elements,
            color_palettes=template.color_palettes,
            font_suggestions=template.font_suggestions,
            license_details=template.license_details,
            version=template.version,
            parent_template_id=template.parent_template_id
        )

print("Canvas Template Service v1.0 완성")
print("- 완전한 CRUD 및 검색 시스템")
print("- 템플릿 적용 및 커스터마이징")
print("- 리뷰 및 즐겨찾기 시스템")
print("- 라이선스 관리 및 사용량 추적")