"""
Canvas 생명주기 관리 서비스
Request-Based Canvas 시스템의 통합 인터페이스
"""

from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging

from app.services.canvas_request_manager import CanvasRequestManager
from app.services.image_generation_service import ImageGenerationService
from app.db.models.image_history import ImageHistory

logger = logging.getLogger(__name__)


class CanvasLifecycleService:
    """
    Canvas 생명주기 통합 관리 서비스
    
    역할:
    1. 채팅/Canvas 요청 구분 및 라우팅
    2. Canvas 생명주기 이벤트 관리
    3. 상태 추적 및 검증
    4. 통합 API 인터페이스 제공
    """
    
    def __init__(self):
        self.image_service = ImageGenerationService()
        self.canvas_manager = CanvasRequestManager(self.image_service)
    
    async def handle_chat_image_request(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        prompt: str,
        style: str = "realistic",
        size: str = "1024x1024",
        generation_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        채팅에서 이미지 생성 요청 처리 (새 Canvas 생성)
        
        Args:
            db: 데이터베이스 세션
            conversation_id: 대화 ID
            user_id: 사용자 ID
            prompt: 이미지 생성 프롬프트
            style: 이미지 스타일
            size: 이미지 크기
            generation_params: 생성 파라미터
        
        Returns:
            처리 결과 및 Canvas 정보
        """
        try:
            logger.info(f"💬 채팅 이미지 요청 처리 시작 - 대화: {conversation_id}")
            
            # 새로운 Canvas 생성
            result = await self.canvas_manager.create_new_canvas_for_chat_request(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
                prompt=prompt,
                style=style,
                size=size,
                generation_params=generation_params
            )
            
            if result.get("success"):
                # Canvas 생성 이벤트 로깅
                await self._log_canvas_event(
                    db=db,
                    event_type="CANVAS_CREATED",
                    canvas_id=UUID(result["canvas_id"]),
                    conversation_id=conversation_id,
                    user_id=user_id,
                    metadata={
                        "source": "chat_request",
                        "prompt": prompt,
                        "version": result["canvas_version"]
                    }
                )
                
                logger.info(f"✅ 채팅 요청으로 새 Canvas 생성: {result['canvas_id']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 채팅 이미지 요청 처리 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "source": "chat_request"
            }
    
    async def handle_canvas_evolution_request(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        canvas_id: UUID,
        reference_image_id: UUID,
        new_prompt: str,
        evolution_type: str = "variation",
        edit_mode_type: str = "EDIT_MODE_INPAINT_INSERTION",
        style: Optional[str] = None,
        size: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Canvas 내 이미지 진화 요청 처리 (기존 Canvas 내 버전 추가)
        
        Args:
            db: 데이터베이스 세션
            conversation_id: 대화 ID
            user_id: 사용자 ID
            canvas_id: Canvas ID
            reference_image_id: 참조 이미지 ID
            new_prompt: 새로운 프롬프트
            evolution_type: 진화 타입
            edit_mode_type: 편집 모드 타입
            style: 이미지 스타일
            size: 이미지 크기
        
        Returns:
            진화 결과 및 새 버전 정보
        """
        try:
            logger.info(f"🎨 Canvas 진화 요청 처리 시작 - Canvas: {canvas_id}")
            
            # Canvas 유효성 검증
            validation_result = await self._validate_canvas_evolution_request(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
                canvas_id=canvas_id,
                reference_image_id=reference_image_id
            )
            
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "source": "canvas_evolution"
                }
            
            # 이미지 진화 수행
            result = await self.canvas_manager.evolve_image_within_canvas(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
                canvas_id=canvas_id,
                reference_image_id=reference_image_id,
                new_prompt=new_prompt,
                evolution_type=evolution_type,
                edit_mode_type=edit_mode_type,
                style=style,
                size=size
            )
            
            if result.get("success"):
                # Canvas 진화 이벤트 로깅
                await self._log_canvas_event(
                    db=db,
                    event_type="CANVAS_EVOLVED",
                    canvas_id=canvas_id,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    metadata={
                        "source": "canvas_evolution",
                        "reference_image_id": str(reference_image_id),
                        "new_prompt": new_prompt,
                        "evolution_type": evolution_type,
                        "version": result["canvas_version"]
                    }
                )
                
                logger.info(f"✅ Canvas 진화 완료: {canvas_id} v{result['canvas_version']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Canvas 진화 요청 처리 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "source": "canvas_evolution"
            }
    
    async def get_conversation_canvas_summary(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        대화의 전체 Canvas 활동 요약 조회
        
        Args:
            db: 데이터베이스 세션
            conversation_id: 대화 ID
            user_id: 사용자 ID
        
        Returns:
            Canvas 활동 요약
        """
        try:
            # 모든 Canvas 목록 조회
            canvases = await self.canvas_manager.get_conversation_canvases(
                db=db,
                conversation_id=conversation_id,
                include_deleted=False
            )
            
            # 통계 계산
            total_canvases = len(canvases)
            total_versions = sum(canvas["total_versions"] for canvas in canvases)
            
            # 최근 활동 Canvas
            recent_canvas = canvases[0] if canvases else None
            
            # Canvas 타입별 분류
            create_canvases = []
            edit_canvases = []
            
            for canvas in canvases:
                if canvas["latest_image"]["edit_mode"] == "CREATE":
                    create_canvases.append(canvas)
                else:
                    edit_canvases.append(canvas)
            
            summary = {
                "conversation_id": str(conversation_id),
                "total_canvases": total_canvases,
                "total_versions": total_versions,
                "create_canvases_count": len(create_canvases),
                "edit_canvases_count": len(edit_canvases),
                "recent_canvas": recent_canvas,
                "all_canvases": canvases,
                "statistics": {
                    "avg_versions_per_canvas": round(total_versions / total_canvases, 2) if total_canvases > 0 else 0,
                    "most_evolved_canvas": max(canvases, key=lambda x: x["total_versions"]) if canvases else None
                }
            }
            
            logger.info(f"📊 대화 Canvas 요약: {total_canvases}개 Canvas, {total_versions}개 버전")
            
            return {
                "success": True,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"❌ Canvas 요약 조회 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_canvas_detailed_history(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        canvas_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        특정 Canvas의 상세 히스토리 조회
        
        Args:
            db: 데이터베이스 세션
            conversation_id: 대화 ID
            canvas_id: Canvas ID
            user_id: 사용자 ID
        
        Returns:
            Canvas 상세 히스토리
        """
        try:
            # 권한 검증
            access_valid = await self._validate_canvas_access(
                db=db,
                conversation_id=conversation_id,
                canvas_id=canvas_id,
                user_id=user_id
            )
            
            if not access_valid:
                return {
                    "success": False,
                    "error": "Canvas에 접근할 권한이 없습니다"
                }
            
            # 상세 히스토리 조회
            history = await self.canvas_manager.get_canvas_history(
                db=db,
                conversation_id=conversation_id,
                canvas_id=canvas_id,
                include_deleted=False
            )
            
            # 히스토리 분석
            if history:
                analysis = {
                    "canvas_id": str(canvas_id),
                    "total_versions": len(history),
                    "creation_time": history[0]["created_at"],
                    "last_update_time": history[-1]["created_at"],
                    "evolution_chain": [],
                    "edit_modes": {},
                    "styles_used": set(),
                    "sizes_used": set()
                }
                
                # 진화 체인 구성
                for version in history:
                    analysis["evolution_chain"].append({
                        "version": version["canvas_version"],
                        "prompt": version["prompt"][:50] + "..." if len(version["prompt"]) > 50 else version["prompt"],
                        "evolution_type": version["evolution_type"],
                        "edit_mode": version["edit_mode"]
                    })
                    
                    # 통계 수집
                    edit_mode = version["edit_mode"]
                    analysis["edit_modes"][edit_mode] = analysis["edit_modes"].get(edit_mode, 0) + 1
                    analysis["styles_used"].add(version["style"])
                    analysis["sizes_used"].add(version["size"])
                
                # Set을 리스트로 변환
                analysis["styles_used"] = list(analysis["styles_used"])
                analysis["sizes_used"] = list(analysis["sizes_used"])
                
                logger.info(f"📋 Canvas 상세 히스토리 조회: {canvas_id} ({len(history)}개 버전)")
                
                return {
                    "success": True,
                    "canvas_id": str(canvas_id),
                    "history": history,
                    "analysis": analysis
                }
            else:
                return {
                    "success": True,
                    "canvas_id": str(canvas_id),
                    "history": [],
                    "analysis": None,
                    "message": "Canvas 히스토리가 비어있습니다"
                }
        
        except Exception as e:
            logger.error(f"❌ Canvas 상세 히스토리 조회 실패: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _validate_canvas_evolution_request(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        user_id: UUID,
        canvas_id: UUID,
        reference_image_id: UUID
    ) -> Dict[str, Any]:
        """Canvas 진화 요청 유효성 검증"""
        
        try:
            # Canvas 존재 여부 확인
            canvas_result = await db.execute(
                select(ImageHistory).where(
                    and_(
                        ImageHistory.canvas_id == canvas_id,
                        ImageHistory.conversation_id == conversation_id,
                        ImageHistory.user_id == user_id,
                        ImageHistory.is_deleted == False
                    )
                ).limit(1)
            )
            
            if not canvas_result.scalars().first():
                return {
                    "valid": False,
                    "error": "지정된 Canvas를 찾을 수 없습니다"
                }
            
            # 참조 이미지 유효성 확인
            reference_result = await db.execute(
                select(ImageHistory).where(
                    and_(
                        ImageHistory.id == reference_image_id,
                        ImageHistory.canvas_id == canvas_id,
                        ImageHistory.conversation_id == conversation_id,
                        ImageHistory.user_id == user_id,
                        ImageHistory.is_deleted == False
                    )
                )
            )
            
            reference_image = reference_result.scalars().first()
            if not reference_image:
                return {
                    "valid": False,
                    "error": "참조 이미지가 존재하지 않거나 접근할 수 없습니다"
                }
            
            return {
                "valid": True,
                "reference_image": reference_image
            }
            
        except Exception as e:
            logger.error(f"❌ Canvas 진화 요청 검증 실패: {str(e)}")
            return {
                "valid": False,
                "error": "검증 중 오류가 발생했습니다"
            }
    
    async def _validate_canvas_access(
        self,
        db: AsyncSession,
        conversation_id: UUID,
        canvas_id: UUID,
        user_id: UUID
    ) -> bool:
        """Canvas 접근 권한 검증"""
        
        try:
            result = await db.execute(
                select(ImageHistory.id).where(
                    and_(
                        ImageHistory.canvas_id == canvas_id,
                        ImageHistory.conversation_id == conversation_id,
                        ImageHistory.user_id == user_id,
                        ImageHistory.is_deleted == False
                    )
                ).limit(1)
            )
            
            return result.scalars().first() is not None
            
        except Exception as e:
            logger.error(f"❌ Canvas 접근 권한 검증 실패: {str(e)}")
            return False
    
    async def _log_canvas_event(
        self,
        db: AsyncSession,
        event_type: str,
        canvas_id: UUID,
        conversation_id: UUID,
        user_id: UUID,
        metadata: Optional[Dict] = None
    ) -> None:
        """Canvas 생명주기 이벤트 로깅"""
        
        try:
            # 이벤트 로깅은 향후 확장 가능
            # 현재는 애플리케이션 로그로만 기록
            logger.info(f"🎭 Canvas Event: {event_type} | Canvas: {canvas_id} | User: {user_id}")
            if metadata:
                logger.info(f"   메타데이터: {metadata}")
                
        except Exception as e:
            logger.error(f"❌ Canvas 이벤트 로깅 실패: {str(e)}")
            # 로깅 실패는 핵심 기능에 영향을 주지 않음
            pass