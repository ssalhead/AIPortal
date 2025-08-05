/**
 * 채팅 페이지
 */

import React, { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ChatInput } from '../components/chat/ChatInput';
import { apiService } from '../services/api';
import type { LLMModel, AgentType, ConversationHistory } from '../types';

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: string;
  agentType?: string;
  model?: string;
}

export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 채팅 히스토리 조회
  const { data: chatHistory } = useQuery({
    queryKey: ['chatHistory'],
    queryFn: () => apiService.getChatHistory(50),
    staleTime: 0, // 항상 최신 데이터 요청
  });

  // 메시지 전송 뮤테이션
  const sendMessageMutation = useMutation({
    mutationFn: (messageData: { message: string; model: string; agent_type: string }) =>
      apiService.sendChatMessage(messageData),
    onSuccess: (response, variables) => {
      // 사용자 메시지 추가
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        content: variables.message,
        isUser: true,
        timestamp: new Date().toISOString(),
      };

      // AI 응답 추가
      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        content: response.response,
        isUser: false,
        timestamp: response.timestamp,
        agentType: response.agent_used,
        model: response.model_used,
      };

      setMessages(prev => [...prev, userMessage, aiMessage]);
    },
    onError: (error) => {
      console.error('메시지 전송 실패:', error);
      // 에러 메시지 추가
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        content: '죄송합니다. 메시지 전송 중 오류가 발생했습니다.',
        isUser: false,
        timestamp: new Date().toISOString(),
        agentType: 'error',
        model: 'system',
      };
      setMessages(prev => [...prev, errorMessage]);
    },
  });

  // 채팅 히스토리를 메시지로 변환
  useEffect(() => {
    if (chatHistory && chatHistory.length > 0) {
      const convertedMessages: Message[] = [];
      
      chatHistory.forEach((item: ConversationHistory) => {
        // 사용자 메시지
        convertedMessages.push({
          id: `user-history-${item.id}`,
          content: item.message,
          isUser: true,
          timestamp: item.timestamp,
        });
        
        // AI 응답
        convertedMessages.push({
          id: `ai-history-${item.id}`,
          content: item.response,
          isUser: false,
          timestamp: item.timestamp,
          agentType: item.agent_type,
          model: item.model,
        });
      });
      
      setMessages(convertedMessages);
    }
  }, [chatHistory]);

  // 새 메시지가 추가되면 스크롤을 맨 아래로
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = (message: string, model: LLMModel, agentType: AgentType) => {
    sendMessageMutation.mutate({
      message,
      model,
      agent_type: agentType,
    });
  };

  return (
    <div className="flex flex-col h-screen">
      {/* 채팅 메시지 영역 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="text-6xl mb-4">🤖</div>
              <h2 className="text-2xl font-semibold text-gray-800 mb-2">
                AI 포탈에 오신 것을 환영합니다!
              </h2>
              <p className="text-gray-600">
                무엇을 도와드릴까요? 아래에 메시지를 입력해주세요.
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg.content}
                isUser={msg.isUser}
                timestamp={msg.timestamp}
                agentType={msg.agentType}
                model={msg.model}
              />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* 채팅 입력 영역 */}
      <ChatInput
        onSendMessage={handleSendMessage}
        isLoading={sendMessageMutation.isPending}
      />
    </div>
  );
};