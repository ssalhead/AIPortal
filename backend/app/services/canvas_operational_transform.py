"""
Canvas Operational Transformation (OT) Engine v1.0
Canvas 협업을 위한 고성능 충돌 해결 및 상태 동기화 시스템
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timezone
import uuid
import json
from copy import deepcopy

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ======= OT 연산 타입 정의 =======

class OperationType(str, Enum):
    """Canvas 작업 연산 타입"""
    # 아이템 생성/삭제
    CREATE_ITEM = "create_item"
    DELETE_ITEM = "delete_item"
    
    # 아이템 수정
    UPDATE_POSITION = "update_position"
    UPDATE_SIZE = "update_size"
    UPDATE_CONTENT = "update_content"
    UPDATE_STYLE = "update_style"
    
    # 텍스트 편집
    TEXT_INSERT = "text_insert"
    TEXT_DELETE = "text_delete"
    TEXT_REPLACE = "text_replace"
    
    # 레이어 관리
    LAYER_MOVE = "layer_move"
    LAYER_LOCK = "layer_lock"
    
    # 그룹 관리
    GROUP_CREATE = "group_create"
    GROUP_UNGROUP = "group_ungroup"
    
    # 필터/변형
    APPLY_FILTER = "apply_filter"
    APPLY_TRANSFORM = "apply_transform"

class OperationPriority(int, Enum):
    """연산 우선순위 (숫자가 클수록 높은 우선순위)"""
    DELETE_ITEM = 100      # 삭제 최우선
    CREATE_ITEM = 90       # 생성 우선
    UPDATE_CONTENT = 80    # 내용 수정
    UPDATE_POSITION = 70   # 위치 변경
    UPDATE_SIZE = 60       # 크기 변경
    UPDATE_STYLE = 50      # 스타일 변경
    TEXT_OPERATIONS = 40   # 텍스트 편집
    LAYER_OPERATIONS = 30  # 레이어 관리
    FILTER_TRANSFORM = 20  # 필터/변형
    GROUP_OPERATIONS = 10  # 그룹 관리

@dataclass
class CanvasOperation:
    """Canvas OT 연산 객체"""
    id: str
    type: OperationType
    target_id: str          # 대상 아이템 ID
    user_id: str
    timestamp: datetime
    state_vector: Dict[str, int]  # 상태 벡터 {user_id: operation_count}
    data: Dict[str, Any]    # 연산 데이터
    priority: int = 0
    dependencies: List[str] = None  # 의존성 있는 연산 ID들
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.priority == 0:
            self.priority = self._calculate_priority()
    
    def _calculate_priority(self) -> int:
        """연산 타입에 따른 우선순위 계산"""
        priority_map = {
            OperationType.DELETE_ITEM: OperationPriority.DELETE_ITEM,
            OperationType.CREATE_ITEM: OperationPriority.CREATE_ITEM,
            OperationType.UPDATE_CONTENT: OperationPriority.UPDATE_CONTENT,
            OperationType.UPDATE_POSITION: OperationPriority.UPDATE_POSITION,
            OperationType.UPDATE_SIZE: OperationPriority.UPDATE_SIZE,
            OperationType.UPDATE_STYLE: OperationPriority.UPDATE_STYLE,
            OperationType.TEXT_INSERT: OperationPriority.TEXT_OPERATIONS,
            OperationType.TEXT_DELETE: OperationPriority.TEXT_OPERATIONS,
            OperationType.TEXT_REPLACE: OperationPriority.TEXT_OPERATIONS,
            OperationType.LAYER_MOVE: OperationPriority.LAYER_OPERATIONS,
            OperationType.LAYER_LOCK: OperationPriority.LAYER_OPERATIONS,
            OperationType.APPLY_FILTER: OperationPriority.FILTER_TRANSFORM,
            OperationType.APPLY_TRANSFORM: OperationPriority.FILTER_TRANSFORM,
            OperationType.GROUP_CREATE: OperationPriority.GROUP_OPERATIONS,
            OperationType.GROUP_UNGROUP: OperationPriority.GROUP_OPERATIONS,
        }
        return priority_map.get(self.type, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['type'] = self.type.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanvasOperation':
        """딕셔너리에서 생성"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['type'] = OperationType(data['type'])
        return cls(**data)

# ======= OT 변환 함수들 =======

