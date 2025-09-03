# Canvas AI 레이아웃 API 엔드포인트 v1.0
# 지능형 레이아웃 시스템 API

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional
from uuid import UUID
import logging

from app.models.canvas_models import (
    CanvasData,
    CreateCanvasRequest,
    UpdateCanvasRequest,
    CanvasOperationRequest,
    CanvasOperationResult
)
from app.services.canvas_ai_layout_service import (
    analyze_canvas_layout,
    get_layout_suggestions,
    apply_auto_layout_fixes
)
from app.services.canvas_smart_layout_engine import (
    generate_smart_grid,
    auto_align_elements,
    optimize_layout,
    GridType,
    AlignmentStrategy,
    LayoutOptimization
)
from app.services.canvas_template_engine import (
    get_recommended_templates,
    apply_template,
    get_available_templates,
    get_color_palettes,
    get_typography_sets,
    TemplateCategory,
    IndustryType,
    LayoutStyle
)
from app.services.canvas_ai_advisor_service import (
    get_canvas_suggestions,
    record_user_feedback,
    get_advisor_performance
)
from app.core.auth import get_current_user
from app.db.session import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/canvas/ai-layout", tags=["Canvas AI Layout"])

# ===== AI 레이아웃 분석 엔드포인트 =====

@router.post("/analyze")
async def analyze_canvas_layout_endpoint(
    canvas_data: CanvasData,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Canvas 레이아웃 AI 분석"""
    try:
        analysis_result = await analyze_canvas_layout(canvas_data)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "canvas_id": str(canvas_data.id),
                    "analysis": analysis_result,
                    "timestamp": analysis_result.get("analyzed_at")
                },
                "message": "Canvas 레이아웃 분석이 완료되었습니다."
            }
        )
        
    except Exception as e:
        logger.error(f"Canvas 분석 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"레이아웃 분석 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/suggestions")
async def get_ai_suggestions_endpoint(
    request: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AI 기반 레이아웃 제안"""
    try:
        canvas_data = CanvasData(**request.get("canvas_data", {}))
        context = request.get("context", {})
        user_id = str(current_user.id)
        
        suggestions = await get_canvas_suggestions(canvas_data, user_id, context)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "canvas_id": str(canvas_data.id),
                    "suggestions": suggestions.get("suggestions", []),
                    "analysis_summary": suggestions.get("analysis_summary", {}),
                    "user_insights": suggestions.get("user_insights", {}),
                    "performance_score": suggestions.get("performance_score", 0.5),
                    "suggestion_count": suggestions.get("suggestion_count", 0)
                },
                "message": f"{suggestions.get('suggestion_count', 0)}개의 개선 제안이 생성되었습니다."
            }
        )
        
    except Exception as e:
        logger.error(f"AI 제안 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"AI 제안 생성 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/suggestions/{suggestion_id}/feedback")
async def record_suggestion_feedback(
    suggestion_id: str,
    feedback_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """제안에 대한 사용자 피드백 기록"""
    try:
        user_id = str(current_user.id)
        feedback = feedback_data.get("feedback")  # "accepted", "rejected", "modified"
        rating = feedback_data.get("rating")  # 1-5 점수
        
        await record_user_feedback(user_id, suggestion_id, feedback, rating)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "피드백이 성공적으로 기록되었습니다."
            }
        )
        
    except Exception as e:
        logger.error(f"피드백 기록 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"피드백 기록 중 오류가 발생했습니다: {str(e)}"
        )

# ===== 스마트 그리드 시스템 엔드포인트 =====

