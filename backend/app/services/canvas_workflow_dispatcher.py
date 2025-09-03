"""
Canvas 워크플로우 분기 디스패처
Create vs Edit 모드를 자동으로 결정하고 적절한 서비스로 라우팅
"""

from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.services.canvas_lifecycle_service import CanvasLifecycleService

logger = logging.getLogger(__name__)


class RequestSource(Enum):
    """요청 소스 타입"""
    CHAT = "chat"
    CANVAS = "canvas"
    API = "api"


class WorkflowMode(Enum):
    """워크플로우 모드"""
    CREATE = "create"
    EDIT = "edit"
    UNKNOWN = "unknown"


@dataclass
class ImageGenerationRequest:
    """이미지 생성 요청 데이터"""
    conversation_id: UUID
    user_id: UUID
    prompt: str
    source: RequestSource
    style: Optional[str] = "realistic"
    size: Optional[str] = "1024x1024"
    
    # Canvas 관련 (Edit 모드용)
    canvas_id: Optional[UUID] = None
    reference_image_id: Optional[UUID] = None
    evolution_type: Optional[str] = "variation"
    edit_mode_type: Optional[str] = "EDIT_MODE_INPAINT_INSERTION"
    
    # 추가 파라미터
    generation_params: Optional[Dict] = None
    metadata: Optional[Dict] = None


