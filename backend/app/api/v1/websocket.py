"""
WebSocket 엔드포인트
실시간 채팅 스트리밍 지원
"""

from typing import Dict, Optional
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, AsyncSessionLocal
from app.db.models.conversation import MessageRole
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.services.agent_service import AgentService
from app.core.config import settings

router = APIRouter()


class ConnectionManager:
    """WebSocket 연결 관리"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """클라이언트 연결"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        """클라이언트 연결 해제"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_message(self, client_id: str, message: dict):
        """특정 클라이언트에 메시지 전송"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        """모든 클라이언트에 메시지 브로드캐스트"""
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to {client_id}: {e}")


# 전역 연결 관리자
manager = ConnectionManager()


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: str,
    user_id: Optional[str] = Query(None),
):
    """채팅 WebSocket 엔드포인트"""
    
    # Mock 인증 모드에서는 기본 사용자 ID 사용
    if settings.MOCK_AUTH_ENABLED and not user_id:
        user_id = settings.MOCK_USER_ID
    
    client_id = f"{user_id}:{conversation_id}"
    await manager.connect(websocket, client_id)
    
    # 데이터베이스 세션
    async with AsyncSessionLocal() as db:
        conversation_repo = ConversationRepository(db)
        message_repo = MessageRepository(db)
        agent_service = AgentService()
        
        try:
            # 대화 확인 또는 생성
            conversation = await conversation_repo.get(conversation_id)
            if not conversation:
                conversation = await conversation_repo.create_conversation(
                    user_id=user_id,
                    title=f"채팅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
            
            # 연결 성공 메시지
            await manager.send_message(client_id, {
                "type": "connection",
                "status": "connected",
                "conversation_id": str(conversation.id)
            })
            
            while True:
                # 클라이언트로부터 메시지 수신
                data = await websocket.receive_json()
                
                if data.get("type") == "ping":
                    # 핑 응답
                    await manager.send_message(client_id, {"type": "pong"})
                    continue
                
                if data.get("type") == "chat":
                    # 사용자 메시지 저장
                    user_message = await message_repo.create_message(
                        conversation_id=conversation.id,
                        role=MessageRole.USER,
                        content=data.get("content", ""),
                        metadata=data.get("metadata", {})
                    )
                    
                    # 메시지 수신 확인
                    await manager.send_message(client_id, {
                        "type": "message_received",
                        "message_id": str(user_message.id),
                        "timestamp": user_message.created_at.isoformat()
                    })
                    
                    # AI 응답 생성 시작
                    await manager.send_message(client_id, {
                        "type": "assistant_start",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # 스트리밍 응답
                    full_response = ""
                    async for chunk in agent_service.stream_response(
                        query=data.get("content", ""),
                        model=data.get("model", "claude-3-haiku"),
                        agent_type=data.get("agent_type", "general"),
                        conversation_id=str(conversation.id)
                    ):
                        full_response += chunk
                        
                        # 청크 전송
                        await manager.send_message(client_id, {
                            "type": "assistant_chunk",
                            "content": chunk,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    # AI 메시지 저장
                    assistant_message = await message_repo.create_message(
                        conversation_id=conversation.id,
                        role=MessageRole.ASSISTANT,
                        content=full_response,
                        model=data.get("model", "claude-3-haiku")
                    )
                    
                    # 응답 완료
                    await manager.send_message(client_id, {
                        "type": "assistant_end",
                        "message_id": str(assistant_message.id),
                        "timestamp": assistant_message.created_at.isoformat()
                    })
        
        except WebSocketDisconnect:
            manager.disconnect(client_id)
            print(f"WebSocket disconnected: {client_id}")
        
        except Exception as e:
            print(f"WebSocket error: {e}")
            await manager.send_message(client_id, {
                "type": "error",
                "message": str(e)
            })
            manager.disconnect(client_id)


@router.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """시스템 상태 WebSocket 엔드포인트"""
    await websocket.accept()
    
    try:
        while True:
            # 주기적으로 상태 전송
            await websocket.send_json({
                "type": "status",
                "timestamp": datetime.utcnow().isoformat(),
                "connections": len(manager.active_connections),
                "status": "healthy"
            })
            await asyncio.sleep(10)  # 10초마다
            
    except WebSocketDisconnect:
        print("Status WebSocket disconnected")