@router.post("/grid/generate")
async def generate_grid_endpoint(
    request: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """스마트 그리드 생성"""
    try:
        stage_data = request.get("stage", {})
        grid_type = request.get("grid_type", GridType.DYNAMIC.value)
        
        from app.models.canvas_models import KonvaStageData
        stage = KonvaStageData(**stage_data)
        
        grid_result = await generate_smart_grid(stage, GridType(grid_type))
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "grid": grid_result,
                    "grid_type": grid_type
                },
                "message": f"{grid_type} 그리드가 생성되었습니다."
            }
        )
        
    except Exception as e:
        logger.error(f"그리드 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"그리드 생성 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/align")
async def auto_align_endpoint(
    request: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """요소 자동 정렬"""
    try:
        from app.models.canvas_models import KonvaNodeData
        
        elements_data = request.get("elements", [])
        grid = request.get("grid", {})
        strategy = request.get("strategy", AlignmentStrategy.AUTO_DETECT.value)
        
        elements = [KonvaNodeData(**elem_data) for elem_data in elements_data]
        
        aligned_elements = await auto_align_elements(
            elements, 
            grid, 
            AlignmentStrategy(strategy)
        )
        
        # KonvaNodeData를 dict로 변환
        aligned_data = [elem.model_dump() for elem in aligned_elements]
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "aligned_elements": aligned_data,
                    "strategy": strategy,
                    "changes_applied": len(aligned_elements)
                },
                "message": f"{len(aligned_elements)}개 요소가 정렬되었습니다."
            }
        )
        
    except Exception as e:
        logger.error(f"자동 정렬 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"자동 정렬 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/optimize")
async def optimize_layout_endpoint(
    request: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """레이아웃 최적화"""
    try:
        from app.models.canvas_models import KonvaNodeData, KonvaStageData
        
        elements_data = request.get("elements", [])
        stage_data = request.get("stage", {})
        optimization_type = request.get("optimization_type", LayoutOptimization.BALANCE_COMPOSITION.value)
        
        elements = [KonvaNodeData(**elem_data) for elem_data in elements_data]
        stage = KonvaStageData(**stage_data)
        
        optimized_elements = await optimize_layout(
            elements, 
            stage, 
            LayoutOptimization(optimization_type)
        )
        
        # KonvaNodeData를 dict로 변환
        optimized_data = [elem.model_dump() for elem in optimized_elements]
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "optimized_elements": optimized_data,
                    "optimization_type": optimization_type,
                    "changes_applied": len(optimized_elements)
                },
                "message": f"{optimization_type} 최적화가 완료되었습니다."
            }
        )
        
    except Exception as e:
        logger.error(f"레이아웃 최적화 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"레이아웃 최적화 중 오류가 발생했습니다: {str(e)}"
        )

# ===== 템플릿 시스템 엔드포인트 =====

@router.get("/templates")
async def get_templates_endpoint(
    category: Optional[str] = None,
    industry: Optional[str] = None,
    style: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """사용 가능한 템플릿 목록"""
    try:
        # 필터링 조건 처리
        category_filter = TemplateCategory(category) if category else None
        industry_filter = IndustryType(industry) if industry else None
        style_filter = LayoutStyle(style) if style else None
        
        if any([category_filter, industry_filter, style_filter]):
            # 추천 템플릿 검색
            templates = await get_recommended_templates(
                category_filter, 
                industry_filter, 
                style_filter
            )
            
            template_data = [
                {
                    "template_id": template["template_id"],
                    "match_score": template["match_score"],
                    **template["template"]
                }
                for template in templates
            ]
        else:
            # 전체 템플릿 목록
            template_data = get_available_templates()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "templates": template_data,
                    "total_count": len(template_data),
                    "filters_applied": {
                        "category": category,
                        "industry": industry,
                        "style": style
                    }
                },
                "message": f"{len(template_data)}개의 템플릿을 찾았습니다."
            }
        )
        
    except Exception as e:
        logger.error(f"템플릿 목록 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"템플릿 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/templates/{template_id}/apply")
async def apply_template_endpoint(
    template_id: str,
    request: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """템플릿 적용"""
    try:
        content_data = request.get("content_data", {})
        customizations = request.get("customizations", {})
        
        # workspace_id 추가 (현재 사용자 기준)
        content_data["workspace_id"] = str(current_user.id)
        
        canvas_result = await apply_template(template_id, content_data, customizations)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "canvas": canvas_result.model_dump(),
                    "template_id": template_id,
                    "applied_customizations": customizations
                },
                "message": "템플릿이 성공적으로 적용되었습니다."
            }
        )
        
    except Exception as e:
        logger.error(f"템플릿 적용 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"템플릿 적용 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/templates/resources")
async def get_template_resources(
    current_user = Depends(get_current_user)
):
    """템플릿 리소스 (색상 팔레트, 타이포그래피 등)"""
    try:
        color_palettes = get_color_palettes()
        typography_sets = get_typography_sets()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "color_palettes": color_palettes,
                    "typography_sets": typography_sets,
                    "template_categories": [category.value for category in TemplateCategory],
                    "industry_types": [industry.value for industry in IndustryType],
                    "layout_styles": [style.value for style in LayoutStyle]
                },
                "message": "템플릿 리소스 정보를 조회했습니다."
            }
        )
        
    except Exception as e:
        logger.error(f"템플릿 리소스 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"리소스 조회 중 오류가 발생했습니다: {str(e)}"
        )

