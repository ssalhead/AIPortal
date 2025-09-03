/**
 * 채팅 메시지 컴포넌트 - Gemini 스타일
 */

import React, { useState, useEffect, useRef } from 'react';
import { TypingIndicator } from '../ui/TypingIndicator';
import { Citation, CitationPreview } from '../citation/Citation';
import { SourceList } from '../citation/SourceList';
import { SearchResultsCard } from '../search/SearchResultsCard';
import { SearchProgressIndicator, type SearchStep } from '../SearchProcess/SearchProgressIndicator';
import type { SearchResult } from '../search/SearchResultsCard';
import { Copy, ThumbsUp, ThumbsDown, RotateCcw, User, Bot, Star, Zap, Search, Loader2 } from '../ui/Icons';
import { ProgressiveMarkdown, type ProgressiveMarkdownRef } from '../ui/ProgressiveMarkdown';
import type { Citation as CitationData, Source as SourceData, CanvasData } from '../../types';
import { feedbackService } from '../../services/feedbackService';
import { useResponsive } from '../../hooks/useResponsive';
import type { MessageFeedback } from '../../types/feedback';
import { loggers } from '../../utils/logger';
import { useCanvasStore } from '../../stores/canvasStore';
import { useImageSessionStore } from '../../stores/imageSessionStore';
import { ConversationCanvasManager } from '../../services/conversationCanvasManager';

