# Canvas AI 어드바이저 서비스 v1.0
# 실시간 레이아웃 제안 및 개선 시스템

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
import json

from app.models.canvas_models import (
    KonvaNodeData, 
    KonvaLayerData, 
    KonvaStageData,
    KonvaNodeType,
    CanvasData
)
from app.services.canvas_ai_layout_service import ai_layout_engine
from app.services.canvas_smart_layout_engine import smart_layout_engine
from app.services.canvas_template_engine import template_engine
from app.agents.llm_router import llm_router

logger = logging.getLogger(__name__)

class SuggestionType(str, Enum):
    """제안 유형"""
    LAYOUT_OPTIMIZATION = "layout_optimization"     # 레이아웃 최적화
    ALIGNMENT_FIX = "alignment_fix"                 # 정렬 수정
    COLOR_HARMONY = "color_harmony"                 # 색상 조화
    TYPOGRAPHY_IMPROVEMENT = "typography_improvement" # 타이포그래피 개선
    SPACING_ADJUSTMENT = "spacing_adjustment"        # 여백 조정
    HIERARCHY_ENHANCEMENT = "hierarchy_enhancement"  # 계층 구조 강화
    TEMPLATE_SUGGESTION = "template_suggestion"      # 템플릿 제안
    CONTENT_OPTIMIZATION = "content_optimization"    # 콘텐츠 최적화

class SuggestionPriority(str, Enum):
    """제안 우선순위"""
    CRITICAL = "critical"    # 필수 수정
    HIGH = "high"           # 높음
    MEDIUM = "medium"       # 보통
    LOW = "low"             # 낮음
    OPTIONAL = "optional"   # 선택사항

class UserPreference:
    """사용자 선호도 모델"""
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.style_preferences = {}
        self.layout_patterns = {}
        self.color_preferences = {}
        self.template_usage = {}
        self.suggestion_feedback = {}
        self.last_updated = datetime.utcnow()

    def update_from_canvas(self, canvas_data: CanvasData):
        """Canvas 데이터로부터 선호도 학습"""
        # 색상 선호도 업데이트
        colors_used = self._extract_colors(canvas_data)
        for color in colors_used:
            self.color_preferences[color] = self.color_preferences.get(color, 0) + 1
        
        # 레이아웃 패턴 업데이트
        layout_pattern = self._analyze_layout_pattern(canvas_data)
        self.layout_patterns[layout_pattern] = self.layout_patterns.get(layout_pattern, 0) + 1
        
        self.last_updated = datetime.utcnow()

    def _extract_colors(self, canvas_data: CanvasData) -> List[str]:
        """Canvas에서 사용된 색상 추출"""
        colors = []
        for layer in canvas_data.stage.layers:
            for node in layer.nodes:
                if node.konva_attrs:
                    fill = node.konva_attrs.get("fill")
                    stroke = node.konva_attrs.get("stroke")
                    if fill and fill not in ["transparent", "none"]:
                        colors.append(fill)
                    if stroke and stroke not in ["transparent", "none"]:
                        colors.append(stroke)
        return colors

    def _analyze_layout_pattern(self, canvas_data: CanvasData) -> str:
        """레이아웃 패턴 분석"""
        # 간단한 패턴 분류 (추후 확장 가능)
        total_elements = sum(len(layer.nodes) for layer in canvas_data.stage.layers)
        
        if total_elements <= 3:
            return "minimal"
        elif total_elements <= 7:
            return "balanced"
        else:
            return "complex"

