from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Text, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base

class CacheEntry(Base):
    __tablename__ = "cache_entries"
    __table_args__ = (
        Index('idx_cache_key_expires', 'key', 'expires_at'),
        Index('idx_cache_expires', 'expires_at'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    
    ttl_seconds = Column(Integer, default=3600)
    expires_at = Column(DateTime, nullable=False)
    
    hit_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    def update_expiry(self, ttl_seconds: int = None):
        if ttl_seconds:
            self.ttl_seconds = ttl_seconds
        self.expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
    
    def increment_hit(self):
        self.hit_count += 1
        self.last_accessed_at = datetime.utcnow()