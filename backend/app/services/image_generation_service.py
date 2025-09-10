"""
GCP Imagen 4 이미지 생성 서비스
"""

import asyncio
import json
import uuid
import time
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import base64
from pathlib import Path
import os
import aiofiles

from app.core.config import settings
from app.services.cache_manager import cache_manager
from app.db.session import AsyncSessionLocal
from app.db.models.image_generation import GeneratedImage
from sqlalchemy.ext.asyncio import AsyncSession

# Logger 초기화 (import 오류 처리를 위해 먼저 정의)
logger = logging.getLogger(__name__)

# Google GenAI 클라이언트 import (Imagen 4용)
try:
    from google import genai
    from google.genai.types import (
        GenerateImagesConfig,
        GenerateContentConfig,
        EditImageConfig,
        EditMode,
        RawReferenceImage,
        MaskReferenceImage,
        StyleReferenceImage,
        SubjectReferenceImage,
        ControlReferenceImage,
        MaskReferenceConfig,
        Image
    )
except ImportError:
    logger.warning("google-genai 라이브러리가 설치되지 않음. 'pip install google-genai'로 설치해주세요.")
    genai = None
    GenerateImagesConfig = None
    EditImageConfig = None
    RawReferenceImage = None
    MaskReferenceImage = None

# PIL 이미지 처리용
try:
    from PIL import Image as PILImage
except ImportError:
    logger.warning("PIL 라이브러리가 설치되지 않음. 'pip install pillow'로 설치해주세요.")
    PILImage = None


