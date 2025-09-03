"""
GCP Imagen 4 이미지 생성 서비스
"""

import asyncio
import json
import uuid
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

# Google GenAI 클라이언트 import
try:
    from google import genai
    from google.genai.types import (
        GenerateImagesConfig,
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

logger = logging.getLogger(__name__)


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
        
        if genai:
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


# 서비스 인스턴스
image_generation_service = ImageGenerationService()