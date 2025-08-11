"""
API v1 메인 라우터
"""

from fastapi import APIRouter

from app.api.v1 import chat, agents, health, websocket, files, workspaces, workspace_websocket
from app.api.v1.endpoints import conversation_history, performance, feedback

api_router = APIRouter()

# 각 기능별 라우터 포함
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(conversation_history.router, prefix="/history", tags=["conversation-history"])
api_router.include_router(performance.router, prefix="/performance", tags=["performance"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(websocket.router, tags=["websocket"])
api_router.include_router(workspace_websocket.router, tags=["workspace-websocket"])