"""
LLM 모델 라우터
"""

from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import BaseLanguageModel
import logging

from app.core.config import settings

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
        model = self.get_model(model_name)
        if model is None:
            raise ValueError(f"모델 '{model_name}'을 사용할 수 없습니다")
        
        try:
            # Mock 응답 (실제 API 키가 없는 경우)
            if not any([settings.GOOGLE_API_KEY, settings.ANTHROPIC_API_KEY, settings.OPENAI_API_KEY]):
                logger.info(f"Mock 응답 생성 - 요청된 모델: {model_name}")
                return (
                    f"안녕하세요! {model_name} 모델을 사용한 Mock 응답입니다. "
                    f"실제 API 키를 설정하면 진짜 AI 응답을 받을 수 있습니다. "
                    f"프롬프트: {prompt[:100]}...",
                    model_name
                )
            
            # 실제 모델 호출
            response = await model.ainvoke(prompt)
            return response.content, model_name
            
        except Exception as e:
            logger.error(f"모델 '{model_name}' 응답 생성 중 오류: {e}")
            # Fallback 시도
            fallback_model = self.get_fallback_model()
            if fallback_model and fallback_model != model:
                try:
                    response = await fallback_model.ainvoke(prompt)
                    fallback_name = next(
                        name for name, m in self._models.items() if m == fallback_model
                    )
                    return response.content, fallback_name
                except Exception as fe:
                    logger.error(f"Fallback 모델 응답 생성 중 오류: {fe}")
            
            raise e


# 싱글톤 인스턴스
llm_router = LLMRouter()