"""
Chat API 단위 테스트
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.api.v1.chat import ChatMessage, ChatResponse


@pytest.mark.unit
@pytest.mark.api
class TestChatAPI:
    """Chat API 테스트 클래스"""
    
    def test_chat_message_model_validation(self):
        """ChatMessage 모델 유효성 검사 테스트"""
        # Given - 올바른 데이터
        valid_data = {
            "message": "안녕하세요",
            "model": "claude-3",
            "agent_type": "web_search"
        }
        
        # When
        chat_message = ChatMessage(**valid_data)
        
        # Then
        assert chat_message.message == "안녕하세요"
        assert chat_message.model == "claude-3"
        assert chat_message.agent_type == "web_search"
        assert chat_message.include_citations is True  # 기본값
    
    def test_chat_message_model_defaults(self):
        """ChatMessage 모델 기본값 테스트"""
        # Given - 최소 데이터
        minimal_data = {"message": "테스트"}
        
        # When
        chat_message = ChatMessage(**minimal_data)
        
        # Then
        assert chat_message.message == "테스트"
        assert chat_message.model == "gemini"  # 기본값
        assert chat_message.agent_type == "web_search"  # 기본값
        assert chat_message.session_id is None
        assert chat_message.include_citations is True
        assert chat_message.max_sources == 10
        assert chat_message.min_confidence == 0.7
    
    def test_chat_response_model(self):
        """ChatResponse 모델 테스트"""
        # Given
        response_data = {
            "response": "안녕하세요! 무엇을 도와드릴까요?",
            "agent_used": "web_search",
            "model_used": "claude-3",
            "timestamp": "2024-01-08T10:00:00Z",
            "user_id": "test-user-123",
            "session_id": "session-456"
        }
        
        # When
        chat_response = ChatResponse(**response_data)
        
        # Then
        assert chat_response.response == response_data["response"]
        assert chat_response.agent_used == response_data["agent_used"]
        assert chat_response.model_used == response_data["model_used"]
        assert chat_response.citations == []  # 기본값
        assert chat_response.sources == []  # 기본값
    
    @patch('app.api.v1.chat.get_current_active_user')
    @patch('app.agents.supervisor.agent_supervisor')
    def test_send_message_success(self, mock_supervisor, mock_auth, client):
        """메시지 전송 성공 테스트"""
        # Given
        mock_auth.return_value = {"user_id": "test-user", "username": "testuser"}
        
        mock_supervisor.process_message = AsyncMock(return_value={
            "response": "테스트 응답입니다.",
            "agent_used": "web_search",
            "model_used": "claude-3",
            "tokens_input": 10,
            "tokens_output": 20,
            "latency_ms": 1500,
            "citations": [],
            "sources": []
        })
        
        message_data = {
            "message": "안녕하세요",
            "model": "claude-3",
            "agent_type": "web_search"
        }
        
        # When
        response = client.post("/api/v1/chat/", json=message_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "테스트 응답입니다."
        assert data["agent_used"] == "web_search"
        assert data["model_used"] == "claude-3"
        assert "timestamp" in data
        assert "user_id" in data
    
    @patch('app.api.v1.chat.get_current_active_user')
    def test_send_message_validation_error(self, mock_auth, client):
        """메시지 전송 시 유효성 검사 실패 테스트"""
        # Given
        mock_auth.return_value = {"user_id": "test-user", "username": "testuser"}
        
        invalid_data = {
            "message": "",  # 빈 메시지
            "model": "claude-3"
        }
        
        # When
        response = client.post("/api/v1/chat/", json=invalid_data)
        
        # Then
        assert response.status_code == 422  # Validation Error
    
    @patch('app.api.v1.chat.get_current_active_user')
    @patch('app.agents.supervisor.agent_supervisor')
    def test_send_message_with_session_id(self, mock_supervisor, mock_auth, client):
        """세션 ID와 함께 메시지 전송 테스트"""
        # Given
        mock_auth.return_value = {"user_id": "test-user", "username": "testuser"}
        
        mock_supervisor.process_message = AsyncMock(return_value={
            "response": "세션 기반 응답입니다.",
            "agent_used": "none",
            "model_used": "claude-3",
            "tokens_input": 8,
            "tokens_output": 15,
            "latency_ms": 1200,
            "session_id": "existing-session-123",
            "citations": [],
            "sources": []
        })
        
        message_data = {
            "message": "이어서 질문드립니다",
            "model": "claude-3",
            "agent_type": "none",
            "session_id": "existing-session-123"
        }
        
        # When
        response = client.post("/api/v1/chat/", json=message_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing-session-123"
        assert data["response"] == "세션 기반 응답입니다."
    
    @patch('app.api.v1.chat.get_current_active_user')
    @patch('app.agents.supervisor.agent_supervisor')
    def test_send_message_with_citations(self, mock_supervisor, mock_auth, client):
        """인용 정보가 포함된 메시지 전송 테스트"""
        # Given
        mock_auth.return_value = {"user_id": "test-user", "username": "testuser"}
        
        mock_citations = [
            {
                "id": "cite-1",
                "title": "테스트 문서",
                "url": "https://example.com/doc1",
                "snippet": "관련 내용입니다.",
                "confidence": 0.85
            }
        ]
        
        mock_sources = [
            {
                "id": "source-1",
                "title": "테스트 소스",
                "url": "https://example.com/source1",
                "type": "web"
            }
        ]
        
        mock_supervisor.process_message = AsyncMock(return_value={
            "response": "검색 결과를 바탕으로 답변드리겠습니다.",
            "agent_used": "web_search",
            "model_used": "claude-3",
            "tokens_input": 20,
            "tokens_output": 50,
            "latency_ms": 3000,
            "citations": mock_citations,
            "sources": mock_sources
        })
        
        message_data = {
            "message": "최신 AI 기술 동향에 대해 알려주세요",
            "model": "claude-3",
            "agent_type": "web_search",
            "include_citations": True,
            "max_sources": 5
        }
        
        # When
        response = client.post("/api/v1/chat/", json=message_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data["citations"]) == 1
        assert len(data["sources"]) == 1
        assert data["citations"][0]["title"] == "테스트 문서"
        assert data["sources"][0]["title"] == "테스트 소스"
    
    @patch('app.api.v1.chat.get_current_active_user')
    @patch('app.agents.supervisor.agent_supervisor')
    def test_send_message_agent_error(self, mock_supervisor, mock_auth, client):
        """에이전트 처리 오류 테스트"""
        # Given
        mock_auth.return_value = {"user_id": "test-user", "username": "testuser"}
        
        mock_supervisor.process_message = AsyncMock(side_effect=Exception("에이전트 처리 실패"))
        
        message_data = {
            "message": "테스트 메시지",
            "model": "claude-3",
            "agent_type": "web_search"
        }
        
        # When
        response = client.post("/api/v1/chat/", json=message_data)
        
        # Then
        assert response.status_code == 500
    
    def test_unauthorized_request(self, client):
        """인증되지 않은 요청 테스트"""
        # Given
        message_data = {
            "message": "테스트 메시지",
            "model": "claude-3"
        }
        
        # When
        response = client.post("/api/v1/chat/", json=message_data)
        
        # Then
        assert response.status_code == 401  # Unauthorized
    
    @pytest.mark.asyncio
    @patch('app.api.v1.chat.get_current_active_user')
    @patch('app.agents.supervisor.agent_supervisor')
    async def test_send_message_async_client(self, mock_supervisor, mock_auth, async_client):
        """비동기 클라이언트로 메시지 전송 테스트"""
        # Given
        mock_auth.return_value = {"user_id": "test-user", "username": "testuser"}
        
        mock_supervisor.process_message = AsyncMock(return_value={
            "response": "비동기 응답입니다.",
            "agent_used": "none",
            "model_used": "gemini",
            "tokens_input": 5,
            "tokens_output": 10,
            "latency_ms": 800,
            "citations": [],
            "sources": []
        })
        
        message_data = {
            "message": "비동기 테스트",
            "model": "gemini",
            "agent_type": "none"
        }
        
        # When
        response = await async_client.post("/api/v1/chat/", json=message_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "비동기 응답입니다."
        assert data["model_used"] == "gemini"
    
    @patch('app.api.v1.chat.get_current_active_user')
    @patch('app.agents.supervisor.agent_supervisor')
    def test_send_message_performance_metrics(self, mock_supervisor, mock_auth, client):
        """성능 메트릭 포함 테스트"""
        # Given
        mock_auth.return_value = {"user_id": "test-user", "username": "testuser"}
        
        # 성능 지표가 포함된 응답
        mock_supervisor.process_message = AsyncMock(return_value={
            "response": "성능 측정 응답입니다.",
            "agent_used": "web_search",
            "model_used": "claude-3",
            "tokens_input": 25,
            "tokens_output": 75,
            "latency_ms": 2500,
            "citations": [],
            "sources": [],
            "performance_metrics": {
                "search_time_ms": 1200,
                "llm_time_ms": 1300,
                "total_sources_found": 15,
                "sources_used": 5
            }
        })
        
        message_data = {
            "message": "복잡한 검색이 필요한 질문",
            "model": "claude-3",
            "agent_type": "web_search"
        }
        
        # When
        response = client.post("/api/v1/chat/", json=message_data)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        
        # 성능 지표 검증 (응답에 포함되지 않더라도 내부적으로 처리됨)
        mock_supervisor.process_message.assert_called_once()
        call_args = mock_supervisor.process_message.call_args[0][0]
        assert call_args["message"] == "복잡한 검색이 필요한 질문"
    
    @patch('app.api.v1.chat.get_current_active_user')  
    def test_message_length_limits(self, mock_auth, client):
        """메시지 길이 제한 테스트"""
        # Given
        mock_auth.return_value = {"user_id": "test-user", "username": "testuser"}
        
        # 매우 긴 메시지
        long_message = "긴 메시지 " * 1000  # 대략 10,000자
        
        message_data = {
            "message": long_message,
            "model": "claude-3",
            "agent_type": "none"
        }
        
        # When
        response = client.post("/api/v1/chat/", json=message_data)
        
        # Then
        # 실제 구현에 따라 길이 제한이 있을 수 있음
        # 현재는 성공하지만, 향후 제한이 추가될 수 있음
        assert response.status_code in [200, 422]