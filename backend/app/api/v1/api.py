"""
API v1 메인 라우터
"""

from fastapi import APIRouter

from app.api.v1 import chat, agents, health

api_router = APIRouter()

# 각 기능별 라우터 포함
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])