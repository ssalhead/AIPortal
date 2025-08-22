"""
대화 이력 전용 3-Tier 캐싱 시스템
L1: 메모리 캐시 (최근 10개 대화, 최근 100개 메시지)
L2: PostgreSQL 캐시 테이블 (최근 100개 대화, 최근 1000개 메시지)  
L3: 메인 테이블 (전체 이력)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import OrderedDict
import json
import hashlib
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.services.cache_manager import cache_manager
from app.db.models.conversation import Conversation, Message, MessageRole, ConversationStatus

logger = logging.getLogger(__name__)


class ConversationCacheManager:
    """대화 이력 전용 고도화된 캐싱 시스템"""
    
    def __init__(self, max_conversations: int = 10, max_messages: int = 100):
        self.base_cache = cache_manager
        
        # L1: 메모리 캐시 (대화별 구분)
        self.conversation_cache: OrderedDict = OrderedDict()  # 최근 대화 목록
        self.message_cache: Dict[str, OrderedDict] = {}  # 대화별 메시지 캐시
        
        # 캐시 크기 제한
        self.max_conversations = max_conversations
        self.max_messages_per_conversation = max_messages
        
        # 통계
        self.stats = {
            'conversation_hits': 0,
            'conversation_misses': 0,
            'message_hits': 0,
            'message_misses': 0
        }
    
    async def get_user_conversations(
        self, 
        user_id: str, 
        session: AsyncSession,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """사용자 대화 목록 조회 (3-tier 캐싱)"""
        
        cache_key = f"user_conversations:{user_id}:{skip}:{limit}"
        
        # L1: 메모리 캐시 확인 (최근 조회된 목록)
        if cache_key in self.conversation_cache:
            self.stats['conversation_hits'] += 1
            # LRU 업데이트
            conversations = self.conversation_cache.pop(cache_key)
            self.conversation_cache[cache_key] = conversations
            return conversations
        
        # L2: PostgreSQL 캐시 테이블 확인
        cached_data = await self.base_cache.get(cache_key, session)
        if cached_data:
            self.stats['conversation_hits'] += 1
            # L1에도 저장
            self._update_conversation_cache(cache_key, cached_data)
            return cached_data
        
        # L3: 메인 테이블에서 조회
        self.stats['conversation_misses'] += 1
        
        query = text("""
            SELECT 
                c.id,
                c.title,
                c.model,
                c.agent_type,
                c.status,
                c.created_at,
                c.updated_at,
                COUNT(m.id) as message_count,
                MAX(m.created_at) as last_message_at,
                SUBSTRING(
                    COALESCE(
                        (SELECT content FROM messages 
                         WHERE conversation_id = c.id 
                         ORDER BY created_at DESC LIMIT 1), 
                        ''
                    ), 1, 100
                ) as last_message_preview
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.user_id = :user_id AND c.status = :status
            GROUP BY c.id, c.title, c.model, c.agent_type, c.status, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
            LIMIT :limit OFFSET :skip
        """)
        
        result = await session.execute(
            query, 
            {
                'user_id': user_id, 
                'status': ConversationStatus.ACTIVE.value,
                'limit': limit, 
                'skip': skip
            }
        )
        
        conversations = []
        for row in result:
            conversation_data = {
                'id': str(row.id),
                'title': row.title,
                'model': row.model,
                'agent_type': row.agent_type,
                'status': str(row.status),
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                'message_count': row.message_count,
                'last_message_at': row.last_message_at.isoformat() if row.last_message_at else None,
                'last_message_preview': row.last_message_preview
            }
            conversations.append(conversation_data)
        
        # 캐시에 저장 (L1 + L2)
        await self.base_cache.set(cache_key, conversations, session, ttl_seconds=300)  # 5분
        self._update_conversation_cache(cache_key, conversations)
        
        return conversations
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        session: AsyncSession,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """대화 메시지 조회 (3-tier 캐싱)"""
        
        cache_key = f"conversation_messages:{conversation_id}:{skip}:{limit}"
        
        # L1: 메모리 캐시 확인
        if conversation_id in self.message_cache:
            if cache_key in self.message_cache[conversation_id]:
                self.stats['message_hits'] += 1
                messages = self.message_cache[conversation_id].pop(cache_key)
                self.message_cache[conversation_id][cache_key] = messages
                return messages
        
        # L2: PostgreSQL 캐시 테이블 확인
        cached_data = await self.base_cache.get(cache_key, session)
        if cached_data:
            self.stats['message_hits'] += 1
            # L1에도 저장
            self._update_message_cache(conversation_id, cache_key, cached_data)
            return cached_data
        
        # L3: 메인 테이블에서 조회
        self.stats['message_misses'] += 1
        
        query = text("""
            SELECT 
                m.id,
                m.role,
                m.content,
                m.model,
                m.tokens_input,
                m.tokens_output,
                m.latency_ms,
                m.metadata_,
                m.attachments,
                m.created_at,
                m.updated_at
            FROM messages m
            WHERE m.conversation_id = :conversation_id
            ORDER BY m.created_at ASC
            LIMIT :limit OFFSET :skip
        """)
        
        result = await session.execute(
            query,
            {
                'conversation_id': conversation_id,
                'limit': limit,
                'skip': skip
            }
        )
        
        messages = []
        for row in result:
            # metadata에서 canvas_data 추출
            metadata = row.metadata_ or {}
            canvas_data = metadata.get('canvas_data', None)
            
            # Canvas 데이터 조회 로깅
            if canvas_data:
                logger.info(f"🔍 Canvas 데이터 조회 성공 - message_id: {row.id}, 타입: {canvas_data.get('type', 'unknown')}")
                logger.debug(f"🔍 조회된 Canvas 데이터 상세: {canvas_data}")
            elif metadata:
                logger.debug(f"🔍 메타데이터 있지만 Canvas 데이터 없음 - message_id: {row.id}, metadata 키: {list(metadata.keys())}")
            else:
                logger.debug(f"🔍 메타데이터 없음 - message_id: {row.id}")
            
            message_data = {
                'id': str(row.id),
                'role': (row.role.value if hasattr(row.role, 'value') else str(row.role)).upper(),
                'content': row.content,
                'model': row.model,
                'tokens_input': row.tokens_input,
                'tokens_output': row.tokens_output,
                'latency_ms': row.latency_ms,
                'metadata_': row.metadata_,
                'attachments': row.attachments,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                'canvas_data': canvas_data  # Canvas 데이터를 별도 필드로 제공
            }
            messages.append(message_data)
        
        # 반환 전 Canvas 데이터 포함 여부 확인
        canvas_messages = [msg for msg in messages if msg.get('canvas_data')]
        if canvas_messages:
            logger.info(f"📤 메시지 반환 - Canvas 데이터 포함된 메시지 수: {len(canvas_messages)}/{len(messages)}")
            for msg in canvas_messages:
                logger.debug(f"📤 Canvas 메시지 반환: ID={msg['id']}, canvas_data 타입={msg['canvas_data'].get('type', 'unknown')}")
        else:
            logger.debug(f"📤 메시지 반환 - Canvas 데이터 없음 ({len(messages)}개 메시지)")
        
        # 캐시에 저장 (L1 + L2)
        await self.base_cache.set(cache_key, messages, session, ttl_seconds=600)  # 10분
        self._update_message_cache(conversation_id, cache_key, messages)
        
        return messages
    
    async def search_conversations(
        self,
        user_id: str,
        query: str,
        session: AsyncSession,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """대화 전문검색 (캐싱 적용)"""
        
        cache_key = f"search_conversations:{user_id}:{hashlib.md5(query.encode()).hexdigest()}:{limit}"
        
        # 검색 결과는 L2 캐시에서 확인 (짧은 TTL)
        cached_data = await self.base_cache.get(cache_key, session)
        if cached_data:
            return cached_data
        
        # 전문검색 실행
        search_query = text("""
            SELECT DISTINCT
                c.id,
                c.title,
                c.model,
                c.agent_type,
                c.created_at,
                c.updated_at,
                ts_rank(to_tsvector('korean', m.content), plainto_tsquery('korean', :query)) as rank,
                ts_headline('korean', m.content, plainto_tsquery('korean', :query)) as highlight
            FROM conversations c
            JOIN messages m ON c.id = m.conversation_id
            WHERE c.user_id = :user_id 
                AND c.status = :status
                AND (
                    to_tsvector('korean', m.content) @@ plainto_tsquery('korean', :query)
                    OR to_tsvector('english', m.content) @@ plainto_tsquery('english', :query)
                    OR c.title ILIKE :title_query
                )
            ORDER BY rank DESC, c.updated_at DESC
            LIMIT :limit
        """)
        
        result = await session.execute(
            search_query,
            {
                'user_id': user_id,
                'query': query,
                'title_query': f'%{query}%',
                'status': ConversationStatus.ACTIVE.value,
                'limit': limit
            }
        )
        
        search_results = []
        for row in result:
            result_data = {
                'id': str(row.id),
                'title': row.title,
                'model': row.model,
                'agent_type': row.agent_type,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None,
                'rank': float(row.rank) if row.rank else 0.0,
                'highlight': row.highlight
            }
            search_results.append(result_data)
        
        # 검색 결과 캐싱 (짧은 TTL - 2분)
        await self.base_cache.set(cache_key, search_results, session, ttl_seconds=120)
        
        return search_results
    
    def _update_conversation_cache(self, key: str, data: List[Dict[str, Any]]):
        """L1 대화 캐시 업데이트"""
        self.conversation_cache[key] = data
        
        # 크기 제한 확인
        if len(self.conversation_cache) > self.max_conversations:
            # 가장 오래된 항목 제거 (LRU)
            self.conversation_cache.popitem(last=False)
    
    def _update_message_cache(self, conversation_id: str, key: str, data: List[Dict[str, Any]]):
        """L1 메시지 캐시 업데이트"""
        if conversation_id not in self.message_cache:
            self.message_cache[conversation_id] = OrderedDict()
        
        self.message_cache[conversation_id][key] = data
        
        # 크기 제한 확인
        if len(self.message_cache[conversation_id]) > self.max_messages_per_conversation:
            # 가장 오래된 항목 제거 (LRU)
            self.message_cache[conversation_id].popitem(last=False)
    
    async def invalidate_conversation_cache(
        self, 
        user_id: str, 
        conversation_id: str, 
        session: Optional[AsyncSession] = None
    ):
        """대화 캐시 무효화"""
        
        # L1 캐시 무효화
        keys_to_remove = []
        for key in self.conversation_cache.keys():
            if f"user_conversations:{user_id}" in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.conversation_cache.pop(key, None)
        
        # 메시지 캐시 무효화
        if conversation_id in self.message_cache:
            self.message_cache.pop(conversation_id)
        
        # L2 캐시 무효화
        if session:
            await self.base_cache.invalidate_pattern(f"user_conversations:{user_id}", session)
            await self.base_cache.invalidate_pattern(f"conversation_messages:{conversation_id}", session)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        total_conversation_requests = self.stats['conversation_hits'] + self.stats['conversation_misses']
        total_message_requests = self.stats['message_hits'] + self.stats['message_misses']
        
        conversation_hit_rate = (
            (self.stats['conversation_hits'] / total_conversation_requests * 100) 
            if total_conversation_requests > 0 else 0
        )
        
        message_hit_rate = (
            (self.stats['message_hits'] / total_message_requests * 100) 
            if total_message_requests > 0 else 0
        )
        
        return {
            'conversation_cache': {
                'size': len(self.conversation_cache),
                'max_size': self.max_conversations,
                'hits': self.stats['conversation_hits'],
                'misses': self.stats['conversation_misses'],
                'hit_rate': f"{conversation_hit_rate:.2f}%"
            },
            'message_cache': {
                'conversations_cached': len(self.message_cache),
                'total_cache_entries': sum(len(cache) for cache in self.message_cache.values()),
                'hits': self.stats['message_hits'],
                'misses': self.stats['message_misses'],
                'hit_rate': f"{message_hit_rate:.2f}%"
            },
            'base_cache': self.base_cache.get_stats()
        }


# 전역 대화 캐시 매니저 인스턴스
conversation_cache_manager = ConversationCacheManager()