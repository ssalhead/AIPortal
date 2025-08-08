/**
 * 채팅 페이지 - Gemini 스타일 3열 레이아웃
 */

import React, { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ChatInput } from '../components/chat/ChatInput';
import { Sidebar } from '../components/layout/Sidebar';
import { WelcomeScreen } from '../components/ui/WelcomeScreen';
import { ToastContainer, useToast } from '../components/ui/Toast';
import { TypingIndicator } from '../components/ui/TypingIndicator';
import { Resizer } from '../components/ui/Resizer';
import { useLoading } from '../contexts/LoadingContext';
import { apiService } from '../services/api';
import { Star, Zap } from 'lucide-react';
import type { LLMModel, AgentType, ConversationHistory, Citation, Source, LLMProvider } from '../types';
import { MODEL_MAP, AGENT_TYPE_MAP } from '../types';
import type { SearchResult } from '../components/search/SearchResultsCard';
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
  searchResults?: SearchResult[];
  searchQuery?: string;
  searchStatus?: {
    isSearching: boolean;
    currentStep: string;
    progress: number;
  };
}

export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<LLMProvider>('claude');
  const [selectedModel, setSelectedModel] = useState<LLMModel>('claude-4');
  const [selectedAgent, setSelectedAgent] = useState<AgentType>('none');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [chatWidth, setChatWidth] = useState(70); // 채팅 영역 비율 (%) - 7:3 비율
  const [searchProgress, setSearchProgress] = useState<{
    isSearching: boolean;
    currentStep: string;
    progress: number;
  } | null>(null);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chatAreaRef = useRef<HTMLDivElement>(null);
  const { isTyping, startTyping, stopTyping, currentModel } = useLoading();
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

  // 메시지 전송 뮤테이션 (기본 버전 - 백업용)
  const sendMessageMutation = useMutation({
    mutationFn: (messageData: { message: string; model: string; agent_type: string; session_id?: string | null }) =>
      apiService.sendChatMessage(messageData),
    onSuccess: (response, variables) => {
      // 타이핑 상태 종료
      stopTyping();
      setSearchProgress(null);
      
      // 세션 ID 업데이트 (새 세션인 경우)
      if (response.session_id && response.session_id !== currentSessionId) {
        setCurrentSessionId(response.session_id);
      }
      
      // 웹 검색 결과를 SearchResult 형식으로 변환 (웹 검색 에이전트인 경우)
      let searchResults: SearchResult[] = [];
      let searchQuery = '';
      
      if (response.agent_used === 'web_search' && response.citations) {
        searchQuery = variables.message; // 원본 사용자 쿼리를 검색 쿼리로 사용
        searchResults = response.citations.map((citation: any, index: number) => ({
          id: citation.id || `search_${index + 1}`,
          title: citation.title || '제목 없음',
          url: citation.url || '',
          snippet: citation.snippet || '',
          source: citation.source || 'unknown',
          score: citation.score || 0.8,
          timestamp: response.timestamp,
          provider: citation.source?.split('_')[0] || 'unknown'
        }));
      }

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
        searchResults: searchResults,
        searchQuery: searchQuery,
      };

      setMessages(prev => [...prev, aiMessage]);
      showSuccess('메시지가 성공적으로 전송되었습니다.');
    },
    onError: (error: any) => {
      // 타이핑 상태 종료
      stopTyping();
      setSearchProgress(null);
      
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
      
      // Toast 표시 제거 - 조용히 기록을 불러옴
      // if (convertedMessages.length > 0) {
      //   showInfo(`${convertedMessages.length / 2}개의 대화를 불러왔습니다.`);
      // }
    }
    // 채팅 히스토리가 빈 배열인 경우 메시지를 빈 배열로 초기화하되 Toast는 표시하지 않음
    else if (chatHistory && chatHistory.length === 0) {
      setMessages([]);
    }
  }, [chatHistory]); // showInfo 의존성 제거

  // 새 메시지가 추가되면 스크롤을 맨 아래로
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (message: string, model: LLMModel, agentType: AgentType) => {
    // 웹 검색 에이전트인 경우 진행 상태 시뮬레이션
    if (agentType === 'web_search') {
      // 타이핑 시작
      startTyping(`${model} 모델로 웹 검색 중...`, model);
      
      // 사용자 메시지 먼저 추가
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        content: message,
        isUser: true,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, userMessage]);

      // 검색 진행 상태 시뮬레이션
      const simulateProgress = () => {
        const steps = [
          { step: '검색어 분석 중...', progress: 10, delay: 500 },
          { step: '웹 검색 중...', progress: 40, delay: 1000 },
          { step: '검색 결과 분석 중...', progress: 70, delay: 1500 },
          { step: 'AI 분석 및 답변 생성 중...', progress: 90, delay: 2000 },
        ];
        
        let currentIndex = 0;
        
        const updateProgress = () => {
          if (currentIndex < steps.length) {
            const { step, progress } = steps[currentIndex];
            setSearchProgress({
              isSearching: true,
              currentStep: step,
              progress: progress,
            });
            currentIndex++;
            setTimeout(updateProgress, steps[currentIndex - 1]?.delay || 500);
          }
        };
        
        // 즉시 첫 번째 단계 시작
        setSearchProgress({
          isSearching: true,
          currentStep: '검색 준비 중...',
          progress: 0,
        });
        
        setTimeout(updateProgress, 300);
      };

      // 진행 상태 시뮬레이션 시작
      simulateProgress();

      try {
        const response = await apiService.sendChatMessage({
          message,
          model,
          agent_type: agentType,
          session_id: currentSessionId,
        });

        // 검색 진행 상태 및 타이핑 인디케이터 종료
        setSearchProgress(null);
        stopTyping();
        
        // 세션 ID 업데이트 (새 세션인 경우)
        if (response.session_id && response.session_id !== currentSessionId) {
          setCurrentSessionId(response.session_id);
        }
        
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

        setMessages(prev => [...prev, aiMessage]);
        showSuccess('메시지가 성공적으로 전송되었습니다.');
        
      } catch (error: any) {
        // 검색 진행 상태 및 타이핑 인디케이터 종료
        setSearchProgress(null);
        stopTyping();
        
        // 에러 메시지 추가
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          content: '죄송합니다. 메시지 처리 중 오류가 발생했습니다.',
          isUser: false,
          timestamp: new Date().toISOString(),
          agentType: 'error',
          model: 'system',
        };
        setMessages(prev => [...prev, errorMessage]);
        
        const errorMsg = error?.response?.data?.message || '메시지 전송 중 오류가 발생했습니다.';
        showError(errorMsg);
      }
    } else {
      // 기타 에이전트는 기존 방식 사용
      // 타이핑 시작
      startTyping(`${model} 모델로 응답 생성 중...`, model);
      
      // 사용자 메시지 먼저 추가
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        content: message,
        isUser: true,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, userMessage]);
      
      sendMessageMutation.mutate({
        message,
        model,
        agent_type: agentType,
        session_id: currentSessionId,
      });
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setCurrentSessionId(null); // 새 세션 시작
    showInfo('새 대화를 시작합니다.');
  };

  const handleFeatureSelect = (agentType: AgentType) => {
    // WelcomeScreen에서 기능 선택 시 에이전트 설정
    setSelectedAgent(agentType);
    showInfo(`${agentType === 'web_search' ? '웹 검색' : agentType === 'deep_research' ? '심층 리서치' : agentType === 'canvas' ? 'Canvas' : '창작'} 모드를 선택했습니다.`);
  };

  const handleResize = (leftWidthPx: number) => {
    if (containerRef.current) {
      const containerWidth = containerRef.current.offsetWidth - (isSidebarOpen ? 256 : 64); // 사이드바 너비 제외
      const leftWidthPercent = (leftWidthPx / containerWidth) * 100;
      const newChatWidth = Math.max(30, Math.min(80, leftWidthPercent)); // 30%-80% 범위로 제한
      setChatWidth(Math.round(newChatWidth * 10) / 10); // 소수점 첫째 자리까지 반올림하여 정밀도 개선
    }
  };

  const getContainerWidth = () => {
    if (containerRef.current) {
      return containerRef.current.offsetWidth - (isSidebarOpen ? 256 : 64);
    }
    return 800; // 기본값
  };

  const getChatWidthPx = () => {
    // useRef로 실제 채팅 영역 너비를 직접 가져오기
    if (chatAreaRef.current) {
      return chatAreaRef.current.offsetWidth;
    }
    
    // fallback: 계산된 값
    const containerWidth = getContainerWidth();
    const calculatedWidth = (chatWidth / 100) * containerWidth;
    return Math.round(calculatedWidth);
  };


  return (
    <div className="flex flex-col h-full bg-slate-50 dark:bg-slate-900">
      {/* Toast 컨테이너 */}
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />
      
      {/* 메인 콘텐츠 - 3열 레이아웃 */}
      <div ref={containerRef} className="flex flex-1 overflow-hidden">
        {/* 사이드바 */}
        <Sidebar
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onNewChat={handleNewChat}
          chatHistory={[]} // TODO: 실제 채팅 히스토리 연결
          onSelectChat={(chatId) => console.log('Select chat:', chatId)}
          onDeleteChat={(chatId) => console.log('Delete chat:', chatId)}
        />
        
        {selectedAgent === 'canvas' ? (
          <>
            {/* 리사이저블 채팅 영역 */}
            <div 
              ref={chatAreaRef}
              data-chat-area
              className="flex flex-col bg-white dark:bg-slate-800"
              style={{ width: `${chatWidth}%` }}
            >
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
                          searchResults={msg.searchResults}
                          searchQuery={msg.searchQuery}
                          citationMode="preview"
                        />
                      ))}
                      
                      {/* 검색 진행 상태 또는 타이핑 인디케이터 */}
                      {searchProgress && (
                        <ChatMessage
                          message=""
                          isUser={false}
                          searchStatus={searchProgress}
                          model={selectedModel}
                        />
                      )}
                      
                      {!searchProgress && isTyping && (
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

              {/* 채팅 입력 영역 - 하단 고정 */}
              <div className="flex-shrink-0 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
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
            
            {/* 리사이저 */}
            <Resizer
              onResize={handleResize}
              initialLeftWidth={getChatWidthPx()}
              minLeftWidth={Math.min(300, getContainerWidth() * 0.3)} // 컨테이너 30% 최소
              maxLeftWidth={Math.max(800, getContainerWidth() * 0.8)} // 컨테이너 80% 최대
              containerWidth={getContainerWidth()}
            />
            
            {/* Canvas 영역 */}
            <div 
              className="flex flex-col bg-slate-100 dark:bg-slate-800 min-w-0"
              style={{ width: `${100 - chatWidth}%` }}
            >
              <CanvasWorkspace />
            </div>
          </>
        ) : (
          /* Canvas가 비활성화된 경우 기존 레이아웃 */
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
                    
                    {/* 검색 진행 상태 또는 타이핑 인디케이터 */}
                    {searchProgress && (
                      <ChatMessage
                        message=""
                        isUser={false}
                        searchStatus={searchProgress}
                        model={selectedModel}
                      />
                    )}
                    
                    {!searchProgress && isTyping && (
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

            {/* 채팅 입력 영역 - 하단 고정 */}
            <div className="flex-shrink-0 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
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
        )}
      </div>
    </div>
  );
};