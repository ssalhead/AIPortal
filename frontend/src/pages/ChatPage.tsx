/**
 * 채팅 페이지 - Gemini 스타일 3열 레이아웃
 */

import React, { useState, useRef, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChatMessage } from '../components/chat/ChatMessage';
import { ChatInput } from '../components/chat/ChatInput';
import { Sidebar } from '../components/layout/Sidebar';
import { WelcomeScreen } from '../components/ui/WelcomeScreen';
import { ToastContainer, useToast } from '../components/ui/Toast';
import { TypingIndicator } from '../components/ui/TypingIndicator';
import { Resizer } from '../components/ui/Resizer';
import { SearchProgressIndicator } from '../components/SearchProcess/SearchProgressIndicator';
import { useLoading } from '../contexts/LoadingContext';
import { useResponsive, useTouchDevice } from '../hooks/useResponsive';
import { useSidebarWidth } from '../hooks/useSidebarWidth';
import { apiService } from '../services/api';
import { conversationHistoryService } from '../services/conversationHistoryService';
import { Star, Zap, Menu, X } from 'lucide-react';
import type { LLMModel, AgentType, ConversationHistory, Citation, Source, LLMProvider } from '../types';
import { MODEL_MAP, AGENT_TYPE_MAP } from '../types';
import { SIDEBAR_WIDTHS, CANVAS_SPLIT } from '../constants/layout';
import type { SearchResult } from '../components/search/SearchResultsCard';
import type { SearchStep } from '../components/SearchProcess/SearchProgressIndicator';
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
  searchSteps?: SearchStep[];
}

