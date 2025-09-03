"""
Request-Based Canvas 시스템 관리자
각 채팅 요청별로 고유한 Canvas를 생성하고 관리하는 서비스
"""

from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import logging

from app.db.models.image_history import ImageHistory
from app.services.image_generation_service import ImageGenerationService

logger = logging.getLogger(__name__)


class CanvasRequestManager:
    """
    Request-Based Canvas 관리 시스템
    
    핵심 원칙:
    1. 채팅 요청 → 새 Canvas 생성 (CREATE 모드)
    2. Canvas 내 진화 → 기존 Canvas 내 버전 관리 (EDIT 모드)
    3. 각 Canvas는 고유한 canvas_id로 식별
    4. Canvas 내에서 version은 순차적으로 증가
    """
    
    def __init__(self, image_service: ImageGenerationService):
        self.image_service = image_service
    
    async def create_new_canvas_for_chat_request(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        prompt: str,
        style: str = "realistic",
        size: str = "1024x1024",
        generation_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        채팅에서 새 이미지 생성 요청 시 새로운 Canvas 생성
        
        Args:
            db: 데이터베이스 세션
            conversation_id: 대화 ID
            user_id: 사용자 ID
            prompt: 이미지 생성 프롬프트
            style: 이미지 스타일
            size: 이미지 크기
            generation_params: 생성 파라미터
        
        Returns:
            생성된 Canvas 정보 및 이미지 데이터
        """
        try:
            # 새로운 Canvas ID 생성
            canvas_id = uuid4()
            
            logger.info(f"🎨 새로운 Canvas 생성 시작: {canvas_id}")
            logger.info(f"📝 프롬프트: {prompt[:50]}...")
            
            # 이미지 생성 서비스 호출
            generation_result = await self.image_service.generate_image(
                job_id=str(uuid4()),
                user_id=str(user_id),
                prompt=prompt,
                style=style,
                size=size,
                num_images=1
            )
            
            if not generation_result.get("success"):
                raise Exception(f"이미지 생성 실패: {generation_result.get('error')}")
            
            # 이미지 URL 추출
            image_urls = generation_result.get("images", [])
            if not image_urls:
                raise Exception("생성된 이미지 URL이 없습니다")
            
            # ImageHistory 레코드 생성 (CREATE 모드)
            image_history = ImageHistory.create_from_generation(
                conversation_id=conversation_id,
                user_id=user_id,
                prompt=prompt,
                image_urls=image_urls,
                style=style,
                size=size,
                generation_params=generation_params,
                canvas_id=canvas_id,
                canvas_version=1,
                edit_mode="CREATE"
            )
            
            # 데이터베이스에 저장
            db.add(image_history)
            await db.commit()
            await db.refresh(image_history)
            
            logger.info(f"✅ Canvas 생성 완료: {canvas_id} (버전 1)")
            
            return {
                "success": True,
                "canvas_id": str(canvas_id),
                "canvas_version": 1,
                "image_history_id": str(image_history.id),
                "image_urls": image_urls,
                "primary_image_url": image_history.primary_image_url,
                "metadata": image_history.generation_metadata,
                "edit_mode": "CREATE"
            }
            
        except Exception as e:
            logger.error(f"❌ Canvas 생성 실패: {str(e)}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e),
                "canvas_id": None
            }
    
    async def evolve_image_within_canvas(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        canvas_id: UUID,
        reference_image_id: UUID,
        new_prompt: str,
        evolution_type: str = "variation",
        edit_mode_type: str = "EDIT_MODE_INPAINT_INSERTION",
        style: Optional[str] = None,
        size: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Canvas 내에서 선택된 이미지를 기반으로 새 이미지 진화
        
        Args:
            db: 데이터베이스 세션
            conversation_id: 대화 ID
            user_id: 사용자 ID
            canvas_id: Canvas ID
            reference_image_id: 참조 이미지 ID
            new_prompt: 새로운 프롬프트
            evolution_type: 진화 타입
            edit_mode_type: 편집 모드 타입
            style: 이미지 스타일 (선택사항)
            size: 이미지 크기 (선택사항)
        
        Returns:
            진화된 이미지 정보
        """
        try:
            logger.info(f"🔄 Canvas 내 이미지 진화 시작: {canvas_id}")
            logger.info(f"🖼️ 참조 이미지: {reference_image_id}")
            logger.info(f"📝 새 프롬프트: {new_prompt[:50]}...")
            
            # 참조 이미지 정보 조회
            result = await db.execute(
                select(ImageHistory).where(
                    and_(
                        ImageHistory.id == reference_image_id,
                        ImageHistory.conversation_id == conversation_id,
                        ImageHistory.canvas_id == canvas_id,
                        ImageHistory.is_deleted == False
                    )
                )
            )
            reference_image = result.scalars().first()
            
            if not reference_image:
                raise Exception(f"참조 이미지를 찾을 수 없습니다: {reference_image_id}")
            
            # 현재 Canvas의 최신 버전 번호 조회
            result = await db.execute(
                select(ImageHistory.canvas_version)
                .where(
                    and_(
                        ImageHistory.canvas_id == canvas_id,
                        ImageHistory.conversation_id == conversation_id,
                        ImageHistory.is_deleted == False
                    )
                )
                .order_by(ImageHistory.canvas_version.desc())
                .limit(1)
            )
            latest_version = result.scalar() or 0
            next_version = latest_version + 1
            
            # 참조 이미지 URL 가져오기
            reference_image_url = reference_image.primary_image_url
            
            # 스타일과 크기는 참조 이미지에서 상속 (지정되지 않은 경우)
            final_style = style or reference_image.style
            final_size = size or reference_image.size
            
            # edit_image 서비스 호출
            edit_result = await self.image_service.edit_image(
                job_id=str(uuid4()),
                user_id=str(user_id),
                prompt=new_prompt,
                reference_image_url=reference_image_url,
                edit_mode=edit_mode_type,
                style=final_style,
                size=final_size,
                num_images=1
            )
            
            if not edit_result.get("success"):
                raise Exception(f"이미지 편집 실패: {edit_result.get('error')}")
            
            # 편집된 이미지 URL 추출
            edited_image_urls = edit_result.get("images", [])
            if not edited_image_urls:
                raise Exception("편집된 이미지 URL이 없습니다")
            
            # 새로운 ImageHistory 레코드 생성 (EDIT 모드)
            evolved_image = ImageHistory.create_from_generation(
                conversation_id=conversation_id,
                user_id=user_id,
                prompt=new_prompt,
                image_urls=edited_image_urls,
                style=final_style,
                size=final_size,
                parent_image_id=reference_image_id,
                evolution_type=evolution_type,
                canvas_id=canvas_id,
                canvas_version=next_version,
                edit_mode="EDIT",
                reference_image_id=reference_image_id
            )
            
            # 데이터베이스에 저장
            db.add(evolved_image)
            await db.commit()
            await db.refresh(evolved_image)
            
            logger.info(f"✅ Canvas 내 이미지 진화 완료: {canvas_id} (버전 {next_version})")
            
            return {
                "success": True,
                "canvas_id": str(canvas_id),
                "canvas_version": next_version,
                "image_history_id": str(evolved_image.id),
                "parent_image_id": str(reference_image_id),
                "image_urls": edited_image_urls,
                "primary_image_url": evolved_image.primary_image_url,
                "evolution_type": evolution_type,
                "metadata": evolved_image.generation_metadata,
                "edit_mode": "EDIT"
            }
            
        except Exception as e:
            logger.error(f"❌ Canvas 내 이미지 진화 실패: {str(e)}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e),
                "canvas_id": str(canvas_id) if canvas_id else None
            }
    
    async def get_canvas_history(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        canvas_id: UUID,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        특정 Canvas의 모든 버전 히스토리 조회
        
        Args:
            db: 데이터베이스 세션
            conversation_id: 대화 ID
            canvas_id: Canvas ID
            include_deleted: 삭제된 항목 포함 여부
        
        Returns:
            Canvas 버전 히스토리 목록
        """
        try:
            # 기본 조건
            conditions = [
                ImageHistory.canvas_id == canvas_id,
                ImageHistory.conversation_id == conversation_id
            ]
            
            # 삭제된 항목 제외 (옵션)
            if not include_deleted:
                conditions.append(ImageHistory.is_deleted == False)
            
            # 쿼리 실행
            result = await db.execute(
                select(ImageHistory)
                .where(and_(*conditions))
                .order_by(ImageHistory.canvas_version.asc())
            )
            
            canvas_history = result.scalars().all()
            
            # 결과 변환
            history_list = []
            for image in canvas_history:
                history_list.append({
                    "id": str(image.id),
                    "canvas_version": image.canvas_version,
                    "prompt": image.prompt,
                    "image_urls": image.image_urls,
                    "primary_image_url": image.primary_image_url,
                    "style": image.style,
                    "size": image.size,
                    "edit_mode": image.edit_mode,
                    "evolution_type": image.evolution_type,
                    "parent_image_id": str(image.parent_image_id) if image.parent_image_id else None,
                    "reference_image_id": str(image.reference_image_id) if image.reference_image_id else None,
                    "is_selected": image.is_selected,
                    "is_deleted": image.is_deleted,
                    "created_at": image.created_at.isoformat() if image.created_at else None,
                    "metadata": image.generation_metadata
                })
            
            logger.info(f"📋 Canvas 히스토리 조회 완료: {canvas_id} ({len(history_list)}개 버전)")
            
            return history_list
            
        except Exception as e:
            logger.error(f"❌ Canvas 히스토리 조회 실패: {str(e)}")
            return []
    
    async def get_conversation_canvases(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        대화 내 모든 Canvas 목록 조회
        
        Args:
            db: 데이터베이스 세션
            conversation_id: 대화 ID
            include_deleted: 삭제된 항목 포함 여부
        
        Returns:
            Canvas 목록 (각 Canvas의 최신 정보)
        """
        try:
            # 기본 조건
            conditions = [
                ImageHistory.conversation_id == conversation_id,
                ImageHistory.canvas_id.isnot(None)
            ]
            
            # 삭제된 항목 제외 (옵션)
            if not include_deleted:
                conditions.append(ImageHistory.is_deleted == False)
            
            # Canvas별 최신 버전 조회
            result = await db.execute(
                select(ImageHistory)
                .where(and_(*conditions))
                .order_by(ImageHistory.canvas_id, ImageHistory.canvas_version.desc())
            )
            
            all_images = result.scalars().all()
            
            # Canvas별로 그룹핑하여 최신 버전만 선택
            canvas_dict = {}
            for image in all_images:
                canvas_key = str(image.canvas_id)
                if canvas_key not in canvas_dict:
                    canvas_dict[canvas_key] = {
                        "canvas_id": canvas_key,
                        "latest_version": image.canvas_version,
                        "total_versions": 0,
                        "created_at": image.created_at.isoformat() if image.created_at else None,
                        "latest_image": {
                            "id": str(image.id),
                            "prompt": image.prompt,
                            "primary_image_url": image.primary_image_url,
                            "style": image.style,
                            "size": image.size,
                            "edit_mode": image.edit_mode
                        }
                    }
            
            # 각 Canvas의 총 버전 수 계산
            for canvas_id in canvas_dict.keys():
                version_count_result = await db.execute(
                    select(ImageHistory.id)
                    .where(
                        and_(
                            ImageHistory.canvas_id == UUID(canvas_id),
                            ImageHistory.conversation_id == conversation_id,
                            ImageHistory.is_deleted == False if not include_deleted else True
                        )
                    )
                )
                canvas_dict[canvas_id]["total_versions"] = len(version_count_result.scalars().all())
            
            canvas_list = list(canvas_dict.values())
            canvas_list.sort(key=lambda x: x["created_at"], reverse=True)
            
            logger.info(f"🎨 대화 Canvas 목록 조회 완료: {conversation_id} ({len(canvas_list)}개 Canvas)")
            
            return canvas_list
            
        except Exception as e:
            logger.error(f"❌대화 Canvas 목록 조회 실패: {str(e)}")
            return []
    
    async def delete_canvas_version(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        canvas_id: UUID,
        version: int,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Canvas의 특정 버전 삭제 (소프트 삭제)
        
        Args:
            db: 데이터베이스 세션
            conversation_id: 대화 ID
            canvas_id: Canvas ID
            version: 삭제할 버전 번호
            user_id: 사용자 ID
        
        Returns:
            삭제 결과
        """
        try:
            # 삭제할 이미지 조회
            result = await db.execute(
                select(ImageHistory).where(
                    and_(
                        ImageHistory.conversation_id == conversation_id,
                        ImageHistory.canvas_id == canvas_id,
                        ImageHistory.canvas_version == version,
                        ImageHistory.user_id == user_id,
                        ImageHistory.is_deleted == False
                    )
                )
            )
            
            image_to_delete = result.scalars().first()
            
            if not image_to_delete:
                return {
                    "success": False,
                    "error": "삭제할 이미지를 찾을 수 없습니다"
                }
            
            # 소프트 삭제 수행
            image_to_delete.soft_delete()
            
            await db.commit()
            
            logger.info(f"🗑️ Canvas 버전 삭제 완료: {canvas_id} v{version}")
            
            return {
                "success": True,
                "message": f"Canvas 버전 {version}이 삭제되었습니다"
            }
            
        except Exception as e:
            logger.error(f"❌ Canvas 버전 삭제 실패: {str(e)}")
            await db.rollback()
            return {
                "success": False,
                "error": str(e)
            }