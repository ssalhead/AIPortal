"""
대화 이력 관리 서비스
PostgreSQL 최적화 + 3-tier 캐싱 통합
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func, text
from sqlalchemy.orm import selectinload

from app.db.models.conversation import Conversation, Message, ConversationStatus, MessageRole
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.services.conversation_cache_manager import conversation_cache_manager
from app.services.intelligent_cache_manager import intelligent_cache_manager
import logging

logger = logging.getLogger(__name__)


class ConversationHistoryService:
    """대화 이력 관리 통합 서비스"""
    
    def __init__(self):
        self.cache_manager = conversation_cache_manager
        self.intelligent_cache = intelligent_cache_manager
    
    async def get_user_conversations(
        self,
        user_id: str,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        status: Optional[ConversationStatus] = ConversationStatus.ACTIVE
    ) -> Dict[str, Any]:
        """사용자 대화 목록 조회 (캐싱 적용)"""
        try:
            # 지능형 캐시 먼저 확인
            cache_key = f"user_conversations:{user_id}:{skip}:{limit}"
            conversations = await self.intelligent_cache.get(cache_key, user_id, session)
            
            if conversations is None:
                # 기존 캐시 매니저에서 조회
                conversations = await self.cache_manager.get_user_conversations(
                    user_id=user_id,
                    session=session,
                    limit=limit,
                    skip=skip
                )
                
                # 지능형 캐시에 저장
                if conversations:
                    await self.intelligent_cache.set(
                        cache_key, conversations, user_id, session, ttl_seconds=300
                    )
            
            # 총 개수 조회 (캐싱)
            total_count = await self._get_total_conversation_count(user_id, session, status)
            
            return {
                'conversations': conversations,
                'total': total_count,
                'skip': skip,
                'limit': limit,
                'has_more': skip + limit < total_count
            }
            
        except Exception as e:
            logger.error(f"대화 목록 조회 실패: {str(e)}")
            raise
    
    async def get_conversation_detail(
        self,
        conversation_id: str,
        user_id: str,
        session: AsyncSession,
        message_limit: int = 100,
        message_skip: int = 0
    ) -> Optional[Dict[str, Any]]:
        """대화 상세 정보 조회 (메시지 포함)"""
        try:
            # 대화 기본 정보 조회
            conversation_repo = ConversationRepository(session)
            conversation = await conversation_repo.get_by_id(conversation_id)
            
            if not conversation or conversation.user_id != user_id:
                return None
            
            # 메시지 조회 (캐싱 적용)
            messages = await self.cache_manager.get_conversation_messages(
                conversation_id=conversation_id,
                session=session,
                limit=message_limit,
                skip=message_skip
            )
            
            # 총 메시지 수 조회
            total_messages = await self._get_total_message_count(conversation_id, session)
            
            return {
                'id': str(conversation.id),
                'title': conversation.title,
                'description': conversation.description,
                'model': conversation.model,
                'agent_type': conversation.agent_type,
                'status': conversation.status.value,
                'metadata_': conversation.metadata_,
                'created_at': conversation.created_at.isoformat(),
                'updated_at': conversation.updated_at.isoformat(),
                'messages': messages,
                'message_pagination': {
                    'total': total_messages,
                    'skip': message_skip,
                    'limit': message_limit,
                    'has_more': message_skip + message_limit < total_messages
                }
            }
            
        except Exception as e:
            logger.error(f"대화 상세 조회 실패: {str(e)}")
            raise
    
    async def search_conversations(
        self,
        user_id: str,
        query: str,
        session: AsyncSession,
        limit: int = 20
    ) -> Dict[str, Any]:
        """대화 전문검색"""
        try:
            search_results = await self.cache_manager.search_conversations(
                user_id=user_id,
                query=query,
                session=session,
                limit=limit
            )
            
            return {
                'query': query,
                'results': search_results,
                'total': len(search_results),
                'limit': limit
            }
            
        except Exception as e:
            logger.error(f"대화 검색 실패: {str(e)}")
            raise
    
    async def create_conversation(
        self,
        user_id: str,
        title: str,
        session: AsyncSession,
        description: Optional[str] = None,
        model: Optional[str] = None,
        agent_type: Optional[str] = None,
        metadata_: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """새 대화 생성"""
        try:
            conversation_repo = ConversationRepository(session)
            conversation = await conversation_repo.create(
                user_id=user_id,
                title=title,
                description=description,
                model=model,
                agent_type=agent_type,
                metadata_=metadata_ or {}
            )
            
            await session.commit()
            
            # 캐시 무효화
            await self.cache_manager.invalidate_conversation_cache(
                user_id=user_id,
                conversation_id=str(conversation.id),
                session=session
            )
            
            return {
                'id': str(conversation.id),
                'title': conversation.title,
                'description': conversation.description,
                'model': conversation.model,
                'agent_type': conversation.agent_type,
                'status': conversation.status.value,
                'metadata_': conversation.metadata_,
                'created_at': conversation.created_at.isoformat(),
                'updated_at': conversation.updated_at.isoformat()
            }
            
        except Exception as e:
            await session.rollback()
            logger.error(f"대화 생성 실패: {str(e)}")
            raise
    
    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: MessageRole,
        content: str,
        session: AsyncSession,
        model: Optional[str] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        latency_ms: Optional[int] = None,
        metadata_: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """메시지 추가"""
        try:
            # 대화 소유권 확인
            conversation_repo = ConversationRepository(session)
            conversation = await conversation_repo.get_by_id(conversation_id)
            
            if not conversation or conversation.user_id != user_id:
                raise ValueError("대화를 찾을 수 없거나 접근 권한이 없습니다.")
            
            # 메시지 생성
            message_repo = MessageRepository(session)
            message = await message_repo.create(
                conversation_id=conversation_id,
                role=role,
                content=content,
                model=model,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
                metadata_=metadata_ or {},
                attachments=attachments or []
            )
            
            # 대화 업데이트 시간 갱신
            conversation.updated_at = datetime.utcnow()
            session.add(conversation)
            
            await session.commit()
            
            # 캐시 무효화
            await self.cache_manager.invalidate_conversation_cache(
                user_id=user_id,
                conversation_id=conversation_id,
                session=session
            )
            
            return {
                'id': str(message.id),
                'conversation_id': str(message.conversation_id),
                'role': message.role.value,
                'content': message.content,
                'model': message.model,
                'tokens_input': message.tokens_input,
                'tokens_output': message.tokens_output,
                'latency_ms': message.latency_ms,
                'metadata_': message.metadata_,
                'attachments': message.attachments,
                'created_at': message.created_at.isoformat(),
                'updated_at': message.updated_at.isoformat()
            }
            
        except Exception as e:
            await session.rollback()
            logger.error(f"메시지 추가 실패: {str(e)}")
            raise
    
    async def update_conversation(
        self,
        conversation_id: str,
        user_id: str,
        session: AsyncSession,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[ConversationStatus] = None,
        metadata_: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """대화 정보 수정"""
        try:
            conversation_repo = ConversationRepository(session)
            conversation = await conversation_repo.get_by_id(conversation_id)
            
            if not conversation or conversation.user_id != user_id:
                return None
            
            # 필드 업데이트
            if title is not None:
                conversation.title = title
            if description is not None:
                conversation.description = description
            if status is not None:
                conversation.status = status
            if metadata_ is not None:
                conversation.metadata_ = metadata_
            
            conversation.updated_at = datetime.utcnow()
            session.add(conversation)
            await session.commit()
            
            # 캐시 무효화
            await self.cache_manager.invalidate_conversation_cache(
                user_id=user_id,
                conversation_id=conversation_id,
                session=session
            )
            
            return {
                'id': str(conversation.id),
                'title': conversation.title,
                'description': conversation.description,
                'status': conversation.status.value,
                'metadata_': conversation.metadata_,
                'updated_at': conversation.updated_at.isoformat()
            }
            
        except Exception as e:
            await session.rollback()
            logger.error(f"대화 수정 실패: {str(e)}")
            raise
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str,
        session: AsyncSession,
        soft_delete: bool = True
    ) -> bool:
        """대화 삭제 (기본적으로 소프트 삭제)"""
        try:
            conversation_repo = ConversationRepository(session)
            conversation = await conversation_repo.get_by_id(conversation_id)
            
            if not conversation or conversation.user_id != user_id:
                return False
            
            if soft_delete:
                # 소프트 삭제 (상태만 변경)
                conversation.status = ConversationStatus.DELETED
                conversation.updated_at = datetime.utcnow()
                session.add(conversation)
            else:
                # 하드 삭제 (실제 삭제)
                await session.delete(conversation)
            
            await session.commit()
            
            # 캐시 무효화
            await self.cache_manager.invalidate_conversation_cache(
                user_id=user_id,
                conversation_id=conversation_id,
                session=session
            )
            
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"대화 삭제 실패: {str(e)}")
            raise
    
    async def get_conversation_statistics(
        self,
        user_id: str,
        session: AsyncSession,
        days: int = 30
    ) -> Dict[str, Any]:
        """대화 통계 조회"""
        try:
            # 최근 N일간 통계
            since_date = datetime.utcnow() - timedelta(days=days)
            
            stats_query = text("""
                SELECT 
                    COUNT(DISTINCT c.id) as conversation_count,
                    COUNT(m.id) as message_count,
                    COUNT(DISTINCT DATE(c.created_at)) as active_days,
                    COALESCE(AVG(m.tokens_input), 0) as avg_input_tokens,
                    COALESCE(AVG(m.tokens_output), 0) as avg_output_tokens,
                    COALESCE(AVG(m.latency_ms), 0) as avg_latency,
                    COUNT(CASE WHEN m.role = 'user' THEN 1 END) as user_messages,
                    COUNT(CASE WHEN m.role = 'assistant' THEN 1 END) as assistant_messages
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.user_id = :user_id 
                    AND c.created_at >= :since_date
                    AND c.status != :deleted_status
            """)
            
            result = await session.execute(
                stats_query,
                {
                    'user_id': user_id,
                    'since_date': since_date,
                    'deleted_status': ConversationStatus.DELETED.value
                }
            )
            
            row = result.first()
            
            return {
                'period_days': days,
                'conversation_count': row.conversation_count or 0,
                'message_count': row.message_count or 0,
                'active_days': row.active_days or 0,
                'avg_input_tokens': float(row.avg_input_tokens or 0),
                'avg_output_tokens': float(row.avg_output_tokens or 0),
                'avg_latency_ms': float(row.avg_latency or 0),
                'user_messages': row.user_messages or 0,
                'assistant_messages': row.assistant_messages or 0
            }
            
        except Exception as e:
            logger.error(f"대화 통계 조회 실패: {str(e)}")
            raise
    
    async def _get_total_conversation_count(
        self,
        user_id: str,
        session: AsyncSession,
        status: Optional[ConversationStatus] = ConversationStatus.ACTIVE
    ) -> int:
        """총 대화 수 조회 (캐싱)"""
        cache_key = f"total_conversations:{user_id}:{status.value if status else 'all'}"
        
        cached_count = await self.cache_manager.base_cache.get(cache_key, session)
        if cached_count is not None:
            return cached_count
        
        query = select(func.count(Conversation.id)).where(
            and_(
                Conversation.user_id == user_id,
                Conversation.status == status if status else True
            )
        )
        
        result = await session.execute(query)
        count = result.scalar() or 0
        
        # 캐시 저장 (5분)
        await self.cache_manager.base_cache.set(cache_key, count, session, ttl_seconds=300)
        
        return count
    
    async def _get_total_message_count(
        self,
        conversation_id: str,
        session: AsyncSession
    ) -> int:
        """총 메시지 수 조회 (캐싱)"""
        cache_key = f"total_messages:{conversation_id}"
        
        cached_count = await self.cache_manager.base_cache.get(cache_key, session)
        if cached_count is not None:
            return cached_count
        
        query = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        result = await session.execute(query)
        count = result.scalar() or 0
        
        # 캐시 저장 (10분)
        await self.cache_manager.base_cache.set(cache_key, count, session, ttl_seconds=600)
        
        return count


# 전역 서비스 인스턴스
conversation_history_service = ConversationHistoryService()