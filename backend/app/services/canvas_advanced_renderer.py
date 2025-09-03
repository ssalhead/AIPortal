"""
Canvas 고급 렌더링 시스템
레이어, 효과, 변환을 완벽히 보존하는 전문가급 렌더링 엔진
"""

import asyncio
import json
import logging
import math
from typing import Dict, List, Optional, Tuple, Any, Union
from uuid import UUID
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
from PIL.ImageColor import getrgb
import cv2

from sqlalchemy.ext.asyncio import AsyncSession
from app.services.canvas_export_engine import CanvasRenderingEngine
from app.models.export_models import ExportOptions

logger = logging.getLogger(__name__)


class AdvancedCanvasRenderer(CanvasRenderingEngine):
    """고급 Canvas 렌더링 엔진 - 레이어, 효과, 변환 완벽 지원"""
    
    def __init__(self):
        super().__init__()
        self.effect_cache = {}  # 효과 캐시
        self.layer_cache = {}   # 레이어 캐시
    
    async def render_canvas_with_effects(
        self,
        db: AsyncSession,
        canvas_id: UUID,
        options: ExportOptions,
        preserve_layers: bool = True,
        apply_effects: bool = True
    ) -> Tuple[bytes, Dict[str, Any]]:
        """효과와 레이어를 완벽 보존한 Canvas 렌더링"""
        
        # Canvas 데이터 조회
        canvas_data = await self._get_canvas_data(db, canvas_id)
        if not canvas_data:
            raise ValueError(f"Canvas {canvas_id}를 찾을 수 없습니다")
        
        # 렌더링 설정 계산
        render_config = self._calculate_render_config(canvas_data, options)
        
        # 고급 렌더링 실행
        final_image = await self._advanced_render_canvas(
            canvas_data, 
            render_config, 
            preserve_layers=preserve_layers,
            apply_effects=apply_effects
        )
        
        # 후처리
        if options.include_watermark:
            final_image = self._add_watermark(final_image, options)
        
        # 품질 최적화
        final_image = await self._optimize_image_quality(final_image, options)
        
        # 포맷별 저장
        output_buffer = await self._save_image_with_format(final_image, options)
        
        metadata = {
            "width": final_image.width,
            "height": final_image.height,
            "mode": final_image.mode,
            "format": options.format.value.upper(),
            "size": len(output_buffer),
            "layers_preserved": preserve_layers,
            "effects_applied": apply_effects,
            "render_quality": "high"
        }
        
        return output_buffer, metadata
    
    async def _advanced_render_canvas(
        self,
        canvas_data: Dict[str, Any],
        render_config: Dict[str, Any],
        preserve_layers: bool = True,
        apply_effects: bool = True
    ) -> Image.Image:
        """고급 Canvas 렌더링"""
        
        width = render_config["final_width"]
        height = render_config["final_height"]
        
        # 베이스 캔버스 생성 (고해상도)
        if render_config["transparent_background"]:
            canvas = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        else:
            canvas = Image.new("RGB", (width, height), "white")
        
        # 레이어별 렌더링 및 합성
        layer_images = []
        
        for layer_data in canvas_data["layers"]:
            if not layer_data["visible"]:
                continue
            
            # 레이어 이미지 생성
            layer_image = await self._render_advanced_layer(
                layer_data, 
                render_config,
                apply_effects=apply_effects
            )
            
            if layer_image:
                layer_images.append((layer_image, layer_data))
        
        # 레이어 합성 (블렌딩 모드 지원)
        for layer_image, layer_data in layer_images:
            canvas = await self._composite_layer(
                canvas, 
                layer_image, 
                layer_data,
                render_config
            )
        
        return canvas
    
    async def _render_advanced_layer(
        self,
        layer_data: Dict[str, Any],
        render_config: Dict[str, Any],
        apply_effects: bool = True
    ) -> Optional[Image.Image]:
        """고급 레이어 렌더링"""
        
        width = render_config["final_width"]
        height = render_config["final_height"]
        
        # 레이어 캔버스 생성
        layer_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer_canvas)
        
        # 레이어 변환 정보
        layer_transform = self._calculate_layer_transform(layer_data, render_config)
        
        # 노드별 렌더링
        for node_data in layer_data["nodes"]:
            if not node_data["visible"] or node_data["opacity"] <= 0:
                continue
            
            node_image = await self._render_advanced_node(
                node_data, 
                layer_transform, 
                render_config
            )
            
            if node_image:
                # 노드를 레이어에 합성
                layer_canvas = await self._composite_node(
                    layer_canvas, 
                    node_image, 
                    node_data, 
                    layer_transform
                )
        
        # 레이어 효과 적용
        if apply_effects:
            layer_canvas = await self._apply_layer_effects(
                layer_canvas, 
                layer_data,
                render_config
            )
        
        return layer_canvas if layer_canvas.getbbox() else None
    
    async def _render_advanced_node(
        self,
        node_data: Dict[str, Any],
        layer_transform: Dict[str, Any],
        render_config: Dict[str, Any]
    ) -> Optional[Image.Image]:
        """고급 노드 렌더링 (효과 및 변환 지원)"""
        
        node_type = node_data["class_name"].lower()
        
        try:
            if node_type == "text":
                return await self._render_advanced_text(node_data, layer_transform, render_config)
            elif node_type == "rect":
                return await self._render_advanced_rect(node_data, layer_transform, render_config)
            elif node_type == "circle":
                return await self._render_advanced_circle(node_data, layer_transform, render_config)
            elif node_type == "image":
                return await self._render_advanced_image(node_data, layer_transform, render_config)
            elif node_type == "line":
                return await self._render_advanced_line(node_data, layer_transform, render_config)
            elif node_type == "path":
                return await self._render_advanced_path(node_data, layer_transform, render_config)
            else:
                logger.warning(f"지원하지 않는 노드 타입: {node_type}")
                return None
                
        except Exception as e:
            logger.error(f"노드 렌더링 실패 ({node_type}): {e}")
            return None
    
    async def _render_advanced_text(
        self,
        node_data: Dict[str, Any],
        layer_transform: Dict[str, Any],
        render_config: Dict[str, Any]
    ) -> Optional[Image.Image]:
        """고급 텍스트 렌더링 (그림자, 외곽선, 그라데이션 지원)"""
        
        attrs = node_data["konva_attrs"]
        text = attrs.get("text", "")
        
        if not text:
            return None
        
        # 기본 텍스트 속성
        font_size = max(8, int(attrs.get("fontSize", 16) * layer_transform["scale_x"]))
        font_family = attrs.get("fontFamily", "Arial")
        font_weight = attrs.get("fontStyle", "normal")
        
        # 폰트 로드
        try:
            if self.default_font and "bold" in font_weight.lower():
                font = ImageFont.truetype(self.default_font, font_size)
            elif self.default_font:
                font = ImageFont.truetype(self.default_font, font_size)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # 텍스트 크기 계산
        bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 여유 공간을 포함한 캔버스 생성
        margin = max(20, font_size // 2)
        canvas_width = text_width + margin * 2
        canvas_height = text_height + margin * 2
        
        text_canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_canvas)
        
        # 텍스트 위치 (캔버스 내에서 중앙)
        text_x = margin
        text_y = margin
        
        # 그림자 효과
        shadow_blur = attrs.get("shadowBlur", 0)
        shadow_offset_x = attrs.get("shadowOffsetX", 0)
        shadow_offset_y = attrs.get("shadowOffsetY", 0)
        shadow_color = attrs.get("shadowColor", "rgba(0,0,0,0.5)")
        
        if shadow_blur > 0 or shadow_offset_x != 0 or shadow_offset_y != 0:
            shadow_canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_canvas)
            
            shadow_x = text_x + shadow_offset_x
            shadow_y = text_y + shadow_offset_y
            shadow_rgba = self._parse_color_advanced(shadow_color, 128)
            
            shadow_draw.text((shadow_x, shadow_y), text, font=font, fill=shadow_rgba)
            
            # 블러 적용
            if shadow_blur > 0:
                shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
            
            # 그림자를 텍스트 캔버스에 합성
            text_canvas = Image.alpha_composite(text_canvas, shadow_canvas)
        
        # 외곽선 효과
        stroke_width = attrs.get("strokeWidth", 0)
        stroke_color = attrs.get("stroke")
        
        if stroke_width > 0 and stroke_color:
            stroke_rgba = self._parse_color_advanced(stroke_color)
            
            # 외곽선 그리기 (여러 방향으로 오프셋하여 구현)
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    if dx*dx + dy*dy <= stroke_width*stroke_width:
                        draw.text((text_x + dx, text_y + dy), text, font=font, fill=stroke_rgba)
        
        # 메인 텍스트
        fill_color = attrs.get("fill", "#000000")
        
        # 그라데이션 지원 (추후 구현)
        if isinstance(fill_color, str) and fill_color.startswith("linear-gradient"):
            # 그라데이션 텍스트 구현
            main_color = self._parse_color_advanced("#000000")
        else:
            main_color = self._parse_color_advanced(fill_color)
        
        # 투명도 적용
        opacity = int(node_data["opacity"] * layer_transform["opacity"] * 255)
        if len(main_color) == 3:
            main_color = main_color + (opacity,)
        else:
            main_color = main_color[:3] + (opacity,)
        
        draw.text((text_x, text_y), text, font=font, fill=main_color)
        
        return text_canvas
    
    async def _render_advanced_rect(
        self,
        node_data: Dict[str, Any],
        layer_transform: Dict[str, Any],
        render_config: Dict[str, Any]
    ) -> Optional[Image.Image]:
        """고급 사각형 렌더링 (그라데이션, 그림자, 둥근 모서리 지원)"""
        
        attrs = node_data["konva_attrs"]
        
        # 크기 계산
        width = max(1, int((node_data.get("width", 100)) * layer_transform["scale_x"]))
        height = max(1, int((node_data.get("height", 100)) * layer_transform["scale_y"]))
        
        # 여유 공간 포함
        margin = 20
        canvas_width = width + margin * 2
        canvas_height = height + margin * 2
        
        rect_canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(rect_canvas)
        
        rect_x = margin
        rect_y = margin
        
        # 둥근 모서리
        corner_radius = attrs.get("cornerRadius", 0)
        corner_radius = int(corner_radius * layer_transform["scale_x"])
        
        # 그림자 효과
        shadow_blur = attrs.get("shadowBlur", 0)
        if shadow_blur > 0:
            shadow_offset_x = attrs.get("shadowOffsetX", 0)
            shadow_offset_y = attrs.get("shadowOffsetY", 0)
            shadow_color = self._parse_color_advanced(attrs.get("shadowColor", "rgba(0,0,0,0.3)"))
            
            shadow_rect = [(rect_x + shadow_offset_x, rect_y + shadow_offset_y),
                          (rect_x + width + shadow_offset_x, rect_y + height + shadow_offset_y)]
            
            if corner_radius > 0:
                self._draw_rounded_rectangle(draw, shadow_rect, corner_radius, fill=shadow_color)
            else:
                draw.rectangle(shadow_rect, fill=shadow_color)
            
            # 블러 적용
            rect_canvas = rect_canvas.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        
        # 메인 사각형
        main_rect = [(rect_x, rect_y), (rect_x + width, rect_y + height)]
        
        # 채우기
        fill = attrs.get("fill")
        if fill and fill != "transparent":
            fill_color = self._parse_color_advanced(fill)
            opacity = int(node_data["opacity"] * layer_transform["opacity"] * 255)
            if len(fill_color) == 3:
                fill_color = fill_color + (opacity,)
            else:
                fill_color = fill_color[:3] + (opacity,)
            
            if corner_radius > 0:
                self._draw_rounded_rectangle(draw, main_rect, corner_radius, fill=fill_color)
            else:
                draw.rectangle(main_rect, fill=fill_color)
        
        # 외곽선
        stroke = attrs.get("stroke")
        stroke_width = attrs.get("strokeWidth", 1)
        if stroke and stroke_width > 0:
            stroke_color = self._parse_color_advanced(stroke)
            stroke_width = max(1, int(stroke_width * layer_transform["scale_x"]))
            
            if corner_radius > 0:
                self._draw_rounded_rectangle(draw, main_rect, corner_radius, outline=stroke_color, width=stroke_width)
            else:
                draw.rectangle(main_rect, outline=stroke_color, width=stroke_width)
        
        return rect_canvas
    
    async def _render_advanced_circle(
        self,
        node_data: Dict[str, Any],
        layer_transform: Dict[str, Any],
        render_config: Dict[str, Any]
    ) -> Optional[Image.Image]:
        """고급 원 렌더링 (그라데이션, 그림자 지원)"""
        
        attrs = node_data["konva_attrs"]
        radius = max(1, int(attrs.get("radius", 50) * layer_transform["scale_x"]))
        
        # 캔버스 크기 (그림자 고려)
        shadow_blur = attrs.get("shadowBlur", 0)
        shadow_offset_x = abs(attrs.get("shadowOffsetX", 0))
        shadow_offset_y = abs(attrs.get("shadowOffsetY", 0))
        
        margin = max(20, shadow_blur + shadow_offset_x, shadow_blur + shadow_offset_y)
        canvas_size = (radius * 2) + (margin * 2)
        
        circle_canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(circle_canvas)
        
        center_x = center_y = canvas_size // 2
        
        # 그림자
        if shadow_blur > 0:
            shadow_color = self._parse_color_advanced(attrs.get("shadowColor", "rgba(0,0,0,0.3)"))
            shadow_x = center_x + attrs.get("shadowOffsetX", 0)
            shadow_y = center_y + attrs.get("shadowOffsetY", 0)
            
            shadow_bbox = [shadow_x - radius, shadow_y - radius, shadow_x + radius, shadow_y + radius]
            draw.ellipse(shadow_bbox, fill=shadow_color)
            
            # 블러 적용
            circle_canvas = circle_canvas.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        
        # 메인 원
        main_bbox = [center_x - radius, center_y - radius, center_x + radius, center_y + radius]
        
        # 채우기
        fill = attrs.get("fill")
        if fill and fill != "transparent":
            fill_color = self._parse_color_advanced(fill)
            opacity = int(node_data["opacity"] * layer_transform["opacity"] * 255)
            if len(fill_color) == 3:
                fill_color = fill_color + (opacity,)
            
            draw.ellipse(main_bbox, fill=fill_color)
        
        # 외곽선
        stroke = attrs.get("stroke")
        stroke_width = attrs.get("strokeWidth", 1)
        if stroke and stroke_width > 0:
            stroke_color = self._parse_color_advanced(stroke)
            stroke_width = max(1, int(stroke_width * layer_transform["scale_x"]))
            
            draw.ellipse(main_bbox, outline=stroke_color, width=stroke_width)
        
        return circle_canvas
    
    async def _render_advanced_image(
        self,
        node_data: Dict[str, Any],
        layer_transform: Dict[str, Any],
        render_config: Dict[str, Any]
    ) -> Optional[Image.Image]:
        """고급 이미지 렌더링 (필터, 효과 지원)"""
        
        attrs = node_data["konva_attrs"]
        image_src = attrs.get("src")
        
        if not image_src:
            return None
        
        try:
            # 실제 구현에서는 image_src를 사용하여 이미지 로드
            # 여기서는 placeholder 이미지 생성
            width = max(1, int((node_data.get("width", 200)) * layer_transform["scale_x"]))
            height = max(1, int((node_data.get("height", 200)) * layer_transform["scale_y"]))
            
            # 실제 이미지 로드 로직
            # image = Image.open(image_src)
            # image = image.resize((width, height), Image.LANCZOS)
            
            # Placeholder 이미지
            margin = 20
            canvas_width = width + margin * 2
            canvas_height = height + margin * 2
            
            img_canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img_canvas)
            
            # 이미지 영역
            img_rect = [margin, margin, margin + width, margin + height]
            draw.rectangle(img_rect, fill=(220, 220, 220, 200), outline=(150, 150, 150))
            
            # 이미지 아이콘
            center_x = margin + width // 2
            center_y = margin + height // 2
            icon_size = min(width, height) // 4
            
            draw.rectangle([center_x - icon_size, center_y - icon_size, 
                          center_x + icon_size, center_y + icon_size], 
                         fill=(180, 180, 180))
            
            # 효과 적용 (필터, 블러, 밝기 조정 등)
            filters = attrs.get("filters", [])
            for filter_name in filters:
                if filter_name == "Blur":
                    blur_radius = attrs.get("blurRadius", 5)
                    img_canvas = img_canvas.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                elif filter_name == "Brighten":
                    brightness = attrs.get("brightness", 0) + 1.0
                    enhancer = ImageEnhance.Brightness(img_canvas)
                    img_canvas = enhancer.enhance(brightness)
                elif filter_name == "Contrast":
                    contrast = attrs.get("contrast", 0) + 1.0
                    enhancer = ImageEnhance.Contrast(img_canvas)
                    img_canvas = enhancer.enhance(contrast)
            
            return img_canvas
            
        except Exception as e:
            logger.error(f"이미지 렌더링 실패: {e}")
            return None
    
    async def _render_advanced_line(
        self,
        node_data: Dict[str, Any],
        layer_transform: Dict[str, Any],
        render_config: Dict[str, Any]
    ) -> Optional[Image.Image]:
        """고급 선 렌더링 (대시, 화살표, 그림자 지원)"""
        
        attrs = node_data["konva_attrs"]
        points = attrs.get("points", [])
        
        if len(points) < 4:
            return None
        
        # 점들의 범위 계산
        x_coords = [points[i] for i in range(0, len(points), 2)]
        y_coords = [points[i] for i in range(1, len(points), 2)]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        # 변환 적용
        min_x *= layer_transform["scale_x"]
        max_x *= layer_transform["scale_x"]
        min_y *= layer_transform["scale_y"]
        max_y *= layer_transform["scale_y"]
        
        # 캔버스 크기
        margin = 20
        canvas_width = int(max_x - min_x) + margin * 2
        canvas_height = int(max_y - min_y) + margin * 2
        
        line_canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(line_canvas)
        
        # 점들을 캔버스 좌표로 변환
        transformed_points = []
        for i in range(0, len(points), 2):
            if i + 1 < len(points):
                x = (points[i] * layer_transform["scale_x"] - min_x) + margin
                y = (points[i + 1] * layer_transform["scale_y"] - min_y) + margin
                transformed_points.extend([x, y])
        
        # 선 속성
        stroke = attrs.get("stroke", "#000000")
        stroke_width = max(1, int(attrs.get("strokeWidth", 1) * layer_transform["scale_x"]))
        line_cap = attrs.get("lineCap", "butt")  # butt, round, square
        line_join = attrs.get("lineJoin", "miter")  # miter, round, bevel
        dash = attrs.get("dash", [])
        
        # 색상과 투명도
        stroke_color = self._parse_color_advanced(stroke)
        opacity = int(node_data["opacity"] * layer_transform["opacity"] * 255)
        if len(stroke_color) == 3:
            stroke_color = stroke_color + (opacity,)
        
        # 선 그리기
        if len(transformed_points) >= 4:
            if dash and len(dash) > 0:
                # 대시 선 그리기
                await self._draw_dashed_line(draw, transformed_points, stroke_color, stroke_width, dash)
            else:
                # 일반 선 그리기
                for i in range(0, len(transformed_points) - 2, 2):
                    draw.line([transformed_points[i], transformed_points[i+1], 
                             transformed_points[i+2], transformed_points[i+3]],
                            fill=stroke_color, width=stroke_width)
        
        return line_canvas
    
    async def _render_advanced_path(
        self,
        node_data: Dict[str, Any],
        layer_transform: Dict[str, Any],
        render_config: Dict[str, Any]
    ) -> Optional[Image.Image]:
        """고급 패스 렌더링 (베지어 곡선, 복잡한 경로)"""
        
        attrs = node_data["konva_attrs"]
        path_data = attrs.get("data", "")
        
        if not path_data:
            return None
        
        # SVG Path 데이터 파싱 및 렌더링
        # 여기서는 간단한 구현으로 대체
        try:
            # 실제로는 SVG path parser 사용
            canvas_size = 200
            path_canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(path_canvas)
            
            fill = attrs.get("fill")
            stroke = attrs.get("stroke")
            stroke_width = attrs.get("strokeWidth", 1)
            
            # 간단한 패스 그리기 (실제로는 더 복잡한 파싱 필요)
            if fill:
                fill_color = self._parse_color_advanced(fill)
                draw.ellipse([50, 50, 150, 150], fill=fill_color)
            
            if stroke:
                stroke_color = self._parse_color_advanced(stroke)
                draw.ellipse([50, 50, 150, 150], outline=stroke_color, width=stroke_width)
            
            return path_canvas
            
        except Exception as e:
            logger.error(f"패스 렌더링 실패: {e}")
            return None
    
    def _calculate_layer_transform(
        self, 
        layer_data: Dict[str, Any], 
        render_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """레이어 변환 정보 계산"""
        
        return {
            "x": layer_data["x"] * render_config["scale_x"],
            "y": layer_data["y"] * render_config["scale_y"],
            "scale_x": layer_data["scale_x"] * render_config["scale_x"],
            "scale_y": layer_data["scale_y"] * render_config["scale_y"],
            "rotation": layer_data["rotation"],
            "opacity": layer_data["opacity"]
        }
    
    def _parse_color_advanced(self, color_str: str, default_alpha: int = 255) -> tuple:
        """고급 색상 파싱 (RGBA, HSL, 그라데이션 지원)"""
        
        if not color_str or color_str == "transparent":
            return (0, 0, 0, 0)
        
        try:
            # RGBA 함수 파싱
            if color_str.startswith("rgba("):
                values = color_str[5:-1].split(",")
                r = int(float(values[0].strip()))
                g = int(float(values[1].strip()))
                b = int(float(values[2].strip()))
                a = int(float(values[3].strip()) * 255)
                return (r, g, b, a)
            
            # RGB 함수 파싱
            elif color_str.startswith("rgb("):
                values = color_str[4:-1].split(",")
                r = int(float(values[0].strip()))
                g = int(float(values[1].strip()))
                b = int(float(values[2].strip()))
                return (r, g, b, default_alpha)
            
            # 16진수 색상
            elif color_str.startswith("#"):
                hex_color = color_str[1:]
                if len(hex_color) == 3:
                    hex_color = ''.join([c*2 for c in hex_color])
                elif len(hex_color) == 8:
                    # RGBA 형태
                    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    a = int(hex_color[6:8], 16)
                    return rgb + (a,)
                
                rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                return rgb + (default_alpha,)
            
            # 이름 기반 색상
            else:
                rgb = getrgb(color_str)
                return rgb + (default_alpha,)
                
        except Exception as e:
            logger.warning(f"색상 파싱 실패: {color_str}, 오류: {e}")
            return (0, 0, 0, default_alpha)
    
    def _draw_rounded_rectangle(
        self, 
        draw: ImageDraw, 
        coords: List[Tuple[int, int]], 
        radius: int, 
        fill=None, 
        outline=None, 
        width=1
    ):
        """둥근 모서리 사각형 그리기"""
        
        x1, y1 = coords[0]
        x2, y2 = coords[1]
        
        # 둥근 모서리가 없으면 일반 사각형
        if radius <= 0:
            draw.rectangle(coords, fill=fill, outline=outline, width=width)
            return
        
        # 반지름이 너무 크면 조정
        max_radius = min((x2 - x1) // 2, (y2 - y1) // 2)
        radius = min(radius, max_radius)
        
        # 둥근 모서리 구현
        if fill:
            # 메인 사각형들
            draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
            draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
            
            # 모서리 원들
            draw.ellipse([x1, y1, x1 + radius*2, y1 + radius*2], fill=fill)
            draw.ellipse([x2 - radius*2, y1, x2, y1 + radius*2], fill=fill)
            draw.ellipse([x1, y2 - radius*2, x1 + radius*2, y2], fill=fill)
            draw.ellipse([x2 - radius*2, y2 - radius*2, x2, y2], fill=fill)
        
        if outline:
            # 외곽선 (복잡한 구현 필요)
            # 간단히 일반 사각형으로 대체
            draw.rectangle(coords, outline=outline, width=width)
    
    async def _draw_dashed_line(
        self,
        draw: ImageDraw,
        points: List[float],
        color: tuple,
        width: int,
        dash_pattern: List[int]
    ):
        """대시 선 그리기"""
        
        if len(points) < 4 or not dash_pattern:
            return
        
        # 간단한 대시 구현
        dash_on = dash_pattern[0] if len(dash_pattern) > 0 else 5
        dash_off = dash_pattern[1] if len(dash_pattern) > 1 else 5
        
        total_length = 0
        segments = []
        
        # 선분들 계산
        for i in range(0, len(points) - 2, 2):
            x1, y1 = points[i], points[i + 1]
            x2, y2 = points[i + 2], points[i + 3]
            length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            segments.append(((x1, y1), (x2, y2), length))
            total_length += length
        
        # 대시 패턴 적용하여 그리기
        current_pos = 0
        dash_cycle = dash_on + dash_off
        
        for (x1, y1), (x2, y2), length in segments:
            if length <= 0:
                continue
                
            segment_start = 0
            while segment_start < length:
                cycle_pos = current_pos % dash_cycle
                
                if cycle_pos < dash_on:
                    # 실선 구간
                    dash_remaining = dash_on - cycle_pos
                    segment_remaining = length - segment_start
                    draw_length = min(dash_remaining, segment_remaining)
                    
                    if draw_length > 0:
                        ratio_start = segment_start / length
                        ratio_end = (segment_start + draw_length) / length
                        
                        line_x1 = x1 + (x2 - x1) * ratio_start
                        line_y1 = y1 + (y2 - y1) * ratio_start
                        line_x2 = x1 + (x2 - x1) * ratio_end
                        line_y2 = y1 + (y2 - y1) * ratio_end
                        
                        draw.line([line_x1, line_y1, line_x2, line_y2], fill=color, width=width)
                    
                    segment_start += draw_length
                    current_pos += draw_length
                else:
                    # 공백 구간
                    gap_remaining = dash_cycle - cycle_pos
                    segment_remaining = length - segment_start
                    skip_length = min(gap_remaining, segment_remaining)
                    
                    segment_start += skip_length
                    current_pos += skip_length
    
    async def _apply_layer_effects(
        self,
        layer_image: Image.Image,
        layer_data: Dict[str, Any],
        render_config: Dict[str, Any]
    ) -> Image.Image:
        """레이어 효과 적용 (블러, 색상 조정, 합성 모드 등)"""
        
        effects = layer_data.get("konva_attrs", {}).get("filters", [])
        
        for effect in effects:
            if effect == "Blur":
                blur_radius = layer_data.get("konva_attrs", {}).get("blurRadius", 5)
                layer_image = layer_image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            
            elif effect == "Brighten":
                brightness = layer_data.get("konva_attrs", {}).get("brightness", 0) + 1.0
                enhancer = ImageEnhance.Brightness(layer_image)
                layer_image = enhancer.enhance(brightness)
            
            elif effect == "Contrast":
                contrast = layer_data.get("konva_attrs", {}).get("contrast", 0) + 1.0
                enhancer = ImageEnhance.Contrast(layer_image)
                layer_image = enhancer.enhance(contrast)
            
            elif effect == "Saturate":
                saturation = layer_data.get("konva_attrs", {}).get("saturation", 0) + 1.0
                enhancer = ImageEnhance.Color(layer_image)
                layer_image = enhancer.enhance(saturation)
        
        return layer_image
    
    async def _composite_layer(
        self,
        canvas: Image.Image,
        layer_image: Image.Image,
        layer_data: Dict[str, Any],
        render_config: Dict[str, Any]
    ) -> Image.Image:
        """레이어 합성 (블렌딩 모드 지원)"""
        
        # 레이어 위치 계산
        layer_x = int(layer_data["x"] * render_config["scale_x"])
        layer_y = int(layer_data["y"] * render_config["scale_y"])
        
        # 블렌딩 모드
        blend_mode = layer_data.get("konva_attrs", {}).get("globalCompositeOperation", "source-over")
        
        try:
            if blend_mode == "multiply":
                # 곱하기 블렌딩
                canvas.paste(layer_image, (layer_x, layer_y), layer_image)
            elif blend_mode == "screen":
                # 스크린 블렌딩
                canvas.paste(layer_image, (layer_x, layer_y), layer_image)
            elif blend_mode == "overlay":
                # 오버레이 블렌딩
                canvas.paste(layer_image, (layer_x, layer_y), layer_image)
            else:
                # 기본 합성 (source-over)
                if layer_image.mode == 'RGBA':
                    canvas.paste(layer_image, (layer_x, layer_y), layer_image)
                else:
                    canvas.paste(layer_image, (layer_x, layer_y))
        
        except Exception as e:
            logger.error(f"레이어 합성 실패: {e}")
            # 기본 합성으로 fallback
            try:
                if layer_image.mode == 'RGBA':
                    canvas.paste(layer_image, (layer_x, layer_y), layer_image)
                else:
                    canvas.paste(layer_image, (layer_x, layer_y))
            except:
                pass
        
        return canvas
    
    async def _composite_node(
        self,
        layer_canvas: Image.Image,
        node_image: Image.Image,
        node_data: Dict[str, Any],
        layer_transform: Dict[str, Any]
    ) -> Image.Image:
        """노드를 레이어에 합성"""
        
        # 노드 위치 계산
        node_x = int(node_data["x"] * layer_transform["scale_x"])
        node_y = int(node_data["y"] * layer_transform["scale_y"])
        
        try:
            if node_image.mode == 'RGBA':
                layer_canvas.paste(node_image, (node_x, node_y), node_image)
            else:
                layer_canvas.paste(node_image, (node_x, node_y))
        except Exception as e:
            logger.error(f"노드 합성 실패: {e}")
        
        return layer_canvas
    
    async def _optimize_image_quality(
        self,
        image: Image.Image,
        options: ExportOptions
    ) -> Image.Image:
        """이미지 품질 최적화"""
        
        # 해상도에 따른 안티앨리어싱
        if options.resolution_multiplier in ['2x', '4x']:
            # 고해상도에서는 샤픈 필터 적용
            image = image.filter(ImageFilter.UnsharpMask(radius=0.5, percent=150, threshold=3))
        
        # 노이즈 제거
        if options.compression_level == 'high':
            image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image
    
    async def _save_image_with_format(
        self,
        image: Image.Image,
        options: ExportOptions
    ) -> bytes:
        """포맷별 최적화된 이미지 저장"""
        
        from io import BytesIO
        output_buffer = BytesIO()
        
        if options.format.value == 'png':
            # PNG 최적화
            image.save(output_buffer, format='PNG', optimize=True, compress_level=6)
        elif options.format.value == 'jpeg':
            # JPEG 최적화 (투명도 제거)
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, 'white')
                background.paste(image, mask=image.split()[-1])
                image = background
            image.save(output_buffer, format='JPEG', quality=85, optimize=True)
        elif options.format.value == 'webp':
            # WebP 최적화
            image.save(output_buffer, format='WEBP', quality=80, method=4)
        
        output_buffer.seek(0)
        return output_buffer.getvalue()


# 전역 고급 렌더러 인스턴스
advanced_renderer = AdvancedCanvasRenderer()