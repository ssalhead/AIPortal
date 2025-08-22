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
import { AgentSuggestionModal } from '../components/ui/AgentSuggestionModal';
import { Resizer } from '../components/ui/Resizer';
import { useLoading } from '../contexts/LoadingContext';
import { useResponsive, useTouchDevice } from '../hooks/useResponsive';
import { useSidebarWidth } from '../hooks/useSidebarWidth';
import { apiService } from '../services/api';
import { conversationHistoryService } from '../services/conversationHistoryService';
import { agentSuggestionService } from '../services/agentSuggestionService';
import { Star, Zap } from 'lucide-react';
import type { LLMModel, AgentType, Citation, Source, LLMProvider, ChatResponse, Message, StreamingProgressMetadata, CanvasData } from '../types';
import { MODEL_MAP, AGENT_TYPE_MAP } from '../types';
import { CANVAS_SPLIT } from '../constants/layout';
import type { SearchResult } from '../components/search/SearchResultsCard';
import { CanvasWorkspace } from '../components/canvas/CanvasWorkspace';
import { useCanvasStore } from '../stores/canvasStore';
import { useImageSessionStore } from '../stores/imageSessionStore';


export const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<LLMProvider>('claude');
  const [selectedModel, setSelectedModel] = useState<LLMModel>('claude-4');
  const [selectedAgent, setSelectedAgent] = useState<AgentType>('none');
  
  // 반응형 hooks
  const { isMobile } = useResponsive();
  const { getMainContentMargin, getContainerWidth } = useSidebarWidth();
  
  // 반응형 사이드바 상태
  const [isSidebarOpen, setIsSidebarOpen] = useState(!isMobile); // 모바일에서는 기본적으로 닫힘
  const [chatWidth, setChatWidth] = useState<number>(CANVAS_SPLIT.DEFAULT_CHAT_WIDTH); // 채팅 영역 비율 (%) - 7:3 비율
  const [currentProgressMessage, setCurrentProgressMessage] = useState<string>('');
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  
  // 청크 스트리밍 상태
  const [streamingMessage, setStreamingMessage] = useState<string>('');
  const [isStreamingResponse, setIsStreamingResponse] = useState<boolean>(false);
  
  // 에이전트 제안 관련 상태
  const [agentSuggestion, setAgentSuggestion] = useState<{
    suggested_agent: AgentType;
    reason: string;
    confidence: number;
    current_agent: AgentType;
    pendingMessage?: string;
  } | null>(null);
  const [isShowingSuggestion, setIsShowingSuggestion] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chatAreaRef = useRef<HTMLDivElement>(null);
  const { isTyping, startTyping, stopTyping, currentModel } = useLoading();
  const queryClient = useQueryClient();
  const { clearCanvas, autoActivateCanvas, hasActiveContent, isCanvasOpen, closeCanvas, shouldActivateForConversation, updateCanvasWithCompletedImage, activateSessionCanvas, syncWithImageSession, loadCanvasForConversation, clearCanvasForNewConversation } = useCanvasStore();
  
  // 진화형 이미지 세션 Store
  const {
    getSession: getImageSession,
    hasSession: hasImageSession,
    createSession: createImageSession,
    addVersion: addImageVersion,
    extractTheme,
    evolvePrompt,
  } = useImageSessionStore();

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
      queryClient.setQueryData(['conversations'], (old: unknown) => {
        if (!Array.isArray(old)) return [];
        return old.filter((conv: unknown) => 
          typeof conv === 'object' && 
          conv !== null && 
          'id' in conv && 
          conv.id !== deletedConversationId
        );
      });
      
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
      // 선택되지 않은 대화가 삭제된 경우 WelcomeScreen 유지
      // 사용자가 명시적으로 대화를 선택할 때까지 빈 상태 유지
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
      // Canvas Store 대화별 상태 관리 시작
      loadCanvasForConversation(conversationId);
      
      // 현재 Canvas 상태 확인 (스마트 상태 관리를 위해)
      const hadActiveCanvas = hasActiveContent();
      
      const conversation = await conversationHistoryService.getConversationDetail(conversationId);
      
      // API 응답 전체 디버깅
      console.log('🔍 API 응답 전체:', conversation);
      console.log('🔍 메시지 배열:', conversation?.messages);
      if (conversation?.messages?.length > 0) {
        console.log('🔍 첫 번째 메시지 샘플:', conversation.messages[0]);
        console.log('🔍 첫 번째 메시지 키들:', Object.keys(conversation.messages[0]));
      }
      
      // 메시지를 UI 형식으로 변환
      const formattedMessages: Message[] = conversation.messages.map((msg: unknown, index: number) => {
        // 타입 가드로 안전한 접근
        if (typeof msg !== 'object' || msg === null) return null;
        const message = msg as Record<string, unknown>;
        
        // Canvas 데이터 로딩 디버깅 (상세) - 강화
        console.log(`🔍 메시지 처리 중 - ID: ${message.id}, Role: ${message.role}, Index: ${index}`);
        console.log(`🔍 메시지 객체 타입: ${typeof message}, 객체인가: ${typeof message === 'object'}`);
        console.log(`🔍 메시지 키들:`, Object.keys(message));
        
        const canvasData = message.canvas_data;
        console.log(`🔍 canvas_data 접근 결과:`, canvasData);
        console.log(`🔍 canvas_data 타입:`, typeof canvasData);
        
        if (canvasData) {
          console.log(`🎨 Canvas 데이터 로딩 성공 - 메시지 ID: ${message.id}, 타입: ${(canvasData as any)?.type}`, canvasData);
          console.log(`✅ Canvas 데이터가 Message 객체의 canvasData 필드로 전달됩니다.`);
        } else if (message.role === 'ASSISTANT') {
          console.log(`❌ Canvas 데이터 없음 - 메시지 ID: ${message.id}, 사용 가능한 키:`, Object.keys(message));
          
          // 직접 키 확인
          if ('canvas_data' in message) {
            console.log(`🔍 'canvas_data' 키는 존재함, 값:`, message.canvas_data);
          } else {
            console.log(`🔍 'canvas_data' 키가 존재하지 않음`);
          }
          
          // metadata에서 canvas_data가 있는지 확인
          const metadata = message.metadata_;
          if (metadata && typeof metadata === 'object') {
            const metadataKeys = Object.keys(metadata);
            console.log(`🔍 metadata에서 찾은 키:`, metadataKeys);
            if ('canvas_data' in metadata) {
              console.log(`🎨 metadata에서 canvas_data 발견:`, (metadata as any).canvas_data);
            }
          }
        }
        
        return {
          id: (typeof message.id === 'string' ? message.id : `msg-${index}`),
          content: (typeof message.content === 'string' ? message.content : ''),
          isUser: message.role === 'USER',
          timestamp: (typeof message.created_at === 'string' ? message.created_at : new Date().toISOString()),
          model: (typeof message.model === 'string' ? message.model : undefined),
          agentType: (typeof conversation.agent_type === 'string' ? conversation.agent_type : undefined),
          citations: [],
          sources: [],
          canvasData: message.canvas_data || undefined  // Canvas 데이터 포함
        };
      }).filter((msg): msg is Message => msg !== null);
      
      setMessages(formattedMessages);
      setCurrentSessionId(conversationId);
      
      // 🎨 스마트 Canvas 상태 관리
      const shouldActivateCanvas = shouldActivateForConversation(formattedMessages);
      
      console.log('🎨 Canvas 상태 결정:', {
        hadActiveCanvas,
        shouldActivateCanvas,
        messagesWithCanvas: formattedMessages.filter(msg => msg.canvasData).length,
        action: shouldActivateCanvas ? 'activate' : (hadActiveCanvas ? 'close' : 'keep_current')
      });
      
      // 🎨 진화형 이미지 세션 시스템과 통합된 Canvas 관리
      if (shouldActivateCanvas) {
        // 1. Canvas 데이터가 있는 경우 - 진화형 세션 확인 및 활성화
        const lastCanvasMessage = formattedMessages
          .filter(msg => msg.canvasData)
          .pop(); // 가장 마지막 Canvas 메시지
          
        if (lastCanvasMessage?.canvasData) {
          console.log('🎨 Canvas 자동 활성화 - 데이터:', lastCanvasMessage.canvasData);
          
          // 진화형 이미지 세션이 있는지 확인
          if (hasImageSession(conversationId) && lastCanvasMessage.canvasData.type === 'image') {
            console.log('🚀 진화형 이미지 세션 활성화:', conversationId);
            
            // 세션 기반 Canvas 활성화
            const itemId = activateSessionCanvas(conversationId);
            if (itemId) {
              console.log('✅ 진화형 Canvas 활성화 완료:', itemId);
            } else {
              // 세션이 있지만 활성화 실패 시 기본 방식 사용
              console.warn('⚠️ 진화형 Canvas 활성화 실패, 기본 방식 사용');
              autoActivateCanvas(lastCanvasMessage.canvasData, conversationId);
            }
          } else {
            // 일반 Canvas 활성화 (conversationId 포함)
            autoActivateCanvas(lastCanvasMessage.canvasData, conversationId);
          }
        }
      } else if (hadActiveCanvas) {
        // Canvas 데이터가 없고 이전에 활성화되어 있었으면 닫기
        console.log('🎨 Canvas 자동 비활성화 - 데이터 없음');
        closeCanvas();
      }
      // 둘 다 아니면 현재 상태 유지
      
      // 모델과 에이전트 타입도 동기화
      if (conversation.model) {
        const modelKey = conversation.model as LLMModel;
        const provider = modelKey.startsWith('claude') ? 'claude' : 'gemini';
        const providerModels = MODEL_MAP[provider as LLMProvider];
        const modelExists = providerModels?.some(m => m.id === modelKey);
        if (modelExists) {
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
;
      
      // 세션 ID 업데이트 (새 세션인 경우)
      const sessionIdToUse = response.session_id || currentSessionId;
      if (response.session_id && response.session_id !== currentSessionId) {
        setCurrentSessionId(response.session_id);
        console.log('🆕 세션 ID 업데이트:', { 이전: currentSessionId, 새세션: response.session_id });
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
        searchResults = response.citations.map((citation: unknown, index: number) => {
          if (typeof citation !== 'object' || citation === null) return null;
          const cite = citation as Record<string, unknown>;
          
          return {
            id: (typeof cite.id === 'string' ? cite.id : `search_${index + 1}`),
            title: (typeof cite.title === 'string' ? cite.title : '제목 없음'),
            url: (typeof cite.url === 'string' ? cite.url : ''),
            snippet: (typeof cite.snippet === 'string' ? cite.snippet : ''),
            domain: (typeof cite.source === 'string' ? cite.source : 'unknown'),
            relevanceScore: (typeof cite.score === 'number' ? cite.score : 0.8),
            publishedDate: response.timestamp
          };
        }).filter((result): result is SearchResult => result !== null);
        
        // 디버그용 로그 추가
        console.log('웹 검색 결과:', {
          agent_used: response.agent_used,
          citations_count: response.citations?.length || 0,
          searchResults_count: searchResults.length,
          searchQuery,
          sample_citation: response.citations?.[0]
        });
      }

      // AI 응답 먼저 추가 (사용자 메시지는 이미 표시됨)
      const aiResponse: Message = {
        id: `ai-${Date.now()}`,
        content: response.response,
        isUser: false,
        timestamp: response.timestamp,
        model: response.model_used,
        agentType: response.agent_used,
        citations: response.citations || [],
        sources: response.sources || [],
        searchResults: searchResults,
        searchQuery: searchQuery,
        canvasData: response.canvas_data // Canvas 데이터 추가
      };
      
      console.log('🔍 일반채팅 - AI 응답 추가:', aiResponse);
      setMessages(prev => [...prev, aiResponse]);
      console.log('🔍 일반채팅 - AI 응답 추가 완료');

      // 🎨 AI 응답 출력 후 Canvas 데이터 처리 및 자동 활성화
      console.log('🔍 응답 전체 확인:', response);
      console.log('🔍 canvas_data 여부:', !!response.canvas_data);
      
      if (response.canvas_data) {
        console.log('🎨 Canvas 데이터 감지 - AI 응답 후 활성화:', response.canvas_data);
        
        // 🎨 이미지 완성 상태 확인
        const isImageComplete = response.canvas_data.type === 'image' && 
                               response.canvas_data.image_data && 
                               (response.canvas_data.image_data.images?.length > 0 || 
                                response.canvas_data.image_data.image_urls?.length > 0);
        
        // 🎨 진화형 이미지 세션 시스템과 통합된 Canvas 자동 활성화
        setTimeout(() => {
          // 1. 진화형 이미지 세션 처리 (이미지 타입이고 currentSessionId가 있는 경우)
          if (response.canvas_data.type === 'image' && sessionIdToUse) {
            console.log('🚀 진화형 이미지 시스템 처리:', {
              type: response.canvas_data.type,
              sessionId: sessionIdToUse,
              hasSession: hasImageSession(sessionIdToUse),
              isImageComplete,
            });
            
            if (!hasImageSession(sessionIdToUse)) {
              // 새로운 이미지 생성 세션 생성
              const theme = extractTheme(response.canvas_data.title || '이미지');
              const initialPrompt = response.canvas_data.image_data?.prompt || response.canvas_data.title || '이미지 생성';
              const newSession = createImageSession(sessionIdToUse, theme, initialPrompt);
              console.log('🎨 새 이미지 세션 생성:', newSession);
            }
            
            // 버전 추가는 ImageGenerator 컴포넌트에서 자동 처리됨 (중복 방지)
            // if (isImageComplete) {
            //   console.log('🎨 이미진 완성됨 - 세션에 버전 추가');
            //   const imageData = response.canvas_data.image_data;
            //   
            //   // 이미지 URL 추출
            //   let imageUrl = '';
            //   if (imageData.image_urls && imageData.image_urls.length > 0) {
            //     imageUrl = imageData.image_urls[0];
            //   } else if (imageData.images && imageData.images.length > 0) {
            //     const firstImage = imageData.images[0];
            //     imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url || '';
            //   }
            //   
            //   if (imageUrl) {
            //     const versionId = addImageVersion(currentSessionId, {
            //       prompt: imageData.prompt || response.canvas_data.title || '이미진 생성',
            //       negativePrompt: imageData.negativePrompt || '',
            //       style: imageData.style || 'default',
            //       size: imageData.size || '1K_1:1',
            //       imageUrl: imageUrl,
            //       status: 'completed',
            //       isSelected: false,
            //     });
            //     console.log('🎨 이미진 버전 추가 완료:', versionId);
            //   }
            // }
            
            // 세션 기반 Canvas 활성화 또는 업데이트
            if (isImageComplete && isCanvasOpen && hasActiveContent()) {
              // Canvas가 이미 열려있고 이미지가 완성된 경우 → 업데이트
              console.log('🎨 Canvas 이미지 업데이트 모드 (진화형)');
              const updatedItemId = updateCanvasWithCompletedImage(response.canvas_data);
              console.log('🎨 Canvas 이미지 업데이트 완료, Item ID:', updatedItemId);
              
              // 세션과 Canvas 동기화
              syncWithImageSession(sessionIdToUse);
            } else {
              // Canvas가 없거나 새로운 작업인 경우 → 세션 기반 활성화
              console.log('🎨 Canvas 신규 활성화 모드 (진화형)');
              const itemId = activateSessionCanvas(sessionIdToUse);
              if (itemId) {
                console.log('✅ 진화형 Canvas 활성화 완료, Item ID:', itemId);
              } else {
                // 세션 활성화 실패 시 기본 방식 사용
                console.warn('⚠️ 진화형 Canvas 활성화 실패, 기본 방식 사용');
                const artifactId = autoActivateCanvas(response.canvas_data, sessionIdToUse);
                console.log('🎨 Canvas 자동 활성화 완료 (기본 방식), Artifact ID:', artifactId);
              }
            }
          } else {
            // 2. 기본 Canvas 활성화 (일반 Canvas 또는 텍스트/마인드맵)
            if (isImageComplete && isCanvasOpen && hasActiveContent()) {
              // Canvas가 이미 열려있고 이미지가 완성된 경우 → 업데이트
              console.log('🎨 Canvas 이미지 업데이트 모드');
              const updatedItemId = updateCanvasWithCompletedImage(response.canvas_data);
              console.log('🎨 Canvas 이미지 업데이트 완료, Item ID:', updatedItemId);
            } else {
              // Canvas가 없거나 새로운 작업인 경우 → 새로 활성화
              console.log('🎨 Canvas 신규 활성화 모드');
              const artifactId = autoActivateCanvas(response.canvas_data, sessionIdToUse);
              console.log('🎨 Canvas 자동 활성화 완료, Artifact ID:', artifactId);
            }
          }
        }, 500); // 0.5초 딜레이
      } else {
        console.log('🔍 canvas_data가 없습니다');
      }
      // 성공 토스트는 제거 - 메시지가 화면에 나타나는 것으로 충분
    },
    onError: (error: Error) => {
      // 타이핑 상태 종료
      stopTyping();
;
      
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

  // 자동 메시지 로딩 로직 제거 - 사용자가 명시적으로 대화를 선택했을 때만 로드
  // 새로고침 시 항상 WelcomeScreen에서 시작하도록 변경

  // 새 메시지가 추가되면 스크롤을 맨 아래로
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 진행 상태 메시지 매핑
  const getProgressMessage = (stepId?: string, metadata?: StreamingProgressMetadata): string => {
    switch (stepId) {
      case 'query_analysis':
        return '🔍 검색어를 분석하는 중...';
      case 'query_generation':
        return '🔍 최적 검색어를 생성하는 중...';
      case 'parallel_search':
        // 맥락 통합 검색어가 있으면 표시
        if (metadata?.has_context && metadata?.context_integrated_query) {
          return `🔍 "${metadata.context_integrated_query}" 검색 중...`;
        }
        return '🔍 웹에서 정보를 찾는 중...';
      case 'result_filtering':
        return '🔍 검색 결과를 정리하는 중...';
      case 'result_ranking':
        return '🔍 결과를 분석하는 중...';
      case 'response_generation':
        return '🤖 AI 답변을 생성하는 중...';
      default:
        return '🔍 검색 중...';
    }
  };

  // 에이전트 제안 분석
  const analyzeAgentSuggestion = async (message: string, currentAgent: AgentType, model: LLMModel) => {
    try {
      // 🎨 이미지 생성 요청 자동 감지
      const imageKeywords = [
        '그려', '그림', '이미지', '사진', '일러스트', '만들어', '생성', '디자인', 
        '캐릭터', '로고', '포스터', '배경', '풍경', 'AI 이미지', '시각화'
      ];
      
      const hasImageRequest = imageKeywords.some(keyword => message.includes(keyword));
      
      if (hasImageRequest && currentAgent === 'none') {
        // 이미지 생성 요청 감지 시 Canvas를 바로 활성화 (제안 모달 없이)
        console.log('🎨 이미지 생성 키워드 감지 - Canvas 모드로 자동 전환:', message);
        
        // Canvas 강제 활성화 
        setSelectedAgent('canvas');
        
        await processSendMessage(message, model, 'canvas');
        return true; // 자동 처리됨을 반환
      }

      const suggestion = await agentSuggestionService.analyzeSuggestionWithTypes(
        message,
        currentAgent,
        model
      );

      if (suggestion.needs_switch && suggestion.suggested_agent && suggestion.confidence && suggestion.reason) {
        setAgentSuggestion({
          suggested_agent: suggestion.suggested_agent as AgentType,
          reason: suggestion.reason,
          confidence: suggestion.confidence,
          current_agent: currentAgent,
          pendingMessage: message
        });
        setIsShowingSuggestion(true);
        return true; // 제안이 있음을 반환
      }
      
      return false; // 제안이 없음
    } catch (error) {
      console.error('에이전트 제안 분석 실패:', error);
      return false;
    }
  };

  // 에이전트 제안 수락
  const handleAcceptSuggestion = () => {
    if (agentSuggestion) {
      setSelectedAgent(agentSuggestion.suggested_agent);
      setIsShowingSuggestion(false);
      
      // 에이전트 전환 알림 및 즉시 메시지 전송
      if (agentSuggestion.pendingMessage) {
        // 에이전트 전환 알림
        showInfo(`${AGENT_TYPE_MAP[agentSuggestion.suggested_agent].name}로 전환하여 처리합니다.`);
        
        // 메시지 전송 (서버 응답에서 사용자 메시지 + AI 응답 모두 처리)
        processSendMessage(agentSuggestion.pendingMessage, selectedModel, agentSuggestion.suggested_agent);
      }
      
      setAgentSuggestion(null);
    }
  };

  // 에이전트 제안 거절
  const handleDeclineSuggestion = () => {
    if (agentSuggestion) {
      setIsShowingSuggestion(false);
      
      // 현재 에이전트로 메시지 전송
      if (agentSuggestion.pendingMessage) {
        processSendMessage(agentSuggestion.pendingMessage, selectedModel, agentSuggestion.current_agent);
      }
      
      setAgentSuggestion(null);
    }
  };

  // 실제 메시지 전송 처리 (에이전트 제안 체크 후 실행)
  const handleSendMessage = async (message: string, model: LLMModel, agentType: AgentType) => {
    // 에이전트 제안 분석 (일반 채팅에서만 - 이미 특정 에이전트가 선택된 경우는 제외)
    if (agentType === 'none') {
      const hasSuggestion = await analyzeAgentSuggestion(message, agentType, model);
      if (hasSuggestion) {
        return; // 제안 모달이 표시되므로 여기서 중단
      }
    }

    // 제안이 없거나 이미 특정 에이전트가 선택된 경우 바로 전송
    await processSendMessage(message, model, agentType);
  };

  // 실제 메시지 전송 로직 (기존 handleSendMessage 내용)
  const processSendMessage = async (message: string, model: LLMModel, agentType: AgentType) => {
    console.log(`📤 메시지 전송 - 에이전트: ${agentType}, 모델: ${model}, 메시지: ${message.slice(0, 50)}...`);
    // 🔥 사용자 메시지 즉시 표시 (기존 UX 복원)
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      content: message,
      isUser: true,
      timestamp: new Date().toISOString(),
      model: model,
      agentType: undefined,
      citations: [],
      sources: []
    };
    setMessages(prev => [...prev, userMessage]);

    // 모든 에이전트에서 스트리밍 사용
    {
      // 에이전트 타입에 따른 초기 메시지 설정
      let initialMessage = `${model} 모델로 응답 생성 중...`;
      if (agentType === 'web_search') {
        initialMessage = `${model} 모델로 웹 검색 중...`;
      } else if (agentType === 'deep_research') {
        initialMessage = `${model} 모델로 심층 리서치 중...`;
      } else if (agentType === 'canvas') {
        initialMessage = `${model} 모델로 Canvas 작업 중...`;
      }
      
      // 타이핑 시작
      startTyping(initialMessage, model);
      
      // 사용자 메시지는 이미 표시됨, AI 응답만 추가 예정


      // 간단한 진행 메시지만 관리
      setCurrentProgressMessage(getProgressMessage('query_analysis'));

      try {
        // 스트리밍 방식으로 실제 진행 상태를 받아서 처리
        let finalResponse: ChatResponse | null = null;
        let streamingError: string | null = null;
        
        try {
          // 스트리밍 API를 Promise로 감싸서 완료 대기
          await new Promise<void>((resolve, reject) => {
            apiService.sendChatMessageWithProgress(
              {
                message,
                model,
                agent_type: agentType,
                session_id: currentSessionId,
                include_citations: true,
              },
              // 진행 상태 콜백 - 간단한 메시지만 업데이트
              (step: string, progress: number, metadata?: StreamingProgressMetadata) => {
                console.log('🚀 실제 진행 상태 수신:', step, progress, metadata);
                
                // 백엔드에서 제공한 step_id 사용
                const stepId = metadata?.step_id;
                
                // 진행 메시지 업데이트
                const progressMessage = getProgressMessage(stepId, metadata);
                setCurrentProgressMessage(progressMessage);
                console.log('📝 진행 메시지 업데이트:', progressMessage);
              },
              // 청크 콜백 - 실시간 스트리밍 텍스트 표시 (줄바꿈 감지 추가)
              (text: string, isFirst: boolean, isFinal: boolean) => {
                console.log('📝 청크 수신:', {
                  text: text.substring(0, 50) + (text.length > 50 ? '...' : ''),
                  길이: text.length,
                  줄바꿈포함: text.includes('\n'),
                  줄바꿈개수: (text.match(/\n/g) || []).length,
                  첫번째: isFirst,
                  마지막: isFinal
                });
                
                if (isFirst) {
                  // 첫 번째 청크에서 스트리밍 모드 시작
                  setIsStreamingResponse(true);
                  setCurrentProgressMessage(''); // 진행 메시지 숨김
                  setStreamingMessage(text);
                } else if (!isFinal) {
                  // 중간 청크들은 누적하여 표시
                  setStreamingMessage(prev => {
                    const newFullText = prev + text;
                    console.log('🔄 텍스트 누적:', {
                      이전길이: prev.length,
                      새청크길이: text.length,
                      전체길이: newFullText.length,
                      새청크줄바꿈: text.includes('\n')
                    });
                    return newFullText;
                  });
                } else {
                  // 마지막 청크 - 스트리밍 완료 준비
                  setStreamingMessage(prev => {
                    const finalText = prev + text;
                    console.log('🏁 최종 텍스트 완성:', {
                      최종길이: finalText.length,
                      총줄수: (finalText.match(/\n/g) || []).length + 1
                    });
                    return finalText;
                  });
                }
              },
              // 최종 결과 콜백
              (result: ChatResponse) => {
                console.log('✅ 최종 결과 수신:', result);
                console.log('🔍 canvas_data 확인:', !!result.canvas_data);
                
                // 🎨 스트리밍 완료 후 Canvas 데이터 처리 (딜레이 적용)
                if (result.canvas_data) {
                  console.log('🎨 스트리밍에서 Canvas 데이터 감지 - 스트리밍 완료 후 활성화:', result.canvas_data);
                  
                  // 🎨 이미지 완성 상태 확인 (스트리밍)
                  const isImageComplete = result.canvas_data.type === 'image' && 
                                         result.canvas_data.image_data && 
                                         (result.canvas_data.image_data.images?.length > 0 || 
                                          result.canvas_data.image_data.image_urls?.length > 0);
                  
                  // 🎨 진화형 이미지 세션 시스템과 통합된 스트리밍 Canvas 활성화
                  setTimeout(() => {
                    // 1. 진화형 이미지 세션 처리 (이미지 타입이고 currentSessionId가 있는 경우)
                    if (result.canvas_data.type === 'image' && sessionIdToUse) {
                      console.log('🚀 진화형 이미지 시스템 처리 (스트리밍):', {
                        type: result.canvas_data.type,
                        sessionId: sessionIdToUse,
                        hasSession: hasImageSession(sessionIdToUse),
                        isImageComplete,
                      });
                      
                      if (!hasImageSession(sessionIdToUse)) {
                        // 새로운 이미지 생성 세션 생성
                        const theme = extractTheme(result.canvas_data.title || '이미지');
                        const initialPrompt = result.canvas_data.image_data?.prompt || result.canvas_data.title || '이미지 생성';
                        const newSession = createImageSession(sessionIdToUse, theme, initialPrompt);
                        console.log('🎨 새 이미지 세션 생성 (스트리밍):', newSession);
                      }
                      
                      // 버전 추가는 ImageGenerator 컴포넌트에서 자동 처리됨 (스트리밍 중복 방지)
                      // if (isImageComplete) {
                      //   console.log('🎨 이미지 완성됨 - 세션에 버전 추가 (스트리밍)');
                      //   const imageData = result.canvas_data.image_data;
                      //   
                      //   // 이미지 URL 추출
                      //   let imageUrl = '';
                      //   if (imageData.image_urls && imageData.image_urls.length > 0) {
                      //     imageUrl = imageData.image_urls[0];
                      //   } else if (imageData.images && imageData.images.length > 0) {
                      //     const firstImage = imageData.images[0];
                      //     imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url || '';
                      //   }
                      //   
                      //   if (imageUrl) {
                      //     const versionId = addImageVersion(currentSessionId, {
                      //       prompt: imageData.prompt || result.canvas_data.title || '이미지 생성',
                      //       negativePrompt: imageData.negativePrompt || '',
                      //       style: imageData.style || 'default',
                      //       size: imageData.size || '1K_1:1',
                      //       imageUrl: imageUrl,
                      //       status: 'completed',
                      //       isSelected: false,
                      //     });
                      //     console.log('🎨 이미지 버전 추가 완료 (스트리밍):', versionId);
                      //   }
                      // }
                      
                      // 세션 기반 Canvas 활성화 또는 업데이트
                      if (isImageComplete && isCanvasOpen && hasActiveContent()) {
                        // Canvas가 이미 열려있고 이미지가 완성된 경우 → 업데이트
                        console.log('🎨 스트리밍 Canvas 이미지 업데이트 모드 (진화형)');
                        const updatedItemId = updateCanvasWithCompletedImage(result.canvas_data);
                        console.log('🎨 스트리밍 Canvas 이미지 업데이트 완료, Item ID:', updatedItemId);
                        
                        // 세션과 Canvas 동기화
                        syncWithImageSession(sessionIdToUse);
                      } else {
                        // Canvas가 없거나 새로운 작업인 경우 → 세션 기반 활성화
                        console.log('🎨 스트리밍 Canvas 신규 활성화 모드 (진화형)');
                        const itemId = activateSessionCanvas(sessionIdToUse);
                        if (itemId) {
                          console.log('✅ 진화형 Canvas 활성화 완료 (스트리밍), Item ID:', itemId);
                        } else {
                          // 세션 활성화 실패 시 기본 방식 사용
                          console.warn('⚠️ 진화형 Canvas 활성화 실패 (스트리밍), 기본 방식 사용');
                          const artifactId = autoActivateCanvas(result.canvas_data, sessionIdToUse);
                          console.log('🎨 Canvas 자동 활성화 완료 (기본 방식, 스트리밍), Artifact ID:', artifactId);
                        }
                      }
                    } else {
                      // 2. 기본 Canvas 활성화 (일반 Canvas 또는 텍스트/마인드맵)
                      if (isImageComplete && isCanvasOpen && hasActiveContent()) {
                        // Canvas가 이미 열려있고 이미지가 완성된 경우 → 업데이트
                        console.log('🎨 스트리밍 Canvas 이미지 업데이트 모드');
                        const updatedItemId = updateCanvasWithCompletedImage(result.canvas_data);
                        console.log('🎨 스트리밍 Canvas 이미지 업데이트 완료, Item ID:', updatedItemId);
                      } else {
                        // Canvas가 없거나 새로운 작업인 경우 → 새로 활성화
                        console.log('🎨 스트리밍 Canvas 신규 활성화 모드');
                        const artifactId = autoActivateCanvas(result.canvas_data, sessionIdToUse);
                        console.log('🎨 스트리밍에서 Canvas 자동 활성화 완료, Artifact ID:', artifactId);
                      }
                    }
                  }, 800); // 0.8초 딜레이 (스트리밍이 완전히 끝난 후)
                }
                
                finalResponse = result;
                resolve(); // Promise 완료 신호
              },
              // 에러 콜백  
              (error: string) => {
                console.error('❌ 스트리밍 에러:', error);
                streamingError = error;
                reject(new Error(error)); // Promise 에러 신호
              }
            );
          });
        } catch (streamError) {
          console.error('🔄 스트리밍 실패, 일반 API로 fallback:', streamError);
          
          // 스트리밍 실패 시 일반 API로 fallback
          const fallbackResponse = await apiService.sendChatMessage({
            message,
            model,
            agent_type: agentType,
            session_id: currentSessionId,
            include_citations: true,
          });
          
          finalResponse = fallbackResponse;
        }
        
        if (streamingError && !finalResponse) {
          throw new Error(`메시지 처리 중 오류가 발생했습니다: ${streamingError}`);
        }
        
        if (!finalResponse) {
          console.error('❌ finalResponse가 null입니다. streamingError:', streamingError);
          throw new Error('응답을 받지 못했습니다');
        }
        
        console.log('✅ finalResponse 확인 완료:', finalResponse);
        const response = finalResponse;

        // 검색 진행 상태 및 타이핑 인디케이터 종료
        setCurrentProgressMessage('');
        stopTyping();
        // 스트리밍 상태는 메시지 추가 후에 정리
        
        // 세션 ID 업데이트 (새 세션인 경우)
        const sessionIdToUse = response.session_id || currentSessionId;
        const isNewSession = response.session_id && response.session_id !== currentSessionId;
        if (isNewSession) {
          setCurrentSessionId(response.session_id);
          console.log('🆕 스트리밍 세션 ID 업데이트:', { 이전: currentSessionId, 새세션: response.session_id });
          
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
        
        // 백엔드 메타데이터에서 맥락 통합 검색어 확인 (모든 에이전트 타입에서 사용)
        const metadata = response.metadata || {};
        const contextIntegratedQueries = metadata.context_integrated_queries || [];
        const hasContext = metadata.has_conversation_context || false;
        
        if (response.agent_used === 'web_search' && response.citations) {
          // 맥락 통합 검색어가 있으면 사용, 없으면 원본 쿼리 사용
          if (hasContext && contextIntegratedQueries.length > 0) {
            searchQuery = contextIntegratedQueries[0]; // 첫 번째 최적 검색어 사용
            console.log('맥락 통합 검색어 사용:', searchQuery, '(원본:', message, ')');
          } else {
            searchQuery = message; // 원본 사용자 쿼리 폴백
            console.log('원본 검색어 사용:', searchQuery);
          }
          
          searchResults = response.citations.map((citation: unknown, index: number) => {
            if (typeof citation !== 'object' || citation === null) return null;
            const cite = citation as Record<string, unknown>;
            
            return {
              id: cite.id || `search_${index + 1}`,
              title: cite.title || '제목 없음',
              url: cite.url || '',
              snippet: cite.snippet || '',
              source: cite.source || 'unknown',
              score: cite.score || 0.8,
              timestamp: response.timestamp,
              provider: cite.source?.split('_')[0] || 'unknown'
            };
          }).filter((result): result is SearchResult => result !== null);
          
          console.log('웹 검색 결과 변환 완료:', {
            searchQuery,
            searchResults_count: searchResults.length,
            sample_result: searchResults[0],
            hasContext,
            contextIntegratedQueries
          });
        }

        // AI 응답만 추가 (사용자 메시지는 이미 표시됨)
        const aiResponse: Message = {
          id: `ai-${Date.now()}`,
          content: response.response,
          isUser: false,
          timestamp: response.timestamp,
          model: response.model_used,
          agentType: response.agent_used,
          citations: response.citations || [],
          sources: response.sources || [],
          searchResults: searchResults,
          searchQuery: searchQuery,
          originalQuery: hasContext ? message : undefined,
          hasContext: hasContext,
          canvasData: response.canvas_data // Canvas 데이터 추가
        };
        
        console.log('🔍 웹검색 - AI 응답 추가:', aiResponse);
        console.log('🔍 현재 메시지 상태:', messages.length, '개');
        
        setMessages(prev => {
          const newMessages = [...prev, aiResponse];
          console.log('🔍 새로운 메시지 상태:', newMessages.length, '개');
          return newMessages;
        });
        
        // 최종 메시지 추가 후 스트리밍 상태 정리
        setIsStreamingResponse(false);
        setStreamingMessage('');
        
        console.log('🔍 웹검색 - AI 응답 추가 완료');
        // 성공 토스트는 제거 - 메시지가 화면에 나타나는 것으로 충분
        
      } catch (error: unknown) {
        // 진행 상태 및 타이핑 인디케이터 종료
        setCurrentProgressMessage('');
        stopTyping();
        
        // 에러 메시지 추가
        const errorText = error instanceof Error ? error.message : '메시지 처리 중 오류가 발생했습니다.';
        const errorMessage: Message = {
          id: `error-${Date.now()}`,
          content: `죄송합니다. ${errorText}`,
          isUser: false,
          timestamp: new Date().toISOString(),
          agentType: 'error',
          model: 'system',
        };
        setMessages(prev => [...prev, errorMessage]);
        
        // 에러 시에도 스트리밍 상태 정리
        setIsStreamingResponse(false);
        setStreamingMessage('');
        
        const errorMsg = error?.response?.data?.message || '메시지 전송 중 오류가 발생했습니다.';
        showError(errorMsg);
      }
    }
  };

  const handleNewChat = async () => {
    try {
      // 새 세션 생성
      const newSession = await apiService.httpClient.post('/chat/sessions/new');
      const sessionData = newSession.data;
      
      setMessages([]);
      setCurrentSessionId(sessionData.session_id);
      
      // Canvas 새 대화를 위한 초기화
      clearCanvasForNewConversation();
      
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
      // Canvas 닫기 (실패 시에도)
      closeCanvas();
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
                console.log('🔄 대화 선택:', conversationId);
                console.log('🔄 기존 currentSessionId:', currentSessionId);
                console.log('🔄 기존 메시지 수:', messages.length);
                
                // Canvas Store 대화별 상태 관리 시작
                loadCanvasForConversation(conversationId);
                
                // 현재 Canvas 상태 확인 (스마트 상태 관리를 위해)
                const hadActiveCanvas = hasActiveContent();
                
                // 선택된 대화의 메시지 로드
                const conversation = await conversationHistoryService.getConversationDetail(conversationId);
                console.log('🔄 로드된 대화 데이터:', conversation);
                
                // 메시지를 UI 형식으로 변환 (Canvas 데이터 포함)
                const formattedMessages: Message[] = conversation.messages.map((msg: any) => {
                  // Canvas 데이터 변환 (히스토리 로딩)
                  const canvasData = msg.canvas_data;
                  if (canvasData) {
                    console.log(`🎨 히스토리 로딩 - Canvas 데이터 발견: 메시지 ID ${msg.id}, 타입: ${canvasData.type}`, canvasData);
                  }
                  
                  return {
                    id: msg.id,
                    content: msg.content,
                    isUser: msg.role === 'USER',
                    timestamp: msg.created_at,
                    model: msg.model,
                    agentType: conversation.agent_type,
                    citations: [],
                    sources: [],
                    canvasData: msg.canvas_data || undefined  // Canvas 데이터 포함
                  };
                });
                
                console.log('🔄 변환된 메시지들:', formattedMessages);
                setMessages(formattedMessages);
                setCurrentSessionId(conversationId);
                console.log('🔄 대화 로딩 완료 - 새 sessionId:', conversationId);
                
                // 🎨 스마트 Canvas 상태 관리 (히스토리 클릭)
                const shouldActivateCanvas = shouldActivateForConversation(formattedMessages);
                
                console.log('🎨 Canvas 상태 결정 (히스토리):', {
                  hadActiveCanvas,
                  shouldActivateCanvas,
                  messagesWithCanvas: formattedMessages.filter(msg => msg.canvasData).length,
                  action: shouldActivateCanvas ? 'activate' : (hadActiveCanvas ? 'close' : 'keep_current')
                });
                
                // 🎨 진화형 이미지 세션 시스템과 통합된 Canvas 관리 (히스토리 클릭)
                if (shouldActivateCanvas) {
                  // Canvas 데이터가 있는 경우 - 진화형 세션 확인 및 활성화
                  const lastCanvasMessage = formattedMessages
                    .filter(msg => msg.canvasData)
                    .pop(); // 가장 마지막 Canvas 메시지
                    
                  if (lastCanvasMessage?.canvasData) {
                    console.log('🎨 Canvas 자동 활성화 (히스토리) - 데이터:', lastCanvasMessage.canvasData);
                    
                    // 진화형 이미지 세션이 있는지 확인
                    if (hasImageSession(conversationId) && lastCanvasMessage.canvasData.type === 'image') {
                      console.log('🚀 진화형 이미지 세션 활성화 (히스토리):', conversationId);
                      
                      // 세션 기반 Canvas 활성화
                      const itemId = activateSessionCanvas(conversationId);
                      if (itemId) {
                        console.log('✅ 진화형 Canvas 활성화 완료 (히스토리):', itemId);
                      } else {
                        // 세션이 있지만 활성화 실패 시 기본 방식 사용
                        console.warn('⚠️ 진화형 Canvas 활성화 실패 (히스토리), 기본 방식 사용');
                        autoActivateCanvas(lastCanvasMessage.canvasData, conversationId);
                      }
                    } else {
                      // 일반 Canvas 활성화 (conversationId 포함)
                      autoActivateCanvas(lastCanvasMessage.canvasData, conversationId);
                    }
                  }
                } else if (hadActiveCanvas) {
                  // Canvas 데이터가 없고 이전에 활성화되어 있었으면 닫기
                  console.log('🎨 Canvas 자동 비활성화 (히스토리) - 데이터 없음');
                  closeCanvas();
                }
                // 둘 다 아니면 현재 상태 유지
                
                // 모델과 에이전트 타입도 동기화
                if (conversation.model) {
                  // 모델 문자열에서 provider와 model 파싱
                  const modelKey = conversation.model as LLMModel;
                  const provider = modelKey.startsWith('claude') ? 'claude' : 'gemini';
                  const providerModels = MODEL_MAP[provider as LLMProvider];
                  const modelExists = providerModels?.some(m => m.id === modelKey);
                  if (modelExists) {
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
        
        {hasActiveContent() && !isMobile ? (
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
              
              
              {/* 채팅 메시지 영역 */}
              <div className="flex-1 overflow-y-auto">
                <div className="h-full">
                  {messages.length === 0 ? (
                    <WelcomeScreen onFeatureSelect={handleFeatureSelect} />
                  ) : (
                    <div className="px-6 py-6 space-y-6 max-w-4xl mx-auto">
                      {messages.map((msg) => (
                        <ChatMessage
                          key={msg.id}
                          message={msg.content}
                          isUser={msg.isUser}
                          timestamp={msg.timestamp}
                          agentType={msg.agentType}
                          model={msg.model}
                          messageId={msg.id}
                          conversationId={currentSessionId || undefined}
                          citations={msg.citations}
                          sources={msg.sources}
                          searchResults={msg.searchResults}
                          searchQuery={msg.searchQuery}
                          originalQuery={msg.originalQuery}
                          hasContext={msg.hasContext}
                          citationMode={msg.agentType === 'web_search' ? 'none' : 'preview'}
                          canvasData={msg.canvasData}
                        />
                      ))}
                      
                      {/* 타이핑 인디케이터 - 진행 메시지 포함 */}
                      {(currentProgressMessage || isTyping) && (
                        <ChatMessage
                          message=""
                          isUser={false}
                          isTyping={true}
                          model={currentModel}
                          customTypingMessage={currentProgressMessage || `${currentModel} 모델로 응답 생성 중...`}
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
              <CanvasWorkspace conversationId={currentSessionId} />
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
                    {messages.map((msg) => (
                      <ChatMessage
                        key={msg.id}
                        message={msg.content}
                        isUser={msg.isUser}
                        timestamp={msg.timestamp}
                        agentType={msg.agentType}
                        model={msg.model}
                        messageId={msg.id}
                        conversationId={currentSessionId || undefined}
                        citations={msg.citations}
                        sources={msg.sources}
                        searchResults={msg.searchResults}
                        searchQuery={msg.searchQuery}
                        citationMode={msg.agentType === 'web_search' ? 'none' : 'preview'}
                        canvasData={msg.canvasData}
                      />
                    ))}
                    
                    {/* 타이핑 인디케이터 또는 스트리밍 메시지 */}
                    {isStreamingResponse ? (
                      <ChatMessage
                        message={streamingMessage}
                        isUser={false}
                        isTyping={false}
                        model={currentModel}
                        agentType={selectedAgent}
                        streamingChunk={streamingMessage}
                        isStreamingMode={true}
                      />
                    ) : (currentProgressMessage || isTyping) ? (
                      <ChatMessage
                        message=""
                        isUser={false}
                        isTyping={true}
                        model={currentModel}
                        customTypingMessage={currentProgressMessage || `${currentModel} 모델로 응답 생성 중...`}
                      />
                    ) : null}
                    
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

      {/* 에이전트 제안 모달 */}
      {agentSuggestion && (
        <AgentSuggestionModal
          suggestion={agentSuggestion}
          onAccept={handleAcceptSuggestion}
          onDecline={handleDeclineSuggestion}
          isVisible={isShowingSuggestion}
        />
      )}

      {/* 모바일 Canvas 모달 */}
      {hasActiveContent() && isMobile && isCanvasOpen && (
        <div className="fixed inset-0 z-50 bg-white dark:bg-slate-900">
          <CanvasWorkspace conversationId={currentSessionId} />
        </div>
      )}

      {/* 토스트 컨테이너 */}
      <ToastContainer toasts={toasts} onRemoveToast={removeToast} />
    </div>
  );
};