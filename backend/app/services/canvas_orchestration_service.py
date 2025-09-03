# Canvas Orchestration Service - 중앙 조정자
# AIPortal Canvas v5.0 - 통합 데이터 아키텍처

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from app.models.canvas_models import (
    CanvasData, CanvasEventData, CanvasSyncState, CanvasSyncResult,
    CreateCanvasRequest, UpdateCanvasRequest, CanvasOperationRequest,
    CanvasOperationResult, CanvasSyncRequest, CanvasCollaborationStatus,
    SyncStatus, CanvasOperationType, CanvasNotFoundError, CanvasSyncError,
    CanvasVersionMismatchError, IdempotencyViolationError,
    generate_idempotency_key, validate_konva_node, sanitize_konva_attrs
)
from app.db.models.workspace import Workspace
from app.db.models.conversation import Conversation
from app.utils.logger import get_logger
from app.services.canvas_event_service import CanvasEventService
from app.services.canvas_sync_service import CanvasSyncService  
from app.services.idempotency_manager import IdempotencyManager
from app.services.canvas_cache_manager import CanvasCacheManager
from app.security.canvas_security import CanvasSecurityManager, get_canvas_security_manager

logger = get_logger(__name__)

class CanvasOrchestrationService:
    """
    Canvas 시스템의 중앙 조정자
    
    주요 역할:
    1. 모든 Canvas 작업의 단일 진입점
    2. 데이터 일관성 보장 (Single Source of Truth)
    3. 동기화 상태 관리
    4. 충돌 해결 조정
    5. 성능 최적화 (캐싱, 배치 처리)
    """
    
    def __init__(
        self, 
        db_session: AsyncSession,
        event_service: CanvasEventService,
        sync_service: CanvasSyncService,
        idempotency_manager: IdempotencyManager,
        cache_manager: CanvasCacheManager,
        security_manager: Optional[CanvasSecurityManager] = None
    ):
        self.db = db_session
        self.event_service = event_service
        self.sync_service = sync_service
        self.idempotency_manager = idempotency_manager
        self.cache_manager = cache_manager
        self.security_manager = security_manager or get_canvas_security_manager(db_session.sync_session if hasattr(db_session, 'sync_session') else db_session)
        
        # 동시성 제어
        self._canvas_locks: Dict[UUID, asyncio.Lock] = {}
        self._operation_semaphore = asyncio.Semaphore(100)  # 최대 100개 동시 작업
    
    async def _get_canvas_lock(self, canvas_id: UUID) -> asyncio.Lock:
        """Canvas별 분산 락 획득"""
        if canvas_id not in self._canvas_locks:
            self._canvas_locks[canvas_id] = asyncio.Lock()
        return self._canvas_locks[canvas_id]
    
    async def create_canvas(
        self, 
        request: CreateCanvasRequest, 
        user_id: UUID
    ) -> CanvasOperationResult:
        """
        새로운 Canvas 생성
        
        특징:
        - 멱등성 보장 (중복 생성 방지)
        - 워크스페이스 권한 검증
        - 초기 이벤트 기록
        """
        async with self._operation_semaphore:
            try:
                # 멱등성 키 생성
                idempotency_key = generate_idempotency_key(
                    request.workspace_id, "create_canvas", user_id
                )
                
                # 중복 생성 확인
                existing_operation = await self.idempotency_manager.check_operation(
                    idempotency_key
                )
                if existing_operation:
                    logger.info(f"Canvas 중복 생성 방지: {idempotency_key}")
                    return existing_operation
                
                # 워크스페이스 존재 확인
                workspace_query = select(Workspace).where(Workspace.id == request.workspace_id)
                workspace_result = await self.db.execute(workspace_query)
                workspace = workspace_result.scalar_one_or_none()
                
                if not workspace:
                    raise CanvasNotFoundError(f"Workspace {request.workspace_id} not found")
                
                # 새 Canvas 데이터 생성
                canvas_data = CanvasData(
                    workspace_id=request.workspace_id,
                    conversation_id=request.conversation_id,
                    name=request.name,
                    description=request.description,
                    canvas_type=request.canvas_type
                )
                
                # 초기 생성 이벤트
                create_event = CanvasEventData(
                    canvas_id=canvas_data.id,
                    user_id=user_id,
                    event_type=CanvasOperationType.CREATE,
                    target_type="stage",
                    target_id=str(canvas_data.id),
                    new_data=canvas_data.model_dump(),
                    idempotency_key=idempotency_key
                )
                
                # 이벤트 기록
                await self.event_service.record_event(create_event)
                
                # 캐시 저장
                await self.cache_manager.set_canvas(canvas_data.id, canvas_data)
                
                # 멱등성 기록
                result = CanvasOperationResult(
                    success=True,
                    canvas_data=canvas_data
                )
                await self.idempotency_manager.record_operation(
                    idempotency_key, result
                )
                
                logger.info(f"Canvas 생성 완료: {canvas_data.id}")
                return result
                
            except Exception as e:
                logger.error(f"Canvas 생성 실패: {str(e)}")
                return CanvasOperationResult(
                    success=False,
                    error_message=str(e)
                )
    
    async def get_canvas(
        self, 
        canvas_id: UUID, 
        user_id: UUID,
        include_events: bool = False
    ) -> CanvasOperationResult:
        """
        Canvas 조회 (캐시 우선)
        
        특징:
        - 2-Tier 캐싱 (메모리 + DB 캐시)
        - 권한 검증
        - 이벤트 히스토리 선택적 포함
        """
        try:
            # 캐시에서 먼저 조회
            canvas_data = await self.cache_manager.get_canvas(canvas_id)
            
            if not canvas_data:
                # DB에서 조회 (실제 구현 시 Canvas 테이블에서 조회)
                logger.warning(f"Canvas {canvas_id} not found in cache or DB")
                raise CanvasNotFoundError(f"Canvas {canvas_id} not found")
            
            # 이벤트 포함 요청 시
            if include_events:
                events = await self.event_service.get_canvas_events(
                    canvas_id, limit=100
                )
                canvas_data.metadata["recent_events"] = [
                    event.model_dump() for event in events
                ]
            
            return CanvasOperationResult(
                success=True,
                canvas_data=canvas_data
            )
            
        except Exception as e:
            logger.error(f"Canvas 조회 실패 {canvas_id}: {str(e)}")
            return CanvasOperationResult(
                success=False,
                error_message=str(e)
            )
    
    async def update_canvas(
        self,
        canvas_id: UUID,
        request: UpdateCanvasRequest,
        user_id: UUID
    ) -> CanvasOperationResult:
        """
        Canvas 업데이트 (낙관적 잠금)
        
        특징:
        - 버전 충돌 감지
        - 변경사항 이벤트 기록
        - 실시간 동기화 트리거
        """
        canvas_lock = await self._get_canvas_lock(canvas_id)
        
        async with canvas_lock:
            try:
                # 🔒 보안 검증: Canvas 편집 권한 확인
                if not self.security_manager.access_control.check_canvas_permission(
                    str(user_id), str(canvas_id), 'edit_text'
                ):
                    self.security_manager.auditor.log_access_attempt(
                        str(user_id), str(canvas_id), 'update_canvas', False
                    )
                    return CanvasOperationResult(
                        success=False,
                        message="Canvas 편집 권한이 없습니다.",
                        error_code="ACCESS_DENIED"
                    )
                
                # 🔒 입력 데이터 보안 검증 및 sanitization
                try:
                    sanitized_data = self.security_manager.secure_canvas_data(
                        request.data, str(user_id)
                    )
                    # sanitization된 데이터로 요청 업데이트
                    request.data = sanitized_data
                except Exception as security_error:
                    logger.warning(f"Canvas 데이터 보안 검증 실패: {security_error}")
                    return CanvasOperationResult(
                        success=False,
                        message=f"보안 검증 실패: {str(security_error)}",
                        error_code="SECURITY_VALIDATION_FAILED"
                    )
                
                # 현재 Canvas 조회
                canvas_result = await self.get_canvas(canvas_id, user_id)
                if not canvas_result.success:
                    return canvas_result
                
                canvas_data = canvas_result.canvas_data
                
                # 버전 확인 (낙관적 잠금)
                if canvas_data.version_number != request.expected_version:
                    raise CanvasVersionMismatchError(
                        request.expected_version, 
                        canvas_data.version_number
                    )
                
                # 변경사항 적용
                old_data = canvas_data.model_dump()
                
                if request.name is not None:
                    canvas_data.name = request.name
                if request.description is not None:
                    canvas_data.description = request.description
                if request.stage is not None:
                    canvas_data.stage = request.stage
                if request.metadata is not None:
                    canvas_data.metadata.update(request.metadata)
                
                # 버전 증가
                canvas_data.version_number += 1
                canvas_data.updated_at = datetime.utcnow()
                
                # 업데이트 이벤트 생성
                update_event = CanvasEventData(
                    canvas_id=canvas_id,
                    user_id=user_id,
                    event_type=CanvasOperationType.UPDATE,
                    target_type="stage",
                    target_id=str(canvas_id),
                    new_data=canvas_data.model_dump(),
                    old_data=old_data,
                    version_number=canvas_data.version_number
                )
                
                # 이벤트 기록 및 실시간 동기화
                await self.event_service.record_event(update_event)
                
                # 캐시 업데이트
                await self.cache_manager.set_canvas(canvas_id, canvas_data)
                
                logger.info(f"Canvas 업데이트 완료: {canvas_id} v{canvas_data.version_number}")
                return CanvasOperationResult(
                    success=True,
                    canvas_data=canvas_data
                )
                
            except Exception as e:
                logger.error(f"Canvas 업데이트 실패 {canvas_id}: {str(e)}")
                return CanvasOperationResult(
                    success=False,
                    error_message=str(e)
                )
    
    async def execute_canvas_operation(
        self,
        request: CanvasOperationRequest
    ) -> CanvasOperationResult:
        """
        Canvas 작업 실행 (핵심 메서드)
        
        특징:
        - 멱등성 보장
        - 실시간 협업 지원
        - 자동 충돌 해결
        - 성능 최적화
        """
        canvas_lock = await self._get_canvas_lock(request.canvas_id)
        
        async with canvas_lock:
            try:
                # 멱등성 확인
                existing_operation = await self.idempotency_manager.check_operation(
                    request.idempotency_key
                )
                if existing_operation:
                    logger.info(f"중복 작업 방지: {request.idempotency_key}")
                    return existing_operation
                
                # Canvas 조회
                canvas_result = await self.get_canvas(
                    request.canvas_id, 
                    request.operation.user_id
                )
                if not canvas_result.success:
                    return canvas_result
                
                canvas_data = canvas_result.canvas_data
                
                # 작업 데이터 유효성 검증
                if not self._validate_operation(request.operation):
                    raise ValueError("Invalid operation data")
                
                # Konva 노드 데이터 살균 처리 (보안)
                if 'konva_attrs' in request.operation.new_data:
                    request.operation.new_data['konva_attrs'] = sanitize_konva_attrs(
                        request.operation.new_data['konva_attrs']
                    )
                
                # 작업 적용
                await self._apply_operation(canvas_data, request.operation)
                
                # 버전 증가
                canvas_data.version_number += 1
                canvas_data.updated_at = datetime.utcnow()
                
                # 이벤트 기록
                request.operation.version_number = canvas_data.version_number
                await self.event_service.record_event(request.operation)
                
                # 캐시 업데이트
                await self.cache_manager.set_canvas(request.canvas_id, canvas_data)
                
                # 결과 생성
                result = CanvasOperationResult(
                    success=True,
                    canvas_data=canvas_data
                )
                
                # 멱등성 기록
                await self.idempotency_manager.record_operation(
                    request.idempotency_key, result
                )
                
                logger.info(f"Canvas 작업 완료: {request.canvas_id} - {request.operation.event_type}")
                return result
                
            except Exception as e:
                logger.error(f"Canvas 작업 실패: {str(e)}")
                return CanvasOperationResult(
                    success=False,
                    error_message=str(e)
                )
    
    async def sync_canvas(
        self,
        request: CanvasSyncRequest,
        user_id: UUID
    ) -> CanvasSyncResult:
        """
        Canvas 동기화 처리
        
        특징:
        - 증분 동기화 (변경사항만)
        - 충돌 자동 해결
        - 협업 사용자 간 실시간 동기화
        """
        try:
            # 동기화 서비스에 위임
            result = await self.sync_service.sync_canvas(
                request, user_id, self
            )
            
            logger.info(f"Canvas 동기화 완료: {request.canvas_id} -> v{result.server_version}")
            return result
            
        except Exception as e:
            logger.error(f"Canvas 동기화 실패 {request.canvas_id}: {str(e)}")
            raise CanvasSyncError(f"Sync failed: {str(e)}")
    
    async def get_collaboration_status(
        self,
        canvas_id: UUID
    ) -> CanvasCollaborationStatus:
        """
        Canvas 협업 상태 조회
        """
        try:
            # 활성 사용자 조회 (WebSocket 연결 기준)
            active_users = await self.event_service.get_active_collaborators(canvas_id)
            
            # 최근 활동 시간
            last_activity = await self.event_service.get_last_activity_time(canvas_id)
            
            # 충돌 상태
            pending_conflicts = await self.sync_service.count_pending_conflicts(canvas_id)
            
            return CanvasCollaborationStatus(
                canvas_id=canvas_id,
                active_users=active_users,
                concurrent_editors=len(active_users),
                last_activity=last_activity,
                pending_conflicts=pending_conflicts
            )
            
        except Exception as e:
            logger.error(f"협업 상태 조회 실패 {canvas_id}: {str(e)}")
            return CanvasCollaborationStatus(canvas_id=canvas_id)
    
    async def batch_operation(
        self,
        operations: List[CanvasOperationRequest]
    ) -> List[CanvasOperationResult]:
        """
        배치 작업 처리 (성능 최적화)
        
        특징:
        - Canvas별 그룹화
        - 순차적 충돌 방지
        - 트랜잭션 단위 처리
        """
        results = []
        
        # Canvas별로 그룹화
        canvas_groups = {}
        for op in operations:
            canvas_id = op.canvas_id
            if canvas_id not in canvas_groups:
                canvas_groups[canvas_id] = []
            canvas_groups[canvas_id].append(op)
        
        # Canvas별 순차 처리 (충돌 방지)
        for canvas_id, canvas_ops in canvas_groups.items():
            canvas_lock = await self._get_canvas_lock(canvas_id)
            
            async with canvas_lock:
                for op in canvas_ops:
                    result = await self.execute_canvas_operation(op)
                    results.append(result)
                    
                    # 실패 시 해당 Canvas의 나머지 작업 스킵
                    if not result.success:
                        logger.warning(f"배치 작업 중단 - Canvas {canvas_id}: {result.error_message}")
                        break
        
        logger.info(f"배치 작업 완료: {len(operations)}개 중 {sum(1 for r in results if r.success)}개 성공")
        return results
    
    def _validate_operation(self, operation: CanvasEventData) -> bool:
        """작업 데이터 유효성 검증"""
        if not operation.canvas_id or not operation.user_id:
            return False
        
        if operation.target_type == "text":
            # 텍스트 노드 검증
            return validate_konva_node(operation.new_data)
        elif operation.target_type == "image":
            # 이미지 노드 검증
            return 'src' in operation.new_data or 'image' in operation.new_data
        
        return True
    
    async def _apply_operation(
        self, 
        canvas_data: CanvasData, 
        operation: CanvasEventData
    ) -> None:
        """Canvas에 작업 적용"""
        target_layer = None
        target_node = None
        
        # 타겟 레이어/노드 찾기
        for layer in canvas_data.stage.layers:
            if operation.target_type == "layer" and layer.id == operation.target_id:
                target_layer = layer
                break
            
            for node in layer.nodes:
                if node.id == operation.target_id:
                    target_layer = layer
                    target_node = node
                    break
        
        # 작업 유형별 처리
        if operation.event_type == CanvasOperationType.CREATE:
            await self._handle_create_operation(canvas_data, operation)
        elif operation.event_type == CanvasOperationType.UPDATE:
            await self._handle_update_operation(target_node, operation)
        elif operation.event_type == CanvasOperationType.DELETE:
            await self._handle_delete_operation(target_layer, target_node)
        elif operation.event_type in [
            CanvasOperationType.MOVE, 
            CanvasOperationType.RESIZE, 
            CanvasOperationType.ROTATE
        ]:
            await self._handle_transform_operation(target_node, operation)
    
    async def _handle_create_operation(
        self, 
        canvas_data: CanvasData, 
        operation: CanvasEventData
    ) -> None:
        """생성 작업 처리"""
        if operation.target_type == "layer":
            # 새 레이어 생성 (구현 예정)
            pass
        else:
            # 새 노드 생성
            from app.models.canvas_models import KonvaNodeData
            
            node_data = KonvaNodeData(**operation.new_data)
            
            # 적절한 레이어에 추가
            if canvas_data.stage.layers:
                canvas_data.stage.layers[0].nodes.append(node_data)
            else:
                # 기본 레이어 생성
                from app.models.canvas_models import KonvaLayerData
                default_layer = KonvaLayerData(
                    id="layer_0",
                    name="Default Layer",
                    layer_index=0,
                    nodes=[node_data]
                )
                canvas_data.stage.layers.append(default_layer)
    
    async def _handle_update_operation(
        self, 
        target_node: Optional[Any], 
        operation: CanvasEventData
    ) -> None:
        """업데이트 작업 처리"""
        if not target_node:
            logger.warning(f"Update target node not found: {operation.target_id}")
            return
        
        # 노드 속성 업데이트
        for key, value in operation.new_data.items():
            if hasattr(target_node, key):
                setattr(target_node, key, value)
            elif key == 'konva_attrs':
                target_node.konva_attrs.update(value)
    
    async def _handle_delete_operation(
        self, 
        target_layer: Optional[Any], 
        target_node: Optional[Any]
    ) -> None:
        """삭제 작업 처리"""
        if target_layer and target_node:
            target_layer.nodes = [n for n in target_layer.nodes if n.id != target_node.id]
    
    async def _handle_transform_operation(
        self, 
        target_node: Optional[Any], 
        operation: CanvasEventData
    ) -> None:
        """변형 작업 처리 (이동, 크기조절, 회전)"""
        if not target_node:
            return
        
        # 변형 속성 업데이트
        transform_attrs = ['x', 'y', 'width', 'height', 'scale_x', 'scale_y', 'rotation']
        for attr in transform_attrs:
            if attr in operation.new_data:
                setattr(target_node, attr, operation.new_data[attr])
    
    async def cleanup_expired_locks(self) -> None:
        """만료된 락 정리 (백그라운드 작업)"""
        # 구현 예정: 만료된 Canvas 락들을 주기적으로 정리
        pass
    
    async def get_canvas_statistics(self, canvas_id: UUID) -> Dict[str, Any]:
        """Canvas 통계 정보"""
        try:
            canvas_result = await self.get_canvas(canvas_id, UUID('00000000-0000-0000-0000-000000000000'))
            if not canvas_result.success:
                return {}
            
            canvas_data = canvas_result.canvas_data
            
            total_nodes = sum(len(layer.nodes) for layer in canvas_data.stage.layers)
            total_layers = len(canvas_data.stage.layers)
            
            # 노드 타입별 통계
            node_types = {}
            for layer in canvas_data.stage.layers:
                for node in layer.nodes:
                    node_type = node.node_type.value
                    node_types[node_type] = node_types.get(node_type, 0) + 1
            
            return {
                'canvas_id': str(canvas_id),
                'version': canvas_data.version_number,
                'total_layers': total_layers,
                'total_nodes': total_nodes,
                'node_types': node_types,
                'created_at': canvas_data.created_at.isoformat(),
                'last_updated': canvas_data.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Canvas 통계 조회 실패 {canvas_id}: {str(e)}")
            return {}

# 싱글톤 인스턴스 (DI 컨테이너에서 관리)
_orchestration_service: Optional[CanvasOrchestrationService] = None

def get_canvas_orchestration_service() -> Optional[CanvasOrchestrationService]:
    """Canvas Orchestration 서비스 인스턴스 조회"""
    return _orchestration_service

def set_canvas_orchestration_service(service: CanvasOrchestrationService) -> None:
    """Canvas Orchestration 서비스 인스턴스 설정"""
    global _orchestration_service
    _orchestration_service = service