class CanvasOTTransform:
    """Canvas OT 변환 함수 모음"""
    
    @staticmethod
    def transform_create_create(op1: CanvasOperation, op2: CanvasOperation) -> Tuple[CanvasOperation, CanvasOperation]:
        """CREATE vs CREATE 변환"""
        # 같은 ID로 생성 시도하는 경우 - timestamp 기준으로 결정
        if op1.target_id == op2.target_id:
            if op1.timestamp < op2.timestamp:
                # op1이 먼저 생성, op2는 무효화
                op2_transformed = CanvasOperation(
                    id=op2.id,
                    type=OperationType.UPDATE_CONTENT,  # 생성 → 업데이트로 변환
                    target_id=op2.target_id,
                    user_id=op2.user_id,
                    timestamp=op2.timestamp,
                    state_vector=op2.state_vector,
                    data=op2.data,
                    dependencies=[op1.id]
                )
                return op1, op2_transformed
            else:
                # op2가 먼저 생성, op1은 무효화
                op1_transformed = CanvasOperation(
                    id=op1.id,
                    type=OperationType.UPDATE_CONTENT,
                    target_id=op1.target_id,
                    user_id=op1.user_id,
                    timestamp=op1.timestamp,
                    state_vector=op1.state_vector,
                    data=op1.data,
                    dependencies=[op2.id]
                )
                return op1_transformed, op2
        
        # 다른 ID 생성은 충돌 없음
        return op1, op2
    
    @staticmethod
    def transform_delete_update(op1: CanvasOperation, op2: CanvasOperation) -> Tuple[CanvasOperation, Optional[CanvasOperation]]:
        """DELETE vs UPDATE 변환"""
        if op1.target_id == op2.target_id:
            # 같은 아이템에 대한 삭제 vs 업데이트
            if op1.timestamp < op2.timestamp:
                # 삭제가 먼저 - 업데이트 무효화
                return op1, None
            else:
                # 업데이트가 먼저 - 삭제 유지, 업데이트도 유지
                return op1, op2
        
        # 다른 아이템은 충돌 없음
        return op1, op2
    
    @staticmethod
    def transform_position_position(op1: CanvasOperation, op2: CanvasOperation) -> Tuple[CanvasOperation, CanvasOperation]:
        """POSITION vs POSITION 변환"""
        if op1.target_id == op2.target_id:
            # 같은 아이템 위치 변경 - 나중 것이 우선
            if op1.timestamp < op2.timestamp:
                return op1, op2  # op2가 최종 위치
            else:
                return op1, op2  # op1이 최종 위치 (원래 순서 유지)
        
        return op1, op2
    
    @staticmethod
    def transform_text_text(op1: CanvasOperation, op2: CanvasOperation) -> Tuple[CanvasOperation, CanvasOperation]:
        """TEXT vs TEXT 변환 (복잡한 텍스트 OT)"""
        if op1.target_id != op2.target_id:
            return op1, op2  # 다른 텍스트 아이템
        
        # 같은 텍스트 아이템에서의 동시 편집
        pos1 = op1.data.get('position', 0)
        pos2 = op2.data.get('position', 0)
        
        if op1.type == OperationType.TEXT_INSERT and op2.type == OperationType.TEXT_INSERT:
            # 동시 삽입
            if pos1 <= pos2:
                # op2의 위치를 op1 삽입 길이만큼 조정
                op2_data = deepcopy(op2.data)
                op2_data['position'] = pos2 + len(op1.data.get('text', ''))
                op2_transformed = CanvasOperation(
                    id=op2.id,
                    type=op2.type,
                    target_id=op2.target_id,
                    user_id=op2.user_id,
                    timestamp=op2.timestamp,
                    state_vector=op2.state_vector,
                    data=op2_data
                )
                return op1, op2_transformed
            else:
                # op1의 위치를 op2 삽입 길이만큼 조정
                op1_data = deepcopy(op1.data)
                op1_data['position'] = pos1 + len(op2.data.get('text', ''))
                op1_transformed = CanvasOperation(
                    id=op1.id,
                    type=op1.type,
                    target_id=op1.target_id,
                    user_id=op1.user_id,
                    timestamp=op1.timestamp,
                    state_vector=op1.state_vector,
                    data=op1_data
                )
                return op1_transformed, op2
        
        elif op1.type == OperationType.TEXT_DELETE and op2.type == OperationType.TEXT_DELETE:
            # 동시 삭제
            length1 = op1.data.get('length', 1)
            length2 = op2.data.get('length', 1)
            
            if pos1 + length1 <= pos2:
                # op2 위치 조정
                op2_data = deepcopy(op2.data)
                op2_data['position'] = pos2 - length1
                op2_transformed = CanvasOperation(
                    id=op2.id,
                    type=op2.type,
                    target_id=op2.target_id,
                    user_id=op2.user_id,
                    timestamp=op2.timestamp,
                    state_vector=op2.state_vector,
                    data=op2_data
                )
                return op1, op2_transformed
            elif pos2 + length2 <= pos1:
                # op1 위치 조정
                op1_data = deepcopy(op1.data)
                op1_data['position'] = pos1 - length2
                op1_transformed = CanvasOperation(
                    id=op1.id,
                    type=op1.type,
                    target_id=op1.target_id,
                    user_id=op1.user_id,
                    timestamp=op1.timestamp,
                    state_vector=op1.state_vector,
                    data=op1_data
                )
                return op1_transformed, op2
            else:
                # 겹치는 삭제 - 먼저 실행된 것 우선
                if op1.timestamp < op2.timestamp:
                    return op1, None
                else:
                    return None, op2
        
        # 삽입 vs 삭제
        elif op1.type == OperationType.TEXT_INSERT and op2.type == OperationType.TEXT_DELETE:
            if pos1 <= pos2:
                # 삽입 후 삭제 위치 조정
                op2_data = deepcopy(op2.data)
                op2_data['position'] = pos2 + len(op1.data.get('text', ''))
                op2_transformed = CanvasOperation(
                    id=op2.id,
                    type=op2.type,
                    target_id=op2.target_id,
                    user_id=op2.user_id,
                    timestamp=op2.timestamp,
                    state_vector=op2.state_vector,
                    data=op2_data
                )
                return op1, op2_transformed
            else:
                return op1, op2
        
        elif op1.type == OperationType.TEXT_DELETE and op2.type == OperationType.TEXT_INSERT:
            length1 = op1.data.get('length', 1)
            if pos2 >= pos1 + length1:
                # 삭제 후 삽입 위치 조정
                op2_data = deepcopy(op2.data)
                op2_data['position'] = pos2 - length1
                op2_transformed = CanvasOperation(
                    id=op2.id,
                    type=op2.type,
                    target_id=op2.target_id,
                    user_id=op2.user_id,
                    timestamp=op2.timestamp,
                    state_vector=op2.state_vector,
                    data=op2_data
                )
                return op1, op2_transformed
            else:
                return op1, op2
        
        return op1, op2

