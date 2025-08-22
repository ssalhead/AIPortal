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
    from google.genai.types import GenerateImagesConfig
except ImportError:
    logger.warning("google-genai 라이브러리가 설치되지 않음. 'pip install google-genai'로 설치해주세요.")
    genai = None
    GenerateImagesConfig = None

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """GCP Imagen 4 전용 이미지 생성 서비스"""
    
    def __init__(self):
        self.jobs_cache: Dict[str, Dict[str, Any]] = {}
        self.max_daily_generations = 50  # 사용자당 일일 최대 생성 수
        self.model_id = "imagen-4.0-generate-001"  # Imagen 4 모델 ID 고정
        
        # Google API 키 설정 (기존 GOOGLE_API_KEY 재사용)
        self.google_api_key = settings.GOOGLE_API_KEY
        
        # Google GenAI 클라이언트 초기화
        self.client = None
        if self.google_api_key and genai:
            try:
                # Google GenAI 1.5.0에서는 configure 함수가 없으므로 직접 API 키로 클라이언트 생성
                self.client = genai.Client(api_key=self.google_api_key)
                logger.info("Imagen 4 클라이언트 초기화 성공")
            except Exception as e:
                logger.error(f"Imagen 4 클라이언트 초기화 실패: {e}")
                self.client = None
        else:
            if not self.google_api_key:
                logger.warning("GOOGLE_API_KEY가 설정되지 않음 - Mock 이미지 생성만 가능")
            if not genai:
                logger.warning("google-genai 라이브러리 없음 - Mock 이미지 생성만 가능")
    
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
            
            # 백그라운드에서 이미지 생성 시작
            asyncio.create_task(self._generate_image_async(job_id))
            
            return {
                "status": "processing",
                "images": [],
                "estimated_completion_time": job_info["estimated_completion_time"],
                "metadata": {
                    "model": self.model_id,
                    "style": style,
                    "size": size,
                    "sample_image_size": sample_image_size,
                    "aspect_ratio": aspect_ratio
                }
            }
            
        except Exception as e:
            logger.error(f"이미지 생성 시작 실패: {e}")
            # 작업 상태를 실패로 업데이트
            if job_id in self.jobs_cache:
                self.jobs_cache[job_id]["status"] = "failed"
                self.jobs_cache[job_id]["error_message"] = str(e)
            
            raise e
    
    async def _generate_image_async(self, job_id: str):
        """비동기 Imagen 4 이미지 생성 작업"""
        
        try:
            job_info = self.jobs_cache.get(job_id)
            if not job_info:
                logger.error(f"작업 정보를 찾을 수 없음: {job_id}")
                return
            
            logger.info(f"Imagen 4 이미지 생성 시작: {job_id}")
            
            # Imagen 4로 이미지 생성
            if self.client:
                images = await self._generate_with_imagen4(job_info)
            else:
                # API 키가 없거나 클라이언트 초기화 실패 시 Mock 이미지
                logger.warning(f"Imagen 4 클라이언트가 사용 불가하여 Mock 이미지 생성: {job_id}")
                images = await self._generate_mock_image(job_info)
            
            # 작업 완료 상태 업데이트
            self.jobs_cache[job_id].update({
                "status": "completed",
                "images": images,
                "completed_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"이미지 생성 완료: {job_id}, {len(images)}개 이미지")
            
            # 일일 사용량 증가
            user_id = job_info["user_id"]
            today = datetime.utcnow().date().isoformat()
            cache_key = f"daily_limit:{user_id}:{today}"
            
            current_count = await cache_manager.get(cache_key) or 0
            await cache_manager.set(
                cache_key, 
                current_count + len(images), 
                ttl_seconds=86400  # 24시간
            )
            
        except Exception as e:
            logger.error(f"이미지 생성 실패: {job_id} - {e}")
            
            # 작업 실패 상태 업데이트
            if job_id in self.jobs_cache:
                self.jobs_cache[job_id].update({
                    "status": "failed",
                    "error_message": str(e),
                    "completed_at": datetime.utcnow().isoformat()
                })
    
    async def _generate_with_imagen4(self, job_info: Dict[str, Any]) -> List[str]:
        """Imagen 4를 사용한 이미지 생성"""
        
        try:
            if not self.client:
                logger.error("Imagen 4 클라이언트가 초기화되지 않음")
                return await self._generate_mock_image(job_info)
            
            # 스타일을 프롬프트에 통합 (프롬프트 기반 스타일링)
            enhanced_prompt = self._enhance_prompt_for_imagen4(
                job_info["prompt"], 
                job_info.get("style", "realistic")
            )
            
            # Imagen 4 설정 - 최소한의 파라미터만 사용
            config = GenerateImagesConfig(
                numberOfImages=job_info.get("num_images", 1),  # 최대 4개
                aspectRatio=job_info.get("aspect_ratio", "1:1")  # 종횡비
            )
            
            logger.info(f"Imagen 4 API 호출: prompt='{enhanced_prompt[:50]}...', config={config}")
            
            # 비동기 실행 (Google GenAI는 동기 함수이므로 executor 사용)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_images(
                    model=self.model_id,
                    prompt=enhanced_prompt,
                    config=config
                )
            )
            
            # 생성된 이미지 처리
            images = []
            for i, generated_image in enumerate(response.generated_images):
                try:
                    # 이미지를 파일로 저장
                    image_url = await self._save_imagen4_image(
                        generated_image.image, 
                        job_info["job_id"], 
                        i
                    )
                    images.append(image_url)
                    
                except Exception as save_error:
                    logger.error(f"이미지 저장 실패: {save_error}")
                    # 저장 실패 시 Base64로 대체
                    image_bytes = generated_image.image.image_bytes
                    base64_data = base64.b64encode(image_bytes).decode()
                    images.append(f"data:image/png;base64,{base64_data}")
            
            logger.info(f"Imagen 4 생성 성공: {len(images)}개 이미지")
            
            # 생성된 이미지 메타데이터를 데이터베이스에 저장
            await self._save_image_metadata(job_info, images, enhanced_prompt)
            
            return images
            
        except Exception as e:
            logger.error(f"Imagen 4 이미지 생성 실패: {e}")
            # 실패 시 Mock 이미지로 대체
            return await self._generate_mock_image(job_info)
    
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
    
    async def _generate_mock_image(self, job_info: Dict[str, Any]) -> List[str]:
        """Mock 이미지 생성 (API 키가 없거나 실패 시 사용)"""
        
        try:
            # 시뮬레이션 대기
            await asyncio.sleep(2)
            
            sample_image_size = job_info.get("sample_image_size", "1K")
            aspect_ratio = job_info.get("aspect_ratio", "1:1")
            style = job_info.get("style", "realistic")
            num_images = job_info.get("num_images", 1)
            
            # 종횡비에 따른 크기 계산
            if sample_image_size == "2K":
                if aspect_ratio == "1:1":
                    size_str = "1024x1024"
                elif aspect_ratio == "4:3":
                    size_str = "1024x768"
                elif aspect_ratio == "3:4":
                    size_str = "768x1024"
                elif aspect_ratio == "16:9":
                    size_str = "1920x1080"
                elif aspect_ratio == "9:16":
                    size_str = "1080x1920"
                else:
                    size_str = "1024x1024"
            else:  # 1K
                if aspect_ratio == "1:1":
                    size_str = "512x512"
                elif aspect_ratio == "4:3":
                    size_str = "512x384"
                elif aspect_ratio == "3:4":
                    size_str = "384x512"
                elif aspect_ratio == "16:9":
                    size_str = "512x288"
                elif aspect_ratio == "9:16":
                    size_str = "288x512"
                else:
                    size_str = "512x512"
            
            # 스타일별 색상 테마
            color_themes = {
                "realistic": "4A90E2/FFFFFF",
                "artistic": "E74C3C/FFFFFF",
                "cartoon": "F39C12/FFFFFF",
                "abstract": "9B59B6/FFFFFF",
                "3d": "27AE60/FFFFFF",
                "anime": "E91E63/FFFFFF"
            }
            
            theme = color_themes.get(style, "4A90E2/FFFFFF")
            
            # Mock 이미지 URL 생성
            images = []
            for i in range(num_images):
                mock_url = f"https://via.placeholder.com/{size_str.replace('x', '/')}/{theme}?text=Imagen+4+Mock+{i+1}+({style})"
                images.append(mock_url)
            
            logger.info(f"Mock 이미지 생성 완료: {job_info['job_id']}, {len(images)}개")
            return images
            
        except Exception as e:
            logger.error(f"Mock 이미지 생성 실패: {e}")
            return []
    
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


# 서비스 인스턴스
image_generation_service = ImageGenerationService()