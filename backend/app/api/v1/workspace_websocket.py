"""
워크스페이스 실시간 협업 WebSocket
"""

from typing import Dict, Any, List, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.websockets import WebSocketState
import json
import asyncio
import logging
import uuid
from datetime import datetime

from app.services.workspace_service import WorkspaceService
from app.db.session import get_db
from app.core.security import verify_token

logger = logging.getLogger(__name__)

router = APIRouter()


class WorkspaceConnectionManager:
    """워크스페이스 연결 관리자"""
    
    def __init__(self):
        # workspace_id -> {user_id: websocket}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # workspace_id -> {user_id: user_info}
        self.workspace_users: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # 편집 중인 아티팩트 추적: workspace_id -> {artifact_id: user_id}
        self.active_editors: Dict[str, Dict[str, str]] = {}
    
    async def connect(self, websocket: WebSocket, workspace_id: str, user_info: Dict[str, Any]):
        """새 사용자 연결"""
        await websocket.accept()
        
        user_id = user_info["id"]
        
        # 연결 정보 저장
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = {}
            self.workspace_users[workspace_id] = {}
            self.active_editors[workspace_id] = {}
        
        self.active_connections[workspace_id][user_id] = websocket
        self.workspace_users[workspace_id][user_id] = user_info
        
        # 다른 사용자들에게 새 사용자 접속 알림
        await self.broadcast_to_workspace(workspace_id, {
            "type": "user_joined",
            "data": {
                "user": user_info,
                "active_users": list(self.workspace_users[workspace_id].values()),
                "timestamp": datetime.utcnow().isoformat()
            }
        }, exclude_user=user_id)
        
        # 새 사용자에게 현재 상태 전송
        await self.send_personal_message(websocket, {
            "type": "workspace_state",
            "data": {
                "active_users": list(self.workspace_users[workspace_id].values()),
                "active_editors": self.active_editors[workspace_id],
                "timestamp": datetime.utcnow().isoformat()
            }
        })
        
        logger.info(f"사용자 {user_info['name']}이 워크스페이스 {workspace_id}에 연결됨")
    
    async def disconnect(self, workspace_id: str, user_id: str):
        """사용자 연결 해제"""
        if workspace_id in self.active_connections:
            if user_id in self.active_connections[workspace_id]:
                del self.active_connections[workspace_id][user_id]
            
            if user_id in self.workspace_users.get(workspace_id, {}):
                user_info = self.workspace_users[workspace_id][user_id]
                del self.workspace_users[workspace_id][user_id]
                
                # 편집 중인 아티팩트에서 제거
                artifacts_to_release = []
                for artifact_id, editor_id in list(self.active_editors[workspace_id].items()):
                    if editor_id == user_id:
                        artifacts_to_release.append(artifact_id)
                        del self.active_editors[workspace_id][artifact_id]
                
                # 다른 사용자들에게 연결 해제 알림
                await self.broadcast_to_workspace(workspace_id, {
                    "type": "user_left",
                    "data": {
                        "user": user_info,
                        "released_artifacts": artifacts_to_release,
                        "active_users": list(self.workspace_users[workspace_id].values()),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })
                
                logger.info(f"사용자 {user_info['name']}이 워크스페이스 {workspace_id}에서 연결 해제됨")
            
            # 워크스페이스에 아무도 없으면 정리
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]
                if workspace_id in self.workspace_users:
                    del self.workspace_users[workspace_id]
                if workspace_id in self.active_editors:
                    del self.active_editors[workspace_id]
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """개별 사용자에게 메시지 전송"""
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_text(json.dumps(message))
    
    async def broadcast_to_workspace(self, workspace_id: str, message: Dict[str, Any], exclude_user: str = None):
        """워크스페이스의 모든 사용자에게 브로드캐스트"""
        if workspace_id not in self.active_connections:
            return
        
        disconnected_users = []
        for user_id, websocket in self.active_connections[workspace_id].items():
            if exclude_user and user_id == exclude_user:
                continue
            
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps(message))
                else:
                    disconnected_users.append(user_id)
            except:
                disconnected_users.append(user_id)
        
        # 연결이 끊어진 사용자들 정리
        for user_id in disconnected_users:
            await self.disconnect(workspace_id, user_id)
    
    async def handle_artifact_edit(self, workspace_id: str, user_id: str, artifact_id: str, action: str, data: Dict[str, Any]):
        """아티팩트 편집 처리"""
        
        if action == "start_editing":
            # 다른 사용자가 편집 중인지 확인
            current_editor = self.active_editors[workspace_id].get(artifact_id)
            if current_editor and current_editor != user_id:
                # 편집 권한 충돌 알림
                user_websocket = self.active_connections[workspace_id].get(user_id)
                if user_websocket:
                    await self.send_personal_message(user_websocket, {
                        "type": "edit_conflict",
                        "data": {
                            "artifact_id": artifact_id,
                            "current_editor": self.workspace_users[workspace_id].get(current_editor, {}).get("name", "다른 사용자"),
                            "message": "다른 사용자가 편집 중입니다"
                        }
                    })
                return False
            
            # 편집 시작
            self.active_editors[workspace_id][artifact_id] = user_id
            await self.broadcast_to_workspace(workspace_id, {
                "type": "artifact_edit_start",
                "data": {
                    "artifact_id": artifact_id,
                    "editor": self.workspace_users[workspace_id].get(user_id, {}),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, exclude_user=user_id)
            
        elif action == "stop_editing":
            # 편집 종료
            if artifact_id in self.active_editors[workspace_id]:
                del self.active_editors[workspace_id][artifact_id]
            
            await self.broadcast_to_workspace(workspace_id, {
                "type": "artifact_edit_stop",
                "data": {
                    "artifact_id": artifact_id,
                    "editor": self.workspace_users[workspace_id].get(user_id, {}),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, exclude_user=user_id)
            
        elif action == "content_change":
            # 실시간 내용 변경 브로드캐스트
            await self.broadcast_to_workspace(workspace_id, {
                "type": "artifact_content_change",
                "data": {
                    "artifact_id": artifact_id,
                    "content": data.get("content", ""),
                    "cursor_position": data.get("cursor_position"),
                    "editor": self.workspace_users[workspace_id].get(user_id, {}),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, exclude_user=user_id)
        
        return True


# 전역 연결 관리자
connection_manager = WorkspaceConnectionManager()


@router.websocket("/ws/workspace/{workspace_id}")
async def workspace_websocket_endpoint(
    websocket: WebSocket,
    workspace_id: str,
    token: str = None
):
    """워크스페이스 실시간 협업 WebSocket"""
    
    # 토큰 검증 (쿼리 파라미터로 전달)
    if not token:
        await websocket.close(code=4001, reason="인증 토큰이 필요합니다")
        return
    
    # Mock 인증 (실제로는 토큰 검증)
    user_info = {
        "id": "ff8e410a-53a4-4541-a7d4-ce265678d66a",
        "name": "테스트 사용자",
        "email": "test@aiportal.com"
    }
    
    try:
        # 연결 설정
        await connection_manager.connect(websocket, workspace_id, user_info)
        
        while True:
            # 클라이언트로부터 메시지 수신
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                message_data = message.get("data", {})
                
                if message_type == "artifact_edit":
                    # 아티팩트 편집 처리
                    artifact_id = message_data.get("artifact_id")
                    action = message_data.get("action")
                    
                    if artifact_id and action:
                        await connection_manager.handle_artifact_edit(
                            workspace_id, 
                            user_info["id"], 
                            artifact_id, 
                            action, 
                            message_data
                        )
                
                elif message_type == "cursor_move":
                    # 커서 위치 브로드캐스트
                    await connection_manager.broadcast_to_workspace(workspace_id, {
                        "type": "cursor_move",
                        "data": {
                            "user": user_info,
                            "artifact_id": message_data.get("artifact_id"),
                            "position": message_data.get("position"),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }, exclude_user=user_info["id"])
                
                elif message_type == "ping":
                    # Keepalive 응답
                    await connection_manager.send_personal_message(websocket, {
                        "type": "pong",
                        "data": {"timestamp": datetime.utcnow().isoformat()}
                    })
                
            except json.JSONDecodeError:
                await connection_manager.send_personal_message(websocket, {
                    "type": "error",
                    "data": {"message": "잘못된 메시지 형식입니다"}
                })
            except Exception as e:
                logger.error(f"메시지 처리 중 오류: {e}")
                await connection_manager.send_personal_message(websocket, {
                    "type": "error", 
                    "data": {"message": f"메시지 처리 실패: {str(e)}"}
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket 연결 해제: 워크스페이스 {workspace_id}")
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
    finally:
        await connection_manager.disconnect(workspace_id, user_info["id"])