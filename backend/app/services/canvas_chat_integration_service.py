"""
Canvas-Chat 통합 서비스
Canvas에서 발생하는 이미지 진화 작업을 채팅 히스토리에 자동 동기화
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from app.db.models.conversation import MessageRole
from app.services.conversation_history_service import ConversationHistoryService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CanvasChatIntegrationService:
    """Canvas 작업과 채팅 히스토리의 통합 관리"""
    
    def __init__(self):
        self.conversation_service = ConversationHistoryService()
    
    async def record_image_evolution_in_chat(
        self,
        db_session,
        conversation_id: str,
        user_id: str,
        evolution_request: str,
        evolved_image_data: Dict[str, Any],
        parent_image_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Canvas 이미지 진화 작업을 채팅 히스토리에 기록
        
        Args:
            db_session: 데이터베이스 세션
            conversation_id: 대화 ID
            user_id: 사용자 ID
            evolution_request: 사용자의 진화 요청 내용
            evolved_image_data: 생성된 진화 이미지 정보
            parent_image_data: 기반이 된 부모 이미지 정보
        
        Returns:
            bool: 성공 여부
        """
        
        try:
            logger.info(f"🔗 Canvas 진화 작업의 채팅 히스토리 기록 시작: {conversation_id}")
            
            # 1. 사용자 메시지 생성 (진화 요청 내용)
            user_message_content = self._format_user_evolution_message(
                evolution_request,
                evolved_image_data.get("evolution_type", "modification"),
                parent_image_data
            )
            
            user_message = await self.conversation_service.add_message(
                conversation_id=conversation_id,
                user_id=user_id,
                role=MessageRole.USER,
                content=user_message_content,
                session=db_session,
                metadata_={
                    "source": "canvas_evolution",
                    "parent_image_id": str(evolved_image_data.get("parent_image_id", "")),
                    "evolution_type": evolved_image_data.get("evolution_type", ""),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.debug(f"✅ 사용자 진화 메시지 생성: {user_message['id']}")
            
            # 2. AI 응답 메시지 생성 (진화 완료 알림)
            ai_response_content = self._format_ai_evolution_response(
                evolution_request,
                evolved_image_data,
                parent_image_data
            )
            
            # Canvas 데이터 포함
            canvas_data = {
                "imageUrl": evolved_image_data.get("primary_image_url", ""),
                "prompt": evolved_image_data.get("prompt", ""),
                "style": evolved_image_data.get("style", "realistic"),
                "size": evolved_image_data.get("size", "1024x1024"),
                "evolution_type": evolved_image_data.get("evolution_type", ""),
                "parent_image_id": str(evolved_image_data.get("parent_image_id", "")),
                "image_id": str(evolved_image_data.get("id", "")),
                "conversation_id": conversation_id,
                "generated_at": evolved_image_data.get("created_at", datetime.utcnow().isoformat())
            }
            
            ai_message = await self.conversation_service.add_message(
                conversation_id=conversation_id,
                user_id=user_id,
                role=MessageRole.ASSISTANT,
                content=ai_response_content,
                session=db_session,
                metadata_={
                    "source": "canvas_evolution_response",
                    "evolved_image_id": str(evolved_image_data.get("id", "")),
                    "evolution_type": evolved_image_data.get("evolution_type", ""),
                    "generation_method": evolved_image_data.get("generation_method", "unknown"),
                    "timestamp": datetime.utcnow().isoformat()
                },
                canvas_data=canvas_data
            )
            
            logger.info(f"🎉 Canvas 진화 작업 채팅 기록 완료: user_msg={user_message['id']}, ai_msg={ai_message['id']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Canvas 진화 작업 채팅 기록 실패: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"💣 상세 오류:\n{traceback.format_exc()}")
            return False
    
    def _format_user_evolution_message(
        self,
        evolution_request: str,
        evolution_type: str,
        parent_image_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """사용자의 진화 요청 메시지 포맷"""
        
        evolution_type_map = {
            "variation": "변형",
            "modification": "수정", 
            "extension": "확장",
            "based_on": "기반으로"
        }
        
        type_korean = evolution_type_map.get(evolution_type, evolution_type)
        
        if parent_image_data:
            parent_prompt = parent_image_data.get("prompt", "이전 이미지")[:30]
            return f"'{parent_prompt}'을 {type_korean}해서 {evolution_request}"
        else:
            return f"이미지를 {type_korean}해서 {evolution_request}"
    
    def _format_ai_evolution_response(
        self,
        evolution_request: str,
        evolved_image_data: Dict[str, Any],
        parent_image_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """AI의 진화 완료 응답 메시지 포맷"""
        
        evolution_type = evolved_image_data.get("evolution_type", "modification")
        evolution_type_map = {
            "variation": "변형",
            "modification": "수정",
            "extension": "확장", 
            "based_on": "기반으로 새로운 이미지"
        }
        
        type_korean = evolution_type_map.get(evolution_type, "변경")
        
        # 진화 타입에 따른 맞춤 응답
        if evolution_type == "variation":
            response = f"요청하신 이미지 변형을 완료했습니다. 원본 이미지를 바탕으로 다양한 스타일로 재해석했습니다."
        elif evolution_type == "modification":
            response = f"'{evolution_request}' 요청에 따라 이미지를 수정했습니다."
        elif evolution_type == "extension":
            response = f"기존 이미지에 '{evolution_request}' 요소를 추가하여 확장된 이미지를 생성했습니다."
        else:  # based_on
            response = f"선택하신 이미지를 기반으로 '{evolution_request}' 새로운 이미지를 생성했습니다."
        
        # Canvas 링크 안내 추가
        response += "\n\n🎨 **Canvas에서 확인하기**를 클릭하여 생성된 이미지와 이전 버전들을 비교해보실 수 있습니다."
        
        return response
    
    async def sync_canvas_session_to_chat(
        self,
        db_session,
        conversation_id: str,
        user_id: str,
        canvas_session_data: Dict[str, Any]
    ) -> bool:
        """
        Canvas 세션 전체를 채팅 히스토리에 동기화
        (처음 Canvas를 열 때 사용)
        """
        
        try:
            logger.info(f"🔗 Canvas 세션 채팅 동기화 시작: {conversation_id}")
            
            # Canvas 세션 정보 기반 메시지 생성
            canvas_summary = self._format_canvas_session_summary(canvas_session_data)
            
            ai_message = await self.conversation_service.add_message(
                conversation_id=conversation_id,
                user_id=user_id,
                role=MessageRole.ASSISTANT,
                content=canvas_summary,
                session=db_session,
                metadata_={
                    "source": "canvas_session_sync",
                    "canvas_session_id": canvas_session_data.get("session_id", ""),
                    "total_images": len(canvas_session_data.get("images", [])),
                    "timestamp": datetime.utcnow().isoformat()
                },
                canvas_data=canvas_session_data
            )
            
            logger.info(f"✅ Canvas 세션 채팅 동기화 완료: {ai_message['id']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Canvas 세션 채팅 동기화 실패: {e}")
            return False
    
    def _format_canvas_session_summary(self, canvas_data: Dict[str, Any]) -> str:
        """Canvas 세션 요약 메시지 포맷"""
        
        images = canvas_data.get("images", [])
        total_count = len(images)
        
        if total_count == 0:
            return "🎨 Canvas 워크스페이스가 준비되었습니다."
        elif total_count == 1:
            return f"🎨 Canvas에서 이미지 1개를 작업 중입니다. **Canvas에서 확인하기**를 클릭하여 자세히 보실 수 있습니다."
        else:
            evolution_count = len([img for img in images if img.get("evolution_type")])
            original_count = total_count - evolution_count
            
            summary = f"🎨 Canvas에서 총 {total_count}개의 이미지를 작업 중입니다"
            if original_count > 0 and evolution_count > 0:
                summary += f" (원본 {original_count}개, 진화 {evolution_count}개)"
            summary += ". **Canvas에서 확인하기**를 클릭하여 모든 버전을 비교해보실 수 있습니다."
            
            return summary