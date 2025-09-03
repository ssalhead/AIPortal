"""
Canvas Open Graph 이미지 생성 서비스
소셜 미디어 공유를 위한 썸네일 이미지 생성
"""

import io
import hashlib
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import requests
from uuid import UUID
import os

from app.core.config import settings
from app.services.canvas_cache_manager import CanvasCacheManager


class CanvasOGImageService:
    """Canvas Open Graph 이미지 생성 서비스"""
    
    def __init__(self):
        self.cache_manager = None  # 필요시 캐시 매니저 연결
        self.og_width = 1200
        self.og_height = 630
        self.twitter_width = 1200 
        self.twitter_height = 600
        
    def generate_og_image(
        self, 
        canvas_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        canvas_image_url: Optional[str] = None,
        creator_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Canvas용 Open Graph 이미지 생성
        
        Args:
            canvas_id: Canvas ID
            title: 공유 제목
            description: 공유 설명
            canvas_image_url: Canvas 미리보기 이미지 URL
            creator_name: 작성자 이름
            
        Returns:
            생성된 OG 이미지 URL 또는 None
        """
        try:
            # 캐시 키 생성
            cache_key = self._generate_cache_key(canvas_id, title, description)
            cached_url = self._get_cached_og_image(cache_key)
            if cached_url:
                return cached_url
            
            # 이미지 생성
            og_image = self._create_og_image(
                title or "Untitled Canvas",
                description,
                canvas_image_url,
                creator_name
            )
            
            # 이미지 저장
            image_url = self._save_og_image(cache_key, og_image)
            
            # 캐시에 저장
            self._cache_og_image_url(cache_key, image_url)
            
            return image_url
            
        except Exception as e:
            print(f"Failed to generate OG image: {e}")
            return None
    
    def generate_twitter_card_image(
        self,
        canvas_id: UUID,
        title: Optional[str] = None,
        canvas_image_url: Optional[str] = None
    ) -> Optional[str]:
        """Twitter Card용 이미지 생성"""
        try:
            cache_key = f"twitter_{self._generate_cache_key(canvas_id, title)}"
            cached_url = self._get_cached_og_image(cache_key)
            if cached_url:
                return cached_url
            
            twitter_image = self._create_twitter_card_image(
                title or "Untitled Canvas",
                canvas_image_url
            )
            
            image_url = self._save_og_image(cache_key, twitter_image)
            self._cache_og_image_url(cache_key, image_url)
            
            return image_url
            
        except Exception as e:
            print(f"Failed to generate Twitter card image: {e}")
            return None
    
    def _create_og_image(
        self,
        title: str,
        description: Optional[str],
        canvas_image_url: Optional[str],
        creator_name: Optional[str]
    ) -> Image.Image:
        """Open Graph 이미지 생성"""
        
        # 기본 캔버스 생성
        img = Image.new('RGB', (self.og_width, self.og_height), color='#ffffff')
        draw = ImageDraw.Draw(img)
        
        # 브랜드 색상 및 스타일
        primary_color = '#2563eb'  # blue-600
        secondary_color = '#f3f4f6'  # gray-100
        text_color = '#1f2937'  # gray-800
        subtitle_color = '#6b7280'  # gray-500
        
        # 배경 그라데이션 효과
        self._draw_gradient_background(img, primary_color)
        
        # Canvas 이미지가 있는 경우 썸네일로 표시
        if canvas_image_url:
            try:
                canvas_thumb = self._get_canvas_thumbnail(canvas_image_url)
                if canvas_thumb:
                    # 오른쪽에 썸네일 배치
                    thumb_size = (400, 300)
                    canvas_thumb = canvas_thumb.resize(thumb_size, Image.Resampling.LANCZOS)
                    
                    # 그림자 효과
                    shadow_offset = 10
                    shadow = Image.new('RGBA', 
                                     (thumb_size[0] + shadow_offset, thumb_size[1] + shadow_offset),
                                     (0, 0, 0, 50))
                    
                    # 이미지 위치 (오른쪽 상단)
                    img_x = self.og_width - thumb_size[0] - 60
                    img_y = 80
                    
                    # 그림자 먼저 붙이기
                    img.paste(shadow, (img_x + shadow_offset, img_y + shadow_offset), shadow)
                    img.paste(canvas_thumb, (img_x, img_y))
            except Exception as e:
                print(f"Failed to add canvas thumbnail: {e}")
        
        # 폰트 설정 (시스템 폰트 사용)
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
            desc_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            meta_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            # 폴백 폰트
            title_font = ImageFont.load_default()
            desc_font = ImageFont.load_default()  
            meta_font = ImageFont.load_default()
        
        # 텍스트 영역 정의
        text_x = 60
        text_width = 600 if canvas_image_url else 1080
        
        # 제목 그리기
        title_lines = self._wrap_text(title, title_font, text_width)
        y_pos = 120
        for line in title_lines[:2]:  # 최대 2줄
            draw.text((text_x, y_pos), line, fill=text_color, font=title_font)
            y_pos += 70
        
        # 설명 그리기
        if description:
            y_pos += 30
            desc_lines = self._wrap_text(description, desc_font, text_width)
            for line in desc_lines[:3]:  # 최대 3줄
                draw.text((text_x, y_pos), line, fill=subtitle_color, font=desc_font)
                y_pos += 45
        
        # 하단 메타 정보
        y_pos = self.og_height - 100
        
        # AI Portal 브랜딩
        brand_text = "🎨 AI Portal Canvas"
        draw.text((text_x, y_pos), brand_text, fill=primary_color, font=meta_font)
        
        # 작성자 정보
        if creator_name:
            creator_text = f"Created by {creator_name}"
            # 오른쪽 정렬
            creator_bbox = draw.textbbox((0, 0), creator_text, font=meta_font)
            creator_x = self.og_width - creator_bbox[2] - 60
            draw.text((creator_x, y_pos), creator_text, fill=subtitle_color, font=meta_font)
        
        return img
    
    def _create_twitter_card_image(
        self,
        title: str,
        canvas_image_url: Optional[str]
    ) -> Image.Image:
        """Twitter Card 이미지 생성 (요약 레이아웃)"""
        
        img = Image.new('RGB', (self.twitter_width, self.twitter_height), color='#ffffff')
        draw = ImageDraw.Draw(img)
        
        # 단순한 레이아웃
        primary_color = '#1da1f2'  # Twitter 블루
        
        # 배경
        self._draw_gradient_background(img, primary_color, opacity=0.1)
        
        # Canvas 이미지 중앙에 크게 표시
        if canvas_image_url:
            try:
                canvas_img = self._get_canvas_thumbnail(canvas_image_url)
                if canvas_img:
                    # 중앙에 큰 썸네일
                    thumb_size = (600, 400)
                    canvas_img = canvas_img.resize(thumb_size, Image.Resampling.LANCZOS)
                    
                    img_x = (self.twitter_width - thumb_size[0]) // 2
                    img_y = (self.twitter_height - thumb_size[1]) // 2 - 50
                    
                    img.paste(canvas_img, (img_x, img_y))
            except Exception as e:
                print(f"Failed to add canvas thumbnail to Twitter card: {e}")
        
        # 제목 (하단)
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        except:
            title_font = ImageFont.load_default()
        
        title_lines = self._wrap_text(title, title_font, self.twitter_width - 120)
        y_pos = self.twitter_height - 120
        
        for line in title_lines[:1]:  # 1줄만
            # 중앙 정렬
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_x = (self.twitter_width - bbox[2]) // 2
            draw.text((text_x, y_pos), line, fill='#14171a', font=title_font)
        
        return img
    
    def _draw_gradient_background(self, img: Image.Image, color: str, opacity: float = 0.05):
        """그라데이션 배경 그리기"""
        overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        # 색상을 RGB로 변환
        color_rgb = self._hex_to_rgb(color)
        
        # 간단한 선형 그라데이션
        for i in range(img.height):
            alpha = int(255 * opacity * (1 - i / img.height))
            color_rgba = color_rgb + (alpha,)
            draw.line([(0, i), (img.width, i)], fill=color_rgba)
        
        img.paste(overlay, (0, 0), overlay)
    
    def _get_canvas_thumbnail(self, image_url: str) -> Optional[Image.Image]:
        """Canvas 이미지 다운로드 및 썸네일 생성"""
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            img = Image.open(io.BytesIO(response.content))
            
            # RGBA를 RGB로 변환 (필요한 경우)
            if img.mode in ('RGBA', 'LA', 'P'):
                # 흰색 배경으로 변환
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            return img
            
        except Exception as e:
            print(f"Failed to download canvas image: {e}")
            return None
    
    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> list:
        """텍스트 줄바꿈"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # 단어가 너무 긴 경우
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """HEX 색상을 RGB 튜플로 변환"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _generate_cache_key(self, canvas_id: UUID, title: Optional[str] = None, description: Optional[str] = None) -> str:
        """캐시 키 생성"""
        content = f"{canvas_id}_{title or ''}_{description or ''}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_og_image(self, cache_key: str) -> Optional[str]:
        """캐시된 OG 이미지 URL 조회"""
        # TODO: 실제 캐시 시스템과 연동
        return None
    
    def _save_og_image(self, cache_key: str, image: Image.Image) -> str:
        """OG 이미지 저장 및 URL 반환"""
        try:
            # 저장 경로 설정
            og_dir = os.path.join(settings.UPLOAD_DIR or "uploads", "og_images")
            os.makedirs(og_dir, exist_ok=True)
            
            # 파일명 생성
            filename = f"{cache_key}.png"
            filepath = os.path.join(og_dir, filename)
            
            # 이미지 저장
            image.save(filepath, 'PNG', optimize=True, quality=90)
            
            # URL 생성
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            image_url = f"{base_url}/uploads/og_images/{filename}"
            
            return image_url
            
        except Exception as e:
            print(f"Failed to save OG image: {e}")
            raise
    
    def _cache_og_image_url(self, cache_key: str, image_url: str):
        """생성된 OG 이미지 URL 캐시"""
        # TODO: 캐시 시스템과 연동 (24시간 TTL)
        pass
    
    def cleanup_expired_images(self):
        """만료된 OG 이미지 정리"""
        try:
            og_dir = os.path.join(settings.UPLOAD_DIR or "uploads", "og_images")
            if not os.path.exists(og_dir):
                return
            
            import time
            current_time = time.time()
            
            for filename in os.listdir(og_dir):
                filepath = os.path.join(og_dir, filename)
                
                # 7일이 지난 파일 삭제
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getctime(filepath)
                    if file_age > (7 * 24 * 60 * 60):  # 7일
                        os.remove(filepath)
                        print(f"Removed expired OG image: {filename}")
                        
        except Exception as e:
            print(f"Failed to cleanup expired OG images: {e}")
    
    def generate_preview_thumbnail(self, canvas_image_url: str) -> Optional[str]:
        """Canvas 이미지의 작은 미리보기 썸네일 생성"""
        try:
            canvas_img = self._get_canvas_thumbnail(canvas_image_url)
            if not canvas_img:
                return None
            
            # 작은 썸네일 (400x300)
            thumbnail = canvas_img.resize((400, 300), Image.Resampling.LANCZOS)
            
            # 저장
            cache_key = hashlib.md5(canvas_image_url.encode()).hexdigest()
            filename = f"thumb_{cache_key}.png"
            
            thumbs_dir = os.path.join(settings.UPLOAD_DIR or "uploads", "thumbnails")
            os.makedirs(thumbs_dir, exist_ok=True)
            
            filepath = os.path.join(thumbs_dir, filename)
            thumbnail.save(filepath, 'PNG', optimize=True, quality=85)
            
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            return f"{base_url}/uploads/thumbnails/{filename}"
            
        except Exception as e:
            print(f"Failed to generate preview thumbnail: {e}")
            return None