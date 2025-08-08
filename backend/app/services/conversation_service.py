"""
대화 컨텍스트 및 메모리 관리 서비스
"""

from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uuid

logger = logging.getLogger(__name__)


class ConversationMessage:
    """대화 메시지 데이터 모델"""
    
    def __init__(
        self,
        message_id: str,
        session_id: str,
        user_id: str,
        role: str,  # 'user' 또는 'assistant'
        content: str,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.message_id = message_id
        self.session_id = session_id
        self.user_id = user_id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'message_id': self.message_id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class ConversationSession:
    """대화 세션 관리"""
    
    def __init__(
        self,
        session_id: str,
        user_id: str,
        created_at: datetime,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = created_at
        self.title = title or f"대화 {created_at.strftime('%Y-%m-%d %H:%M')}"
        self.metadata = metadata or {}
        self.messages: List[ConversationMessage] = []
        self.context_summary = ""
    
    def add_message(self, message: ConversationMessage):
        """메시지 추가"""
        self.messages.append(message)
    
    def get_recent_messages(self, limit: int = 10) -> List[ConversationMessage]:
        """최근 메시지 조회"""
        return self.messages[-limit:] if self.messages else []
    
    def get_context_for_llm(self, max_tokens: int = 4000) -> str:
        """LLM에 전달할 컨텍스트 생성 (토큰 수 제한)"""
        if not self.messages:
            return ""
        
        # 최근 메시지부터 역순으로 컨텍스트 구성
        context_parts = []
        estimated_tokens = 0
        
        for message in reversed(self.messages):
            # 대략적인 토큰 수 계산 (한글: 1글자 ≈ 2토큰, 영어: 1단어 ≈ 1토큰)
            content_tokens = len(message.content) * 2  # 보수적 추정
            
            if estimated_tokens + content_tokens > max_tokens:
                break
            
            if message.role == 'user':
                context_parts.append(f"사용자: {message.content}")
            else:
                context_parts.append(f"AI: {message.content}")
            
            estimated_tokens += content_tokens
        
        # 시간 순으로 다시 정렬
        context_parts.reverse()
        
        if context_parts:
            return f"이전 대화 내용:\n" + "\n".join(context_parts) + "\n\n현재 질문:"
        
        return ""
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'message_count': len(self.messages),
            'last_activity': self.messages[-1].timestamp.isoformat() if self.messages else None,
            'metadata': self.metadata
        }


class ConversationService:
    """대화 컨텍스트 관리 서비스"""
    
    def __init__(self):
        self.active_sessions: Dict[str, ConversationSession] = {}
        self.session_timeout = timedelta(hours=24)  # 24시간 후 세션 만료
    
    async def get_or_create_session(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> ConversationSession:
        """세션 조회 또는 생성"""
        
        if session_id and session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            # 세션 만료 확인
            if datetime.utcnow() - session.created_at > self.session_timeout:
                del self.active_sessions[session_id]
                session_id = None
        
        if not session_id:
            # 새 세션 생성
            session_id = str(uuid.uuid4())
            session = ConversationSession(
                session_id=session_id,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            self.active_sessions[session_id] = session
        else:
            session = self.active_sessions[session_id]
        
        return session
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationMessage:
        """메시지 추가"""
        
        session = await self.get_or_create_session(user_id, session_id)
        
        message = ConversationMessage(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )
        
        session.add_message(message)
        
        # 메시지가 너무 많아지면 오래된 메시지 정리
        if len(session.messages) > 50:
            session.messages = session.messages[-30:]  # 최근 30개만 유지
        
        logger.info(f"메시지 추가됨 - 세션: {session_id}, 역할: {role}, 길이: {len(content)}")
        
        return message
    
    async def get_conversation_context(
        self,
        session_id: str,
        user_id: str,
        max_tokens: int = 4000
    ) -> str:
        """대화 컨텍스트 조회"""
        
        session = await self.get_or_create_session(user_id, session_id)
        return session.get_context_for_llm(max_tokens)
    
    async def get_session_history(
        self,
        session_id: str,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """세션 메시지 히스토리 조회"""
        
        if session_id not in self.active_sessions:
            return []
        
        session = self.active_sessions[session_id]
        recent_messages = session.get_recent_messages(limit)
        
        return [message.to_dict() for message in recent_messages]
    
    async def get_user_sessions(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """사용자의 세션 목록 조회"""
        
        user_sessions = [
            session for session in self.active_sessions.values()
            if session.user_id == user_id
        ]
        
        # 최근 활동 순으로 정렬
        user_sessions.sort(
            key=lambda s: s.messages[-1].timestamp if s.messages else s.created_at,
            reverse=True
        )
        
        return [session.to_dict() for session in user_sessions[:limit]]
    
    async def create_new_session(self, user_id: str) -> ConversationSession:
        """새 대화 세션 생성"""
        
        session = ConversationSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        
        self.active_sessions[session.session_id] = session
        
        logger.info(f"새 세션 생성됨 - 세션ID: {session.session_id}, 사용자: {user_id}")
        
        return session
    
    async def end_session(self, session_id: str, user_id: str) -> bool:
        """세션 종료"""
        
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if session.user_id == user_id:
                del self.active_sessions[session_id]
                logger.info(f"세션 종료됨 - 세션ID: {session_id}")
                return True
        
        return False
    
    async def cleanup_expired_sessions(self):
        """만료된 세션 정리"""
        
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if current_time - session.created_at > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        if expired_sessions:
            logger.info(f"{len(expired_sessions)}개 만료된 세션 정리됨")
    
    async def update_session_title(
        self,
        session_id: str,
        user_id: str,
        title: str
    ) -> bool:
        """세션 제목 업데이트"""
        
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            if session.user_id == user_id:
                session.title = title
                logger.info(f"세션 제목 업데이트됨 - 세션ID: {session_id}, 제목: {title}")
                return True
        
        return False


# 서비스 인스턴스
conversation_service = ConversationService()