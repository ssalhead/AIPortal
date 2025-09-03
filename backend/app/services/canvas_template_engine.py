# Canvas 템플릿 엔진 v1.0
# 업계별/용도별 전문 레이아웃 템플릿 시스템

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
import json

from app.models.canvas_models import (
    KonvaNodeData, 
    KonvaLayerData, 
    KonvaStageData,
    KonvaNodeType,
    CanvasData
)

logger = logging.getLogger(__name__)

class TemplateCategory(str, Enum):
    """템플릿 카테고리"""
    POSTER = "poster"                    # 포스터/전단지
    SOCIAL_MEDIA = "social_media"        # 소셜 미디어
    PRESENTATION = "presentation"        # 프레젠테이션
    BUSINESS_CARD = "business_card"      # 명함/카드
    WEBSITE = "website"                  # 웹사이트
    DOCUMENT = "document"                # 문서/리포트
    INFOGRAPHIC = "infographic"          # 인포그래픽
    MARKETING = "marketing"              # 마케팅 자료

class IndustryType(str, Enum):
    """산업 분야"""
    TECHNOLOGY = "technology"            # IT/기술
    HEALTHCARE = "healthcare"            # 의료/헬스케어
    EDUCATION = "education"              # 교육
    FINANCE = "finance"                  # 금융
    RETAIL = "retail"                   # 소매/유통
    RESTAURANT = "restaurant"            # 식음료
    REAL_ESTATE = "real_estate"         # 부동산
    CREATIVE = "creative"               # 크리에이티브
    GENERAL = "general"                 # 일반

class LayoutStyle(str, Enum):
    """레이아웃 스타일"""
    MODERN = "modern"                   # 모던/미니멀
    CLASSIC = "classic"                 # 클래식/전통적
    PLAYFUL = "playful"                # 활동적/재미있는
    PROFESSIONAL = "professional"       # 전문적/비즈니스
    CREATIVE = "creative"              # 크리에이티브/예술적
    MINIMAL = "minimal"                # 미니멀/심플

