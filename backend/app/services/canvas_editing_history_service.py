"""
Canvas 편집 히스토리 서비스 v1.0

특징:
- 완전한 실행 취소/다시 실행 시스템
- 편집 작업 추적 및 관리
- 메모리 최적화된 히스토리 저장
- 브랜치 히스토리 지원
- 자동 병합 및 최적화
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import asyncio
from pathlib import Path
import pickle
import gzip
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import desc, asc, and_, or_
from app.db.session import get_db
from app.db.models.canvas import Canvas
from app.db.models.canvas_history import CanvasHistory, EditAction, HistorySnapshot
from app.core.config import get_settings

settings = get_settings()

# ======= 편집 액션 타입 =======

class ActionType(str, Enum):
    # 텍스트 관련
    TEXT_ADD = "text_add"
    TEXT_EDIT = "text_edit"
    TEXT_DELETE = "text_delete"
    TEXT_STYLE = "text_style"
    
    # 이미지 관련
    IMAGE_ADD = "image_add"
    IMAGE_MOVE = "image_move"
    IMAGE_RESIZE = "image_resize"
    IMAGE_DELETE = "image_delete"
    IMAGE_FILTER = "image_filter"
    IMAGE_CROP = "image_crop"
    
    # 도형 관련
    SHAPE_ADD = "shape_add"
    SHAPE_EDIT = "shape_edit"
    SHAPE_DELETE = "shape_delete"
    SHAPE_STYLE = "shape_style"
    
    # 브러시 관련
    BRUSH_STROKE = "brush_stroke"
    BRUSH_ERASE = "brush_erase"
    
    # 레이어 관련
    LAYER_ADD = "layer_add"
    LAYER_DELETE = "layer_delete"
    LAYER_MOVE = "layer_move"
    LAYER_STYLE = "layer_style"
    
    # 필터 관련
    FILTER_APPLY = "filter_apply"
    FILTER_REMOVE = "filter_remove"
    FILTER_ADJUST = "filter_adjust"
    
    # 선택 관련
    SELECTION_CREATE = "selection_create"
    SELECTION_MODIFY = "selection_modify"
    SELECTION_DELETE = "selection_delete"
    
    # 변형 관련
    TRANSFORM_MOVE = "transform_move"
    TRANSFORM_ROTATE = "transform_rotate"
    TRANSFORM_SCALE = "transform_scale"
    TRANSFORM_DISTORT = "transform_distort"
    
    # AI 작업 관련
    AI_BACKGROUND_REMOVE = "ai_background_remove"
    AI_OBJECT_REMOVE = "ai_object_remove"
    AI_INPAINTING = "ai_inpainting"
    AI_ENHANCE = "ai_enhance"
    
    # 배치 작업
    BATCH_OPERATION = "batch_operation"
    
    # 스냅샷
    SNAPSHOT_CREATE = "snapshot_create"


class ActionCategory(str, Enum):
    CONTENT = "content"      # 콘텐츠 변경
    STYLE = "style"         # 스타일 변경
    TRANSFORM = "transform"  # 변형 작업
    FILTER = "filter"       # 필터 작업
    AI = "ai"              # AI 작업
    SYSTEM = "system"      # 시스템 작업


@dataclass
class EditActionData:
    """편집 액션 데이터"""
    action_id: str
    action_type: ActionType
    category: ActionCategory
    timestamp: datetime
    element_id: Optional[str] = None
    element_type: Optional[str] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    can_undo: bool = True
    can_redo: bool = True
    description: str = ""
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class HistoryBranch:
    """히스토리 브랜치"""
    branch_id: str
    parent_action_id: Optional[str]
    actions: List[EditActionData]
    created_at: datetime
    name: str = ""
    description: str = ""


@dataclass
class HistoryState:
    """현재 히스토리 상태"""
    canvas_id: str
    current_action_index: int
    current_branch_id: str
    total_actions: int
    can_undo: bool
    can_redo: bool
    memory_usage: int  # bytes


# ======= 메인 히스토리 서비스 =======

class CanvasEditingHistoryService:
    """Canvas 편집 히스토리 관리 서비스"""
    
    def __init__(self):
        self.max_history_size = 100  # 최대 히스토리 크기
        self.max_memory_mb = 50      # 최대 메모리 사용량 (MB)
        self.snapshot_interval = 20  # 스냅샷 생성 간격
        self.cleanup_interval = 3600 # 정리 작업 간격 (초)
        
        # 메모리 캐시
        self._action_cache: Dict[str, List[EditActionData]] = {}
        self._branch_cache: Dict[str, List[HistoryBranch]] = {}
        self._snapshot_cache: Dict[str, Any] = {}
        
        # 성능 통계
        self._stats = {
            "total_actions": 0,
            "undo_count": 0,
            "redo_count": 0,
            "snapshot_count": 0,
            "memory_optimizations": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # 백그라운드 작업
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_background_tasks()

    # ======= 액션 기록 =======

    async def record_action(
        self,
        canvas_id: str,
        action_type: ActionType,
        element_id: Optional[str] = None,
        element_type: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        description: str = "",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> str:
        """편집 액션을 기록합니다."""
        
        async with self._get_db_session(db) as session:
            action_data = EditActionData(
                action_id=str(uuid.uuid4()),
                action_type=action_type,
                category=self._get_action_category(action_type),
                timestamp=datetime.utcnow(),
                element_id=element_id,
                element_type=element_type,
                before_state=before_state,
                after_state=after_state,
                metadata=metadata or {},
                description=description or self._generate_description(action_type),
                user_id=user_id,
                session_id=session_id
            )

            # 데이터베이스에 저장
            await self._save_action_to_db(session, canvas_id, action_data)
            
            # 메모리 캐시 업데이트
            await self._update_action_cache(canvas_id, action_data)
            
            # 스냅샷 생성 체크
            await self._check_snapshot_creation(canvas_id, session)
            
            # 메모리 최적화 체크
            await self._check_memory_optimization(canvas_id)
            
            self._stats["total_actions"] += 1
            
            print(f"✅ 편집 액션 기록: {action_type.value} ({action_data.action_id})")
            return action_data.action_id

    async def _save_action_to_db(
        self,
        session: AsyncSession,
        canvas_id: str,
        action_data: EditActionData
    ) -> None:
        """액션을 데이터베이스에 저장합니다."""
        
        edit_action = EditAction(
            id=action_data.action_id,
            canvas_id=canvas_id,
            action_type=action_data.action_type.value,
            category=action_data.category.value,
            element_id=action_data.element_id,
            element_type=action_data.element_type,
            before_state=action_data.before_state,
            after_state=action_data.after_state,
            metadata=action_data.metadata,
            description=action_data.description,
            can_undo=action_data.can_undo,
            can_redo=action_data.can_redo,
            user_id=action_data.user_id,
            session_id=action_data.session_id,
            timestamp=action_data.timestamp
        )
        
        session.add(edit_action)
        await session.commit()

    # ======= 실행 취소/다시 실행 =======

    async def undo(
        self,
        canvas_id: str,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[EditActionData]:
        """마지막 액션을 실행 취소합니다."""
        
        async with self._get_db_session(db) as session:
            # 현재 히스토리 상태 조회
            state = await self.get_history_state(canvas_id, session)
            
            if not state.can_undo:
                print(f"⚠️ 실행 취소할 작업이 없습니다: {canvas_id}")
                return None
            
            # 실행 취소할 액션 조회
            actions = await self._get_canvas_actions(canvas_id, session)
            if state.current_action_index < 0 or state.current_action_index >= len(actions):
                return None
                
            action_to_undo = actions[state.current_action_index]
            
            if not action_to_undo.can_undo:
                print(f"⚠️ 실행 취소할 수 없는 작업: {action_to_undo.action_type}")
                return None
            
            # 실제 실행 취소 처리
            success = await self._perform_undo(canvas_id, action_to_undo, session)
            
            if success:
                # 히스토리 포인터 이동
                await self._update_history_pointer(canvas_id, state.current_action_index - 1, session)
                
                # 실행 취소 액션 기록
                await self._record_undo_action(canvas_id, action_to_undo, user_id, session)
                
                self._stats["undo_count"] += 1
                print(f"⏪ 실행 취소 완료: {action_to_undo.action_type.value}")
                
                return action_to_undo
            
            return None

    async def redo(
        self,
        canvas_id: str,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[EditActionData]:
        """다음 액션을 다시 실행합니다."""
        
        async with self._get_db_session(db) as session:
            # 현재 히스토리 상태 조회
            state = await self.get_history_state(canvas_id, session)
            
            if not state.can_redo:
                print(f"⚠️ 다시 실행할 작업이 없습니다: {canvas_id}")
                return None
            
            # 다시 실행할 액션 조회
            actions = await self._get_canvas_actions(canvas_id, session)
            next_index = state.current_action_index + 1
            
            if next_index >= len(actions):
                return None
                
            action_to_redo = actions[next_index]
            
            if not action_to_redo.can_redo:
                print(f"⚠️ 다시 실행할 수 없는 작업: {action_to_redo.action_type}")
                return None
            
            # 실제 다시 실행 처리
            success = await self._perform_redo(canvas_id, action_to_redo, session)
            
            if success:
                # 히스토리 포인터 이동
                await self._update_history_pointer(canvas_id, next_index, session)
                
                # 다시 실행 액션 기록
                await self._record_redo_action(canvas_id, action_to_redo, user_id, session)
                
                self._stats["redo_count"] += 1
                print(f"⏩ 다시 실행 완료: {action_to_redo.action_type.value}")
                
                return action_to_redo
            
            return None

    async def _perform_undo(
        self,
        canvas_id: str,
        action: EditActionData,
        session: AsyncSession
    ) -> bool:
        """실제 실행 취소를 수행합니다."""
        
        try:
            if action.before_state is None:
                print(f"⚠️ 복원할 이전 상태가 없습니다: {action.action_id}")
                return False
            
            # Canvas 상태를 이전 상태로 복원
            await self._restore_canvas_state(canvas_id, action.before_state, session)
            
            return True
            
        except Exception as e:
            print(f"❌ 실행 취소 실패: {action.action_id} - {e}")
            return False

    async def _perform_redo(
        self,
        canvas_id: str,
        action: EditActionData,
        session: AsyncSession
    ) -> bool:
        """실제 다시 실행을 수행합니다."""
        
        try:
            if action.after_state is None:
                print(f"⚠️ 복원할 이후 상태가 없습니다: {action.action_id}")
                return False
            
            # Canvas 상태를 이후 상태로 복원
            await self._restore_canvas_state(canvas_id, action.after_state, session)
            
            return True
            
        except Exception as e:
            print(f"❌ 다시 실행 실패: {action.action_id} - {e}")
            return False

    # ======= 히스토리 관리 =======

    async def get_history_state(
        self,
        canvas_id: str,
        db: Optional[AsyncSession] = None
    ) -> HistoryState:
        """현재 히스토리 상태를 조회합니다."""
        
        async with self._get_db_session(db) as session:
            # 캔버스 히스토리 조회
            canvas_history = await self._get_canvas_history(canvas_id, session)
            
            if not canvas_history:
                return HistoryState(
                    canvas_id=canvas_id,
                    current_action_index=-1,
                    current_branch_id="main",
                    total_actions=0,
                    can_undo=False,
                    can_redo=False,
                    memory_usage=0
                )
            
            # 액션 목록 조회
            actions = await self._get_canvas_actions(canvas_id, session)
            total_actions = len(actions)
            current_index = canvas_history.current_action_index
            
            # 메모리 사용량 계산
            memory_usage = self._calculate_memory_usage(canvas_id)
            
            return HistoryState(
                canvas_id=canvas_id,
                current_action_index=current_index,
                current_branch_id=canvas_history.current_branch_id,
                total_actions=total_actions,
                can_undo=current_index >= 0,
                can_redo=current_index < total_actions - 1,
                memory_usage=memory_usage
            )

    async def get_action_history(
        self,
        canvas_id: str,
        limit: int = 50,
        offset: int = 0,
        action_types: Optional[List[ActionType]] = None,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> List[EditActionData]:
        """액션 히스토리를 조회합니다."""
        
        async with self._get_db_session(db) as session:
            # 캐시 확인
            cache_key = f"{canvas_id}:{limit}:{offset}"
            if cache_key in self._action_cache:
                self._stats["cache_hits"] += 1
                cached_actions = self._action_cache[cache_key]
                
                # 필터 적용
                filtered_actions = self._filter_actions(
                    cached_actions, action_types, user_id
                )
                return filtered_actions[offset:offset + limit]
            
            self._stats["cache_misses"] += 1
            
            # 데이터베이스 쿼리
            query = session.query(EditAction).filter(
                EditAction.canvas_id == canvas_id
            ).order_by(desc(EditAction.timestamp))
            
            if action_types:
                type_values = [t.value for t in action_types]
                query = query.filter(EditAction.action_type.in_(type_values))
            
            if user_id:
                query = query.filter(EditAction.user_id == user_id)
            
            query = query.offset(offset).limit(limit)
            results = await query.all()
            
            # 데이터 변환
            actions = []
            for result in results:
                action_data = EditActionData(
                    action_id=result.id,
                    action_type=ActionType(result.action_type),
                    category=ActionCategory(result.category),
                    timestamp=result.timestamp,
                    element_id=result.element_id,
                    element_type=result.element_type,
                    before_state=result.before_state,
                    after_state=result.after_state,
                    metadata=result.metadata or {},
                    can_undo=result.can_undo,
                    can_redo=result.can_redo,
                    description=result.description,
                    user_id=result.user_id,
                    session_id=result.session_id
                )
                actions.append(action_data)
            
            # 캐시 업데이트
            self._action_cache[cache_key] = actions
            
            return actions

    # ======= 스냅샷 관리 =======

    async def create_snapshot(
        self,
        canvas_id: str,
        name: str = "",
        description: str = "",
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> str:
        """현재 Canvas 상태의 스냅샷을 생성합니다."""
        
        async with self._get_db_session(db) as session:
            # 현재 Canvas 상태 캡처
            canvas_state = await self._capture_canvas_state(canvas_id, session)
            
            # 스냅샷 ID 생성
            snapshot_id = str(uuid.uuid4())
            
            # 압축된 상태 데이터 생성
            compressed_data = await self._compress_state_data(canvas_state)
            
            # 데이터베이스에 저장
            snapshot = HistorySnapshot(
                id=snapshot_id,
                canvas_id=canvas_id,
                name=name or f"스냅샷 {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                description=description,
                state_data=compressed_data,
                created_by=user_id,
                created_at=datetime.utcnow()
            )
            
            session.add(snapshot)
            await session.commit()
            
            # 캐시에 추가
            self._snapshot_cache[snapshot_id] = canvas_state
            
            self._stats["snapshot_count"] += 1
            print(f"📸 스냅샷 생성 완료: {snapshot_id} ({name})")
            
            return snapshot_id

    async def restore_snapshot(
        self,
        canvas_id: str,
        snapshot_id: str,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """스냅샷으로 Canvas 상태를 복원합니다."""
        
        async with self._get_db_session(db) as session:
            # 스냅샷 조회
            snapshot = await session.get(HistorySnapshot, snapshot_id)
            if not snapshot or snapshot.canvas_id != canvas_id:
                print(f"❌ 스냅샷을 찾을 수 없습니다: {snapshot_id}")
                return False
            
            try:
                # 캐시 확인
                if snapshot_id in self._snapshot_cache:
                    state_data = self._snapshot_cache[snapshot_id]
                else:
                    # 압축 해제
                    state_data = await self._decompress_state_data(snapshot.state_data)
                    self._snapshot_cache[snapshot_id] = state_data
                
                # 현재 상태를 백업
                current_state = await self._capture_canvas_state(canvas_id, session)
                
                # 스냅샷 상태로 복원
                await self._restore_canvas_state(canvas_id, state_data, session)
                
                # 복원 액션 기록
                await self.record_action(
                    canvas_id=canvas_id,
                    action_type=ActionType.SNAPSHOT_CREATE,
                    before_state=current_state,
                    after_state=state_data,
                    description=f"스냅샷 복원: {snapshot.name}",
                    user_id=user_id,
                    db=session
                )
                
                print(f"📷 스냅샷 복원 완료: {snapshot.name}")
                return True
                
            except Exception as e:
                print(f"❌ 스냅샷 복원 실패: {snapshot_id} - {e}")
                return False

    # ======= 브랜치 관리 =======

    async def create_branch(
        self,
        canvas_id: str,
        branch_name: str,
        from_action_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> str:
        """새로운 히스토리 브랜치를 생성합니다."""
        
        async with self._get_db_session(db) as session:
            branch_id = str(uuid.uuid4())
            
            branch = HistoryBranch(
                branch_id=branch_id,
                parent_action_id=from_action_id,
                actions=[],
                created_at=datetime.utcnow(),
                name=branch_name,
                description=f"브랜치 생성: {branch_name}"
            )
            
            # 캐시에 추가
            if canvas_id not in self._branch_cache:
                self._branch_cache[canvas_id] = []
            self._branch_cache[canvas_id].append(branch)
            
            print(f"🌿 브랜치 생성: {branch_name} ({branch_id})")
            return branch_id

    async def switch_branch(
        self,
        canvas_id: str,
        branch_id: str,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """다른 브랜치로 전환합니다."""
        
        async with self._get_db_session(db) as session:
            # 브랜치 존재 확인
            branches = self._branch_cache.get(canvas_id, [])
            target_branch = next((b for b in branches if b.branch_id == branch_id), None)
            
            if not target_branch:
                print(f"❌ 브랜치를 찾을 수 없습니다: {branch_id}")
                return False
            
            # 현재 브랜치 상태 저장
            await self._save_current_branch_state(canvas_id, session)
            
            # 대상 브랜치로 전환
            await self._switch_to_branch(canvas_id, target_branch, session)
            
            print(f"🔀 브랜치 전환: {target_branch.name}")
            return True

    # ======= 배치 작업 =======

    async def start_batch_operation(
        self,
        canvas_id: str,
        operation_name: str,
        user_id: Optional[str] = None
    ) -> str:
        """배치 작업을 시작합니다."""
        
        batch_id = str(uuid.uuid4())
        
        # 배치 시작 액션 기록
        await self.record_action(
            canvas_id=canvas_id,
            action_type=ActionType.BATCH_OPERATION,
            metadata={
                "batch_id": batch_id,
                "operation_name": operation_name,
                "status": "started"
            },
            description=f"배치 작업 시작: {operation_name}",
            user_id=user_id
        )
        
        print(f"📦 배치 작업 시작: {operation_name} ({batch_id})")
        return batch_id

    async def end_batch_operation(
        self,
        canvas_id: str,
        batch_id: str,
        user_id: Optional[str] = None
    ) -> None:
        """배치 작업을 종료합니다."""
        
        # 배치 종료 액션 기록
        await self.record_action(
            canvas_id=canvas_id,
            action_type=ActionType.BATCH_OPERATION,
            metadata={
                "batch_id": batch_id,
                "status": "completed"
            },
            description=f"배치 작업 완료: {batch_id}",
            user_id=user_id
        )
        
        print(f"✅ 배치 작업 완료: {batch_id}")

    # ======= 메모리 최적화 =======

    async def optimize_memory(self, canvas_id: str) -> Dict[str, Any]:
        """메모리 사용량을 최적화합니다."""
        
        start_usage = self._calculate_memory_usage(canvas_id)
        
        # 오래된 캐시 데이터 정리
        await self._cleanup_old_cache_data(canvas_id)
        
        # 불필요한 스냅샷 압축
        await self._compress_old_snapshots(canvas_id)
        
        # 중복 상태 데이터 병합
        await self._merge_duplicate_states(canvas_id)
        
        end_usage = self._calculate_memory_usage(canvas_id)
        saved = start_usage - end_usage
        
        self._stats["memory_optimizations"] += 1
        
        result = {
            "canvas_id": canvas_id,
            "before_mb": start_usage / (1024 * 1024),
            "after_mb": end_usage / (1024 * 1024),
            "saved_mb": saved / (1024 * 1024),
            "optimization_count": self._stats["memory_optimizations"]
        }
        
        print(f"🧹 메모리 최적화 완료: {saved / (1024 * 1024):.2f}MB 절약")
        return result

    async def get_statistics(self) -> Dict[str, Any]:
        """히스토리 서비스 통계를 조회합니다."""
        
        return {
            "total_actions": self._stats["total_actions"],
            "undo_count": self._stats["undo_count"],
            "redo_count": self._stats["redo_count"],
            "snapshot_count": self._stats["snapshot_count"],
            "memory_optimizations": self._stats["memory_optimizations"],
            "cache_performance": {
                "hits": self._stats["cache_hits"],
                "misses": self._stats["cache_misses"],
                "hit_ratio": self._stats["cache_hits"] / (self._stats["cache_hits"] + self._stats["cache_misses"]) if (self._stats["cache_hits"] + self._stats["cache_misses"]) > 0 else 0
            },
            "cached_canvases": len(self._action_cache),
            "cached_branches": sum(len(branches) for branches in self._branch_cache.values()),
            "cached_snapshots": len(self._snapshot_cache)
        }

    # ======= 헬퍼 메서드 =======

    def _get_action_category(self, action_type: ActionType) -> ActionCategory:
        """액션 타입에서 카테고리를 결정합니다."""
        
        content_actions = [
            ActionType.TEXT_ADD, ActionType.TEXT_DELETE,
            ActionType.IMAGE_ADD, ActionType.IMAGE_DELETE,
            ActionType.SHAPE_ADD, ActionType.SHAPE_DELETE,
            ActionType.BRUSH_STROKE, ActionType.BRUSH_ERASE
        ]
        
        style_actions = [
            ActionType.TEXT_STYLE, ActionType.SHAPE_STYLE,
            ActionType.LAYER_STYLE
        ]
        
        transform_actions = [
            ActionType.TRANSFORM_MOVE, ActionType.TRANSFORM_ROTATE,
            ActionType.TRANSFORM_SCALE, ActionType.TRANSFORM_DISTORT,
            ActionType.IMAGE_MOVE, ActionType.IMAGE_RESIZE
        ]
        
        filter_actions = [
            ActionType.FILTER_APPLY, ActionType.FILTER_REMOVE,
            ActionType.FILTER_ADJUST, ActionType.IMAGE_FILTER
        ]
        
        ai_actions = [
            ActionType.AI_BACKGROUND_REMOVE, ActionType.AI_OBJECT_REMOVE,
            ActionType.AI_INPAINTING, ActionType.AI_ENHANCE
        ]
        
        if action_type in content_actions:
            return ActionCategory.CONTENT
        elif action_type in style_actions:
            return ActionCategory.STYLE
        elif action_type in transform_actions:
            return ActionCategory.TRANSFORM
        elif action_type in filter_actions:
            return ActionCategory.FILTER
        elif action_type in ai_actions:
            return ActionCategory.AI
        else:
            return ActionCategory.SYSTEM

    def _generate_description(self, action_type: ActionType) -> str:
        """액션 타입에서 설명을 생성합니다."""
        
        descriptions = {
            ActionType.TEXT_ADD: "텍스트 추가",
            ActionType.TEXT_EDIT: "텍스트 편집",
            ActionType.TEXT_DELETE: "텍스트 삭제",
            ActionType.TEXT_STYLE: "텍스트 스타일 변경",
            ActionType.IMAGE_ADD: "이미지 추가",
            ActionType.IMAGE_MOVE: "이미지 이동",
            ActionType.IMAGE_RESIZE: "이미지 크기 조정",
            ActionType.IMAGE_DELETE: "이미지 삭제",
            ActionType.IMAGE_FILTER: "이미지 필터 적용",
            ActionType.IMAGE_CROP: "이미지 크롭",
            ActionType.SHAPE_ADD: "도형 추가",
            ActionType.SHAPE_EDIT: "도형 편집",
            ActionType.SHAPE_DELETE: "도형 삭제",
            ActionType.SHAPE_STYLE: "도형 스타일 변경",
            ActionType.BRUSH_STROKE: "브러시 스트로크",
            ActionType.BRUSH_ERASE: "브러시 지우기",
            ActionType.FILTER_APPLY: "필터 적용",
            ActionType.FILTER_REMOVE: "필터 제거",
            ActionType.AI_BACKGROUND_REMOVE: "AI 배경 제거",
            ActionType.AI_OBJECT_REMOVE: "AI 객체 제거",
            ActionType.BATCH_OPERATION: "배치 작업",
            ActionType.SNAPSHOT_CREATE: "스냅샷 생성"
        }
        
        return descriptions.get(action_type, action_type.value)

    async def _update_action_cache(self, canvas_id: str, action: EditActionData) -> None:
        """액션 캐시를 업데이트합니다."""
        
        # 캐시에서 해당 캔버스의 액션 목록 업데이트
        for key in list(self._action_cache.keys()):
            if key.startswith(f"{canvas_id}:"):
                cached_actions = self._action_cache[key]
                cached_actions.insert(0, action)  # 최신 액션을 맨 앞에 추가
                
                # 캐시 크기 제한
                if len(cached_actions) > self.max_history_size:
                    cached_actions.pop()

    def _calculate_memory_usage(self, canvas_id: str) -> int:
        """메모리 사용량을 계산합니다."""
        
        total_size = 0
        
        # 액션 캐시 크기
        for key, actions in self._action_cache.items():
            if key.startswith(f"{canvas_id}:"):
                for action in actions:
                    total_size += self._estimate_action_size(action)
        
        # 브랜치 캐시 크기
        branches = self._branch_cache.get(canvas_id, [])
        for branch in branches:
            for action in branch.actions:
                total_size += self._estimate_action_size(action)
        
        # 스냅샷 캐시 크기
        for snapshot_id, state_data in self._snapshot_cache.items():
            if isinstance(state_data, dict):
                total_size += len(json.dumps(state_data).encode())
        
        return total_size

    def _estimate_action_size(self, action: EditActionData) -> int:
        """액션의 메모리 사용량을 추정합니다."""
        
        size = 0
        
        # 기본 필드들
        size += len(action.action_id.encode()) if action.action_id else 0
        size += len(action.description.encode()) if action.description else 0
        size += len(action.element_id.encode()) if action.element_id else 0
        
        # 상태 데이터
        if action.before_state:
            size += len(json.dumps(action.before_state).encode())
        if action.after_state:
            size += len(json.dumps(action.after_state).encode())
        
        # 메타데이터
        if action.metadata:
            size += len(json.dumps(action.metadata).encode())
        
        return size

    @asynccontextmanager
    async def _get_db_session(self, db: Optional[AsyncSession] = None):
        """데이터베이스 세션을 가져옵니다."""
        if db:
            yield db
        else:
            async for session in get_db():
                try:
                    yield session
                finally:
                    await session.close()

    # ======= 백그라운드 작업 =======

    def _start_background_tasks(self) -> None:
        """백그라운드 작업을 시작합니다."""
        
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._background_cleanup())

    async def _background_cleanup(self) -> None:
        """백그라운드 정리 작업을 수행합니다."""
        
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # 메모리 사용량 체크
                total_memory = sum(
                    self._calculate_memory_usage(canvas_id) 
                    for canvas_id in set(
                        key.split(":")[0] for key in self._action_cache.keys()
                    )
                )
                
                if total_memory > self.max_memory_mb * 1024 * 1024:
                    print(f"🧹 메모리 사용량 초과, 정리 작업 시작: {total_memory / (1024 * 1024):.2f}MB")
                    
                    # 각 캔버스의 메모리 최적화
                    canvas_ids = set(
                        key.split(":")[0] for key in self._action_cache.keys()
                    )
                    
                    for canvas_id in canvas_ids:
                        await self.optimize_memory(canvas_id)
                
            except Exception as e:
                print(f"❌ 백그라운드 정리 작업 오류: {e}")

    async def cleanup(self) -> None:
        """서비스 정리를 수행합니다."""
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # 캐시 정리
        self._action_cache.clear()
        self._branch_cache.clear()
        self._snapshot_cache.clear()
        
        print("🧹 CanvasEditingHistoryService 정리 완료")


# ======= 전역 서비스 인스턴스 =======

_history_service: Optional[CanvasEditingHistoryService] = None

def get_canvas_editing_history_service() -> CanvasEditingHistoryService:
    """Canvas 편집 히스토리 서비스 인스턴스를 가져옵니다."""
    global _history_service
    if _history_service is None:
        _history_service = CanvasEditingHistoryService()
    return _history_service