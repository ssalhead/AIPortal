/**
 * WebSocket 기반 실시간 채팅 페이지
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ChatInput } from '../components/chat/ChatInput';
import { useWebSocket, WebSocketResponse } from '../hooks/useWebSocket';
import type { LLMModel, AgentType } from '../types';

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: string;
  agentType?: string;
  model?: string;
  isStreaming?: boolean;
}

export const WebSocketChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentStreamingMessageId, setCurrentStreamingMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // WebSocket 연결 상태 메시지 처리
  const handleWebSocketMessage = useCallback((response: WebSocketResponse) => {
    switch (response.type) {
      case 'connection':
        console.log('WebSocket 연결 확인됨');
        break;

      case 'message_received':
        console.log('메시지 수신 확인됨:', response.message_id);
        break;

      case 'assistant_start':
        // 새로운 AI 메시지 시작
        const newMessageId = `ai-${Date.now()}`;
        setCurrentStreamingMessageId(newMessageId);
        
        const streamingMessage: Message = {
          id: newMessageId,
          content: '',
          isUser: false,
          timestamp: new Date().toISOString(),
          isStreaming: true,
        };
        
        setMessages(prev => [...prev, streamingMessage]);
        break;

      case 'assistant_chunk':
        // 스트리밍 청크 추가
        if (response.content && currentStreamingMessageId) {
          setMessages(prev => 
            prev.map(msg => 
              msg.id === currentStreamingMessageId 
                ? { ...msg, content: msg.content + response.content }
                : msg
            )
          );
        }
        break;

      case 'assistant_end':
        // 스트리밍 완료
        if (currentStreamingMessageId) {
          setMessages(prev => 
            prev.map(msg => 
              msg.id === currentStreamingMessageId 
                ? { ...msg, isStreaming: false }
                : msg
            )
          );
          setCurrentStreamingMessageId(null);
        }
        break;

      case 'error':
        // 에러 메시지 추가
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          content: `오류: ${response.message || '알 수 없는 오류가 발생했습니다.'}`,
          isUser: false,
          timestamp: new Date().toISOString(),
          agentType: 'error',
          model: 'system',
        };
        setMessages(prev => [...prev, errorMessage]);
        break;
    }
  }, [currentStreamingMessageId]);

  // WebSocket 훅 사용
  const {
    isConnected,
    isConnecting,
    isTyping,
    connect,
    disconnect,
    sendMessage,
    sendPing,
    error: wsError
  } = useWebSocket({
    conversationId: `chat-${Date.now()}`,
    userId: 'user-1',
    onMessage: handleWebSocketMessage,
    onConnect: () => {
      console.log('WebSocket 연결됨');
      // 연결 성공 메시지 추가
      const connectMessage: Message = {
        id: `system-${Date.now()}`,
        content: '✅ 실시간 채팅이 시작되었습니다! WebSocket 연결이 완료되었습니다.',
        isUser: false,
        timestamp: new Date().toISOString(),
        agentType: 'system',
        model: 'websocket',
      };
      setMessages(prev => [...prev, connectMessage]);
    },
    onDisconnect: () => {
      console.log('WebSocket 연결 해제됨');
    },
    onError: (error) => {
      console.error('WebSocket 오류:', error);
    }
  });

  // 컴포넌트 마운트 시 자동 연결
  useEffect(() => {
    if (!isConnected && !isConnecting) {
      connect();
    }
  }, [connect, isConnected, isConnecting]);

  // 새 메시지가 추가되면 스크롤을 맨 아래로
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = useCallback((message: string, model: LLMModel, agentType: AgentType) => {
    if (!isConnected) {
      alert('WebSocket이 연결되지 않았습니다. 연결 버튼을 클릭해주세요.');
      return;
    }

    // 사용자 메시지 추가
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      content: message,
      isUser: true,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);

    // WebSocket으로 메시지 전송
    sendMessage({
      type: 'chat',
      content: message,
      model,
      agent_type: agentType,
      metadata: {
        timestamp: new Date().toISOString(),
        user_id: 'user-1'
      }
    });
  }, [isConnected, sendMessage]);

  const handleReconnect = () => {
    disconnect();
    setTimeout(connect, 1000);
  };

  const handlePingTest = () => {
    sendPing();
  };

  return (
    <div className="flex flex-col h-screen">
      {/* 연결 상태 표시바 */}
      <div className={`px-4 py-2 text-sm font-medium transition-colors duration-300 ${
        isConnected 
          ? 'bg-green-100 text-green-800 border-b border-green-200'
          : isConnecting
          ? 'bg-yellow-100 text-yellow-800 border-b border-yellow-200'
          : 'bg-red-100 text-red-800 border-b border-red-200'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : isConnecting ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'
            }`} />
            <span>
              {isConnected 
                ? '✅ 실시간 채팅 연결됨' 
                : isConnecting 
                ? '🔄 연결 중...' 
                : '❌ 연결 끊어짐'}
            </span>
            {isTyping && <span className="text-blue-600">🤖 AI가 응답 중...</span>}
          </div>
          
          <div className="flex space-x-2">
            <button
              onClick={handlePingTest}
              disabled={!isConnected}
              className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
            >
              Ping 테스트
            </button>
            <button
              onClick={handleReconnect}
              className="px-2 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600"
            >
              재연결
            </button>
          </div>
        </div>
        
        {wsError && (
          <div className="mt-1 text-red-600 text-xs">
            오류: {wsError}
          </div>
        )}
      </div>

      {/* 채팅 메시지 영역 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-6xl mb-4">🚀</div>
              <h2 className="text-2xl font-semibold text-gray-800 mb-2">
                실시간 AI 채팅에 오신 것을 환영합니다!
              </h2>
              <p className="text-gray-600 mb-4">
                WebSocket을 통한 실시간 스트리밍 채팅을 경험해보세요.
              </p>
              <div className="text-sm text-gray-500 space-y-1">
                <p>• 실시간 타이핑 표시</p>
                <p>• 스트리밍 응답</p>
                <p>• 자동 재연결</p>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <div key={msg.id}>
                <ChatMessage
                  message={msg.content}
                  isUser={msg.isUser}
                  timestamp={msg.timestamp}
                  agentType={msg.agentType}
                  model={msg.model}
                />
                {msg.isStreaming && (
                  <div className="flex justify-start mb-2">
                    <div className="bg-gray-100 rounded-lg px-3 py-2 text-sm text-gray-500">
                      <div className="flex items-center space-x-1">
                        <div className="flex space-x-1">
                          <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce"></div>
                          <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                        <span>스트리밍 중...</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* 채팅 입력 영역 */}
      <ChatInput
        onSendMessage={handleSendMessage}
        isLoading={isTyping || !isConnected}
        placeholder={
          !isConnected 
            ? "연결을 기다리는 중..." 
            : isTyping 
            ? "AI가 응답 중입니다..."
            : "실시간 메시지를 입력하세요..."
        }
      />
    </div>
  );
};