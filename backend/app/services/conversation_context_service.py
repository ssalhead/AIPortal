"""
대화 맥락 추출 및 분석 서비스
"""

from typing import Dict, Any, List, Optional
import json
import re
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, desc

from app.agents.base import ConversationContext
from app.agents.llm_router import llm_router

logger = logging.getLogger(__name__)


class UniversalContextAnalyzer:
    """범용 대화 맥락 추출 및 분석 서비스"""
    
    def __init__(self):
        self.max_recent_messages = 10  # 더 많은 맥락 확보를 위해 증가
        
        # 하드코딩된 패턴 제거 - 완전 LLM 기반으로 전환
        # 이제 모든 도메인과 의도 분류를 LLM이 동적으로 수행
        
        # 도메인 분류 신뢰도 임계값
        self.domain_confidence_threshold = 0.7
        
        # 동적 학습 도메인 캐시 (성능 최적화 + 지식 축적)
        self.domain_cache = {}
        self.cache_max_size = 1000
        self.domain_learning_enabled = True
        
        # 실시간 도메인 통계
        self.domain_stats = {
            "total_classifications": 0,
            "high_confidence_count": 0,
            "discovered_domains": set(),
            "domain_frequency": {},
            "confidence_distribution": []
        }
    
    async def extract_conversation_context(
        self, 
        session_id: str, 
        current_query: str,
        db_session: AsyncSession,
        model: str = "gemini"
    ) -> ConversationContext:
        """
        대화 세션에서 맥락 정보를 추출합니다.
        
        Args:
            session_id: 대화 세션 ID
            current_query: 현재 사용자 질문
            db_session: 데이터베이스 세션
            model: LLM 모델명
            
        Returns:
            추출된 대화 맥락 정보
        """
        try:
            # 1. 최근 메시지 조회
            recent_messages = await self._get_recent_messages(session_id, db_session)
            logger.info(f"🔍 메시지 조회 완료 - session_id: {session_id}, 조회된 메시지 수: {len(recent_messages)}")
            
            # 2. 맥락 분석 (첫 메시지이거나 메시지가 1개일 때도 시도)
            if len(recent_messages) <= 1:
                logger.info(f"🔍 메시지 수가 적음 ({len(recent_messages)}개) - 기본 맥락으로 분석 시도")
                # 첫 메시지거나 메시지가 1개면 기본 맥락만 생성
                return ConversationContext(
                    recent_messages=recent_messages,
                    conversation_topics=[],
                    mentioned_entities=[],
                    previous_search_queries=[],
                    conversation_flow="첫 번째 대화 또는 초기 단계",
                    current_focus_topic=None,
                    question_depth_level="basic"
                )
            
            # 3. 전체 맥락 분석 (2개 이상 메시지일 때)
            logger.info(f"🔍 맥락 분석 시작 - {len(recent_messages)}개 메시지로 분석")
            context = await self._analyze_conversation_context(
                recent_messages, 
                current_query, 
                model
            )
            
            return context
            
        except Exception as e:
            logger.error(f"대화 맥락 추출 오류: {e}")
            return ConversationContext()
    
    async def _get_recent_messages(
        self, 
        session_id: str, 
        db_session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """최근 메시지들을 조회합니다."""
        try:
            logger.info(f"🔍 DB 메시지 조회 시작 - session_id: {session_id}, limit: {self.max_recent_messages}")
            
            # messages 테이블에서 최근 메시지 조회
            query = text("""
                SELECT id, role, content, created_at, metadata_
                FROM messages 
                WHERE conversation_id = :session_id
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = await db_session.execute(
                query, 
                {"session_id": session_id, "limit": self.max_recent_messages}
            )
            
            logger.info(f"🔍 DB 쿼리 실행 완료 - session_id: {session_id}")
            
            messages = []
            for row in result:
                # metadata는 이미 dict 타입이므로 JSON 파싱 불필요
                metadata = row.metadata_ if row.metadata_ else {}
                if isinstance(metadata, str):
                    # 만약 문자열로 저장되어 있다면 JSON 파싱
                    try:
                        metadata = json.loads(metadata)
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                        
                message_data = {
                    'id': str(row.id),
                    'role': row.role,
                    'content': row.content,
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                    'metadata': metadata
                }
                messages.append(message_data)
            
            # 시간순으로 정렬 (오래된 것부터)
            messages.reverse()
            return messages
            
        except Exception as e:
            logger.error(f"최근 메시지 조회 오류: {e}")
            return []
    
    async def _analyze_conversation_context(
        self, 
        recent_messages: List[Dict[str, Any]], 
        current_query: str,
        model: str
    ) -> ConversationContext:
        """LLM을 활용하여 대화 맥락을 분석합니다."""
        
        # 메시지 내용만 추출
        message_contents = []
        search_queries = []
        
        for msg in recent_messages:
            message_contents.append(f"{msg['role']}: {msg['content']}")
            
            # 이전 검색어 추출 (메타데이터에서)
            if msg.get('metadata', {}).get('agent_type') == 'web_search':
                queries = msg.get('metadata', {}).get('search_queries', [])
                search_queries.extend(queries)
        
        # 완전 동적 LLM 맥락 분석 프롬프트  
        prompt = f"""
다음은 사용자와 AI의 완전한 대화 기록입니다. 전체 맥락을 분석하여 현재 사용자의 검색 의도를 파악해주세요.

=== 전체 대화 기록 (질문 + AI 답변 포함) ===
{chr(10).join(message_contents)}

=== 현재 사용자 질문 ===
"{current_query}"

=== 이전 검색어 ===
{', '.join(search_queries[-3:]) if search_queries else '없음'}

전체 대화를 분석하여 다음 JSON 형식으로 응답해주세요:
{{
  "domain": "대화 전체를 분석하여 가장 적합한 도메인을 자유롭게 정의 (예: 우주항공공학, 푸드테크, 반려동물행동학 등)",
  "domain_confidence": 0.9,
  "main_domain": "주요 도메인",
  "sub_domains": ["세부 도메인1", "세부 도메인2"],
  "conversation_topics": ["대화에서 다뤄진 핵심 주제들을 자유롭게 추출"],
  "topic_evolution": ["주제가 어떻게 진화했는지 순서대로 나열"],
  "mentioned_entities": ["구체적 엔티티들: 제품명, 기술명, 장소명 등을 자유롭게 추출"],
  "user_intent": "사용자의 의도를 자유롭게 정의 (정보수집, 문제해결, 추천요청, 비교분석, 최신동향파악, 학습목적 등)",
  "context_connection": "현재 질문이 이전 대화와 어떻게 연결되는지 구체적으로 설명",
  "search_focus": "검색에서 중점적으로 찾아야 할 내용을 구체적으로 명시",
  "optimal_search_queries": [
    "첫 번째: 이전 대화 맥락을 완전히 통합한 가장 핵심적인 검색어",
    "두 번째: 위와 다른 각도의 보완적 검색어", 
    "세 번째: 확장된 관점의 추가 검색어"
  ],
  "conversation_flow": "대화 전체 흐름을 한 문장으로 요약",
  "current_focus_topic": "현재 가장 집중하고 있는 주제",
  "question_depth_level": "basic|intermediate|advanced",
  "dynamic_categories": {{
    "complexity": "simple|moderate|complex",
    "urgency": "low|medium|high", 
    "scope": "narrow|broad|comprehensive",
    "novelty": "familiar|emerging|cutting_edge"
  }}
}}

**완전 동적 분석 원칙**:
1. **도메인 자유 정의**: 기존 카테고리에 얽매이지 말고 대화 내용에 가장 적합한 도메인명을 창의적으로 정의
2. **맥락 연결성 중시**: 현재 질문과 이전 대화의 연관성을 깊이 분석
3. **지능적 검색어 생성**: 단순히 현재 질문만 보지 말고, 전체 대화 맥락을 종합하여 사용자가 정말 원하는 정보를 찾을 수 있는 검색어 생성
4. **세분화**: 복잡한 주제는 메인/서브 도메인으로 구분하여 정확성 향상

**특별 케이스 처리**:
- "추천", "신간", "최신", "판매중", "서점" 등이 나오면 이전 대화 주제와 결합
- "이거", "그거", "관련된", "재품" 등 지시어가 나오면 직전 언급된 주제 참조
- 전문 용어나 고유명사가 나오면 해당 분야로 도메인 특정

**🚨 극도로 중요한 최적 검색어 생성 규칙**:
1. optimal_search_queries는 반드시 3개의 구체적 검색어 배열이어야 함
2. 현재 질문 "{current_query}"만 보지 말고, 전체 대화 맥락을 종합해서 생성
3. 예시: 토마토 → 동화 → 서점 판매 = ["토마토 관련 동화책 서점 판매", "토마토 동화책 최신 신간", "토마토 테마 아동도서 구매"]
4. 단순히 현재 질문을 그대로 복사하지 말고, 맥락을 통합한 새로운 검색어 생성

JSON만 응답해주세요.
"""
        
        try:
            logger.info(f"🔍 맥락 분석 시작 - 현재 질문: {current_query}")
            logger.info(f"🔍 대화 기록 수: {len(recent_messages)}")
            
            response, _ = await llm_router.generate_response(model, prompt)
            
            # JSON 파싱
            clean_response = self._clean_json_response(response)
            logger.info(f"🔍 LLM 응답: {clean_response[:500]}...")
            context_data = json.loads(clean_response)
            
            logger.info(f"🔍 분석된 도메인: {context_data.get('domain', 'N/A')}")
            logger.info(f"🔍 최적 검색어: {context_data.get('optimal_search_queries', [])}")
            
            # 새로운 동적 ConversationContext 객체 생성
            context = ConversationContext(
                recent_messages=recent_messages,
                conversation_topics=context_data.get("conversation_topics", []),
                mentioned_entities=context_data.get("mentioned_entities", []),
                previous_search_queries=search_queries[-5:],  # 최근 5개만
                conversation_flow=context_data.get("conversation_flow", ""),
                current_focus_topic=context_data.get("current_focus_topic"),
                question_depth_level=context_data.get("question_depth_level", "basic"),
                
                # 동적 도메인 분류 필드들
                domain=context_data.get("domain", "general"),
                domain_confidence=context_data.get("domain_confidence", 0.5),
                main_domain=context_data.get("main_domain", context_data.get("domain", "general")),
                sub_domains=context_data.get("sub_domains", []),
                topic_evolution=context_data.get("topic_evolution", []),
                user_intent=context_data.get("user_intent", "정보수집"),
                context_connection=context_data.get("context_connection", ""),
                search_focus=context_data.get("search_focus", ""),
                optimal_search_queries=context_data.get("optimal_search_queries", []),
                
                # 다차원 동적 카테고리
                dynamic_categories=context_data.get("dynamic_categories", {
                    "complexity": "simple",
                    "urgency": "low", 
                    "scope": "narrow",
                    "novelty": "familiar"
                })
            )
            
            # 도메인 학습 및 통계 업데이트
            if self.domain_learning_enabled:
                await self._update_domain_learning(context, current_query)
            
            return context
            
        except Exception as e:
            logger.error(f"LLM 맥락 분석 오류: {e}")
            # 기본적인 패턴 기반 분석으로 폴백
            return self._extract_basic_context(recent_messages, current_query, search_queries)
    
    def _clean_json_response(self, response: str) -> str:
        """LLM 응답에서 JSON 부분만 추출합니다."""
        response = response.strip()
        
        # ```json 제거
        if response.startswith('```json'):
            response = response[7:]
        if response.endswith('```'):
            response = response[:-3]
        
        return response.strip()
    
    async def _update_domain_learning(self, context, current_query: str):
        """도메인 학습 및 통계 업데이트"""
        try:
            domain = context.domain
            confidence = context.domain_confidence
            
            # 통계 업데이트
            self.domain_stats["total_classifications"] += 1
            
            if confidence >= self.domain_confidence_threshold:
                self.domain_stats["high_confidence_count"] += 1
            
            # 새로운 도메인 발견
            if domain not in self.domain_stats["discovered_domains"]:
                self.domain_stats["discovered_domains"].add(domain)
                logger.info(f"🆕 새로운 도메인 발견: {domain} (신뢰도: {confidence:.2f})")
            
            # 도메인 빈도 업데이트
            if domain not in self.domain_stats["domain_frequency"]:
                self.domain_stats["domain_frequency"][domain] = 0
            self.domain_stats["domain_frequency"][domain] += 1
            
            # 신뢰도 분포 업데이트
            self.domain_stats["confidence_distribution"].append({
                "domain": domain,
                "confidence": confidence,
                "query": current_query[:50] + "..." if len(current_query) > 50 else current_query,
                "timestamp": datetime.now().isoformat()
            })
            
            # 캐시 크기 제한
            if len(self.domain_stats["confidence_distribution"]) > 100:
                self.domain_stats["confidence_distribution"] = self.domain_stats["confidence_distribution"][-50:]
            
            # 고품질 도메인 분류 캐싱 (신뢰도 높은 것만)
            if confidence >= self.domain_confidence_threshold:
                cache_key = hash(current_query[:100])  # 쿼리 기반 캐시 키
                self.domain_cache[cache_key] = {
                    "domain": domain,
                    "context": context,
                    "confidence": confidence,
                    "cached_at": datetime.now().isoformat()
                }
                
                # 캐시 크기 제한
                if len(self.domain_cache) > self.cache_max_size:
                    # 오래된 캐시 제거 (FIFO)
                    oldest_key = min(self.domain_cache.keys(), 
                                   key=lambda k: self.domain_cache[k]["cached_at"])
                    del self.domain_cache[oldest_key]
            
            # 주기적 로깅 (매 10번째 분류마다)
            if self.domain_stats["total_classifications"] % 10 == 0:
                logger.info(f"""
📊 도메인 학습 현황:
- 총 분류 횟수: {self.domain_stats['total_classifications']}
- 고신뢰도 분류: {self.domain_stats['high_confidence_count']}
- 발견된 도메인: {len(self.domain_stats['discovered_domains'])}
- 상위 도메인: {dict(sorted(self.domain_stats['domain_frequency'].items(), key=lambda x: x[1], reverse=True)[:5])}
""")
                
        except Exception as e:
            logger.error(f"도메인 학습 업데이트 오류: {e}")
    
    def get_domain_statistics(self) -> Dict[str, Any]:
        """도메인 학습 통계 조회"""
        return {
            "total_classifications": self.domain_stats["total_classifications"],
            "high_confidence_count": self.domain_stats["high_confidence_count"],
            "high_confidence_rate": (
                self.domain_stats["high_confidence_count"] / self.domain_stats["total_classifications"]
                if self.domain_stats["total_classifications"] > 0 else 0
            ),
            "discovered_domains": list(self.domain_stats["discovered_domains"]),
            "domain_count": len(self.domain_stats["discovered_domains"]),
            "domain_frequency": self.domain_stats["domain_frequency"],
            "recent_classifications": self.domain_stats["confidence_distribution"][-10:],
            "cache_size": len(self.domain_cache)
        }
    
    def _extract_basic_context(
        self, 
        recent_messages: List[Dict[str, Any]], 
        current_query: str,
        search_queries: List[str]
    ) -> ConversationContext:
        """LLM 분석 실패 시 기본적인 동적 맥락 추출"""
        
        # 간단한 키워드 추출
        all_content = ' '.join([msg['content'] for msg in recent_messages])
        
        # 동적 키워드 추출 (패턴 매칭 없이)
        import re
        korean_keywords = re.findall(r'[가-힣]{2,}', all_content)
        english_keywords = re.findall(r'\b[A-Za-z]{3,}\b', all_content)
        
        # 빈도순 정렬
        from collections import Counter
        all_keywords = korean_keywords + english_keywords
        keyword_freq = Counter(all_keywords)
        top_keywords = [word for word, _ in keyword_freq.most_common(5)]
        
        # 연속성 지시어 감지 (동적)
        continuation_patterns = ['관련된', '이와', '그것', '그거', '추천', '최신', '신간', '더', '자세히']
        has_continuation = any(pattern in current_query for pattern in continuation_patterns)
        
        # 질문 깊이 수준 판단 (동적)
        depth_level = "basic"
        if any(word in current_query for word in ['구체적', '자세히', '심화', '전문적']):
            depth_level = "advanced"
        elif any(word in current_query for word in ['비교', '차이', '분석']):
            depth_level = "intermediate"
        
        return ConversationContext(
            recent_messages=recent_messages,
            conversation_topics=top_keywords[:3],
            mentioned_entities=top_keywords,
            previous_search_queries=search_queries[-5:],
            conversation_flow="동적 패턴 분석 결과",
            current_focus_topic=top_keywords[0] if top_keywords else None,
            question_depth_level=depth_level,
            # 동적 도메인 분류 필드들 (기본값)
            domain="general",
            domain_confidence=0.3,  # 패턴 기반이므로 낮은 신뢰도
            main_domain="general",
            sub_domains=top_keywords[:2] if len(top_keywords) > 1 else [],
            topic_evolution=top_keywords[:3] if top_keywords else [],
            user_intent="정보수집" if not has_continuation else "추가정보요청",
            context_connection="이전 대화와 연관" if has_continuation else "새로운 주제",
            search_focus="주요 키워드 기반 검색",
            optimal_search_queries=[current_query],  # 기본적으로는 현재 질문 사용
            # 다차원 동적 카테고리 (기본값)
            dynamic_categories={
                "complexity": "simple",
                "urgency": "low", 
                "scope": "narrow",
                "novelty": "familiar"
            }
        )


# 전역 인스턴스
universal_context_analyzer = UniversalContextAnalyzer()