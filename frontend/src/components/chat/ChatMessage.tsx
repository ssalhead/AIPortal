/**
 * 채팅 메시지 컴포넌트 - Gemini 스타일
 */

import React, { useState } from 'react';
import { TypingIndicator } from '../ui/TypingIndicator';
import { Citation, CitationPreview } from '../citation/Citation';
import { SourceList } from '../citation/SourceList';
import { SearchResultsCard } from '../search/SearchResultsCard';
import type { SearchResult } from '../search/SearchResultsCard';
import { Copy, ThumbsUp, ThumbsDown, RotateCcw, User, Bot, Star, Zap, Search, Loader2 } from 'lucide-react';
import type { Citation as CitationData, Source as SourceData } from '../../types';

interface ChatMessageProps {
  message: string;
  isUser: boolean;
  timestamp?: string;
  agentType?: string;
  model?: string;
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
  /** 인용 정보 */
  citations?: CitationData[];
  /** 출처 정보 */
  sources?: SourceData[];
  /** 검색 결과 (웹 검색 에이전트용) */
  searchResults?: SearchResult[];
  /** 검색 쿼리 (웹 검색 에이전트용) */
  searchQuery?: string;
  /** 인용 표시 모드 */
  citationMode?: 'full' | 'preview' | 'none';
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isUser,
  timestamp,
  agentType,
  model,
  isTyping = false,
  isLoading = false,
  searchStatus,
  citations = [],
  sources = [],
  searchResults = [],
  searchQuery = '',
  citationMode = 'preview',
}) => {
  const [copySuccess, setCopySuccess] = useState(false);
  const [rating, setRating] = useState<'up' | 'down' | null>(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('복사 실패:', err);
    }
  };

  const handleRating = (type: 'up' | 'down') => {
    setRating(rating === type ? null : type);
  };
  // 검색 중이거나 타이핑 중이면 진행 상태 표시
  if ((searchStatus?.isSearching || isTyping) && !isUser) {
    return (
      <div className="flex items-start space-x-3 max-w-4xl">
        {/* AI 아바타 */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center">
          <Bot className="w-4 h-4 text-slate-600 dark:text-slate-300" />
        </div>
        
        {/* 진행 상태 버블 */}
        <div className="bg-white dark:bg-slate-800 rounded-3xl rounded-tl-lg px-6 py-4 shadow-sm border border-slate-200 dark:border-slate-700 min-w-0 flex-1 max-w-md">
          {searchStatus?.isSearching ? (
            <div className="space-y-3">
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
          ) : (
            /* 기본 타이핑 인디케이터 */
            <div className="flex items-center space-x-1">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
              </div>
              {model && (
                <span className="text-xs text-slate-500 ml-2">
                  {model.replace('claude', 'Claude').replace('gemini', 'Gemini')}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  // 인용이 포함된 메시지 텍스트 렌더링
  const renderMessageWithCitations = () => {
    if (!citations.length || citationMode === 'none') {
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
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} group w-full`}>
      <div className={`flex items-start space-x-3 max-w-4xl ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
        {/* 아바타 */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 ${
          isUser 
            ? 'bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-md' 
            : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
        }`}>
          {isUser ? (
            <User className="w-4 h-4" />
          ) : (
            <Bot className="w-4 h-4" />
          )}
        </div>

        {/* 메시지 콘텐츠 */}
        <div className="flex-1 min-w-0">
          {/* 메시지 헤더 */}
          {!isUser && (
            <div className="flex items-center mb-2">
              <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                AI Assistant
              </span>
              
              {/* 모델 뱃지 */}
              {model && (
                <div className="flex items-center ml-2">
                  {model.includes('claude') && (
                    <div className="flex items-center gap-1 px-2 py-0.5 bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 rounded-full text-xs font-medium">
                      <Star className="w-3 h-3" />
                      Claude
                    </div>
                  )}
                  {model.includes('gemini') && (
                    <div className="flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-xs font-medium">
                      <Zap className="w-3 h-3" />
                      Gemini
                    </div>
                  )}
                </div>
              )}
              
              {/* 에이전트 뱃지 */}
              {agentType && agentType !== 'none' && (
                <span className={`ml-2 px-2 py-0.5 text-xs font-medium rounded-full ${
                  agentType === 'web_search' 
                    ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                    : agentType === 'deep_research'
                    ? 'bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300'
                    : 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300'
                }`}>
                  {agentType === 'web_search' ? '웹 검색' : 
                   agentType === 'deep_research' ? '심층 리서치' : 
                   agentType === 'canvas' ? 'Canvas' : '문서 분석'}
                </span>
              )}

              {/* 타임스탬프 */}
              {timestamp && (
                <span className="text-xs text-slate-400 dark:text-slate-500 ml-auto">
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
                  ? 'bg-primary-600 dark:bg-primary-700 text-white rounded-3xl rounded-tr-lg px-5 py-3 shadow-lg'
                  : 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 rounded-3xl rounded-tl-lg px-5 py-3 shadow-sm border border-slate-200 dark:border-slate-700'
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
          {!isUser && agentType === 'web_search' && searchResults.length > 0 && (
            <div className="mt-3 ml-1">
              <SearchResultsCard 
                query={searchQuery}
                results={searchResults}
                collapsible={true}
                defaultCollapsed={false}
                maxResults={3}
                showMetadata={true}
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
                  className={`p-2 rounded-lg transition-all duration-200 ${
                    rating === 'up'
                      ? 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400'
                      : 'text-slate-400 hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20'
                  }`}
                  title="좋아요"
                >
                  <ThumbsUp className="w-4 h-4" />
                </button>

                <button
                  onClick={() => handleRating('down')}
                  className={`p-2 rounded-lg transition-all duration-200 ${
                    rating === 'down'
                      ? 'text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400'
                      : 'text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20'
                  }`}
                  title="싫어요"
                >
                  <ThumbsDown className="w-4 h-4" />
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