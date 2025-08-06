"""
LLM 모델 라우터
"""

from typing import Optional, Dict, Any, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseLanguageModel
import logging

from app.core.config import settings
from app.agents.mock_llm import mock_llm

logger = logging.getLogger(__name__)


class LLMRouter:
    """LLM 모델 라우터 클래스"""
    
    def __init__(self):
        self._models: Dict[str, BaseLanguageModel] = {}
        self._initialize_models()
    
    def _initialize_models(self):
        """사용 가능한 모델들을 초기화"""
        try:
            # Gemini 모델 초기화
            if settings.GOOGLE_API_KEY:
                self._models["gemini"] = ChatGoogleGenerativeAI(
                    model="gemini-pro",
                    google_api_key=settings.GOOGLE_API_KEY,
                    temperature=0.7,
                    max_tokens=2048
                )
                logger.info("Gemini 모델 초기화 완료")
            else:
                logger.warning("GOOGLE_API_KEY가 설정되지 않음 - Gemini 모델 사용 불가")
            
            # Claude 모델 초기화
            if settings.ANTHROPIC_API_KEY:
                self._models["claude"] = ChatAnthropic(
                    model="claude-3-sonnet-20240229",
                    anthropic_api_key=settings.ANTHROPIC_API_KEY,
                    temperature=0.7,
                    max_tokens=2048
                )
                logger.info("Claude 모델 초기화 완료")
            else:
                logger.warning("ANTHROPIC_API_KEY가 설정되지 않음 - Claude 모델 사용 불가")
            
            # OpenAI 모델 초기화 (fallback)
            if settings.OPENAI_API_KEY:
                self._models["openai"] = ChatOpenAI(
                    model="gpt-3.5-turbo",
                    openai_api_key=settings.OPENAI_API_KEY,
                    temperature=0.7,
                    max_tokens=2048
                )
                logger.info("OpenAI 모델 초기화 완료")
            else:
                logger.warning("OPENAI_API_KEY가 설정되지 않음 - OpenAI 모델 사용 불가")
                
        except Exception as e:
            logger.error(f"모델 초기화 중 오류 발생: {e}")
    
    def get_model(self, model_name: str) -> Optional[BaseLanguageModel]:
        """
        지정된 모델 반환
        
        Args:
            model_name: 모델 이름 (gemini, claude, openai)
            
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
        # 우선순위: gemini > claude > openai
        for model_name in ["gemini", "claude", "openai"]:
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

    def is_mock_mode(self) -> bool:
        """Mock 모드 여부 확인"""
        return (
            not any([settings.GOOGLE_API_KEY, settings.ANTHROPIC_API_KEY, settings.OPENAI_API_KEY]) or
            getattr(settings, 'MOCK_LLM_ENABLED', False)
        )

    async def generate_response(
        self, 
        model_name: str, 
        prompt: str, 
        **kwargs
    ) -> tuple[str, str]:
        """
        모델을 사용하여 응답 생성
        
        Args:
            model_name: 사용할 모델 이름
            prompt: 프롬프트
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