class CanvasWorkflowDispatcher:
    """
    Canvas 워크플로우 분기 디스패처
    
    역할:
    1. 요청 분석 및 모드 결정 (CREATE vs EDIT)
    2. 적절한 서비스로 라우팅
    3. 워크플로우 상태 추적
    4. 오류 처리 및 복구
    """
    
    def __init__(self):
        self.lifecycle_service = CanvasLifecycleService()
    
    async def dispatch_image_generation_request(
        self,
        db: AsyncSession,
        request: ImageGenerationRequest
    ) -> Dict[str, Any]:
        """
        이미지 생성 요청을 분석하고 적절한 워크플로우로 분기
        
        Args:
            db: 데이터베이스 세션
            request: 이미지 생성 요청 데이터
        
        Returns:
            처리 결과
        """
        try:
            logger.info(f"🔀 워크플로우 분기 시작 - 소스: {request.source.value}")
            
            # 1. 워크플로우 모드 결정
            workflow_mode = await self._determine_workflow_mode(db, request)
            
            logger.info(f"📍 결정된 워크플로우 모드: {workflow_mode.value}")
            
            # 2. 요청 검증
            validation_result = await self._validate_request(db, request, workflow_mode)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "workflow_mode": workflow_mode.value,
                    "request_source": request.source.value
                }
            
            # 3. 워크플로우별 처리
            if workflow_mode == WorkflowMode.CREATE:
                result = await self._handle_create_workflow(db, request)
            elif workflow_mode == WorkflowMode.EDIT:
                result = await self._handle_edit_workflow(db, request)
            else:
                return {
                    "success": False,
                    "error": "알 수 없는 워크플로우 모드입니다",
                    "workflow_mode": workflow_mode.value,
                    "request_source": request.source.value
                }
            
            # 4. 결과에 워크플로우 정보 추가
            if result:
                result.update({
                    "workflow_mode": workflow_mode.value,
                    "request_source": request.source.value,
                    "dispatch_timestamp": str(datetime.now())
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 워크플로우 분기 처리 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "workflow_mode": "unknown",
                "request_source": request.source.value if request.source else "unknown"
            }
    
    async def _determine_workflow_mode(
        self,
        db: AsyncSession,
        request: ImageGenerationRequest
    ) -> WorkflowMode:
        """
        요청 데이터를 분석하여 워크플로우 모드 결정
        
        결정 규칙:
        1. CHAT 소스 + Canvas ID 없음 → CREATE
        2. CANVAS 소스 + Canvas ID 있음 + 참조 이미지 있음 → EDIT
        3. API 소스 → 파라미터에 따라 결정
        """
        try:
            # Rule 1: 채팅에서 오는 모든 요청은 CREATE 모드
            if request.source == RequestSource.CHAT:
                if request.canvas_id or request.reference_image_id:
                    logger.warning("⚠️ 채팅 요청에 Canvas 정보가 포함되어 있음 - CREATE 모드로 강제 변경")
                return WorkflowMode.CREATE
            
            # Rule 2: Canvas에서 오는 요청 분석
            elif request.source == RequestSource.CANVAS:
                if request.canvas_id and request.reference_image_id:
                    # Canvas 및 참조 이미지 유효성 확인
                    if await self._verify_canvas_and_reference(db, request):
                        return WorkflowMode.EDIT
                    else:
                        logger.warning("⚠️ Canvas 또는 참조 이미지가 유효하지 않음 - CREATE 모드로 변경")
                        return WorkflowMode.CREATE
                else:
                    logger.info("ℹ️ Canvas 소스이지만 참조 정보 부족 - CREATE 모드")
                    return WorkflowMode.CREATE
            
            # Rule 3: API 요청 분석
            elif request.source == RequestSource.API:
                if request.canvas_id and request.reference_image_id:
                    if await self._verify_canvas_and_reference(db, request):
                        return WorkflowMode.EDIT
                    else:
                        return WorkflowMode.CREATE
                else:
                    return WorkflowMode.CREATE
            
            # 기본값: CREATE 모드
            return WorkflowMode.CREATE
            
        except Exception as e:
            logger.error(f"❌ 워크플로우 모드 결정 실패: {str(e)}")
            return WorkflowMode.CREATE  # 안전한 기본값
    
    async def _verify_canvas_and_reference(
        self,
        db: AsyncSession,
        request: ImageGenerationRequest
    ) -> bool:
        """Canvas와 참조 이미지 유효성 검증"""
        
        try:
            # Canvas 접근 권한 확인
            access_valid = await self.lifecycle_service._validate_canvas_access(
                db=db,
                conversation_id=request.conversation_id,
                canvas_id=request.canvas_id,
                user_id=request.user_id
            )
            
            if not access_valid:
                logger.warning(f"❌ Canvas 접근 권한 없음: {request.canvas_id}")
                return False
            
            # 참조 이미지 유효성 확인
            validation = await self.lifecycle_service._validate_canvas_evolution_request(
                db=db,
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                canvas_id=request.canvas_id,
                reference_image_id=request.reference_image_id
            )
            
            if not validation["valid"]:
                logger.warning(f"❌ 참조 이미지 유효성 검증 실패: {validation['error']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Canvas 및 참조 이미지 검증 실패: {str(e)}")
            return False
    
    async def _validate_request(
        self,
        db: AsyncSession,
        request: ImageGenerationRequest,
        workflow_mode: WorkflowMode
    ) -> Dict[str, Any]:
        """요청 데이터 검증"""
        
        try:
            # 공통 필수 필드 검증
            if not request.conversation_id or not request.user_id or not request.prompt:
                return {
                    "valid": False,
                    "error": "필수 필드가 누락되었습니다 (conversation_id, user_id, prompt)"
                }
            
            # 프롬프트 길이 검증
            if len(request.prompt.strip()) < 3:
                return {
                    "valid": False,
                    "error": "프롬프트가 너무 짧습니다 (최소 3자)"
                }
            
            if len(request.prompt) > 2000:
                return {
                    "valid": False,
                    "error": "프롬프트가 너무 깁니다 (최대 2000자)"
                }
            
            # EDIT 모드 전용 검증
            if workflow_mode == WorkflowMode.EDIT:
                if not request.canvas_id:
                    return {
                        "valid": False,
                        "error": "EDIT 모드에서는 canvas_id가 필수입니다"
                    }
                
                if not request.reference_image_id:
                    return {
                        "valid": False,
                        "error": "EDIT 모드에서는 reference_image_id가 필수입니다"
                    }
                
                # 진화 타입 검증
                valid_evolution_types = ["based_on", "variation", "extension", "modification", "reference_edit"]
                if request.evolution_type and request.evolution_type not in valid_evolution_types:
                    return {
                        "valid": False,
                        "error": f"유효하지 않은 진화 타입: {request.evolution_type}"
                    }
            
            # 스타일 검증
            valid_styles = ["realistic", "artistic", "cartoon", "abstract", "photographic", "cinematic"]
            if request.style and request.style not in valid_styles:
                logger.warning(f"⚠️ 비표준 스타일 사용: {request.style}")
            
            # 크기 검증
            valid_sizes = ["1024x1024", "1024x768", "768x1024", "1280x720", "720x1280"]
            if request.size and request.size not in valid_sizes:
                logger.warning(f"⚠️ 비표준 크기 사용: {request.size}")
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"❌ 요청 검증 실패: {str(e)}")
            return {
                "valid": False,
                "error": "요청 검증 중 오류가 발생했습니다"
            }
    
    async def _handle_create_workflow(
        self,
        db: AsyncSession,
        request: ImageGenerationRequest
    ) -> Dict[str, Any]:
        """CREATE 워크플로우 처리 (새 Canvas 생성)"""
        
        try:
            logger.info(f"🆕 CREATE 워크플로우 시작 - 프롬프트: {request.prompt[:30]}...")
            
            result = await self.lifecycle_service.handle_chat_image_request(
                db=db,
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                prompt=request.prompt,
                style=request.style or "realistic",
                size=request.size or "1024x1024",
                generation_params=request.generation_params
            )
            
            if result.get("success"):
                logger.info(f"✅ CREATE 워크플로우 완료 - Canvas: {result.get('canvas_id')}")
            else:
                logger.error(f"❌ CREATE 워크플로우 실패: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ CREATE 워크플로우 처리 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "workflow_type": "create"
            }
    
    async def _handle_edit_workflow(
        self,
        db: AsyncSession,
        request: ImageGenerationRequest
    ) -> Dict[str, Any]:
        """EDIT 워크플로우 처리 (Canvas 내 이미지 진화)"""
        
        try:
            logger.info(f"✏️ EDIT 워크플로우 시작 - Canvas: {request.canvas_id}")
            
            result = await self.lifecycle_service.handle_canvas_evolution_request(
                db=db,
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                canvas_id=request.canvas_id,
                reference_image_id=request.reference_image_id,
                new_prompt=request.prompt,
                evolution_type=request.evolution_type or "variation",
                edit_mode_type=request.edit_mode_type or "EDIT_MODE_INPAINT_INSERTION",
                style=request.style,
                size=request.size
            )
            
            if result.get("success"):
                logger.info(f"✅ EDIT 워크플로우 완료 - 버전: {result.get('canvas_version')}")
            else:
                logger.error(f"❌ EDIT 워크플로우 실패: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ EDIT 워크플로우 처리 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "workflow_type": "edit"
            }
    
    @staticmethod
    def create_chat_request(
        conversation_id: UUID,
        user_id: UUID,
        prompt: str,
        style: str = "realistic",
        size: str = "1024x1024",
        generation_params: Optional[Dict] = None
    ) -> ImageGenerationRequest:
        """채팅 요청용 ImageGenerationRequest 생성 헬퍼"""
        
        return ImageGenerationRequest(
            conversation_id=conversation_id,
            user_id=user_id,
            prompt=prompt,
            source=RequestSource.CHAT,
            style=style,
            size=size,
            generation_params=generation_params
        )
    
    @staticmethod
    def create_canvas_evolution_request(
        conversation_id: UUID,
        user_id: UUID,
        canvas_id: UUID,
        reference_image_id: UUID,
        prompt: str,
        evolution_type: str = "variation",
        edit_mode_type: str = "EDIT_MODE_INPAINT_INSERTION",
        style: Optional[str] = None,
        size: Optional[str] = None
    ) -> ImageGenerationRequest:
        """Canvas 진화 요청용 ImageGenerationRequest 생성 헬퍼"""
        
        return ImageGenerationRequest(
            conversation_id=conversation_id,
            user_id=user_id,
            prompt=prompt,
            source=RequestSource.CANVAS,
            canvas_id=canvas_id,
            reference_image_id=reference_image_id,
            evolution_type=evolution_type,
            edit_mode_type=edit_mode_type,
            style=style,
            size=size
        )


# 전역 인스턴스
workflow_dispatcher = CanvasWorkflowDispatcher()