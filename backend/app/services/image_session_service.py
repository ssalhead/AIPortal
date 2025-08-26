"""
ImageSession 관리를 위한 서비스
진화형 이미지 생성 세션의 생성, 조회, 수정, 삭제 및 버전 관리
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, desc, select, update
from uuid import UUID, uuid4
import logging

from app.db.models import ImageGenerationSession, ImageGenerationVersion, User, Conversation
from app.utils.timezone import now_kst

logger = logging.getLogger(__name__)


class ImageSessionService:
    """ImageSession 관련 비즈니스 로직 처리"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # === Session 관리 ===
    
    async def create_session(
        self, 
        user_id: UUID, 
        conversation_id: UUID, 
        theme: str, 
        base_prompt: str,
        evolution_history: Optional[List[str]] = None
    ) -> ImageGenerationSession:
        """새로운 이미지 생성 세션 생성"""
        
        # 기존 세션이 있는지 확인
        existing_session = await self.get_session_by_conversation(user_id, conversation_id)
        if existing_session:
            logger.info(f"기존 세션 발견: {existing_session.id}, 재사용")
            return existing_session
        
        # 새 세션 생성
        session = ImageGenerationSession(
            user_id=user_id,
            conversation_id=conversation_id,
            theme=theme,
            base_prompt=base_prompt,
            evolution_history=evolution_history or [base_prompt],
            is_active=True,
            is_deleted=False
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        logger.info(f"새 이미지 세션 생성: {session.id}, 대화: {conversation_id}")
        return session

    async def get_session_by_conversation(
        self, 
        user_id: UUID, 
        conversation_id: UUID
    ) -> Optional[ImageGenerationSession]:
        """대화 ID로 이미지 세션 조회"""
        
        stmt = select(ImageGenerationSession).where(
            and_(
                ImageGenerationSession.user_id == user_id,
                ImageGenerationSession.conversation_id == conversation_id,
                ImageGenerationSession.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_session_with_versions(
        self, 
        user_id: UUID, 
        session_id: UUID
    ) -> Optional[ImageGenerationSession]:
        """버전 정보를 포함한 세션 조회"""
        
        stmt = select(ImageGenerationSession).where(
            and_(
                ImageGenerationSession.id == session_id,
                ImageGenerationSession.user_id == user_id,
                ImageGenerationSession.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        # 버전 로딩 완전 비활성화 - SQLAlchemy 관계 문제 해결을 위해
            
        return session

    async def update_session(
        self, 
        user_id: UUID, 
        session_id: UUID, 
        **updates
    ) -> Optional[ImageGenerationSession]:
        """세션 정보 업데이트"""
        
        stmt = select(ImageGenerationSession).where(
            and_(
                ImageGenerationSession.id == session_id,
                ImageGenerationSession.user_id == user_id,
                ImageGenerationSession.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            return None
            
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        session.updated_at = now_kst()
        await self.db.commit()
        await self.db.refresh(session)
        
        logger.info(f"세션 업데이트 완료: {session_id}")
        return session

    async def delete_session(self, user_id: UUID, session_id: UUID) -> bool:
        """세션 삭제 (소프트 삭제)"""
        
        stmt = select(ImageGenerationSession).where(
            and_(
                ImageGenerationSession.id == session_id,
                ImageGenerationSession.user_id == user_id,
                ImageGenerationSession.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            return False
            
        session.is_deleted = True
        session.deleted_at = now_kst()
        await self.db.commit()
        
        logger.info(f"세션 삭제 완료: {session_id}")
        return True

    # === Version 관리 ===
    
    async def add_version(
        self, 
        user_id: UUID, 
        session_id: UUID, 
        prompt: str,
        negative_prompt: str = "",
        style: str = "realistic",
        size: str = "1K_1:1",
        image_url: Optional[str] = None,
        parent_version_id: Optional[UUID] = None,
        status: str = "generating"
    ) -> Optional[ImageGenerationVersion]:
        """세션에 새로운 버전 추가"""
        
        # 세션 존재 확인
        session = await self.get_session_with_versions(user_id, session_id)
        if not session:
            logger.warning(f"세션을 찾을 수 없음: {session_id}")
            return None
        
        # 다음 버전 번호 계산 - 관계가 비활성화되어 있으므로 수동으로 조회
        from sqlalchemy import select, func
        from app.db.models.image_session import ImageGenerationVersion
        
        max_version_stmt = select(func.max(ImageGenerationVersion.version_number)).where(
            ImageGenerationVersion.session_id == session_id,
            ImageGenerationVersion.is_deleted == False
        )
        max_version_result = await self.db.execute(max_version_stmt)
        max_version = max_version_result.scalar() or 0
        next_version_number = max_version + 1
        
        # 새 버전 생성
        version = ImageGenerationVersion(
            session_id=session_id,
            version_number=next_version_number,
            parent_version_id=parent_version_id,
            prompt=prompt,
            negative_prompt=negative_prompt,
            style=style,
            size=size,
            image_url=image_url,
            status=status,
            is_selected=True,  # 새로 생성된 버전을 선택된 상태로
            is_deleted=False
        )
        
        self.db.add(version)
        
        # 기존 선택된 버전들 해제
        stmt = update(ImageGenerationVersion).where(
            and_(
                ImageGenerationVersion.session_id == session_id,
                ImageGenerationVersion.is_selected == True,
                ImageGenerationVersion.is_deleted == False
            )
        ).values(is_selected=False)
        await self.db.execute(stmt)
        
        await self.db.commit()
        await self.db.refresh(version)
        
        # 세션의 선택된 버전 ID 업데이트 (임시 비활성화)
        # session.selected_version_id = version.id
        session.updated_at = now_kst()
        await self.db.commit()
        
        logger.info(f"새 버전 추가: {version.id}, 세션: {session_id}, 버전 번호: {next_version_number}")
        return version

    async def update_version(
        self, 
        user_id: UUID, 
        version_id: UUID, 
        **updates
    ) -> Optional[ImageGenerationVersion]:
        """버전 정보 업데이트"""
        
        stmt = select(ImageGenerationVersion).join(ImageGenerationSession).where(
            and_(
                ImageGenerationVersion.id == version_id,
                ImageGenerationSession.user_id == user_id,
                ImageGenerationVersion.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        version = result.scalar_one_or_none()
        
        if not version:
            return None
            
        for key, value in updates.items():
            if hasattr(version, key):
                setattr(version, key, value)
        
        version.updated_at = now_kst()
        await self.db.commit()
        await self.db.refresh(version)
        
        logger.info(f"버전 업데이트 완료: {version_id}")
        return version

    async def select_version(
        self, 
        user_id: UUID, 
        session_id: UUID, 
        version_id: UUID
    ) -> Optional[ImageGenerationVersion]:
        """특정 버전을 선택된 버전으로 설정"""
        
        # 버전 존재 확인
        stmt = select(ImageGenerationVersion).join(ImageGenerationSession).where(
            and_(
                ImageGenerationVersion.id == version_id,
                ImageGenerationVersion.session_id == session_id,
                ImageGenerationSession.user_id == user_id,
                ImageGenerationVersion.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        version = result.scalar_one_or_none()
        
        if not version:
            return None
        
        # 기존 선택된 버전들 해제
        stmt = update(ImageGenerationVersion).where(
            and_(
                ImageGenerationVersion.session_id == session_id,
                ImageGenerationVersion.is_selected == True,
                ImageGenerationVersion.is_deleted == False
            )
        ).values(is_selected=False)
        await self.db.execute(stmt)
        
        # 새 버전 선택
        version.is_selected = True
        version.updated_at = now_kst()
        
        # 세션의 선택된 버전 ID 업데이트 (임시 비활성화)
        session = version.session
        # session.selected_version_id = version_id
        session.updated_at = now_kst()
        
        await self.db.commit()
        await self.db.refresh(version)
        
        logger.info(f"버전 선택 완료: {version_id}, 세션: {session_id}")
        return version

    async def delete_version(
        self, 
        user_id: UUID, 
        session_id: UUID, 
        version_id: UUID
    ) -> Dict[str, Any]:
        """버전 삭제 및 관련 정보 반환"""
        
        # 버전 존재 확인
        stmt = select(ImageGenerationVersion).join(ImageGenerationSession).where(
            and_(
                ImageGenerationVersion.id == version_id,
                ImageGenerationVersion.session_id == session_id,
                ImageGenerationSession.user_id == user_id,
                ImageGenerationVersion.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        version = result.scalar_one_or_none()
        
        if not version:
            return {"success": False, "message": "버전을 찾을 수 없습니다"}
        
        # 삭제할 버전의 이미지 URL 저장
        deleted_image_url = version.image_url
        was_selected = version.is_selected
        
        # 소프트 삭제
        version.is_deleted = True
        version.deleted_at = now_kst()
        
        # 선택된 버전이 삭제된 경우 다른 버전 선택
        new_selected_version = None
        if was_selected:
            # 가장 최신 버전을 새로 선택
            stmt = select(ImageGenerationVersion).where(
                and_(
                    ImageGenerationVersion.session_id == session_id,
                    ImageGenerationVersion.id != version_id,
                    ImageGenerationVersion.is_deleted == False
                )
            ).order_by(desc(ImageGenerationVersion.version_number))
            result = await self.db.execute(stmt)
            new_selected_version = result.scalar_one_or_none()
            
            if new_selected_version:
                new_selected_version.is_selected = True
                new_selected_version.updated_at = now_kst()
                
                # 세션의 선택된 버전 ID 업데이트 (임시 비활성화)
                session = version.session
                # session.selected_version_id = new_selected_version.id
                session.updated_at = now_kst()
        
        await self.db.commit()
        
        result = {
            "success": True,
            "deleted_version_id": version_id,
            "deleted_image_url": deleted_image_url,
            "new_selected_version": new_selected_version.to_dict() if new_selected_version else None
        }
        
        logger.info(f"버전 삭제 완료: {version_id}, 세션: {session_id}")
        return result

    async def get_deleted_image_urls(
        self, 
        user_id: UUID, 
        conversation_id: UUID
    ) -> List[str]:
        """대화에서 삭제된 이미지 URL 목록 조회"""
        
        stmt = select(ImageGenerationVersion).join(ImageGenerationSession).where(
            and_(
                ImageGenerationSession.user_id == user_id,
                ImageGenerationSession.conversation_id == conversation_id,
                ImageGenerationVersion.is_deleted == True,
                ImageGenerationVersion.image_url.isnot(None)
            )
        )
        result = await self.db.execute(stmt)
        deleted_versions = result.scalars().all()
        
        return [v.image_url for v in deleted_versions if v.image_url]

    # === 유틸리티 메서드 ===
    
    def extract_theme(self, prompt: str) -> str:
        """프롬프트에서 주제 추출 (단순한 구현)"""
        # 첫 번째 단어나 핵심 키워드 추출
        words = prompt.strip().split()
        if words:
            return words[0][:50]  # 최대 50자
        return "AI Image"

    async def get_user_sessions(
        self, 
        user_id: UUID, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[ImageGenerationSession]:
        """사용자의 모든 이미지 세션 조회"""
        
        stmt = select(ImageGenerationSession).where(
            and_(
                ImageGenerationSession.user_id == user_id,
                ImageGenerationSession.is_deleted == False
            )
        ).order_by(desc(ImageGenerationSession.updated_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()