class CanvasAIAdvisor:
    """Canvas AI 어드바이저"""
    
    def __init__(self):
        self.user_preferences = {}  # user_id -> UserPreference
        self.suggestion_cache = {}  # canvas_id -> suggestions with TTL
        self.performance_metrics = {
            "suggestions_generated": 0,
            "suggestions_accepted": 0,
            "suggestions_rejected": 0,
            "user_satisfaction_score": 0.0
        }

    async def analyze_and_suggest(
        self, 
        canvas_data: CanvasData,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Canvas 분석 및 제안 생성"""
        try:
            # 캐시 확인
            cache_key = f"{canvas_data.id}_{hash(str(canvas_data.updated_at))}"
            if cache_key in self.suggestion_cache:
                cached_result = self.suggestion_cache[cache_key]
                if datetime.utcnow() - cached_result["generated_at"] < timedelta(minutes=5):
                    return cached_result["suggestions"]

            # 사용자 선호도 로드
            user_pref = self._get_user_preference(user_id)
            user_pref.update_from_canvas(canvas_data)

            # 기본 레이아웃 분석
            layout_analysis = await ai_layout_engine.analyze_canvas_elements(canvas_data)
            
            # 다양한 제안 생성
            suggestions = []
            
            # 1. 레이아웃 최적화 제안
            layout_suggestions = await self._generate_layout_suggestions(
                canvas_data, layout_analysis, user_pref, context
            )
            suggestions.extend(layout_suggestions)
            
            # 2. 정렬 개선 제안
            alignment_suggestions = await self._generate_alignment_suggestions(
                canvas_data, layout_analysis
            )
            suggestions.extend(alignment_suggestions)
            
            # 3. 색상 조화 제안
            color_suggestions = await self._generate_color_suggestions(
                canvas_data, layout_analysis, user_pref
            )
            suggestions.extend(color_suggestions)
            
            # 4. 타이포그래피 제안
            typography_suggestions = await self._generate_typography_suggestions(
                canvas_data, layout_analysis
            )
            suggestions.extend(typography_suggestions)
            
            # 5. 템플릿 제안
            template_suggestions = await self._generate_template_suggestions(
                canvas_data, context
            )
            suggestions.extend(template_suggestions)
            
            # 6. 컨텍스트 기반 제안 (LLM)
            contextual_suggestions = await self._generate_contextual_suggestions(
                canvas_data, layout_analysis, context
            )
            suggestions.extend(contextual_suggestions)
            
            # 우선순위별 정렬 및 중복 제거
            suggestions = self._prioritize_and_deduplicate(suggestions, user_pref)
            
            result = {
                "suggestions": suggestions,
                "analysis_summary": self._create_analysis_summary(layout_analysis),
                "user_insights": self._create_user_insights(user_pref),
                "performance_score": self._calculate_performance_score(layout_analysis),
                "generated_at": datetime.utcnow().isoformat(),
                "suggestion_count": len(suggestions)
            }
            
            # 캐시 저장
            self.suggestion_cache[cache_key] = {
                "suggestions": result,
                "generated_at": datetime.utcnow()
            }
            
            self.performance_metrics["suggestions_generated"] += len(suggestions)
            
            return result
            
        except Exception as e:
            logger.error(f"AI 제안 생성 실패: {str(e)}")
            return {
                "suggestions": [],
                "error": f"제안 생성 중 오류 발생: {str(e)}",
                "generated_at": datetime.utcnow().isoformat(),
                "suggestion_count": 0
            }

    def _get_user_preference(self, user_id: str) -> UserPreference:
        """사용자 선호도 가져오기"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreference(user_id)
        return self.user_preferences[user_id]

    async def _generate_layout_suggestions(
        self, 
        canvas_data: CanvasData, 
        analysis: Dict[str, Any], 
        user_pref: UserPreference,
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """레이아웃 최적화 제안"""
        suggestions = []
        
        # 균형 문제 감지
        composition = analysis.get("composition", {})
        distribution = composition.get("distribution", {})
        balance_score = distribution.get("balance_score", 0.5)
        
        if balance_score < 0.4:
            suggestions.append({
                "id": f"layout_balance_{canvas_data.id}",
                "type": SuggestionType.LAYOUT_OPTIMIZATION,
                "priority": SuggestionPriority.HIGH,
                "title": "레이아웃 균형 개선",
                "description": "요소들의 무게중심이 치우쳐 있어 시각적 불안정감을 줍니다. 요소들을 재배치하여 균형을 맞춰보세요.",
                "action": "rebalance_elements",
                "expected_improvement": "시각적 안정감 향상",
                "confidence": 0.85,
                "auto_fix_available": True,
                "preview_changes": await self._generate_balance_preview(canvas_data)
            })

        # 밀도 문제 감지
        spacing_analysis = composition.get("spacing_density", {})
        density = spacing_analysis.get("density", "balanced")
        
        if density == "overcrowded":
            suggestions.append({
                "id": f"layout_density_{canvas_data.id}",
                "type": SuggestionType.SPACING_ADJUSTMENT,
                "priority": SuggestionPriority.MEDIUM,
                "title": "여백 확보",
                "description": "요소들이 너무 밀집되어 있습니다. 적절한 여백을 확보하여 가독성을 높여보세요.",
                "action": "increase_spacing",
                "expected_improvement": "가독성 및 시각적 편안함 향상",
                "confidence": 0.78,
                "auto_fix_available": True
            })
        elif density == "sparse":
            suggestions.append({
                "id": f"layout_fill_{canvas_data.id}",
                "type": SuggestionType.LAYOUT_OPTIMIZATION,
                "priority": SuggestionPriority.LOW,
                "title": "공간 활용도 개선",
                "description": "캔버스에 빈 공간이 많습니다. 요소들을 더 효과적으로 배치해보세요.",
                "action": "optimize_space_usage",
                "expected_improvement": "공간 활용도 및 정보 밀도 향상",
                "confidence": 0.65,
                "auto_fix_available": True
            })
        
        return suggestions

    async def _generate_alignment_suggestions(
        self, 
        canvas_data: CanvasData, 
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """정렬 개선 제안"""
        suggestions = []
        
        composition = analysis.get("composition", {})
        grid_analysis = composition.get("grid_alignment", {})
        overall_score = grid_analysis.get("overall_score", 0.5)
        
        if overall_score < 0.6:
            suggestions.append({
                "id": f"alignment_{canvas_data.id}",
                "type": SuggestionType.ALIGNMENT_FIX,
                "priority": SuggestionPriority.HIGH,
                "title": "요소 정렬 개선",
                "description": "요소들이 일관된 정렬 없이 배치되어 있습니다. 그리드 라인에 맞춰 정렬하면 더 전문적인 느낌을 줄 수 있습니다.",
                "action": "align_to_grid",
                "expected_improvement": "전문적이고 정돈된 외관",
                "confidence": 0.82,
                "auto_fix_available": True,
                "fix_options": [
                    {"type": "left_align", "name": "좌측 정렬"},
                    {"type": "center_align", "name": "중앙 정렬"},
                    {"type": "distribute", "name": "균등 분배"}
                ]
            })
        
        return suggestions

    async def _generate_color_suggestions(
        self, 
        canvas_data: CanvasData, 
        analysis: Dict[str, Any], 
        user_pref: UserPreference
    ) -> List[Dict[str, Any]]:
        """색상 조화 제안"""
        suggestions = []
        
        composition = analysis.get("composition", {})
        color_analysis = composition.get("color_harmony", {})
        harmony_score = color_analysis.get("harmony_score", 0.5)
        color_count = color_analysis.get("color_count", 0)
        
        if harmony_score < 0.6:
            # 사용자 선호 색상 고려한 팔레트 제안
            preferred_colors = sorted(
                user_pref.color_preferences.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
            
            suggestions.append({
                "id": f"color_harmony_{canvas_data.id}",
                "type": SuggestionType.COLOR_HARMONY,
                "priority": SuggestionPriority.MEDIUM,
                "title": "색상 조화 개선",
                "description": f"현재 {color_count}개의 색상이 사용되어 시각적 혼란을 줄 수 있습니다. 조화로운 색상 팔레트를 적용해보세요.",
                "action": "apply_color_palette",
                "expected_improvement": "시각적 일관성 및 브랜드 인상 향상",
                "confidence": 0.75,
                "auto_fix_available": True,
                "palette_options": [
                    {
                        "name": "사용자 선호 팔레트",
                        "colors": [color for color, _ in preferred_colors]
                    },
                    {
                        "name": "모던 블루",
                        "colors": ["#3498db", "#2980b9", "#ecf0f1", "#2c3e50"]
                    },
                    {
                        "name": "웜 선셋",
                        "colors": ["#ff6b6b", "#ee5a24", "#feca57", "#2d3436"]
                    }
                ]
            })
        
        return suggestions

    async def _generate_typography_suggestions(
        self, 
        canvas_data: CanvasData, 
        analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """타이포그래피 제안"""
        suggestions = []
        
        # 텍스트 요소들 분석
        text_elements = []
        for layer in canvas_data.stage.layers:
            for node in layer.nodes:
                if node.node_type == "text":
                    text_elements.append(node)
        
        if not text_elements:
            return suggestions
        
        # 폰트 크기 일관성 확인
        font_sizes = []
        for element in text_elements:
            font_size = element.konva_attrs.get("fontSize", 14)
            font_sizes.append(font_size)
        
        # 너무 작은 텍스트 감지
        small_texts = [size for size in font_sizes if size < 12]
        if small_texts:
            suggestions.append({
                "id": f"typography_size_{canvas_data.id}",
                "type": SuggestionType.TYPOGRAPHY_IMPROVEMENT,
                "priority": SuggestionPriority.HIGH,
                "title": "텍스트 크기 개선",
                "description": f"{len(small_texts)}개의 텍스트가 너무 작아 가독성이 떨어집니다. 최소 12px 이상으로 조정하는 것을 권장합니다.",
                "action": "increase_font_size",
                "expected_improvement": "가독성 및 접근성 향상",
                "confidence": 0.90,
                "auto_fix_available": True
            })
        
        # 폰트 패밀리 일관성 확인
        font_families = set()
        for element in text_elements:
            font_family = element.konva_attrs.get("fontFamily", "Arial")
            font_families.add(font_family)
        
        if len(font_families) > 3:
            suggestions.append({
                "id": f"typography_consistency_{canvas_data.id}",
                "type": SuggestionType.TYPOGRAPHY_IMPROVEMENT,
                "priority": SuggestionPriority.MEDIUM,
                "title": "폰트 일관성 개선",
                "description": f"{len(font_families)}가지 폰트가 사용되어 일관성이 부족합니다. 2-3가지 폰트로 통일하는 것을 권장합니다.",
                "action": "unify_typography",
                "expected_improvement": "시각적 일관성 및 전문성 향상",
                "confidence": 0.73,
                "auto_fix_available": True,
                "typography_sets": list(template_engine.typography_sets.keys())
            })
        
        return suggestions

    async def _generate_template_suggestions(
        self, 
        canvas_data: CanvasData, 
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """템플릿 제안"""
        suggestions = []
        
        if not context:
            return suggestions
        
        # 현재 Canvas의 특성 분석
        total_elements = sum(len(layer.nodes) for layer in canvas_data.stage.layers)
        canvas_ratio = canvas_data.stage.width / canvas_data.stage.height
        
        # 적합한 템플릿 검색
        if canvas_ratio > 1.5:  # 가로형
            category = "presentation"
        elif 0.8 <= canvas_ratio <= 1.2:  # 정사각형
            category = "social_media"
        else:  # 세로형
            category = "poster"
        
        if total_elements < 5:  # 요소가 적으면 템플릿 추천
            suggestions.append({
                "id": f"template_{canvas_data.id}",
                "type": SuggestionType.TEMPLATE_SUGGESTION,
                "priority": SuggestionPriority.LOW,
                "title": f"{category.title()} 템플릿 적용",
                "description": "현재 Canvas에 적합한 전문 템플릿을 적용하여 더 완성도 높은 디자인을 만들어보세요.",
                "action": "apply_template",
                "expected_improvement": "전문적인 디자인 완성도",
                "confidence": 0.65,
                "auto_fix_available": False,
                "template_recommendations": await self._get_suitable_templates(canvas_data, category)
            })
        
        return suggestions

    async def _generate_contextual_suggestions(
        self, 
        canvas_data: CanvasData, 
        analysis: Dict[str, Any], 
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """컨텍스트 기반 LLM 제안"""
        suggestions = []
        
        try:
            # LLM에게 컨텍스트 기반 제안 요청
            context_prompt = f"""
당신은 전문 UI/UX 디자이너입니다. 다음 Canvas와 컨텍스트를 분석하여 구체적인 개선 제안을 해주세요.

## Canvas 정보
- 크기: {canvas_data.stage.width}x{canvas_data.stage.height}
- 요소 수: {sum(len(layer.nodes) for layer in canvas_data.stage.layers)}
- 분석 점수: {analysis.get('composition', {}).get('design_principles_score', {})}

## 컨텍스트
{json.dumps(context or {}, ensure_ascii=False, indent=2)}

## 요청사항
Canvas의 목적과 대상 사용자를 고려하여 3가지 핵심 개선사항을 JSON 형식으로 제안해주세요.

형식:
{{
    "suggestions": [
        {{
            "title": "제안 제목",
            "description": "상세 설명",
            "priority": "high/medium/low",
            "reasoning": "제안 이유",
            "implementation": "구현 방법"
        }}
    ]
}}
"""
            
            llm_response = await llm_router.route_request(
                messages=[{"role": "user", "content": context_prompt}],
                model_preference="claude",
                temperature=0.4
            )
            
            try:
                llm_suggestions = json.loads(llm_response.response)
                
                for i, suggestion in enumerate(llm_suggestions.get("suggestions", [])):
                    suggestions.append({
                        "id": f"contextual_{canvas_data.id}_{i}",
                        "type": SuggestionType.CONTENT_OPTIMIZATION,
                        "priority": getattr(SuggestionPriority, suggestion.get("priority", "medium").upper(), SuggestionPriority.MEDIUM),
                        "title": suggestion.get("title", "컨텍스트 기반 제안"),
                        "description": suggestion.get("description", ""),
                        "action": "manual_review",
                        "expected_improvement": suggestion.get("reasoning", ""),
                        "confidence": 0.70,
                        "auto_fix_available": False,
                        "implementation_guide": suggestion.get("implementation", "")
                    })
                    
            except json.JSONDecodeError:
                logger.warning("LLM 응답을 JSON으로 파싱할 수 없습니다")
                
        except Exception as e:
            logger.error(f"컨텍스트 제안 생성 실패: {str(e)}")
        
        return suggestions

    def _prioritize_and_deduplicate(
        self, 
        suggestions: List[Dict[str, Any]], 
        user_pref: UserPreference
    ) -> List[Dict[str, Any]]:
        """제안 우선순위 정렬 및 중복 제거"""
        
        # 중복 제거 (같은 action을 가진 제안들)
        seen_actions = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            action = suggestion.get("action")
            if action not in seen_actions:
                seen_actions.add(action)
                unique_suggestions.append(suggestion)
        
        # 우선순위 정렬
        priority_order = {
            SuggestionPriority.CRITICAL: 0,
            SuggestionPriority.HIGH: 1,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 3,
            SuggestionPriority.OPTIONAL: 4
        }
        
        unique_suggestions.sort(
            key=lambda x: (
                priority_order.get(x.get("priority", SuggestionPriority.MEDIUM), 2),
                -x.get("confidence", 0.5)
            )
        )
        
        return unique_suggestions[:8]  # 최대 8개 제안

    async def _generate_balance_preview(self, canvas_data: CanvasData) -> Dict[str, Any]:
        """균형 개선 미리보기"""
        # 간단한 미리보기 데이터 생성
        return {
            "description": "요소들을 캔버스 중앙 기준으로 재배치",
            "affected_elements": sum(len(layer.nodes) for layer in canvas_data.stage.layers),
            "estimated_improvement": "+35% 시각적 균형"
        }

    async def _get_suitable_templates(self, canvas_data: CanvasData, category: str) -> List[Dict[str, Any]]:
        """적합한 템플릿 추천"""
        # 템플릿 엔진에서 추천 템플릿 가져오기
        templates = await template_engine.get_recommended_templates(
            category=category,
            canvas_size={"width": canvas_data.stage.width, "height": canvas_data.stage.height}
        )
        
        return [
            {
                "template_id": template["template_id"],
                "name": template["template"]["name"],
                "preview": template_engine.get_template_preview(template["template_id"])
            }
            for template in templates[:3]  # 상위 3개만
        ]

    def _create_analysis_summary(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """분석 요약 생성"""
        composition = analysis.get("composition", {})
        
        return {
            "overall_quality": self._calculate_overall_quality(composition),
            "key_strengths": self._identify_strengths(composition),
            "main_issues": self._identify_issues(composition),
            "improvement_potential": self._estimate_improvement_potential(composition)
        }

    def _create_user_insights(self, user_pref: UserPreference) -> Dict[str, Any]:
        """사용자 인사이트 생성"""
        top_colors = sorted(
            user_pref.color_preferences.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        top_patterns = sorted(
            user_pref.layout_patterns.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:2]
        
        return {
            "preferred_colors": [color for color, _ in top_colors],
            "preferred_layouts": [pattern for pattern, _ in top_patterns],
            "design_style": self._infer_user_style(user_pref),
            "experience_level": self._estimate_experience_level(user_pref)
        }

    def _calculate_performance_score(self, analysis: Dict[str, Any]) -> float:
        """성능 점수 계산"""
        composition = analysis.get("composition", {})
        scores = composition.get("design_principles_score", {})
        
        if not scores:
            return 0.5
        
        return sum(scores.values()) / len(scores)

    def _calculate_overall_quality(self, composition: Dict[str, Any]) -> str:
        """전체 품질 평가"""
        scores = composition.get("design_principles_score", {})
        if not scores:
            return "보통"
        
        avg_score = sum(scores.values()) / len(scores)
        
        if avg_score >= 0.8:
            return "우수"
        elif avg_score >= 0.6:
            return "양호"
        elif avg_score >= 0.4:
            return "보통"
        else:
            return "개선 필요"

    def _identify_strengths(self, composition: Dict[str, Any]) -> List[str]:
        """강점 식별"""
        strengths = []
        scores = composition.get("design_principles_score", {})
        
        for principle, score in scores.items():
            if score >= 0.7:
                strengths.append(principle.replace("_", " ").title())
        
        return strengths or ["기본적인 구성"]

    def _identify_issues(self, composition: Dict[str, Any]) -> List[str]:
        """문제점 식별"""
        issues = []
        scores = composition.get("design_principles_score", {})
        
        for principle, score in scores.items():
            if score < 0.4:
                issues.append(principle.replace("_", " ").title())
        
        return issues or ["특별한 문제 없음"]

    def _estimate_improvement_potential(self, composition: Dict[str, Any]) -> str:
        """개선 잠재력 평가"""
        scores = composition.get("design_principles_score", {})
        if not scores:
            return "보통"
        
        min_score = min(scores.values())
        
        if min_score < 0.3:
            return "높음"
        elif min_score < 0.6:
            return "보통"
        else:
            return "낮음"

    def _infer_user_style(self, user_pref: UserPreference) -> str:
        """사용자 스타일 추론"""
        if not user_pref.layout_patterns:
            return "탐색중"
        
        dominant_pattern = max(user_pref.layout_patterns.items(), key=lambda x: x[1])[0]
        
        style_map = {
            "minimal": "미니멀",
            "balanced": "균형잡힌",
            "complex": "역동적"
        }
        
        return style_map.get(dominant_pattern, "개성적")

    def _estimate_experience_level(self, user_pref: UserPreference) -> str:
        """경험 수준 추정"""
        total_usage = sum(user_pref.layout_patterns.values())
        
        if total_usage < 5:
            return "초보"
        elif total_usage < 20:
            return "중급"
        else:
            return "고급"

    async def record_feedback(
        self, 
        user_id: str, 
        suggestion_id: str, 
        feedback: str,
        rating: Optional[int] = None
    ):
        """사용자 피드백 기록"""
        user_pref = self._get_user_preference(user_id)
        
        user_pref.suggestion_feedback[suggestion_id] = {
            "feedback": feedback,
            "rating": rating,
            "timestamp": datetime.utcnow()
        }
        
        # 성능 메트릭 업데이트
        if feedback == "accepted":
            self.performance_metrics["suggestions_accepted"] += 1
        elif feedback == "rejected":
            self.performance_metrics["suggestions_rejected"] += 1
        
        if rating:
            current_score = self.performance_metrics["user_satisfaction_score"]
            total_ratings = self.performance_metrics.get("total_ratings", 0)
            
            new_score = ((current_score * total_ratings) + rating) / (total_ratings + 1)
            self.performance_metrics["user_satisfaction_score"] = new_score
            self.performance_metrics["total_ratings"] = total_ratings + 1

# 전역 인스턴스
ai_advisor = CanvasAIAdvisor()

# 공개 함수들
async def get_canvas_suggestions(
    canvas_data: CanvasData,
    user_id: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Canvas에 대한 AI 제안 생성"""
    return await ai_advisor.analyze_and_suggest(canvas_data, user_id, context)

async def record_user_feedback(
    user_id: str, 
    suggestion_id: str, 
    feedback: str,
    rating: Optional[int] = None
):
    """사용자 피드백 기록"""
    await ai_advisor.record_feedback(user_id, suggestion_id, feedback, rating)

def get_advisor_performance() -> Dict[str, Any]:
    """어드바이저 성능 메트릭"""
    return ai_advisor.performance_metrics.copy()