interface ChatMessageProps {
  message: string;
  isUser: boolean;
  timestamp?: string;
  agentType?: string;
  model?: string;
  /** 메시지 ID (피드백용) */
  messageId?: string;
  /** 대화 ID (피드백용) */
  conversationId?: string;
  /** 사용자 질문 (피드백용) */
  userQuery?: string;
  /** 응답 시간 (피드백용) */
  responseTimeMs?: number;
  /** 타이핑 중인지 여부 */
  isTyping?: boolean;
  /** 로딩 중인지 여부 */
  isLoading?: boolean;
  /** 검색 진행 상태 */
  searchStatus?: {
    isSearching: boolean;
    currentStep: string;
    progress: number;
  };
  /** 검색 진행 단계 (SearchProgressIndicator용) */
  searchSteps?: SearchStep[];
  /** 인용 정보 */
  citations?: CitationData[];
  /** 출처 정보 */
  sources?: SourceData[];
  /** 검색 결과 (웹 검색 에이전트용) */
  searchResults?: SearchResult[];
  /** 검색 쿼리 (웹 검색 에이전트용) */
  searchQuery?: string;
  /** 원본 사용자 질문 (맥락 통합 검색 시) */
  originalQuery?: string;
  /** 맥락이 적용되었는지 여부 */
  hasContext?: boolean;
  /** 인용 표시 모드 */
  citationMode?: 'full' | 'preview' | 'none';
  /** 커스텀 타이핑 메시지 */
  customTypingMessage?: string;
  /** 스트리밍 청크 데이터 (스트리밍 모드용) */
  streamingChunk?: string;
  /** 스트리밍 모드 여부 */
  isStreamingMode?: boolean;
  /** Canvas 데이터 (Artifact 링크용) */
  canvasData?: CanvasData;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isUser,
  timestamp,
  agentType,
  model,
  messageId,
  conversationId,
  userQuery,
  responseTimeMs,
  isTyping = false,
  isLoading = false,
  searchStatus,
  searchSteps = [],
  citations = [],
  sources = [],
  searchResults = [],
  searchQuery = '',
  originalQuery,
  hasContext = false,
  citationMode = 'preview',
  customTypingMessage,
  streamingChunk,
  isStreamingMode = false,
  canvasData,
}) => {
  const [copySuccess, setCopySuccess] = useState(false);
  const [rating, setRating] = useState<'up' | 'down' | null>(null);
  const [feedback, setFeedback] = useState<MessageFeedback | null>(null);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  
  // Canvas Store 함수들 (새로운 통합 시스템 사용)
  const { getOrCreateCanvas, openWithArtifact } = useCanvasStore();
  const { isImageDeleted } = useImageSessionStore();
  
  // ProgressiveMarkdown ref
  const progressiveMarkdownRef = useRef<ProgressiveMarkdownRef>(null);
  const lastChunkRef = useRef<string>('');
  const streamingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // 반응형 hooks
  const { isMobile, isTablet } = useResponsive();

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('복사 실패:', err);
    }
  };

  // Canvas Artifact 열기 핸들러 (새로운 통합 시스템 사용)
  const handleOpenCanvas = async () => {
    // 비활성화된 인라인 링크는 클릭 방지
    if (isInlineLinkDisabled) {
      console.log('🗑️ 삭제된 이미지로 인한 인라인 링크 클릭 차단');
      return;
    }
    
    if (canvasData && conversationId) {
      console.log('🎨 Artifact 버튼 클릭 (새 시스템) - Canvas 데이터:', canvasData);
      console.log('🎨 Artifact 버튼 클릭 (새 시스템) - conversationId:', conversationId);
      
      // ConversationCanvasManager를 통한 타입 추론
      const inferredType = ConversationCanvasManager.inferCanvasType(canvasData);
      
      console.log('🔍 Canvas 타입 추론:', inferredType);
      
      // getOrCreateCanvas 사용 - 중복 생성 완전 방지
      const canvasId = getOrCreateCanvas(conversationId, inferredType, canvasData);
      console.log('✅ Canvas 활성화 완료 (중복 방지) - Canvas ID:', canvasId);
      
      // 🎨 ImageSession 버전 선택 동기화 (이미지 타입인 경우)
      if (inferredType === 'image' && (canvasData.image_data || canvasData.imageUrl || canvasData.images)) {
        const imageSessionStore = useImageSessionStore.getState();
        const session = imageSessionStore.getSession(conversationId);
        
        if (session) {
          // 클릭한 메시지의 이미지 URL 추출 (호환성 강화)
          let targetImageUrl = null;
          const { image_data } = canvasData;
          
          // 새 표준 형식에서 추출
          if (image_data?.image_urls && image_data.image_urls.length > 0) {
            targetImageUrl = image_data.image_urls[0];
          } else if (image_data?.images && image_data.images.length > 0) {
            const firstImage = image_data.images[0];
            targetImageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
          } else if (image_data?.generation_result?.images?.[0]) {
            const firstImage = image_data.generation_result.images[0];
            targetImageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
          }
          // 구 형식 호환성
          else if (canvasData.imageUrl) {
            targetImageUrl = canvasData.imageUrl;
          } else if (canvasData.images && canvasData.images.length > 0) {
            const firstImage = canvasData.images[0];
            targetImageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
          } else if (canvasData.image_urls && canvasData.image_urls.length > 0) {
            targetImageUrl = canvasData.image_urls[0];
          }
          
          if (targetImageUrl) {
            // 해당 이미지 URL에 맞는 버전 찾기
            const matchingVersion = session.versions.find(v => v.imageUrl === targetImageUrl);
            
            if (matchingVersion && matchingVersion.id !== session.selectedVersionId) {
              console.log('🔄 ImageSession 버전 동기화 (인라인 링크 클릭):', {
                from: session.selectedVersionId,
                to: matchingVersion.id,
                targetImageUrl: targetImageUrl.slice(0, 50) + '...'
              });
              
              // 🚀 Canvas Store의 selectVersionInCanvas 직접 호출로 실시간 이미지 업데이트
              const canvasStore = useCanvasStore.getState();
              await canvasStore.selectVersionInCanvas(conversationId, matchingVersion.id);
              
              console.log('✅ 인라인 링크 클릭: Canvas 이미지 실시간 업데이트 완료');
            } else {
              console.log('🔍 대상 버전이 이미 선택되어 있거나 찾을 수 없음');
            }
          }
        }
      }
    } else {
      console.warn('⚠️ Canvas 데이터 또는 conversationId가 없음');
    }
  };
  
  // v4.0 스마트 인라인 링크 생명주기 관리
  const inlineLinkStatus = React.useMemo(() => {
    if (!canvasData || !conversationId) {
      return { isDisabled: true, reason: 'no_canvas_data' };
    }
    
    // 이미지 Canvas 특별 처리 (호환성 강화)
    if (canvasData.type === 'image') {
      let imageUrl = null;
      const { image_data } = canvasData;
      
      // 새 표준 형식에서 이미지 URL 추출
      if (image_data?.image_urls?.[0]) {
        imageUrl = image_data.image_urls[0];
      } else if (image_data?.images?.[0]) {
        const firstImage = image_data.images[0];
        imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
      } else if (image_data?.generation_result?.images?.[0]) {
        const firstImage = image_data.generation_result.images[0];
        imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
      }
      // 구 형식 호환성: canvasData에 직접 있는 경우
      else if (canvasData.imageUrl) {
        imageUrl = canvasData.imageUrl;
      } else if (canvasData.images?.[0]) {
        const firstImage = canvasData.images[0];
        imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
      } else if (canvasData.image_urls?.[0]) {
        imageUrl = canvasData.image_urls[0];
      }
      
      if (imageUrl) {
        const deleted = isImageDeleted(conversationId, imageUrl);
        if (deleted) {
          console.log('🗑️ 삭제된 이미지로 인한 인라인 링크 비활성화:', imageUrl.slice(0, 50) + '...');
          return { isDisabled: true, reason: 'image_deleted' };
        }
      }
    }
    
    // v4.0 Canvas 지속성 체크 (호환성 강화)
    const hasValidCanvasData = canvasData && (() => {
      // 새 표준 형식 검사
      if (canvasData.type === 'image' && canvasData.image_data) {
        return true;
      }
      if (canvasData.type === 'text' && canvasData.text_data) {
        return true;
      }
      if (canvasData.type === 'mindmap' && canvasData.mindmap_data) {
        return true;
      }
      if (canvasData.type === 'code' && canvasData.code_data) {
        return true;
      }
      if (canvasData.type === 'chart' && canvasData.chart_data) {
        return true;
      }
      
      // 구 형식 호환성 검사 (v3.x 이하)
      if (canvasData.type === 'image') {
        // 구 형식: imageUrl, images 등이 직접 canvasData에 있는 경우
        return canvasData.imageUrl || canvasData.images || canvasData.image_urls;
      }
      
      return false;
    })();
    
    if (!hasValidCanvasData) {
      return { isDisabled: true, reason: 'invalid_canvas_data' };
    }
    
    // 활성 상태 - Canvas 데이터가 존재하고 유효함
    return { isDisabled: false, reason: 'active' };
  }, [canvasData, conversationId, isImageDeleted]);
  
  // 하위 호환성을 위한 기존 변수
  const isInlineLinkDisabled = inlineLinkStatus.isDisabled;
  
  // v4.0 Canvas 타입별 레이블
  const getCanvasTypeLabel = (type?: string): string => {
    switch (type) {
      case 'image': return '이미지 생성';
      case 'text': return '텍스트 노트';
      case 'mindmap': return '마인드맵';
      case 'code': return '코드 편집';
      case 'chart': return '차트 분석';
      default: return '작업';
    }
  };
  
  // 비활성화 이유별 메시지
  const getDisabledLinkMessage = (reason: string): string => {
    switch (reason) {
      case 'image_deleted': return '🗑️ 이미지가 삭제되어 사용할 수 없음';
      case 'no_canvas_data': return '❌ Canvas 데이터 없음';
      case 'invalid_canvas_data': return '⚠️ Canvas 데이터 손상됨';
      case 'canvas_not_found': return '🔍 Canvas를 찾을 수 없음';
      case 'session_expired': return '⏱️ 세션이 만료됨';
      default: return '❓ 사용할 수 없음';
    }
  };
  
  // Canvas 데이터 변경 감지 (v4.0 강화 버전 - 상세 로깅)
  useEffect(() => {
    if (!isUser) {
      if (canvasData) {
        console.log(`🎨 ChatMessage Canvas 데이터 수신 - 메시지 ID: ${messageId}`, {
          type: canvasData.type,
          status: inlineLinkStatus.reason,
          isDisabled: inlineLinkStatus.isDisabled,
          hasMetadata: !!canvasData.metadata,
          hasContinuity: !!canvasData.metadata?.continuity,
          // 구조 정보 추가
          hasImageData: !!canvasData.image_data,
          hasLegacyImageUrl: !!canvasData.imageUrl,
          hasLegacyImages: !!canvasData.images,
          structureFormat: canvasData.metadata?.structure_format || 'unknown'
        });
        
        // 이미지 데이터 상세 분석 (이미지 타입인 경우)
        if (canvasData.type === 'image') {
          const imageAnalysis = {
            hasStandardImageData: !!canvasData.image_data,
            hasLegacyFormat: !!canvasData.imageUrl || !!canvasData.images || !!canvasData.image_urls
          };
          
          if (canvasData.image_data) {
            imageAnalysis.standardFormat = {
              hasImageUrls: !!canvasData.image_data.image_urls,
              hasImages: !!canvasData.image_data.images,
              hasGenerationResult: !!canvasData.image_data.generation_result,
              imageUrlsCount: canvasData.image_data.image_urls?.length || 0,
              imagesCount: canvasData.image_data.images?.length || 0
            };
          }
          
          if (canvasData.imageUrl || canvasData.images) {
            imageAnalysis.legacyFormat = {
              hasDirectImageUrl: !!canvasData.imageUrl,
              hasDirectImages: !!canvasData.images,
              directImagesCount: canvasData.images?.length || 0
            };
          }
          
          console.log(`🔍 Canvas 이미지 데이터 분석:`, imageAnalysis);
        }
        
        // 연속성 정보 로깅
        if (canvasData.metadata?.continuity) {
          console.log(`🔗 Canvas 연속성 정보:`, {
            baseCanvasId: canvasData.metadata.continuity.baseCanvasId,
            relationshipType: canvasData.metadata.continuity.relationshipType,
            referenceDescription: canvasData.metadata.continuity.referenceDescription
          });
        }
        
        console.log(`✅ 인라인 링크 버튼 상태: ${inlineLinkStatus.isDisabled ? '비활성' : '활성'} (이유: ${inlineLinkStatus.reason})`);
      } else {
        console.log(`❌ ChatMessage Canvas 데이터 없음 - 메시지 ID: ${messageId}, 인라인 버튼이 표시되지 않습니다.`);
      }
    }
  }, [canvasData, messageId, isUser, inlineLinkStatus]);

  // 기존 피드백 로드
  useEffect(() => {
    if (!isUser && messageId) {
      loadExistingFeedback();
    }
  }, [messageId, isUser]);

  // 컴포넌트 언마운트 시 타이머 정리
  useEffect(() => {
    return () => {
      if (streamingTimeoutRef.current) {
        clearTimeout(streamingTimeoutRef.current);
      }
    };
  }, []);

  // 스트리밍 청크 처리 (중복 방지)
  useEffect(() => {
    if (isStreamingMode && streamingChunk && progressiveMarkdownRef.current) {
      // 증분 청크만 전달 (중복 방지)
      const previousLength = lastChunkRef.current.length;
      const newChunk = streamingChunk.slice(previousLength);
      
      if (newChunk.length > 0) {
        loggers.stream('스트리밍 청크 처리', {
          newChunkLength: newChunk.length,
          totalLength: streamingChunk.length
        }, 'ChatMessage');
        
        progressiveMarkdownRef.current.appendChunk(streamingChunk); // 전체 누적 텍스트 전달
        lastChunkRef.current = streamingChunk;
      }
      
      // 스트리밍 완료 감지를 위한 타이머 설정 (1초 후 완료로 간주)
      if (streamingTimeoutRef.current) {
        clearTimeout(streamingTimeoutRef.current);
      }
      
      streamingTimeoutRef.current = setTimeout(() => {
        if (progressiveMarkdownRef.current) {
          progressiveMarkdownRef.current.endStreaming();
        }
      }, 1000); // 1초간 새로운 청크가 없으면 완료로 간주
    }
  }, [streamingChunk, isStreamingMode]);

  // 스트리밍 완료 처리
  useEffect(() => {
    loggers.debug('스트리밍 모드 변경 감지', { 
      isStreamingMode, 
      hasRef: !!progressiveMarkdownRef.current, 
      hasLastChunk: !!lastChunkRef.current 
    }, 'ChatMessage');
    
    if (!isStreamingMode && progressiveMarkdownRef.current && lastChunkRef.current) {
      loggers.info('스트리밍 완료 - endStreaming() 호출', 'ChatMessage');
      progressiveMarkdownRef.current.endStreaming();
      lastChunkRef.current = '';
    } else if (!isStreamingMode) {
      loggers.debug('endStreaming 호출되지 않음 - 조건 미충족', undefined, 'ChatMessage');
    }
  }, [isStreamingMode]);

  const loadExistingFeedback = async () => {
    if (!messageId) return;
    
    try {
      const existingFeedback = await feedbackService.getMessageFeedback(messageId);
      if (existingFeedback) {
        setFeedback(existingFeedback);
        // 기존 피드백이 있으면 UI 상태 동기화
        if (existingFeedback.is_positive !== undefined) {
          setRating(existingFeedback.is_positive ? 'up' : 'down');
        }
      }
    } catch (error) {
      console.error('기존 피드백 로드 실패:', error);
    }
  };

  const handleRating = async (type: 'up' | 'down') => {
    if (!messageId || isSubmittingFeedback) return;
    
    const newRating = rating === type ? null : type;
    setRating(newRating);
    
    // 피드백이 있으면 제출
    if (newRating !== null) {
      await submitThumbsFeedback(newRating === 'up');
    }
  };

  const submitThumbsFeedback = async (isPositive: boolean) => {
    if (!messageId || isSubmittingFeedback) return;
    
    setIsSubmittingFeedback(true);
    try {
      const feedbackId = await feedbackService.submitThumbsFeedback(
        messageId,
        isPositive,
        {
          conversationId,
          agentType,
          modelUsed: model,
          responseTimeMs,
          userQuery,
          aiResponse: message
        }
      );
      
      // 피드백 상태 업데이트
      await loadExistingFeedback();
      
      console.log('피드백 제출 성공:', feedbackId);
    } catch (error) {
      console.error('피드백 제출 실패:', error);
      // 에러 시 UI 상태 되돌리기
      setRating(null);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };
  // 검색 중이거나 타이핑 중이면 진행 상태 표시
  if ((searchStatus?.isSearching || isTyping) && !isUser) {
    return (
      <div className="flex items-start space-x-3 max-w-4xl">
        {/* AI 아바타 */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center">
          <Bot className="w-4 h-4 text-slate-600 dark:text-slate-300" />
        </div>
        
        {/* 진행 상태 표시 */}
        <div className="flex-1 min-w-0 max-w-3xl">
          {searchStatus?.isSearching ? (
            /* 기존 검색 진행 상태 (폴백) */
            <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm">
              <div className="p-4 space-y-3">
                {/* 검색 단계 표시 */}
                <div className="flex items-center space-x-2">
                  <Search className="w-4 h-4 text-blue-500 animate-pulse" />
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    웹 검색 중...
                  </span>
                </div>
                
                {/* 현재 단계 */}
                <div className="text-xs text-slate-600 dark:text-slate-400">
                  {searchStatus.currentStep}
                </div>
                
                {/* 진행률 바 */}
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${searchStatus.progress}%` }}
                  />
                </div>
                
                {/* 모델 정보 */}
                {model && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-500">
                      {model.replace('claude', 'Claude').replace('gemini', 'Gemini')}
                    </span>
                    <span className="text-xs text-slate-500">
                      {Math.round(searchStatus.progress)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* 간단한 타이핑 인디케이터 - 동적 메시지 지원 */
            <div className="bg-white dark:bg-slate-800 rounded-3xl rounded-tl-lg px-6 py-4 shadow-sm border border-slate-200 dark:border-slate-700 min-w-0 max-w-3xl">
              <div className="flex items-center space-x-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                </div>
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  {customTypingMessage || `${model?.replace('claude', 'Claude').replace('gemini', 'Gemini')} 모델로 응답 생성 중...`}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // 인용이 포함된 메시지 텍스트 렌더링
  const renderMessageWithCitations = () => {
    if (!citations.length || citationMode === 'none') {
      // AI 응답은 마크다운 렌더링, 사용자 메시지는 일반 텍스트
      if (!isUser) {
        return (
          <ProgressiveMarkdown 
            ref={progressiveMarkdownRef}
            text={isStreamingMode ? '' : message} // 스트리밍 모드가 아닐 때만 텍스트 설정
            isStreaming={isStreamingMode}
            className=""
          />
        );
      }
      return <div className="text-sm leading-relaxed whitespace-pre-wrap">{message}</div>;
    }

    // 인용 위치 기준으로 정렬
    const sortedCitations = [...citations].sort((a, b) => a.startPosition - b.startPosition);
    
    let renderedMessage = [];
    let lastPosition = 0;

    sortedCitations.forEach((citation, index) => {
      const source = sources.find(s => s.id === citation.sourceId);
      if (!source) return;

      // 인용 이전 텍스트 추가
      if (citation.startPosition > lastPosition) {
        renderedMessage.push(
          <span key={`text-${index}`}>
            {message.slice(lastPosition, citation.startPosition)}
          </span>
        );
      }

      // 인용된 텍스트와 인용 번호 추가
      renderedMessage.push(
        <span key={`citation-${index}`} className="relative">
          <span className="bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300 px-2 py-0.5 rounded-lg text-sm font-medium">
            {citation.text}
          </span>
          {citationMode === 'full' ? (
            <Citation
              citation={citation}
              source={source}
              index={index + 1}
            />
          ) : (
            <CitationPreview
              citation={citation}
              source={source}
              index={index + 1}
            />
          )}
        </span>
      );

    return <div className="text-sm leading-relaxed whitespace-pre-wrap">{renderedMessage}</div>;

      lastPosition = citation.endPosition;
    });

    // 마지막 인용 이후 남은 텍스트 추가
    if (lastPosition < message.length) {
      renderedMessage.push(
        <span key="text-final">
          {message.slice(lastPosition)}
        </span>
      );
    }

    return <div className="text-sm leading-relaxed whitespace-pre-wrap">{renderedMessage}</div>;
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} group w-full ${
      isMobile ? 'px-2' : 'px-0'
    }`}>
      <div className={`flex items-start ${isMobile ? 'space-x-2' : 'space-x-3'} ${
        isMobile ? 'max-w-full' : 'max-w-4xl'
      } ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
        {/* 아바타 - 모바일에서는 더 작게 */}
        <div className={`flex-shrink-0 ${isMobile ? 'w-6 h-6' : 'w-8 h-8'} rounded-full flex items-center justify-center transition-all duration-200 ${
          isUser 
            ? 'bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-md' 
            : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
        }`}>
          {isUser ? (
            <User className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`} />
          ) : (
            <Bot className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'}`} />
          )}
        </div>

        {/* 메시지 콘텐츠 */}
        <div className="flex-1 min-w-0">
          {/* 메시지 헤더 */}
          {!isUser && (
            <div className={`flex items-center mb-2 ${isMobile ? 'flex-wrap gap-1' : ''}`}>
              <span className={`${isMobile ? 'text-xs' : 'text-sm'} font-semibold text-slate-900 dark:text-slate-100`}>
                AI Assistant
              </span>
              
              {/* 모델 뱃지 - 모바일에서는 더 작게 */}
              {model && (
                <div className={`flex items-center ${isMobile ? 'ml-1' : 'ml-2'}`}>
                  {model.includes('claude') && (
                    <div className={`flex items-center gap-1 px-2 py-0.5 bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 rounded-full ${
                      isMobile ? 'text-xs' : 'text-xs'
                    } font-medium`}>
                      <Star className={`${isMobile ? 'w-2.5 h-2.5' : 'w-3 h-3'}`} />
                      {isMobile ? 'C' : 'Claude'}
                    </div>
                  )}
                  {model.includes('gemini') && (
                    <div className={`flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full ${
                      isMobile ? 'text-xs' : 'text-xs'
                    } font-medium`}>
                      <Zap className={`${isMobile ? 'w-2.5 h-2.5' : 'w-3 h-3'}`} />
                      {isMobile ? 'G' : 'Gemini'}
                    </div>
                  )}
                </div>
              )}
              
              {/* 에이전트 뱃지 - 명확한 기능 사용시에만 표시 */}
              {agentType && ['web_search', 'deep_research', 'canvas'].includes(agentType) && (
                <span className={`${isMobile ? 'ml-1' : 'ml-2'} px-2 py-0.5 ${
                  isMobile ? 'text-xs' : 'text-xs'
                } font-medium rounded-full ${
                  agentType === 'web_search' 
                    ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                    : agentType === 'deep_research'
                    ? 'bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300'
                    : 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300'
                }`}>
                  {isMobile ? (
                    agentType === 'web_search' ? '검색' : 
                    agentType === 'deep_research' ? '리서치' : 
                    'Canvas'
                  ) : (
                    agentType === 'web_search' ? '웹 검색' : 
                    agentType === 'deep_research' ? '심층 리서치' : 
                    'Canvas'
                  )}
                </span>
              )}

              {/* 타임스탬프 */}
              {timestamp && (
                <span className={`${
                  isMobile ? 'text-xs ml-auto w-full text-right' : 'text-xs ml-auto'
                } text-slate-400 dark:text-slate-500`}>
                  {new Date(timestamp).toLocaleTimeString('ko-KR', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
              )}
            </div>
          )}

          {/* 메시지 내용 */}
          <div className="relative">
            <div
              className={`inline-block max-w-full transition-all duration-200 ${
                isUser
                  ? `bg-primary-600 dark:bg-primary-700 text-white rounded-3xl rounded-tr-lg ${
                      isMobile ? 'px-4 py-2.5 text-sm' : 'px-5 py-3'
                    } shadow-lg`
                  : `bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-3xl rounded-tl-lg ${
                      isMobile ? 'px-4 py-2.5 text-sm' : 'px-5 py-3'
                    } shadow-sm border border-slate-200 dark:border-slate-700`
              }`}
            >
              <div className={`max-w-none ${
                isUser 
                  ? 'text-white' 
                  : 'text-slate-900 dark:text-slate-100'
              }`}>
                {renderMessageWithCitations()}
              </div>
            </div>
            
            {/* 사용자 메시지 타임스탬프 */}
            {isUser && timestamp && (
              <div className="text-xs text-slate-400 dark:text-slate-500 mt-1 text-right">
                {new Date(timestamp).toLocaleTimeString('ko-KR', { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </div>
            )}
          </div>

          {/* 검색 결과 시각화 (웹 검색 에이전트용) */}
          {!isUser && agentType === 'web_search' && searchResults && searchResults.length > 0 && (
            <div className="mt-3 ml-1">
              <SearchResultsCard 
                query={searchQuery || '검색 쿼리'}
                results={searchResults}
                collapsible={true}
                defaultCollapsed={true}
                maxResults={3}
                showMetadata={true}
                originalQuery={originalQuery}
                hasContext={hasContext}
              />
            </div>
          )}
          
          {/* Canvas Artifact 버튼 (AI 응답에 canvas_data가 있을 때) */}
          {!isUser && canvasData && (
            <div className="mt-3 ml-1">
              <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl shadow-sm transition-all duration-200 group/artifact ${
                isInlineLinkDisabled 
                  ? 'bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 opacity-60 cursor-not-allowed'
                  : 'bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/30 dark:to-pink-900/30 border border-purple-200 dark:border-purple-700 hover:shadow-md cursor-pointer'
              }`} onClick={handleOpenCanvas}>
                <div className="flex items-center gap-2">
                  {/* Canvas 타입별 아이콘 */}
                  <div className={`p-1.5 rounded-lg ${
                    isInlineLinkDisabled 
                      ? 'bg-gray-400 dark:bg-gray-600'
                      : 'bg-gradient-to-br from-purple-500 to-pink-500'
                  }`}>
                    {canvasData.type === 'image' ? (
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                        <circle cx="9" cy="9" r="2" />
                        <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
                      </svg>
                    ) : canvasData.type === 'mindmap' ? (
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2v4m0 4v4m0 4v4M4 12h4m4 0h4m4 0h4" />
                        <circle cx="12" cy="12" r="2" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                        <path d="M9 12l2 2 4-4" />
                      </svg>
                    )}
                  </div>
                  
                  {/* Canvas 정보 */}
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className={`text-sm font-medium ${
                        isInlineLinkDisabled 
                          ? 'text-gray-500 dark:text-gray-400'
                          : 'text-purple-700 dark:text-purple-300'
                      }`}>
                        {canvasData.title || `Canvas ${canvasData.type === 'image' ? '이미지' : canvasData.type === 'mindmap' ? '마인드맵' : '작업'}`}
                      </span>
                      
                      {/* v4.0 연속성 정보 배지 */}
                      {!inlineLinkStatus.isDisabled && canvasData.metadata?.continuity?.baseCanvasId && (
                        <div className="flex items-center gap-1 px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 rounded text-xs font-medium"
                             title={`이전 Canvas를 ${canvasData.metadata.continuity.relationshipType || '참조'}하여 생성됨`}>
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                          </svg>
                          연속
                        </div>
                      )}
                    </div>
                    <span className={`text-xs ${
                      inlineLinkStatus.isDisabled 
                        ? 'text-gray-400 dark:text-gray-500'
                        : 'text-purple-600 dark:text-purple-400'
                    }`}>
                      {inlineLinkStatus.isDisabled 
                        ? getDisabledLinkMessage(inlineLinkStatus.reason)
                        : `🎨 Canvas에서 보기 • ${getCanvasTypeLabel(canvasData?.type)}`}
                    </span>
                  </div>
                </div>
                
                {/* 열기 아이콘 */}
                <svg className="w-4 h-4 text-purple-600 dark:text-purple-400 group-hover/artifact:translate-x-0.5 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </div>
            </div>
          )}

          {/* 출처 및 추가 정보 (AI 응답에만, 웹 검색 아닌 경우) */}
          {!isUser && agentType !== 'web_search' && sources.length > 0 && (
            <div className="mt-3 ml-1">
              <SourceList 
                sources={sources} 
                collapsible={true}
                showMetadata={false}
              />
            </div>
          )}

          {/* 메시지 액션 버튼들 */}
          <div className={`flex items-center space-x-1 mt-2 opacity-0 group-hover:opacity-100 transition-all duration-200 ${
            isUser ? 'justify-end' : 'justify-start'
          }`}>
            {/* 복사 버튼 */}
            <button
              onClick={handleCopy}
              className={`p-2 rounded-lg transition-all duration-200 ${
                copySuccess 
                  ? 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400' 
                  : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 dark:hover:text-slate-300'
              }`}
              title={copySuccess ? '복사됨!' : '메시지 복사'}
            >
              <Copy className="w-4 h-4" />
            </button>

            {/* AI 응답에만 표시되는 추가 액션들 */}
            {!isUser && (
              <>
                {/* 좋아요/싫어요 */}
                <button
                  onClick={() => handleRating('up')}
                  disabled={isSubmittingFeedback}
                  className={`p-2 rounded-lg transition-all duration-200 ${
                    rating === 'up'
                      ? 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400'
                      : isSubmittingFeedback
                      ? 'text-slate-300 cursor-not-allowed'
                      : 'text-slate-400 hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20'
                  }`}
                  title={isSubmittingFeedback ? '피드백 제출 중...' : '좋아요'}
                >
                  {isSubmittingFeedback && rating === 'up' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ThumbsUp className="w-4 h-4" />
                  )}
                </button>

                <button
                  onClick={() => handleRating('down')}
                  disabled={isSubmittingFeedback}
                  className={`p-2 rounded-lg transition-all duration-200 ${
                    rating === 'down'
                      ? 'text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400'
                      : isSubmittingFeedback
                      ? 'text-slate-300 cursor-not-allowed'
                      : 'text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20'
                  }`}
                  title={isSubmittingFeedback ? '피드백 제출 중...' : '싫어요'}
                >
                  {isSubmittingFeedback && rating === 'down' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ThumbsDown className="w-4 h-4" />
                  )}
                </button>

                {/* 재생성 */}
                <button
                  className="p-2 text-slate-400 hover:text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-all duration-200"
                  title="응답 재생성"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};