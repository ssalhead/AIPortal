"""
Canvas 내보내기 엔진
고품질 렌더링과 다양한 포맷 지원을 제공하는 전문가급 내보내기 시스템
"""

import asyncio
import json
import logging
import os
import tempfile
import time
import zipfile
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from uuid import UUID, uuid4

# 이미지 처리
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cairosvg
from wand.image import Image as WandImage
from wand.color import Color as WandColor

# PDF 생성
from reportlab.lib.pagesizes import A4, A3, A5, letter, legal
from reportlab.lib.units import mm, inch
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, white, gray

# 데이터베이스 및 모델
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models.canvas import Canvas, KonvaLayer, KonvaNode
from app.db.models.image_history import ImageHistory
from app.models.export_models import *
from app.core.config import settings

logger = logging.getLogger(__name__)


class CanvasRenderingEngine:
    """Canvas 렌더링 엔진"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="canvas_export_")
        self._setup_fonts()
    
    def _setup_fonts(self):
        """폰트 설정"""
        try:
            # 시스템 기본 폰트 찾기
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/Windows/Fonts/arial.ttf"
            ]
            
            self.default_font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    self.default_font = font_path
                    break
                    
        except Exception as e:
            logger.warning(f"폰트 설정 실패: {e}")
            self.default_font = None
    
    async def render_canvas_to_image(
        self,
        db: AsyncSession,
        canvas_id: UUID,
        options: ExportOptions,
        format_options: Optional[Union[JPEGOptions, PNGOptions, WebPOptions]] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Canvas를 이미지로 렌더링"""
        
        # Canvas 데이터 조회
        canvas_data = await self._get_canvas_data(db, canvas_id)
        if not canvas_data:
            raise ValueError(f"Canvas {canvas_id}를 찾을 수 없습니다")
        
        # 렌더링 설정 계산
        render_config = self._calculate_render_config(canvas_data, options)
        
        # 이미지 생성
        image = await self._create_canvas_image(canvas_data, render_config)
        
        # 후처리 적용
        if options.include_watermark:
            image = self._add_watermark(image, options)
        
        # 포맷별 저장
        output_buffer = BytesIO()
        image_format = options.format.value.upper()
        
        if options.format == ExportFormat.PNG:
            png_opts = format_options or PNGOptions()
            image.save(
                output_buffer,
                format=image_format,
                optimize=png_opts.compression_level > 0,
                compress_level=png_opts.compression_level
            )
        elif options.format == ExportFormat.JPEG:
            jpeg_opts = format_options or JPEGOptions()
            # JPEG는 투명도를 지원하지 않으므로 배경 추가
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, 'white')
                background.paste(image, mask=image.split()[-1])
                image = background
            
            image.save(
                output_buffer,
                format=image_format,
                quality=jpeg_opts.quality,
                optimize=jpeg_opts.optimize,
                progressive=jpeg_opts.progressive
            )
        elif options.format == ExportFormat.WEBP:
            webp_opts = format_options or WebPOptions()
            image.save(
                output_buffer,
                format=image_format,
                quality=webp_opts.quality,
                lossless=webp_opts.lossless,
                method=webp_opts.method
            )
        
        output_buffer.seek(0)
        
        metadata = {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": image_format,
            "size": len(output_buffer.getvalue())
        }
        
        return output_buffer.getvalue(), metadata
    
    async def render_canvas_to_svg(
        self,
        db: AsyncSession,
        canvas_id: UUID,
        options: ExportOptions,
        svg_options: Optional[SVGOptions] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Canvas를 SVG로 렌더링"""
        
        canvas_data = await self._get_canvas_data(db, canvas_id)
        if not canvas_data:
            raise ValueError(f"Canvas {canvas_id}를 찾을 수 없습니다")
        
        svg_opts = svg_options or SVGOptions()
        
        # SVG 문서 생성
        svg_content = await self._create_svg_from_canvas(canvas_data, options, svg_opts)
        
        metadata = {
            "width": canvas_data["stage_config"]["width"],
            "height": canvas_data["stage_config"]["height"],
            "format": "SVG",
            "size": len(svg_content.encode('utf-8'))
        }
        
        return svg_content, metadata
    
    async def _get_canvas_data(self, db: AsyncSession, canvas_id: UUID) -> Optional[Dict[str, Any]]:
        """Canvas 데이터 조회"""
        try:
            # Canvas 기본 정보
            canvas_query = select(Canvas).where(Canvas.id == canvas_id)
            canvas_result = await db.execute(canvas_query)
            canvas = canvas_result.scalar_one_or_none()
            
            if not canvas:
                return None
            
            # 레이어들 조회
            layers_query = (
                select(KonvaLayer)
                .where(KonvaLayer.canvas_id == canvas_id)
                .order_by(KonvaLayer.layer_index)
            )
            layers_result = await db.execute(layers_query)
            layers = layers_result.scalars().all()
            
            # 각 레이어의 노드들 조회
            layers_data = []
            for layer in layers:
                nodes_query = (
                    select(KonvaNode)
                    .where(KonvaNode.layer_id == layer.id)
                    .order_by(KonvaNode.z_index)
                )
                nodes_result = await db.execute(nodes_query)
                nodes = nodes_result.scalars().all()
                
                layer_data = {
                    "id": str(layer.id),
                    "name": layer.name,
                    "visible": layer.visible,
                    "opacity": layer.opacity,
                    "x": layer.x,
                    "y": layer.y,
                    "scale_x": layer.scale_x,
                    "scale_y": layer.scale_y,
                    "rotation": layer.rotation,
                    "konva_attrs": layer.konva_attrs,
                    "nodes": [
                        {
                            "id": str(node.id),
                            "type": node.node_type,
                            "class_name": node.class_name,
                            "x": node.x,
                            "y": node.y,
                            "width": node.width,
                            "height": node.height,
                            "scale_x": node.scale_x,
                            "scale_y": node.scale_y,
                            "rotation": node.rotation,
                            "opacity": node.opacity,
                            "visible": node.visible,
                            "konva_attrs": node.konva_attrs
                        }
                        for node in nodes
                    ]
                }
                layers_data.append(layer_data)
            
            return {
                "id": str(canvas.id),
                "name": canvas.name,
                "stage_config": canvas.stage_config,
                "layers": layers_data
            }
            
        except Exception as e:
            logger.error(f"Canvas 데이터 조회 실패: {e}")
            return None
    
    def _calculate_render_config(self, canvas_data: Dict[str, Any], options: ExportOptions) -> Dict[str, Any]:
        """렌더링 설정 계산"""
        
        # 기본 크기
        base_width = canvas_data["stage_config"]["width"]
        base_height = canvas_data["stage_config"]["height"]
        
        # 사전 설정 또는 커스텀 크기
        if options.social_preset != SocialMediaPreset.CUSTOM:
            target_width, target_height = SocialMediaOptimization.get_preset_dimensions(options.social_preset)
        else:
            target_width = options.custom_width or base_width
            target_height = options.custom_height or base_height
        
        # 해상도 배수 적용
        multiplier = int(options.resolution_multiplier.value[0])  # "1x" -> 1
        final_width = target_width * multiplier
        final_height = target_height * multiplier
        
        # 스케일 계산
        scale_x = final_width / base_width
        scale_y = final_height / base_height
        
        return {
            "base_width": base_width,
            "base_height": base_height,
            "final_width": final_width,
            "final_height": final_height,
            "scale_x": scale_x,
            "scale_y": scale_y,
            "transparent_background": options.transparent_background
        }
    
    async def _create_canvas_image(self, canvas_data: Dict[str, Any], render_config: Dict[str, Any]) -> Image.Image:
        """Canvas를 PIL Image로 생성"""
        
        width = render_config["final_width"]
        height = render_config["final_height"]
        
        # 배경 설정
        if render_config["transparent_background"]:
            image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        else:
            image = Image.new("RGB", (width, height), "white")
        
        draw = ImageDraw.Draw(image)
        
        # 레이어별 렌더링
        for layer in canvas_data["layers"]:
            if not layer["visible"]:
                continue
            
            await self._render_layer(image, draw, layer, render_config)
        
        return image
    
    async def _render_layer(self, image: Image.Image, draw: ImageDraw, layer_data: Dict[str, Any], render_config: Dict[str, Any]):
        """레이어 렌더링"""
        
        if layer_data["opacity"] <= 0:
            return
        
        # 레이어 변환 정보
        layer_transform = {
            "x": layer_data["x"] * render_config["scale_x"],
            "y": layer_data["y"] * render_config["scale_y"],
            "scale_x": layer_data["scale_x"] * render_config["scale_x"],
            "scale_y": layer_data["scale_y"] * render_config["scale_y"],
            "rotation": layer_data["rotation"],
            "opacity": layer_data["opacity"]
        }
        
        # 노드별 렌더링
        for node in layer_data["nodes"]:
            if not node["visible"] or node["opacity"] <= 0:
                continue
            
            await self._render_node(image, draw, node, layer_transform, render_config)
    
    async def _render_node(
        self, 
        image: Image.Image, 
        draw: ImageDraw, 
        node_data: Dict[str, Any], 
        layer_transform: Dict[str, Any],
        render_config: Dict[str, Any]
    ):
        """노드 렌더링"""
        
        node_type = node_data["class_name"].lower()
        
        try:
            if node_type == "text":
                await self._render_text_node(image, draw, node_data, layer_transform, render_config)
            elif node_type == "rect":
                await self._render_rect_node(image, draw, node_data, layer_transform, render_config)
            elif node_type == "circle":
                await self._render_circle_node(image, draw, node_data, layer_transform, render_config)
            elif node_type == "image":
                await self._render_image_node(image, draw, node_data, layer_transform, render_config)
            elif node_type == "line":
                await self._render_line_node(image, draw, node_data, layer_transform, render_config)
            else:
                logger.warning(f"지원하지 않는 노드 타입: {node_type}")
                
        except Exception as e:
            logger.error(f"노드 렌더링 실패 ({node_type}): {e}")
    
    async def _render_text_node(self, image: Image.Image, draw: ImageDraw, node_data: Dict[str, Any], layer_transform: Dict[str, Any], render_config: Dict[str, Any]):
        """텍스트 노드 렌더링"""
        
        attrs = node_data["konva_attrs"]
        text = attrs.get("text", "")
        
        if not text:
            return
        
        # 위치 계산
        x = (node_data["x"] + layer_transform["x"]) * layer_transform["scale_x"]
        y = (node_data["y"] + layer_transform["y"]) * layer_transform["scale_y"]
        
        # 폰트 설정
        font_size = int(attrs.get("fontSize", 16) * layer_transform["scale_x"])
        try:
            if self.default_font:
                font = ImageFont.truetype(self.default_font, font_size)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # 색상
        fill_color = attrs.get("fill", "#000000")
        if fill_color.startswith("#"):
            fill_color = fill_color[1:]
        
        try:
            fill_rgb = tuple(int(fill_color[i:i+2], 16) for i in (0, 2, 4))
        except:
            fill_rgb = (0, 0, 0)
        
        # 투명도 적용
        opacity = int(node_data["opacity"] * layer_transform["opacity"] * 255)
        if len(fill_rgb) == 3:
            fill_color_with_alpha = fill_rgb + (opacity,)
        else:
            fill_color_with_alpha = fill_rgb
        
        # 텍스트 그리기
        draw.text((x, y), text, font=font, fill=fill_color_with_alpha)
    
    async def _render_rect_node(self, image: Image.Image, draw: ImageDraw, node_data: Dict[str, Any], layer_transform: Dict[str, Any], render_config: Dict[str, Any]):
        """사각형 노드 렌더링"""
        
        attrs = node_data["konva_attrs"]
        
        # 위치와 크기
        x = (node_data["x"] + layer_transform["x"]) * layer_transform["scale_x"]
        y = (node_data["y"] + layer_transform["y"]) * layer_transform["scale_y"]
        width = (node_data["width"] or 100) * layer_transform["scale_x"]
        height = (node_data["height"] or 100) * layer_transform["scale_y"]
        
        # 색상 설정
        fill = attrs.get("fill")
        stroke = attrs.get("stroke")
        stroke_width = int(attrs.get("strokeWidth", 1) * layer_transform["scale_x"])
        
        # 투명도
        opacity = int(node_data["opacity"] * layer_transform["opacity"] * 255)
        
        bbox = [x, y, x + width, y + height]
        
        # 채우기
        if fill and fill != "transparent":
            fill_color = self._parse_color(fill, opacity)
            draw.rectangle(bbox, fill=fill_color)
        
        # 외곽선
        if stroke and stroke_width > 0:
            stroke_color = self._parse_color(stroke, opacity)
            draw.rectangle(bbox, outline=stroke_color, width=stroke_width)
    
    async def _render_circle_node(self, image: Image.Image, draw: ImageDraw, node_data: Dict[str, Any], layer_transform: Dict[str, Any], render_config: Dict[str, Any]):
        """원 노드 렌더링"""
        
        attrs = node_data["konva_attrs"]
        
        # 중심과 반지름
        x = (node_data["x"] + layer_transform["x"]) * layer_transform["scale_x"]
        y = (node_data["y"] + layer_transform["y"]) * layer_transform["scale_y"]
        radius = attrs.get("radius", 50) * layer_transform["scale_x"]
        
        bbox = [x - radius, y - radius, x + radius, y + radius]
        
        # 색상과 투명도
        fill = attrs.get("fill")
        stroke = attrs.get("stroke")
        stroke_width = int(attrs.get("strokeWidth", 1) * layer_transform["scale_x"])
        opacity = int(node_data["opacity"] * layer_transform["opacity"] * 255)
        
        # 채우기
        if fill and fill != "transparent":
            fill_color = self._parse_color(fill, opacity)
            draw.ellipse(bbox, fill=fill_color)
        
        # 외곽선
        if stroke and stroke_width > 0:
            stroke_color = self._parse_color(stroke, opacity)
            draw.ellipse(bbox, outline=stroke_color, width=stroke_width)
    
    async def _render_image_node(self, image: Image.Image, draw: ImageDraw, node_data: Dict[str, Any], layer_transform: Dict[str, Any], render_config: Dict[str, Any]):
        """이미지 노드 렌더링"""
        
        attrs = node_data["konva_attrs"]
        image_src = attrs.get("src")
        
        if not image_src:
            return
        
        try:
            # 이미지 로드 (실제 구현에서는 image_src에서 이미지를 로드)
            # 여기서는 placeholder로 처리
            x = (node_data["x"] + layer_transform["x"]) * layer_transform["scale_x"]
            y = (node_data["y"] + layer_transform["y"]) * layer_transform["scale_y"]
            width = (node_data["width"] or 100) * layer_transform["scale_x"]
            height = (node_data["height"] or 100) * layer_transform["scale_y"]
            
            # 이미지 placeholder 그리기
            bbox = [x, y, x + width, y + height]
            draw.rectangle(bbox, fill=(200, 200, 200, 128), outline=(100, 100, 100))
            draw.text((x + 10, y + height//2), "Image", fill=(50, 50, 50))
            
        except Exception as e:
            logger.error(f"이미지 노드 렌더링 실패: {e}")
    
    async def _render_line_node(self, image: Image.Image, draw: ImageDraw, node_data: Dict[str, Any], layer_transform: Dict[str, Any], render_config: Dict[str, Any]):
        """선 노드 렌더링"""
        
        attrs = node_data["konva_attrs"]
        points = attrs.get("points", [])
        
        if len(points) < 4:  # 최소 2개 점 (x1, y1, x2, y2)
            return
        
        # 점들을 변환
        transformed_points = []
        for i in range(0, len(points), 2):
            if i + 1 < len(points):
                x = (points[i] + layer_transform["x"]) * layer_transform["scale_x"]
                y = (points[i + 1] + layer_transform["y"]) * layer_transform["scale_y"]
                transformed_points.extend([x, y])
        
        # 선 그리기
        stroke = attrs.get("stroke", "#000000")
        stroke_width = int(attrs.get("strokeWidth", 1) * layer_transform["scale_x"])
        opacity = int(node_data["opacity"] * layer_transform["opacity"] * 255)
        stroke_color = self._parse_color(stroke, opacity)
        
        if len(transformed_points) >= 4:
            for i in range(0, len(transformed_points) - 2, 2):
                draw.line(
                    [transformed_points[i], transformed_points[i+1], 
                     transformed_points[i+2], transformed_points[i+3]],
                    fill=stroke_color,
                    width=stroke_width
                )
    
    def _parse_color(self, color_str: str, opacity: int = 255) -> tuple:
        """색상 문자열을 RGBA 튜플로 변환"""
        
        if not color_str or color_str == "transparent":
            return (0, 0, 0, 0)
        
        if color_str.startswith("#"):
            hex_color = color_str[1:]
            try:
                if len(hex_color) == 3:
                    hex_color = ''.join([c*2 for c in hex_color])
                rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                return rgb + (opacity,)
            except:
                return (0, 0, 0, opacity)
        
        # 기본 색상들
        colors = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "cyan": (0, 255, 255),
            "magenta": (255, 0, 255),
        }
        
        rgb = colors.get(color_str.lower(), (0, 0, 0))
        return rgb + (opacity,)
    
    def _add_watermark(self, image: Image.Image, options: ExportOptions) -> Image.Image:
        """워터마크 추가"""
        
        if not options.watermark_text:
            return image
        
        # 워터마크용 레이어 생성
        watermark_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(watermark_layer)
        
        # 폰트 크기 계산 (이미지 크기에 비례)
        font_size = max(12, min(image.width, image.height) // 40)
        
        try:
            if self.default_font:
                font = ImageFont.truetype(self.default_font, font_size)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), options.watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 위치 계산
        margin = 20
        positions = {
            "top-left": (margin, margin),
            "top-right": (image.width - text_width - margin, margin),
            "bottom-left": (margin, image.height - text_height - margin),
            "bottom-right": (image.width - text_width - margin, image.height - text_height - margin),
            "center": ((image.width - text_width) // 2, (image.height - text_height) // 2)
        }
        
        position = positions.get(options.watermark_position, positions["bottom-right"])
        
        # 워터마크 그리기 (반투명)
        draw.text(position, options.watermark_text, font=font, fill=(255, 255, 255, 128))
        
        # 합성
        result = Image.alpha_composite(image.convert("RGBA"), watermark_layer)
        return result if image.mode == "RGBA" else result.convert(image.mode)
    
    async def _create_svg_from_canvas(self, canvas_data: Dict[str, Any], options: ExportOptions, svg_options: SVGOptions) -> str:
        """Canvas를 SVG로 변환"""
        
        stage_config = canvas_data["stage_config"]
        width = stage_config["width"]
        height = stage_config["height"]
        
        # SVG 헤더
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<defs>',
            '<style type="text/css">',
            '.konva-text { font-family: Arial, sans-serif; }',
            '</style>',
            '</defs>'
        ]
        
        # 배경
        if not options.transparent_background:
            svg_parts.append(f'<rect width="100%" height="100%" fill="white"/>')
        
        # 레이어별 렌더링
        for layer in canvas_data["layers"]:
            if not layer["visible"]:
                continue
            
            layer_group = f'<g opacity="{layer["opacity"]}">'
            svg_parts.append(layer_group)
            
            # 노드별 SVG 요소 생성
            for node in layer["nodes"]:
                if not node["visible"]:
                    continue
                
                svg_element = self._create_svg_element(node)
                if svg_element:
                    svg_parts.append(svg_element)
            
            svg_parts.append('</g>')
        
        svg_parts.append('</svg>')
        
        return '\n'.join(svg_parts)
    
    def _create_svg_element(self, node_data: Dict[str, Any]) -> Optional[str]:
        """노드를 SVG 요소로 변환"""
        
        node_type = node_data["class_name"].lower()
        attrs = node_data["konva_attrs"]
        
        # 공통 속성
        common_attrs = [
            f'opacity="{node_data["opacity"]}"',
            f'transform="translate({node_data["x"]},{node_data["y"]}) scale({node_data["scale_x"]},{node_data["scale_y"]}) rotate({node_data["rotation"]})"'
        ]
        
        if node_type == "text":
            text = attrs.get("text", "")
            font_size = attrs.get("fontSize", 16)
            fill = attrs.get("fill", "#000000")
            
            return f'<text {" ".join(common_attrs)} font-size="{font_size}" fill="{fill}" class="konva-text">{text}</text>'
        
        elif node_type == "rect":
            width = node_data.get("width", 100)
            height = node_data.get("height", 100)
            fill = attrs.get("fill", "transparent")
            stroke = attrs.get("stroke", "none")
            stroke_width = attrs.get("strokeWidth", 1)
            
            return f'<rect {" ".join(common_attrs)} width="{width}" height="{height}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
        
        elif node_type == "circle":
            radius = attrs.get("radius", 50)
            fill = attrs.get("fill", "transparent")
            stroke = attrs.get("stroke", "none")
            stroke_width = attrs.get("strokeWidth", 1)
            
            return f'<circle {" ".join(common_attrs)} r="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
        
        elif node_type == "line":
            points = attrs.get("points", [])
            if len(points) >= 4:
                points_str = " ".join([f"{points[i]},{points[i+1]}" for i in range(0, len(points), 2)])
                stroke = attrs.get("stroke", "#000000")
                stroke_width = attrs.get("strokeWidth", 1)
                
                return f'<polyline {" ".join(common_attrs)} points="{points_str}" fill="none" stroke="{stroke}" stroke-width="{stroke_width}"/>'
        
        return None


class PDFExportEngine:
    """PDF 내보내기 엔진"""
    
    def __init__(self):
        self.page_sizes = {
            "A4": A4,
            "A3": A3,
            "A5": A5,
            "Letter": letter,
            "Legal": legal
        }
    
    async def create_pdf_from_canvas(
        self,
        db: AsyncSession,
        canvas_id: UUID,
        options: ExportOptions,
        pdf_options: PDFOptions
    ) -> Tuple[bytes, Dict[str, Any]]:
        """단일 Canvas를 PDF로 변환"""
        
        # Canvas를 이미지로 렌더링
        renderer = CanvasRenderingEngine()
        image_data, image_metadata = await renderer.render_canvas_to_image(
            db, canvas_id, options
        )
        
        # PDF 생성
        pdf_buffer = BytesIO()
        page_size = self.page_sizes.get(pdf_options.page_size, A4)
        
        if pdf_options.orientation == "landscape":
            page_size = (page_size[1], page_size[0])
        
        pdf = pdf_canvas.Canvas(pdf_buffer, pagesize=page_size)
        
        # 메타데이터 설정
        if pdf_options.metadata:
            metadata = pdf_options.metadata
            if metadata.title:
                pdf.setTitle(metadata.title)
            if metadata.author:
                pdf.setAuthor(metadata.author)
            if metadata.subject:
                pdf.setSubject(metadata.subject)
            if metadata.keywords:
                pdf.setKeywords(" ".join(metadata.keywords))
            pdf.setCreator(metadata.creator)
            pdf.setProducer(metadata.producer)
        
        # 이미지를 PDF에 추가
        image_obj = ImageReader(BytesIO(image_data))
        
        # 여백 적용
        margin = pdf_options.margin_mm * mm
        available_width = page_size[0] - 2 * margin
        available_height = page_size[1] - 2 * margin
        
        # 이미지 크기 조정 (비율 유지)
        img_width = image_metadata["width"]
        img_height = image_metadata["height"]
        
        scale_x = available_width / img_width
        scale_y = available_height / img_height
        scale = min(scale_x, scale_y)
        
        final_width = img_width * scale
        final_height = img_height * scale
        
        # 중앙 정렬
        x = margin + (available_width - final_width) / 2
        y = margin + (available_height - final_height) / 2
        
        pdf.drawImage(image_obj, x, y, final_width, final_height)
        
        # 페이지 번호 (옵션)
        if pdf_options.add_page_numbers:
            pdf.drawString(page_size[0] - margin - 50, margin, "1")
        
        pdf.save()
        pdf_buffer.seek(0)
        
        metadata = {
            "pages": 1,
            "page_size": pdf_options.page_size,
            "orientation": pdf_options.orientation,
            "size": len(pdf_buffer.getvalue())
        }
        
        return pdf_buffer.getvalue(), metadata
    
    async def create_multi_page_pdf(
        self,
        db: AsyncSession,
        canvas_ids: List[UUID],
        options: ExportOptions,
        pdf_options: PDFOptions,
        batch_options: BatchExportOptions
    ) -> Tuple[bytes, Dict[str, Any]]:
        """다중 Canvas를 하나의 PDF로 변환"""
        
        pdf_buffer = BytesIO()
        page_size = self.page_sizes.get(pdf_options.page_size, A4)
        
        if pdf_options.orientation == "landscape":
            page_size = (page_size[1], page_size[0])
        
        pdf = pdf_canvas.Canvas(pdf_buffer, pagesize=page_size)
        
        # 메타데이터 설정
        if pdf_options.metadata:
            metadata = pdf_options.metadata
            if metadata.title:
                pdf.setTitle(metadata.title)
            if metadata.author:
                pdf.setAuthor(metadata.author)
        
        renderer = CanvasRenderingEngine()
        page_count = 0
        
        # 여백 및 레이아웃 계산
        margin = pdf_options.margin_mm * mm
        available_width = page_size[0] - 2 * margin
        available_height = page_size[1] - 2 * margin
        
        images_per_page = pdf_options.images_per_page
        cols = int(images_per_page ** 0.5)
        rows = (images_per_page + cols - 1) // cols
        
        cell_width = available_width / cols
        cell_height = available_height / rows
        
        current_page_images = 0
        
        for i, canvas_id in enumerate(canvas_ids):
            try:
                # Canvas를 이미지로 렌더링
                image_data, image_metadata = await renderer.render_canvas_to_image(
                    db, canvas_id, options
                )
                
                if current_page_images == 0:
                    page_count += 1
                
                # 이미지 위치 계산
                col = current_page_images % cols
                row = current_page_images // cols
                
                x = margin + col * cell_width
                y = page_size[1] - margin - (row + 1) * cell_height
                
                # 이미지 크기 조정
                img_width = image_metadata["width"]
                img_height = image_metadata["height"]
                
                scale_x = (cell_width - 10) / img_width
                scale_y = (cell_height - 10) / img_height
                scale = min(scale_x, scale_y)
                
                final_width = img_width * scale
                final_height = img_height * scale
                
                # 셀 중앙에 배치
                x += (cell_width - final_width) / 2
                y += (cell_height - final_height) / 2
                
                # 이미지 추가
                image_obj = ImageReader(BytesIO(image_data))
                pdf.drawImage(image_obj, x, y, final_width, final_height)
                
                current_page_images += 1
                
                # 페이지가 꽉 찼거나 마지막 이미지면 다음 페이지
                if current_page_images >= images_per_page or i == len(canvas_ids) - 1:
                    # 페이지 번호
                    if pdf_options.add_page_numbers:
                        pdf.drawString(page_size[0] - margin - 50, margin, str(page_count))
                    
                    if i < len(canvas_ids) - 1:  # 마지막 페이지가 아니면
                        pdf.showPage()
                        current_page_images = 0
                
            except Exception as e:
                logger.error(f"Canvas {canvas_id} PDF 추가 실패: {e}")
                continue
        
        pdf.save()
        pdf_buffer.seek(0)
        
        metadata = {
            "pages": page_count,
            "canvases_count": len(canvas_ids),
            "images_per_page": images_per_page,
            "page_size": pdf_options.page_size,
            "orientation": pdf_options.orientation,
            "size": len(pdf_buffer.getvalue())
        }
        
        return pdf_buffer.getvalue(), metadata


class BatchExportEngine:
    """일괄 내보내기 엔진"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="batch_export_")
    
    async def create_batch_export(
        self,
        db: AsyncSession,
        canvas_ids: List[UUID],
        options: ExportOptions,
        batch_options: BatchExportOptions,
        format_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """일괄 내보내기 실행"""
        
        renderer = CanvasRenderingEngine()
        exported_files = []
        
        # ZIP 파일 생성
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            for i, canvas_id in enumerate(canvas_ids):
                try:
                    # 파일명 생성
                    filename = self._generate_filename(
                        batch_options.filename_pattern,
                        i + 1,
                        canvas_id,
                        options.format
                    )
                    
                    # Canvas 내보내기
                    if options.format in [ExportFormat.PNG, ExportFormat.JPEG, ExportFormat.WEBP]:
                        file_data, metadata = await renderer.render_canvas_to_image(
                            db, canvas_id, options, format_options
                        )
                    elif options.format == ExportFormat.SVG:
                        svg_content, metadata = await renderer.render_canvas_to_svg(
                            db, canvas_id, options, format_options
                        )
                        file_data = svg_content.encode('utf-8')
                    else:
                        continue  # PDF는 별도 처리
                    
                    # ZIP에 추가
                    zip_file.writestr(filename, file_data)
                    
                    exported_files.append({
                        "filename": filename,
                        "canvas_id": str(canvas_id),
                        "size": len(file_data),
                        "format": options.format.value,
                        "metadata": metadata
                    })
                    
                except Exception as e:
                    logger.error(f"Canvas {canvas_id} 내보내기 실패: {e}")
                    continue
            
            # Manifest 파일 생성
            if batch_options.create_manifest:
                manifest = {
                    "export_info": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "total_files": len(exported_files),
                        "format": options.format.value,
                        "options": options.dict()
                    },
                    "files": exported_files
                }
                
                manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False)
                zip_file.writestr("manifest.json", manifest_json)
        
        zip_buffer.seek(0)
        
        metadata = {
            "files_count": len(exported_files),
            "total_size": len(zip_buffer.getvalue()),
            "format": options.format.value,
            "has_manifest": batch_options.create_manifest
        }
        
        return zip_buffer.getvalue(), metadata
    
    def _generate_filename(self, pattern: str, index: int, canvas_id: UUID, format: ExportFormat) -> str:
        """파일명 생성"""
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        replacements = {
            "{index}": f"{index:03d}",
            "{timestamp}": timestamp,
            "{canvas_id}": str(canvas_id)[:8],
            "{format}": format.value
        }
        
        filename = pattern
        for placeholder, value in replacements.items():
            filename = filename.replace(placeholder, value)
        
        # 확장자 추가
        extension = SUPPORTED_FORMATS[format]["extension"]
        if not filename.endswith(extension):
            filename += extension
        
        return filename
    
    def __del__(self):
        """임시 디렉토리 정리"""
        try:
            import shutil
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except:
            pass