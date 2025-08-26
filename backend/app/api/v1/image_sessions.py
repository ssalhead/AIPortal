"""
이미지 세션 관리 API 엔드포인트
진화형 이미지 생성 세션의 CRUD 작업 처리
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.services.image_session_service import ImageSessionService
from app.core.auth import get_current_user_with_header
from app.db.models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# === Pydantic 모델 정의 ===

class ImageSessionCreate(BaseModel):
    """이미지 세션 생성 요청"""
    conversation_id: UUID
    theme: str = Field(..., min_length=1, max_length=255)
    base_prompt: str = Field(..., min_length=1)
    evolution_history: Optional[List[str]] = None


class ImageSessionUpdate(BaseModel):
    """이미지 세션 업데이트 요청"""
    theme: Optional[str] = Field(None, min_length=1, max_length=255)
    base_prompt: Optional[str] = Field(None, min_length=1)
    evolution_history: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ImageVersionCreate(BaseModel):
    """이미지 버전 생성 요청"""
    prompt: str = Field(..., min_length=1)
    negative_prompt: str = ""
    style: str = "realistic"
    size: str = "1K_1:1"
    image_url: Optional[str] = None
    parent_version_id: Optional[UUID] = None
    status: str = "generating"


class ImageVersionUpdate(BaseModel):
    """이미지 버전 업데이트 요청"""
    prompt: Optional[str] = Field(None, min_length=1)
    negative_prompt: Optional[str] = None
    style: Optional[str] = None
    size: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None


class ImageSessionResponse(BaseModel):
    """이미지 세션 응답"""
    id: UUID
    conversation_id: UUID
    theme: str
    base_prompt: str
    evolution_history: List[str]
    selected_version_id: Optional[UUID]
    is_active: bool
    created_at: str
    updated_at: str
    versions: List[Dict[str, Any]] = []


class ImageVersionResponse(BaseModel):
    """이미지 버전 응답"""
    id: UUID
    session_id: UUID
    version_number: int
    parent_version_id: Optional[UUID]
    prompt: str
    negative_prompt: str
    style: str
    size: str
    image_url: Optional[str]
    status: str
    is_selected: bool
    created_at: str


# === API 엔드포인트 ===

@router.post("/sessions", response_model=ImageSessionResponse)
async def create_session(
    session_data: ImageSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_header)
):
    """새로운 이미지 생성 세션 생성"""
    
    try:
        service = ImageSessionService(db)
        
        session = await service.create_session(
            user_id=current_user.id,
            conversation_id=session_data.conversation_id,
            theme=session_data.theme,
            base_prompt=session_data.base_prompt,
            evolution_history=session_data.evolution_history
        )
        
        logger.info(f"이미지 세션 생성 성공: {session.id}")
        
        return ImageSessionResponse(
            id=session.id,
            conversation_id=session.conversation_id,
            theme=session.theme,
            base_prompt=session.base_prompt,
            evolution_history=session.evolution_history or [],
            selected_version_id=None,  # Temporarily removed due to circular reference
            is_active=session.is_active,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            versions=[]  # 관계가 비활성화되어 있으므로 빈 배열 반환
        )
        
    except Exception as e:
        logger.error(f"이미지 세션 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 세션 생성에 실패했습니다"
        )


@router.get("/conversations/{conversation_id}/session", response_model=Optional[ImageSessionResponse])
async def get_session_by_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_header)
):
    """대화 ID로 이미지 세션 조회"""
    
    try:
        service = ImageSessionService(db)
        
        session = await service.get_session_by_conversation(current_user.id, conversation_id)
        
        if not session:
            return None
            
        # 버전 정보도 함께 로드
        session_with_versions = await service.get_session_with_versions(current_user.id, session.id)
        if not session_with_versions:
            return None
        
        logger.info(f"이미지 세션 조회 성공: {session.id}")
        
        return ImageSessionResponse(
            id=session_with_versions.id,
            conversation_id=session_with_versions.conversation_id,
            theme=session_with_versions.theme,
            base_prompt=session_with_versions.base_prompt,
            evolution_history=session_with_versions.evolution_history or [],
            selected_version_id=None,  # Temporarily removed due to circular reference
            is_active=session_with_versions.is_active,
            created_at=session_with_versions.created_at.isoformat(),
            updated_at=session_with_versions.updated_at.isoformat(),
            versions=[]  # 관계가 비활성화되어 있으므로 빈 배열 반환
        )
        
    except Exception as e:
        logger.error(f"이미지 세션 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 세션 조회에 실패했습니다"
        )


@router.get("/sessions/{session_id}", response_model=ImageSessionResponse)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_header)
):
    """세션 ID로 이미지 세션 조회"""
    
    try:
        service = ImageSessionService(db)
        
        session = await service.get_session_with_versions(current_user.id, session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지 세션을 찾을 수 없습니다"
            )
        
        logger.info(f"이미지 세션 조회 성공: {session_id}")
        
        return ImageSessionResponse(
            id=session.id,
            conversation_id=session.conversation_id,
            theme=session.theme,
            base_prompt=session.base_prompt,
            evolution_history=session.evolution_history or [],
            selected_version_id=None,  # Temporarily removed due to circular reference
            is_active=session.is_active,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            versions=[]  # 관계가 비활성화되어 있으므로 빈 배열 반환 (get_session)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 세션 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 세션 조회에 실패했습니다"
        )


@router.put("/sessions/{session_id}", response_model=ImageSessionResponse)
async def update_session(
    session_id: UUID,
    session_data: ImageSessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_header)
):
    """이미지 세션 업데이트"""
    
    try:
        service = ImageSessionService(db)
        
        # None이 아닌 필드만 업데이트
        update_data = {k: v for k, v in session_data.dict().items() if v is not None}
        
        session = await service.update_session(current_user.id, session_id, **update_data)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지 세션을 찾을 수 없습니다"
            )
        
        # 최신 정보와 버전들 로드
        updated_session = await service.get_session_with_versions(current_user.id, session_id)
        
        logger.info(f"이미지 세션 업데이트 성공: {session_id}")
        
        return ImageSessionResponse(
            id=updated_session.id,
            conversation_id=updated_session.conversation_id,
            theme=updated_session.theme,
            base_prompt=updated_session.base_prompt,
            evolution_history=updated_session.evolution_history or [],
            selected_version_id=None,  # Temporarily removed due to circular reference
            is_active=updated_session.is_active,
            created_at=updated_session.created_at.isoformat(),
            updated_at=updated_session.updated_at.isoformat(),
            versions=[]  # 관계가 비활성화되어 있으므로 빈 배열 반환 (update_session)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 세션 업데이트 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 세션 업데이트에 실패했습니다"
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_header)
):
    """이미지 세션 삭제"""
    
    try:
        service = ImageSessionService(db)
        
        success = await service.delete_session(current_user.id, session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지 세션을 찾을 수 없습니다"
            )
        
        logger.info(f"이미지 세션 삭제 성공: {session_id}")
        
        return {"message": "이미지 세션이 성공적으로 삭제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 세션 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 세션 삭제에 실패했습니다"
        )


# === 버전 관련 엔드포인트 ===

@router.post("/sessions/{session_id}/versions", response_model=ImageVersionResponse)
async def add_version(
    session_id: UUID,
    version_data: ImageVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_header)
):
    """세션에 새로운 이미지 버전 추가"""
    
    try:
        service = ImageSessionService(db)
        
        version = await service.add_version(
            user_id=current_user.id,
            session_id=session_id,
            **version_data.dict()
        )
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지 세션을 찾을 수 없습니다"
            )
        
        logger.info(f"이미지 버전 추가 성공: {version.id}")
        
        return ImageVersionResponse(
            id=version.id,
            session_id=version.session_id,
            version_number=version.version_number,
            parent_version_id=version.parent_version_id,
            prompt=version.prompt,
            negative_prompt=version.negative_prompt,
            style=version.style,
            size=version.size,
            image_url=version.image_url,
            status=version.status,
            is_selected=version.is_selected,
            created_at=version.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 버전 추가 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 버전 추가에 실패했습니다"
        )


@router.put("/versions/{version_id}", response_model=ImageVersionResponse)
async def update_version(
    version_id: UUID,
    version_data: ImageVersionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_header)
):
    """이미지 버전 업데이트"""
    
    try:
        service = ImageSessionService(db)
        
        # None이 아닌 필드만 업데이트
        update_data = {k: v for k, v in version_data.dict().items() if v is not None}
        
        version = await service.update_version(current_user.id, version_id, **update_data)
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지 버전을 찾을 수 없습니다"
            )
        
        logger.info(f"이미지 버전 업데이트 성공: {version_id}")
        
        return ImageVersionResponse(
            id=version.id,
            session_id=version.session_id,
            version_number=version.version_number,
            parent_version_id=version.parent_version_id,
            prompt=version.prompt,
            negative_prompt=version.negative_prompt,
            style=version.style,
            size=version.size,
            image_url=version.image_url,
            status=version.status,
            is_selected=version.is_selected,
            created_at=version.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 버전 업데이트 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 버전 업데이트에 실패했습니다"
        )


@router.put("/sessions/{session_id}/versions/{version_id}/select", response_model=ImageVersionResponse)
async def select_version(
    session_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_header)
):
    """특정 버전을 선택된 버전으로 설정"""
    
    try:
        service = ImageSessionService(db)
        
        version = await service.select_version(current_user.id, session_id, version_id)
        
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="이미지 버전을 찾을 수 없습니다"
            )
        
        logger.info(f"이미지 버전 선택 성공: {version_id}")
        
        return ImageVersionResponse(
            id=version.id,
            session_id=version.session_id,
            version_number=version.version_number,
            parent_version_id=version.parent_version_id,
            prompt=version.prompt,
            negative_prompt=version.negative_prompt,
            style=version.style,
            size=version.size,
            image_url=version.image_url,
            status=version.status,
            is_selected=version.is_selected,
            created_at=version.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 버전 선택 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 버전 선택에 실패했습니다"
        )


@router.delete("/sessions/{session_id}/versions/{version_id}")
async def delete_version(
    session_id: UUID,
    version_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_header)
):
    """이미지 버전 삭제"""
    
    try:
        service = ImageSessionService(db)
        
        result = await service.delete_version(current_user.id, session_id, version_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get("message", "이미지 버전을 찾을 수 없습니다")
            )
        
        logger.info(f"이미지 버전 삭제 성공: {version_id}")
        
        return {
            "message": "이미지 버전이 성공적으로 삭제되었습니다",
            "deleted_version_id": result["deleted_version_id"],
            "deleted_image_url": result["deleted_image_url"],
            "new_selected_version": result["new_selected_version"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 버전 삭제 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이미지 버전 삭제에 실패했습니다"
        )


@router.get("/conversations/{conversation_id}/deleted-images")
async def get_deleted_image_urls(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_header)
):
    """대화에서 삭제된 이미지 URL 목록 조회"""
    
    try:
        service = ImageSessionService(db)
        
        deleted_urls = await service.get_deleted_image_urls(current_user.id, conversation_id)
        
        logger.info(f"삭제된 이미지 URL 조회 성공: {len(deleted_urls)}개")
        
        return {"deleted_image_urls": deleted_urls}
        
    except Exception as e:
        logger.error(f"삭제된 이미지 URL 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="삭제된 이미지 URL 조회에 실패했습니다"
        )