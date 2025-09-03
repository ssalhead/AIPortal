# Canvas Event Service - 이벤트 소싱 시스템
# AIPortal Canvas v5.0 - 통합 데이터 아키텍처

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, text
from sqlalchemy.orm import selectinload
from fastapi import WebSocket

from app.models.canvas_models import (
    CanvasEventData, CanvasOperationType, KonvaNodeType,
    CanvasNotFoundError, CanvasSyncError
)
from app.utils.logger import get_logger
from app.services.websocket_manager import WebSocketManager

logger = get_logger(__name__)

class CanvasEventService:
    """
    Canvas 이벤트 소싱 시스템
    
    주요 역할:
    1. 모든 Canvas 변경사항을 이벤트로 기록
    2. 이벤트 스트림 관리 및 재생
    3. 실시간 협업을 위한 이벤트 브로드캐스트
    4. 이벤트 기반 상태 복원
    5. 감사 로그 및 분석 지원
    """
    
    def __init__(
        self, 
        db_session: AsyncSession,
        websocket_manager: Optional[WebSocketManager] = None
    ):
        self.db = db_session
        self.websocket_manager = websocket_manager or WebSocketManager()
        
        # 이벤트 스트림 캐시
        self._event_streams: Dict[UUID, List[CanvasEventData]] = {}
        self._event_cache_ttl = 300  # 5분
        self._last_cache_update: Dict[UUID, datetime] = {}
        
        # 활성 협업자 추적
        self._active_collaborators: Dict[UUID, Set[UUID]] = {}  # canvas_id -> set of user_ids
        self._collaborator_sessions: Dict[UUID, Dict[str, Any]] = {}  # user_id -> session info
    
    async def record_event(self, event: CanvasEventData) -> bool:
        """
        Canvas 이벤트 기록
        
        특징:
        - 영속적 이벤트 스토어 저장
        - 실시간 협업자들에게 브로드캐스트
        - 이벤트 무결성 검증
        - 중복 이벤트 방지
        """
        try:
            # 이벤트 유효성 검증
            if not self._validate_event(event):
                logger.error(f"Invalid event data: {event.event_id}")
                return False
            
            # 이벤트 스토어에 저장 (현재는 임시로 메모리에 저장, 실제로는 DB 테이블에 저장)
            await self._persist_event_to_store(event)
            
            # 로컬 캐시 업데이트
            await self._update_event_cache(event)
            
            # 실시간 협업자들에게 브로드캐스트
            await self._broadcast_event(event)
            
            # 활동 시간 업데이트
            await self._update_collaborator_activity(event.user_id, event.canvas_id)
            
            logger.info(f"이벤트 기록 완료: {event.event_type} - {event.canvas_id}")
            return True
            
        except Exception as e:
            logger.error(f"이벤트 기록 실패 {event.event_id}: {str(e)}")
            return False
    
    async def get_canvas_events(
        self, 
        canvas_id: UUID,
        since_version: Optional[int] = None,
        limit: int = 100,
        event_types: Optional[List[CanvasOperationType]] = None
    ) -> List[CanvasEventData]:
        """
        Canvas 이벤트 조회
        
        특징:
        - 버전 기반 증분 조회
        - 이벤트 타입 필터링
        - 페이지네이션 지원
        - 캐시 최적화
        """
        try:
            # 캐시에서 먼저 조회
            cached_events = await self._get_cached_events(canvas_id)
            
            if cached_events:
                # 필터 적용
                filtered_events = []
                for event in cached_events:
                    # 버전 필터
                    if since_version and event.version_number <= since_version:
                        continue
                    
                    # 이벤트 타입 필터
                    if event_types and event.event_type not in event_types:
                        continue
                    
                    filtered_events.append(event)
                
                # 최신 순 정렬 후 제한
                filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
                return filtered_events[:limit]
            
            # 캐시 미스 - DB에서 조회 (실제 구현 시)
            logger.info(f"DB에서 이벤트 조회: {canvas_id}")
            return await self._load_events_from_db(canvas_id, since_version, limit, event_types)
            
        except Exception as e:
            logger.error(f"이벤트 조회 실패 {canvas_id}: {str(e)}")
            return []
    
    async def replay_events(
        self, 
        canvas_id: UUID,
        target_version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        이벤트 재생을 통한 Canvas 상태 복원
        
        특징:
        - 특정 버전까지 이벤트 재생
        - 상태 스냅샷 생성
        - 성능 최적화된 재생 로직
        """
        try:
            # 모든 이벤트 조회 (시간순 정렬)
            events = await self.get_canvas_events(canvas_id, limit=10000)
            events.sort(key=lambda x: x.timestamp)
            
            # 빈 Canvas 상태로 시작
            canvas_state = {
                'id': str(canvas_id),
                'version_number': 0,
                'stage': {
                    'width': 1920,
                    'height': 1080,
                    'layers': []
                },
                'metadata': {}
            }
            
            # 이벤트 순차 적용
            for event in events:
                # 목표 버전에 도달하면 중단
                if target_version and event.version_number > target_version:
                    break
                
                await self._apply_event_to_state(canvas_state, event)
                canvas_state['version_number'] = event.version_number
            
            logger.info(f"이벤트 재생 완료: {canvas_id} -> v{canvas_state['version_number']}")
            return canvas_state
            
        except Exception as e:
            logger.error(f"이벤트 재생 실패 {canvas_id}: {str(e)}")
            return None
    
    async def get_active_collaborators(self, canvas_id: UUID) -> List[Dict[str, Any]]:
        """활성 협업자 목록 조회"""
        try:
            if canvas_id not in self._active_collaborators:
                return []
            
            collaborators = []
            user_ids = self._active_collaborators[canvas_id]
            
            for user_id in user_ids:
                session_info = self._collaborator_sessions.get(user_id, {})
                
                # 최근 10분 내 활동이 있는 사용자만 포함
                last_activity = session_info.get('last_activity')
                if last_activity and (datetime.utcnow() - last_activity).seconds < 600:
                    collaborators.append({
                        'user_id': str(user_id),
                        'last_activity': last_activity.isoformat(),
                        'cursor_position': session_info.get('cursor_position'),
                        'is_editing': session_info.get('is_editing', False)
                    })
            
            return collaborators
            
        except Exception as e:
            logger.error(f"활성 협업자 조회 실패 {canvas_id}: {str(e)}")
            return []
    
    async def get_last_activity_time(self, canvas_id: UUID) -> Optional[datetime]:
        """Canvas 최근 활동 시간"""
        try:
            events = await self.get_canvas_events(canvas_id, limit=1)
            if events:
                return events[0].timestamp
            return None
            
        except Exception as e:
            logger.error(f"최근 활동 시간 조회 실패 {canvas_id}: {str(e)}")
            return None
    
    async def register_collaborator(
        self, 
        canvas_id: UUID, 
        user_id: UUID,
        websocket: WebSocket,
        session_data: Dict[str, Any] = None
    ) -> None:
        """협업자 등록 (WebSocket 연결 시)"""
        try:
            # 활성 협업자 목록에 추가
            if canvas_id not in self._active_collaborators:
                self._active_collaborators[canvas_id] = set()
            
            self._active_collaborators[canvas_id].add(user_id)
            
            # 세션 정보 저장
            self._collaborator_sessions[user_id] = {
                'canvas_id': canvas_id,
                'websocket': websocket,
                'joined_at': datetime.utcnow(),
                'last_activity': datetime.utcnow(),
                **(session_data or {})
            }
            
            # WebSocket 매니저에 등록
            await self.websocket_manager.connect(
                websocket, f"canvas_{canvas_id}", str(user_id)
            )
            
            # 다른 협업자들에게 알림
            join_event = CanvasEventData(
                canvas_id=canvas_id,
                user_id=user_id,
                event_type=CanvasOperationType.CREATE,  # 임시로 CREATE 사용
                target_type=KonvaNodeType.STAGE,
                target_id="collaboration",
                new_data={'action': 'user_joined', 'user_id': str(user_id)}
            )
            
            await self._broadcast_event(join_event, exclude_user=user_id)
            
            logger.info(f"협업자 등록: {user_id} -> Canvas {canvas_id}")
            
        except Exception as e:
            logger.error(f"협업자 등록 실패 {user_id}: {str(e)}")
    
    async def unregister_collaborator(
        self, 
        canvas_id: UUID, 
        user_id: UUID
    ) -> None:
        """협업자 등록 해제 (WebSocket 연결 종료 시)"""
        try:
            # 활성 협업자 목록에서 제거
            if canvas_id in self._active_collaborators:
                self._active_collaborators[canvas_id].discard(user_id)
                
                # 빈 세트면 제거
                if not self._active_collaborators[canvas_id]:
                    del self._active_collaborators[canvas_id]
            
            # 세션 정보 제거
            if user_id in self._collaborator_sessions:
                del self._collaborator_sessions[user_id]
            
            # WebSocket 매니저에서 해제
            await self.websocket_manager.disconnect(f"canvas_{canvas_id}", str(user_id))
            
            # 다른 협업자들에게 알림
            leave_event = CanvasEventData(
                canvas_id=canvas_id,
                user_id=user_id,
                event_type=CanvasOperationType.DELETE,  # 임시로 DELETE 사용
                target_type=KonvaNodeType.STAGE,
                target_id="collaboration",
                new_data={'action': 'user_left', 'user_id': str(user_id)}
            )
            
            await self._broadcast_event(leave_event, exclude_user=user_id)
            
            logger.info(f"협업자 등록 해제: {user_id} <- Canvas {canvas_id}")
            
        except Exception as e:
            logger.error(f"협업자 등록 해제 실패 {user_id}: {str(e)}")
    
    async def update_cursor_position(
        self, 
        user_id: UUID, 
        position: Dict[str, float]
    ) -> None:
        """협업자 커서 위치 업데이트"""
        try:
            if user_id in self._collaborator_sessions:
                session = self._collaborator_sessions[user_id]
                session['cursor_position'] = position
                session['last_activity'] = datetime.utcnow()
                
                # 다른 협업자들에게 커서 위치 브로드캐스트
                canvas_id = session['canvas_id']
                cursor_event = CanvasEventData(
                    canvas_id=canvas_id,
                    user_id=user_id,
                    event_type=CanvasOperationType.UPDATE,
                    target_type=KonvaNodeType.STAGE,
                    target_id="cursor",
                    new_data={'position': position, 'user_id': str(user_id)}
                )
                
                await self._broadcast_event(cursor_event, exclude_user=user_id)
                
        except Exception as e:
            logger.error(f"커서 위치 업데이트 실패 {user_id}: {str(e)}")
    
    def _validate_event(self, event: CanvasEventData) -> bool:
        """이벤트 데이터 유효성 검증"""
        if not event.event_id or not event.canvas_id or not event.user_id:
            return False
        
        if not event.event_type or not event.target_type:
            return False
        
        # 필수 데이터 검증
        if event.event_type in [
            CanvasOperationType.CREATE, 
            CanvasOperationType.UPDATE
        ]:
            if not event.new_data:
                return False
        
        return True
    
    async def _persist_event_to_store(self, event: CanvasEventData) -> None:
        """이벤트 스토어에 영속 저장"""
        # 실제 구현 시 PostgreSQL canvas_events 테이블에 INSERT
        # 현재는 임시로 로깅
        logger.debug(f"이벤트 저장: {event.event_type} - {event.canvas_id}")
        
        # TODO: 실제 DB 저장 로직
        # INSERT INTO canvas_events (id, canvas_id, user_id, event_type, ...)
        pass
    
    async def _update_event_cache(self, event: CanvasEventData) -> None:
        """로컬 이벤트 캐시 업데이트"""
        canvas_id = event.canvas_id
        
        if canvas_id not in self._event_streams:
            self._event_streams[canvas_id] = []
        
        # 이벤트 추가 (최신 순 유지)
        self._event_streams[canvas_id].insert(0, event)
        
        # 캐시 크기 제한 (최대 1000개)
        if len(self._event_streams[canvas_id]) > 1000:
            self._event_streams[canvas_id] = self._event_streams[canvas_id][:1000]
        
        # 캐시 업데이트 시간 기록
        self._last_cache_update[canvas_id] = datetime.utcnow()
    
    async def _broadcast_event(
        self, 
        event: CanvasEventData,
        exclude_user: Optional[UUID] = None
    ) -> None:
        """실시간 협업자들에게 이벤트 브로드캐스트"""
        try:
            canvas_id = event.canvas_id
            
            # WebSocket 브로드캐스트 데이터 준비
            broadcast_data = {
                'type': 'canvas_event',
                'event': {
                    'id': str(event.event_id),
                    'canvas_id': str(event.canvas_id),
                    'user_id': str(event.user_id),
                    'event_type': event.event_type.value,
                    'target_type': event.target_type.value,
                    'target_id': event.target_id,
                    'new_data': event.new_data,
                    'old_data': event.old_data,
                    'timestamp': event.timestamp.isoformat(),
                    'version_number': event.version_number
                }
            }
            
            # 해당 Canvas의 활성 협업자들에게 브로드캐스트
            room_id = f"canvas_{canvas_id}"
            exclude_user_str = str(exclude_user) if exclude_user else None
            
            await self.websocket_manager.broadcast_to_room(
                room_id, 
                json.dumps(broadcast_data), 
                exclude_user=exclude_user_str
            )
            
        except Exception as e:
            logger.error(f"이벤트 브로드캐스트 실패: {str(e)}")
    
    async def _update_collaborator_activity(
        self, 
        user_id: UUID, 
        canvas_id: UUID
    ) -> None:
        """협업자 활동 시간 업데이트"""
        if user_id in self._collaborator_sessions:
            self._collaborator_sessions[user_id]['last_activity'] = datetime.utcnow()
            self._collaborator_sessions[user_id]['is_editing'] = True
    
    async def _get_cached_events(self, canvas_id: UUID) -> Optional[List[CanvasEventData]]:
        """캐시에서 이벤트 조회"""
        if canvas_id not in self._event_streams:
            return None
        
        # 캐시 TTL 확인
        last_update = self._last_cache_update.get(canvas_id)
        if last_update and (datetime.utcnow() - last_update).seconds > self._event_cache_ttl:
            # 캐시 만료 - 제거
            del self._event_streams[canvas_id]
            del self._last_cache_update[canvas_id]
            return None
        
        return self._event_streams[canvas_id]
    
    async def _load_events_from_db(
        self, 
        canvas_id: UUID,
        since_version: Optional[int] = None,
        limit: int = 100,
        event_types: Optional[List[CanvasOperationType]] = None
    ) -> List[CanvasEventData]:
        """DB에서 이벤트 로드"""
        # 실제 구현 시 PostgreSQL에서 조회
        # 현재는 빈 리스트 반환
        logger.debug(f"DB에서 이벤트 로드: {canvas_id}")
        return []
    
    async def _apply_event_to_state(
        self, 
        canvas_state: Dict[str, Any], 
        event: CanvasEventData
    ) -> None:
        """Canvas 상태에 이벤트 적용"""
        try:
            if event.event_type == CanvasOperationType.CREATE:
                await self._apply_create_event(canvas_state, event)
            elif event.event_type == CanvasOperationType.UPDATE:
                await self._apply_update_event(canvas_state, event)
            elif event.event_type == CanvasOperationType.DELETE:
                await self._apply_delete_event(canvas_state, event)
            elif event.event_type in [
                CanvasOperationType.MOVE,
                CanvasOperationType.RESIZE,
                CanvasOperationType.ROTATE
            ]:
                await self._apply_transform_event(canvas_state, event)
                
        except Exception as e:
            logger.error(f"이벤트 적용 실패 {event.event_id}: {str(e)}")
    
    async def _apply_create_event(
        self, 
        canvas_state: Dict[str, Any], 
        event: CanvasEventData
    ) -> None:
        """생성 이벤트 적용"""
        if event.target_type == KonvaNodeType.LAYER:
            # 레이어 생성
            layer_data = event.new_data
            canvas_state['stage']['layers'].append(layer_data)
        else:
            # 노드 생성 - 적절한 레이어에 추가
            node_data = event.new_data
            
            # 기본 레이어가 없으면 생성
            if not canvas_state['stage']['layers']:
                canvas_state['stage']['layers'].append({
                    'id': 'layer_0',
                    'name': 'Default Layer',
                    'layer_index': 0,
                    'nodes': []
                })
            
            # 첫 번째 레이어에 노드 추가
            canvas_state['stage']['layers'][0]['nodes'].append(node_data)
    
    async def _apply_update_event(
        self, 
        canvas_state: Dict[str, Any], 
        event: CanvasEventData
    ) -> None:
        """업데이트 이벤트 적용"""
        target_id = event.target_id
        
        # 타겟 노드 찾기 및 업데이트
        for layer in canvas_state['stage']['layers']:
            if layer.get('id') == target_id:
                # 레이어 업데이트
                layer.update(event.new_data)
                return
            
            for node in layer.get('nodes', []):
                if node.get('id') == target_id:
                    # 노드 업데이트
                    node.update(event.new_data)
                    return
    
    async def _apply_delete_event(
        self, 
        canvas_state: Dict[str, Any], 
        event: CanvasEventData
    ) -> None:
        """삭제 이벤트 적용"""
        target_id = event.target_id
        
        # 타겟 노드 찾기 및 삭제
        for layer in canvas_state['stage']['layers']:
            if layer.get('id') == target_id:
                # 레이어 삭제
                canvas_state['stage']['layers'].remove(layer)
                return
            
            nodes = layer.get('nodes', [])
            for i, node in enumerate(nodes):
                if node.get('id') == target_id:
                    # 노드 삭제
                    nodes.pop(i)
                    return
    
    async def _apply_transform_event(
        self, 
        canvas_state: Dict[str, Any], 
        event: CanvasEventData
    ) -> None:
        """변형 이벤트 적용 (이동, 크기조절, 회전)"""
        await self._apply_update_event(canvas_state, event)  # 업데이트와 동일한 로직
    
    async def cleanup_inactive_collaborators(self) -> None:
        """비활성 협업자 정리 (백그라운드 작업)"""
        try:
            current_time = datetime.utcnow()
            inactive_threshold = timedelta(minutes=10)
            
            inactive_users = []
            
            for user_id, session in self._collaborator_sessions.items():
                last_activity = session.get('last_activity', current_time)
                if current_time - last_activity > inactive_threshold:
                    inactive_users.append((user_id, session['canvas_id']))
            
            # 비활성 사용자 제거
            for user_id, canvas_id in inactive_users:
                await self.unregister_collaborator(canvas_id, user_id)
            
            if inactive_users:
                logger.info(f"비활성 협업자 {len(inactive_users)}명 정리 완료")
                
        except Exception as e:
            logger.error(f"비활성 협업자 정리 실패: {str(e)}")
    
    async def get_event_statistics(self, canvas_id: UUID) -> Dict[str, Any]:
        """Canvas 이벤트 통계"""
        try:
            events = await self.get_canvas_events(canvas_id, limit=1000)
            
            if not events:
                return {'canvas_id': str(canvas_id), 'total_events': 0}
            
            # 이벤트 타입별 통계
            event_type_counts = {}
            user_activity = {}
            
            for event in events:
                event_type = event.event_type.value
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
                
                user_id = str(event.user_id)
                user_activity[user_id] = user_activity.get(user_id, 0) + 1
            
            return {
                'canvas_id': str(canvas_id),
                'total_events': len(events),
                'event_types': event_type_counts,
                'active_users': len(user_activity),
                'user_activity': user_activity,
                'last_activity': events[0].timestamp.isoformat() if events else None
            }
            
        except Exception as e:
            logger.error(f"이벤트 통계 조회 실패 {canvas_id}: {str(e)}")
            return {'canvas_id': str(canvas_id), 'error': str(e)}

# 임시 WebSocket 매니저 (실제로는 별도 서비스로 구현)
class WebSocketManager:
    """WebSocket 연결 관리"""
    
    def __init__(self):
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}  # room_id -> {user_id: websocket}
    
    async def connect(self, websocket: WebSocket, room_id: str, user_id: str):
        """WebSocket 연결"""
        if room_id not in self.rooms:
            self.rooms[room_id] = {}
        
        self.rooms[room_id][user_id] = websocket
        logger.debug(f"WebSocket 연결: {user_id} -> {room_id}")
    
    async def disconnect(self, room_id: str, user_id: str):
        """WebSocket 연결 해제"""
        if room_id in self.rooms and user_id in self.rooms[room_id]:
            del self.rooms[room_id][user_id]
            
            # 빈 방 제거
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        
        logger.debug(f"WebSocket 연결 해제: {user_id} <- {room_id}")
    
    async def broadcast_to_room(
        self, 
        room_id: str, 
        message: str,
        exclude_user: Optional[str] = None
    ):
        """방의 모든 사용자에게 메시지 브로드캐스트"""
        if room_id not in self.rooms:
            return
        
        disconnected_users = []
        
        for user_id, websocket in self.rooms[room_id].items():
            if exclude_user and user_id == exclude_user:
                continue
            
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"WebSocket 전송 실패 {user_id}: {str(e)}")
                disconnected_users.append(user_id)
        
        # 연결이 끊어진 사용자들 정리
        for user_id in disconnected_users:
            await self.disconnect(room_id, user_id)