class ImageGenerationService:
    """GCP Imagen 4 전용 이미지 생성 서비스"""
    
    def __init__(self):
        self.jobs_cache: Dict[str, Dict[str, Any]] = {}
        self.max_daily_generations = 50  # 사용자당 일일 최대 생성 수
        self.model_id = "imagen-4.0-generate-001"  # Imagen 4 생성용 모델 ID
        self.edit_model_id = "imagen-3.0-capability-001"  # 편집용 모델 ID
        
        # Vertex AI 설정
        self.google_project_id = settings.GOOGLE_CLOUD_PROJECT
        self.google_location = settings.GOOGLE_CLOUD_LOCATION
        self.google_api_key = settings.GOOGLE_API_KEY
        self.google_credentials = settings.GOOGLE_APPLICATION_CREDENTIALS
        
        # Google GenAI 클라이언트 초기화 (Vertex AI 우선)
        self.client = None
        self.use_vertex_ai = settings.use_vertex_ai
        
        # Gemini 2.5 Flash Image Preview 클라이언트 초기화
        self.gemini_client = None
        self.gemini_client = None
        self.gemini_model_id = "gemini-2.5-flash-image-preview"
        
        if 'genai' in globals() and globals()['genai']:
            try:
                if self.use_vertex_ai and self.google_project_id:
                    # Vertex AI 클라이언트 사용 - 서비스 계정 키 설정
                    logger.info(f"🔧 Vertex AI 클라이언트 초기화 시도 (Project: {self.google_project_id}, Location: {self.google_location})")
                    
                    # 환경 변수로 서비스 계정 키 설정
                    if self.google_credentials:
                        # 상대 경로를 절대 경로로 변환
                        if not os.path.isabs(self.google_credentials):
                            abs_path = os.path.abspath(self.google_credentials)
                            logger.info(f"🔄 상대 경로를 절대 경로로 변환: {self.google_credentials} → {abs_path}")
                            self.google_credentials = abs_path
                        
                        # 파일 존재 여부 확인
                        if os.path.exists(self.google_credentials):
                            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.google_credentials
                            logger.info(f"🔑 Google 서비스 계정 키 설정: {self.google_credentials}")
                        else:
                            logger.error(f"❌ 서비스 계정 키 파일을 찾을 수 없음: {self.google_credentials}")
                            raise FileNotFoundError(f"서비스 계정 키 파일 없음: {self.google_credentials}")
                    
                    self.client = genai.Client(
                        vertexai=True,
                        project=self.google_project_id,
                        location=self.google_location
                    )
                    logger.info("✅ Vertex AI 클라이언트 초기화 성공 - edit_image API 사용 가능")
                elif self.google_api_key:
                    # Developer API 클라이언트 사용 (edit_image 기능 제한)
                    logger.warning("⚠️ Vertex AI 설정 누락 - Developer API 클라이언트 사용 (edit_image 기능 제한)")
                    self.client = genai.Client(api_key=self.google_api_key)
                    self.use_vertex_ai = False
                    logger.info("✅ Developer API 클라이언트 초기화 성공 - generate_images만 사용 가능")
                else:
                    logger.error("❌ Google API 키 및 Vertex AI 설정 모두 누락")
                    self.client = None
                    
            except Exception as e:
                logger.error(f"❌ Google GenAI 클라이언트 초기화 실패: {e}")
                self.client = None
                self.use_vertex_ai = False
        else:
            logger.warning("⚠️ google-genai 라이브러리 없음 - Mock 이미지 생성만 가능")
        
        # Gemini 2.5 Flash Image Preview 모델 초기화 (Vertex AI 방식)
        try:
            if genai and self.use_vertex_ai and self.google_project_id:
                # Vertex AI 클라이언트 사용 - 이미지 생성을 위한 설정
                logger.info(f"🔧 Gemini Vertex AI 클라이언트 초기화 시도 (Project: {self.google_project_id}, Location: global)")
                
                # 서비스 계정 키 설정
                if self.google_credentials:
                    if not os.path.isabs(self.google_credentials):
                        abs_path = os.path.abspath(self.google_credentials)
                        self.google_credentials = abs_path
                    
                    if os.path.exists(self.google_credentials):
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.google_credentials
                        logger.info(f"🔑 Gemini용 Google 서비스 계정 키 설정: {self.google_credentials}")
                        
                        # 사용자 제공 해결책 적용: credentials 명시적 로드
                        try:
                            from google.oauth2 import service_account
                        except ImportError:
                            # fallback to google.auth.service_account
                            from google.auth import service_account
                        
                        credentials = service_account.Credentials.from_service_account_file(
                            self.google_credentials,
                            scopes=['https://www.googleapis.com/auth/cloud-platform']
                        )
                        
                        # Vertex AI 클라이언트 초기화 (credentials 명시적 전달)
                        # Gemini 2.5 Flash Image Preview는 global 리전 사용 필요
                        self.gemini_client = genai.Client(
                            location="global",  # Image Preview 모델은 global 리전 사용
                            project=self.google_project_id,
                            credentials=credentials,
                            vertexai=True
                        )
                        logger.info(f"✅ Gemini Vertex AI 클라이언트 초기화 성공 (credentials 명시적 전달): {self.gemini_model_id}")
                    else:
                        logger.error(f"❌ Gemini용 서비스 계정 키 파일을 찾을 수 없음: {self.google_credentials}")
                        self.gemini_client = None
                else:
                    logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS 설정 필요")
                    self.gemini_client = None
            elif genai and self.google_api_key:
                # Developer API 클라이언트 사용 (제한된 기능)
                logger.warning("⚠️ Vertex AI 설정 누락 - Developer API 클라이언트 사용 (이미지 생성 제한)")
                self.gemini_client = genai.Client(api_key=self.google_api_key)
                logger.info("✅ Gemini Developer API 클라이언트 초기화 성공 (제한된 기능)")
            else:
                if not genai:
                    logger.warning("⚠️ google-genai 라이브러리가 import되지 않음")
                if not self.google_api_key:
                    logger.warning("⚠️ Google API Key 없음")
                if not self.google_project_id:
                    logger.warning("⚠️ Google Project ID 없음")
                self.gemini_client = None
                
        except Exception as e:
            logger.error(f"❌ Gemini 클라이언트 초기화 실패: {e}")
            self.gemini_client = None
    
    async def generate_image(
        self,
        job_id: str,
        user_id: str,
        prompt: str,
        negative_prompt: Optional[str] = None,
        style: str = "realistic",
        size: str = "512x512",
        quality: str = "standard",
        num_images: int = 1,
        model: str = "imagen-4"
    ) -> Dict[str, Any]:
        """
        Imagen 4 이미지 생성
        
        Args:
            job_id: 작업 ID
            user_id: 사용자 ID
            prompt: 생성 프롬프트
            negative_prompt: 네거티브 프롬프트 (Imagen 4는 지원하지 않으므로 무시)
            style: 이미지 스타일
            size: 이미지 크기
            quality: 품질 (Imagen 4에서는 해상도로 처리)
            num_images: 생성할 이미지 수 (최대 4개)
            model: 모델명 (imagen-4 고정)
            
        Returns:
            생성 결과
        """
        
        try:
            # 크기와 종횡비 변환
            sample_image_size, aspect_ratio = self._convert_size_for_imagen4(size)
            
            # 작업 정보 저장
            job_info = {
                "job_id": job_id,
                "user_id": user_id,
                "prompt": prompt,
                "style": style,
                "sample_image_size": sample_image_size,
                "aspect_ratio": aspect_ratio,
                "num_images": min(num_images, 4),  # Imagen 4는 최대 4개
                "model": self.model_id,
                "status": "processing",
                "images": [],
                "created_at": datetime.utcnow().isoformat(),
                "estimated_completion_time": (datetime.utcnow() + timedelta(seconds=30)).isoformat()
            }
            
            self.jobs_cache[job_id] = job_info
            
            # 동기적으로 이미지 생성 완료 대기
            await self._generate_image_async(job_id)
            
            # 완성된 결과 반환
            final_job_info = self.jobs_cache.get(job_id, job_info)
            
            if final_job_info.get("status") == "completed" and final_job_info.get("images"):
                return {
                    "status": "completed",
                    "images": final_job_info["images"],
                    "safety_score": final_job_info.get("safety_score", 1.0),
                    "metadata": {
                        "model": self.model_id,
                        "style": style,
                        "size": size,
                        "sample_image_size": sample_image_size,
                        "aspect_ratio": aspect_ratio,
                        "generation_method": final_job_info.get("generation_method", "imagen-4")
                    }
                }
            else:
                # 생성 실패
                error_msg = final_job_info.get("error_message", "알 수 없는 오류")
                logger.error(f"❌ 이미지 생성 최종 실패: {error_msg}")
                raise Exception(f"이미지 생성 실패: {error_msg}")
            
        except Exception as e:
            logger.error(f"이미지 생성 시작 실패: {e}")
            # 작업 상태를 실패로 업데이트
            if job_id in self.jobs_cache:
                self.jobs_cache[job_id]["status"] = "failed"
                self.jobs_cache[job_id]["error_message"] = str(e)
            
            raise e
    
    async def _generate_image_async(self, job_id: str):
        """비동기 Imagen 4 이미지 생성 작업 (강화된 디버깅)"""
        
        try:
            job_info = self.jobs_cache.get(job_id)
            if not job_info:
                logger.error(f"❌ 작업 정보를 찾을 수 없음: {job_id}")
                return
            
            logger.info(f"🎨 Imagen 4 이미지 생성 시작: {job_id}")
            logger.debug(f"📋 작업 정보: prompt='{job_info['prompt'][:50]}...', style={job_info.get('style')}, size={job_info.get('sample_image_size')}")
            
            images = []
            
            # Imagen 4로 이미지 생성 (Google GenAI 클라이언트 필수)
            if not self.client:
                raise ValueError("Imagen 4 클라이언트가 초기화되지 않았습니다. API 키를 확인해주세요.")
            
            logger.info(f"🚀 Imagen 4 API 클라이언트로 생성 시작")
            images = await self._generate_with_imagen4(job_info)
            logger.info(f"✅ Imagen 4 API 생성 성공: {len(images)}개 이미지")
            
            # 이미지 생성 결과 검증
            if not images or len(images) == 0:
                raise ValueError("이미지 생성 결과가 비어있습니다")
            
            # 이미지 URL 유효성 검증
            valid_images = []
            for i, image_url in enumerate(images):
                if isinstance(image_url, str) and (image_url.startswith('http') or image_url.startswith('data:')):
                    valid_images.append(image_url)
                    logger.debug(f"✅ 유효한 이미지 URL {i}: {image_url[:50]}...")
                else:
                    logger.warning(f"⚠️ 무효한 이미지 URL {i}: {type(image_url)} - {str(image_url)[:50]}")
            
            if not valid_images:
                raise ValueError(f"유효한 이미지 URL이 없습니다. 원본 결과: {images}")
                
            # 작업 완료 상태 업데이트
            self.jobs_cache[job_id].update({
                "status": "completed",
                "images": valid_images,
                "completed_at": datetime.utcnow().isoformat(),
                "generation_details": {
                    "original_image_count": len(images),
                    "valid_image_count": len(valid_images),
                    "generation_method": "imagen4" if self.client else "mock"
                }
            })
            
            logger.info(f"🎉 이미지 생성 완료: {job_id}, {len(valid_images)}개 유효 이미지")
            
            # 일일 사용량 증가
            user_id = job_info["user_id"]
            today = datetime.utcnow().date().isoformat()
            cache_key = f"daily_limit:{user_id}:{today}"
            
            try:
                current_count = await cache_manager.get(cache_key) or 0
                await cache_manager.set(
                    cache_key, 
                    current_count + len(valid_images), 
                    ttl_seconds=86400  # 24시간
                )
                logger.debug(f"📊 일일 사용량 업데이트: {user_id} - {current_count + len(valid_images)}개")
            except Exception as cache_error:
                logger.warning(f"⚠️ 일일 사용량 캐시 업데이트 실패: {cache_error}")
            
        except Exception as e:
            logger.error(f"❌ 이미지 생성 실패: {job_id} - {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"💣 전체 스택트레이스:\n{traceback.format_exc()}")
            
            # 작업 실패 상태 업데이트
            if job_id in self.jobs_cache:
                self.jobs_cache[job_id].update({
                    "status": "failed",
                    "error_message": str(e),
                    "error_type": type(e).__name__,
                    "completed_at": datetime.utcnow().isoformat()
                })
    
    async def _generate_with_imagen4(self, job_info: Dict[str, Any]) -> List[str]:
        """Imagen 4를 사용한 이미지 생성 (강화된 예외 처리)"""
        
        try:
            if not self.client:
                logger.error("❌ Imagen 4 클라이언트가 초기화되지 않음")
                raise ValueError("Imagen 4 클라이언트 초기화 실패")
            
            # 스타일을 프롬프트에 통합 (프롬프트 기반 스타일링)
            enhanced_prompt = self._enhance_prompt_for_imagen4(
                job_info["prompt"], 
                job_info.get("style", "realistic")
            )
            logger.debug(f"🎨 강화된 프롬프트: '{enhanced_prompt[:100]}...'")
            
            # Imagen 4 설정 - 최소한의 파라미터만 사용
            num_images = min(job_info.get("num_images", 1), 4)  # 최대 4개 제한
            aspect_ratio = job_info.get("aspect_ratio", "1:1")
            
            if not GenerateImagesConfig:
                logger.error("❌ GenerateImagesConfig 클래스가 로드되지 않음")
                raise ImportError("google-genai 라이브러리의 GenerateImagesConfig를 가져올 수 없습니다")
                
            config = GenerateImagesConfig(
                numberOfImages=num_images,
                aspectRatio=aspect_ratio
            )
            
            logger.info(f"🚀 Imagen 4 API 호출 시작")
            logger.debug(f"📋 API 파라미터: model={self.model_id}, numberOfImages={num_images}, aspectRatio={aspect_ratio}")
            
            # API 호출 전 유효성 검사
            if not enhanced_prompt.strip():
                raise ValueError("강화된 프롬프트가 비어있습니다")
                
            # 비동기 실행 (Google GenAI는 동기 함수이므로 executor 사용)
            loop = asyncio.get_event_loop()
            
            try:
                logger.debug("🔄 executor에서 Imagen 4 API 실행 중...")
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_images(
                        model=self.model_id,
                        prompt=enhanced_prompt,
                        config=config
                    )
                )
                logger.info("✅ Imagen 4 API 호출 성공")
                
            except Exception as api_error:
                logger.error(f"❌ Imagen 4 API 호출 실패: {type(api_error).__name__}: {api_error}")
                raise api_error
            
            # 응답 검증
            if not hasattr(response, 'generated_images') or not response.generated_images:
                logger.error("❌ API 응답에 generated_images가 없거나 비어있음")
                raise ValueError("Imagen 4 API에서 이미지를 생성하지 못했습니다")
                
            logger.info(f"✅ {len(response.generated_images)}개 이미지 생성됨")
            
            # 생성된 이미지 처리
            images = []
            for i, generated_image in enumerate(response.generated_images):
                try:
                    logger.debug(f"💾 이미지 {i+1} 저장 시작")
                    
                    # 이미지를 파일로 저장
                    image_url = await self._save_imagen4_image(
                        generated_image.image, 
                        job_info["job_id"], 
                        i
                    )
                    images.append(image_url)
                    logger.debug(f"✅ 이미지 {i+1} 저장 완료: {image_url[:50]}...")
                    
                except Exception as save_error:
                    logger.error(f"❌ 이미지 {i+1} 저장 실패: {save_error}")
                    try:
                        # 저장 실패 시 Base64로 대체
                        logger.warning(f"⚠️ 이미지 {i+1}를 Base64로 변환 시도")
                        image_bytes = generated_image.image.image_bytes
                        base64_data = base64.b64encode(image_bytes).decode()
                        images.append(f"data:image/png;base64,{base64_data}")
                        logger.debug(f"✅ 이미지 {i+1} Base64 변환 완료")
                    except Exception as base64_error:
                        logger.error(f"❌ 이미지 {i+1} Base64 변환도 실패: {base64_error}")
                        # 최후의 수단으로 Mock 이미지 URL 추가
                        mock_url = f"https://via.placeholder.com/512x512.png?text=Image+{i+1}+Failed"
                        images.append(mock_url)
                        logger.warning(f"⚠️ 이미지 {i+1}에 대해 Mock URL 사용: {mock_url}")
            
            if not images:
                logger.error("❌ 모든 이미지 처리 실패")
                raise ValueError("생성된 이미지를 처리할 수 없습니다")
            
            logger.info(f"🎉 Imagen 4 생성 성공: {len(images)}개 이미지")
            
            # 생성된 이미지 메타데이터를 데이터베이스에 저장 (선택적)
            try:
                await self._save_image_metadata(job_info, images, enhanced_prompt)
                logger.debug("📊 이미지 메타데이터 저장 완료")
            except Exception as metadata_error:
                logger.warning(f"⚠️ 이미지 메타데이터 저장 실패 (이미지는 정상): {metadata_error}")
            
            return images
            
        except Exception as e:
            logger.error(f"❌ Imagen 4 이미지 생성 실패: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"💣 Imagen 4 상세 오류:\n{traceback.format_exc()}")
            
            # 완전 실패 시 예외를 상위로 전파 (Mock으로 대체하지 않음)
            raise e
    
    async def _save_imagen4_image(self, image_obj, job_id: str, index: int) -> str:
        """Imagen 4로 생성된 이미지를 파일로 저장"""
        
        try:
            # 업로드 디렉토리 설정
            upload_dir = Path(settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else './uploads')
            image_dir = upload_dir / "generated_images"
            image_dir.mkdir(parents=True, exist_ok=True)
            
            # 파일명 생성
            filename = f"{job_id}_{index}.png"
            file_path = image_dir / filename
            
            # 이미지 저장 (Google GenAI Image 객체에서 직접 저장)
            image_obj.save(str(file_path))
            
            # URL 반환 (실제 서버 URL로 변경 필요)
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            return f"{base_url}/api/v1/images/generated/{filename}"
            
        except Exception as e:
            logger.error(f"이미지 저장 실패: {e}")
            # 저장 실패 시 Base64로 대체
            image_bytes = image_obj.image_bytes
            base64_data = base64.b64encode(image_bytes).decode()
            return f"data:image/png;base64,{base64_data}"
    
    async def _save_image_metadata(
        self, 
        job_info: Dict[str, Any], 
        image_urls: List[str], 
        enhanced_prompt: str
    ) -> None:
        """생성된 이미지 메타데이터를 데이터베이스에 저장"""
        
        try:
            async with AsyncSessionLocal() as session:
                for i, image_url in enumerate(image_urls):
                    # 파일 경로에서 파일 크기 확인
                    file_size = 0
                    if image_url.startswith("http://"):
                        # URL에서 파일명 추출
                        filename = image_url.split("/")[-1]
                        upload_dir = Path(settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else './uploads')
                        file_path = upload_dir / "generated_images" / filename
                        
                        if file_path.exists():
                            file_size = file_path.stat().st_size
                            relative_path = str(Path("uploads") / "generated_images" / filename)
                        else:
                            relative_path = f"base64_image_{job_info['job_id']}_{i}"
                    else:
                        # Base64 이미지인 경우
                        relative_path = f"base64_image_{job_info['job_id']}_{i}"
                        # Base64 데이터 크기 추정 (실제 바이너리 크기의 약 1.33배)
                        if "base64," in image_url:
                            base64_data = image_url.split("base64,")[1]
                            file_size = int(len(base64_data) * 0.75)  # Base64 디코딩 후 크기
                    
                    # 데이터베이스에 저장
                    generated_image = GeneratedImage(
                        user_id=job_info["user_id"],
                        job_id=job_info["job_id"],
                        prompt=job_info["prompt"],
                        enhanced_prompt=enhanced_prompt,
                        file_path=relative_path,
                        file_url=image_url,
                        file_size=file_size,
                        content_type="image/png",
                        model_name=self.model_id,
                        style=job_info["style"],
                        sample_image_size=job_info["sample_image_size"],
                        aspect_ratio=job_info["aspect_ratio"],
                        num_images=job_info["num_images"],
                        status="completed",
                        extra_metadata={
                            "image_index": i,
                            "generation_timestamp": datetime.now().isoformat(),
                            "api_version": "imagen-4.0",
                            "enhanced_prompt_used": bool(enhanced_prompt != job_info["prompt"])
                        }
                    )
                    
                    session.add(generated_image)
                
                await session.commit()
                logger.info(f"이미지 메타데이터 저장 완료: {job_info['job_id']}, {len(image_urls)}개")
                
        except Exception as e:
            logger.error(f"이미지 메타데이터 저장 실패: {e}")
            # 메타데이터 저장 실패는 이미지 생성 자체를 실패로 처리하지 않음
    
    
    def _enhance_prompt_for_imagen4(self, prompt: str, style: str) -> str:
        """Imagen 4에 최적화된 스타일 프롬프트 향상"""
        
        # Imagen 4에 특화된 스타일 프롬프트 템플릿
        style_templates = {
            "realistic": "A highly detailed, photorealistic {prompt}, professional photography, sharp focus, natural lighting",
            "artistic": "An artistic interpretation of {prompt}, oil painting style, masterpiece, fine art, gallery quality",
            "cartoon": "A cartoon-style illustration of {prompt}, animated, colorful, stylized, Disney-like animation",
            "abstract": "An abstract artistic representation of {prompt}, modern art, conceptual, geometric shapes, vibrant colors",
            "3d": "A 3D rendered image of {prompt}, CGI, digital art, realistic materials, professional lighting",
            "anime": "An anime-style illustration of {prompt}, Japanese animation, manga style, vibrant colors, detailed"
        }
        
        template = style_templates.get(style, "A detailed image of {prompt}, high quality")
        enhanced = template.format(prompt=prompt)
        
        # Imagen 4는 최대 480 토큰이므로 길이 제한
        if len(enhanced) > 400:  # 안전 마진
            enhanced = enhanced[:397] + "..."
        
        return enhanced
    
    def _convert_size_for_imagen4(self, size: str) -> tuple[str, str]:
        """Imagen 4 지원 크기 및 종횡비로 변환"""
        
        # Imagen 4 지원 크기와 종횡비 매핑
        size_mappings = {
            "256x256": ("1K", "1:1"),
            "512x512": ("1K", "1:1"),
            "1024x1024": ("2K", "1:1"),
            "1024x768": ("2K", "4:3"),
            "768x1024": ("2K", "3:4"),
            "1920x1080": ("2K", "16:9"),
            "1080x1920": ("2K", "9:16")
        }
        
        return size_mappings.get(size, ("1K", "1:1"))  # 기본값: 1K, 정사각형
    
    async def get_job_status(self, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """작업 상태 조회"""
        
        job_info = self.jobs_cache.get(job_id)
        if not job_info or job_info["user_id"] != user_id:
            return None
        
        return {
            "status": job_info["status"],
            "images": job_info.get("images", []),
            "prompt": job_info["prompt"],
            "created_at": job_info["created_at"],
            "completed_at": job_info.get("completed_at"),
            "estimated_completion_time": job_info.get("estimated_completion_time"),
            "error_message": job_info.get("error_message"),
            "metadata": {
                "model": job_info["model"],
                "style": job_info["style"],
                "sample_image_size": job_info.get("sample_image_size"),
                "aspect_ratio": job_info.get("aspect_ratio")
            }
        }
    
    async def get_user_history(self, user_id: str, limit: int = 20, skip: int = 0) -> Dict[str, Any]:
        """사용자 생성 히스토리 조회"""
        
        # 사용자의 작업들 필터링
        user_jobs = [
            job for job in self.jobs_cache.values() 
            if job["user_id"] == user_id
        ]
        
        # 생성 시간순 정렬
        user_jobs.sort(key=lambda x: x["created_at"], reverse=True)
        
        # 페이지네이션
        paginated_jobs = user_jobs[skip:skip + limit]
        
        return {
            "jobs": paginated_jobs,
            "total": len(user_jobs)
        }
    
    async def delete_job(self, job_id: str, user_id: str) -> bool:
        """작업 삭제"""
        
        job_info = self.jobs_cache.get(job_id)
        if not job_info or job_info["user_id"] != user_id:
            return False
        
        # 캐시에서 제거
        del self.jobs_cache[job_id]
        
        # TODO: 생성된 이미지 파일도 함께 삭제
        
        return True
    
    async def check_daily_limit(self, user_id: str) -> bool:
        """일일 생성 제한 확인"""
        
        try:
            today = datetime.utcnow().date().isoformat()
            cache_key = f"daily_limit:{user_id}:{today}"
            
            current_count = await cache_manager.get(cache_key) or 0
            
            return current_count < self.max_daily_generations
            
        except Exception as e:
            logger.error(f"일일 제한 확인 실패: {e}")
            return True  # 오류 시 허용
    
    async def get_daily_usage(self, user_id: str) -> Dict[str, int]:
        """일일 사용량 조회"""
        
        try:
            today = datetime.utcnow().date().isoformat()
            cache_key = f"daily_limit:{user_id}:{today}"
            
            current_count = await cache_manager.get(cache_key) or 0
            
            return {
                "used": current_count,
                "limit": self.max_daily_generations,
                "remaining": max(0, self.max_daily_generations - current_count)
            }
            
        except Exception as e:
            logger.error(f"일일 사용량 조회 실패: {e}")
            return {"used": 0, "limit": self.max_daily_generations, "remaining": self.max_daily_generations}
    
    async def edit_image(
        self,
        job_id: str,
        user_id: str,
        prompt: str,
        reference_image_url: str,
        edit_mode: str = "EDIT_MODE_INPAINT_INSERTION",
        mask_mode: Optional[str] = None,
        style: Optional[str] = None,
        size: Optional[str] = None,
        num_images: int = 1
    ) -> Dict[str, Any]:
        """
        Reference Images를 사용한 이미지 편집
        
        Args:
            job_id: 작업 ID
            user_id: 사용자 ID
            prompt: 편집 프롬프트
            reference_image_url: 참조할 기존 이미지 URL
            edit_mode: 편집 모드 (EDIT_MODE_INPAINT_INSERTION, EDIT_MODE_STYLE, etc.)
            mask_mode: 마스크 모드 (선택적)
            style: 이미지 스타일 (선택적)
            size: 이미지 크기 (선택적)
            num_images: 생성할 이미지 수
            
        Returns:
            편집 결과
        """
        
        try:
            # 작업 정보 저장
            job_info = {
                "job_id": job_id,
                "user_id": user_id,
                "prompt": prompt,
                "reference_image_url": reference_image_url,
                "edit_mode": edit_mode,
                "mask_mode": mask_mode,
                "style": style,
                "size": size,
                "num_images": min(num_images, 4),  # 최대 4개 제한
                "status": "processing",
                "images": [],
                "created_at": datetime.utcnow().isoformat(),
                "estimated_completion_time": (datetime.utcnow() + timedelta(seconds=40)).isoformat()
            }
            
            self.jobs_cache[job_id] = job_info
            
            # 동기적으로 이미지 편집 완료 대기
            await self._edit_image_async(job_id)
            
            # 완성된 결과 반환
            final_job_info = self.jobs_cache.get(job_id, job_info)
            
            if final_job_info.get("status") == "completed" and final_job_info.get("images"):
                return {
                    "status": "completed",
                    "images": final_job_info["images"],
                    "safety_score": final_job_info.get("safety_score", 1.0),
                    "metadata": {
                        "edit_mode": edit_mode,
                        "reference_image_url": reference_image_url,
                        "model": "imagen-3.0-capability-001",
                        "generation_method": final_job_info.get("generation_method", "edit_image")
                    }
                }
            else:
                # 편집 실패
                error_msg = final_job_info.get("error_message", "알 수 없는 오류")
                logger.error(f"❌ 이미지 편집 최종 실패: {error_msg}")
                raise Exception(f"이미지 편집 실패: {error_msg}")
            
        except Exception as e:
            logger.error(f"이미지 편집 시작 실패: {e}")
            # 작업 상태를 실패로 업데이트
            if job_id in self.jobs_cache:
                self.jobs_cache[job_id]["status"] = "failed"
                self.jobs_cache[job_id]["error_message"] = str(e)
            
            raise e
    
    async def _edit_image_async(self, job_id: str):
        """비동기 이미지 편집 작업"""
        
        try:
            job_info = self.jobs_cache.get(job_id)
            if not job_info:
                logger.error(f"❌ 편집 작업 정보를 찾을 수 없음: {job_id}")
                return
            
            logger.info(f"✏️ 이미지 편집 시작: {job_id}")
            logger.debug(f"📋 편집 정보: prompt='{job_info['prompt'][:50]}...', edit_mode={job_info['edit_mode']}")
            
            images = []
            
            # 실제 이미지 편집 (Google GenAI 클라이언트 필수)
            if not self.client:
                raise ValueError("Google GenAI 클라이언트가 초기화되지 않았습니다. API 키를 확인해주세요.")
            
            logger.info(f"🚀 Google GenAI 클라이언트로 편집 시작")
            images = await self._edit_with_imagen3(job_info)
            logger.info(f"✅ 이미지 편집 성공: {len(images)}개 이미지")
            
            # 편집 결과 검증
            if not images or len(images) == 0:
                raise ValueError("이미지 편집 결과가 비어있습니다")
            
            # 작업 완료 상태 업데이트
            self.jobs_cache[job_id].update({
                "status": "completed",
                "images": images,
                "completed_at": datetime.utcnow().isoformat(),
                "generation_method": "edit_image",
                "generation_details": {
                    "edit_count": len(images),
                    "edit_mode": job_info["edit_mode"],
                    "reference_used": bool(job_info["reference_image_url"])
                }
            })
            
            logger.info(f"🎉 이미지 편집 완료: {job_id}, {len(images)}개 편집된 이미지")
            
        except Exception as e:
            logger.error(f"❌ 이미지 편집 실패: {job_id} - {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"💣 편집 전체 스택트레이스:\n{traceback.format_exc()}")
            
            # 작업 실패 상태 업데이트
            if job_id in self.jobs_cache:
                self.jobs_cache[job_id].update({
                    "status": "failed",
                    "error_message": str(e),
                    "error_type": type(e).__name__,
                    "completed_at": datetime.utcnow().isoformat()
                })
    
    async def _edit_with_imagen3(self, job_info: Dict[str, Any]) -> List[str]:
        """참조 이미지 기반 새 이미진 생성 (이미지 편집 대체 기능)"""
        
        try:
            if not self.client:
                logger.error("❌ Google GenAI 클라이언트가 초기화되지 않음")
                raise ValueError("Google GenAI 클라이언트 초기화 실패")
            
            # Vertex AI 사용 여부 확인
            if not self.use_vertex_ai:
                logger.warning("⚠️ Vertex AI 클라이언트가 아니므로 edit_image API를 사용할 수 없음")
                raise ValueError("edit_image API는 Vertex AI 클라이언트에서만 지원됩니다. GOOGLE_CLOUD_PROJECT를 설정하고 Vertex AI를 활성화하세요.")
            
            # Fallback 방식으로 참조 이미지 로드
            reference_image = await self._load_reference_image_with_fallback(
                job_info["reference_image_url"]
            )
            if not reference_image:
                raise ValueError("참조 이미지를 로드할 수 없습니다")
            
            # Reference Images 설정
            reference_images = []
            
            # Raw Reference Image (기본 이미지)
            if RawReferenceImage:
                # PIL Image를 Google GenAI Image 객체로 변환
                import io
                img_byte_arr = io.BytesIO()
                reference_image.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                # Google GenAI Image 객체 생성 - 정확한 필드명 사용
                genai_image = Image(
                    image_bytes=img_bytes,
                    mime_type="image/png"
                )
                
                # 디버깅: Image 객체 내용 확인
                logger.debug(f"📋 GenAI Image 생성됨:")
                logger.debug(f"   - mime_type: {genai_image.mime_type}")
                logger.debug(f"   - gcs_uri: {genai_image.gcs_uri}")
                logger.debug(f"   - image_bytes 존재: {bool(genai_image.image_bytes)}")
                if genai_image.image_bytes:
                    logger.debug(f"   - image_bytes 크기: {len(genai_image.image_bytes)}")
                
                raw_ref_image = RawReferenceImage(
                    reference_id=1,
                    reference_image=genai_image,  # Google GenAI Image 객체 사용
                )
                reference_images.append(raw_ref_image)
                logger.debug("✅ Raw Reference Image 추가 (GenAI Image 객체로 변환)")
            
            # Mask Reference Image는 기본적으로 생략 (간단한 편집에서는 불필요)
            logger.debug("✅ Mask Reference Image 생략 - 기본 편집 모드")
            
            if not EditImageConfig:
                logger.error("❌ EditImageConfig 클래스가 로드되지 않음")
                raise ImportError("google-genai 라이브러리의 EditImageConfig를 가져올 수 없습니다")
            
            logger.info(f"🚀 Imagen 3.0 Edit API 호출 시작")
            logger.debug(f"📋 편집 파라미터: edit_mode={job_info['edit_mode']}, references={len(reference_images)}")
            
            # 비동기 실행
            loop = asyncio.get_event_loop()
            
            try:
                logger.debug("🔄 executor에서 edit_image API 실행 중...")
                
                # 편집 요청을 생성 프롬프트로 변환
                original_prompt = job_info["prompt"]
                edit_mode_str = job_info["edit_mode"]
                
                # 안전한 기본 편집 모드 사용 (Context7 문서 기반)
                # 마스크가 필요 없는 EDIT_MODE_DEFAULT 강제 사용
                edit_mode_enum = EditMode.EDIT_MODE_DEFAULT
                logger.info(f"🎨 Context7 표준: EDIT_MODE_DEFAULT (마스크 프리) 사용")
                
                # Context7 문서 기반 마스크 프리 편집을 위한 프롬프트 최적화
                # "Based on the reference image" 패턴 사용 (공식 문서 예시)
                enhanced_prompt = f"Based on the reference image, create a new version with the following changes: {original_prompt}. Maintain high quality and the overall aesthetic."
                
                logger.debug(f"📝 향상된 프롬프트: {enhanced_prompt[:100]}...")
                
                response = await loop.run_in_executor(
                    None,
                    lambda: self.client.models.edit_image(
                        model=self.edit_model_id,  # 편집 전용 모델 사용
                        prompt=enhanced_prompt,
                        reference_images=reference_images if reference_images else [],
                        config=EditImageConfig(
                            edit_mode=edit_mode_enum,  # EDIT_MODE_DEFAULT (마스크 프리)
                            number_of_images=job_info.get("num_images", 1),
                            safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",  # Context7 표준
                            person_generation="ALLOW_ADULT",  # Context7 표준 형식
                            output_mime_type="image/jpeg",  # 더 안정적인 JPEG
                            include_rai_reason=True
                        )
                    )
                )
                logger.info("✅ Imagen 4 Edit API 호출 성공 (참조 이미지 기반)")
                
            except Exception as api_error:
                error_type = type(api_error).__name__
                error_msg = str(api_error)
                
                # 사용자 친화적 오류 메시지 생성
                if "person_generation" in error_msg.lower():
                    user_message = "이미지에 포함된 인물 생성 설정에 문제가 있습니다. 잠시 후 다시 시도해주세요."
                elif "safety" in error_msg.lower() or "blocked" in error_msg.lower():
                    user_message = "안전 설정으로 인해 일부 내용이 차단되었습니다. 프롬프트를 수정하여 다시 시도해주세요."
                elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                    user_message = "일일 사용 한도에 도달했습니다. 내일 다시 시도하거나 관리자에게 문의해주세요."
                elif "timeout" in error_msg.lower():
                    user_message = "서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
                else:
                    user_message = "이미지 편집 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                
                logger.error(f"❌ Imagen 4 Edit API 호출 실패: {error_type}: {api_error}")
                logger.error(f"👤 사용자 메시지: {user_message}")
                
                # 사용자 친화적 오류로 래핑
                raise ValueError(user_message)
            
            # 응답 구조 상세 분석
            logger.info(f"📋 Edit API 응답 구조 분석:")
            logger.info(f"  - response 타입: {type(response)}")
            logger.info(f"  - response 속성들: {dir(response)}")
            
            # response 내용 직접 로깅
            if hasattr(response, '__dict__'):
                logger.info(f"  - response.__dict__: {response.__dict__}")
            
            # candidates 속성 확인
            if hasattr(response, 'candidates'):
                logger.info(f"  - response.candidates 존재: {len(response.candidates) if response.candidates else 0}개")
                if response.candidates:
                    for i, candidate in enumerate(response.candidates):
                        logger.info(f"    - candidate[{i}] 타입: {type(candidate)}")
                        logger.info(f"    - candidate[{i}] 속성: {dir(candidate)}")
            else:
                logger.info("  - response.candidates 속성 없음")
                
            # 다른 가능한 속성들 확인
            possible_attrs = ['images', 'result', 'content', 'data', 'generations']
            for attr in possible_attrs:
                if hasattr(response, attr):
                    value = getattr(response, attr)
                    logger.info(f"  - response.{attr}: {type(value)} = {value}")
            
            # Context7 문서 기반 응답 구조 확인
            if hasattr(response, 'generated_images') and response.generated_images:
                logger.info(f"✅ Context7 표준: generated_images 속성 발견 ({len(response.generated_images)}개)")
                candidates_or_images = response.generated_images
            elif hasattr(response, 'candidates') and response.candidates:
                logger.info(f"✅ Candidates 속성 발견 ({len(response.candidates)}개)")
                candidates_or_images = response.candidates
            else:
                logger.error("❌ API 응답에 generated_images나 candidates가 없거나 비어있음")
                # 모든 속성 출력해서 디버깅
                all_attrs = [attr for attr in dir(response) if not attr.startswith('_')]
                logger.error(f"💡 사용 가능한 속성들: {all_attrs}")
                raise ValueError("Imagen 4 Edit API에서 참조 이미지 기반 이미지를 생성하지 못했습니다")
            
            logger.info(f"✅ {len(candidates_or_images)}개 참조 기반 이미지 생성됨")
            
            # 생성된 이미지 처리
            images = []
            for i, candidate_or_image in enumerate(candidates_or_images):
                try:
                    logger.debug(f"💾 생성된 이미지 {i+1} 저장 시작")
                    
                    # Context7 문서 기반 이미지 저장 (generated_images vs candidates)
                    if hasattr(candidate_or_image, 'image'):
                        # generated_images 구조: candidate_or_image.image 
                        logger.debug("📋 Context7 generated_images 구조 사용")
                        image_to_save = candidate_or_image.image
                    else:
                        # candidates 구조: candidate_or_image 자체가 이미지
                        logger.debug("📋 Candidates 구조 사용")
                        image_to_save = candidate_or_image
                        
                    image_url = await self._save_edited_image(
                        image_to_save,
                        job_info["job_id"],
                        i
                    )
                    images.append(image_url)
                    logger.debug(f"✅ 생성된 이미지 {i+1} 저장 완료: {image_url[:50]}...")
                    
                except Exception as save_error:
                    logger.error(f"❌ 생성된 이미지 {i+1} 저장 실패: {save_error}")
                    # Base64로 대체 시도
                    try:
                        # Context7 호환성: image_bytes 속성 확인
                        if hasattr(image_to_save, 'image_bytes'):
                            image_bytes = image_to_save.image_bytes
                        elif hasattr(candidate_or_image, 'image_bytes'):
                            image_bytes = candidate_or_image.image_bytes
                        else:
                            raise AttributeError("image_bytes 속성을 찾을 수 없음")
                            
                        base64_data = base64.b64encode(image_bytes).decode()
                        images.append(f"data:image/jpeg;base64,{base64_data}")
                        logger.debug(f"✅ 생성된 이미지 {i+1} Base64 변환 완료")
                    except Exception as base64_error:
                        logger.error(f"❌ Base64 변환도 실패: {base64_error}")
                        # 실제 로컬 URL로 대체 시도
                        try:
                            fallback_url = f"http://localhost:8000/api/v1/images/generated/{job_info['job_id']}_edited_{i}.jpg"
                            images.append(fallback_url)
                            logger.debug(f"🔄 Fallback URL 사용: {fallback_url}")
                        except Exception:
                            logger.error(f"❌ Fallback URL 생성도 실패")
            
            if not images:
                logger.error("❌ 모든 생성된 이미지 처리 실패")
                raise ValueError("참조 이미지 기반 생성 결과를 처리할 수 없습니다")
            
            logger.info(f"🎉 참조 이미지 기반 생성 성공: {len(images)}개 이미지")
            return images
            
        except Exception as e:
            logger.error(f"❌ 참조 이미지 기반 생성 실패: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"💣 생성 상세 오류:\n{traceback.format_exc()}")
            raise e
    
    async def _load_reference_image_with_fallback(self, image_url: str):
        """
        참조 이미지를 HTTP URL → 로컬 파일 순서로 로딩 (Fallback)
        
        1차: HTTP/HTTPS URL 로딩 시도
        2차: 로컬 파일 경로 변환하여 직접 로딩
        """
        
        try:
            # 1차 시도: 기존 HTTP URL 방식
            logger.info(f"🌐 1차 시도: HTTP URL 로딩 - {image_url[:50]}...")
            reference_image = await self._load_reference_image_http(image_url)
            if reference_image:
                logger.info("✅ HTTP URL 로딩 성공")
                return reference_image
                
        except Exception as http_error:
            error_type = type(http_error).__name__
            # 구체적인 HTTP 에러 타입별 로깅
            if "timeout" in str(http_error).lower():
                logger.warning(f"⏰ HTTP URL 로딩 타임아웃: {http_error}")
            elif "connection" in str(http_error).lower():
                logger.warning(f"🌐 HTTP URL 연결 실패: {http_error}")
            elif "404" in str(http_error):
                logger.warning(f"🔍 HTTP URL 리소스 없음 (404): {http_error}")
            elif "403" in str(http_error):
                logger.warning(f"🔒 HTTP URL 권한 없음 (403): {http_error}")
            else:
                logger.warning(f"⚠️ HTTP URL 로딩 실패 ({error_type}): {http_error}")
        
        try:
            # 2차 시도: 로컬 파일 직접 로딩
            local_path = self._convert_url_to_local_path(image_url)
            logger.info(f"📁 2차 시도: 로컬 파일 로딩 - {local_path}")
            reference_image = await self._load_reference_image_local(local_path)
            if reference_image:
                logger.info("✅ 로컬 파일 로딩 성공")
                return reference_image
                
        except FileNotFoundError as file_error:
            logger.error(f"📄 로컬 파일 없음: {file_error}")
        except PermissionError as perm_error:
            logger.error(f"🔐 로컬 파일 권한 없음: {perm_error}")
        except ValueError as value_error:
            logger.error(f"🖼️ 이미지 파일 손상/무효: {value_error}")
        except Exception as local_error:
            logger.error(f"❌ 로컬 파일 로딩 알 수 없는 실패 ({type(local_error).__name__}): {local_error}")
        
        # 모든 시도 실패
        logger.error(f"💥 참조 이미지 로딩 완전 실패: {image_url}")
        logger.error(f"   - HTTP URL 접근: 실패 (네트워크/권한 문제)")
        logger.error(f"   - 로컬 파일 접근: 실패 (파일 없음/권한/손상)")
        raise ValueError(f"참조 이미지를 HTTP 및 로컬에서 모두 로드할 수 없습니다: {image_url}")

    async def _load_reference_image_http(self, image_url: str):
        """HTTP URL에서 이미지 로딩 (기존 방식, 타임아웃 추가)"""
        
        if image_url.startswith('data:image'):
            # Base64 이미지 처리
            logger.debug("📷 Base64 이미지에서 참조 이미지 로드")
            import base64
            import io
            from PIL import Image
            
            # Base64 데이터 추출
            base64_data = image_url.split(',')[1]
            image_bytes = base64.b64decode(base64_data)
            
            # PIL Image 객체로 변환
            pil_image = Image.open(io.BytesIO(image_bytes))
            return pil_image
            
        elif image_url.startswith('http'):
            # HTTP URL에서 이미지 로드 (타임아웃 설정)
            logger.debug(f"🌐 HTTP URL에서 참조 이미지 로드: {image_url[:50]}...")
            import httpx
            
            # 타임아웃 설정: 연결 10초, 읽기 30초
            timeout = httpx.Timeout(connect=10.0, read=30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                
                import io
                from PIL import Image
                pil_image = Image.open(io.BytesIO(response.content))
                
                # 이미지 검증
                pil_image.verify()
                pil_image = Image.open(io.BytesIO(response.content))  # verify 후 다시 열기
                
                return pil_image
                
        else:
            raise ValueError(f"지원하지 않는 URL 형식: {image_url}")
    
    async def _load_reference_image_local(self, local_file_path: str):
        """로컬 파일에서 직접 이미지 로딩"""
        
        import os
        from PIL import Image
        
        # 파일 존재 검증
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"이미지 파일이 존재하지 않습니다: {local_file_path}")
        
        # 파일 권한 검증
        if not os.access(local_file_path, os.R_OK):
            raise PermissionError(f"이미지 파일 읽기 권한이 없습니다: {local_file_path}")
        
        # PIL로 이미지 로딩
        logger.debug(f"📁 로컬 파일에서 이미지 로딩: {local_file_path}")
        pil_image = Image.open(local_file_path)
        
        # 이미지 유효성 검증
        try:
            pil_image.verify()
            # verify() 후에는 이미지를 다시 열어야 함
            pil_image = Image.open(local_file_path)
            logger.debug(f"✅ 이미지 검증 성공: {pil_image.size}, {pil_image.mode}")
            return pil_image
        except Exception as e:
            raise ValueError(f"이미지 파일이 손상되었거나 유효하지 않습니다: {e}")
    
    def _convert_url_to_local_path(self, image_url: str) -> str:
        """이미지 URL을 로컬 파일 경로로 변환"""
        
        import os
        from urllib.parse import urlparse
        from pathlib import Path
        
        try:
            # URL 파싱하여 경로 추출
            parsed_url = urlparse(image_url)
            url_path = parsed_url.path
            
            # URL에서 파일명 추출
            # 예: /api/v1/images/generated/46ff723d-1c6a-4914-874e-2f8c53510f77_0.png
            # → 46ff723d-1c6a-4914-874e-2f8c53510f77_0.png
            filename = os.path.basename(url_path.split('?')[0])  # 쿼리 파라미터 제거
            
            if not filename:
                raise ValueError("URL에서 파일명을 추출할 수 없습니다")
            
            # 로컬 저장소 경로 구성
            upload_dir = Path(settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else './uploads')
            
            # URL 경로에 따라 적절한 폴더 선택
            if '/api/v1/images/generated/' in url_path:
                image_folder = 'generated_images'
            elif '/api/v1/images/edited/' in url_path:
                image_folder = 'edited_images'
            else:
                # 기본값: generated_images 폴더
                image_folder = 'generated_images'
                logger.warning(f"⚠️ 알 수 없는 이미지 URL 경로: {url_path}, 기본 폴더 사용")
            
            local_path = upload_dir / image_folder / filename
            
            # 경로 보안 검증 (Path Traversal 공격 방지)
            try:
                resolved_path = local_path.resolve()
                allowed_base = (upload_dir / image_folder).resolve()
                if not str(resolved_path).startswith(str(allowed_base)):
                    raise ValueError("허용되지 않는 파일 경로입니다")
            except Exception as e:
                raise ValueError(f"파일 경로 보안 검증 실패: {e}")
            
            logger.debug(f"🔄 URL → 로컬 경로 변환: {image_url} → {local_path}")
            return str(local_path)
            
        except Exception as e:
            logger.error(f"❌ URL → 로컬 경로 변환 실패: {e}")
            raise ValueError(f"URL을 로컬 경로로 변환할 수 없습니다: {e}")
    
    async def _save_edited_image(self, image_obj, job_id: str, index: int) -> str:
        """편집된 이미지를 파일로 저장"""
        
        try:
            # 업로드 디렉토리 설정
            upload_dir = Path(settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else './uploads')
            image_dir = upload_dir / "edited_images"
            image_dir.mkdir(parents=True, exist_ok=True)
            
            # 파일명 생성
            filename = f"{job_id}_edited_{index}.jpg"
            file_path = image_dir / filename
            
            # 이미지 저장
            image_obj.save(str(file_path))
            
            # 파일이 실제로 저장되고 접근 가능한지 확인
            await self._ensure_file_accessible(str(file_path))
            
            # URL 반환
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            return f"{base_url}/api/v1/images/edited/{filename}"
            
        except Exception as e:
            logger.error(f"편집된 이미지 저장 실패: {e}")
            # 저장 실패 시 Base64로 대체
            image_bytes = image_obj.image_bytes
            base64_data = base64.b64encode(image_bytes).decode()
            return f"data:image/jpeg;base64,{base64_data}"
    
    async def _ensure_file_accessible(self, file_path: str, max_retries: int = 10) -> bool:
        """파일이 실제로 저장되고 접근 가능한지 확인"""
        import os
        import asyncio
        
        for i in range(max_retries):
            try:
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    logger.debug(f"✅ 파일 접근 가능 확인: {file_path} ({i + 1}번째 시도)")
                    return True
            except Exception as e:
                logger.debug(f"⏳ 파일 접근 대기 중: {file_path} ({i + 1}/{max_retries}) - {e}")
            
            # 100ms 간격으로 재시도
            await asyncio.sleep(0.1)
        
        logger.warning(f"❌ 파일 접근 실패: {file_path} ({max_retries}번 시도 후 포기)")
        return False

    async def edit_image_with_gemini(
        self,
        job_id: str,
        user_id: str,
        prompt: str,
        reference_image_url: str,
        optimize_prompt: bool = False
    ) -> Dict[str, Any]:
        """
        Gemini 2.5 Flash Image Preview를 사용한 이미지 편집
        
        Args:
            job_id: 작업 ID
            user_id: 사용자 ID  
            prompt: 편집 요청 프롬프트 (자연어)
            reference_image_url: 편집할 기준 이미지 URL
            optimize_prompt: 프롬프트 최적화 여부
            
        Returns:
            Dict containing status, images, and metadata
        """
        
        try:
            if not self.gemini_client:
                logger.error("❌ Gemini 2.5 Flash Image Preview 클라이언트가 초기화되지 않음")
                raise ValueError("Gemini Image Preview 클라이언트 초기화 실패")
            
            logger.info(f"🎨 Gemini 2.5 Flash 이미지 편집 시작: {job_id}")
            logger.debug(f"📋 편집 정보: prompt='{prompt[:50]}...', optimize={optimize_prompt}")
            
            # 작업 정보 캐시에 저장
            job_info = {
                "job_id": job_id,
                "user_id": user_id,
                "prompt": prompt,
                "reference_image_url": reference_image_url,
                "optimize_prompt": optimize_prompt,
                "status": "processing",
                "created_at": datetime.utcnow().isoformat(),
                "num_images": 1,
                "model": self.gemini_model_id,
                "generation_method": "modification"
            }
            
            self.jobs_cache[job_id] = job_info
            
            # 프롬프트 최적화 (옵션)
            final_prompt = prompt
            if optimize_prompt:
                try:
                    final_prompt = await self.optimize_edit_prompt(prompt)
                    logger.info(f"✨ 프롬프트 최적화 완료: '{final_prompt[:50]}...'")
                except Exception as e:
                    logger.warning(f"⚠️ 프롬프트 최적화 실패, 원본 사용: {e}")
                    final_prompt = prompt
            
            # 직접 이미지 편집 수행
            logger.info(f"🖼️ 참조 이미지 로드 중: {reference_image_url}")
            
            # 참조 이미지 로드
            reference_image = await self._load_reference_image_with_fallback(reference_image_url)
            if not reference_image:
                raise ValueError("참조 이미지를 로드할 수 없습니다")
            
            # 편집 프롬프트 구성 (이미지 생성 요청)
            edit_instruction = f"Edit this image as follows: {final_prompt}. Keep the original style and composition while making the requested changes naturally."
            
            logger.debug(f"📝 편집 명령: {edit_instruction[:100]}...")
            
            # Gemini를 사용하여 이미지 편집
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._generate_content_with_image(edit_instruction, reference_image)
            )
            
            # Gemini 응답에서 직접 이미지 추출 (Google 공식 예제 방식)
            images = await self._process_gemini_response(response, job_id)
            
            if images:
                logger.info(f"🎉 Gemini 2.5 Flash Image Preview 편집 성공: {len(images)}개 이미지")
                return {
                    "status": "completed",
                    "images": images,
                    "safety_score": 1.0,
                    "metadata": {
                        "model": self.gemini_model_id,
                        "generation_method": "gemini_direct_edit",
                        "prompt_optimized": optimize_prompt,
                        "final_prompt": final_prompt[:100] + "..." if len(final_prompt) > 100 else final_prompt
                    }
                }
            else:
                raise Exception("편집된 이미지를 생성할 수 없습니다")
            
        except Exception as e:
            logger.error(f"Gemini 이미지 편집 시작 실패: {e}")
            # 캐시에 실패 상태 저장
            if job_id in self.jobs_cache:
                self.jobs_cache[job_id]["status"] = "failed"
                self.jobs_cache[job_id]["error_message"] = str(e)
            
            raise e
    
    # 이제 사용하지 않는 메서드 - 직접 편집으로 대체됨
    # async def _edit_image_with_gemini_async(self, job_id: str, final_prompt: str):

    def _generate_content_with_image(self, edit_instruction: str, image):
        """Gemini 2.5 Flash Image Preview를 사용한 이미지 편집"""
        try:
            # 사용자 제공 해결책 적용: GenerateContentConfig with response_modalities
            config = GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                candidate_count=1,
            )
            
            # Google GenAI 공식 문서 패턴 + 이미지 생성 config 사용
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_id,
                contents=[edit_instruction, image],
                config=config
            )
            logger.debug(f"✅ Gemini API 호출 성공 (response_modalities=TEXT,IMAGE)")
            
            # 응답 구조 분석을 위한 상세 로깅
            logger.info(f"📋 Gemini 응답 타입: {type(response)}")
            logger.info(f"📋 Gemini 응답 속성: {dir(response)}")
            
            if hasattr(response, 'candidates'):
                logger.info(f"📋 응답 후보 수: {len(response.candidates) if response.candidates else 0}")
                if response.candidates:
                    candidate = response.candidates[0]
                    logger.info(f"📋 첫 번째 후보 타입: {type(candidate)}")
                    logger.info(f"📋 첫 번째 후보 속성: {dir(candidate)}")
                    
                    if hasattr(candidate, 'content'):
                        content = candidate.content
                        logger.info(f"📋 콘텐츠 타입: {type(content)}")
                        logger.info(f"📋 콘텐츠 속성: {dir(content)}")
                        
                        if hasattr(content, 'parts'):
                            logger.info(f"📋 파트 수: {len(content.parts) if content.parts else 0}")
                            for i, part in enumerate(content.parts):
                                logger.info(f"📋 파트 {i} 타입: {type(part)}")
                                logger.info(f"📋 파트 {i} 속성: {dir(part)}")
                                if hasattr(part, 'text'):
                                    text_content = part.text[:200] if part.text else 'None'
                                    logger.info(f"📋 파트 {i} 텍스트: {text_content}...")
                                if hasattr(part, 'inline_data'):
                                    logger.info(f"📋 파트 {i} 인라인 데이터 존재: {part.inline_data is not None}")
            
            return response
        except Exception as e:
            logger.error(f"❌ Gemini generate_content 실패: {e}")
            raise e

    async def _process_gemini_response(self, response, job_id: str) -> List[str]:
        """Gemini 응답에서 이미지를 추출하고 저장 (Google 공식 예제 방식)"""
        
        try:
            images = []
            
            # Chat 응답에서는 response.candidates[0].content.parts에 직접 접근
            if not hasattr(response, 'candidates') or not response.candidates or len(response.candidates) == 0:
                logger.error("❌ Gemini 응답에 후보가 없음")
                raise ValueError("Gemini API 응답이 비어있습니다")
            
            candidate = response.candidates[0]
            if not hasattr(candidate, 'content') or not candidate.content or not candidate.content.parts:
                logger.error("❌ Gemini 응답에 콘텐츠가 없음")
                raise ValueError("Gemini API 응답 콘텐츠가 비어있습니다")
            
            # Google 공식 문서 패턴: content.parts 순회
            for i, part in enumerate(candidate.content.parts):
                logger.info(f"🔍 파트 {i} 처리: {type(part)}")
                logger.info(f"🔍 파트 {i} 속성들: {dir(part)}")
                
                # 디버깅: part의 모든 속성 확인
                if hasattr(part, 'inline_data'):
                    logger.info(f"🔍 파트 {i} inline_data: {part.inline_data}")
                    if part.inline_data is not None:
                        logger.info(f"🔍 파트 {i} inline_data.data 크기: {len(part.inline_data.data) if hasattr(part.inline_data, 'data') else 'None'}")
                        logger.info(f"🔍 파트 {i} inline_data 속성: {dir(part.inline_data)}")
                        logger.info(f"🔍 파트 {i} inline_data 타입: {type(part.inline_data)}")
                
                if hasattr(part, 'text'):
                    text_content = part.text[:200] if part.text else 'None'
                    logger.info(f"🔍 파트 {i} text: {text_content}")
                
                if hasattr(part, 'function_call'):
                    logger.info(f"🔍 파트 {i} function_call: {part.function_call}")
                
                # 추가 속성 체크
                for attr_name in ['data', 'image_data', 'blob', 'binary_data', 'file_data']:
                    if hasattr(part, attr_name):
                        attr_value = getattr(part, attr_name)
                        logger.info(f"🔍 파트 {i} {attr_name}: {attr_value is not None} (타입: {type(attr_value)})")
                
                # 이미지 데이터 추출 시도 (여러 방법)
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    logger.info(f"📸 inline_data 방식으로 이미지 파트 {i} 발견")
                    
                    try:
                        # Google 공식 예제 패턴
                        from io import BytesIO
                        image = PILImage.open(BytesIO(part.inline_data.data))
                        
                        # 파일로 저장
                        saved_url = await self._save_gemini_image(image, job_id, i)
                        images.append(saved_url)
                        
                        logger.info(f"✅ 이미지 {i+1} 처리 완료: {saved_url[:50]}...")
                        
                    except Exception as part_error:
                        logger.error(f"❌ 이미지 파트 {i} (inline_data) 처리 실패: {part_error}")
                        continue
                
                # as_image 메서드로도 시도
                elif hasattr(part, 'as_image'):
                    logger.info(f"📸 as_image 방식으로 이미지 파트 {i} 시도")
                    
                    try:
                        image = part.as_image()
                        if image:
                            # 파일로 저장
                            saved_url = await self._save_gemini_image(image, job_id, i)
                            images.append(saved_url)
                            
                            logger.info(f"✅ 이미지 {i+1} (as_image) 처리 완료: {saved_url[:50]}...")
                    
                    except Exception as part_error:
                        logger.error(f"❌ 이미지 파트 {i} (as_image) 처리 실패: {part_error}")
                        continue
                        
                elif hasattr(part, 'text') and part.text:
                    logger.info(f"📝 텍스트 파트 {i}: {part.text[:200]}...")
                    # 텍스트가 이미지 설명인지 확인
                    if any(keyword in part.text.lower() for keyword in ['이미지', 'image', '생성', '편집', '바뀜', 'edited']):
                        logger.warning(f"⚠️ 파트 {i}는 이미지 설명으로 보임 - 실제 이미지가 아닌 텍스트 응답일 수 있음")
            
            if not images:
                logger.error("❌ 모든 이미지 파트 처리 실패")
                raise ValueError("Gemini 응답에서 유효한 이미지를 찾을 수 없습니다")
            
            logger.info(f"🎉 Gemini 이미지 편집 완료: {len(images)}개 이미지")
            return images
            
        except Exception as e:
            logger.error(f"❌ Gemini 응답 처리 실패: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"💣 상세 오류:\n{traceback.format_exc()}")
            raise e

    async def _save_gemini_image(self, image, job_id: str, index: int) -> str:
        """Gemini로 편집된 이미지를 파일로 저장 (향상된 로깅)"""
        
        start_time = time.time()
        logger.info(f"💾 Gemini 이미지 저장 시작: {job_id}_{index}")
        
        try:
            # 업로드 디렉토리 설정
            upload_dir = Path(settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else './uploads')
            image_dir = upload_dir / "generated_images"
            image_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"📁 저장 디렉토리 준비: {image_dir}")
            
            # 파일명 생성
            filename = f"{job_id}_gemini_edit_{index}.png"
            file_path = image_dir / filename
            logger.debug(f"📄 파일 경로: {file_path}")
            
            # 이미지 정보 로깅
            try:
                if hasattr(image, 'size'):
                    logger.info(f"🖼️ 이미지 크기: {image.size[0]}x{image.size[1]}")
                if hasattr(image, 'mode'):
                    logger.debug(f"🎨 이미지 모드: {image.mode}")
            except Exception as info_error:
                logger.debug(f"⚠️ 이미지 정보 조회 실패: {info_error}")
            
            # 이미지 저장 (PIL Image 객체)
            save_start = time.time()
            image.save(str(file_path), "PNG")
            save_duration = time.time() - save_start
            
            # 파일 저장 확인 및 크기 로깅
            if file_path.exists():
                file_size = file_path.stat().st_size
                logger.info(f"✅ 이미지 저장 성공: {filename} ({file_size:,} bytes, {save_duration:.3f}초)")
            else:
                raise FileNotFoundError(f"이미지 파일이 생성되지 않음: {file_path}")
            
            # URL 반환 (실제 서버 URL로 변경 필요)
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            image_url = f"{base_url}/api/v1/images/generated/{filename}"
            
            # 전체 처리 시간 로깅
            total_duration = time.time() - start_time
            logger.info(f"🎉 이미지 파이프라인 완료: {image_url} (총 {total_duration:.3f}초)")
            
            # 파일 접근성 확인 (비동기)
            import asyncio
            asyncio.create_task(self._verify_file_accessibility(file_path, image_url))
            
            return image_url
            
        except Exception as e:
            error_duration = time.time() - start_time
            logger.error(f"❌ Gemini 이미지 저장 실패 ({error_duration:.3f}초 경과): {e}")
            logger.error(f"💣 상세 오류: {traceback.format_exc()}")
            
            # 저장 실패 시 Base64로 대체
            try:
                from io import BytesIO
                import base64
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                image_bytes = buffer.getvalue()
                base64_data = base64.b64encode(image_bytes).decode()
                fallback_url = f"data:image/png;base64,{base64_data}"
                logger.info(f"🔄 Base64 대체 URL 생성: {len(base64_data)} 문자")
                return fallback_url
            except Exception as fallback_error:
                logger.error(f"💥 Base64 대체 실패: {fallback_error}")
                raise e
    
    async def _verify_file_accessibility(self, file_path: Path, image_url: str) -> None:
        """파일 접근성 확인 (비동기)"""
        try:
            # 파일 시스템 접근성 확인
            await asyncio.sleep(0.1)  # 파일 시스템 sync 대기
            
            if file_path.exists() and file_path.is_file():
                file_size = file_path.stat().st_size
                logger.info(f"🔍 파일 접근성 확인 - 존재: ✅, 크기: {file_size:,} bytes")
                
                # HTTP 접근성 확인 (선택적)
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.head(image_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                            if response.status == 200:
                                logger.info(f"🌐 HTTP 접근성 확인 - 상태: {response.status} ✅")
                            else:
                                logger.warn(f"⚠️ HTTP 접근성 확인 - 상태: {response.status}")
                except Exception as http_error:
                    logger.debug(f"🔍 HTTP 접근성 확인 생략: {http_error}")
            else:
                logger.error(f"❌ 파일 접근성 확인 실패: 파일이 존재하지 않음")
                
        except Exception as verify_error:
            logger.debug(f"🔍 파일 접근성 확인 중 오류: {verify_error}")

    async def optimize_edit_prompt(self, original_prompt: str) -> str:
        """
        편집 프롬프트를 이미지 편집에 최적화된 형태로 변환
        
        Args:
            original_prompt: 사용자가 입력한 원본 프롬프트
            
        Returns:
            최적화된 편집 프롬프트
        """
        
        try:
            if not self.gemini_client:
                logger.warning("⚠️ Gemini 클라이언트 없음 - 프롬프트 최적화 건너뛰기")
                return original_prompt
            
            # 프롬프트 최적화를 위한 메타 프롬프트
            optimization_prompt = f"""
다음 사용자 입력을 이미지 편집에 최적화된 영어 프롬프트로 변환해주세요:

사용자 입력: "{original_prompt}"

요구사항:
1. "Using the provided image" 로 시작
2. 구체적이고 명확한 편집 지시사항 포함
3. 원본 이미지의 스타일, 조명, 구성 유지 언급
4. 자연스럽고 매끄러운 편집 요청
5. 영어로 작성
6. 50-100단어 내외

최적화된 프롬프트만 출력해주세요.
"""
            
            loop = asyncio.get_event_loop()
            
            # Gemini 클라이언트로 프롬프트 최적화
            response = await loop.run_in_executor(
                None,
                lambda: self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[optimization_prompt]
                )
            )
            
            if response.text:
                optimized_prompt = response.text.strip()
                logger.debug(f"📝 프롬프트 최적화: '{original_prompt}' → '{optimized_prompt[:50]}...'")
                return optimized_prompt
            else:
                logger.warning("⚠️ 프롬프트 최적화 응답이 비어있음 - 원본 사용")
                return original_prompt
                
        except Exception as e:
            logger.error(f"❌ 프롬프트 최적화 실패: {e}")
            return original_prompt

    async def improve_prompt_same_language(self, original_prompt: str) -> str:
        """
        프롬프트를 입력된 언어 그대로 유지하면서 개선
        
        Args:
            original_prompt: 사용자가 입력한 원본 프롬프트
            
        Returns:
            동일 언어로 개선된 프롬프트
        """
        
        try:
            if not self.gemini_client:
                logger.warning("⚠️ Gemini 클라이언트 없음 - 프롬프트 개선 건너뛰기")
                return original_prompt
            
            # 언어 감지 및 동일 언어로 개선하는 메타 프롬프트
            improvement_prompt = f"""
다음 사용자 입력을 동일한 언어로 더 구체적이고 명확하게 개선해주세요:

사용자 입력: "{original_prompt}"

요구사항:
1. 입력된 언어와 동일한 언어로 응답 (한글→한글, 영어→영어)
2. 원래 의도를 정확히 유지
3. 더 구체적이고 상세한 설명 추가
4. 이미지 편집에 유용한 세부사항 포함
5. 자연스럽고 명확한 표현 사용
6. 개선된 프롬프트만 출력 (설명 없이)

예시:
- "빨간 모자 추가" → "이미지의 인물 머리 위에 선명한 빨간색 베레모나 야구모자를 자연스럽게 추가해주세요. 모자는 머리 크기에 맞게 적절한 비율로 배치하고, 기존 헤어스타일과 조화롭게 어울리도록 해주세요."
- "배경 바꿔줘" → "현재 배경을 완전히 새로운 배경으로 교체해주세요. 인물이나 주요 객체는 그대로 유지하면서 배경만 자연스럽게 변경하고, 조명과 색감도 새로운 배경에 맞게 조정해주세요."
"""
            
            loop = asyncio.get_event_loop()
            
            # Gemini 클라이언트로 프롬프트 개선
            response = await loop.run_in_executor(
                None,
                lambda: self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[improvement_prompt]
                )
            )
            
            if response.text:
                improved_prompt = response.text.strip()
                logger.debug(f"✨ 프롬프트 개선: '{original_prompt}' → '{improved_prompt[:50]}...'")
                return improved_prompt
            else:
                logger.warning("⚠️ 개선된 프롬프트 생성 실패 - 빈 응답")
                return original_prompt
                
        except Exception as e:
            logger.error(f"❌ 프롬프트 개선 실패: {e}")
            return original_prompt


# 서비스 인스턴스
image_generation_service = ImageGenerationService()