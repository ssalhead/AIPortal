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