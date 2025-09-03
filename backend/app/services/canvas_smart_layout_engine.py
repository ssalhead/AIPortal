# Canvas 스마트 레이아웃 엔진 v1.0
# 지능형 정렬 알고리즘 및 자동 배치 시스템

import logging
import asyncio
import math
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from enum import Enum

from app.models.canvas_models import (
    KonvaNodeData, 
    KonvaLayerData, 
    KonvaStageData,
    KonvaNodeType,
    CanvasData
)

logger = logging.getLogger(__name__)

class GridType(str, Enum):
    """그리드 유형"""
    UNIFORM = "uniform"           # 균등 그리드
    GOLDEN_RATIO = "golden_ratio" # 황금비율 그리드
    RULE_OF_THIRDS = "rule_of_thirds" # 삼분할법 그리드
    FIBONACCI = "fibonacci"       # 피보나치 그리드
    DYNAMIC = "dynamic"          # 동적 적응형 그리드

class AlignmentStrategy(str, Enum):
    """정렬 전략"""
    AUTO_DETECT = "auto_detect"   # 자동 감지
    LEFT_ALIGN = "left_align"     # 좌정렬
    CENTER_ALIGN = "center_align" # 중앙정렬
    RIGHT_ALIGN = "right_align"   # 우정렬
    JUSTIFY = "justify"          # 양쪽 정렬
    DISTRIBUTE = "distribute"     # 균등 분배

class LayoutOptimization(str, Enum):
    """레이아웃 최적화 유형"""
    MINIMIZE_OVERLAP = "minimize_overlap"     # 겹침 최소화
    MAXIMIZE_READABILITY = "maximize_readability" # 가독성 최대화
    OPTIMIZE_FLOW = "optimize_flow"           # 시각적 플로우 최적화
    BALANCE_COMPOSITION = "balance_composition" # 구성 균형 최적화
    ENHANCE_HIERARCHY = "enhance_hierarchy"   # 계층 구조 강화

