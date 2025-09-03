"""
API v1 메인 라우터
"""

from fastapi import APIRouter

from app.api.v1 import chat, agents, health, files, workspaces, image_generation, image_sessions, canvas_telemetry, simple_image_history, canvas, image_series, canvas_export, canvas_share, canvas_ai_layout, routing
from app.api.v1.endpoints import conversation_history, performance, feedback

api_router = APIRouter()

# 각 기능별 라우터 포함
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(image_generation.router, prefix="/images", tags=["image-generation"])
api_router.include_router(image_sessions.router, prefix="/image-sessions", tags=["image-sessions"])
api_router.include_router(simple_image_history.router, prefix="", tags=["simple-image-history"])
api_router.include_router(conversation_history.router, prefix="/history", tags=["conversation-history"])
api_router.include_router(performance.router, prefix="/performance", tags=["performance"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(canvas_telemetry.router, tags=["canvas-telemetry"])
api_router.include_router(canvas.router, prefix="/canvas", tags=["canvas"])
api_router.include_router(canvas_export.router, prefix="/canvas-export", tags=["canvas-export"])
api_router.include_router(canvas_share.router, tags=["canvas-share"])
api_router.include_router(canvas_ai_layout.router, tags=["canvas-ai-layout"])
api_router.include_router(image_series.router, prefix="/image-series", tags=["image-series"])
api_router.include_router(routing.router, prefix="/routing", tags=["intelligent-routing"])