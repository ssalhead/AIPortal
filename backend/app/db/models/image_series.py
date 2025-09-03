"""
이미지 시리즈 메타데이터 모델
연속성 있는 이미지 생성을 위한 시리즈 관리 시스템
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from app.db.base import Base


class ImageSeries(Base):
    """
    이미지 시리즈 메타데이터 모델
    
    연속성 있는 이미지 시리즈를 관리하고 템플릿 기반 생성을 지원
    """
    __tablename__ = "image_series"
    
    # ======= 기본 식별자 =======
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # ======= 시리즈 기본 정보 =======
    title = Column(String(255), nullable=False, comment="시리즈 제목")
    description = Column(Text, nullable=True, comment="시리즈 설명")
    series_type = Column(String(30), nullable=False, comment="시리즈 타입 (webtoon, instagram, brand, educational, story)")
    template_config = Column(JSON, default=dict, comment="템플릿 설정 (레이아웃, 스타일 등)")
    
    # ======= 시리즈 진행 상태 =======
    target_count = Column(Integer, nullable=False, default=4, comment="목표 이미지 개수")
    current_count = Column(Integer, default=0, comment="현재 생성된 이미지 개수")
    completion_status = Column(String(20), default="planning", comment="완성 상태 (planning, generating, completed, failed)")
    
    # ======= 연속성 유지 설정 =======
    base_style = Column(String(50), nullable=False, comment="기본 스타일")
    consistency_prompt = Column(Text, nullable=True, comment="일관성 유지용 공통 프롬프트")
    character_descriptions = Column(JSON, default=dict, comment="캐릭터 설명 딕셔너리")
    scene_continuity = Column(JSON, default=dict, comment="씬 연속성 정보")
    
    # ======= 프롬프트 체이닝 =======
    base_prompt_template = Column(Text, nullable=True, comment="기본 프롬프트 템플릿")
    prompt_variables = Column(JSON, default=dict, comment="프롬프트 변수 딕셔너리")
    chaining_strategy = Column(String(30), default="sequential", comment="체이닝 전략 (sequential, parallel, reference_based)")
    
    # ======= 생성 진행 추적 =======
    generation_queue = Column(JSON, default=list, comment="생성 대기열 (프롬프트 리스트)")
    generation_progress = Column(JSON, default=dict, comment="생성 진행 상황")
    failed_generations = Column(JSON, default=list, comment="실패한 생성 기록")
    
    # ======= 메타데이터 =======
    tags = Column(JSON, default=list, comment="시리즈 태그")
    settings = Column(JSON, default=dict, comment="추가 설정")
    is_public = Column(Boolean, default=False, comment="공개 여부")
    
    # ======= 상태 관리 =======
    is_active = Column(Boolean, default=True, comment="활성 상태")
    is_template = Column(Boolean, default=False, comment="템플릿으로 사용 가능 여부")
    
    # ======= 타임스탬프 =======
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # ======= 관계 정의 =======
    images = relationship("ImageHistory", backref="series", foreign_keys="ImageHistory.series_id")
    conversation = relationship("Conversation")
    user = relationship("User")
    
    # ======= 제약조건 =======
    __table_args__ = (
        CheckConstraint("target_count >= 1 AND target_count <= 50", name='valid_target_count'),
        CheckConstraint("current_count >= 0", name='valid_current_count'),
        CheckConstraint("completion_status IN ('planning', 'generating', 'completed', 'failed', 'paused')", name='valid_completion_status'),
        CheckConstraint("series_type IN ('webtoon', 'instagram', 'brand', 'educational', 'story', 'custom')", name='valid_series_type'),
        CheckConstraint("chaining_strategy IN ('sequential', 'parallel', 'reference_based', 'hybrid')", name='valid_chaining_strategy'),
    )
    
    def __repr__(self) -> str:
        return f"<ImageSeries(id={self.id}, title='{self.title}', type='{self.series_type}', progress={self.current_count}/{self.target_count})>"
    
    # ======= 비즈니스 로직 메서드 =======
    
    @property
    def is_completed(self) -> bool:
        """시리즈가 완성되었는지 확인"""
        return self.completion_status == "completed" and self.current_count >= self.target_count
    
    @property
    def is_in_progress(self) -> bool:
        """시리즈가 진행 중인지 확인"""
        return self.completion_status == "generating" and self.current_count < self.target_count
    
    @property
    def progress_percentage(self) -> float:
        """진행률 반환 (0.0 ~ 1.0)"""
        if self.target_count <= 0:
            return 0.0
        return min(self.current_count / self.target_count, 1.0)
    
    @property
    def remaining_count(self) -> int:
        """남은 생성 개수"""
        return max(self.target_count - self.current_count, 0)
    
    @property
    def next_series_index(self) -> int:
        """다음 이미지의 시리즈 인덱스"""
        return self.current_count + 1
    
    @property
    def template_metadata(self) -> Dict[str, Any]:
        """템플릿 메타데이터 반환"""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "series_type": self.series_type,
            "template_config": self.template_config,
            "base_style": self.base_style,
            "consistency_prompt": self.consistency_prompt,
            "target_count": self.target_count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def update_progress(self, increment: int = 1) -> None:
        """진행 상황 업데이트"""
        self.current_count += increment
        self.updated_at = func.now()
        
        # 완성 체크
        if self.current_count >= self.target_count:
            self.completion_status = "completed"
            self.completed_at = func.now()
    
    def add_to_queue(self, prompts: List[str]) -> None:
        """생성 대기열에 프롬프트 추가"""
        current_queue = self.generation_queue or []
        current_queue.extend(prompts)
        self.generation_queue = current_queue
        self.updated_at = func.now()
    
    def pop_from_queue(self) -> Optional[str]:
        """대기열에서 다음 프롬프트 가져오기"""
        current_queue = self.generation_queue or []
        if not current_queue:
            return None
        
        next_prompt = current_queue.pop(0)
        self.generation_queue = current_queue
        self.updated_at = func.now()
        return next_prompt
    
    def mark_generation_failed(self, prompt: str, error: str) -> None:
        """실패한 생성 기록"""
        failed_list = self.failed_generations or []
        failed_list.append({
            "prompt": prompt,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
            "series_index": self.next_series_index
        })
        self.failed_generations = failed_list
        self.updated_at = func.now()
    
    def get_character_description(self, character_name: str) -> Optional[str]:
        """특정 캐릭터 설명 가져오기"""
        descriptions = self.character_descriptions or {}
        return descriptions.get(character_name)
    
    def set_character_description(self, character_name: str, description: str) -> None:
        """캐릭터 설명 설정"""
        descriptions = self.character_descriptions or {}
        descriptions[character_name] = description
        self.character_descriptions = descriptions
        self.updated_at = func.now()
    
    def build_consistency_prompt(self, base_prompt: str, series_index: int) -> str:
        """일관성 유지 프롬프트 생성"""
        # 기본 일관성 프롬프트
        consistency_parts = []
        
        if self.consistency_prompt:
            consistency_parts.append(self.consistency_prompt)
        
        # 캐릭터 설명 추가
        if self.character_descriptions:
            char_descriptions = ", ".join([
                f"{name}: {desc}" 
                for name, desc in self.character_descriptions.items()
            ])
            consistency_parts.append(f"Characters: {char_descriptions}")
        
        # 시리즈 인덱스 정보
        consistency_parts.append(f"Scene {series_index} of {self.target_count}")
        
        # 템플릿 설정 반영
        template_config = self.template_config or {}
        if template_config.get("layout"):
            consistency_parts.append(f"Layout: {template_config['layout']}")
        
        # 전체 프롬프트 조합
        full_prompt = base_prompt
        if consistency_parts:
            consistency_text = " | ".join(consistency_parts)
            full_prompt = f"{base_prompt} [{consistency_text}]"
        
        return full_prompt
    
    @classmethod
    def create_series(
        cls,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        series_type: str,
        target_count: int = 4,
        base_style: str = "realistic",
        template_config: Optional[Dict] = None,
        consistency_prompt: Optional[str] = None
    ) -> "ImageSeries":
        """새 이미지 시리즈 생성"""
        
        return cls(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
            series_type=series_type,
            target_count=target_count,
            base_style=base_style,
            template_config=template_config or {},
            consistency_prompt=consistency_prompt,
            completion_status="planning",
            is_active=True
        )


# ======= 시리즈 템플릿 모델 =======

class SeriesTemplate(Base):
    """
    시리즈 템플릿 모델
    
    재사용 가능한 시리즈 템플릿을 저장하고 관리
    """
    __tablename__ = "series_templates"
    
    # ======= 기본 식별자 =======
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # ======= 템플릿 정보 =======
    name = Column(String(255), nullable=False, comment="템플릿 이름")
    description = Column(Text, nullable=True, comment="템플릿 설명")
    series_type = Column(String(30), nullable=False, comment="시리즈 타입")
    category = Column(String(50), nullable=True, comment="템플릿 카테고리")
    
    # ======= 템플릿 설정 =======
    template_config = Column(JSON, nullable=False, comment="템플릿 설정")
    default_target_count = Column(Integer, default=4, comment="기본 목표 개수")
    recommended_style = Column(String(50), default="realistic", comment="추천 스타일")
    
    # ======= 프롬프트 템플릿 =======
    prompt_templates = Column(JSON, default=list, comment="프롬프트 템플릿 리스트")
    consistency_rules = Column(JSON, default=dict, comment="일관성 규칙")
    
    # ======= 메타데이터 =======
    tags = Column(JSON, default=list, comment="템플릿 태그")
    usage_count = Column(Integer, default=0, comment="사용 횟수")
    rating = Column(Integer, default=0, comment="평점 (0-5)")
    
    # ======= 상태 관리 =======
    is_active = Column(Boolean, default=True, comment="활성 상태")
    is_featured = Column(Boolean, default=False, comment="추천 템플릿 여부")
    is_public = Column(Boolean, default=True, comment="공개 여부")
    
    # ======= 타임스탬프 =======
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # ======= 관계 정의 =======
    creator = relationship("User")
    
    # ======= 제약조건 =======
    __table_args__ = (
        CheckConstraint("default_target_count >= 1 AND default_target_count <= 50", name='valid_default_target_count'),
        CheckConstraint("rating >= 0 AND rating <= 5", name='valid_rating'),
        CheckConstraint("usage_count >= 0", name='valid_usage_count'),
        CheckConstraint("series_type IN ('webtoon', 'instagram', 'brand', 'educational', 'story', 'custom')", name='valid_template_series_type'),
    )
    
    def __repr__(self) -> str:
        return f"<SeriesTemplate(id={self.id}, name='{self.name}', type='{self.series_type}', rating={self.rating})>"
    
    def increment_usage(self) -> None:
        """사용 횟수 증가"""
        self.usage_count += 1
        self.updated_at = func.now()
    
    @property
    def template_preview(self) -> Dict[str, Any]:
        """템플릿 미리보기 정보"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "series_type": self.series_type,
            "category": self.category,
            "default_target_count": self.default_target_count,
            "recommended_style": self.recommended_style,
            "rating": self.rating,
            "usage_count": self.usage_count,
            "tags": self.tags
        }