class SmartLayoutEngine:
    """스마트 레이아웃 엔진"""
    
    def __init__(self):
        self.golden_ratio = 1.618
        self.fibonacci_sequence = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
        
        # 기본 그리드 설정
        self.default_grid_size = 20
        self.min_margin = 10
        self.min_spacing = 5
        
        # 요소별 기본 크기
        self.default_sizes = {
            "heading": {"width": 300, "height": 40},
            "subheading": {"width": 250, "height": 30},
            "body_text": {"width": 200, "height": 20},
            "image": {"width": 200, "height": 150},
            "button": {"width": 120, "height": 35},
            "icon": {"width": 24, "height": 24}
        }

    async def generate_smart_grid(self, stage: KonvaStageData, grid_type: GridType = GridType.DYNAMIC) -> Dict[str, Any]:
        """스마트 그리드 생성"""
        try:
            width, height = stage.width, stage.height
            
            if grid_type == GridType.UNIFORM:
                return self._generate_uniform_grid(width, height)
            elif grid_type == GridType.GOLDEN_RATIO:
                return self._generate_golden_ratio_grid(width, height)
            elif grid_type == GridType.RULE_OF_THIRDS:
                return self._generate_rule_of_thirds_grid(width, height)
            elif grid_type == GridType.FIBONACCI:
                return self._generate_fibonacci_grid(width, height)
            else:  # DYNAMIC
                return self._generate_dynamic_grid(width, height)
                
        except Exception as e:
            logger.error(f"스마트 그리드 생성 실패: {str(e)}")
            return self._generate_uniform_grid(stage.width, stage.height)

    def _generate_uniform_grid(self, width: int, height: int) -> Dict[str, Any]:
        """균등 그리드 생성"""
        grid_size = self.default_grid_size
        
        # 그리드 라인 계산
        vertical_lines = [i * grid_size for i in range(0, width // grid_size + 1)]
        horizontal_lines = [i * grid_size for i in range(0, height // grid_size + 1)]
        
        # 스냅 포인트 생성
        snap_points = []
        for x in vertical_lines:
            for y in horizontal_lines:
                snap_points.append({"x": x, "y": y})
        
        return {
            "type": "uniform",
            "grid_size": grid_size,
            "vertical_lines": vertical_lines,
            "horizontal_lines": horizontal_lines,
            "snap_points": snap_points,
            "zones": self._create_uniform_zones(width, height, grid_size)
        }

    def _generate_golden_ratio_grid(self, width: int, height: int) -> Dict[str, Any]:
        """황금비율 그리드 생성"""
        # 황금비율 분할점들
        major_x = width / self.golden_ratio
        minor_x = width - major_x
        major_y = height / self.golden_ratio
        minor_y = height - major_y
        
        vertical_lines = [0, minor_x, major_x, width]
        horizontal_lines = [0, minor_y, major_y, height]
        
        # 황금비율 교차점들 (중요 위치)
        focal_points = [
            {"x": major_x, "y": major_y, "importance": 1.0},
            {"x": minor_x, "y": minor_y, "importance": 0.8},
            {"x": major_x, "y": minor_y, "importance": 0.7},
            {"x": minor_x, "y": major_y, "importance": 0.7}
        ]
        
        return {
            "type": "golden_ratio",
            "vertical_lines": vertical_lines,
            "horizontal_lines": horizontal_lines,
            "focal_points": focal_points,
            "zones": self._create_golden_ratio_zones(width, height, major_x, major_y)
        }

    def _generate_rule_of_thirds_grid(self, width: int, height: int) -> Dict[str, Any]:
        """삼분할법 그리드 생성"""
        third_x = width / 3
        third_y = height / 3
        
        vertical_lines = [0, third_x, third_x * 2, width]
        horizontal_lines = [0, third_y, third_y * 2, height]
        
        # 삼분할법 교차점들
        focal_points = [
            {"x": third_x, "y": third_y, "importance": 1.0},
            {"x": third_x * 2, "y": third_y, "importance": 1.0},
            {"x": third_x, "y": third_y * 2, "importance": 1.0},
            {"x": third_x * 2, "y": third_y * 2, "importance": 1.0}
        ]
        
        return {
            "type": "rule_of_thirds",
            "vertical_lines": vertical_lines,
            "horizontal_lines": horizontal_lines,
            "focal_points": focal_points,
            "zones": self._create_thirds_zones(width, height, third_x, third_y)
        }

    def _generate_fibonacci_grid(self, width: int, height: int) -> Dict[str, Any]:
        """피보나치 그리드 생성"""
        # 피보나치 비율로 공간 분할
        total_ratio = sum(self.fibonacci_sequence[:5])  # 첫 5개 수 사용
        
        x_divisions = []
        y_divisions = []
        current_x = 0
        current_y = 0
        
        for i, ratio in enumerate(self.fibonacci_sequence[:4]):
            x_divisions.append(current_x)
            y_divisions.append(current_y)
            current_x += (width * ratio) / total_ratio
            current_y += (height * ratio) / total_ratio
        
        x_divisions.append(width)
        y_divisions.append(height)
        
        return {
            "type": "fibonacci",
            "vertical_lines": x_divisions,
            "horizontal_lines": y_divisions,
            "zones": self._create_fibonacci_zones(width, height, x_divisions, y_divisions)
        }

    def _generate_dynamic_grid(self, width: int, height: int) -> Dict[str, Any]:
        """동적 적응형 그리드 생성"""
        # 캔버스 크기에 따른 적응형 그리드
        
        # 기본 그리드 크기 계산 (캔버스 크기에 비례)
        adaptive_grid_size = max(10, min(width, height) // 50)
        
        # 주요 분할점들 (여러 원칙 조합)
        third_x, third_y = width / 3, height / 3
        golden_x, golden_y = width / self.golden_ratio, height / self.golden_ratio
        
        # 중요 수직선들
        vertical_lines = [
            0, 
            third_x, 
            golden_x,
            width / 2,
            width - golden_x,
            third_x * 2,
            width
        ]
        
        # 중요 수평선들
        horizontal_lines = [
            0,
            third_y,
            golden_y,
            height / 2,
            height - golden_y,
            third_y * 2,
            height
        ]
        
        # 중복 제거 및 정렬
        vertical_lines = sorted(list(set(vertical_lines)))
        horizontal_lines = sorted(list(set(horizontal_lines)))
        
        # 적응형 그리드 추가
        for i in range(adaptive_grid_size, width, adaptive_grid_size):
            if i not in vertical_lines:
                vertical_lines.append(i)
        
        for i in range(adaptive_grid_size, height, adaptive_grid_size):
            if i not in horizontal_lines:
                horizontal_lines.append(i)
        
        vertical_lines.sort()
        horizontal_lines.sort()
        
        return {
            "type": "dynamic",
            "adaptive_grid_size": adaptive_grid_size,
            "vertical_lines": vertical_lines,
            "horizontal_lines": horizontal_lines,
            "focal_points": self._calculate_dynamic_focal_points(width, height),
            "zones": self._create_dynamic_zones(width, height, vertical_lines, horizontal_lines)
        }

    def _create_uniform_zones(self, width: int, height: int, grid_size: int) -> List[Dict[str, Any]]:
        """균등 그리드 영역 생성"""
        zones = []
        rows = height // grid_size
        cols = width // grid_size
        
        for row in range(rows):
            for col in range(cols):
                zones.append({
                    "id": f"zone_{row}_{col}",
                    "x": col * grid_size,
                    "y": row * grid_size,
                    "width": grid_size,
                    "height": grid_size,
                    "priority": 0.5,
                    "recommended_content": ["any"]
                })
        
        return zones

    def _create_golden_ratio_zones(self, width: int, height: int, major_x: float, major_y: float) -> List[Dict[str, Any]]:
        """황금비율 영역 생성"""
        return [
            {
                "id": "primary_focus",
                "x": 0, "y": 0,
                "width": major_x, "height": major_y,
                "priority": 1.0,
                "recommended_content": ["heading", "logo", "key_visual"]
            },
            {
                "id": "secondary_left",
                "x": 0, "y": major_y,
                "width": major_x, "height": height - major_y,
                "priority": 0.7,
                "recommended_content": ["subheading", "navigation"]
            },
            {
                "id": "secondary_right",
                "x": major_x, "y": 0,
                "width": width - major_x, "height": major_y,
                "priority": 0.7,
                "recommended_content": ["supporting_content", "sidebar"]
            },
            {
                "id": "tertiary",
                "x": major_x, "y": major_y,
                "width": width - major_x, "height": height - major_y,
                "priority": 0.4,
                "recommended_content": ["footer", "additional_info"]
            }
        ]

    def _create_thirds_zones(self, width: int, height: int, third_x: float, third_y: float) -> List[Dict[str, Any]]:
        """삼분할법 영역 생성"""
        zones = []
        zone_width = third_x
        zone_height = third_y
        
        priorities = [
            [0.6, 1.0, 0.6],
            [0.8, 0.9, 0.8],
            [0.4, 0.5, 0.4]
        ]
        
        content_types = [
            [["header"], ["main_heading"], ["header"]],
            [["sidebar"], ["main_content"], ["sidebar"]],
            [["footer"], ["footer"], ["footer"]]
        ]
        
        for row in range(3):
            for col in range(3):
                zones.append({
                    "id": f"thirds_{row}_{col}",
                    "x": col * zone_width,
                    "y": row * zone_height,
                    "width": zone_width,
                    "height": zone_height,
                    "priority": priorities[row][col],
                    "recommended_content": content_types[row][col]
                })
        
        return zones

    def _create_fibonacci_zones(self, width: int, height: int, x_divisions: List[float], y_divisions: List[float]) -> List[Dict[str, Any]]:
        """피보나치 영역 생성"""
        zones = []
        priorities = [1.0, 0.8, 0.6, 0.4, 0.3]
        
        for i in range(len(x_divisions) - 1):
            for j in range(len(y_divisions) - 1):
                priority = priorities[min(i + j, len(priorities) - 1)]
                zones.append({
                    "id": f"fib_{i}_{j}",
                    "x": x_divisions[i],
                    "y": y_divisions[j],
                    "width": x_divisions[i + 1] - x_divisions[i],
                    "height": y_divisions[j + 1] - y_divisions[j],
                    "priority": priority,
                    "recommended_content": self._get_fibonacci_content_type(priority)
                })
        
        return zones

    def _create_dynamic_zones(self, width: int, height: int, v_lines: List[float], h_lines: List[float]) -> List[Dict[str, Any]]:
        """동적 영역 생성"""
        zones = []
        center_x, center_y = width / 2, height / 2
        
        for i in range(len(v_lines) - 1):
            for j in range(len(h_lines) - 1):
                zone_x = v_lines[i]
                zone_y = h_lines[j]
                zone_w = v_lines[i + 1] - v_lines[i]
                zone_h = h_lines[j + 1] - h_lines[j]
                
                # 중심에서의 거리로 우선순위 계산
                zone_center_x = zone_x + zone_w / 2
                zone_center_y = zone_y + zone_h / 2
                distance_from_center = math.sqrt(
                    (zone_center_x - center_x) ** 2 + (zone_center_y - center_y) ** 2
                )
                max_distance = math.sqrt(center_x ** 2 + center_y ** 2)
                priority = 1 - (distance_from_center / max_distance)
                
                zones.append({
                    "id": f"dynamic_{i}_{j}",
                    "x": zone_x,
                    "y": zone_y,
                    "width": zone_w,
                    "height": zone_h,
                    "priority": priority,
                    "recommended_content": self._get_dynamic_content_type(priority)
                })
        
        return zones

    def _calculate_dynamic_focal_points(self, width: int, height: int) -> List[Dict[str, Any]]:
        """동적 초점 계산"""
        return [
            {"x": width / self.golden_ratio, "y": height / self.golden_ratio, "importance": 1.0},
            {"x": width / 3, "y": height / 3, "importance": 0.9},
            {"x": width * 2 / 3, "y": height / 3, "importance": 0.9},
            {"x": width / 3, "y": height * 2 / 3, "importance": 0.8},
            {"x": width * 2 / 3, "y": height * 2 / 3, "importance": 0.8},
            {"x": width / 2, "y": height / 2, "importance": 0.7}
        ]

    def _get_fibonacci_content_type(self, priority: float) -> List[str]:
        """피보나치 우선순위에 따른 콘텐츠 유형"""
        if priority >= 0.8:
            return ["heading", "logo", "hero_image"]
        elif priority >= 0.6:
            return ["subheading", "important_text"]
        elif priority >= 0.4:
            return ["body_text", "supporting_image"]
        else:
            return ["footer", "decorative"]

    def _get_dynamic_content_type(self, priority: float) -> List[str]:
        """동적 우선순위에 따른 콘텐츠 유형"""
        if priority >= 0.8:
            return ["heading", "logo", "call_to_action"]
        elif priority >= 0.6:
            return ["subheading", "key_content"]
        elif priority >= 0.4:
            return ["body_text", "supporting_content"]
        else:
            return ["background", "decorative", "footer"]

    async def auto_align_elements(
        self, 
        elements: List[KonvaNodeData], 
        grid: Dict[str, Any],
        strategy: AlignmentStrategy = AlignmentStrategy.AUTO_DETECT
    ) -> List[KonvaNodeData]:
        """요소 자동 정렬"""
        try:
            if strategy == AlignmentStrategy.AUTO_DETECT:
                strategy = self._detect_best_alignment_strategy(elements, grid)
            
            aligned_elements = []
            
            for element in elements:
                aligned_element = await self._align_single_element(element, grid, strategy)
                aligned_elements.append(aligned_element)
            
            # 겹침 해결
            aligned_elements = self._resolve_overlaps(aligned_elements)
            
            return aligned_elements
            
        except Exception as e:
            logger.error(f"요소 자동 정렬 실패: {str(e)}")
            return elements

    def _detect_best_alignment_strategy(self, elements: List[KonvaNodeData], grid: Dict[str, Any]) -> AlignmentStrategy:
        """최적 정렬 전략 감지"""
        if not elements:
            return AlignmentStrategy.CENTER_ALIGN
        
        # 요소들의 현재 분포 분석
        x_positions = [elem.x for elem in elements]
        y_positions = [elem.y for elem in elements]
        
        # 좌측 정렬 경향성 확인
        left_aligned_count = sum(1 for x in x_positions if x < grid.get("vertical_lines", [100])[1])
        
        if left_aligned_count / len(elements) > 0.7:
            return AlignmentStrategy.LEFT_ALIGN
        
        # 중앙 정렬 경향성 확인
        canvas_width = max(grid.get("vertical_lines", [1000]))
        center_range = (canvas_width * 0.4, canvas_width * 0.6)
        center_aligned_count = sum(1 for x in x_positions if center_range[0] <= x <= center_range[1])
        
        if center_aligned_count / len(elements) > 0.5:
            return AlignmentStrategy.CENTER_ALIGN
        
        # 기본값: 분산 배치
        return AlignmentStrategy.DISTRIBUTE

    async def _align_single_element(
        self, 
        element: KonvaNodeData, 
        grid: Dict[str, Any], 
        strategy: AlignmentStrategy
    ) -> KonvaNodeData:
        """단일 요소 정렬"""
        
        vertical_lines = grid.get("vertical_lines", [])
        horizontal_lines = grid.get("horizontal_lines", [])
        
        # 현재 위치에서 가장 가까운 그리드 라인 찾기
        if vertical_lines:
            closest_v_line = min(vertical_lines, key=lambda x: abs(x - element.x))
        else:
            closest_v_line = element.x
            
        if horizontal_lines:
            closest_h_line = min(horizontal_lines, key=lambda y: abs(y - element.y))
        else:
            closest_h_line = element.y
        
        # 정렬 전략 적용
        new_element = element.model_copy()
        
        if strategy == AlignmentStrategy.LEFT_ALIGN:
            new_element.x = vertical_lines[0] if vertical_lines else element.x
            new_element.y = closest_h_line
            
        elif strategy == AlignmentStrategy.CENTER_ALIGN:
            canvas_width = max(vertical_lines) if vertical_lines else 1000
            element_width = element.width or 100
            new_element.x = (canvas_width - element_width) / 2
            new_element.y = closest_h_line
            
        elif strategy == AlignmentStrategy.RIGHT_ALIGN:
            canvas_width = max(vertical_lines) if vertical_lines else 1000
            element_width = element.width or 100
            new_element.x = canvas_width - element_width
            new_element.y = closest_h_line
            
        else:  # DISTRIBUTE or default
            new_element.x = closest_v_line
            new_element.y = closest_h_line
        
        return new_element

    def _resolve_overlaps(self, elements: List[KonvaNodeData]) -> List[KonvaNodeData]:
        """겹침 해결"""
        resolved_elements = []
        
        for i, element in enumerate(elements):
            new_element = element.model_copy()
            
            # 이전 요소들과의 겹침 확인 및 해결
            for prev_element in resolved_elements:
                if self._check_overlap(new_element, prev_element):
                    new_element = self._adjust_position_to_avoid_overlap(new_element, prev_element)
            
            resolved_elements.append(new_element)
        
        return resolved_elements

    def _check_overlap(self, elem1: KonvaNodeData, elem2: KonvaNodeData) -> bool:
        """요소 겹침 확인"""
        e1_right = elem1.x + (elem1.width or 100)
        e1_bottom = elem1.y + (elem1.height or 100)
        e2_right = elem2.x + (elem2.width or 100)
        e2_bottom = elem2.y + (elem2.height or 100)
        
        return not (e1_right <= elem2.x or elem1.x >= e2_right or 
                   e1_bottom <= elem2.y or elem1.y >= e2_bottom)

    def _adjust_position_to_avoid_overlap(self, element: KonvaNodeData, obstacle: KonvaNodeData) -> KonvaNodeData:
        """겹침 회피를 위한 위치 조정"""
        new_element = element.model_copy()
        
        obstacle_right = obstacle.x + (obstacle.width or 100)
        obstacle_bottom = obstacle.y + (obstacle.height or 100)
        
        # 가장 가까운 비어있는 위치 찾기
        # 오른쪽으로 이동
        option1_x = obstacle_right + self.min_spacing
        option1_distance = abs(option1_x - element.x)
        
        # 아래쪽으로 이동
        option2_y = obstacle_bottom + self.min_spacing
        option2_distance = abs(option2_y - element.y)
        
        # 가장 가까운 옵션 선택
        if option1_distance <= option2_distance:
            new_element.x = option1_x
        else:
            new_element.y = option2_y
        
        return new_element

    async def optimize_layout(
        self, 
        elements: List[KonvaNodeData], 
        stage: KonvaStageData,
        optimization_type: LayoutOptimization = LayoutOptimization.BALANCE_COMPOSITION
    ) -> List[KonvaNodeData]:
        """레이아웃 최적화"""
        try:
            if optimization_type == LayoutOptimization.MINIMIZE_OVERLAP:
                return self._minimize_overlaps(elements)
            elif optimization_type == LayoutOptimization.MAXIMIZE_READABILITY:
                return self._maximize_readability(elements, stage)
            elif optimization_type == LayoutOptimization.OPTIMIZE_FLOW:
                return self._optimize_visual_flow(elements, stage)
            elif optimization_type == LayoutOptimization.ENHANCE_HIERARCHY:
                return self._enhance_hierarchy(elements, stage)
            else:  # BALANCE_COMPOSITION
                return self._balance_composition(elements, stage)
                
        except Exception as e:
            logger.error(f"레이아웃 최적화 실패: {str(e)}")
            return elements

    def _minimize_overlaps(self, elements: List[KonvaNodeData]) -> List[KonvaNodeData]:
        """겹침 최소화"""
        return self._resolve_overlaps(elements)

    def _maximize_readability(self, elements: List[KonvaNodeData], stage: KonvaStageData) -> List[KonvaNodeData]:
        """가독성 최대화"""
        optimized_elements = []
        text_elements = [e for e in elements if e.node_type == "text"]
        other_elements = [e for e in elements if e.node_type != "text"]
        
        # 텍스트 요소들을 가독성 최적화
        for element in text_elements:
            new_element = element.model_copy()
            
            # 적절한 여백 확보
            new_element.x = max(self.min_margin, new_element.x)
            new_element.y = max(self.min_margin, new_element.y)
            
            # 텍스트 크기 조정 (필요시)
            font_size = new_element.konva_attrs.get("fontSize", 14)
            if font_size < 12:  # 너무 작은 텍스트
                new_element.konva_attrs["fontSize"] = 12
            
            optimized_elements.append(new_element)
        
        # 다른 요소들 추가
        optimized_elements.extend(other_elements)
        
        return self._resolve_overlaps(optimized_elements)

    def _optimize_visual_flow(self, elements: List[KonvaNodeData], stage: KonvaStageData) -> List[KonvaNodeData]:
        """시각적 플로우 최적화"""
        # Z형 또는 F형 읽기 패턴을 고려한 배치
        optimized_elements = []
        
        # 중요도별 정렬
        elements_by_importance = self._sort_by_importance(elements)
        
        # Z형 패턴 적용
        flow_positions = self._calculate_z_pattern_positions(stage)
        
        for i, element in enumerate(elements_by_importance):
            if i < len(flow_positions):
                new_element = element.model_copy()
                new_element.x = flow_positions[i]["x"]
                new_element.y = flow_positions[i]["y"]
                optimized_elements.append(new_element)
            else:
                optimized_elements.append(element)
        
        return optimized_elements

    def _enhance_hierarchy(self, elements: List[KonvaNodeData], stage: KonvaStageData) -> List[KonvaNodeData]:
        """계층 구조 강화"""
        optimized_elements = []
        
        # 중요도별 그룹화
        primary_elements = []
        secondary_elements = []
        tertiary_elements = []
        
        for element in elements:
            importance = self._calculate_element_importance(element)
            if importance >= 0.8:
                primary_elements.append(element)
            elif importance >= 0.5:
                secondary_elements.append(element)
            else:
                tertiary_elements.append(element)
        
        # 주요 요소들을 상단 중앙에 배치
        for i, element in enumerate(primary_elements):
            new_element = element.model_copy()
            new_element.x = (stage.width - (element.width or 100)) / 2
            new_element.y = 50 + i * 80
            optimized_elements.append(new_element)
        
        # 보조 요소들을 중간 영역에 배치
        start_y = 200 if primary_elements else 50
        for i, element in enumerate(secondary_elements):
            new_element = element.model_copy()
            new_element.x = 100 + (i % 2) * (stage.width / 2 - 200)
            new_element.y = start_y + (i // 2) * 80
            optimized_elements.append(new_element)
        
        # 3차 요소들은 하단에 배치
        start_y = max(400, start_y + len(secondary_elements) * 40)
        for i, element in enumerate(tertiary_elements):
            new_element = element.model_copy()
            new_element.x = 50 + (i % 3) * (stage.width / 3 - 100)
            new_element.y = start_y + (i // 3) * 60
            optimized_elements.append(new_element)
        
        return optimized_elements

    def _balance_composition(self, elements: List[KonvaNodeData], stage: KonvaStageData) -> List[KonvaNodeData]:
        """구성 균형 최적화"""
        # 무게중심 계산 및 균형 조정
        center_x, center_y = stage.width / 2, stage.height / 2
        
        # 현재 무게중심 계산
        total_weight = 0
        weighted_x = 0
        weighted_y = 0
        
        for element in elements:
            weight = (element.width or 100) * (element.height or 100)
            total_weight += weight
            weighted_x += element.x * weight
            weighted_y += element.y * weight
        
        if total_weight == 0:
            return elements
        
        current_center_x = weighted_x / total_weight
        current_center_y = weighted_y / total_weight
        
        # 중심 이동량 계산
        offset_x = center_x - current_center_x
        offset_y = center_y - current_center_y
        
        # 모든 요소를 이동하여 균형 맞추기
        balanced_elements = []
        for element in elements:
            new_element = element.model_copy()
            new_element.x += offset_x * 0.5  # 50% 정도만 보정
            new_element.y += offset_y * 0.5
            
            # 캔버스 경계 내 유지
            new_element.x = max(0, min(new_element.x, stage.width - (element.width or 100)))
            new_element.y = max(0, min(new_element.y, stage.height - (element.height or 100)))
            
            balanced_elements.append(new_element)
        
        return balanced_elements

    def _sort_by_importance(self, elements: List[KonvaNodeData]) -> List[KonvaNodeData]:
        """중요도별 정렬"""
        return sorted(elements, key=self._calculate_element_importance, reverse=True)

    def _calculate_element_importance(self, element: KonvaNodeData) -> float:
        """요소 중요도 계산"""
        importance = 0.0
        
        # 크기 기반 중요도
        if element.width and element.height:
            area = element.width * element.height
            importance += min(1.0, area / 10000)  # 정규화
        
        # 텍스트 크기 기반
        if element.node_type == "text":
            font_size = element.konva_attrs.get("fontSize", 14)
            importance += min(1.0, font_size / 48)
        
        # z-index 기반
        z_index = element.z_index or 0
        importance += min(0.5, z_index / 20)
        
        return min(1.0, importance)

    def _calculate_z_pattern_positions(self, stage: KonvaStageData) -> List[Dict[str, float]]:
        """Z형 패턴 위치 계산"""
        return [
            {"x": 50, "y": 50},                                    # 좌상단
            {"x": stage.width - 250, "y": 50},                     # 우상단
            {"x": stage.width / 2 - 100, "y": stage.height / 2},   # 중앙
            {"x": 50, "y": stage.height - 150},                    # 좌하단
            {"x": stage.width - 250, "y": stage.height - 150}      # 우하단
        ]

# 전역 인스턴스
smart_layout_engine = SmartLayoutEngine()

# 공개 함수들
async def generate_smart_grid(stage: KonvaStageData, grid_type: GridType = GridType.DYNAMIC) -> Dict[str, Any]:
    """스마트 그리드 생성"""
    return await smart_layout_engine.generate_smart_grid(stage, grid_type)

async def auto_align_elements(
    elements: List[KonvaNodeData], 
    grid: Dict[str, Any],
    strategy: AlignmentStrategy = AlignmentStrategy.AUTO_DETECT
) -> List[KonvaNodeData]:
    """요소 자동 정렬"""
    return await smart_layout_engine.auto_align_elements(elements, grid, strategy)

async def optimize_layout(
    elements: List[KonvaNodeData], 
    stage: KonvaStageData,
    optimization_type: LayoutOptimization = LayoutOptimization.BALANCE_COMPOSITION
) -> List[KonvaNodeData]:
    """레이아웃 최적화"""
    return await smart_layout_engine.optimize_layout(elements, stage, optimization_type)

async def apply_template_layout(
    elements: List[KonvaNodeData], 
    stage: KonvaStageData,
    template_type: str
) -> List[KonvaNodeData]:
    """템플릿 기반 레이아웃 적용 (다음 단계에서 구현)"""
    logger.info(f"템플릿 레이아웃 적용: {template_type}")
    return elements