class CanvasTemplateEngine:
    """Canvas 템플릿 엔진"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
        self.color_palettes = self._initialize_color_palettes()
        self.typography_sets = self._initialize_typography_sets()

    def _initialize_templates(self) -> Dict[str, Any]:
        """기본 템플릿 초기화"""
        return {
            # 소셜 미디어 포스트 템플릿들
            "instagram_post_1": {
                "name": "Instagram 정사각 포스트 - 모던",
                "category": TemplateCategory.SOCIAL_MEDIA,
                "industry": IndustryType.GENERAL,
                "style": LayoutStyle.MODERN,
                "canvas_size": {"width": 1080, "height": 1080},
                "elements": [
                    {
                        "type": "background",
                        "node_type": "rect",
                        "position": {"x": 0, "y": 0},
                        "size": {"width": 1080, "height": 1080},
                        "style": {"fill": "#f8f9fa"},
                        "z_index": 0
                    },
                    {
                        "type": "main_image",
                        "node_type": "image",
                        "position": {"x": 90, "y": 90},
                        "size": {"width": 900, "height": 600},
                        "z_index": 1
                    },
                    {
                        "type": "title",
                        "node_type": "text",
                        "position": {"x": 90, "y": 720},
                        "size": {"width": 900, "height": 80},
                        "style": {
                            "fontSize": 48,
                            "fontFamily": "Inter",
                            "fontStyle": "bold",
                            "fill": "#212529",
                            "align": "center"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "subtitle",
                        "node_type": "text",
                        "position": {"x": 90, "y": 810},
                        "size": {"width": 900, "height": 60},
                        "style": {
                            "fontSize": 24,
                            "fontFamily": "Inter",
                            "fill": "#6c757d",
                            "align": "center"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "logo",
                        "node_type": "image",
                        "position": {"x": 90, "y": 900},
                        "size": {"width": 120, "height": 120},
                        "z_index": 3
                    }
                ]
            },
            
            # 포스터 템플릿들
            "event_poster_1": {
                "name": "이벤트 포스터 - 세로형",
                "category": TemplateCategory.POSTER,
                "industry": IndustryType.GENERAL,
                "style": LayoutStyle.MODERN,
                "canvas_size": {"width": 1080, "height": 1920},
                "elements": [
                    {
                        "type": "background",
                        "node_type": "rect",
                        "position": {"x": 0, "y": 0},
                        "size": {"width": 1080, "height": 1920},
                        "style": {"fill": "#1a1a2e"},
                        "z_index": 0
                    },
                    {
                        "type": "header_section",
                        "node_type": "rect",
                        "position": {"x": 0, "y": 0},
                        "size": {"width": 1080, "height": 400},
                        "style": {"fill": "#16213e"},
                        "z_index": 1
                    },
                    {
                        "type": "event_title",
                        "node_type": "text",
                        "position": {"x": 80, "y": 100},
                        "size": {"width": 920, "height": 120},
                        "style": {
                            "fontSize": 72,
                            "fontFamily": "Inter",
                            "fontStyle": "bold",
                            "fill": "#ffffff",
                            "align": "center"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "event_date",
                        "node_type": "text",
                        "position": {"x": 80, "y": 250},
                        "size": {"width": 920, "height": 80},
                        "style": {
                            "fontSize": 36,
                            "fontFamily": "Inter",
                            "fill": "#e74c3c",
                            "align": "center"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "main_image",
                        "node_type": "image",
                        "position": {"x": 140, "y": 480},
                        "size": {"width": 800, "height": 800},
                        "z_index": 1
                    },
                    {
                        "type": "description",
                        "node_type": "text",
                        "position": {"x": 80, "y": 1350},
                        "size": {"width": 920, "height": 200},
                        "style": {
                            "fontSize": 28,
                            "fontFamily": "Inter",
                            "fill": "#ffffff",
                            "align": "center"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "call_to_action",
                        "node_type": "rect",
                        "position": {"x": 240, "y": 1600},
                        "size": {"width": 600, "height": 100},
                        "style": {
                            "fill": "#e74c3c",
                            "cornerRadius": 50
                        },
                        "z_index": 2
                    },
                    {
                        "type": "cta_text",
                        "node_type": "text",
                        "position": {"x": 240, "y": 1620},
                        "size": {"width": 600, "height": 60},
                        "style": {
                            "fontSize": 32,
                            "fontFamily": "Inter",
                            "fontStyle": "bold",
                            "fill": "#ffffff",
                            "align": "center"
                        },
                        "z_index": 3
                    }
                ]
            },
            
            # 명함 템플릿들
            "business_card_1": {
                "name": "비즈니스 명함 - 모던",
                "category": TemplateCategory.BUSINESS_CARD,
                "industry": IndustryType.GENERAL,
                "style": LayoutStyle.MODERN,
                "canvas_size": {"width": 1050, "height": 600},  # 105mm x 60mm (10px per mm)
                "elements": [
                    {
                        "type": "background",
                        "node_type": "rect",
                        "position": {"x": 0, "y": 0},
                        "size": {"width": 1050, "height": 600},
                        "style": {"fill": "#ffffff"},
                        "z_index": 0
                    },
                    {
                        "type": "accent_bar",
                        "node_type": "rect",
                        "position": {"x": 0, "y": 0},
                        "size": {"width": 10, "height": 600},
                        "style": {"fill": "#3498db"},
                        "z_index": 1
                    },
                    {
                        "type": "company_name",
                        "node_type": "text",
                        "position": {"x": 50, "y": 80},
                        "size": {"width": 900, "height": 60},
                        "style": {
                            "fontSize": 32,
                            "fontFamily": "Inter",
                            "fontStyle": "bold",
                            "fill": "#2c3e50",
                            "align": "left"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "person_name",
                        "node_type": "text",
                        "position": {"x": 50, "y": 200},
                        "size": {"width": 600, "height": 80},
                        "style": {
                            "fontSize": 48,
                            "fontFamily": "Inter",
                            "fontStyle": "bold",
                            "fill": "#2c3e50",
                            "align": "left"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "job_title",
                        "node_type": "text",
                        "position": {"x": 50, "y": 300},
                        "size": {"width": 600, "height": 40},
                        "style": {
                            "fontSize": 24,
                            "fontFamily": "Inter",
                            "fill": "#7f8c8d",
                            "align": "left"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "contact_info",
                        "node_type": "text",
                        "position": {"x": 50, "y": 400},
                        "size": {"width": 600, "height": 120},
                        "style": {
                            "fontSize": 18,
                            "fontFamily": "Inter",
                            "fill": "#34495e",
                            "align": "left"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "logo",
                        "node_type": "image",
                        "position": {"x": 750, "y": 200},
                        "size": {"width": 200, "height": 200},
                        "z_index": 1
                    }
                ]
            },
            
            # 프레젠테이션 템플릿들
            "presentation_title_slide": {
                "name": "프레젠테이션 제목 슬라이드",
                "category": TemplateCategory.PRESENTATION,
                "industry": IndustryType.TECHNOLOGY,
                "style": LayoutStyle.PROFESSIONAL,
                "canvas_size": {"width": 1920, "height": 1080},
                "elements": [
                    {
                        "type": "background",
                        "node_type": "rect",
                        "position": {"x": 0, "y": 0},
                        "size": {"width": 1920, "height": 1080},
                        "style": {
                            "fill": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
                        },
                        "z_index": 0
                    },
                    {
                        "type": "main_title",
                        "node_type": "text",
                        "position": {"x": 200, "y": 350},
                        "size": {"width": 1520, "height": 150},
                        "style": {
                            "fontSize": 84,
                            "fontFamily": "Inter",
                            "fontStyle": "bold",
                            "fill": "#ffffff",
                            "align": "center"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "subtitle",
                        "node_type": "text",
                        "position": {"x": 200, "y": 550},
                        "size": {"width": 1520, "height": 100},
                        "style": {
                            "fontSize": 36,
                            "fontFamily": "Inter",
                            "fill": "#e8eaf6",
                            "align": "center"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "author_info",
                        "node_type": "text",
                        "position": {"x": 200, "y": 750},
                        "size": {"width": 1520, "height": 80},
                        "style": {
                            "fontSize": 28,
                            "fontFamily": "Inter",
                            "fill": "#b39ddb",
                            "align": "center"
                        },
                        "z_index": 2
                    },
                    {
                        "type": "decorative_shape",
                        "node_type": "circle",
                        "position": {"x": 1600, "y": 100},
                        "size": {"width": 200, "height": 200},
                        "style": {
                            "fill": "rgba(255, 255, 255, 0.1)"
                        },
                        "z_index": 1
                    }
                ]
            }
        }

    def _initialize_color_palettes(self) -> Dict[str, Dict[str, Any]]:
        """색상 팔레트 초기화"""
        return {
            "modern_blue": {
                "name": "Modern Blue",
                "primary": "#3498db",
                "secondary": "#2980b9",
                "accent": "#e74c3c",
                "background": "#ecf0f1",
                "text": "#2c3e50",
                "text_light": "#7f8c8d"
            },
            "warm_sunset": {
                "name": "Warm Sunset",
                "primary": "#ff6b6b",
                "secondary": "#ee5a24",
                "accent": "#feca57",
                "background": "#fff5f5",
                "text": "#2d3436",
                "text_light": "#636e72"
            },
            "forest_green": {
                "name": "Forest Green",
                "primary": "#27ae60",
                "secondary": "#229954",
                "accent": "#f39c12",
                "background": "#f8fff8",
                "text": "#2c3e50",
                "text_light": "#7f8c8d"
            },
            "corporate_gray": {
                "name": "Corporate Gray",
                "primary": "#34495e",
                "secondary": "#2c3e50",
                "accent": "#3498db",
                "background": "#ffffff",
                "text": "#2c3e50",
                "text_light": "#7f8c8d"
            },
            "vibrant_purple": {
                "name": "Vibrant Purple",
                "primary": "#9b59b6",
                "secondary": "#8e44ad",
                "accent": "#e67e22",
                "background": "#faf5ff",
                "text": "#2c3e50",
                "text_light": "#7f8c8d"
            }
        }

    def _initialize_typography_sets(self) -> Dict[str, Dict[str, Any]]:
        """타이포그래피 세트 초기화"""
        return {
            "modern_clean": {
                "name": "Modern Clean",
                "heading": {
                    "fontFamily": "Inter",
                    "fontStyle": "bold",
                    "fontSize_large": 72,
                    "fontSize_medium": 48,
                    "fontSize_small": 36
                },
                "body": {
                    "fontFamily": "Inter",
                    "fontStyle": "normal",
                    "fontSize_large": 24,
                    "fontSize_medium": 18,
                    "fontSize_small": 14
                },
                "accent": {
                    "fontFamily": "Inter",
                    "fontStyle": "italic",
                    "fontSize_large": 28,
                    "fontSize_medium": 20,
                    "fontSize_small": 16
                }
            },
            "classic_serif": {
                "name": "Classic Serif",
                "heading": {
                    "fontFamily": "Playfair Display",
                    "fontStyle": "bold",
                    "fontSize_large": 76,
                    "fontSize_medium": 52,
                    "fontSize_small": 38
                },
                "body": {
                    "fontFamily": "Source Sans Pro",
                    "fontStyle": "normal",
                    "fontSize_large": 22,
                    "fontSize_medium": 17,
                    "fontSize_small": 13
                },
                "accent": {
                    "fontFamily": "Playfair Display",
                    "fontStyle": "italic",
                    "fontSize_large": 26,
                    "fontSize_medium": 19,
                    "fontSize_small": 15
                }
            },
            "tech_minimal": {
                "name": "Tech Minimal",
                "heading": {
                    "fontFamily": "Roboto",
                    "fontStyle": "300",
                    "fontSize_large": 68,
                    "fontSize_medium": 44,
                    "fontSize_small": 32
                },
                "body": {
                    "fontFamily": "Roboto",
                    "fontStyle": "normal",
                    "fontSize_large": 20,
                    "fontSize_medium": 16,
                    "fontSize_small": 12
                },
                "accent": {
                    "fontFamily": "Roboto Mono",
                    "fontStyle": "normal",
                    "fontSize_large": 24,
                    "fontSize_medium": 18,
                    "fontSize_small": 14
                }
            }
        }

    async def get_recommended_templates(
        self, 
        category: Optional[TemplateCategory] = None,
        industry: Optional[IndustryType] = None,
        style: Optional[LayoutStyle] = None,
        canvas_size: Optional[Dict[str, int]] = None
    ) -> List[Dict[str, Any]]:
        """추천 템플릿 검색"""
        try:
            recommendations = []
            
            for template_id, template in self.templates.items():
                match_score = 0
                
                # 카테고리 매치
                if category and template["category"] == category:
                    match_score += 3
                
                # 산업 매치
                if industry and template["industry"] == industry:
                    match_score += 2
                elif industry and template["industry"] == IndustryType.GENERAL:
                    match_score += 1
                
                # 스타일 매치
                if style and template["style"] == style:
                    match_score += 2
                
                # 캔버스 크기 매치 (비슷한 비율)
                if canvas_size:
                    template_ratio = template["canvas_size"]["width"] / template["canvas_size"]["height"]
                    requested_ratio = canvas_size["width"] / canvas_size["height"]
                    
                    ratio_diff = abs(template_ratio - requested_ratio)
                    if ratio_diff < 0.1:
                        match_score += 2
                    elif ratio_diff < 0.3:
                        match_score += 1
                
                if match_score > 0:
                    recommendations.append({
                        "template_id": template_id,
                        "template": template,
                        "match_score": match_score
                    })
            
            # 매치 점수순으로 정렬
            recommendations.sort(key=lambda x: x["match_score"], reverse=True)
            
            return recommendations[:10]  # 상위 10개 반환
            
        except Exception as e:
            logger.error(f"템플릿 추천 실패: {str(e)}")
            return []

    async def apply_template(
        self, 
        template_id: str, 
        content_data: Dict[str, Any],
        customizations: Optional[Dict[str, Any]] = None
    ) -> CanvasData:
        """템플릿 적용"""
        try:
            if template_id not in self.templates:
                raise ValueError(f"템플릿을 찾을 수 없습니다: {template_id}")
            
            template = self.templates[template_id]
            
            # 기본 캔버스 데이터 생성
            canvas_data = CanvasData(
                workspace_id=content_data.get("workspace_id"),
                name=f"{template['name']} - {datetime.now().strftime('%Y%m%d_%H%M')}",
                description=f"템플릿 기반 자동 생성: {template['name']}"
            )
            
            # Stage 설정
            canvas_size = template["canvas_size"]
            canvas_data.stage = KonvaStageData(
                width=canvas_size["width"],
                height=canvas_size["height"]
            )
            
            # 레이어 생성
            main_layer = KonvaLayerData(
                id="main_layer",
                name="Main Layer",
                layer_index=0
            )
            
            # 템플릿 요소들을 Konva 노드로 변환
            for i, element_template in enumerate(template["elements"]):
                node = await self._create_node_from_template(
                    element_template, 
                    content_data, 
                    customizations,
                    i
                )
                main_layer.nodes.append(node)
            
            canvas_data.stage.layers = [main_layer]
            
            return canvas_data
            
        except Exception as e:
            logger.error(f"템플릿 적용 실패: {str(e)}")
            raise

    async def _create_node_from_template(
        self, 
        element_template: Dict[str, Any], 
        content_data: Dict[str, Any],
        customizations: Optional[Dict[str, Any]],
        index: int
    ) -> KonvaNodeData:
        """템플릿 요소를 Konva 노드로 변환"""
        
        element_type = element_template["type"]
        node_type = element_template["node_type"]
        position = element_template["position"]
        size = element_template.get("size", {})
        style = element_template.get("style", {})
        z_index = element_template.get("z_index", index)
        
        # 콘텐츠 데이터에서 해당 요소의 내용 찾기
        content_value = content_data.get(element_type, "")
        
        # 커스터마이제이션 적용
        if customizations:
            # 색상 팔레트 적용
            if "color_palette" in customizations:
                palette = self.color_palettes.get(customizations["color_palette"])
                if palette:
                    style = self._apply_color_palette(style, palette, element_type)
            
            # 타이포그래피 적용
            if "typography_set" in customizations and node_type == "text":
                typography = self.typography_sets.get(customizations["typography_set"])
                if typography:
                    style = self._apply_typography(style, typography, element_type)
        
        # Konva 속성 구성
        konva_attrs = {}
        
        if node_type == "text":
            konva_attrs = {
                **style,
                "text": content_value or f"[{element_type.replace('_', ' ').title()}]"
            }
        elif node_type == "rect":
            konva_attrs = {
                **style
            }
        elif node_type == "circle":
            konva_attrs = {
                **style
            }
        elif node_type == "image":
            konva_attrs = {
                "image": content_value or "/api/placeholder/image"
            }
        
        # KonvaNodeData 생성
        node = KonvaNodeData(
            id=f"template_node_{index}_{element_type}",
            node_type=getattr(KonvaNodeType, node_type.upper(), KonvaNodeType.RECT),
            class_name=node_type.capitalize(),
            x=float(position["x"]),
            y=float(position["y"]),
            width=float(size.get("width", 100)),
            height=float(size.get("height", 100)),
            z_index=z_index,
            konva_attrs=konva_attrs
        )
        
        return node

    def _apply_color_palette(
        self, 
        style: Dict[str, Any], 
        palette: Dict[str, str], 
        element_type: str
    ) -> Dict[str, Any]:
        """색상 팔레트 적용"""
        new_style = style.copy()
        
        # 요소 타입에 따른 색상 매핑
        color_mappings = {
            "background": "background",
            "title": "text",
            "heading": "text",
            "subtitle": "text_light",
            "body_text": "text",
            "accent_bar": "primary",
            "call_to_action": "primary",
            "cta_text": "background",
            "decorative_shape": "accent"
        }
        
        color_key = color_mappings.get(element_type, "text")
        
        if "fill" in new_style:
            new_style["fill"] = palette.get(color_key, new_style["fill"])
        
        if "stroke" in new_style:
            new_style["stroke"] = palette.get("accent", new_style["stroke"])
        
        return new_style

    def _apply_typography(
        self, 
        style: Dict[str, Any], 
        typography: Dict[str, Any], 
        element_type: str
    ) -> Dict[str, Any]:
        """타이포그래피 적용"""
        new_style = style.copy()
        
        # 요소 타입에 따른 타이포그래피 매핑
        type_mappings = {
            "title": "heading",
            "main_title": "heading",
            "event_title": "heading",
            "company_name": "heading",
            "person_name": "heading",
            "subtitle": "body",
            "description": "body",
            "job_title": "accent",
            "contact_info": "body",
            "author_info": "accent"
        }
        
        typo_category = type_mappings.get(element_type, "body")
        typo_settings = typography.get(typo_category, {})
        
        # 폰트 설정 적용
        if "fontFamily" in typo_settings:
            new_style["fontFamily"] = typo_settings["fontFamily"]
        
        if "fontStyle" in typo_settings:
            new_style["fontStyle"] = typo_settings["fontStyle"]
        
        # 폰트 크기는 기존 크기를 기준으로 적절히 매핑
        current_font_size = new_style.get("fontSize", 16)
        if current_font_size >= 60:
            size_key = "fontSize_large"
        elif current_font_size >= 30:
            size_key = "fontSize_medium"
        else:
            size_key = "fontSize_small"
        
        if size_key in typo_settings:
            new_style["fontSize"] = typo_settings[size_key]
        
        return new_style

    async def generate_custom_template(
        self, 
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AI 기반 커스텀 템플릿 생성"""
        try:
            # LLM을 활용한 템플릿 생성 (추후 구현)
            logger.info(f"커스텀 템플릿 생성 요청: {requirements}")
            
            # 현재는 기본 템플릿 반환
            return self.templates["instagram_post_1"]
            
        except Exception as e:
            logger.error(f"커스텀 템플릿 생성 실패: {str(e)}")
            return self.templates["instagram_post_1"]

    def get_template_preview(self, template_id: str) -> Dict[str, Any]:
        """템플릿 미리보기 데이터"""
        if template_id not in self.templates:
            return {}
        
        template = self.templates[template_id]
        
        return {
            "template_id": template_id,
            "name": template["name"],
            "category": template["category"],
            "industry": template["industry"],
            "style": template["style"],
            "canvas_size": template["canvas_size"],
            "preview_elements": [
                {
                    "type": element["type"],
                    "position": element["position"],
                    "size": element.get("size", {}),
                    "preview_content": self._get_preview_content(element["type"])
                }
                for element in template["elements"]
            ]
        }

    def _get_preview_content(self, element_type: str) -> str:
        """미리보기용 콘텐츠 생성"""
        preview_contents = {
            "title": "제목이 들어갈 자리",
            "main_title": "메인 제목",
            "event_title": "이벤트명",
            "subtitle": "부제목이 들어갈 자리",
            "description": "설명 텍스트가 들어갈 자리입니다.",
            "company_name": "회사명",
            "person_name": "홍길동",
            "job_title": "직책명",
            "contact_info": "연락처 정보",
            "event_date": "2024년 12월 25일",
            "cta_text": "지금 신청하기",
            "author_info": "작성자 정보"
        }
        
        return preview_contents.get(element_type, "콘텐츠")

