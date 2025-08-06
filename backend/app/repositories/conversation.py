from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.db.models.conversation import Conversation, Message, ConversationStatus, MessageRole


class ConversationRepository(BaseRepository[Conversation]):
    """대화 Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)
    
    async def get_user_conversations(
        self,
        user_id: str,
        status: Optional[ConversationStatus] = ConversationStatus.ACTIVE,
        skip: int = 0,
        limit: int = 20
    ) -> List[Conversation]:
        """사용자의 대화 목록 조회"""
        query = select(Conversation).where(
            and_(
                Conversation.user_id == user_id,
                Conversation.status == status if status else True
            )
        ).order_by(Conversation.updated_at.desc())
        
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_with_messages(
        self,
        conversation_id: str,
        message_limit: int = 50
    ) -> Optional[Conversation]:
        """메시지를 포함한 대화 조회"""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()
    
    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        model: Optional[str] = None,
        agent_type: Optional[str] = None
    ) -> Conversation:
        """새 대화 생성"""
        return await self.create(
            user_id=user_id,
            title=title or f"새 대화 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            model=model,
            agent_type=agent_type,
            status=ConversationStatus.ACTIVE
        )


class MessageRepository(BaseRepository[Message]):
    """메시지 Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Message]:
        """대화의 메시지 목록 조회"""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def create_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        model: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Message:
        """새 메시지 생성"""
        message = await self.create(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model=model,
            metadata=metadata or {}
        )
        
        # 대화 업데이트 시간 갱신
        await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
        )
        
        return message