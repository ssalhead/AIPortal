/**
 * 채팅 메시지 컴포넌트 - Gemini 스타일
 */

import React, { useState, useEffect } from 'react';
import { TypingIndicator } from '../ui/TypingIndicator';
import { Citation, CitationPreview } from '../citation/Citation';
import { SourceList } from '../citation/SourceList';
import { SearchResultsCard } from '../search/SearchResultsCard';
import { SearchProgressIndicator, type SearchStep } from '../SearchProcess/SearchProgressIndicator';
import type { SearchResult } from '../search/SearchResultsCard';
import { Copy, ThumbsUp, ThumbsDown, RotateCcw, User, Bot, Star, Zap, Search, Loader2 } from 'lucide-react';
import { SimpleMarkdown } from '../ui/SimpleMarkdown';
import type { Citation as CitationData, Source as SourceData } from '../../types';
import { feedbackService } from '../../services/feedbackService';
import { useResponsive } from '../../hooks/useResponsive';
import type { MessageFeedback } from '../../types/feedback';

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
}) => {
  const [copySuccess, setCopySuccess] = useState(false);
  const [rating, setRating] = useState<'up' | 'down' | null>(null);
  const [feedback, setFeedback] = useState<MessageFeedback | null>(null);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  
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

  // 기존 피드백 로드
  useEffect(() => {
    if (!isUser && messageId) {
      loadExistingFeedback();
    }
  }, [messageId, isUser]);

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
        return <SimpleMarkdown text={message} className="text-sm leading-relaxed" />;
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
              
              {/* 에이전트 뱃지 - 모바일에서는 더 간결하게 */}
              {agentType && agentType !== 'none' && (
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
                    agentType === 'canvas' ? 'Canvas' : '분석'
                  ) : (
                    agentType === 'web_search' ? '웹 검색' : 
                    agentType === 'deep_research' ? '심층 리서치' : 
                    agentType === 'canvas' ? 'Canvas' : '문서 분석'
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
                defaultCollapsed={false}
                maxResults={3}
                showMetadata={true}
                originalQuery={originalQuery}
                hasContext={hasContext}
              />
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