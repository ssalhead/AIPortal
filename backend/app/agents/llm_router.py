"""
LLM 모델 라우터
"""

from typing import Optional, Dict, Any, AsyncGenerator, List
from langchain_aws import ChatBedrock
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseLanguageModel
import logging
import boto3
from datetime import datetime

from app.core.config import settings
from app.agents.mock_llm import mock_llm
from app.services.logging_service import logging_service, log_llm_usage

logger = logging.getLogger(__name__)


class LLMRouter:
    """LLM 모델 라우터 클래스"""
    
    def __init__(self):
        self._models: Dict[str, BaseLanguageModel] = {}
        self._initialize_models()
    
    def _initialize_models(self):
        """사용 가능한 모델들을 초기화"""
        try:
            # AWS Bedrock Claude 모델 초기화
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                try:
                    # Bedrock 클라이언트 생성
                    bedrock_client = boto3.client(
                        service_name="bedrock-runtime",
                        region_name=settings.AWS_REGION,
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    )
                    
                    # Claude Sonnet 4.0 (최신 모델) - inference profile 사용
                    self._models["claude-4"] = ChatBedrock(
                        client=bedrock_client,
                        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
                        model_kwargs={
                            "temperature": 0.7,
                            "max_tokens": 4096,
                            "top_p": 0.9,
                        }
                    )
                    logger.info("AWS Bedrock Claude 4.0 Sonnet 모델 초기화 완료")
                    
                    # Claude 3.7 Sonnet - inference profile 사용
                    self._models["claude-3.7"] = ChatBedrock(
                        client=bedrock_client,
                        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                        model_kwargs={
                            "temperature": 0.7,
                            "max_tokens": 4096,
                            "top_p": 0.9,
                        }
                    )
                    logger.info("AWS Bedrock Claude 3.7 Sonnet 모델 초기화 완료")
                    
                    # Claude 3.5 Sonnet (기본 모델)
                    self._models["claude"] = ChatBedrock(
                        client=bedrock_client,
                        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                        model_kwargs={
                            "temperature": 0.7,
                            "max_tokens": 4096,
                            "top_p": 0.9,
                        }
                    )
                    logger.info("AWS Bedrock Claude 3.5 Sonnet 모델 초기화 완료")
                    
                    # Claude 3.5 Sonnet (별칭 - 명시적 버전)
                    self._models["claude-3.5"] = ChatBedrock(
                        client=bedrock_client,
                        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                        model_kwargs={
                            "temperature": 0.7,
                            "max_tokens": 4096,
                            "top_p": 0.9,
                        }
                    )
                    logger.info("AWS Bedrock Claude 3.5 Sonnet (별칭) 모델 초기화 완료")
                    
                    # Claude 3.5 Haiku (빠른 응답용)
                    self._models["claude-haiku"] = ChatBedrock(
                        client=bedrock_client,
                        model_id="anthropic.claude-3-haiku-20240307-v1:0",
                        model_kwargs={
                            "temperature": 0.7,
                            "max_tokens": 4096,
                        }
                    )
                    logger.info("AWS Bedrock Claude 3.5 Haiku 모델 초기화 완료")
                    
                except Exception as e:
                    logger.error(f"AWS Bedrock 초기화 실패: {e}")
            else:
                logger.warning("AWS 인증 정보가 설정되지 않음 - Claude 모델 사용 불가")
            
            # GCP Gemini 모델 초기화
            if settings.GOOGLE_API_KEY:
                try:
                    # Gemini Pro 1.5
                    self._models["gemini-pro"] = ChatGoogleGenerativeAI(
                        model="gemini-1.5-pro",
                        google_api_key=settings.GOOGLE_API_KEY,
                        temperature=0.7,
                        max_output_tokens=8192,
                        top_p=0.9,
                    )
                    logger.info("Google Gemini 1.5 Pro 모델 초기화 완료")
                    
                    # Gemini Flash (더 빠른 응답용)
                    self._models["gemini-flash"] = ChatGoogleGenerativeAI(
                        model="gemini-1.5-flash",
                        google_api_key=settings.GOOGLE_API_KEY,
                        temperature=0.7,
                        max_output_tokens=8192,
                    )
                    logger.info("Google Gemini 1.5 Flash 모델 초기화 완료")
                    
                    # Gemini 1.0 Pro (기본 모델)
                    self._models["gemini-1.0"] = ChatGoogleGenerativeAI(
                        model="gemini-1.0-pro",
                        google_api_key=settings.GOOGLE_API_KEY,
                        temperature=0.7,
                        max_output_tokens=8192,
                    )
                    logger.info("Google Gemini 1.0 Pro 모델 초기화 완료")
                    
                    # Gemini 기본 별칭 (gemini-pro로 매핑)
                    self._models["gemini"] = self._models["gemini-pro"]
                    logger.info("Google Gemini 기본 별칭 설정 완료")
                    
                except Exception as e:
                    logger.error(f"Google Gemini 초기화 실패: {e}")
            else:
                logger.warning("GOOGLE_API_KEY가 설정되지 않음 - Gemini 모델 사용 불가")
                
        except Exception as e:
            logger.error(f"모델 초기화 중 오류 발생: {e}")
    
    def get_model(self, model_name: str) -> Optional[BaseLanguageModel]:
        """
        지정된 모델 반환
        
        Args:
            model_name: 모델 이름 (claude, claude-haiku, gemini, gemini-flash)
            
        Returns:
            언어 모델 인스턴스 또는 None
        """
        model = self._models.get(model_name.lower())
        if model is None:
            logger.warning(f"모델 '{model_name}'을 찾을 수 없음")
            # 사용 가능한 다른 모델로 fallback
            return self.get_fallback_model()
        return model
    
    def get_fallback_model(self) -> Optional[BaseLanguageModel]:
        """
        사용 가능한 fallback 모델 반환
        
        Returns:
            언어 모델 인스턴스 또는 None
        """
        # 우선순위: gemini-pro > gemini-flash > gemini-1.0 > claude-4 > claude-3.7 > claude-3.5 > claude > claude-haiku (Gemini 우선 - 안정성)
        for model_name in ["gemini-pro", "gemini-flash", "gemini-1.0", "claude-4", "claude-3.7", "claude-3.5", "claude", "claude-haiku"]:
            if model_name in self._models:
                logger.info(f"Fallback 모델로 {model_name} 사용")
                return self._models[model_name]
        
        logger.error("사용 가능한 모델이 없음")
        return None
    
    def get_available_models(self) -> list[str]:
        """
        사용 가능한 모델 목록 반환
        
        Returns:
            모델 이름 목록
        """
        return list(self._models.keys())
    
    def is_model_available(self, model_name: str) -> bool:
        """
        모델 사용 가능 여부 확인
        
        Args:
            model_name: 모델 이름
            
        Returns:
            사용 가능 여부
        """
        return model_name.lower() in self._models

    def get_optimal_model(self, task_type: str = "general", context_length: int = 0) -> str:
        """
        작업 유형에 따른 최적 모델 선택
        
        Args:
            task_type: 작업 유형 (general, reasoning, speed, creative, coding)
            context_length: 컨텍스트 길이
            
        Returns:
            최적 모델 이름
        """
        available_models = self.get_available_models()
        
        if not available_models:
            return "mock-general"
        
        # 작업 유형별 모델 우선순위 (Claude 4.0 > 3.7 > 3.5 > Gemini Pro 순서)
        model_preferences = {
            "reasoning": ["claude-4", "claude-3.7", "claude-3.5", "claude", "gemini-pro", "claude-haiku", "gemini-flash", "gemini-1.0"],
            "creative": ["claude-4", "claude-3.7", "claude-3.5", "claude", "gemini-pro", "gemini-flash", "claude-haiku", "gemini-1.0"],
            "coding": ["claude-4", "claude-3.7", "claude-3.5", "claude", "gemini-pro", "claude-haiku", "gemini-flash", "gemini-1.0"],
            "speed": ["claude-haiku", "gemini-flash", "gemini-pro", "claude-3.5", "claude", "claude-3.7", "claude-4", "gemini-1.0"],
            "general": ["claude-4", "claude-3.7", "claude-3.5", "claude", "gemini-pro", "claude-haiku", "gemini-flash", "gemini-1.0"]
        }
        
        preferred_models = model_preferences.get(task_type, model_preferences["general"])
        
        # 사용 가능한 모델 중에서 첫 번째 우선순위 모델 선택
        for model in preferred_models:
            if model in available_models:
                logger.info(f"작업 유형 '{task_type}'에 대해 '{model}' 모델 선택")
                return model
        
        # fallback
        return available_models[0] if available_models else "mock-general"

    def is_mock_mode(self) -> bool:
        """Mock 모드 여부 확인"""
        return (
            not any([
                settings.GOOGLE_API_KEY, 
                (settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)
            ]) or
            getattr(settings, 'MOCK_LLM_ENABLED', False)
        )

    @log_llm_usage
    async def generate_response(
        self, 
        model_name: str, 
        prompt: str, 
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> tuple[str, str]:
        """
        모델을 사용하여 응답 생성
        
        Args:
            model_name: 사용할 모델 이름
            prompt: 프롬프트
            user_id: 사용자 ID (로깅용)
            conversation_id: 대화 ID (로깅용)
            **kwargs: 추가 파라미터
            
        Returns:
            (응답 텍스트, 실제 사용된 모델 이름)
        """
        # Mock 모드 확인
        if self.is_mock_mode():
            logger.info(f"Mock 모드로 응답 생성 - 요청된 모델: {model_name}")
            mock_model_name = f"mock-{model_name.lower()}"
            response = mock_llm.generate_response(prompt, mock_model_name)
            return response, mock_model_name
        
        model = self.get_model(model_name)
        if model is None:
            raise ValueError(f"모델 '{model_name}'을 사용할 수 없습니다")
        
        try:
            # 실제 모델 호출
            response = await model.ainvoke(prompt)
            return response.content, model_name
            
        except Exception as e:
            logger.error(f"모델 '{model_name}' 응답 생성 중 오류: {e}")
            
            # Mock 모드로 fallback
            logger.warning(f"실제 API 호출 실패, Mock 응답으로 대체: {e}")
            mock_model_name = f"mock-{model_name.lower()}-fallback"
            response = mock_llm.generate_response(
                prompt, 
                f"{mock_model_name} (API 오류로 인한 Mock 응답)"
            )
            return response, mock_model_name

    async def generate_response_with_context(
        self,
        message: str,
        model: str,
        agent_type: str,
        user_id: str,
        session_id: Optional[str] = None,
        stream: bool = False
    ):
        """
        컨텍스트를 포함한 응답 생성
        
        Args:
            message: 사용자 메시지
            model: 사용할 모델
            agent_type: 에이전트 타입
            user_id: 사용자 ID
            session_id: 세션 ID (컨텍스트 로딩용)
            stream: 스트리밍 여부
            
        Returns:
            응답 객체
        """
        try:
            # 컨텍스트 포함 프롬프트 구성
            final_prompt = await self._build_prompt_with_context(
                message=message,
                session_id=session_id,
                user_id=user_id,
                agent_type=agent_type
            )
            
            # 기존 generate_response 메서드 호출
            response_content, used_model = await self.generate_response(
                model_name=model,
                prompt=final_prompt,
                user_id=user_id,
                conversation_id=session_id
            )
            
            # 응답 객체 구성
            from app.models.citation import CitedResponse
            
            return CitedResponse(
                response_text=response_content,
                sources=[],
                total_sources=0,
                citation_count=0,
                citations=[]
            )
            
        except Exception as e:
            logger.error(f"컨텍스트 포함 응답 생성 실패: {e}")
            # 컨텍스트 없이 재시도
            response_content, used_model = await self.generate_response(
                model_name=model,
                prompt=message,
                user_id=user_id,
                conversation_id=session_id
            )
            
            from app.models.citation import CitedResponse
            
            return CitedResponse(
                response_text=response_content,
                sources=[],
                total_sources=0,
                citation_count=0,
                citations=[]
            )
    
    async def _build_prompt_with_context(
        self,
        message: str,
        session_id: Optional[str],
        user_id: str,
        agent_type: str
    ) -> str:
        """컨텍스트를 포함한 프롬프트 구성"""
        
        # 세션 ID가 없으면 컨텍스트 없이 진행 (제목 생성 시에는 session_id가 None)
        if not session_id:
            return message
        
        try:
            from app.services.conversation_memory_service import conversation_memory_service
            
            # 대화 컨텍스트 조회
            context_data = await conversation_memory_service.get_conversation_context(
                conversation_id=session_id,
                user_id=user_id
            )
            
            context_prompt = context_data.get('context_prompt', '')
            total_tokens = context_data.get('total_tokens', 0)
            
            # 토큰 제한 확인
            if total_tokens > 3000:  # 토큰 제한 초과시 컨텍스트 단축
                logger.warning(f"컨텍스트 토큰 수 초과: {total_tokens}, 단축 처리")
                # 단기메모리만 사용
                short_term = context_data.get('short_term_memory', [])
                if short_term:
                    context_prompt = self._build_short_context(short_term[-2:])  # 최근 2개만
            
            # 컨텍스트가 있는 경우 프롬프트에 포함
            if context_prompt:
                final_prompt = f"""{context_prompt}

현재 사용자 질문: {message}

위 대화 맥락을 고려하여 답변해주세요."""
                
                logger.info(f"컨텍스트 포함 프롬프트 생성 완료 (예상 토큰: {total_tokens})")
                return final_prompt
            else:
                return message
                
        except Exception as e:
            logger.error(f"컨텍스트 구성 실패: {e}")
            return message
    
    def _build_short_context(self, qa_pairs: List[Dict]) -> str:
        """단축된 컨텍스트 구성"""
        if not qa_pairs:
            return ""
        
        context_parts = ["[최근 대화]"]
        for pair in qa_pairs:
            context_parts.append(f"사용자: {pair['question']}")
            if pair['answer']:
                context_parts.append(f"AI: {pair['answer']}")
        
        return "\n".join(context_parts)

    async def stream_response(
        self,
        model_name: str,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        스트리밍 응답 생성
        
        Args:
            model_name: 사용할 모델 이름
            prompt: 프롬프트
            **kwargs: 추가 파라미터
            
        Yields:
            응답 텍스트 청크
        """
        # Mock 모드 확인
        if self.is_mock_mode():
            logger.info(f"Mock 스트리밍 응답 생성 - 요청된 모델: {model_name}")
            mock_model_name = f"mock-{model_name.lower()}"
            async for chunk in mock_llm.stream_response(prompt, mock_model_name):
                yield chunk
            return
        
        model = self.get_model(model_name)
        if model is None:
            # Mock으로 fallback
            async for chunk in mock_llm.stream_response(prompt, f"mock-{model_name}-unavailable"):
                yield chunk
            return
        
        try:
            # 실제 스트리밍 (LangChain 모델이 스트리밍을 지원하는 경우)
            if hasattr(model, 'astream'):
                async for chunk in model.astream(prompt):
                    if hasattr(chunk, 'content'):
                        yield chunk.content
                    else:
                        yield str(chunk)
            else:
                # 스트리밍을 지원하지 않는 경우 일반 응답을 청크로 나누어 전송
                response = await model.ainvoke(prompt)
                content = response.content
                
                # 단어별로 스트리밍 시뮬레이션
                import asyncio
                words = content.split()
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield chunk
                    await asyncio.sleep(0.03)  # 스트리밍 딜레이
                    
        except Exception as e:
            logger.error(f"스트리밍 응답 생성 중 오류: {e}")
            # Mock 스트리밍으로 fallback
            async for chunk in mock_llm.stream_response(
                prompt, 
                f"mock-{model_name}-error-fallback"
            ):
                yield chunk


# 싱글톤 인스턴스
llm_router = LLMRouter()