# 전역 인스턴스
template_engine = CanvasTemplateEngine()

# 공개 함수들
async def get_recommended_templates(
    category: Optional[TemplateCategory] = None,
    industry: Optional[IndustryType] = None,
    style: Optional[LayoutStyle] = None,
    canvas_size: Optional[Dict[str, int]] = None
) -> List[Dict[str, Any]]:
    """추천 템플릿 검색"""
    return await template_engine.get_recommended_templates(category, industry, style, canvas_size)

async def apply_template(
    template_id: str, 
    content_data: Dict[str, Any],
    customizations: Optional[Dict[str, Any]] = None
) -> CanvasData:
    """템플릿 적용"""
    return await template_engine.apply_template(template_id, content_data, customizations)

def get_available_templates() -> List[Dict[str, Any]]:
    """사용 가능한 모든 템플릿 목록"""
    return [
        {
            "template_id": template_id,
            **template_engine.get_template_preview(template_id)
        }
        for template_id in template_engine.templates.keys()
    ]

def get_color_palettes() -> Dict[str, Dict[str, Any]]:
    """사용 가능한 색상 팔레트"""
    return template_engine.color_palettes

def get_typography_sets() -> Dict[str, Dict[str, Any]]:
    """사용 가능한 타이포그래피 세트"""
    return template_engine.typography_sets

async def generate_custom_template(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """AI 기반 커스텀 템플릿 생성"""
    return await template_engine.generate_custom_template(requirements)