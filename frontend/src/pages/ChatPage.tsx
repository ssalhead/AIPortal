/**
 * 채팅 페이지 - Gemini 스타일 3열 레이아웃
 */

import React, { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ChatInput } from '../components/chat/ChatInput';
import { Header } from '../components/layout/Header';
import { Sidebar } from '../components/layout/Sidebar';
import { WelcomeScreen } from '../components/ui/WelcomeScreen';
import { ToastContainer, useToast } from '../components/ui/Toast';
import { TypingIndicator } from '../components/ui/TypingIndicator';
import { useLoading } from '../contexts/LoadingContext';
import { apiService } from '../services/api';
import { Star, Zap } from 'lucide-react';
import type { LLMModel, AgentType, ConversationHistory, Citation, Source, LLMProvider } from '../types';
import { MODEL_MAP, AGENT_TYPE_MAP } from '../types';
import { CanvasWorkspace } from '../components/canvas/CanvasWorkspace';
import { useCanvasStore } from '../stores/canvasStore';

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: string;
  agentType?: string;
  model?: string;
  citations?: Citation[];
  sources?: Source[];
}

export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<LLMProvider>('claude');
  const [selectedModel, setSelectedModel] = useState<LLMModel>('claude-4');
  const [selectedAgent, setSelectedAgent] = useState<AgentType>('none');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { isTyping, stopTyping, currentModel } = useLoading();
  const { 
    toasts, 
    removeToast, 
    showSuccess, 
    showError, 
    showWarning,
    showInfo 
  } = useToast();

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
      // 타이핑 상태 종료
      stopTyping();
      
      // 사용자 메시지 추가
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        content: variables.message,
        isUser: true,
        timestamp: new Date().toISOString(),
      };

      // AI 응답 추가 (인용 정보 포함)
      const aiMessage: Message = {
        id: `ai-${Date.now()}`,
        content: response.response,
        isUser: false,
        timestamp: response.timestamp,
        agentType: response.agent_used,
        model: response.model_used,
        citations: response.citations || [],
        sources: response.sources || [],
      };

      setMessages(prev => [...prev, userMessage, aiMessage]);
      showSuccess('메시지가 성공적으로 전송되었습니다.');
    },
    onError: (error: any) => {
      // 타이핑 상태 종료
      stopTyping();
      
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
      
      // 에러 Toast 표시
      const errorMsg = error?.response?.data?.message || '메시지 전송 중 오류가 발생했습니다.';
      showError(errorMsg);
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
      
      // Toast는 한 번만 표시 (의존성 배열에서 제거)
      if (convertedMessages.length > 0) {
        showInfo('채팅 기록을 불러왔습니다.');
      }
    }
  }, [chatHistory]); // showInfo 의존성 제거

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

  const handleNewChat = () => {
    setMessages([]);
    showInfo('새 대화를 시작합니다.');
  };

  const handleFeatureSelect = (agentType: AgentType) => {
    // WelcomeScreen에서 기능 선택 시 에이전트 설정
    setSelectedAgent(agentType);
    showInfo(`${agentType === 'web_search' ? '웹 검색' : agentType === 'deep_research' ? '심층 리서치' : agentType === 'canvas' ? 'Canvas' : '창작'} 모드를 선택했습니다.`);
  };

  return (
    <div className="flex flex-col h-screen bg-slate-50 dark:bg-slate-900">
      {/* Toast 컨테이너 */}
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />
      
      {/* 헤더 */}
      <Header />
      
      {/* 메인 콘텐츠 - 3열 레이아웃 */}
      <div className="flex flex-1 overflow-hidden">
        {/* 사이드바 */}
        <Sidebar
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onNewChat={handleNewChat}
          chatHistory={[]} // TODO: 실제 채팅 히스토리 연결
          onSelectChat={(chatId) => console.log('Select chat:', chatId)}
          onDeleteChat={(chatId) => console.log('Delete chat:', chatId)}
        />
        
        {/* 중앙 채팅 영역 */}
        <div className="flex-1 flex flex-col bg-white dark:bg-slate-800">
          {/* 채팅 헤더 - 선택된 모델과 기능 표시 */}
          {messages.length > 0 && (
            <div className="border-b border-slate-200 dark:border-slate-700 px-6 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {/* 모델 표시 */}
                  <div className="flex items-center space-x-2">
                    {selectedProvider === 'claude' ? (
                      <div className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 rounded-full text-sm font-medium">
                        <Star className="w-3.5 h-3.5" />
                        <span>Claude</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium">
                        <Zap className="w-3.5 h-3.5" />
                        <span>Gemini</span>
                      </div>
                    )}
                    
                    {/* 모델 버전 */}
                    <span className="text-sm text-slate-600 dark:text-slate-400">
                      {MODEL_MAP[selectedProvider]?.find(m => m.id === selectedModel)?.name}
                    </span>
                    
                    {/* 에이전트 표시 */}
                    {selectedAgent && selectedAgent !== 'none' && (
                      <div className={`px-3 py-1.5 rounded-full text-sm font-medium ${
                        selectedAgent === 'web_search' 
                          ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                          : selectedAgent === 'deep_research'
                          ? 'bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300'
                          : 'bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300'
                      }`}>
                        {AGENT_TYPE_MAP[selectedAgent]?.name}
                      </div>
                    )}
                  </div>
                </div>
                
                {/* 채팅 액션 */}
                <div className="text-sm text-slate-500 dark:text-slate-400">
                  {messages.length}개 메시지
                </div>
              </div>
            </div>
          )}
          
          {/* 채팅 메시지 영역 */}
          <div className="flex-1 overflow-y-auto">
            <div className="h-full">
              {messages.length === 0 ? (
                <WelcomeScreen onFeatureSelect={handleFeatureSelect} />
              ) : (
                <div className="px-6 py-6 space-y-6 max-w-4xl mx-auto">
                  {messages.map((msg, index) => (
                    <ChatMessage
                      key={msg.id}
                      message={msg.content}
                      isUser={msg.isUser}
                      timestamp={msg.timestamp}
                      agentType={msg.agentType}
                      model={msg.model}
                      citations={msg.citations}
                      sources={msg.sources}
                      citationMode="preview"
                    />
                  ))}
                  
                  {/* 타이핑 인디케이터 */}
                  {isTyping && (
                    <ChatMessage
                      message=""
                      isUser={false}
                      isTyping={true}
                      model={currentModel}
                    />
                  )}
                  
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          </div>

          {/* 채팅 입력 영역 */}
          <div className="border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
            <ChatInput
              onSendMessage={handleSendMessage}
              isLoading={sendMessageMutation.isPending}
              selectedProvider={selectedProvider}
              selectedModel={selectedModel}
              selectedAgent={selectedAgent}
              onProviderChange={setSelectedProvider}
              onModelChange={setSelectedModel}
              onAgentChange={setSelectedAgent}
            />
          </div>
        </div>
        
        {/* 오른쪽 패널 (Canvas 기능 활성화시에만 표시) */}
        {selectedAgent === 'canvas' && (
          <div className="flex-1 max-w-2xl bg-slate-100 dark:bg-slate-800 border-l border-slate-200 dark:border-slate-700 xl:flex flex-col hidden">
            <CanvasWorkspace />
          </div>
        )}
      </div>
    </div>
  );
};