"""
ConversationService 단위 테스트
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.exc import SQLAlchemyError

from app.services.conversation_service import ConversationService
from app.db.models.conversation import Conversation, Message
from app.core.exceptions import NotFoundError, ValidationError


@pytest.mark.unit
@pytest.mark.db
class TestConversationService:
    """ConversationService 테스트 클래스"""
    
    def test_create_conversation_success(self, conversation_service, sample_conversation_data):
        """대화 생성 성공 테스트"""
        # Given
        conversation_data = sample_conversation_data
        
        # When
        result = conversation_service.create_conversation(conversation_data)
        
        # Then
        assert result is not None
        assert result.title == conversation_data["title"]
        assert result.description == conversation_data["description"]
        assert result.model == conversation_data["model"]
        assert result.agent_type == conversation_data["agent_type"]
        assert result.status == "active"
        assert result.id is not None
    
    def test_create_conversation_validation_error(self, conversation_service):
        """대화 생성 시 유효성 검사 실패 테스트"""
        # Given
        invalid_data = {"title": ""}  # 빈 제목
        
        # When & Then
        with pytest.raises(ValidationError):
            conversation_service.create_conversation(invalid_data)
    
    def test_get_conversation_by_id_success(self, conversation_service, db_session, test_helpers):
        """ID로 대화 조회 성공 테스트"""
        # Given
        conversation = test_helpers.create_test_conversation(db_session)
        
        # When
        result = conversation_service.get_conversation_by_id(conversation.id)
        
        # Then
        assert result is not None
        assert result.id == conversation.id
        assert result.title == conversation.title
    
    def test_get_conversation_by_id_not_found(self, conversation_service):
        """존재하지 않는 대화 조회 테스트"""
        # Given
        non_existent_id = str(uuid.uuid4())
        
        # When & Then
        with pytest.raises(NotFoundError):
            conversation_service.get_conversation_by_id(non_existent_id)
    
    def test_get_conversations_with_pagination(self, conversation_service, db_session, test_helpers):
        """페이지네이션을 포함한 대화 목록 조회 테스트"""
        # Given
        conversations = []
        for i in range(5):
            conv = test_helpers.create_test_conversation(
                db_session, 
                title=f"테스트 대화 {i+1}"
            )
            conversations.append(conv)
        
        # When
        result = conversation_service.get_conversations(skip=1, limit=2)
        
        # Then
        assert len(result.conversations) == 2
        assert result.total == 5
        assert result.skip == 1
        assert result.limit == 2
        assert result.has_more is True
    
    def test_add_message_to_conversation(self, conversation_service, db_session, test_helpers, sample_message_data):
        """대화에 메시지 추가 테스트"""
        # Given
        conversation = test_helpers.create_test_conversation(db_session)
        message_data = sample_message_data
        
        # When
        result = conversation_service.add_message(conversation.id, message_data)
        
        # Then
        assert result is not None
        assert result.conversation_id == conversation.id
        assert result.content == message_data["content"]
        assert result.role == message_data["role"]
    
    def test_add_message_to_nonexistent_conversation(self, conversation_service, sample_message_data):
        """존재하지 않는 대화에 메시지 추가 테스트"""
        # Given
        non_existent_id = str(uuid.uuid4())
        message_data = sample_message_data
        
        # When & Then
        with pytest.raises(NotFoundError):
            conversation_service.add_message(non_existent_id, message_data)
    
    def test_update_conversation_success(self, conversation_service, db_session, test_helpers):
        """대화 정보 수정 성공 테스트"""
        # Given
        conversation = test_helpers.create_test_conversation(db_session)
        update_data = {
            "title": "수정된 제목",
            "description": "수정된 설명",
            "status": "archived"
        }
        
        # When
        result = conversation_service.update_conversation(conversation.id, update_data)
        
        # Then
        assert result.title == update_data["title"]
        assert result.description == update_data["description"]
        assert result.status == update_data["status"]
    
    def test_delete_conversation_soft_delete(self, conversation_service, db_session, test_helpers):
        """대화 소프트 삭제 테스트"""
        # Given
        conversation = test_helpers.create_test_conversation(db_session)
        
        # When
        result = conversation_service.delete_conversation(conversation.id, hard_delete=False)
        
        # Then
        assert result["message"] == "대화가 삭제되었습니다."
        assert result["conversation_id"] == conversation.id
        
        # 대화가 실제로 삭제 상태로 변경되었는지 확인
        updated_conversation = conversation_service.get_conversation_by_id(conversation.id)
        assert updated_conversation.status == "deleted"
    
    def test_delete_conversation_hard_delete(self, conversation_service, db_session, test_helpers):
        """대화 하드 삭제 테스트"""
        # Given
        conversation = test_helpers.create_test_conversation(db_session)
        
        # When
        result = conversation_service.delete_conversation(conversation.id, hard_delete=True)
        
        # Then
        assert result["message"] == "대화가 완전히 삭제되었습니다."
        assert result["conversation_id"] == conversation.id
        
        # 대화가 실제로 삭제되었는지 확인
        with pytest.raises(NotFoundError):
            conversation_service.get_conversation_by_id(conversation.id)
    
    def test_search_conversations(self, conversation_service, db_session, test_helpers):
        """대화 검색 테스트"""
        # Given
        conversations = [
            test_helpers.create_test_conversation(db_session, title="Python 프로그래밍"),
            test_helpers.create_test_conversation(db_session, title="JavaScript 기초"),
            test_helpers.create_test_conversation(db_session, title="Python 고급")
        ]
        
        # When
        result = conversation_service.search_conversations("Python", limit=10)
        
        # Then
        assert len(result.results) == 2
        assert all("Python" in conv.title for conv in result.results)
        assert result.query == "Python"
    
    def test_get_conversation_statistics(self, conversation_service, db_session, test_helpers):
        """대화 통계 조회 테스트"""
        # Given
        # 최근 30일 내 대화 생성
        for i in range(3):
            conversation = test_helpers.create_test_conversation(
                db_session, 
                title=f"최근 대화 {i+1}"
            )
            # 각 대화에 메시지 추가
            test_helpers.create_test_message(
                db_session, 
                conversation.id,
                tokens_input=10,
                tokens_output=20
            )
        
        # When
        result = conversation_service.get_statistics(days=30)
        
        # Then
        assert result.conversation_count == 3
        assert result.message_count == 3
        assert result.avg_input_tokens > 0
        assert result.avg_output_tokens > 0
        assert result.period_days == 30
    
    def test_cache_integration(self, conversation_service, mock_cache_manager, db_session, test_helpers):
        """캐시 통합 테스트"""
        # Given
        conversation = test_helpers.create_test_conversation(db_session)
        cache_key = f"conversation:{conversation.id}"
        
        # 캐시에서 조회 시 None 반환 설정
        mock_cache_manager.get.return_value = None
        
        # When
        result = conversation_service.get_conversation_by_id(conversation.id)
        
        # Then
        # 캐시에서 조회를 시도했는지 확인
        mock_cache_manager.get.assert_called_with(cache_key)
        # 캐시에 저장했는지 확인
        mock_cache_manager.set.assert_called()
        assert result.id == conversation.id
    
    @patch('app.services.conversation_service.logger')
    def test_database_error_handling(self, mock_logger, conversation_service, db_session):
        """데이터베이스 에러 처리 테스트"""
        # Given
        with patch.object(db_session, 'commit', side_effect=SQLAlchemyError("DB Error")):
            # When & Then
            with pytest.raises(SQLAlchemyError):
                conversation_service.create_conversation({
                    "title": "테스트 대화",
                    "model": "claude-3"
                })
            
            # 에러 로깅 확인
            mock_logger.error.assert_called()
    
    def test_conversation_message_count_update(self, conversation_service, db_session, test_helpers, sample_message_data):
        """대화에 메시지 추가 시 메시지 수 업데이트 테스트"""
        # Given
        conversation = test_helpers.create_test_conversation(db_session)
        initial_count = conversation.message_count
        
        # When
        conversation_service.add_message(conversation.id, sample_message_data)
        
        # Then
        updated_conversation = conversation_service.get_conversation_by_id(conversation.id)
        assert updated_conversation.message_count == initial_count + 1
    
    def test_conversation_last_message_update(self, conversation_service, db_session, test_helpers, sample_message_data):
        """대화에 메시지 추가 시 마지막 메시지 시간 업데이트 테스트"""
        # Given
        conversation = test_helpers.create_test_conversation(db_session)
        message_data = sample_message_data
        
        # When
        message = conversation_service.add_message(conversation.id, message_data)
        
        # Then
        updated_conversation = conversation_service.get_conversation_by_id(conversation.id)
        assert updated_conversation.last_message_at is not None
        assert updated_conversation.last_message_at >= message.created_at
    
    def test_get_messages_pagination(self, conversation_service, db_session, test_helpers):
        """대화 메시지 페이지네이션 테스트"""
        # Given
        conversation = test_helpers.create_test_conversation(db_session)
        
        # 여러 메시지 생성
        for i in range(5):
            test_helpers.create_test_message(
                db_session,
                conversation.id,
                content=f"메시지 {i+1}"
            )
        
        # When
        result = conversation_service.get_conversation_detail(
            conversation.id,
            message_skip=2,
            message_limit=2
        )
        
        # Then
        assert len(result.messages) == 2
        assert result.message_pagination["total"] == 5
        assert result.message_pagination["skip"] == 2
        assert result.message_pagination["limit"] == 2
        assert result.message_pagination["has_more"] is True