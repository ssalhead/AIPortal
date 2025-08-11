"""
워크스페이스 API 엔드포인트
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.services.workspace_service import WorkspaceService
from app.db.models.workspace import WorkspaceType, ArtifactType, PermissionLevel

router = APIRouter()


class WorkspaceCreateRequest(BaseModel):
    """워크스페이스 생성 요청"""
    name: str
    description: Optional[str] = None
    type: WorkspaceType = WorkspaceType.CANVAS
    is_public: bool = False


class ArtifactCreateRequest(BaseModel):
    """아티팩트 생성 요청"""
    title: str
    type: ArtifactType
    content: str = ""
    position: Optional[Dict[str, Any]] = None
    size: Optional[Dict[str, Any]] = None


class CollaboratorInviteRequest(BaseModel):
    """협업자 초대 요청"""
    email: str
    permission_level: PermissionLevel = PermissionLevel.EDITOR


@router.post("/", response_model=Dict[str, Any])
async def create_workspace(
    request: WorkspaceCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """새 워크스페이스 생성"""
    
    workspace_service = WorkspaceService(db)
    
    try:
        workspace = await workspace_service.create_workspace(
            user_id=current_user["id"],
            name=request.name,
            description=request.description,
            workspace_type=request.type,
            is_public=request.is_public
        )
        
        return {
            "id": str(workspace.id),
            "name": workspace.name,
            "description": workspace.description,
            "type": workspace.type.value,
            "is_public": workspace.is_public,
            "created_at": workspace.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"워크스페이스 생성 실패: {str(e)}"
        )


@router.get("/", response_model=List[Dict[str, Any]])
async def get_user_workspaces(
    limit: int = 20,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """사용자의 워크스페이스 목록 조회"""
    
    workspace_service = WorkspaceService(db)
    
    return await workspace_service.get_user_workspaces(
        user_id=current_user["id"],
        limit=limit,
        offset=offset
    )


@router.get("/{workspace_id}", response_model=Dict[str, Any])
async def get_workspace_detail(
    workspace_id: str,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """워크스페이스 상세 정보 조회"""
    
    workspace_service = WorkspaceService(db)
    
    workspace = await workspace_service.get_workspace_detail(
        workspace_id=workspace_id,
        user_id=current_user["id"]
    )
    
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="워크스페이스를 찾을 수 없거나 접근 권한이 없습니다"
        )
    
    return workspace


@router.post("/{workspace_id}/artifacts", response_model=Dict[str, Any])
async def create_artifact(
    workspace_id: str,
    request: ArtifactCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """새 아티팩트 생성"""
    
    workspace_service = WorkspaceService(db)
    
    artifact = await workspace_service.create_artifact(
        workspace_id=workspace_id,
        user_id=current_user["id"],
        title=request.title,
        artifact_type=request.type,
        content=request.content,
        position=request.position,
        size=request.size
    )
    
    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="아티팩트 생성 권한이 없습니다"
        )
    
    return artifact


@router.post("/{workspace_id}/collaborators")
async def invite_collaborator(
    workspace_id: str,
    request: CollaboratorInviteRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """협업자 초대"""
    
    workspace_service = WorkspaceService(db)
    
    success = await workspace_service.add_collaborator(
        workspace_id=workspace_id,
        user_id=current_user["id"],
        target_user_email=request.email,
        permission_level=request.permission_level,
        inviter_id=current_user["id"]
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="협업자 초대에 실패했습니다"
        )
    
    return {"message": f"협업자 {request.email}를 성공적으로 초대했습니다"}


@router.get("/{workspace_id}/activities", response_model=List[Dict[str, Any]])
async def get_workspace_activities(
    workspace_id: str,
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """워크스페이스 활동 로그 조회"""
    
    workspace_service = WorkspaceService(db)
    
    return await workspace_service.get_workspace_activities(
        workspace_id=workspace_id,
        user_id=current_user["id"],
        limit=limit
    )