# ===== 자동 수정 엔드포인트 =====

@router.post("/auto-fix")
async def apply_auto_fixes_endpoint(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """자동 레이아웃 수정 적용"""
    try:
        canvas_data = CanvasData(**request.get("canvas_data", {}))
        suggestion_ids = request.get("suggestion_ids", [])
        
        # 백그라운드에서 자동 수정 적용
        background_tasks.add_task(
            apply_auto_layout_fixes,
            canvas_data,
            suggestion_ids
        )
        
        return JSONResponse(
            status_code=202,
            content={
                "success": True,
                "data": {
                    "canvas_id": str(canvas_data.id),
                    "suggestion_ids": suggestion_ids,
                    "status": "processing"
                },
                "message": f"{len(suggestion_ids)}개의 자동 수정이 적용 중입니다."
            }
        )
        
    except Exception as e:
        logger.error(f"자동 수정 적용 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"자동 수정 적용 중 오류가 발생했습니다: {str(e)}"
        )

# ===== 성능 및 통계 엔드포인트 =====

@router.get("/performance")
async def get_ai_performance(
    current_user = Depends(get_current_user)
):
    """AI 시스템 성능 지표"""
    try:
        performance_data = get_advisor_performance()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "performance_metrics": performance_data,
                    "timestamp": "2024-12-31T00:00:00Z"  # 현재 시간으로 대체 필요
                },
                "message": "AI 시스템 성능 지표를 조회했습니다."
            }
        )
        
    except Exception as e:
        logger.error(f"성능 지표 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"성능 지표 조회 중 오류가 발생했습니다: {str(e)}"
        )

# ===== 실시간 레이아웃 힌트 엔드포인트 =====

@router.post("/hints")
async def get_realtime_hints(
    request: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """실시간 레이아웃 힌트"""
    try:
        canvas_data = CanvasData(**request.get("canvas_data", {}))
        current_operation = request.get("current_operation", {})
        
        # 현재 작업 컨텍스트를 고려한 빠른 힌트 생성
        hints = []
        
        # 요소 추가 중이라면 최적 위치 제안
        if current_operation.get("type") == "add_element":
            hints.append({
                "type": "positioning",
                "title": "최적 위치 제안",
                "description": "황금비율 지점(우측 하단)에 배치하면 시각적 주목도가 높아집니다.",
                "position": {
                    "x": canvas_data.stage.width / 1.618,
                    "y": canvas_data.stage.height / 1.618
                }
            })
        
        # 텍스트 편집 중이라면 가독성 힌트
        elif current_operation.get("type") == "edit_text":
            hints.append({
                "type": "typography",
                "title": "가독성 개선",
                "description": "현재 폰트 크기가 작습니다. 최소 14px 이상을 권장합니다.",
                "suggested_font_size": 16
            })
        
        # 색상 변경 중이라면 조화 힌트
        elif current_operation.get("type") == "change_color":
            hints.append({
                "type": "color_harmony",
                "title": "색상 조화",
                "description": "현재 색상과 조화로운 색상을 제안합니다.",
                "suggested_colors": ["#3498db", "#2980b9", "#1abc9c"]
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "hints": hints,
                    "context": current_operation.get("type", "unknown")
                },
                "message": f"{len(hints)}개의 실시간 힌트를 제공합니다."
            }
        )
        
    except Exception as e:
        logger.error(f"실시간 힌트 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"힌트 생성 중 오류가 발생했습니다: {str(e)}"
        )

# ===== 사용자 맞춤 AI 엔드포인트 =====

@router.get("/personalization")
async def get_user_personalization(
    current_user = Depends(get_current_user)
):
    """사용자 맞춤 AI 설정 및 인사이트"""
    try:
        # 사용자별 선호도 및 패턴 분석 (추후 구현)
        user_id = str(current_user.id)
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {
                    "user_id": user_id,
                    "design_preferences": {
                        "preferred_styles": ["modern", "minimal"],
                        "color_preferences": ["#3498db", "#2c3e50"],
                        "layout_patterns": ["balanced", "grid-based"]
                    },
                    "experience_level": "intermediate",
                    "personalized_suggestions_enabled": True
                },
                "message": "사용자 맞춤 AI 설정을 조회했습니다."
            }
        )
        
    except Exception as e:
        logger.error(f"개인화 설정 조회 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"개인화 설정 조회 중 오류가 발생했습니다: {str(e)}"
        )