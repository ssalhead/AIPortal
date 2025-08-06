from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.db.models.workspace import Workspace, Artifact, WorkspaceType, ArtifactType


class WorkspaceRepository(BaseRepository[Workspace]):
    """워크스페이스 Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Workspace, session)
    
    async def get_user_workspaces(
        self,
        user_id: str,
        workspace_type: Optional[WorkspaceType] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Workspace]:
        """사용자의 워크스페이스 목록 조회"""
        query = select(Workspace).where(Workspace.user_id == user_id)
        
        if workspace_type:
            query = query.where(Workspace.type == workspace_type)
        
        query = query.order_by(Workspace.updated_at.desc())
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_with_artifacts(
        self,
        workspace_id: str
    ) -> Optional[Workspace]:
        """아티팩트를 포함한 워크스페이스 조회"""
        result = await self.session.execute(
            select(Workspace)
            .where(Workspace.id == workspace_id)
            .options(selectinload(Workspace.artifacts))
        )
        return result.scalar_one_or_none()
    
    async def create_workspace(
        self,
        user_id: str,
        name: str,
        workspace_type: WorkspaceType = WorkspaceType.CANVAS,
        description: Optional[str] = None
    ) -> Workspace:
        """새 워크스페이스 생성"""
        return await self.create(
            user_id=user_id,
            name=name,
            type=workspace_type,
            description=description,
            config={},
            layout={}
        )


class ArtifactRepository(BaseRepository[Artifact]):
    """아티팩트 Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Artifact, session)
    
    async def get_workspace_artifacts(
        self,
        workspace_id: str,
        artifact_type: Optional[ArtifactType] = None
    ) -> List[Artifact]:
        """워크스페이스의 아티팩트 목록 조회"""
        query = select(Artifact).where(Artifact.workspace_id == workspace_id)
        
        if artifact_type:
            query = query.where(Artifact.type == artifact_type)
        
        query = query.order_by(Artifact.created_at.desc())
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def create_artifact(
        self,
        workspace_id: str,
        title: str,
        artifact_type: ArtifactType,
        content: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Artifact:
        """새 아티팩트 생성"""
        return await self.create(
            workspace_id=workspace_id,
            title=title,
            type=artifact_type,
            content=content,
            metadata=metadata or {},
            version=1,
            is_pinned=False
        )
    
    async def update_artifact_content(
        self,
        artifact_id: str,
        content: str,
        increment_version: bool = True
    ) -> Optional[Artifact]:
        """아티팩트 내용 업데이트"""
        artifact = await self.get(artifact_id)
        if not artifact:
            return None
        
        artifact.content = content
        if increment_version:
            artifact.version += 1
        
        await self.session.commit()
        await self.session.refresh(artifact)
        return artifact