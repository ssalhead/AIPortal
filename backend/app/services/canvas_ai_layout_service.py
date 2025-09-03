# Canvas AI 레이아웃 엔진 v1.0
# 지능형 요소 배치 및 정렬 시스템

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
import json
import math
import uuid

from app.agents.llm_router import llm_router
from app.models.canvas_models import (
    KonvaNodeData, 
    KonvaLayerData, 
    KonvaStageData,
    KonvaNodeType,
    CanvasData
)

logger = logging.getLogger(__name__)

class LayoutTemplate(str, Enum):
    """레이아웃 템플릿 유형"""
    POSTER = "poster"                    # 포스터/전단지
    SOCIAL_POST = "social_post"          # 소셜 미디어 포스트
    PRESENTATION = "presentation"        # 프레젠테이션 슬라이드
    WEBSITE_SECTION = "website_section"  # 웹사이트 섹션
    BUSINESS_CARD = "business_card"      # 명함/카드
    FREEFORM = "freeform"               # 자유형 레이아웃
    GRID_SYSTEM = "grid_system"         # 그리드 시스템 기반

class LayoutPrinciple(str, Enum):
    """디자인 원칙"""
    GOLDEN_RATIO = "golden_ratio"        # 황금비율
    RULE_OF_THIRDS = "rule_of_thirds"    # 삼분할법
    GRID_ALIGNMENT = "grid_alignment"    # 그리드 정렬
    VISUAL_HIERARCHY = "visual_hierarchy" # 시각적 계층 구조
    COLOR_HARMONY = "color_harmony"      # 색상 조화
    PROXIMITY_GROUPING = "proximity_grouping" # 근접성 그룹핑

class ElementImportance(str, Enum):
    """요소 중요도"""
    PRIMARY = "primary"      # 주요 요소 (제목, 로고)
    SECONDARY = "secondary"  # 보조 요소 (부제목, 중요 이미지)
    TERTIARY = "tertiary"    # 3차 요소 (본문, 부가 정보)
    DECORATIVE = "decorative" # 장식 요소 (배경, 아이콘)

