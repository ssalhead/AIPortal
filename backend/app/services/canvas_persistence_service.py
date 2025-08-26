"""
Canvas 영구 저장 전담 서비스 (v4.0)
Canvas 작업물의 완전한 영구 보존 및 복원 기능 제공
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func, text
from sqlalchemy.orm import selectinload
import json
import uuid
import logging

from app.db.models.conversation import Conversation, Message, MessageRole
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.services.conversation_cache_manager import conversation_cache_manager

logger = logging.getLogger(__name__)

class CanvasPersistenceService:
    """Canvas 영구 저장 전담 서비스"""
    
    def __init__(self):
        self.cache_manager = conversation_cache_manager
    
    async def save_canvas_data(
        self,
        conversation_id: str,
        user_id: str,
        canvas_id: str,
        canvas_type: str,
        content: Dict[str, Any],
        metadata: Dict[str, Any],
        session: AsyncSession,
        parent_canvas_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Canvas 데이터 영구 저장"""
        try:
            logger.info(f"📂 Canvas 영구 저장 시작: {canvas_id} (type: {canvas_type})")
            
            # Canvas 데이터 구조화
            canvas_persistent_data = {
                "canvas_id": canvas_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "type": canvas_type,
                "content": content,
                "metadata": {
                    **metadata,
                    "title": metadata.get("title", f"{canvas_type.title()} Canvas"),
                    "description": metadata.get("description", ""),
                    "version": metadata.get("version", 1),
                    "parent_canvas_id": parent_canvas_id,
                    "created_by": "canvas_system_v4",
                    "auto_save_enabled": True
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Message에 Canvas 데이터로 저장 (기존 방식 확장)
            message_repo = MessageRepository(session)
            
            # 기존 Canvas 메시지가 있는지 확인
            existing_canvas_message = await self._find_canvas_message(
                conversation_id, canvas_id, session
            )
            
            if existing_canvas_message:
                # 기존 Canvas 업데이트
                logger.info(f"🔄 기존 Canvas 업데이트: {canvas_id}")
                
                updated_metadata = existing_canvas_message.metadata_ or {}
                updated_metadata["canvas_data"] = canvas_persistent_data
                
                existing_canvas_message.metadata_ = updated_metadata
                existing_canvas_message.updated_at = datetime.now()
                
                await session.commit()
                
                result = {
                    "canvas_id": canvas_id,
                    "action": "updated",
                    "message_id": str(existing_canvas_message.id),
                    "timestamp": existing_canvas_message.updated_at.isoformat()
                }
            else:
                # 새 Canvas 메시지 생성
                logger.info(f"✨ 새 Canvas 메시지 생성: {canvas_id}")
                
                canvas_message = await message_repo.create(
                    conversation_id=conversation_id,
                    role=MessageRole.SYSTEM,
                    content=f"Canvas 작업 저장: {metadata.get('title', canvas_type)}",
                    metadata_={
                        "canvas_data": canvas_persistent_data,
                        "is_canvas_data": True,
                        "canvas_id": canvas_id,
                        "canvas_type": canvas_type
                    },
                    attachments=[]
                )
                
                result = {
                    "canvas_id": canvas_id,
                    "action": "created",
                    "message_id": str(canvas_message.id),
                    "timestamp": canvas_message.created_at.isoformat()
                }
            
            # 캐시 무효화 (실시간 반영)
            self.cache_manager.invalidate_conversation_cache(conversation_id)
            
            logger.info(f"✅ Canvas 영구 저장 완료: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Canvas 영구 저장 실패: {canvas_id}, 오류: {e}")
            await session.rollback()
            raise
    
    async def load_canvas_data(
        self,
        conversation_id: str,
        user_id: str,
        canvas_id: Optional[str] = None,
        canvas_type: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """Canvas 데이터 로드"""
        try:
            logger.info(f"📂 Canvas 데이터 로드: conversation={conversation_id}, canvas_id={canvas_id}, type={canvas_type}")
            
            if session is None:
                # 세션이 없으면 캐시에서 먼저 시도
                cached_messages = self.cache_manager.get_conversation_messages(conversation_id)
                if cached_messages:
                    canvas_data_list = []
                    for msg in cached_messages:
                        if isinstance(msg, dict) and msg.get("metadata", {}).get("is_canvas_data"):
                            canvas_data = msg["metadata"].get("canvas_data")
                            if canvas_data and self._matches_filter(canvas_data, canvas_id, canvas_type):
                                canvas_data_list.append(canvas_data)
                    
                    if canvas_data_list:
                        logger.info(f"✅ 캐시에서 Canvas 데이터 로드 완료: {len(canvas_data_list)}개")
                        return canvas_data_list
            
            # DB에서 직접 조회
            if session:
                message_repo = MessageRepository(session)
                messages = await message_repo.get_conversation_messages(conversation_id)
                
                canvas_data_list = []
                for msg in messages:
                    if msg.metadata_ and msg.metadata_.get("is_canvas_data"):
                        canvas_data = msg.metadata_.get("canvas_data")
                        if canvas_data and self._matches_filter(canvas_data, canvas_id, canvas_type):
                            canvas_data_list.append(canvas_data)
                
                logger.info(f"✅ DB에서 Canvas 데이터 로드 완료: {len(canvas_data_list)}개")
                return canvas_data_list
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Canvas 데이터 로드 실패: {e}")
            return []
    
    async def get_canvas_history(
        self,
        conversation_id: str,
        user_id: str,
        session: AsyncSession,
        canvas_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """대화별 Canvas 히스토리 조회"""
        try:
            logger.info(f"📋 Canvas 히스토리 조회: conversation={conversation_id}, type={canvas_type}")
            
            canvas_data_list = await self.load_canvas_data(
                conversation_id=conversation_id,
                user_id=user_id,
                canvas_type=canvas_type,
                session=session
            )
            
            # 생성 시간순으로 정렬
            sorted_canvas_list = sorted(
                canvas_data_list,
                key=lambda x: x.get("created_at", ""),
                reverse=True  # 최신순
            )
            
            # 히스토리 메타데이터 추가
            for i, canvas_data in enumerate(sorted_canvas_list):
                canvas_data["metadata"]["history_index"] = i
                canvas_data["metadata"]["is_latest"] = (i == 0)
            
            logger.info(f"✅ Canvas 히스토리 조회 완료: {len(sorted_canvas_list)}개")
            return sorted_canvas_list
            
        except Exception as e:
            logger.error(f"❌ Canvas 히스토리 조회 실패: {e}")
            return []
    
    async def delete_canvas_data(
        self,
        conversation_id: str,
        user_id: str,
        canvas_id: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """Canvas 데이터 삭제"""
        try:
            logger.info(f"🗑️ Canvas 데이터 삭제: {canvas_id}")
            
            # Canvas 메시지 찾기
            canvas_message = await self._find_canvas_message(
                conversation_id, canvas_id, session
            )
            
            if canvas_message:
                # 메시지 삭제 (soft delete)
                canvas_message.metadata_["is_deleted"] = True
                canvas_message.metadata_["deleted_at"] = datetime.now().isoformat()
                canvas_message.updated_at = datetime.now()
                
                await session.commit()
                
                # 캐시 무효화
                self.cache_manager.invalidate_conversation_cache(conversation_id)
                
                result = {
                    "canvas_id": canvas_id,
                    "action": "deleted",
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"✅ Canvas 데이터 삭제 완료: {result}")
                return result
            else:
                logger.warning(f"⚠️ 삭제할 Canvas를 찾을 수 없음: {canvas_id}")
                return {
                    "canvas_id": canvas_id,
                    "action": "not_found",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Canvas 데이터 삭제 실패: {canvas_id}, 오류: {e}")
            await session.rollback()
            raise
    
    # === 내부 헬퍼 메서드 ===
    
    async def _find_canvas_message(
        self, 
        conversation_id: str, 
        canvas_id: str, 
        session: AsyncSession
    ) -> Optional[Message]:
        """Canvas ID로 메시지 찾기"""
        try:
            message_repo = MessageRepository(session)
            messages = await message_repo.get_conversation_messages(conversation_id)
            
            for msg in messages:
                if (msg.metadata_ and 
                    msg.metadata_.get("canvas_id") == canvas_id and 
                    not msg.metadata_.get("is_deleted", False)):
                    return msg
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Canvas 메시지 검색 실패: {e}")
            return None
    
    def _matches_filter(
        self, 
        canvas_data: Dict[str, Any], 
        canvas_id: Optional[str], 
        canvas_type: Optional[str]
    ) -> bool:
        """필터 조건 확인"""
        if canvas_id and canvas_data.get("canvas_id") != canvas_id:
            return False
        
        if canvas_type and canvas_data.get("type") != canvas_type:
            return False
        
        # 삭제된 Canvas 제외
        if canvas_data.get("metadata", {}).get("is_deleted", False):
            return False
        
        return True


# 서비스 인스턴스 생성
canvas_persistence_service = CanvasPersistenceService()