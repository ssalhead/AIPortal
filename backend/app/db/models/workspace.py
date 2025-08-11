from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Boolean, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from app.db.base import Base

class WorkspaceType(str, enum.Enum):
    CANVAS = "canvas"
    DOCUMENT = "document"
    CODE = "code"
    DATA = "data"
    WORKFLOW = "workflow"

class ArtifactType(str, enum.Enum):
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    CHART = "chart"
    TABLE = "table"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    MINDMAP = "mindmap"
    WHITEBOARD = "whiteboard"

class PermissionLevel(str, enum.Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"
    COMMENTER = "commenter"

class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(SQLEnum(WorkspaceType), default=WorkspaceType.CANVAS)
    
    is_public = Column(Boolean, default=False)
    is_template = Column(Boolean, default=False)
    
    config = Column(JSON, default=dict)
    layout = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="workspaces")
    artifacts = relationship("Artifact", back_populates="workspace", cascade="all, delete-orphan")
    collaborators = relationship("WorkspaceCollaborator", cascade="all, delete-orphan")
    activities = relationship("WorkspaceActivity", cascade="all, delete-orphan")

class Artifact(Base):
    __tablename__ = "artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    
    title = Column(String(255), nullable=False)
    type = Column(SQLEnum(ArtifactType), nullable=False)
    content = Column(Text)
    
    version = Column(Integer, default=1)
    is_pinned = Column(Boolean, default=False)
    
    position = Column(JSON)
    size = Column(JSON)
    style = Column(JSON, default=dict)
    metadata_ = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    workspace = relationship("Workspace", back_populates="artifacts")
    versions = relationship("ArtifactVersion", back_populates="artifact", cascade="all, delete-orphan")

class WorkspaceCollaborator(Base):
    """워크스페이스 협업자"""
    __tablename__ = "workspace_collaborators"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    permission_level = Column(SQLEnum(PermissionLevel), default=PermissionLevel.VIEWER)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    workspace = relationship("Workspace")
    user = relationship("User", foreign_keys=[user_id])
    inviter = relationship("User", foreign_keys=[invited_by])

class ArtifactVersion(Base):
    """아티팩트 버전 관리"""
    __tablename__ = "artifact_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(UUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=False)
    
    version_number = Column(Integer, nullable=False)
    content = Column(Text)
    diff_data = Column(JSON)  # 변경 내용 저장
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    artifact = relationship("Artifact", back_populates="versions")
    creator = relationship("User")

class WorkspaceActivity(Base):
    """워크스페이스 활동 로그"""
    __tablename__ = "workspace_activities"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    action_type = Column(String(50), nullable=False)  # create, edit, delete, share, comment
    target_type = Column(String(50))  # artifact, workspace, comment
    target_id = Column(String(255))
    
    description = Column(Text)
    metadata_ = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workspace = relationship("Workspace")
    user = relationship("User")