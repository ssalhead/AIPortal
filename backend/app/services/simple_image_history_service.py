"""
단순화된 이미지 히스토리 서비스
conversationId 기반 통합 이미지 관리 시스템

기존 복잡한 ImageSessionService를 대체하는 단순하고 효율적인 서비스
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_
from sqlalchemy.orm import selectinload
import uuid
import hashlib
from datetime import datetime
import json

from app.db.models.image_history import ImageHistory
from app.db.models.conversation import Conversation
from app.services.image_generation_service import ImageGenerationService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SimpleImageHistoryService:
    """
    단순화된 이미지 히스토리 관리 서비스
    
    핵심 기능:
    1. conversationId 기반 이미지 히스토리 관리
    2. 선택된 이미지 기반 신규 이미지 생성
    3. 단방향 데이터 플로우
    4. 중복 방지 및 성능 최적화
    """
    
    def __init__(self):
        self.image_generation_service = ImageGenerationService()
    
    @staticmethod
    def safe_uuid_to_str(obj: Any) -> Any:
        """
        UUID 객체를 안전하게 문자열로 변환하는 재귀 함수
        딕셔너리, 리스트, UUID 등을 JSON 직렬화 가능한 형태로 변환
        """
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, dict):
            return {key: SimpleImageHistoryService.safe_uuid_to_str(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [SimpleImageHistoryService.safe_uuid_to_str(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj
    
    # ======= 핵심 CRUD 메서드 =======
    
    async def get_conversation_images(
        self, 
        db: AsyncSession, 
        conversation_id: uuid.UUID, 
        user_id: uuid.UUID,
        include_deleted: bool = False
    ) -> List[ImageHistory]:
        """대화의 모든 이미지 히스토리 조회 (생성 시간 역순)"""
        
        query = select(ImageHistory).where(
            and_(
                ImageHistory.conversation_id == conversation_id,
                ImageHistory.user_id == user_id
            )
        )
        
        # 삭제된 이미지 제외 (기본값)
        if not include_deleted:
            query = query.where(ImageHistory.is_deleted == False)
        
        # 생성 시간 역순 정렬 (최신순)
        query = query.order_by(desc(ImageHistory.created_at))
        
        # 부모-자식 관계 로딩 최적화
        query = query.options(selectinload(ImageHistory.parent_image))
        
        result = await db.execute(query)
        images = result.scalars().all()
        
        logger.debug(f"📋 대화 {conversation_id}의 이미지 히스토리 조회: {len(images)}개")
        return images
    
    async def get_selected_image(
        self, 
        db: AsyncSession, 
        conversation_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> Optional[ImageHistory]:
        """대화에서 현재 선택된 이미지 조회"""
        
        query = select(ImageHistory).where(
            and_(
                ImageHistory.conversation_id == conversation_id,
                ImageHistory.user_id == user_id,
                ImageHistory.is_selected == True,
                ImageHistory.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        selected = result.scalars().first()  # Multiple results 에러 방지를 위해 first() 사용
        
        if selected:
            logger.debug(f"🎯 선택된 이미지: {selected.id} (프롬프트: {selected.prompt[:50]}...)")
        else:
            logger.debug(f"❌ 대화 {conversation_id}에 선택된 이미지 없음")
            
        return selected
    
    async def save_generated_image(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        prompt: str,
        image_urls: List[str],
        style: str = "realistic",
        size: str = "1024x1024",
        parent_image_id: Optional[uuid.UUID] = None,
        evolution_type: Optional[str] = None,
        generation_params: Optional[Dict] = None,
        safety_score: float = 1.0,
        canvas_id: Optional[uuid.UUID] = None,
        canvas_version: int = 1,
        edit_mode: str = "CREATE",
        reference_image_id: Optional[uuid.UUID] = None
    ) -> ImageHistory:
        """생성된 이미지를 히스토리에 저장"""
        
        # 1. 새로운 히스토리 엔트리 생성 (안전한 UUID 처리 포함)
        safe_generation_params = self.safe_uuid_to_str(generation_params or {})
        
        image_history = ImageHistory.create_from_generation(
            conversation_id=conversation_id,
            user_id=user_id,
            prompt=prompt,
            image_urls=image_urls,
            style=style,
            size=size,
            parent_image_id=parent_image_id,
            evolution_type=evolution_type,
            generation_params=safe_generation_params,
            safety_score=safety_score,
            canvas_id=canvas_id,
            canvas_version=canvas_version,
            edit_mode=edit_mode,
            reference_image_id=reference_image_id
        )
        
        # 2. DB 저장 (향상된 오류 처리)
        try:
            db.add(image_history)
            await db.commit()
            await db.refresh(image_history)
            
            logger.info(f"💾 새 이미지 히스토리 저장: {image_history.id} (대화: {conversation_id})")
            return image_history
            
        except Exception as db_error:
            logger.error(f"❌ PostgreSQL 저장 오류: {type(db_error).__name__}: {db_error}")
            await db.rollback()
            
            # UUID 직렬화 오류 전용 처리
            if "Object of type UUID is not JSON serializable" in str(db_error):
                logger.error(f"🔍 UUID 직렬화 오류 발생 - generation_params 점검 필요")
                logger.error(f"📋 generation_params 내용: {generation_params}")
                raise ValueError("UUID serialization error in generation_params - check UUID conversion")
            
            raise db_error
    
    async def select_image(
        self,
        db: AsyncSession,
        image_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[ImageHistory]:
        """특정 이미지를 선택된 상태로 설정"""
        
        # 1. 이미지 조회 및 권한 확인
        query = select(ImageHistory).where(
            and_(
                ImageHistory.id == image_id,
                ImageHistory.user_id == user_id,
                ImageHistory.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        image = result.scalar_one_or_none()
        
        if not image:
            logger.warning(f"❌ 이미지를 찾을 수 없음: {image_id} (사용자: {user_id})")
            return None
        
        # 2. 선택 상태로 설정 (트리거가 다른 이미지들을 자동으로 해제함)
        image.mark_as_selected()
        await db.commit()
        await db.refresh(image)
        
        logger.info(f"🎯 이미지 선택: {image.id} (대화: {image.conversation_id})")
        return image
    
    async def delete_image(
        self,
        db: AsyncSession,
        image_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """이미지 소프트 삭제"""
        
        # 1. 이미지 조회 및 권한 확인
        query = select(ImageHistory).where(
            and_(
                ImageHistory.id == image_id,
                ImageHistory.user_id == user_id
            )
        )
        
        result = await db.execute(query)
        image = result.scalar_one_or_none()
        
        if not image:
            logger.warning(f"❌ 삭제할 이미지를 찾을 수 없음: {image_id}")
            return False
        
        # 2. 소프트 삭제 처리
        image.soft_delete()
        await db.commit()
        
        logger.info(f"🗑️ 이미지 삭제: {image.id} (대화: {image.conversation_id})")
        return True
    
    # ======= 고급 기능 메서드 =======
    
    async def generate_evolution_image(
        self,
        db: AsyncSession,
        parent_image_id: uuid.UUID,
        user_id: uuid.UUID,
        new_prompt: str,
        evolution_type: str = "modification",
        style: Optional[str] = None,
        size: Optional[str] = None
    ) -> Optional[ImageHistory]:
        """선택된 이미지를 기반으로 새로운 이미지 생성 (트랜잭션 안전성 보장)"""
        
        logger.info(f"🔄 진화 이미지 생성 시작: 부모={parent_image_id}, 사용자={user_id}")
        
        # 1. 부모 이미지 조회 및 검증 (Lock 적용)
        try:
            query = select(ImageHistory).where(
                and_(
                    ImageHistory.id == parent_image_id,
                    ImageHistory.user_id == user_id,
                    ImageHistory.is_deleted == False
                )
            ).with_for_update()  # Row-level lock 적용
            
            result = await db.execute(query)
            parent_image = result.scalar_one_or_none()
            
            if not parent_image:
                logger.error(f"❌ 부모 이미지를 찾을 수 없음: {parent_image_id} (사용자: {user_id})")
                return None
            
            logger.debug(f"✅ 부모 이미지 확인: {parent_image.id}, 프롬프트='{parent_image.prompt[:50]}...'")
            
            # 2. 중복 진화 이미지 검증 (같은 parent + prompt + evolution_type 조합)
            duplicate_query = select(ImageHistory).where(
                and_(
                    ImageHistory.parent_image_id == parent_image_id,
                    ImageHistory.user_id == user_id,
                    ImageHistory.prompt == new_prompt.strip(),
                    ImageHistory.evolution_type == evolution_type,
                    ImageHistory.is_deleted == False
                )
            )
            
            duplicate_result = await db.execute(duplicate_query)
            existing_evolution = duplicate_result.scalar_one_or_none()
            
            if existing_evolution:
                logger.warning(f"⚠️ 이미 존재하는 진화 이미지: {existing_evolution.id}")
                # 기존 이미지를 선택 상태로 만들고 반환
                existing_evolution.mark_as_selected()
                await db.commit()
                return existing_evolution
            
            # 3. 부모 이미지의 설정 상속
            generation_style = style or parent_image.style
            generation_size = size or parent_image.size
            
            logger.debug(f"📋 진화 설정: style={generation_style}, size={generation_size}, type={evolution_type}")
            
            # 4. 진화된 프롬프트 생성 (기존 프롬프트 + 새 요구사항)
            enhanced_prompt = self._create_evolution_prompt(
                parent_image.prompt,
                new_prompt,
                evolution_type
            )
            
            logger.debug(f"🎨 강화된 프롬프트: '{enhanced_prompt[:100]}...'")
            
        except Exception as db_error:
            logger.error(f"❌ 데이터베이스 검증 단계 실패: {db_error}")
            raise db_error
        
        # 5. AI 이미지 생성 API 호출 (트랜잭션 외부에서 실행)
        try:
            logger.info(f"🚀 AI 이미지 생성 API 호출 시작")
            job_id = str(uuid.uuid4())  # 고유한 작업 ID 생성
            generation_result = await self.image_generation_service.generate_image(
                job_id=job_id,
                user_id=str(user_id),
                prompt=enhanced_prompt,
                style=generation_style,
                size=generation_size,
                num_images=1
            )
            
            if not generation_result or not generation_result.get("images"):
                logger.error(f"❌ 이미지 생성 실패: {enhanced_prompt}")
                return None
                
            logger.info(f"✅ AI 이미지 생성 성공: {len(generation_result['images'])}개 이미지")
            
        except Exception as generation_error:
            logger.error(f"❌ AI 이미지 생성 API 실패: {type(generation_error).__name__}: {generation_error}")
            return None
        
        # 6. 새로운 히스토리 엔트리 데이터베이스 저장 (새 트랜잭션)
        try:
            logger.info(f"💾 진화 이미지 데이터베이스 저장 시작")
            
            new_image = await self.save_generated_image(
                db=db,
                conversation_id=parent_image.conversation_id,
                user_id=user_id,
                prompt=new_prompt,  # 사용자가 입력한 원본 프롬프트 저장
                image_urls=generation_result["images"],
                style=generation_style,
                size=generation_size,
                parent_image_id=parent_image_id,
                evolution_type=evolution_type,
                generation_params=self.safe_uuid_to_str({
                    "enhanced_prompt": enhanced_prompt,
                    "parent_prompt": parent_image.prompt,
                    "evolution_request": new_prompt,
                    "generation_method": generation_result.get("metadata", {}).get("generation_method", "unknown"),
                    "parent_image_id": parent_image_id
                }),
                safety_score=generation_result.get("safety_score", 1.0)
            )
            
            logger.info(f"🎉 진화 이미지 생성 완료: {new_image.id} (부모: {parent_image_id})")
            return new_image
            
        except Exception as save_error:
            logger.error(f"❌ 진화 이미지 데이터베이스 저장 실패: {type(save_error).__name__}: {save_error}")
            
            # UUID 직렯화 오류 첫겨 및 록백 처리
            if "Object of type UUID is not JSON serializable" in str(save_error):
                logger.error(f"🔍 UUID 직렬화 오류 발생 - generation_params 점검 필요")
                try:
                    await db.rollback()
                    logger.info(f"🔄 데이터베이스 록백 완료")
                except Exception as rollback_error:
                    logger.error(f"❌ 록백 실패: {rollback_error}")
            
            import traceback
            logger.error(f"💣 저장 실패 상세 오류:\n{traceback.format_exc()}")
            return None
    
    async def get_image_by_id(
        self,
        db: AsyncSession,
        image_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[ImageHistory]:
        """ID로 특정 이미지 조회 (권한 확인 포함)"""
        
        query = select(ImageHistory).where(
            and_(
                ImageHistory.id == image_id,
                ImageHistory.user_id == user_id
            )
        ).options(selectinload(ImageHistory.parent_image))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_conversation_stats(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """대화의 이미지 생성 통계 조회"""
        
        query = select(
            func.count(ImageHistory.id).label("total_images"),
            func.count(func.nullif(ImageHistory.parent_image_id, None)).label("evolution_images"),
            func.avg(ImageHistory.safety_score).label("avg_safety_score"),
            func.sum(ImageHistory.file_size_bytes).label("total_file_size")
        ).where(
            and_(
                ImageHistory.conversation_id == conversation_id,
                ImageHistory.user_id == user_id,
                ImageHistory.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        stats = result.one()
        
        return {
            "total_images": stats.total_images or 0,
            "evolution_images": stats.evolution_images or 0,
            "original_images": (stats.total_images or 0) - (stats.evolution_images or 0),
            "avg_safety_score": float(stats.avg_safety_score or 0),
            "total_file_size_mb": round((stats.total_file_size or 0) / (1024 * 1024), 2)
        }
    
    # ======= 유틸리티 메서드 =======
    
    def _create_evolution_prompt(
        self,
        original_prompt: str,
        evolution_request: str,
        evolution_type: str
    ) -> str:
        """기존 프롬프트와 새 요구사항을 결합한 진화 프롬프트 생성"""
        
        evolution_templates = {
            "modification": f"Based on this image concept: '{original_prompt}', create a modified version with these changes: {evolution_request}",
            "variation": f"Create a variation of this concept: '{original_prompt}', incorporating: {evolution_request}",
            "extension": f"Extend this image idea: '{original_prompt}', by adding: {evolution_request}",
            "based_on": f"Using this as inspiration: '{original_prompt}', create something new: {evolution_request}"
        }
        
        template = evolution_templates.get(evolution_type, evolution_templates["modification"])
        return template
    
    async def check_duplicate_prompt(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        prompt: str,
        style: str,
        size: str
    ) -> Optional[ImageHistory]:
        """중복 프롬프트 확인 (동일한 설정으로 이미 생성된 이미지가 있는지)"""
        
        prompt_hash = hashlib.sha256(f"{prompt}_{style}_{size}".encode()).hexdigest()
        
        query = select(ImageHistory).where(
            and_(
                ImageHistory.conversation_id == conversation_id,
                ImageHistory.user_id == user_id,
                ImageHistory.prompt_hash == prompt_hash,
                ImageHistory.is_deleted == False
            )
        ).order_by(desc(ImageHistory.created_at))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()