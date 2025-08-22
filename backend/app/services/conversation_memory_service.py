"""
대화 메모리 서비스 - 하이브리드 메모리 시스템

장기메모리: 5개 초과 시 LLM 요약 생성
단기메모리: 최근 5개 Q&A 쌍 (원문 보존)
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import json

from app.db.session import AsyncSessionLocal
from app.db.models import ConversationSummary
from app.services.conversation_history_service import conversation_history_service
from app.agents.llm_router import llm_router
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


class ConversationMemoryService:
    """대화 메모리 관리 서비스"""
    
    def __init__(self):
        self.short_term_limit = 5  # 단기메모리 최대 Q&A 쌍 수
        self.max_tokens_per_message = 1000  # 메시지당 최대 토큰 수 (추정)
        self.max_context_tokens = 3000  # 전체 컨텍스트 최대 토큰 수
    
    async def get_conversation_context(
        self,
        conversation_id: str,
        user_id: str,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        대화 컨텍스트 조회 (장기 + 단기 메모리)
        
        Args:
            conversation_id: 대화 ID
            user_id: 사용자 ID  
            session: DB 세션
            
        Returns:
            {
                'long_term_memory': str,  # 요약된 장기 기억
                'short_term_memory': List[Dict],  # 최근 메시지들
                'context_prompt': str,  # LLM용 컨텍스트 프롬프트
                'total_tokens': int  # 예상 토큰 수
            }
        """
        try:
            if not session:
                async with AsyncSessionLocal() as db:
                    return await self._build_context(conversation_id, user_id, db)
            else:
                return await self._build_context(conversation_id, user_id, session)
                
        except Exception as e:
            logger.error(f"컨텍스트 조회 실패: {e}")
            return {
                'long_term_memory': '',
                'short_term_memory': [],
                'context_prompt': '',
                'total_tokens': 0
            }
    
    async def _build_context(
        self,
        conversation_id: str,
        user_id: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """내부: 컨텍스트 구성"""
        
        # 1. 대화 상세 정보 조회
        conversation_detail = await conversation_history_service.get_conversation_detail(
            conversation_id=conversation_id,
            user_id=user_id,
            session=session
        )
        
        if not conversation_detail or not conversation_detail.get('messages'):
            return {
                'long_term_memory': '',
                'short_term_memory': [],
                'context_prompt': '',
                'total_tokens': 0
            }
        
        messages = conversation_detail['messages']
        
        # 2. 메시지를 Q&A 쌍으로 그룹화
        qa_pairs = self._group_messages_to_qa_pairs(messages)
        
        # 3. 장기/단기 메모리 분리
        if len(qa_pairs) <= self.short_term_limit:
            # 단기메모리만 사용
            long_term_memory = ''
            short_term_memory = qa_pairs
        else:
            # 장기 + 단기 메모리 사용
            long_term_qa_pairs = qa_pairs[:-self.short_term_limit]
            short_term_memory = qa_pairs[-self.short_term_limit:]
            
            # 장기메모리 요약 조회 또는 생성
            long_term_memory = await self._get_or_create_summary(
                conversation_id, long_term_qa_pairs, session
            )
        
        # 4. LLM용 컨텍스트 프롬프트 구성
        context_prompt = self._build_context_prompt(long_term_memory, short_term_memory)
        
        # 5. 토큰 수 추정
        total_tokens = self._estimate_tokens(context_prompt)
        
        return {
            'long_term_memory': long_term_memory,
            'short_term_memory': short_term_memory,
            'context_prompt': context_prompt,
            'total_tokens': total_tokens
        }
    
    def _group_messages_to_qa_pairs(self, messages: List[Dict]) -> List[Dict]:
        """메시지를 Q&A 쌍으로 그룹화"""
        qa_pairs = []
        current_pair = {}
        
        for message in messages:
            role = message.get('role', '').upper()
            content = message.get('content', '')
            timestamp = message.get('created_at', '')
            
            if role == 'USER':
                # 새 Q&A 쌍 시작
                if current_pair.get('answer'):
                    qa_pairs.append(current_pair)
                current_pair = {
                    'question': content,
                    'question_time': timestamp,
                    'answer': '',
                    'answer_time': ''
                }
            elif role == 'ASSISTANT' and current_pair.get('question'):
                # 답변 추가
                current_pair['answer'] = content
                current_pair['answer_time'] = timestamp
        
        # 마지막 쌍 추가
        if current_pair.get('question'):
            qa_pairs.append(current_pair)
            
        return qa_pairs
    
    async def _get_or_create_summary(
        self,
        conversation_id: str,
        qa_pairs: List[Dict],
        session: AsyncSession
    ) -> str:
        """장기메모리 요약 조회 또는 생성"""
        
        try:
            # conversation_summaries 테이블에서 기존 요약 조회
            async with AsyncSessionLocal() as session:
                existing_summary = await session.execute(
                    select(ConversationSummary)
                    .where(ConversationSummary.conversation_id == conversation_id)
                    .order_by(ConversationSummary.updated_at.desc())
                )
                existing_record = existing_summary.scalar_one_or_none()
                
                # 기존 요약이 있고, 메시지 개수가 크게 변하지 않았으면 재사용
                current_message_count = len(qa_pairs)
                if existing_record and abs(existing_record.messages_count - current_message_count) <= 2:
                    logger.info(f"기존 요약 재사용: {conversation_id}")
                    return existing_record.summary_text
            
            # 새로운 요약 생성
            summary = await self._generate_summary(qa_pairs)
            
            # 생성된 요약을 데이터베이스에 저장
            async with AsyncSessionLocal() as session:
                # 기존 요약이 있다면 업데이트, 없다면 생성
                if existing_record:
                    existing_record.summary_text = summary
                    existing_record.messages_count = len(qa_pairs)
                    existing_record.updated_at = datetime.utcnow()
                    await session.merge(existing_record)
                else:
                    new_summary = ConversationSummary(
                        conversation_id=conversation_id,
                        summary_text=summary,
                        summary_type="auto",
                        messages_count=len(qa_pairs)
                    )
                    session.add(new_summary)
                
                await session.commit()
            
            logger.info(f"대화 {conversation_id} 요약 생성 완료 (길이: {len(summary)})")
            
            return summary
            
        except Exception as e:
            logger.error(f"요약 생성 실패: {e}")
            # 폴백: 간단한 요약
            return self._create_simple_summary(qa_pairs)
    
    async def _generate_summary(self, qa_pairs: List[Dict]) -> str:
        """LLM을 사용하여 대화 요약 생성"""
        
        if not qa_pairs:
            return ""
        
        # 요약할 대화 내용 구성
        conversation_text = ""
        for i, pair in enumerate(qa_pairs, 1):
            conversation_text += f"Q{i}: {pair['question']}\n"
            conversation_text += f"A{i}: {pair['answer']}\n\n"
        
        # 요약 생성 프롬프트
        summary_prompt = f"""다음 대화 내용을 간결하게 요약해주세요.

{conversation_text}

요약 규칙:
1. 주요 주제와 핵심 내용만 포함
2. 사용자의 질문 의도와 AI의 답변 요점 중심
3. 200자 이내로 작성
4. 구체적인 정보나 맥락이 있다면 보존
5. 대화의 흐름과 연결성 유지

요약:"""

        try:
            # 기본 모델로 요약 생성 (gemini 사용)
            response = await llm_router.generate_response(
                message=summary_prompt,
                model="gemini",
                agent_type="none",
                user_id="system",
                session_id=None,
                stream=False
            )
            
            summary = response.response.strip()
            
            # 길이 제한
            if len(summary) > 300:
                summary = summary[:297] + "..."
                
            return summary
            
        except Exception as e:
            logger.error(f"LLM 요약 생성 실패: {e}")
            return self._create_simple_summary(qa_pairs)
    
    def _create_simple_summary(self, qa_pairs: List[Dict]) -> str:
        """간단한 규칙 기반 요약 생성 (폴백)"""
        if not qa_pairs:
            return ""
        
        # 주요 키워드 추출 (간단한 방식)
        all_text = " ".join([pair['question'] + " " + pair['answer'] for pair in qa_pairs])
        
        # 첫 번째 질문을 기반으로 간단한 요약
        first_question = qa_pairs[0]['question']
        summary = f"'{first_question[:50]}...' 관련 대화 ({len(qa_pairs)}개 질문)"
        
        return summary
    
    def _build_context_prompt(self, long_term_memory: str, short_term_memory: List[Dict]) -> str:
        """LLM용 컨텍스트 프롬프트 구성"""
        
        context_parts = []
        
        # 장기메모리 추가
        if long_term_memory:
            context_parts.append(f"[이전 대화 요약]\n{long_term_memory}\n")
        
        # 단기메모리 추가 (최근 대화)
        if short_term_memory:
            context_parts.append("[최근 대화]")
            for i, pair in enumerate(short_term_memory, 1):
                context_parts.append(f"사용자: {pair['question']}")
                if pair['answer']:
                    context_parts.append(f"AI: {pair['answer']}")
        
        return "\n".join(context_parts)
    
    def _estimate_tokens(self, text: str) -> int:
        """텍스트 토큰 수 추정 (한국어 기준)"""
        # 간단한 추정: 한국어는 보통 1글자당 1.5토큰 정도
        # 영어는 단어당 1.3토큰 정도
        korean_chars = len([c for c in text if ord(c) > 127])
        english_chars = len(text) - korean_chars
        
        estimated_tokens = int(korean_chars * 1.5 + english_chars * 0.25)
        return estimated_tokens
    
    async def should_create_summary(
        self,
        conversation_id: str,
        user_id: str,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """요약 생성이 필요한지 판단"""
        
        try:
            if not session:
                async with AsyncSessionLocal() as db:
                    return await self._check_summary_needed(conversation_id, user_id, db)
            else:
                return await self._check_summary_needed(conversation_id, user_id, session)
                
        except Exception as e:
            logger.error(f"요약 필요 여부 확인 실패: {e}")
            return False
    
    async def _check_summary_needed(
        self,
        conversation_id: str,
        user_id: str,
        session: AsyncSession
    ) -> bool:
        """내부: 요약 필요 여부 확인"""
        
        conversation_detail = await conversation_history_service.get_conversation_detail(
            conversation_id=conversation_id,
            user_id=user_id,
            session=session
        )
        
        if not conversation_detail:
            return False
        
        messages = conversation_detail.get('messages', [])
        qa_pairs = self._group_messages_to_qa_pairs(messages)
        
        # 5개 Q&A 쌍을 초과하면 요약 필요
        return len(qa_pairs) > self.short_term_limit
    
    async def cleanup_old_summaries(self, days_old: int = 30):
        """오래된 요약 정리"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            async with AsyncSessionLocal() as session:
                # 비활성 대화의 오래된 요약 삭제
                old_summaries = await session.execute(
                    select(ConversationSummary)
                    .where(ConversationSummary.updated_at < cutoff_date)
                )
                summaries_to_delete = old_summaries.scalars().all()
                
                deleted_count = 0
                for summary in summaries_to_delete:
                    await session.delete(summary)
                    deleted_count += 1
                
                await session.commit()
                logger.info(f"오래된 요약 {deleted_count}개 정리 완료")
                
        except Exception as e:
            logger.error(f"요약 정리 실패: {e}")


# 서비스 인스턴스
conversation_memory_service = ConversationMemoryService()