class AILayoutEngine:
    """AI 기반 레이아웃 엔진"""
    
    def __init__(self):
        self.golden_ratio = 1.618
        self.rule_of_thirds = [1/3, 2/3]
        
        # 디자인 원칙별 가중치
        self.principle_weights = {
            LayoutPrinciple.GOLDEN_RATIO: 0.25,
            LayoutPrinciple.RULE_OF_THIRDS: 0.20,
            LayoutPrinciple.GRID_ALIGNMENT: 0.20,
            LayoutPrinciple.VISUAL_HIERARCHY: 0.15,
            LayoutPrinciple.COLOR_HARMONY: 0.10,
            LayoutPrinciple.PROXIMITY_GROUPING: 0.10
        }

    async def analyze_canvas_elements(self, canvas_data: CanvasData) -> Dict[str, Any]:
        """Canvas 요소 분석"""
        try:
            elements = []
            
            # 모든 노드 추출 및 분석
            for layer in canvas_data.stage.layers:
                for node in layer.nodes:
                    element_analysis = await self._analyze_single_element(node)
                    elements.append(element_analysis)
            
            # 전체 구성 분석
            composition_analysis = await self._analyze_composition(elements, canvas_data.stage)
            
            # LLM 기반 컨텍스트 분석
            llm_analysis = await self._get_llm_layout_analysis(elements, composition_analysis)
            
            return {
                "elements": elements,
                "composition": composition_analysis,
                "llm_insights": llm_analysis,
                "optimization_suggestions": await self._generate_optimization_suggestions(elements, composition_analysis, llm_analysis),
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Canvas 요소 분석 실패: {str(e)}")
            raise

    async def _analyze_single_element(self, node: KonvaNodeData) -> Dict[str, Any]:
        """단일 요소 분석"""
        element_type = self._classify_element_type(node)
        importance = self._calculate_element_importance(node)
        visual_properties = self._extract_visual_properties(node)
        spatial_properties = self._extract_spatial_properties(node)
        
        return {
            "id": node.id,
            "node_type": node.node_type,
            "element_type": element_type,
            "importance": importance,
            "visual_properties": visual_properties,
            "spatial_properties": spatial_properties,
            "relationships": await self._find_element_relationships(node)
        }

    def _classify_element_type(self, node: KonvaNodeData) -> str:
        """요소 타입 분류"""
        node_type = node.node_type.lower()
        konva_attrs = node.konva_attrs or {}
        
        if node_type == "text":
            font_size = konva_attrs.get("fontSize", 14)
            if font_size >= 24:
                return "heading"
            elif font_size >= 18:
                return "subheading"
            else:
                return "body_text"
        
        elif node_type == "image":
            return "image"
        
        elif node_type in ["rect", "circle", "path"]:
            # 색상과 크기로 판단
            if konva_attrs.get("fill") and not konva_attrs.get("stroke"):
                return "background_shape"
            else:
                return "decorative_shape"
        
        elif node_type == "line":
            return "divider"
        
        else:
            return "unknown"

    def _calculate_element_importance(self, node: KonvaNodeData) -> ElementImportance:
        """요소 중요도 계산"""
        importance_score = 0
        konva_attrs = node.konva_attrs or {}
        
        # 크기 기준 중요도
        if node.width and node.height:
            area = node.width * node.height
            if area > 50000:  # 큰 요소
                importance_score += 3
            elif area > 10000:  # 중간 요소
                importance_score += 2
            else:  # 작은 요소
                importance_score += 1
        
        # 텍스트 크기 기준
        if node.node_type == "text":
            font_size = konva_attrs.get("fontSize", 14)
            if font_size >= 24:
                importance_score += 3
            elif font_size >= 18:
                importance_score += 2
        
        # 색상 대비 기준
        if konva_attrs.get("fill"):
            # 진한 색상이나 밝은 색상은 중요도 증가
            importance_score += 1
        
        # z-index 기준
        z_index = node.z_index or 0
        if z_index > 10:
            importance_score += 2
        elif z_index > 5:
            importance_score += 1
        
        # 중요도 매핑
        if importance_score >= 7:
            return ElementImportance.PRIMARY
        elif importance_score >= 4:
            return ElementImportance.SECONDARY
        elif importance_score >= 2:
            return ElementImportance.TERTIARY
        else:
            return ElementImportance.DECORATIVE

    def _extract_visual_properties(self, node: KonvaNodeData) -> Dict[str, Any]:
        """시각적 속성 추출"""
        konva_attrs = node.konva_attrs or {}
        
        return {
            "color": {
                "fill": konva_attrs.get("fill"),
                "stroke": konva_attrs.get("stroke"),
                "stroke_width": konva_attrs.get("strokeWidth", 0)
            },
            "typography": {
                "font_family": konva_attrs.get("fontFamily"),
                "font_size": konva_attrs.get("fontSize"),
                "font_style": konva_attrs.get("fontStyle"),
                "text_align": konva_attrs.get("align")
            },
            "effects": {
                "opacity": node.opacity,
                "shadow": konva_attrs.get("shadowEnabled", False),
                "blur": konva_attrs.get("blur", 0)
            }
        }

    def _extract_spatial_properties(self, node: KonvaNodeData) -> Dict[str, Any]:
        """공간적 속성 추출"""
        return {
            "position": {"x": node.x, "y": node.y},
            "size": {"width": node.width, "height": node.height},
            "transform": {
                "scale_x": node.scale_x,
                "scale_y": node.scale_y,
                "rotation": node.rotation,
                "skew_x": node.skew_x,
                "skew_y": node.skew_y
            },
            "bounds": self._calculate_element_bounds(node),
            "center": self._calculate_element_center(node)
        }

    def _calculate_element_bounds(self, node: KonvaNodeData) -> Dict[str, float]:
        """요소 경계 계산"""
        if node.width and node.height:
            return {
                "left": node.x,
                "top": node.y,
                "right": node.x + node.width * node.scale_x,
                "bottom": node.y + node.height * node.scale_y
            }
        return {"left": node.x, "top": node.y, "right": node.x, "bottom": node.y}

    def _calculate_element_center(self, node: KonvaNodeData) -> Dict[str, float]:
        """요소 중심점 계산"""
        bounds = self._calculate_element_bounds(node)
        return {
            "x": (bounds["left"] + bounds["right"]) / 2,
            "y": (bounds["top"] + bounds["bottom"]) / 2
        }

    async def _find_element_relationships(self, node: KonvaNodeData) -> Dict[str, Any]:
        """요소 간 관계 분석"""
        # 현재는 기본적인 관계만 분석, 추후 확장 가능
        return {
            "parent_id": node.parent_id,
            "layer_index": node.layer_index,
            "z_index": node.z_index,
            "is_grouped": node.parent_id is not None
        }

    async def _analyze_composition(self, elements: List[Dict[str, Any]], stage: KonvaStageData) -> Dict[str, Any]:
        """전체 구성 분석"""
        try:
            # 요소들의 분포 분석
            distribution = self._analyze_element_distribution(elements, stage)
            
            # 그리드 정렬 분석
            grid_analysis = self._analyze_grid_alignment(elements, stage)
            
            # 시각적 계층 구조 분석
            hierarchy_analysis = self._analyze_visual_hierarchy(elements)
            
            # 색상 조화 분석
            color_analysis = self._analyze_color_harmony(elements)
            
            # 여백 및 밀도 분석
            spacing_analysis = self._analyze_spacing_density(elements, stage)
            
            return {
                "distribution": distribution,
                "grid_alignment": grid_analysis,
                "visual_hierarchy": hierarchy_analysis,
                "color_harmony": color_analysis,
                "spacing_density": spacing_analysis,
                "design_principles_score": self._calculate_design_principles_score(elements, stage)
            }
            
        except Exception as e:
            logger.error(f"구성 분석 실패: {str(e)}")
            return {}

    def _analyze_element_distribution(self, elements: List[Dict[str, Any]], stage: KonvaStageData) -> Dict[str, Any]:
        """요소 분포 분석"""
        if not elements:
            return {"balance": "empty", "coverage": 0}
        
        # 무게중심 계산
        total_weight = 0
        weighted_x = 0
        weighted_y = 0
        
        for element in elements:
            spatial = element.get("spatial_properties", {})
            center = spatial.get("center", {"x": 0, "y": 0})
            size = spatial.get("size", {"width": 0, "height": 0})
            
            # 요소의 "무게" (크기 * 중요도)
            importance_weight = {"primary": 3, "secondary": 2, "tertiary": 1, "decorative": 0.5}
            weight = (size.get("width", 0) * size.get("height", 0)) * importance_weight.get(element.get("importance", "decorative").value, 1)
            
            total_weight += weight
            weighted_x += center["x"] * weight
            weighted_y += center["y"] * weight
        
        if total_weight > 0:
            center_of_mass = {
                "x": weighted_x / total_weight,
                "y": weighted_y / total_weight
            }
        else:
            center_of_mass = {"x": stage.width / 2, "y": stage.height / 2}
        
        # 캔버스 중심과의 거리로 균형 판단
        canvas_center = {"x": stage.width / 2, "y": stage.height / 2}
        distance_from_center = math.sqrt(
            (center_of_mass["x"] - canvas_center["x"]) ** 2 +
            (center_of_mass["y"] - canvas_center["y"]) ** 2
        )
        
        # 정규화 (캔버스 대각선 길이로 나눔)
        diagonal_length = math.sqrt(stage.width ** 2 + stage.height ** 2)
        normalized_distance = distance_from_center / diagonal_length
        
        balance_score = 1 - normalized_distance  # 0~1 스케일
        
        return {
            "center_of_mass": center_of_mass,
            "balance_score": balance_score,
            "balance": "balanced" if balance_score > 0.8 else "unbalanced" if balance_score < 0.4 else "moderate"
        }

    def _analyze_grid_alignment(self, elements: List[Dict[str, Any]], stage: KonvaStageData) -> Dict[str, Any]:
        """그리드 정렬 분석"""
        if not elements:
            return {"aligned": False, "score": 0}
        
        # 요소들의 x, y 좌표 수집
        x_positions = []
        y_positions = []
        
        for element in elements:
            spatial = element.get("spatial_properties", {})
            pos = spatial.get("position", {"x": 0, "y": 0})
            bounds = spatial.get("bounds", {})
            
            x_positions.extend([pos["x"], bounds.get("right", pos["x"])])
            y_positions.extend([pos["y"], bounds.get("bottom", pos["y"])])
        
        # 정렬 점수 계산
        x_alignment_score = self._calculate_alignment_score(x_positions, stage.width)
        y_alignment_score = self._calculate_alignment_score(y_positions, stage.height)
        
        overall_score = (x_alignment_score + y_alignment_score) / 2
        
        return {
            "aligned": overall_score > 0.7,
            "x_alignment_score": x_alignment_score,
            "y_alignment_score": y_alignment_score,
            "overall_score": overall_score
        }

    def _calculate_alignment_score(self, positions: List[float], canvas_dimension: float) -> float:
        """정렬 점수 계산"""
        if not positions:
            return 0
        
        # 위치들을 정렬
        sorted_positions = sorted(set(positions))
        
        if len(sorted_positions) < 2:
            return 1.0  # 요소가 하나뿐이면 완전 정렬
        
        # 등간격 가정하에 예상 위치들 계산
        expected_spacing = canvas_dimension / (len(sorted_positions) + 1)
        expected_positions = [expected_spacing * (i + 1) for i in range(len(sorted_positions))]
        
        # 실제 위치와 예상 위치의 차이 계산
        total_deviation = 0
        for actual, expected in zip(sorted_positions, expected_positions):
            total_deviation += abs(actual - expected)
        
        # 정규화된 점수 (0~1)
        max_possible_deviation = canvas_dimension * len(sorted_positions)
        alignment_score = 1 - (total_deviation / max_possible_deviation)
        
        return max(0, alignment_score)

    def _analyze_visual_hierarchy(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """시각적 계층 구조 분석"""
        hierarchy_groups = {
            "primary": [],
            "secondary": [],
            "tertiary": [],
            "decorative": []
        }
        
        # 중요도별 그룹핑
        for element in elements:
            importance = element.get("importance", ElementImportance.DECORATIVE).value
            hierarchy_groups[importance].append(element)
        
        # 계층 구조 품질 평가
        hierarchy_score = 0
        
        # 주요 요소가 있는지 확인
        if hierarchy_groups["primary"]:
            hierarchy_score += 0.4
        
        # 적절한 분산이 있는지 확인
        non_empty_levels = sum(1 for group in hierarchy_groups.values() if group)
        if non_empty_levels >= 3:
            hierarchy_score += 0.3
        elif non_empty_levels >= 2:
            hierarchy_score += 0.2
        
        # 주요 요소가 적절한 위치에 있는지 확인 (상단 1/3 영역)
        primary_elements = hierarchy_groups["primary"]
        if primary_elements:
            well_positioned_primary = sum(
                1 for elem in primary_elements
                if elem.get("spatial_properties", {}).get("center", {}).get("y", 1000) < 360  # 1080/3
            )
            hierarchy_score += (well_positioned_primary / len(primary_elements)) * 0.3
        
        return {
            "hierarchy_groups": {k: len(v) for k, v in hierarchy_groups.items()},
            "hierarchy_score": hierarchy_score,
            "has_clear_hierarchy": hierarchy_score > 0.7
        }

    def _analyze_color_harmony(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """색상 조화 분석"""
        colors = []
        
        # 모든 요소의 색상 수집
        for element in elements:
            visual = element.get("visual_properties", {})
            color_info = visual.get("color", {})
            
            fill_color = color_info.get("fill")
            stroke_color = color_info.get("stroke")
            
            if fill_color and fill_color not in ["transparent", "none"]:
                colors.append(fill_color)
            if stroke_color and stroke_color not in ["transparent", "none"]:
                colors.append(stroke_color)
        
        # 중복 제거
        unique_colors = list(set(colors))
        
        # 색상 조화 점수 계산
        if not unique_colors:
            harmony_score = 1.0  # 색상이 없으면 조화로움
        elif len(unique_colors) <= 3:
            harmony_score = 0.9  # 3색 이하는 조화로움
        elif len(unique_colors) <= 5:
            harmony_score = 0.7  # 5색 이하는 보통
        else:
            harmony_score = 0.4  # 너무 많은 색상
        
        return {
            "color_count": len(unique_colors),
            "colors": unique_colors,
            "harmony_score": harmony_score,
            "is_harmonious": harmony_score > 0.6
        }

    def _analyze_spacing_density(self, elements: List[Dict[str, Any]], stage: KonvaStageData) -> Dict[str, Any]:
        """여백 및 밀도 분석"""
        if not elements:
            return {"density": "empty", "spacing_score": 1.0}
        
        # 전체 요소 면적 계산
        total_element_area = 0
        for element in elements:
            spatial = element.get("spatial_properties", {})
            size = spatial.get("size", {"width": 0, "height": 0})
            total_element_area += size.get("width", 0) * size.get("height", 0)
        
        # 캔버스 면적
        canvas_area = stage.width * stage.height
        
        # 밀도 계산 (0~1)
        density_ratio = total_element_area / canvas_area if canvas_area > 0 else 0
        
        # 밀도 범주 분류
        if density_ratio < 0.2:
            density_category = "sparse"
            spacing_score = 0.8  # 너무 비어있음
        elif density_ratio < 0.4:
            density_category = "balanced"
            spacing_score = 1.0  # 이상적
        elif density_ratio < 0.6:
            density_category = "dense"
            spacing_score = 0.7  # 약간 빡빡함
        else:
            density_category = "overcrowded"
            spacing_score = 0.4  # 너무 빡빡함
        
        return {
            "density_ratio": density_ratio,
            "density": density_category,
            "spacing_score": spacing_score
        }

    def _calculate_design_principles_score(self, elements: List[Dict[str, Any]], stage: KonvaStageData) -> Dict[str, float]:
        """디자인 원칙별 점수 계산"""
        scores = {}
        
        # 황금비율 점수
        scores[LayoutPrinciple.GOLDEN_RATIO.value] = self._calculate_golden_ratio_score(elements, stage)
        
        # 삼분할법 점수
        scores[LayoutPrinciple.RULE_OF_THIRDS.value] = self._calculate_rule_of_thirds_score(elements, stage)
        
        # 그리드 정렬 점수 (이미 계산됨)
        grid_analysis = self._analyze_grid_alignment(elements, stage)
        scores[LayoutPrinciple.GRID_ALIGNMENT.value] = grid_analysis["overall_score"]
        
        # 시각적 계층 구조 점수 (이미 계산됨)
        hierarchy_analysis = self._analyze_visual_hierarchy(elements)
        scores[LayoutPrinciple.VISUAL_HIERARCHY.value] = hierarchy_analysis["hierarchy_score"]
        
        # 색상 조화 점수 (이미 계산됨)
        color_analysis = self._analyze_color_harmony(elements)
        scores[LayoutPrinciple.COLOR_HARMONY.value] = color_analysis["harmony_score"]
        
        # 근접성 그룹핑 점수
        scores[LayoutPrinciple.PROXIMITY_GROUPING.value] = self._calculate_proximity_grouping_score(elements)
        
        return scores

    def _calculate_golden_ratio_score(self, elements: List[Dict[str, Any]], stage: KonvaStageData) -> float:
        """황금비율 점수 계산"""
        if not elements:
            return 1.0
        
        # 주요 요소들의 위치가 황금비율 지점에 가까운지 확인
        golden_x = stage.width / self.golden_ratio
        golden_y = stage.height / self.golden_ratio
        
        primary_elements = [e for e in elements if e.get("importance") == ElementImportance.PRIMARY.value]
        
        if not primary_elements:
            return 0.5
        
        total_score = 0
        for element in primary_elements:
            center = element.get("spatial_properties", {}).get("center", {"x": 0, "y": 0})
            
            # 황금비율 지점과의 거리 계산
            distance_x = abs(center["x"] - golden_x) / stage.width
            distance_y = abs(center["y"] - golden_y) / stage.height
            
            # 거리 점수 (가까울수록 높음)
            element_score = 1 - math.sqrt(distance_x**2 + distance_y**2)
            total_score += max(0, element_score)
        
        return total_score / len(primary_elements)

    def _calculate_rule_of_thirds_score(self, elements: List[Dict[str, Any]], stage: KonvaStageData) -> float:
        """삼분할법 점수 계산"""
        if not elements:
            return 1.0
        
        # 삼분할 지점들
        third_x_points = [stage.width * ratio for ratio in self.rule_of_thirds]
        third_y_points = [stage.height * ratio for ratio in self.rule_of_thirds]
        
        important_elements = [e for e in elements if e.get("importance") in [ElementImportance.PRIMARY.value, ElementImportance.SECONDARY.value]]
        
        if not important_elements:
            return 0.5
        
        total_score = 0
        for element in important_elements:
            center = element.get("spatial_properties", {}).get("center", {"x": 0, "y": 0})
            
            # 가장 가까운 삼분할 지점 찾기
            min_x_distance = min(abs(center["x"] - x_point) for x_point in third_x_points)
            min_y_distance = min(abs(center["y"] - y_point) for y_point in third_y_points)
            
            # 정규화된 거리 점수
            x_score = 1 - (min_x_distance / stage.width)
            y_score = 1 - (min_y_distance / stage.height)
            
            element_score = (x_score + y_score) / 2
            total_score += max(0, element_score)
        
        return total_score / len(important_elements)

    def _calculate_proximity_grouping_score(self, elements: List[Dict[str, Any]]) -> float:
        """근접성 그룹핑 점수 계산"""
        if len(elements) < 2:
            return 1.0
        
        # 관련된 요소들이 가까이 배치되어 있는지 확인
        # 현재는 단순하게 그룹화된 요소들의 비율로 계산
        grouped_elements = sum(1 for e in elements if e.get("relationships", {}).get("is_grouped", False))
        grouping_ratio = grouped_elements / len(elements)
        
        return min(1.0, grouping_ratio * 2)  # 50% 그룹화되면 만점

    async def _get_llm_layout_analysis(self, elements: List[Dict[str, Any]], composition: Dict[str, Any]) -> Dict[str, Any]:
        """LLM을 활용한 레이아웃 분석"""
        try:
            # 분석용 컨텍스트 생성
            context = self._create_analysis_context(elements, composition)
            
            analysis_prompt = f"""
당신은 전문 UI/UX 디자이너입니다. 다음 Canvas 레이아웃을 분석하고 개선안을 제안해주세요.

## 현재 Canvas 구성
{json.dumps(context, indent=2, ensure_ascii=False)}

## 분석 요청사항
1. **레이아웃 품질 평가** (1-10점)
2. **디자인 원칙 준수도** 분석
3. **사용자 경험 관점**에서의 문제점
4. **구체적 개선 제안** (우선순위별)
5. **적용 가능한 템플릿** 추천

## 응답 형식 (JSON)
{{
    "overall_score": 숫자,
    "design_principles": {{
        "hierarchy": 점수,
        "balance": 점수,
        "contrast": 점수,
        "alignment": 점수
    }},
    "strengths": ["강점1", "강점2"],
    "weaknesses": ["약점1", "약점2"],
    "improvements": [
        {{
            "priority": "high|medium|low",
            "suggestion": "구체적 개선안",
            "reasoning": "개선 이유",
            "expected_impact": "예상 효과"
        }}
    ],
    "recommended_templates": ["template1", "template2"],
    "user_experience_insights": "UX 관점 분석"
}}

한글로 자세히 분석해주세요.
"""
            
            # LLM 분석 실행
            llm_response = await llm_router.route_request(
                messages=[{"role": "user", "content": analysis_prompt}],
                model_preference="claude",  # 분석에는 Claude 선호
                temperature=0.3
            )
            
            # JSON 파싱 시도
            try:
                analysis_result = json.loads(llm_response.response)
            except json.JSONDecodeError:
                # JSON 파싱 실패시 기본 분석 제공
                analysis_result = {
                    "overall_score": 5,
                    "raw_analysis": llm_response.response,
                    "parsing_error": "LLM 응답을 JSON으로 파싱할 수 없습니다"
                }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"LLM 레이아웃 분석 실패: {str(e)}")
            return {
                "overall_score": 5,
                "error": f"LLM 분석 실패: {str(e)}",
                "fallback": "기본 분석을 사용합니다"
            }

    def _create_analysis_context(self, elements: List[Dict[str, Any]], composition: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 분석용 컨텍스트 생성"""
        return {
            "총_요소수": len(elements),
            "요소_유형별_개수": self._count_by_element_type(elements),
            "중요도별_분포": self._count_by_importance(elements),
            "전체_구성_점수": {
                "균형": composition.get("distribution", {}).get("balance_score", 0),
                "정렬": composition.get("grid_alignment", {}).get("overall_score", 0),
                "계층구조": composition.get("visual_hierarchy", {}).get("hierarchy_score", 0),
                "색상조화": composition.get("color_harmony", {}).get("harmony_score", 0),
                "여백밀도": composition.get("spacing_density", {}).get("spacing_score", 0)
            },
            "주요_문제점": self._identify_major_issues(elements, composition),
            "디자인_특성": self._extract_design_characteristics(elements, composition)
        }

    def _count_by_element_type(self, elements: List[Dict[str, Any]]) -> Dict[str, int]:
        """요소 유형별 개수"""
        type_counts = {}
        for element in elements:
            elem_type = element.get("element_type", "unknown")
            type_counts[elem_type] = type_counts.get(elem_type, 0) + 1
        return type_counts

    def _count_by_importance(self, elements: List[Dict[str, Any]]) -> Dict[str, int]:
        """중요도별 개수"""
        importance_counts = {}
        for element in elements:
            importance = element.get("importance", "decorative").value if hasattr(element.get("importance"), "value") else element.get("importance", "decorative")
            importance_counts[importance] = importance_counts.get(importance, 0) + 1
        return importance_counts

    def _identify_major_issues(self, elements: List[Dict[str, Any]], composition: Dict[str, Any]) -> List[str]:
        """주요 문제점 식별"""
        issues = []
        
        # 균형 문제
        balance_score = composition.get("distribution", {}).get("balance_score", 0)
        if balance_score < 0.4:
            issues.append("요소 배치가 불균형합니다")
        
        # 정렬 문제
        alignment_score = composition.get("grid_alignment", {}).get("overall_score", 0)
        if alignment_score < 0.5:
            issues.append("요소들의 정렬이 일관되지 않습니다")
        
        # 계층 구조 문제
        hierarchy_score = composition.get("visual_hierarchy", {}).get("hierarchy_score", 0)
        if hierarchy_score < 0.5:
            issues.append("시각적 계층 구조가 명확하지 않습니다")
        
        # 색상 조화 문제
        color_score = composition.get("color_harmony", {}).get("harmony_score", 0)
        if color_score < 0.6:
            issues.append("색상 조화도가 낮습니다")
        
        # 밀도 문제
        spacing_score = composition.get("spacing_density", {}).get("spacing_score", 0)
        if spacing_score < 0.6:
            issues.append("여백과 밀도가 적절하지 않습니다")
        
        return issues

    def _extract_design_characteristics(self, elements: List[Dict[str, Any]], composition: Dict[str, Any]) -> Dict[str, Any]:
        """디자인 특성 추출"""
        return {
            "스타일": self._infer_design_style(elements),
            "복잡도": "높음" if len(elements) > 10 else "보통" if len(elements) > 5 else "낮음",
            "주요_색상": composition.get("color_harmony", {}).get("colors", [])[:3],
            "레이아웃_패턴": self._infer_layout_pattern(elements, composition)
        }

    def _infer_design_style(self, elements: List[Dict[str, Any]]) -> str:
        """디자인 스타일 추론"""
        text_count = sum(1 for e in elements if e.get("element_type") == "heading" or e.get("element_type") == "body_text")
        image_count = sum(1 for e in elements if e.get("element_type") == "image")
        shape_count = sum(1 for e in elements if "shape" in e.get("element_type", ""))
        
        if text_count > image_count + shape_count:
            return "텍스트 중심"
        elif image_count > text_count + shape_count:
            return "이미지 중심"
        elif shape_count > 0:
            return "그래픽 중심"
        else:
            return "혼합형"

    def _infer_layout_pattern(self, elements: List[Dict[str, Any]], composition: Dict[str, Any]) -> str:
        """레이아웃 패턴 추론"""
        alignment_score = composition.get("grid_alignment", {}).get("overall_score", 0)
        balance = composition.get("distribution", {}).get("balance", "moderate")
        
        if alignment_score > 0.8:
            return "그리드형"
        elif balance == "balanced":
            return "균형형"
        else:
            return "자유형"

    async def _generate_optimization_suggestions(self, elements: List[Dict[str, Any]], composition: Dict[str, Any], llm_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """최적화 제안 생성"""
        suggestions = []
        
        # 자동 생성된 제안들
        auto_suggestions = self._generate_auto_suggestions(elements, composition)
        suggestions.extend(auto_suggestions)
        
        # LLM 기반 제안들 (있다면)
        llm_improvements = llm_analysis.get("improvements", [])
        suggestions.extend(llm_improvements)
        
        # 우선순위로 정렬
        priority_order = {"high": 1, "medium": 2, "low": 3}
        suggestions.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
        
        return suggestions[:10]  # 상위 10개만 반환

    def _generate_auto_suggestions(self, elements: List[Dict[str, Any]], composition: Dict[str, Any]) -> List[Dict[str, Any]]:
        """자동 최적화 제안 생성"""
        suggestions = []
        
        # 균형 개선 제안
        balance_score = composition.get("distribution", {}).get("balance_score", 0)
        if balance_score < 0.5:
            suggestions.append({
                "priority": "high",
                "suggestion": "요소들을 캔버스 중앙을 기준으로 균형있게 재배치",
                "reasoning": "현재 레이아웃의 무게중심이 치우쳐 있어 시각적 불안정감을 줍니다",
                "expected_impact": "전체적인 안정감과 조화로운 느낌 향상",
                "auto_fix_available": True
            })
        
        # 정렬 개선 제안
        alignment_score = composition.get("grid_alignment", {}).get("overall_score", 0)
        if alignment_score < 0.6:
            suggestions.append({
                "priority": "medium",
                "suggestion": "요소들을 그리드 라인에 맞춰 정렬",
                "reasoning": "일관된 정렬이 없어 정리되지 않은 느낌을 줍니다",
                "expected_impact": "전문적이고 정돈된 인상 향상",
                "auto_fix_available": True
            })
        
        # 계층 구조 개선 제안
        hierarchy_score = composition.get("visual_hierarchy", {}).get("hierarchy_score", 0)
        if hierarchy_score < 0.5:
            suggestions.append({
                "priority": "high",
                "suggestion": "중요한 요소를 상단 영역으로 이동하고 크기 조정",
                "reasoning": "시각적 계층 구조가 명확하지 않아 정보 전달이 비효율적입니다",
                "expected_impact": "정보 전달력과 사용자 이해도 향상",
                "auto_fix_available": True
            })
        
        return suggestions

# 전역 인스턴스
ai_layout_engine = AILayoutEngine()

# 공개 함수들
async def analyze_canvas_layout(canvas_data: CanvasData) -> Dict[str, Any]:
    """Canvas 레이아웃 분석"""
    return await ai_layout_engine.analyze_canvas_elements(canvas_data)

async def get_layout_suggestions(canvas_data: CanvasData) -> List[Dict[str, Any]]:
    """레이아웃 개선 제안"""
    analysis = await analyze_canvas_layout(canvas_data)
    return analysis.get("optimization_suggestions", [])

async def apply_auto_layout_fixes(canvas_data: CanvasData, suggestion_ids: List[str]) -> CanvasData:
    """자동 레이아웃 수정 적용"""
    # 이 함수는 다음 단계에서 구현
    logger.info(f"자동 레이아웃 수정 요청: {suggestion_ids}")
    return canvas_data