export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<LLMProvider>('claude');
  const [selectedModel, setSelectedModel] = useState<LLMModel>('claude-4');
  const [selectedAgent, setSelectedAgent] = useState<AgentType>('none');
  
  // 반응형 hooks
  const { isMobile, isTablet, isDesktop } = useResponsive();
  const isTouchDevice = useTouchDevice();
  const { getSidebarWidth, getMainContentMargin, getContainerWidth } = useSidebarWidth();
  
  // 반응형 사이드바 상태
  const [isSidebarOpen, setIsSidebarOpen] = useState(!isMobile); // 모바일에서는 기본적으로 닫힘
  const [chatWidth, setChatWidth] = useState(CANVAS_SPLIT.DEFAULT_CHAT_WIDTH); // 채팅 영역 비율 (%) - 7:3 비율
  const [searchProgress, setSearchProgress] = useState<{
    isSearching: boolean;
    currentStep: string;
    progress: number;
  } | null>(null);
  const [searchSteps, setSearchSteps] = useState<SearchStep[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chatAreaRef = useRef<HTMLDivElement>(null);
  const { isTyping, startTyping, stopTyping, currentModel } = useLoading();
  const queryClient = useQueryClient();

  // 대화 기록 로딩
  const { data: chatHistoryData, refetch: refetchHistory } = useQuery({
    queryKey: ['conversations'],
    queryFn: async () => {
      try {
        const response = await conversationHistoryService.getConversations({ limit: 50 });
        return response.conversations;
      } catch (error) {
        console.error('대화 기록 로딩 실패:', error);
        return [];
      }
    },
    staleTime: 0, // 항상 최신 데이터 가져오기
    cacheTime: 1000 * 60, // 1분간 캐시 유지
  });

  // 안전하게 chatHistory 처리 및 형식 변환
  const chatHistory = Array.isArray(chatHistoryData) 
    ? chatHistoryData.map(item => ({
        id: item.id,
        title: item.title,
        timestamp: item.updated_at || item.created_at // updated_at을 timestamp로 사용
      }))
    : [];

  const { 
    toasts, 
    removeToast, 
    showSuccess, 
    showError, 
    showWarning,
    showInfo 
  } = useToast();

  // 대화 삭제 뮤테이션 (Optimistic Updates 포함)
  const deleteConversationMutation = useMutation({
    mutationFn: async (conversationId: string) => {
      await conversationHistoryService.deleteConversation(conversationId);
      return conversationId;
    },
    onMutate: async (deletedConversationId) => {
      // Optimistic Update: 낙관적 업데이트로 즉시 UI 반영
      await queryClient.cancelQueries({ queryKey: ['conversations'] });
      
      // 이전 데이터 스냅샷 저장 (롤백용)
      const previousConversations = queryClient.getQueryData(['conversations']);
      
      // 낙관적 업데이트: 삭제된 대화를 즉시 목록에서 제거
      queryClient.setQueryData(['conversations'], (old: any[]) => 
        old ? old.filter(conv => conv.id !== deletedConversationId) : []
      );
      
      return { previousConversations };
    },
    onSuccess: async (deletedConversationId) => {
      // 서버에서 최신 데이터 다시 가져오기
      await refetchHistory();
      
      // 최신 대화 목록 가져오기
      const updatedHistoryData = queryClient.getQueryData<any[]>(['conversations']) || [];
      const updatedHistory = updatedHistoryData.map(item => ({
        id: item.id,
        title: item.title,
        timestamp: item.updated_at || item.created_at
      }));
      
      showSuccess('대화가 삭제되었습니다.');
      
      // 현재 선택된 대화가 삭제된 경우
      if (currentSessionId === deletedConversationId) {
        setMessages([]);
        
        if (updatedHistory.length > 0) {
          // 가장 최근 대화로 자동 전환
          const latestChat = updatedHistory[0];
          await loadConversation(latestChat.id);
          showInfo(`"${latestChat.title}" 대화로 이동했습니다.`);
        } else {
          // 모든 대화가 삭제된 경우 새 대화 준비
          setCurrentSessionId(null);
          showInfo('새로운 대화를 시작해보세요.');
        }
      } 
      // 선택되지 않은 대화가 삭제되었지만, 현재 화면이 빈 상태인 경우
      else if (!currentSessionId && updatedHistory.length > 0) {
        // 가장 최근 대화로 자동 이동
        const latestChat = updatedHistory[0];
        await loadConversation(latestChat.id);
        showInfo(`"${latestChat.title}" 대화를 불러왔습니다.`);
      }
    },
    onError: (error, deletedConversationId, context) => {
      // 에러 발생 시 이전 상태로 롤백
      if (context?.previousConversations) {
        queryClient.setQueryData(['conversations'], context.previousConversations);
      }
      
      console.error('대화 삭제 실패:', error);
      showError('대화를 삭제할 수 없습니다.');
    }
  });

  // 대화 로드 함수 분리 (재사용성을 위해)
  const loadConversation = async (conversationId: string) => {
    try {
      const conversation = await conversationHistoryService.getConversationDetail(conversationId);
      
      // 메시지를 UI 형식으로 변환
      const formattedMessages: Message[] = conversation.messages.map((msg: any, index: number) => ({
        id: msg.id || `msg-${index}`,
        content: msg.content,
        isUser: msg.role === 'USER',
        timestamp: msg.created_at,
        model: msg.model,
        agentType: conversation.agent_type,
        citations: [],
        sources: []
      }));
      
      setMessages(formattedMessages);
      setCurrentSessionId(conversationId);
      
      // 모델과 에이전트 타입도 동기화
      if (conversation.model) {
        const modelKey = conversation.model as LLMModel;
        if (MODEL_MAP[modelKey]) {
          const provider = modelKey.startsWith('claude') ? 'claude' : 'gemini';
          setSelectedProvider(provider as LLMProvider);
          setSelectedModel(modelKey);
        }
      }
      
      if (conversation.agent_type) {
        setSelectedAgent(conversation.agent_type as AgentType);
      }
      
      return conversation;
    } catch (error) {
      console.error('대화 로딩 실패:', error);
      throw error;
    }
  };

  // 메시지 전송 뮤테이션 (기본 버전 - 백업용)
  const sendMessageMutation = useMutation({
    mutationFn: (messageData: { message: string; model: string; agent_type: string; session_id?: string | null }) => {
      console.log('API 호출 시작:', messageData);
      return apiService.sendChatMessage(messageData);
    },
    onSuccess: (response, variables) => {
      console.log('🎉 onSuccess 콜백 실행됨!', response);
      
      // 타이핑 상태 종료
      stopTyping();
      setSearchProgress(null);
      setSearchSteps([]);
      
      // 세션 ID 업데이트 (새 세션인 경우)
      if (response.session_id && response.session_id !== currentSessionId) {
        setCurrentSessionId(response.session_id);
      }
      
      // 웹 검색 결과를 SearchResult 형식으로 변환 (웹 검색 에이전트인 경우)
      let searchResults: SearchResult[] = [];
      let searchQuery = '';
      
      console.log('Response data:', {
        agent_used: response.agent_used,
        has_citations: !!response.citations,
        citations_length: response.citations?.length,
        citations_data: response.citations
      });
      
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
        
        // 디버그용 로그 추가
        console.log('웹 검색 결과:', {
          agent_used: response.agent_used,
          citations_count: response.citations?.length || 0,
          searchResults_count: searchResults.length,
          searchQuery,
          sample_citation: response.citations?.[0]
        });
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
      // 성공 토스트는 제거 - 메시지가 화면에 나타나는 것으로 충분
    },
    onError: (error: any) => {
      // 타이핑 상태 종료
      stopTyping();
      setSearchProgress(null);
      setSearchSteps([]);
      
      console.error('메시지 전송 실패:', error);
      console.error('에러 상세:', {
        status: error?.response?.status,
        data: error?.response?.data,
        message: error?.message
      });
      
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
  }, [chatHistory?.length]); // 길이만 감지하여 무한 루프 방지

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

      // 상세한 검색 진행 단계 시뮬레이션
      const simulateDetailedProgress = () => {
        const initialSteps: SearchStep[] = [
          {
            id: 'query_analysis',
            name: '검색어 분석',
            description: '사용자 질문을 분석하고 검색 키워드를 추출합니다',
            status: 'pending',
            startTime: new Date(),
            progress: 0,
            details: []
          },
          {
            id: 'query_generation', 
            name: '검색 쿼리 생성',
            description: '최적화된 검색 쿼리를 생성합니다',
            status: 'pending',
            startTime: undefined,
            progress: 0,
            details: []
          },
          {
            id: 'parallel_search',
            name: '병렬 웹 검색',
            description: '여러 검색 엔진에서 동시에 검색을 수행합니다',
            status: 'pending',
            startTime: undefined,
            progress: 0,
            details: []
          },
          {
            id: 'result_filtering',
            name: '결과 필터링',
            description: '검색 결과의 품질을 평가하고 필터링합니다',
            status: 'pending',
            startTime: undefined,
            progress: 0,
            details: []
          },
          {
            id: 'result_ranking',
            name: '결과 순위화',
            description: '관련성과 신뢰도에 따라 결과를 순위화합니다',
            status: 'pending',
            startTime: undefined,
            progress: 0,
            details: []
          },
          {
            id: 'response_generation',
            name: 'AI 답변 생성',
            description: '검색 결과를 바탕으로 종합적인 답변을 생성합니다',
            status: 'pending',
            startTime: undefined,
            progress: 0,
            details: []
          }
        ];

        setSearchSteps(initialSteps);

        // 단계별 진행 시뮬레이션
        const progressSteps = [
          { 
            stepId: 'query_analysis', 
            delay: 500, 
            duration: 800,
            details: [
              '질문 의도 파악 중...',
              '핵심 키워드 추출 중...',
              '검색 전략 수립 중...'
            ],
            metadata: { keywords: message.split(' ').slice(0, 3) }
          },
          { 
            stepId: 'query_generation', 
            delay: 1200, 
            duration: 600,
            details: [
              '검색 엔진 최적화 쿼리 생성',
              '동의어 및 관련 용어 추가',
              '검색 범위 설정'
            ],
            metadata: { queries: ['주요 쿼리', '보조 쿼리 1', '보조 쿼리 2'] }
          },
          { 
            stepId: 'parallel_search', 
            delay: 1800, 
            duration: 2000,
            details: [
              'Google 검색 실행 중...',
              'Bing 검색 실행 중...',
              '추가 소스 검색 중...',
              '검색 결과 수집 완료'
            ],
            metadata: { sources: 4, totalResults: 28 }
          },
          { 
            stepId: 'result_filtering', 
            delay: 3800, 
            duration: 1000,
            details: [
              '중복 결과 제거 중...',
              '품질 점수 계산 중...',
              '관련성 평가 중...',
              '신뢰도 검증 중...'
            ],
            metadata: { filteredResults: 12, qualityScore: 8.5 }
          },
          { 
            stepId: 'result_ranking', 
            delay: 4800, 
            duration: 800,
            details: [
              '관련성 점수 계산',
              '신뢰도 가중치 적용',
              '최종 순위 결정'
            ],
            metadata: { topResults: 5, avgRelevance: 9.2 }
          },
          { 
            stepId: 'response_generation', 
            delay: 5600, 
            duration: 1500,
            details: [
              '핵심 정보 추출 중...',
              '답변 구조 설계 중...',
              '인용 정보 정리 중...',
              '최종 답변 생성 중...'
            ],
            metadata: { citations: 3, confidence: 0.92 }
          }
        ];

        progressSteps.forEach(({ stepId, delay, duration, details, metadata }) => {
          // 단계 시작
          setTimeout(() => {
            setSearchSteps(prev => prev.map(step => 
              step.id === stepId 
                ? { 
                    ...step, 
                    status: 'in_progress', 
                    startTime: new Date(),
                    details: details,
                    metadata: metadata
                  }
                : step
            ));

            // 진행률 업데이트 (애니메이션)
            let progress = 0;
            const progressInterval = setInterval(() => {
              progress += Math.random() * 25;
              if (progress >= 100) {
                progress = 100;
                clearInterval(progressInterval);
                
                // 단계 완료
                setTimeout(() => {
                  setSearchSteps(prev => prev.map(step => 
                    step.id === stepId 
                      ? { ...step, status: 'completed', endTime: new Date(), progress: 100 }
                      : step
                  ));
                }, 200);
              } else {
                setSearchSteps(prev => prev.map(step => 
                  step.id === stepId ? { ...step, progress } : step
                ));
              }
            }, duration / 10);
          }, delay);
        });
      };

      // 상세 진행 상태 시뮬레이션 시작
      simulateDetailedProgress();

      try {
        const response = await apiService.sendChatMessage({
          message,
          model,
          agent_type: agentType,
          session_id: currentSessionId,
        });

        // 검색 진행 상태 및 타이핑 인디케이터 종료
        setSearchProgress(null);
        setSearchSteps([]);
        stopTyping();
        
        // 세션 ID 업데이트 (새 세션인 경우)
        const isNewSession = response.session_id && response.session_id !== currentSessionId;
        if (isNewSession) {
          setCurrentSessionId(response.session_id);
          
          // 새 세션인 경우 제목 자동 생성
          try {
            const generatedTitle = await conversationHistoryService.generateTitle(message, model);
            await conversationHistoryService.updateConversation(response.session_id, {
              title: generatedTitle
            });
          } catch (error) {
            console.error('제목 생성 실패:', error);
          }
        }
        
        // 새 메시지가 추가된 경우 대화 기록 즉시 새로고침
        queryClient.invalidateQueries({ queryKey: ['conversations'] });
        await refetchHistory();
        
        // 웹 검색 결과를 SearchResult 형식으로 변환
        let searchResults: SearchResult[] = [];
        let searchQuery = '';
        
        if (response.agent_used === 'web_search' && response.citations) {
          searchQuery = message; // 원본 사용자 쿼리를 검색 쿼리로 사용
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
          
          console.log('웹 검색 결과 변환 완료:', {
            searchQuery,
            searchResults_count: searchResults.length,
            sample_result: searchResults[0]
          });
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
        // 성공 토스트는 제거 - 메시지가 화면에 나타나는 것으로 충분
        
      } catch (error: any) {
        // 검색 진행 상태 및 타이핑 인디케이터 종료
        setSearchProgress(null);
        setSearchSteps([]);
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

  const handleNewChat = async () => {
    try {
      // 새 세션 생성
      const newSession = await apiService.httpClient.post('/v1/chat/sessions/new');
      const sessionData = newSession.data;
      
      setMessages([]);
      setCurrentSessionId(sessionData.session_id);
      
      // Canvas 상태 초기화
      if (selectedAgent === 'canvas') {
        clearCanvas();
      }
      
      // 대화 기록 새로고침
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      await refetchHistory();
      
      showSuccess('새 대화를 시작했습니다.');
      
      // 모바일에서는 새 대화 시작 시 사이드바 자동 닫기
      if (isMobile) {
        setIsSidebarOpen(false);
      }
    } catch (error) {
      console.error('새 채팅 생성 실패:', error);
      setMessages([]);
      setCurrentSessionId(null); // 실패 시 세션 없이 시작
      showInfo('새 대화를 시작합니다.');
      
      if (isMobile) {
        setIsSidebarOpen(false);
      }
    }
  };

  const handleSidebarToggle = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  // 모바일에서 사이드바 외부 클릭 시 닫기
  const handleOverlayClick = () => {
    if (isMobile && isSidebarOpen) {
      setIsSidebarOpen(false);
    }
  };

  // 헤더의 모바일 사이드바 토글 이벤트 리스너
  useEffect(() => {
    const handleToggleEvent = () => {
      if (isMobile) {
        setIsSidebarOpen(!isSidebarOpen);
      }
    };

    window.addEventListener('toggleMobileSidebar', handleToggleEvent);
    return () => window.removeEventListener('toggleMobileSidebar', handleToggleEvent);
  }, [isMobile, isSidebarOpen]);

  const handleFeatureSelect = (agentType: AgentType) => {
    // WelcomeScreen에서 기능 선택 시 에이전트 설정
    setSelectedAgent(agentType);
    showInfo(`${agentType === 'web_search' ? '웹 검색' : agentType === 'deep_research' ? '심층 리서치' : agentType === 'canvas' ? 'Canvas' : '창작'} 모드를 선택했습니다.`);
  };

  const handleResize = (leftWidthPx: number) => {
    const containerWidth = getContainerWidth(containerRef, isSidebarOpen, isMobile);
    const leftWidthPercent = (leftWidthPx / containerWidth) * 100;
    const newChatWidth = Math.max(CANVAS_SPLIT.MIN_CHAT_WIDTH, Math.min(CANVAS_SPLIT.MAX_CHAT_WIDTH, leftWidthPercent));
    setChatWidth(Math.round(newChatWidth * 10) / 10);
  };

  // getContainerWidth는 useSidebarWidth 훅으로 이동됨

  const getChatWidthPx = () => {
    // useRef로 실제 채팅 영역 너비를 직접 가져오기
    if (chatAreaRef.current) {
      return chatAreaRef.current.offsetWidth;
    }
    
    // fallback: 계산된 값
    const containerWidth = getContainerWidth(containerRef, isSidebarOpen, isMobile);
    const calculatedWidth = (chatWidth / 100) * containerWidth;
    return Math.round(calculatedWidth);
  };


  return (
    <div className="flex flex-col h-full">
      {/* Toast 컨테이너 */}
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />
      
      
      {/* 모바일 오버레이 */}
      {isMobile && isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={handleOverlayClick}
        />
      )}
      
      {/* 메인 콘텐츠 - 3열 레이아웃 */}
      <div ref={containerRef} className="flex flex-1 overflow-hidden relative bg-gray-50 dark:bg-gray-900">
        {/* 사이드바 */}
        <div 
          className={`fixed top-16 left-0 bottom-0 z-30 transition-transform duration-300 ${
            isMobile 
              ? `transform ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}`
              : '' // 데스크톱에서는 transform 없이 항상 표시
          }`}
        >
          <Sidebar
            isOpen={isSidebarOpen}
            onToggle={handleSidebarToggle}
            onNewChat={handleNewChat}
            chatHistory={chatHistory}
            onSelectChat={async (conversationId) => {
              try {
                // 선택된 대화의 메시지 로드
                const conversation = await conversationHistoryService.getConversationDetail(conversationId);
                
                // 메시지를 UI 형식으로 변환
                const formattedMessages: Message[] = conversation.messages.map(msg => ({
                  id: msg.id,
                  content: msg.content,
                  isUser: msg.role === 'USER',
                  timestamp: msg.created_at,
                  model: msg.model,
                  agentType: conversation.agent_type,
                  citations: [],
                  sources: []
                }));
                
                setMessages(formattedMessages);
                setCurrentSessionId(conversationId);
                
                // 모델과 에이전트 타입도 동기화
                if (conversation.model) {
                  // 모델 문자열에서 provider와 model 파싱
                  const modelKey = conversation.model as LLMModel;
                  if (MODEL_MAP[modelKey]) {
                    const provider = modelKey.startsWith('claude') ? 'claude' : 'gemini';
                    setSelectedProvider(provider as LLMProvider);
                    setSelectedModel(modelKey);
                  }
                }
                
                if (conversation.agent_type) {
                  setSelectedAgent(conversation.agent_type as AgentType);
                }
                
                // 모바일에서 채팅 선택 시 사이드바 닫기
                if (isMobile) {
                  setIsSidebarOpen(false);
                }
                
                showSuccess('대화를 불러왔습니다.');
              } catch (error) {
                console.error('대화 로딩 실패:', error);
                showError('대화를 불러올 수 없습니다.');
              }
            }}
            onDeleteChat={(conversationId) => {
              if (deleteConversationMutation.isPending) {
                showInfo('이미 삭제 중입니다. 잠시만 기다려주세요.');
                return;
              }
              deleteConversationMutation.mutate(conversationId);
            }}
            onUpdateChat={async (conversationId, updates) => {
              try {
                await conversationHistoryService.updateConversation(conversationId, updates);
                queryClient.invalidateQueries({ queryKey: ['conversations'] });
                await refetchHistory();
                showSuccess('대화 제목이 수정되었습니다.');
              } catch (error) {
                console.error('대화 제목 수정 실패:', error);
                showError('대화 제목 수정에 실패했습니다.');
              }
            }}
            isMobile={isMobile}
          />
        </div>
        
        {selectedAgent === 'canvas' && !isMobile ? (
          <>
            {/* 리사이저블 채팅 영역 - 데스크톱만 */}
            <div 
              ref={chatAreaRef}
              data-chat-area
              className="flex flex-col bg-white dark:bg-slate-800"
              style={{ 
                width: `${chatWidth}%`,
                paddingLeft: `${getMainContentMargin(isSidebarOpen, isMobile)}px`
              }}
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
              
              {/* 검색 진행 상태 표시 (상단) */}
              {(searchProgress?.isSearching || searchSteps.length > 0) && (
                <div className="px-6 py-4 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                  <SearchProgressIndicator 
                    steps={searchSteps}
                    isVisible={true}
                    compact={true}
                  />
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
                          messageId={msg.id}
                          conversationId={currentSessionId}
                          citations={msg.citations}
                          sources={msg.sources}
                          searchResults={msg.searchResults}
                          searchQuery={msg.searchQuery}
                          citationMode={msg.agentType === 'web_search' ? 'none' : 'preview'}
                        />
                      ))}
                      
                      {/* 검색 진행 상태 또는 타이핑 인디케이터 */}
                      {(searchProgress || searchSteps.length > 0) && (
                        <ChatMessage
                          message=""
                          isUser={false}
                          searchStatus={searchProgress}
                          searchSteps={searchSteps}
                          model={selectedModel}
                        />
                      )}
                      
                      {!searchProgress && searchSteps.length === 0 && isTyping && (
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
              minLeftWidth={Math.min(300, getContainerWidth(containerRef, isSidebarOpen, isMobile) * 0.3)} // 컨테이너 30% 최소
              maxLeftWidth={Math.max(800, getContainerWidth(containerRef, isSidebarOpen, isMobile) * 0.8)} // 컨테이너 80% 최대
              containerWidth={getContainerWidth(containerRef, isSidebarOpen, isMobile)}
            />
            
            {/* Canvas 영역 */}
            <div 
              className="flex flex-col bg-gray-100 dark:bg-gray-800 min-w-0 border-l border-gray-200 dark:border-gray-700"
              style={{ width: `${100 - chatWidth}%` }}
            >
              <CanvasWorkspace />
            </div>
          </>
        ) : (
          /* Canvas가 비활성화되거나 모바일인 경우 풀스크린 채팅 */
          <div 
            className={`flex-1 flex flex-col bg-white dark:bg-slate-800 ${
              isMobile && isSidebarOpen ? 'opacity-50 pointer-events-none' : ''
            }`}
            style={{
              paddingLeft: `${getMainContentMargin(isSidebarOpen, isMobile)}px`
            }}
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
                        messageId={msg.id}
                        conversationId={currentSessionId}
                        citations={msg.citations}
                        sources={msg.sources}
                        searchResults={msg.searchResults}
                        searchQuery={msg.searchQuery}
                        citationMode={msg.agentType === 'web_search' ? 'none' : 'preview'}
                      />
                    ))}
                    
                    {/* 검색 진행 상태 또는 타이핑 인디케이터 */}
                    {(searchProgress || searchSteps.length > 0) && (
                      <ChatMessage
                        message=""
                        isUser={false}
                        searchStatus={searchProgress}
                        searchSteps={searchSteps}
                        model={selectedModel}
                      />
                    )}
                    
                    {!searchProgress && searchSteps.length === 0 && isTyping && (
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