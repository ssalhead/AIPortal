"""
이미지 시리즈 생성 및 관리 서비스

연속성 있는 이미지 시리즈를 생성하고 관리하는 핵심 서비스
- 시리즈 생성 및 진행 관리
- 연속성 유지 알고리즘
- 프롬프트 체이닝 시스템
- 일괄 생성 큐 관리
- 템플릿 기반 시리즈 생성
"""

import asyncio
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.db.models.image_series import ImageSeries, SeriesTemplate
from app.db.models.image_history import ImageHistory
from app.services.image_generation_service import ImageGenerationService
from app.services.simple_image_history_service import SimpleImageHistoryService
from app.db.session import get_db

logger = logging.getLogger(__name__)


class ImageSeriesService:
    """이미지 시리즈 생성 및 관리 서비스"""
    
    def __init__(self):
        self.image_generation_service = ImageGenerationService()
        self.image_history_service = SimpleImageHistoryService()
        
        # 시리즈 템플릿 설정
        self.series_templates = {
            "webtoon": {
                "name": "웹툰 페이지",
                "template_config": {
                    "layout": "vertical_panels",
                    "aspect_ratio": "3:4",
                    "panel_count": [1, 2, 3, 4],
                    "style_consistency": "high"
                },
                "consistency_rules": {
                    "character_consistency": True,
                    "background_consistency": True,
                    "color_palette": True,
                    "art_style": True
                },
                "prompt_templates": [
                    "Panel {index}: {scene_description}. Webtoon style, consistent character design, {art_style}",
                    "Comic panel {index} of {total}: {scene_description}. Maintain character appearance and art style"
                ]
            },
            "instagram": {
                "name": "인스타그램 캐러셀",
                "template_config": {
                    "layout": "square_grid",
                    "aspect_ratio": "1:1",
                    "slide_count": [3, 4, 5, 6],
                    "style_consistency": "medium"
                },
                "consistency_rules": {
                    "color_palette": True,
                    "brand_consistency": True,
                    "typography_style": True
                },
                "prompt_templates": [
                    "Instagram post {index}/{total}: {content}. Modern social media style, consistent branding",
                    "Social media carousel slide {index}: {content}. Cohesive visual design"
                ]
            },
            "brand": {
                "name": "브랜드 시리즈",
                "template_config": {
                    "layout": "flexible",
                    "aspect_ratio": "flexible",
                    "brand_elements": ["logo", "colors", "typography"],
                    "style_consistency": "very_high"
                },
                "consistency_rules": {
                    "brand_colors": True,
                    "logo_placement": True,
                    "typography": True,
                    "style_guide": True
                },
                "prompt_templates": [
                    "Brand asset {index}: {description}. Corporate style, consistent brand identity",
                    "Marketing material {index}/{total}: {description}. Professional brand design"
                ]
            },
            "educational": {
                "name": "교육용 단계별",
                "template_config": {
                    "layout": "step_by_step",
                    "aspect_ratio": "16:9",
                    "step_indicators": True,
                    "style_consistency": "high"
                },
                "consistency_rules": {
                    "diagram_style": True,
                    "color_coding": True,
                    "typography": True,
                    "layout_consistency": True
                },
                "prompt_templates": [
                    "Educational step {index}: {instruction}. Clear diagram style, consistent visual design",
                    "Tutorial slide {index} of {total}: {instruction}. Instructional design, step-by-step visual"
                ]
            },
            "story": {
                "name": "스토리보드",
                "template_config": {
                    "layout": "cinematic",
                    "aspect_ratio": "16:9",
                    "scene_progression": True,
                    "style_consistency": "very_high"
                },
                "consistency_rules": {
                    "character_consistency": True,
                    "location_consistency": True,
                    "lighting_consistency": True,
                    "camera_style": True
                },
                "prompt_templates": [
                    "Storyboard frame {index}: {scene}. Cinematic style, consistent characters and setting",
                    "Scene {index} of {total}: {scene}. Film storyboard style, maintain visual continuity"
                ]
            }
        }
    
    async def create_series(
        self,
        db: Session,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        series_type: str,
        target_count: int = 4,
        base_style: str = "realistic",
        consistency_prompt: Optional[str] = None,
        template_id: Optional[uuid.UUID] = None,
        custom_config: Optional[Dict] = None
    ) -> ImageSeries:
        """새 이미지 시리즈 생성"""
        
        logger.info(f"Creating new image series: {title} ({series_type})")
        
        # 템플릿 설정 로드
        template_config = {}
        if template_id:
            template = db.query(SeriesTemplate).filter(SeriesTemplate.id == template_id).first()
            if template:
                template_config = template.template_config
                template.increment_usage()
        elif series_type in self.series_templates:
            template_config = self.series_templates[series_type]["template_config"]
        
        # 커스텀 설정 병합
        if custom_config:
            template_config.update(custom_config)
        
        # 시리즈 생성
        series = ImageSeries.create_series(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
            series_type=series_type,
            target_count=target_count,
            base_style=base_style,
            template_config=template_config,
            consistency_prompt=consistency_prompt
        )
        
        db.add(series)
        db.commit()
        db.refresh(series)
        
        logger.info(f"Image series created successfully: {series.id}")
        return series
    
    async def generate_series_prompts(
        self,
        series: ImageSeries,
        base_prompts: List[str],
        character_descriptions: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """시리즈용 프롬프트 체이닝 생성"""
        
        logger.info(f"Generating prompts for series: {series.id}")
        
        # 캐릭터 설명 저장
        if character_descriptions:
            for name, desc in character_descriptions.items():
                series.set_character_description(name, desc)
        
        # 프롬프트 템플릿 가져오기
        series_config = self.series_templates.get(series.series_type, {})
        prompt_templates = series_config.get("prompt_templates", [])
        
        enhanced_prompts = []
        
        for i, base_prompt in enumerate(base_prompts):
            series_index = i + 1
            
            # 일관성 프롬프트 추가
            enhanced_prompt = series.build_consistency_prompt(base_prompt, series_index)
            
            # 템플릿 적용
            if prompt_templates:
                template = prompt_templates[i % len(prompt_templates)]
                template_prompt = template.format(
                    index=series_index,
                    total=len(base_prompts),
                    scene_description=base_prompt,
                    content=base_prompt,
                    description=base_prompt,
                    instruction=base_prompt,
                    scene=base_prompt,
                    art_style=series.base_style
                )
                enhanced_prompt = template_prompt
            
            enhanced_prompts.append(enhanced_prompt)
        
        # 생성 대기열에 추가
        series.add_to_queue(enhanced_prompts)
        
        logger.info(f"Generated {len(enhanced_prompts)} enhanced prompts")
        return enhanced_prompts
    
    async def generate_series_batch(
        self,
        db: Session,
        series_id: uuid.UUID,
        batch_size: int = 4
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """시리즈 일괄 생성 (스트리밍)"""
        
        series = db.query(ImageSeries).filter(ImageSeries.id == series_id).first()
        if not series:
            raise ValueError(f"Series not found: {series_id}")
        
        logger.info(f"Starting batch generation for series: {series.id}")
        series.completion_status = "generating"
        db.commit()
        
        try:
            generated_count = 0
            while generated_count < batch_size and series.generation_queue:
                # 대기열에서 프롬프트 가져오기
                next_prompt = series.pop_from_queue()
                if not next_prompt:
                    break
                
                series_index = series.next_series_index
                
                yield {
                    "status": "generating",
                    "series_id": str(series.id),
                    "current_index": series_index,
                    "total_count": series.target_count,
                    "prompt": next_prompt,
                    "progress": series.progress_percentage
                }
                
                try:
                    # 이미지 생성
                    generation_result = await self.image_generation_service.generate_image_async(
                        prompt=next_prompt,
                        style=series.base_style,
                        size="1024x1024"
                    )
                    
                    if generation_result["status"] == "completed" and generation_result["images"]:
                        image_url = generation_result["images"][0]
                        
                        # 이미지 히스토리에 저장
                        image_history = ImageHistory.create_from_generation(
                            conversation_id=series.conversation_id,
                            user_id=series.user_id,
                            prompt=next_prompt,
                            image_urls=[image_url],
                            style=series.base_style,
                            series_id=series.id,
                            series_index=series_index,
                            series_type=series.series_type,
                            series_metadata=series.template_metadata
                        )
                        
                        db.add(image_history)
                        
                        # 시리즈 진행 상황 업데이트
                        series.update_progress(1)
                        db.commit()
                        
                        generated_count += 1
                        
                        yield {
                            "status": "completed",
                            "series_id": str(series.id),
                            "image_id": str(image_history.id),
                            "image_url": image_url,
                            "series_index": series_index,
                            "progress": series.progress_percentage
                        }
                        
                    else:
                        # 생성 실패 처리
                        error_msg = generation_result.get("error", "Unknown error")
                        series.mark_generation_failed(next_prompt, error_msg)
                        db.commit()
                        
                        yield {
                            "status": "failed",
                            "series_id": str(series.id),
                            "series_index": series_index,
                            "error": error_msg,
                            "progress": series.progress_percentage
                        }
                        
                except Exception as e:
                    logger.error(f"Error generating image for series {series.id}: {str(e)}")
                    series.mark_generation_failed(next_prompt, str(e))
                    db.commit()
                    
                    yield {
                        "status": "failed",
                        "series_id": str(series.id),
                        "series_index": series_index,
                        "error": str(e),
                        "progress": series.progress_percentage
                    }
                
                # 짧은 지연 (API 레이트 리밋 고려)
                await asyncio.sleep(2)
            
            # 시리즈 완성 체크
            if series.is_completed:
                series.completion_status = "completed"
                db.commit()
                
                yield {
                    "status": "series_completed",
                    "series_id": str(series.id),
                    "total_generated": series.current_count,
                    "completion_time": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Batch generation failed for series {series.id}: {str(e)}")
            series.completion_status = "failed"
            db.commit()
            
            yield {
                "status": "series_failed",
                "series_id": str(series.id),
                "error": str(e)
            }
    
    async def get_series_images(
        self,
        db: Session,
        series_id: uuid.UUID,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """시리즈 이미지 목록 조회"""
        
        images = db.query(ImageHistory).filter(
            and_(
                ImageHistory.series_id == series_id,
                ImageHistory.is_active == True
            )
        ).order_by(ImageHistory.series_index).all()
        
        result = []
        for image in images:
            image_data = {
                "id": str(image.id),
                "image_url": image.primary_image_url,
                "series_index": image.series_index,
                "prompt": image.prompt,
                "status": image.status,
                "created_at": image.created_at.isoformat() if image.created_at else None
            }
            
            if include_metadata:
                image_data["metadata"] = image.generation_metadata
            
            result.append(image_data)
        
        return result
    
    async def get_series_progress(
        self,
        db: Session,
        series_id: uuid.UUID
    ) -> Dict[str, Any]:
        """시리즈 진행 상황 조회"""
        
        series = db.query(ImageSeries).filter(ImageSeries.id == series_id).first()
        if not series:
            raise ValueError(f"Series not found: {series_id}")
        
        return {
            "series_id": str(series.id),
            "title": series.title,
            "series_type": series.series_type,
            "current_count": series.current_count,
            "target_count": series.target_count,
            "progress_percentage": series.progress_percentage,
            "completion_status": series.completion_status,
            "queue_length": len(series.generation_queue) if series.generation_queue else 0,
            "failed_count": len(series.failed_generations) if series.failed_generations else 0,
            "created_at": series.created_at.isoformat() if series.created_at else None,
            "updated_at": series.updated_at.isoformat() if series.updated_at else None
        }
    
    async def create_series_template(
        self,
        db: Session,
        name: str,
        series_type: str,
        template_config: Dict[str, Any],
        prompt_templates: List[str],
        created_by: Optional[uuid.UUID] = None,
        description: Optional[str] = None
    ) -> SeriesTemplate:
        """새 시리즈 템플릿 생성"""
        
        template = SeriesTemplate(
            name=name,
            description=description,
            series_type=series_type,
            template_config=template_config,
            prompt_templates=prompt_templates,
            created_by=created_by,
            is_active=True,
            is_public=True
        )
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        logger.info(f"Series template created: {template.id}")
        return template
    
    async def get_available_templates(
        self,
        db: Session,
        series_type: Optional[str] = None,
        featured_only: bool = False
    ) -> List[Dict[str, Any]]:
        """사용 가능한 시리즈 템플릿 목록"""
        
        query = db.query(SeriesTemplate).filter(
            and_(
                SeriesTemplate.is_active == True,
                SeriesTemplate.is_public == True
            )
        )
        
        if series_type:
            query = query.filter(SeriesTemplate.series_type == series_type)
        
        if featured_only:
            query = query.filter(SeriesTemplate.is_featured == True)
        
        templates = query.order_by(desc(SeriesTemplate.rating), desc(SeriesTemplate.usage_count)).all()
        
        return [template.template_preview for template in templates]
    
    async def duplicate_series_as_template(
        self,
        db: Session,
        series_id: uuid.UUID,
        template_name: str,
        created_by: uuid.UUID
    ) -> SeriesTemplate:
        """완성된 시리즈를 템플릿으로 복제"""
        
        series = db.query(ImageSeries).filter(ImageSeries.id == series_id).first()
        if not series or not series.is_completed:
            raise ValueError("Series must be completed to create template")
        
        # 시리즈의 이미지들에서 프롬프트 템플릿 추출
        images = await self.get_series_images(db, series_id, include_metadata=False)
        prompt_templates = [img["prompt"] for img in images]
        
        template = await self.create_series_template(
            db=db,
            name=template_name,
            series_type=series.series_type,
            template_config=series.template_config,
            prompt_templates=prompt_templates,
            created_by=created_by,
            description=f"Based on series: {series.title}"
        )
        
        return template
    
    async def delete_series(
        self,
        db: Session,
        series_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """시리즈 삭제 (소프트 삭제)"""
        
        series = db.query(ImageSeries).filter(
            and_(
                ImageSeries.id == series_id,
                ImageSeries.user_id == user_id
            )
        ).first()
        
        if not series:
            return False
        
        # 시리즈 비활성화
        series.is_active = False
        
        # 관련 이미지들 소프트 삭제
        images = db.query(ImageHistory).filter(ImageHistory.series_id == series_id).all()
        for image in images:
            image.soft_delete()
        
        db.commit()
        logger.info(f"Series deleted: {series_id}")
        return True