# ======= OT 엔진 메인 클래스 =======

class CanvasOperationalTransformEngine:
    """Canvas OT 엔진 - 충돌 해결 및 상태 동기화"""
    
    def __init__(self):
        self.operation_history: Dict[str, List[CanvasOperation]] = {}  # {conversation_id: operations}
        self.state_vectors: Dict[str, Dict[str, int]] = {}  # {conversation_id: {user_id: count}}
        self.pending_operations: Dict[str, List[CanvasOperation]] = {}  # 대기 중인 연산들
        self.transform_functions = {
            # 변환 함수 매핑
            (OperationType.CREATE_ITEM, OperationType.CREATE_ITEM): CanvasOTTransform.transform_create_create,
            (OperationType.DELETE_ITEM, OperationType.UPDATE_POSITION): CanvasOTTransform.transform_delete_update,
            (OperationType.DELETE_ITEM, OperationType.UPDATE_SIZE): CanvasOTTransform.transform_delete_update,
            (OperationType.DELETE_ITEM, OperationType.UPDATE_CONTENT): CanvasOTTransform.transform_delete_update,
            (OperationType.DELETE_ITEM, OperationType.UPDATE_STYLE): CanvasOTTransform.transform_delete_update,
            (OperationType.UPDATE_POSITION, OperationType.UPDATE_POSITION): CanvasOTTransform.transform_position_position,
            (OperationType.TEXT_INSERT, OperationType.TEXT_INSERT): CanvasOTTransform.transform_text_text,
            (OperationType.TEXT_INSERT, OperationType.TEXT_DELETE): CanvasOTTransform.transform_text_text,
            (OperationType.TEXT_DELETE, OperationType.TEXT_INSERT): CanvasOTTransform.transform_text_text,
            (OperationType.TEXT_DELETE, OperationType.TEXT_DELETE): CanvasOTTransform.transform_text_text,
        }
    
    def integrate_operation(
        self, 
        conversation_id: str, 
        operation: CanvasOperation
    ) -> List[CanvasOperation]:
        """
        새로운 연산을 기존 상태와 통합
        Returns: 실제 적용할 연산들의 리스트 (변환된 연산들)
        """
        logger.info(f"🔄 OT 연산 통합 시작: {operation.type} by {operation.user_id}")
        
        # 대화방 히스토리 초기화
        if conversation_id not in self.operation_history:
            self.operation_history[conversation_id] = []
            self.state_vectors[conversation_id] = {}
            self.pending_operations[conversation_id] = []
        
        # 상태 벡터 확인
        user_expected_state = operation.state_vector
        current_state = self.state_vectors[conversation_id]
        
        # 상태 벡터 불일치 검사 (동시성 제어)
        if self._has_causal_dependency(user_expected_state, current_state):
            # 대기 큐에 추가
            self.pending_operations[conversation_id].append(operation)
            logger.warning(f"⏸️ 연산 대기 큐 추가: {operation.id} (상태 불일치)")
            return []
        
        # 기존 연산들과 변환 수행
        transformed_operation = operation
        history = self.operation_history[conversation_id]
        
        for existing_op in reversed(history[-50:]):  # 최근 50개만 검사 (성능 최적화)
            if existing_op.user_id == operation.user_id:
                continue  # 같은 사용자의 연산은 변환 불필요
                
            # 변환 함수 적용
            transform_key = (existing_op.type, transformed_operation.type)
            reverse_key = (transformed_operation.type, existing_op.type)
            
            if transform_key in self.transform_functions:
                _, transformed_operation = self.transform_functions[transform_key](existing_op, transformed_operation)
            elif reverse_key in self.transform_functions:
                transformed_operation, _ = self.transform_functions[reverse_key](transformed_operation, existing_op)
            
            # 변환 후 연산이 무효화된 경우
            if transformed_operation is None:
                logger.info(f"❌ 연산 무효화: {operation.id}")
                return []
        
        # 히스토리에 추가
        self.operation_history[conversation_id].append(transformed_operation)
        
        # 상태 벡터 업데이트
        if transformed_operation.user_id not in self.state_vectors[conversation_id]:
            self.state_vectors[conversation_id][transformed_operation.user_id] = 0
        self.state_vectors[conversation_id][transformed_operation.user_id] += 1
        
        # 대기 중인 연산들 재검사
        resolved_operations = [transformed_operation]
        resolved_operations.extend(self._process_pending_operations(conversation_id))
        
        logger.info(f"✅ OT 연산 통합 완료: {len(resolved_operations)}개 연산 적용")
        return resolved_operations
    
    def _has_causal_dependency(
        self, 
        user_state: Dict[str, int], 
        current_state: Dict[str, int]
    ) -> bool:
        """인과 관계 의존성 검사"""
        for user_id, user_count in user_state.items():
            current_count = current_state.get(user_id, 0)
            if user_count > current_count:
                return True  # 미래 상태를 요구하는 연산
        return False
    
    def _process_pending_operations(self, conversation_id: str) -> List[CanvasOperation]:
        """대기 중인 연산들 재처리"""
        resolved = []
        remaining_pending = []
        
        for pending_op in self.pending_operations[conversation_id]:
            user_expected_state = pending_op.state_vector
            current_state = self.state_vectors[conversation_id]
            
            if not self._has_causal_dependency(user_expected_state, current_state):
                # 의존성 해결됨 - 재귀 통합
                newly_resolved = self.integrate_operation(conversation_id, pending_op)
                resolved.extend(newly_resolved)
            else:
                remaining_pending.append(pending_op)
        
        self.pending_operations[conversation_id] = remaining_pending
        return resolved
    
    def get_operation_history(self, conversation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """연산 히스토리 조회"""
        if conversation_id not in self.operation_history:
            return []
        
        operations = self.operation_history[conversation_id][-limit:]
        return [op.to_dict() for op in operations]
    
    def get_current_state_vector(self, conversation_id: str) -> Dict[str, int]:
        """현재 상태 벡터 조회"""
        return self.state_vectors.get(conversation_id, {}).copy()
    
    def cleanup_old_operations(self, conversation_id: str, max_history: int = 1000):
        """오래된 연산 히스토리 정리"""
        if conversation_id in self.operation_history:
            history = self.operation_history[conversation_id]
            if len(history) > max_history:
                self.operation_history[conversation_id] = history[-max_history:]
                logger.info(f"🧹 OT 히스토리 정리: {conversation_id} ({len(history)} → {max_history})")

# ======= 글로벌 OT 엔진 인스턴스 =======

canvas_ot_engine = CanvasOperationalTransformEngine()