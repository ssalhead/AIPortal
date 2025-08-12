"""
AI 에이전트 서비스
"""

from typing import Dict, Any, List, AsyncGenerator
import logging
import asyncio
from datetime import datetime
from app.utils.timezone import now_kst

from app.agents.base import AgentInput
from app.agents.supervisor import supervisor_agent
from app.agents.workers.web_search import web_search_agent
from app.agents.workers.canvas import canvas_agent

logger = logging.getLogger(__name__)


class AgentService:
    """AI 에이전트 서비스"""
    
    def __init__(self):
        self.supervisor = supervisor_agent
        self.agents = {
            "supervisor": supervisor_agent,
            "web_search": web_search_agent,
            "canvas": canvas_agent,
        }
    
    async def execute_chat(
        self, 
        message: str, 
        model: str = "auto",
        agent_type: str = "auto",
        user_id: str = "default_user",
        session_id: str = None,
        context: Dict[str, Any] = None,
        progress_callback = None
    ) -> Dict[str, Any]:
        """
        채팅 메시지 처리 (대화 컨텍스트 지원)
        
        Args:
            message: 사용자 메시지
            model: 사용할 LLM 모델
            agent_type: 에이전트 타입 (auto는 supervisor가 자동 선택)
            user_id: 사용자 ID
            session_id: 대화 세션 ID
            context: 추가 컨텍스트
            progress_callback: 진행 상태 콜백
            
        Returns:
            처리 결과
        """
        try:
            from app.services.conversation_history_service import conversation_history_service
            from app.db.session import AsyncSessionLocal
            from app.db.models.conversation import MessageRole
            
            # 대화 생성 또는 기존 대화 사용
            async with AsyncSessionLocal() as db:
                if session_id:
                    # 기존 대화 확인
                    conversation_detail = await conversation_history_service.get_conversation_detail(
                        conversation_id=session_id,
                        user_id=user_id,
                        session=db
                    )
                    if not conversation_detail:
                        # 대화가 없으면 새로 생성
                        conversation = await conversation_history_service.create_conversation(
                            user_id=user_id,
                            title=f"대화 {now_kst().strftime('%Y-%m-%d %H:%M')}",
                            session=db,
                            model=model,
                            agent_type=agent_type
                        )
                        session_id = conversation['id']
                else:
                    # 새 대화 생성 - 임시 제목으로 생성
                    conversation = await conversation_history_service.create_conversation(
                        user_id=user_id,
                        title=f"대화 {now_kst().strftime('%Y-%m-%d %H:%M')}",
                        session=db,
                        model=model,
                        agent_type=agent_type
                    )
                    session_id = conversation['id']
                
                # 사용자 메시지를 대화 히스토리에 추가
                await conversation_history_service.add_message(
                    conversation_id=session_id,
                    user_id=user_id,
                    role=MessageRole.USER,
                    content=message,
                    session=db
                )
            
            # LLM 라우터를 통한 최적 모델 선택
            from app.agents.llm_router import llm_router
            
            if model == "auto":
                task_type_mapping = {
                    "web_search": "speed",
                    "supervisor": "reasoning",
                    "auto": "general"
                }
                task_type = task_type_mapping.get(agent_type, "general")
                selected_model = llm_router.get_optimal_model(task_type, len(message))
            else:
                selected_model = model
            
            # 대화 컨텍스트 가져오기 (최근 메시지들)
            conversation_context = ""
            async with AsyncSessionLocal() as db:
                conversation_detail = await conversation_history_service.get_conversation_detail(
                    conversation_id=session_id,
                    user_id=user_id,
                    session=db,
                    message_limit=10  # 최근 10개 메시지만
                )
                if conversation_detail and conversation_detail.get('messages'):
                    context_messages = []
                    for msg in conversation_detail['messages'][-6:]:  # 최근 6개만 사용
                        role = "사용자" if msg['role'] == 'USER' else "어시스턴트"
                        context_messages.append(f"{role}: {msg['content']}")
                    if context_messages:
                        conversation_context = "\n".join(context_messages)
            
            # 컨텍스트가 있으면 메시지에 포함
            enhanced_message = message
            if conversation_context:
                enhanced_message = f"대화 기록:\n{conversation_context}\n\n현재 질문: {message}"
            
            # 입력 데이터 생성
            agent_input = AgentInput(
                query=enhanced_message,
                context=context or {"has_conversation_context": bool(conversation_context)},
                user_id=user_id,
                session_id=session_id
            )
            
            # 에이전트 선택 및 실행
            if agent_type == "none":
                # 일반 채팅 모드 - 컨텍스트 포함 LLM 호출
                from app.agents.llm_router import llm_router
                
                # 컨텍스트 포함 응답 생성
                cited_response = await llm_router.generate_response_with_context(
                    message=message,
                    model=selected_model,
                    agent_type=agent_type,
                    user_id=user_id,
                    session_id=session_id,
                    stream=False
                )
                
                # CitedResponse를 AgentOutput 형태로 변환
                class SimpleAgentOutput:
                    def __init__(self, response_text: str, model: str):
                        self.result = response_text
                        self.model_used = model
                        self.timestamp = now_kst().isoformat()
                        self.agent_id = "general_chat"
                        self.metadata = {}
                        self.execution_time_ms = 0
                        self.citations = []
                        self.sources = []
                
                result = SimpleAgentOutput(cited_response.response_text, selected_model)
                
            elif agent_type == "auto" or agent_type == "supervisor":
                # Supervisor가 자동으로 적절한 에이전트 선택
                result = await self.supervisor.execute(agent_input, selected_model, progress_callback)
            else:
                # 특정 에이전트 직접 실행
                agent = self.agents.get(agent_type)
                if not agent:
                    raise ValueError(f"알 수 없는 에이전트 타입: {agent_type}")
                result = await agent.execute(agent_input, selected_model, progress_callback)
            
            # AI 응답을 대화 히스토리에 추가
            async with AsyncSessionLocal() as db:
                await conversation_history_service.add_message(
                    conversation_id=session_id,
                    user_id=user_id,
                    role=MessageRole.ASSISTANT,
                    content=result.result,
                    session=db,
                    model=result.model_used
                )
            
            # 새 대화인 경우 제목 자동 생성 (첫 번째 메시지인지 확인)
            is_new_conversation = False
            try:
                async with AsyncSessionLocal() as db:
                    # 대화의 메시지 개수 확인 (사용자 메시지 + AI 응답 = 2개면 새 대화)
                    conversation_detail = await conversation_history_service.get_conversation_detail(
                        conversation_id=session_id,
                        user_id=user_id,
                        session=db
                    )
                    if conversation_detail and len(conversation_detail.get('messages', [])) == 2:
                        is_new_conversation = True
                        
                        # 제목 자동 생성
                        await self._generate_conversation_title(
                            session_id=session_id,
                            user_message=message,
                            model=model,
                            user_id=user_id
                        )
            except Exception as e:
                logger.error(f"제목 생성 실패: {e}")
                # 제목 생성 실패해도 채팅은 계속 진행
                pass
            
            # 대화 메시지 조회 (사용자 메시지 + AI 응답 포함)
            async with AsyncSessionLocal() as db:
                conversation_detail = await conversation_history_service.get_conversation_detail(
                    conversation_id=session_id,
                    user_id=user_id,
                    session=db
                )
                messages = conversation_detail.get('messages', []) if conversation_detail else []
            
            return {
                "response": result.result,
                "agent_used": result.agent_id,
                "model_used": result.model_used,
                "timestamp": result.timestamp,
                "user_id": user_id,
                "session_id": session_id,  # 대화 ID 반환
                "metadata": result.metadata,
                "execution_time_ms": result.execution_time_ms,
                "citations": getattr(result, 'citations', []),  # citations 추가
                "sources": getattr(result, 'sources', []),  # sources 추가
                "messages": messages,  # 전체 대화 메시지 포함
                "user_message": message  # 현재 사용자 메시지도 포함 (프론트엔드 참조용)
            }
            
        except Exception as e:
            import traceback
            logger.error(f"채팅 처리 중 오류: {e}")
            logger.error(f"스택 트레이스: {traceback.format_exc()}")
            return {
                "response": f"죄송합니다. 메시지 처리 중 오류가 발생했습니다: {str(e)}",
                "agent_used": "error_handler",
                "model_used": "system",
                "timestamp": "2024-01-01T00:00:00Z",
                "user_id": user_id,
                "metadata": {"error": str(e)},
                "execution_time_ms": 0
            }
    
    def get_agent_info(self, agent_id: str = None) -> List[Dict[str, Any]]:
        """
        에이전트 정보 조회
        
        Args:
            agent_id: 특정 에이전트 ID (None이면 전체 목록)
            
        Returns:
            에이전트 정보 목록
        """
        if agent_id:
            agent = self.agents.get(agent_id)
            if not agent:
                return []
            
            return [{
                "id": agent.agent_id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.get_capabilities(),
                "supported_models": agent.get_supported_models(),
                "is_enabled": True
            }]
        
        # 전체 에이전트 목록
        agent_info_list = []
        for agent_id, agent in self.agents.items():
            if agent_id == "supervisor":
                continue  # Supervisor는 내부 에이전트이므로 목록에서 제외
                
            agent_info_list.append({
                "id": agent.agent_id,
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.get_capabilities(),
                "supported_models": agent.get_supported_models(),
                "is_enabled": True
            })
        
        # 아직 구현되지 않은 에이전트들도 추가 (비활성화 상태)
        planned_agents = [
            {
                "id": "deep_research",
                "name": "심층 리서치 에이전트",
                "description": "특정 주제에 대해 심층적인 연구를 수행합니다",
                "capabilities": ["심층 분석", "보고서 생성", "다중 소스 종합"],
                "supported_models": ["claude", "gemini", "claude-haiku", "gemini-flash"],
                "is_enabled": False
            },
            {
                "id": "multimodal_rag",
                "name": "멀티모달 RAG 에이전트",
                "description": "문서와 이미지를 분석하여 답변을 생성합니다",
                "capabilities": ["문서 분석", "이미지 이해", "RAG 검색"],
                "supported_models": ["claude", "gemini", "claude-haiku", "gemini-flash"],
                "is_enabled": False
            }
        ]
        
        agent_info_list.extend(planned_agents)
        return agent_info_list
    
    async def execute_agent_directly(
        self,
        agent_id: str,
        input_data: Dict[str, Any],
        model: str = "auto"
    ) -> Dict[str, Any]:
        """
        특정 에이전트 직접 실행
        
        Args:
            agent_id: 에이전트 ID
            input_data: 입력 데이터
            model: 사용할 모델
            
        Returns:
            실행 결과
        """
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                raise ValueError(f"에이전트 '{agent_id}'를 찾을 수 없습니다")
            
            # AgentInput 생성
            agent_input = AgentInput(
                query=input_data.get("query", ""),
                context=input_data.get("context", {}),
                user_id=input_data.get("user_id", "default_user")
            )
            
            # 에이전트 실행
            result = await agent.execute(agent_input, model)
            
            return {
                "agent_id": result.agent_id,
                "result": {
                    "response": result.result,
                    "metadata": result.metadata
                },
                "execution_time_ms": result.execution_time_ms,
                "model_used": result.model_used
            }
            
        except Exception as e:
            logger.error(f"에이전트 '{agent_id}' 직접 실행 중 오류: {e}")
            return {
                "agent_id": agent_id,
                "result": {
                    "response": f"에이전트 실행 중 오류가 발생했습니다: {str(e)}",
                    "metadata": {"error": str(e)}
                },
                "execution_time_ms": 0,
                "model_used": model
            }
    
    async def stream_response(
        self,
        query: str,
        model: str = "auto",
        agent_type: str = "general",
        conversation_id: str = None,
        user_id: str = "default_user"
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 응답 생성
        
        Args:
            query: 사용자 쿼리
            model: 사용할 모델
            agent_type: 에이전트 타입
            conversation_id: 대화 ID
            user_id: 사용자 ID
            
        Yields:
            응답 텍스트 청크
        """
        try:
            # LLM 라우터를 통한 직접 스트리밍
            from app.agents.llm_router import llm_router
            
            # LLM 라우터를 통한 최적 모델 선택
            if model == "auto":
                # 에이전트 유형에 따른 최적 모델 선택
                task_type_mapping = {
                    "web_search": "speed",
                    "technical": "reasoning", 
                    "creative": "creative",
                    "general": "general"
                }
                task_type = task_type_mapping.get(agent_type, "general")
                normalized_model = llm_router.get_optimal_model(task_type, len(query))
            else:
                # 모델 이름 정규화 (새로운 형식 지원)
                model_mapping = {
                    "claude-3-haiku": "claude-haiku",
                    "claude-3-sonnet": "claude", 
                    "claude-3-5-sonnet": "claude-3.5",
                    "claude-3.5": "claude-3.5",
                    "gemini": "gemini-pro",  # 기존 gemini를 gemini-pro로 매핑
                    "gemini-1.5-pro": "gemini-pro",
                    "gemini-1.0-pro": "gemini-1.0",
                    "gemini-flash": "gemini-flash"
                }
                normalized_model = model_mapping.get(model, model)
            
            # 에이전트별 프롬프트 구성
            if agent_type == "none":
                # 일반 채팅 모드 - 간단한 프롬프트
                prompt = query
            elif agent_type == "web_search":
                prompt = f"웹 검색 요청: {query}\n\n최신 정보를 검색하여 정확하고 유용한 답변을 제공해주세요."
            elif agent_type == "technical":
                prompt = f"기술 질문: {query}\n\n기술적으로 정확하고 실용적인 답변을 제공해주세요."
            else:
                prompt = f"사용자 질문: {query}\n\n친근하고 도움이 되는 답변을 제공해주세요."
            
            # 컨텍스트 정보 추가
            if conversation_id:
                prompt += f"\n\n[대화 ID: {conversation_id}]"
            if user_id:
                prompt += f"\n[사용자 ID: {user_id}]"
            
            # LLM 라우터를 통한 스트리밍
            async for chunk in llm_router.stream_response(normalized_model, prompt):
                yield chunk
                
        except Exception as e:
            logger.error(f"스트리밍 응답 생성 중 오류: {e}")
            yield f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"
    
    async def _generate_conversation_title(
        self,
        session_id: str,
        user_message: str, 
        model: str,
        user_id: str
    ):
        """
        대화 제목 자동 생성
        
        Args:
            session_id: 세션 ID
            user_message: 첫 번째 사용자 메시지
            model: 사용할 모델
            user_id: 사용자 ID
        """
        try:
            from app.agents.llm_router import llm_router
            
            # 제목 생성을 위한 프롬프트
            title_prompt = f"""다음 사용자의 질문이나 요청을 바탕으로 대화의 제목을 생성해주세요.

사용자 메시지: "{user_message}"

제목 생성 규칙:
1. 50자 이내로 작성
2. 구체적이고 명확하게 작성
3. 한국어로 작성
4. 질문의 핵심 내용을 담아서 작성
5. "대화", "채팅" 같은 일반적인 단어는 피하고 구체적인 내용으로 작성

제목만 응답하고 다른 설명은 하지 마세요."""

            # LLM을 통해 제목 생성
            response_content, used_model = await llm_router.generate_response(
                model_name=model,
                prompt=title_prompt,
                user_id=user_id,
                conversation_id=None
            )
            
            # 생성된 제목 정리
            generated_title = response_content.strip()
            
            # 따옴표 제거
            if generated_title.startswith('"') and generated_title.endswith('"'):
                generated_title = generated_title[1:-1]
            
            # 길이 제한
            if len(generated_title) > 50:
                generated_title = generated_title[:47] + "..."
            
            # 제목 업데이트
            from app.db.session import AsyncSessionLocal
            from app.services.conversation_history_service import conversation_history_service
            
            async with AsyncSessionLocal() as db:
                await conversation_history_service.update_conversation_title(
                    conversation_id=session_id,
                    user_id=user_id,
                    title=generated_title,
                    session=db
                )
                
            logger.info(f"대화 제목 자동 생성 완료: {generated_title}")
            
        except Exception as e:
            logger.error(f"제목 자동 생성 실패: {e}")
            # 실패 시 기본 제목으로 폴백
            try:
                fallback_title = user_message[:30] + ("..." if len(user_message) > 30 else "")
                from app.db.session import AsyncSessionLocal
                from app.services.conversation_history_service import conversation_history_service
                
                async with AsyncSessionLocal() as db:
                    await conversation_history_service.update_conversation_title(
                        conversation_id=session_id,
                        user_id=user_id,
                        title=fallback_title,
                        session=db
                    )
                logger.info(f"기본 제목으로 폴백: {fallback_title}")
            except Exception as fallback_error:
                logger.error(f"폴백 제목 설정 실패: {fallback_error}")


# 서비스 인스턴스
agent_service = AgentService()