"""
워크스페이스 관리 서비스
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload
import uuid
import logging
from datetime import datetime

from app.db.models.workspace import (
    Workspace, 
    Artifact, 
    WorkspaceCollaborator, 
    ArtifactVersion, 
    WorkspaceActivity,
    WorkspaceType,
    ArtifactType,
    PermissionLevel
)
from app.db.models.user import User

logger = logging.getLogger(__name__)


class WorkspaceService:
    """워크스페이스 관리 서비스"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_workspace(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        workspace_type: WorkspaceType = WorkspaceType.CANVAS,
        is_public: bool = False
    ) -> Workspace:
        """새 워크스페이스 생성"""
        
        workspace = Workspace(
            user_id=uuid.UUID(user_id),
            name=name,
            description=description,
            type=workspace_type,
            is_public=is_public,
            config={
                "default_permissions": "editor",
                "auto_save": True,
                "version_control": True
            },
            layout={
                "grid_size": 20,
                "snap_to_grid": True,
                "zoom_level": 1.0
            }
        )
        
        self.db.add(workspace)
        await self.db.flush()
        
        # 생성자를 소유자로 자동 추가
        collaborator = WorkspaceCollaborator(
            workspace_id=workspace.id,
            user_id=uuid.UUID(user_id),
            permission_level=PermissionLevel.OWNER,
            invited_by=uuid.UUID(user_id)
        )
        
        self.db.add(collaborator)
        
        # 활동 로그 기록
        await self.log_activity(
            workspace_id=str(workspace.id),
            user_id=user_id,
            action_type="create",
            target_type="workspace",
            target_id=str(workspace.id),
            description=f"워크스페이스 '{name}' 생성"
        )
        
        await self.db.commit()
        return workspace
    
    async def get_user_workspaces(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """사용자의 워크스페이스 목록 조회"""
        
        query = select(Workspace, WorkspaceCollaborator.permission_level).join(
            WorkspaceCollaborator, 
            and_(
                WorkspaceCollaborator.workspace_id == Workspace.id,
                WorkspaceCollaborator.user_id == uuid.UUID(user_id)
            )
        ).options(
            selectinload(Workspace.artifacts)
        ).order_by(desc(Workspace.updated_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        workspaces_data = result.all()
        
        workspaces = []
        for workspace, permission in workspaces_data:
            workspaces.append({
                "id": str(workspace.id),
                "name": workspace.name,
                "description": workspace.description,
                "type": workspace.type.value,
                "is_public": workspace.is_public,
                "permission_level": permission.value,
                "artifact_count": len(workspace.artifacts),
                "created_at": workspace.created_at.isoformat(),
                "updated_at": workspace.updated_at.isoformat()
            })
        
        return workspaces
    
    async def get_workspace_detail(
        self,
        workspace_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """워크스페이스 상세 정보 조회"""
        
        # 권한 확인
        if not await self.check_user_permission(workspace_id, user_id):
            return None
        
        query = select(Workspace).where(
            Workspace.id == uuid.UUID(workspace_id)
        ).options(
            selectinload(Workspace.artifacts),
            selectinload(Workspace.collaborators)
        )
        
        result = await self.db.execute(query)
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            return None
        
        # 협업자 정보 가져오기
        collaborators_query = select(
            WorkspaceCollaborator, User.email, User.full_name
        ).join(User, WorkspaceCollaborator.user_id == User.id).where(
            WorkspaceCollaborator.workspace_id == workspace.id
        )
        
        collab_result = await self.db.execute(collaborators_query)
        collaborators_data = collab_result.all()
        
        collaborators = []
        for collab, email, name in collaborators_data:
            collaborators.append({
                "user_id": str(collab.user_id),
                "email": email,
                "name": name,
                "permission_level": collab.permission_level.value,
                "joined_at": collab.created_at.isoformat()
            })
        
        # 아티팩트 정보
        artifacts = []
        for artifact in workspace.artifacts:
            artifacts.append({
                "id": str(artifact.id),
                "title": artifact.title,
                "type": artifact.type.value,
                "version": artifact.version,
                "is_pinned": artifact.is_pinned,
                "position": artifact.position,
                "size": artifact.size,
                "created_at": artifact.created_at.isoformat(),
                "updated_at": artifact.updated_at.isoformat()
            })
        
        return {
            "id": str(workspace.id),
            "name": workspace.name,
            "description": workspace.description,
            "type": workspace.type.value,
            "is_public": workspace.is_public,
            "config": workspace.config,
            "layout": workspace.layout,
            "artifacts": artifacts,
            "collaborators": collaborators,
            "created_at": workspace.created_at.isoformat(),
            "updated_at": workspace.updated_at.isoformat()
        }
    
    async def check_user_permission(
        self,
        workspace_id: str,
        user_id: str,
        required_level: PermissionLevel = PermissionLevel.VIEWER
    ) -> bool:
        """사용자 권한 확인"""
        
        query = select(WorkspaceCollaborator.permission_level).where(
            and_(
                WorkspaceCollaborator.workspace_id == uuid.UUID(workspace_id),
                WorkspaceCollaborator.user_id == uuid.UUID(user_id)
            )
        )
        
        result = await self.db.execute(query)
        permission = result.scalar_one_or_none()
        
        if not permission:
            # 공개 워크스페이스인지 확인
            workspace_query = select(Workspace.is_public).where(
                Workspace.id == uuid.UUID(workspace_id)
            )
            workspace_result = await self.db.execute(workspace_query)
            is_public = workspace_result.scalar_one_or_none()
            return is_public if is_public is not None else False
        
        # 권한 레벨 체크
        permission_hierarchy = {
            PermissionLevel.OWNER: 4,
            PermissionLevel.EDITOR: 3,
            PermissionLevel.COMMENTER: 2,
            PermissionLevel.VIEWER: 1
        }
        
        return permission_hierarchy.get(permission, 0) >= permission_hierarchy.get(required_level, 1)
    
    async def add_collaborator(
        self,
        workspace_id: str,
        user_id: str,
        target_user_email: str,
        permission_level: PermissionLevel,
        inviter_id: str
    ) -> bool:
        """협업자 추가"""
        
        # 권한 확인 (EDITOR 이상만 초대 가능)
        if not await self.check_user_permission(workspace_id, inviter_id, PermissionLevel.EDITOR):
            return False
        
        # 대상 사용자 찾기
        user_query = select(User.id).where(User.email == target_user_email)
        user_result = await self.db.execute(user_query)
        target_user_id = user_result.scalar_one_or_none()
        
        if not target_user_id:
            return False
        
        # 이미 협업자인지 확인
        existing_query = select(WorkspaceCollaborator).where(
            and_(
                WorkspaceCollaborator.workspace_id == uuid.UUID(workspace_id),
                WorkspaceCollaborator.user_id == target_user_id
            )
        )
        existing_result = await self.db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            return False
        
        # 협업자 추가
        collaborator = WorkspaceCollaborator(
            workspace_id=uuid.UUID(workspace_id),
            user_id=target_user_id,
            permission_level=permission_level,
            invited_by=uuid.UUID(inviter_id)
        )
        
        self.db.add(collaborator)
        
        # 활동 로그
        await self.log_activity(
            workspace_id=workspace_id,
            user_id=inviter_id,
            action_type="invite",
            target_type="user",
            target_id=str(target_user_id),
            description=f"협업자 초대: {target_user_email} ({permission_level.value})"
        )
        
        await self.db.commit()
        return True
    
    async def create_artifact(
        self,
        workspace_id: str,
        user_id: str,
        title: str,
        artifact_type: ArtifactType,
        content: str = "",
        position: Optional[Dict[str, Any]] = None,
        size: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """새 아티팩트 생성"""
        
        # 권한 확인 (EDITOR 이상)
        if not await self.check_user_permission(workspace_id, user_id, PermissionLevel.EDITOR):
            return None
        
        artifact = Artifact(
            workspace_id=uuid.UUID(workspace_id),
            title=title,
            type=artifact_type,
            content=content,
            position=position or {"x": 100, "y": 100},
            size=size or {"width": 400, "height": 300},
            version=1
        )
        
        self.db.add(artifact)
        await self.db.flush()
        
        # 첫 번째 버전 생성
        version = ArtifactVersion(
            artifact_id=artifact.id,
            version_number=1,
            content=content,
            created_by=uuid.UUID(user_id)
        )
        
        self.db.add(version)
        
        # 활동 로그
        await self.log_activity(
            workspace_id=workspace_id,
            user_id=user_id,
            action_type="create",
            target_type="artifact",
            target_id=str(artifact.id),
            description=f"아티팩트 '{title}' 생성 ({artifact_type.value})"
        )
        
        await self.db.commit()
        
        return {
            "id": str(artifact.id),
            "title": artifact.title,
            "type": artifact.type.value,
            "content": artifact.content,
            "position": artifact.position,
            "size": artifact.size,
            "version": artifact.version,
            "created_at": artifact.created_at.isoformat()
        }
    
    async def log_activity(
        self,
        workspace_id: str,
        user_id: str,
        action_type: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """워크스페이스 활동 로그 기록"""
        
        activity = WorkspaceActivity(
            workspace_id=uuid.UUID(workspace_id),
            user_id=uuid.UUID(user_id),
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            description=description,
            metadata_=metadata or {}
        )
        
        self.db.add(activity)
        # commit은 호출자에서 처리
    
    async def get_workspace_activities(
        self,
        workspace_id: str,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """워크스페이스 활동 로그 조회"""
        
        # 권한 확인
        if not await self.check_user_permission(workspace_id, user_id):
            return []
        
        query = select(
            WorkspaceActivity, User.full_name, User.email
        ).join(User, WorkspaceActivity.user_id == User.id).where(
            WorkspaceActivity.workspace_id == uuid.UUID(workspace_id)
        ).order_by(desc(WorkspaceActivity.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        activities_data = result.all()
        
        activities = []
        for activity, user_name, user_email in activities_data:
            activities.append({
                "id": str(activity.id),
                "action_type": activity.action_type,
                "target_type": activity.target_type,
                "target_id": activity.target_id,
                "description": activity.description,
                "user": {
                    "name": user_name,
                    "email": user_email
                },
                "metadata": activity.metadata_,
                "created_at": activity.created_at.isoformat()
            })
        
        return activities


# 의존성 주입을 위한 서비스 팩토리
async def get_workspace_service(db: AsyncSession) -> WorkspaceService:
    """워크스페이스 서비스 의존성 주입"""
    return WorkspaceService(db)