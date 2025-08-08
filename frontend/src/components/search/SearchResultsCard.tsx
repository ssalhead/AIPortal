/**
 * 검색 결과 카드 컴포넌트 - 웹 검색 결과를 시각적으로 표시
 */

import React, { useState } from 'react';
import { ExternalLink, Globe, Search, Clock, Star, TrendingUp, ChevronDown, ChevronUp, Eye } from 'lucide-react';

export interface SearchResult {
  id: string;
  title: string;
  url: string;
  snippet: string;
  source: string;
  score: number;
  timestamp?: string;
  provider?: string;
}

interface SearchResultsCardProps {
  /** 검색 쿼리 */
  query: string;
  /** 검색 결과 목록 */
  results: SearchResult[];
  /** 접기/펼치기 가능 여부 */
  collapsible?: boolean;
  /** 기본 접힘 상태 */
  defaultCollapsed?: boolean;
  /** 최대 표시할 결과 수 */
  maxResults?: number;
  /** 메타데이터 표시 여부 */
  showMetadata?: boolean;
}

export const SearchResultsCard: React.FC<SearchResultsCardProps> = ({
  query,
  results,
  collapsible = true,
  defaultCollapsed = false,
  maxResults = 5,
  showMetadata = true,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [showAll, setShowAll] = useState(false);

  if (!results || results.length === 0) {
    return null;
  }

  const displayResults = showAll ? results : results.slice(0, maxResults);
  const hasMoreResults = results.length > maxResults;

  const getSourceIcon = (source: string) => {
    if (source.includes('google')) return '🌐';
    if (source.includes('duckduckgo')) return '🦆';
    return '🔍';
  };

  const getSourceColor = (source: string) => {
    if (source.includes('google')) return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400';
    if (source.includes('duckduckgo')) return 'text-orange-600 bg-orange-50 dark:bg-orange-900/20 dark:text-orange-400';
    return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20 dark:text-gray-400';
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.9) return 'text-green-600 bg-green-50 dark:bg-green-900/20 dark:text-green-400';
    if (score >= 0.8) return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400';
    if (score >= 0.7) return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 dark:text-yellow-400';
    return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20 dark:text-gray-400';
  };

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-sm">
      {/* 헤더 */}
      <div 
        className={`flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700 ${
          collapsible ? 'cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50' : ''
        }`}
        onClick={collapsible ? () => setIsCollapsed(!isCollapsed) : undefined}
      >
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
            <Search className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100">
              웹 검색 결과
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              "{query}" 에 대한 {results.length}개 결과
            </p>
          </div>
        </div>
        
        {collapsible && (
          <button className="p-1 hover:bg-slate-100 dark:hover:bg-slate-600 rounded">
            {isCollapsed ? (
              <ChevronDown className="w-5 h-5 text-slate-400" />
            ) : (
              <ChevronUp className="w-5 h-5 text-slate-400" />
            )}
          </button>
        )}
      </div>

      {/* 검색 결과 목록 */}
      {!isCollapsed && (
        <div className="divide-y divide-slate-200 dark:divide-slate-700">
          {displayResults.map((result, index) => (
            <div key={result.id || index} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors duration-200">
              {/* 결과 헤더 */}
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex-1 min-w-0">
                  <a
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex items-start gap-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
                  >
                    <h4 className="font-medium text-sm leading-tight overflow-hidden group-hover:underline" 
                        style={{
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                        }}>
                      {result.title}
                    </h4>
                    <ExternalLink className="w-4 h-4 flex-shrink-0 opacity-60 group-hover:opacity-100" />
                  </a>
                  
                  {/* URL 표시 */}
                  <div className="flex items-center gap-2 mt-1">
                    <Globe className="w-3 h-3 text-slate-400" />
                    <span className="text-xs text-slate-500 dark:text-slate-400 truncate">
                      {new URL(result.url).hostname}
                    </span>
                  </div>
                </div>

                {/* 순위 및 점수 */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-xs font-medium text-slate-400">#{index + 1}</span>
                  {showMetadata && (
                    <div className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreColor(result.score)}`}>
                      {Math.round(result.score * 100)}%
                    </div>
                  )}
                </div>
              </div>

              {/* 스니펫 */}
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-3 overflow-hidden"
                 style={{
                   display: '-webkit-box',
                   WebkitLineClamp: 3,
                   WebkitBoxOrient: 'vertical',
                 }}>
                {result.snippet}
              </p>

              {/* 메타데이터 */}
              {showMetadata && (
                <div className="flex items-center gap-3 text-xs">
                  {/* 출처 */}
                  <div className={`flex items-center gap-1 px-2 py-1 rounded-full ${getSourceColor(result.source)}`}>
                    <span>{getSourceIcon(result.source)}</span>
                    <span className="font-medium">
                      {result.source.split('_')[0]?.charAt(0).toUpperCase() + result.source.split('_')[0]?.slice(1)}
                    </span>
                  </div>

                  {/* 신뢰도 */}
                  <div className="flex items-center gap-1 text-slate-500">
                    <TrendingUp className="w-3 h-3" />
                    <span>신뢰도: {Math.round(result.score * 100)}%</span>
                  </div>

                  {/* 타임스탬프 */}
                  {result.timestamp && (
                    <div className="flex items-center gap-1 text-slate-500">
                      <Clock className="w-3 h-3" />
                      <span>{new Date(result.timestamp).toLocaleDateString('ko-KR')}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          
          {/* 더 보기/접기 버튼 */}
          {hasMoreResults && (
            <div className="p-4 border-t border-slate-200 dark:border-slate-700">
              <button
                onClick={() => setShowAll(!showAll)}
                className="w-full flex items-center justify-center gap-2 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
              >
                <Eye className="w-4 h-4" />
                {showAll ? (
                  <>
                    간단히 보기 ({maxResults}개만)
                    <ChevronUp className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    모든 결과 보기 ({results.length - maxResults}개 더)
                    <ChevronDown className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}
      
      {/* 요약 정보 (접힌 상태에서도 표시) */}
      {isCollapsed && (
        <div className="px-4 pb-4">
          <div className="flex items-center justify-between text-sm text-slate-500">
            <span>{results.length}개 검색 결과</span>
            <div className="flex items-center gap-2">
              {results.slice(0, 3).map((result, idx) => (
                <span key={idx} className="text-xs">
                  {getSourceIcon(result.source)}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};