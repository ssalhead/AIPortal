# Canvas Sync Service - 분산 트랜잭션 (Saga 패턴)
# AIPortal Canvas v5.0 - 통합 데이터 아키텍처

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canvas_models import (
    CanvasEventData, CanvasSyncRequest, CanvasSyncResult, CanvasSyncState,
    SyncStatus, CanvasOperationType, CanvasSyncError, CanvasConflictError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

class SagaStepStatus(str, Enum):
    """Saga 단계 상태"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"

@dataclass
class SagaStep:
    """Saga 단계 정의"""
    step_id: str
    step_name: str
    execute_func: callable
    compensate_func: Optional[callable] = None
    status: SagaStepStatus = SagaStepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None

class CanvasSyncSaga:
    """
    Canvas 동기화를 위한 Saga 패턴 구현
    
    동기화 단계:
    1. 로컬 변경사항 검증
    2. 서버 버전 충돌 검사
    3. 이벤트 병합 및 정렬
    4. 충돌 해결
    5. 서버 상태 업데이트
    6. 로컬 캐시 업데이트
    """
    
    def __init__(self, sync_request: CanvasSyncRequest, orchestrator):
        self.sync_request = sync_request
        self.orchestrator = orchestrator
        self.steps: List[SagaStep] = []
        self.saga_id = str(uuid4())
        self.started_at = datetime.utcnow()
        
        # 동기화 상태 추적
        self.local_events: List[CanvasEventData] = []
        self.server_events: List[CanvasEventData] = []
        self.merged_events: List[CanvasEventData] = []
        self.conflicts: List[Tuple[CanvasEventData, CanvasEventData]] = []
        
        self._init_saga_steps()
    
    def _init_saga_steps(self):
        """Saga 단계 초기화"""
        self.steps = [
            SagaStep(
                "validate_request",
                "동기화 요청 검증",
                self._step_validate_request,
                self._compensate_validate_request
            ),
            SagaStep(
                "load_server_state",
                "서버 상태 로드",
                self._step_load_server_state,
                self._compensate_load_server_state
            ),
            SagaStep(
                "detect_conflicts",
                "충돌 감지",
                self._step_detect_conflicts,
                self._compensate_detect_conflicts
            ),
            SagaStep(
                "resolve_conflicts",
                "충돌 해결",
                self._step_resolve_conflicts,
                self._compensate_resolve_conflicts
            ),
            SagaStep(
                "apply_changes",
                "변경사항 적용",
                self._step_apply_changes,
                self._compensate_apply_changes
            ),
            SagaStep(
                "update_cache",
                "캐시 업데이트",
                self._step_update_cache,
                self._compensate_update_cache
            )
        ]
    
    async def execute(self) -> CanvasSyncResult:
        """Saga 실행"""
        try:
            logger.info(f"Saga 시작: {self.saga_id} - Canvas {self.sync_request.canvas_id}")
            
            # 각 단계 순차 실행
            for step in self.steps:
                try:
                    logger.debug(f"Saga 단계 실행: {step.step_name}")
                    step.result = await step.execute_func()
                    step.status = SagaStepStatus.COMPLETED
                    
                except Exception as e:
                    step.status = SagaStepStatus.FAILED
                    step.error = str(e)
                    
                    # 실패 시 보상 트랜잭션 실행
                    await self._execute_compensations()
                    
                    return CanvasSyncResult(
                        success=False,
                        server_version=0,
                        message=f"Sync failed at step '{step.step_name}': {str(e)}",
                        next_sync_version=self.sync_request.local_version
                    )
            
            # 성공 시 결과 생성
            canvas_data = await self._get_final_canvas_data()
            
            result = CanvasSyncResult(
                success=True,
                canvas_data=canvas_data,
                server_version=canvas_data.version_number if canvas_data else 0,
                applied_events=self.merged_events,
                conflicted_events=[conflict[0] for conflict in self.conflicts],
                message="Sync completed successfully",
                next_sync_version=canvas_data.version_number if canvas_data else 0
            )
            
            logger.info(f"Saga 성공: {self.saga_id}")
            return result
            
        except Exception as e:
            logger.error(f"Saga 실패: {self.saga_id} - {str(e)}")
            await self._execute_compensations()
            raise CanvasSyncError(f"Saga execution failed: {str(e)}")
    
    async def _execute_compensations(self):
        """보상 트랜잭션 실행 (역순으로)"""
        logger.warning(f"Saga 보상 트랜잭션 실행: {self.saga_id}")
        
        # 완료된 단계들을 역순으로 보상
        for step in reversed(self.steps):
            if step.status == SagaStepStatus.COMPLETED and step.compensate_func:
                try:
                    await step.compensate_func()
                    step.status = SagaStepStatus.COMPENSATED
                    logger.debug(f"보상 완료: {step.step_name}")
                    
                except Exception as e:
                    logger.error(f"보상 실패: {step.step_name} - {str(e)}")
    
    # ===== Saga 단계 구현 =====
    
    async def _step_validate_request(self) -> Dict[str, Any]:
        """1단계: 동기화 요청 검증"""
        request = self.sync_request
        
        # 필수 필드 검증
        if not request.canvas_id or not request.client_id:
            raise ValueError("Missing required fields in sync request")
        
        # 버전 유효성 검증
        if request.local_version < 0:
            raise ValueError("Invalid local version")
        
        return {"validated": True, "canvas_id": request.canvas_id}
    
    async def _compensate_validate_request(self):
        """1단계 보상: 검증 상태 정리"""
        pass  # 검증 단계는 보상할 것이 없음
    
    async def _step_load_server_state(self) -> Dict[str, Any]:
        """2단계: 서버 상태 로드"""
        canvas_id = self.sync_request.canvas_id
        
        # 서버에서 현재 Canvas 상태 조회
        canvas_result = await self.orchestrator.get_canvas(
            canvas_id, 
            UUID('00000000-0000-0000-0000-000000000000'),  # 시스템 사용자
            include_events=True
        )
        
        if not canvas_result.success:
            raise CanvasSyncError(f"Failed to load server state: {canvas_result.error_message}")
        
        self.server_canvas = canvas_result.canvas_data
        
        # 로컬 버전 이후의 서버 이벤트 조회
        events_since = self.sync_request.events_since_version or self.sync_request.local_version
        self.server_events = await self.orchestrator.event_service.get_canvas_events(
            canvas_id, 
            since_version=events_since,
            limit=1000
        )
        
        return {
            "server_version": self.server_canvas.version_number,
            "server_events_count": len(self.server_events)
        }
    
    async def _compensate_load_server_state(self):
        """2단계 보상: 로드된 서버 상태 정리"""
        self.server_canvas = None
        self.server_events = []
    
    async def _step_detect_conflicts(self) -> Dict[str, Any]:
        """3단계: 충돌 감지"""
        conflicts_found = 0
        
        # 로컬 이벤트가 있다고 가정 (실제로는 요청에서 전달받아야 함)
        # 현재는 서버 이벤트만으로 충돌 검사
        
        # 동일한 타겟에 대한 동시 변경사항 감지
        target_changes = {}  # target_id -> [events]
        
        for event in self.server_events:
            target_key = f"{event.target_type.value}:{event.target_id}"
            
            if target_key not in target_changes:
                target_changes[target_key] = []
            
            target_changes[target_key].append(event)
        
        # 동일 타겟에 여러 변경사항이 있으면 잠재적 충돌
        for target_key, events in target_changes.items():
            if len(events) > 1:
                # 시간 간격이 짧은 경우 충돌로 판단
                events.sort(key=lambda x: x.timestamp)
                for i in range(len(events) - 1):
                    time_diff = events[i + 1].timestamp - events[i].timestamp
                    if time_diff.total_seconds() < 5:  # 5초 이내 동시 변경
                        self.conflicts.append((events[i], events[i + 1]))
                        conflicts_found += 1
        
        logger.info(f"충돌 감지 완료: {conflicts_found}개")
        return {"conflicts_count": conflicts_found}
    
    async def _compensate_detect_conflicts(self):
        """3단계 보상: 충돌 감지 상태 정리"""
        self.conflicts = []
    
    async def _step_resolve_conflicts(self) -> Dict[str, Any]:
        """4단계: 충돌 해결"""
        resolved_count = 0
        
        for conflict_pair in self.conflicts:
            event1, event2 = conflict_pair
            
            # 간단한 충돌 해결 전략: 최신 타임스탬프 우선
            if event1.timestamp > event2.timestamp:
                winner, loser = event1, event2
            else:
                winner, loser = event2, event1
            
            # 승자 이벤트를 병합 리스트에 추가
            self.merged_events.append(winner)
            resolved_count += 1
            
            logger.debug(f"충돌 해결: {winner.event_id} wins over {loser.event_id}")
        
        # 충돌하지 않은 이벤트들도 병합 리스트에 추가
        conflict_event_ids = set()
        for event1, event2 in self.conflicts:
            conflict_event_ids.add(event1.event_id)
            conflict_event_ids.add(event2.event_id)
        
        for event in self.server_events:
            if event.event_id not in conflict_event_ids:
                self.merged_events.append(event)
        
        # 시간순 정렬
        self.merged_events.sort(key=lambda x: x.timestamp)
        
        logger.info(f"충돌 해결 완료: {resolved_count}개 해결, {len(self.merged_events)}개 이벤트 병합")
        return {"resolved_count": resolved_count, "merged_events": len(self.merged_events)}
    
    async def _compensate_resolve_conflicts(self):
        """4단계 보상: 충돌 해결 상태 정리"""
        self.merged_events = []
    
    async def _step_apply_changes(self) -> Dict[str, Any]:
        """5단계: 변경사항 적용"""
        if not self.merged_events:
            return {"applied_count": 0}
        
        # Canvas 데이터에 병합된 이벤트들 순차 적용
        canvas_data = self.server_canvas
        applied_count = 0
        
        for event in self.merged_events:
            try:
                await self.orchestrator._apply_operation(canvas_data, event)
                applied_count += 1
                
            except Exception as e:
                logger.error(f"이벤트 적용 실패 {event.event_id}: {str(e)}")
                # 일부 실패해도 계속 진행
        
        # 버전 업데이트
        if applied_count > 0:
            canvas_data.version_number = max(
                canvas_data.version_number,
                max(event.version_number for event in self.merged_events if event.version_number)
            )
            canvas_data.updated_at = datetime.utcnow()
        
        logger.info(f"변경사항 적용 완료: {applied_count}개")
        return {"applied_count": applied_count}
    
    async def _compensate_apply_changes(self):
        """5단계 보상: 변경사항 롤백"""
        # 실제로는 이전 상태로 복원해야 하지만
        # 현재는 서버 상태 다시 로드로 대체
        if hasattr(self, 'server_canvas'):
            canvas_result = await self.orchestrator.get_canvas(
                self.sync_request.canvas_id,
                UUID('00000000-0000-0000-0000-000000000000')
            )
            if canvas_result.success:
                self.server_canvas = canvas_result.canvas_data
    
    async def _step_update_cache(self) -> Dict[str, Any]:
        """6단계: 캐시 업데이트"""
        canvas_id = self.sync_request.canvas_id
        
        # 업데이트된 Canvas 데이터를 캐시에 저장
        await self.orchestrator.cache_manager.set_canvas(canvas_id, self.server_canvas)
        
        # 클라이언트별 동기화 상태 업데이트
        sync_state = CanvasSyncState(
            canvas_id=canvas_id,
            status=SyncStatus.SUCCESS,
            local_version=self.server_canvas.version_number,
            server_version=self.server_canvas.version_number,
            last_sync_version=self.server_canvas.version_number,
            last_sync_time=datetime.utcnow(),
            sync_in_progress=False
        )
        
        # 동기화 상태 캐시에 저장
        await self.orchestrator.cache_manager.set_sync_state(
            canvas_id, 
            self.sync_request.client_id, 
            sync_state
        )
        
        logger.info(f"캐시 업데이트 완료: Canvas {canvas_id}")
        return {"cache_updated": True}
    
    async def _compensate_update_cache(self):
        """6단계 보상: 캐시 무효화"""
        await self.orchestrator.cache_manager.invalidate_canvas(self.sync_request.canvas_id)
    
    async def _get_final_canvas_data(self):
        """최종 Canvas 데이터 조회"""
        return getattr(self, 'server_canvas', None)

class CanvasSyncService:
    """
    Canvas 동기화 서비스
    
    주요 역할:
    1. 분산 동기화 조정
    2. Saga 패턴 기반 트랜잭션 관리
    3. 충돌 감지 및 자동 해결
    4. 실시간 협업 지원
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        
        # 진행 중인 Saga 추적
        self._active_sagas: Dict[str, CanvasSyncSaga] = {}
        
        # 충돌 해결 전략
        self._conflict_resolvers = {
            'last_write_wins': self._resolve_last_write_wins,
            'user_priority': self._resolve_user_priority,
            'merge_changes': self._resolve_merge_changes,
        }
    
    async def sync_canvas(
        self, 
        request: CanvasSyncRequest, 
        user_id: UUID,
        orchestrator
    ) -> CanvasSyncResult:
        """
        Canvas 동기화 실행
        
        특징:
        - Saga 패턴 기반 트랜잭션
        - 자동 충돌 해결
        - 실시간 협업 지원
        """
        saga_id = None
        
        try:
            # 동시 동기화 방지 검사
            if await self._is_sync_in_progress(request.canvas_id, request.client_id):
                return CanvasSyncResult(
                    success=False,
                    server_version=0,
                    message="Sync already in progress for this client",
                    next_sync_version=request.local_version
                )
            
            # 새 Saga 생성 및 실행
            saga = CanvasSyncSaga(request, orchestrator)
            saga_id = saga.saga_id
            
            # 활성 Saga 목록에 추가
            self._active_sagas[saga_id] = saga
            
            # Saga 실행
            result = await saga.execute()
            
            logger.info(f"Canvas 동기화 성공: {request.canvas_id} -> v{result.server_version}")
            return result
            
        except Exception as e:
            logger.error(f"Canvas 동기화 실패 {request.canvas_id}: {str(e)}")
            
            return CanvasSyncResult(
                success=False,
                server_version=0,
                message=f"Sync failed: {str(e)}",
                next_sync_version=request.local_version
            )
            
        finally:
            # 활성 Saga 목록에서 제거
            if saga_id and saga_id in self._active_sagas:
                del self._active_sagas[saga_id]
    
    async def count_pending_conflicts(self, canvas_id: UUID) -> int:
        """대기 중인 충돌 수 조회"""
        try:
            # 활성 Saga에서 충돌 수 집계
            pending_conflicts = 0
            
            for saga in self._active_sagas.values():
                if saga.sync_request.canvas_id == canvas_id:
                    pending_conflicts += len(saga.conflicts)
            
            return pending_conflicts
            
        except Exception as e:
            logger.error(f"충돌 수 조회 실패 {canvas_id}: {str(e)}")
            return 0
    
    async def get_sync_status(
        self, 
        canvas_id: UUID, 
        client_id: str
    ) -> Optional[CanvasSyncState]:
        """클라이언트의 동기화 상태 조회"""
        # 실제로는 캐시에서 조회
        # 현재는 기본 상태 반환
        return CanvasSyncState(
            canvas_id=canvas_id,
            status=SyncStatus.IDLE
        )
    
    async def force_sync(
        self, 
        canvas_id: UUID, 
        client_id: str,
        orchestrator
    ) -> CanvasSyncResult:
        """강제 동기화 (충돌 무시)"""
        try:
            # 현재 서버 버전으로 강제 동기화 요청 생성
            canvas_result = await orchestrator.get_canvas(
                canvas_id, 
                UUID('00000000-0000-0000-0000-000000000000')
            )
            
            if not canvas_result.success:
                raise CanvasSyncError("Cannot load server state for force sync")
            
            server_version = canvas_result.canvas_data.version_number
            
            force_request = CanvasSyncRequest(
                canvas_id=canvas_id,
                local_version=0,  # 0으로 설정하여 모든 서버 변경사항 받기
                client_id=client_id
            )
            
            return await self.sync_canvas(force_request, UUID('00000000-0000-0000-0000-000000000000'), orchestrator)
            
        except Exception as e:
            logger.error(f"강제 동기화 실패 {canvas_id}: {str(e)}")
            raise CanvasSyncError(f"Force sync failed: {str(e)}")
    
    async def _is_sync_in_progress(self, canvas_id: UUID, client_id: str) -> bool:
        """동기화 진행 중 여부 확인"""
        for saga in self._active_sagas.values():
            if (saga.sync_request.canvas_id == canvas_id and 
                saga.sync_request.client_id == client_id):
                return True
        return False
    
    # ===== 충돌 해결 전략 =====
    
    async def _resolve_last_write_wins(
        self, 
        conflicts: List[Tuple[CanvasEventData, CanvasEventData]]
    ) -> List[CanvasEventData]:
        """최종 쓰기 우선 전략"""
        resolved = []
        
        for event1, event2 in conflicts:
            winner = event1 if event1.timestamp > event2.timestamp else event2
            resolved.append(winner)
        
        return resolved
    
    async def _resolve_user_priority(
        self, 
        conflicts: List[Tuple[CanvasEventData, CanvasEventData]]
    ) -> List[CanvasEventData]:
        """사용자 우선순위 기반 해결"""
        # 실제로는 사용자 권한이나 역할을 확인해야 함
        # 현재는 최종 쓰기 우선과 동일
        return await self._resolve_last_write_wins(conflicts)
    
    async def _resolve_merge_changes(
        self, 
        conflicts: List[Tuple[CanvasEventData, CanvasEventData]]
    ) -> List[CanvasEventData]:
        """변경사항 병합 전략"""
        resolved = []
        
        for event1, event2 in conflicts:
            # 서로 다른 속성을 변경한 경우 병합 시도
            if self._can_merge_events(event1, event2):
                merged_event = self._merge_events(event1, event2)
                resolved.append(merged_event)
            else:
                # 병합 불가능하면 최종 쓰기 우선
                winner = event1 if event1.timestamp > event2.timestamp else event2
                resolved.append(winner)
        
        return resolved
    
    def _can_merge_events(
        self, 
        event1: CanvasEventData, 
        event2: CanvasEventData
    ) -> bool:
        """이벤트 병합 가능 여부 판단"""
        # 동일한 타겟에 대한 업데이트 이벤트만 병합 가능
        if (event1.event_type != CanvasOperationType.UPDATE or 
            event2.event_type != CanvasOperationType.UPDATE):
            return False
        
        if event1.target_id != event2.target_id:
            return False
        
        # 변경된 속성이 겹치지 않으면 병합 가능
        keys1 = set(event1.new_data.keys()) if event1.new_data else set()
        keys2 = set(event2.new_data.keys()) if event2.new_data else set()
        
        return len(keys1.intersection(keys2)) == 0
    
    def _merge_events(
        self, 
        event1: CanvasEventData, 
        event2: CanvasEventData
    ) -> CanvasEventData:
        """이벤트 병합"""
        # 나중 이벤트를 기준으로 병합
        base_event = event1 if event1.timestamp > event2.timestamp else event2
        other_event = event2 if base_event == event1 else event1
        
        # 새 이벤트 생성
        merged_event = CanvasEventData(
            canvas_id=base_event.canvas_id,
            user_id=base_event.user_id,  # 기준 이벤트의 사용자
            event_type=base_event.event_type,
            target_type=base_event.target_type,
            target_id=base_event.target_id,
            new_data={**other_event.new_data, **base_event.new_data},  # 병합
            old_data=base_event.old_data,
            timestamp=base_event.timestamp,
            version_number=max(base_event.version_number, other_event.version_number)
        )
        
        return merged_event
    
    async def get_saga_statistics(self) -> Dict[str, Any]:
        """Saga 실행 통계"""
        try:
            active_count = len(self._active_sagas)
            
            # Saga별 상태 통계
            saga_statuses = {}
            for saga in self._active_sagas.values():
                for step in saga.steps:
                    status = step.status.value
                    saga_statuses[status] = saga_statuses.get(status, 0) + 1
            
            return {
                'active_sagas': active_count,
                'step_statuses': saga_statuses,
                'conflict_resolution_strategies': list(self._conflict_resolvers.keys())
            }
            
        except Exception as e:
            logger.error(f"Saga 통계 조회 실패: {str(e)}")
            return {'error': str(e)}
    
    async def cleanup_completed_sagas(self):
        """완료된 Saga 정리 (백그라운드 작업)"""
        try:
            current_time = datetime.utcnow()
            cleanup_threshold = timedelta(hours=1)
            
            completed_sagas = []
            
            for saga_id, saga in self._active_sagas.items():
                if current_time - saga.started_at > cleanup_threshold:
                    completed_sagas.append(saga_id)
            
            for saga_id in completed_sagas:
                del self._active_sagas[saga_id]
            
            if completed_sagas:
                logger.info(f"완료된 Saga {len(completed_sagas)}개 정리")
                
        except Exception as e:
            logger.error(f"Saga 정리 실패: {str(e)}")