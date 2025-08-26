from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from app.db.base import Base
from app.utils.timezone import now_kst

class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class ConversationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    
    model = Column(String(100))
    agent_type = Column(String(100))
    
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ACTIVE)
    metadata_ = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=now_kst)
    updated_at = Column(DateTime, default=now_kst, onupdate=now_kst)
    
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    feedbacks = relationship("MessageFeedback", back_populates="conversation", cascade="all, delete-orphan")
    summaries = relationship("ConversationSummary", back_populates="conversation", cascade="all, delete-orphan")
    # image_sessions = relationship("ImageGenerationSession", back_populates="conversation", cascade="all, delete-orphan")  # 임시 비활성화

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    role = Column(SQLEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    
    model = Column(String(100))
    
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    latency_ms = Column(Integer)
    
    metadata_ = Column(JSON, default=dict)
    attachments = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=now_kst)
    updated_at = Column(DateTime, default=now_kst, onupdate=now_kst)
    
    conversation = relationship("Conversation", back_populates="messages")


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    summary_text = Column(Text, nullable=False)
    summary_type = Column(String(50), default="auto")  # auto, manual, periodic
    
    messages_count = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    
    metadata_ = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=now_kst)
    updated_at = Column(DateTime, default=now_kst, onupdate=now_kst)
    
    conversation = relationship("Conversation", back_populates="summaries")


# Conversation 모델에 summaries 관계 추가를 위해 기존 관계 확장이 필요하지만,
# 순환 import를 피하기 위해 relationship을 나중에 추가하도록 설계