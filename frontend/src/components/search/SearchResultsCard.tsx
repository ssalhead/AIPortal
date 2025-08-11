/**
 * 검색 결과 카드 컴포넌트 - 웹 검색 결과를 시각적으로 표시
 */

import React, { useState } from 'react';
import { ExternalLink, Globe, Search, Clock, Star, TrendingUp, ChevronDown, ChevronUp, Eye, BarChart3, Hash } from 'lucide-react';

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

  const avgScore = results.length > 0 ? results.reduce((sum, r) => sum + r.score, 0) / results.length : 0;
  const topSources = [...new Set(results.map(r => r.source))].slice(0, 3);

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
      {/* 헤더 - 향상된 디자인 */}
      <div 
        className={`flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-b border-slate-200 dark:border-slate-700 ${
          collapsible ? 'cursor-pointer hover:from-blue-100 hover:to-indigo-100 dark:hover:from-blue-900/30 dark:hover:to-indigo-900/30' : ''
        }`}
        onClick={collapsible ? () => setIsCollapsed(!isCollapsed) : undefined}
      >
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0 p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg shadow-sm">
            <Search className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              웹 검색 결과
              <div className="flex items-center gap-1">
                <BarChart3 className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                  {Math.round(avgScore * 100)}% 관련도
                </span>
              </div>
            </h3>
            <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400 mt-1">
              <span>"{query}" 검색</span>
              <div className="flex items-center gap-1">
                <Hash className="w-3 h-3" />
                <span>{results.length}개 결과</span>
              </div>
              <div className="flex items-center gap-1">
                {topSources.map((source, idx) => (
                  <span key={idx} className="text-xs">
                    {getSourceIcon(source)}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {/* 신뢰도 배지 */}
          <div className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreColor(avgScore)}`}>
            {avgScore >= 0.9 ? '🏆 높음' : avgScore >= 0.7 ? '⭐ 보통' : '📊 낮음'}
          </div>
          
          {collapsible && (
            <button className="p-1 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-md transition-colors">
              {isCollapsed ? (
                <ChevronDown className="w-5 h-5 text-slate-400" />
              ) : (
                <ChevronUp className="w-5 h-5 text-slate-400" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* 검색 결과 목록 */}
      {!isCollapsed && (
        <div className="divide-y divide-slate-200 dark:divide-slate-700">
          {displayResults.map((result, index) => (
            <div key={result.id || index} className="group p-4 hover:bg-gradient-to-r hover:from-slate-50 hover:to-blue-50/30 dark:hover:from-slate-700/50 dark:hover:to-blue-900/10 transition-all duration-200 border-l-4 border-transparent hover:border-blue-400">
              {/* 결과 헤더 - 향상된 레이아웃 */}
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {/* 순위 배지 */}
                    <div className={`
                      flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold
                      ${index === 0 ? 'bg-gradient-to-br from-yellow-400 to-orange-500 text-white' :
                        index === 1 ? 'bg-gradient-to-br from-gray-300 to-gray-500 text-white' :
                        index === 2 ? 'bg-gradient-to-br from-orange-400 to-red-500 text-white' :
                        'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400'}
                    `}>
                      {index + 1}
                    </div>
                    
                    {/* 신뢰도 점수 */}
                    {showMetadata && (
                      <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getScoreColor(result.score)}`}>
                        <TrendingUp className="w-3 h-3" />
                        {Math.round(result.score * 100)}%
                      </div>
                    )}
                  </div>
                  
                  <a
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group/link block hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
                  >
                    <h4 className="font-semibold text-slate-900 dark:text-slate-100 leading-tight mb-1 group-hover/link:underline" 
                        style={{
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden'
                        }}>
                      {result.title}
                    </h4>
                  </a>
                  
                  {/* URL 및 메타 정보 */}
                  <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 mb-2">
                    <div className="flex items-center gap-1">
                      <Globe className="w-3 h-3" />
                      <span className="truncate max-w-40">
                        {new URL(result.url).hostname}
                      </span>
                    </div>
                    
                    {result.timestamp && (
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{new Date(result.timestamp).toLocaleDateString('ko-KR')}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* 외부 링크 아이콘 */}
                <a
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-shrink-0 p-2 rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors opacity-60 group-hover:opacity-100"
                  title="외부 링크로 이동"
                >
                  <ExternalLink className="w-4 h-4 text-slate-600 dark:text-slate-400" />
                </a>
              </div>

              {/* 스니펫 - 향상된 디자인 */}
              <div className="bg-slate-50 dark:bg-slate-700/30 rounded-lg p-3 mb-3 border-l-4 border-blue-200 dark:border-blue-700">
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed overflow-hidden"
                   style={{
                     display: '-webkit-box',
                     WebkitLineClamp: 3,
                     WebkitBoxOrient: 'vertical',
                   }}>
                  {result.snippet}
                </p>
              </div>

              {/* 메타데이터 - 향상된 레이아웃 */}
              {showMetadata && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 text-xs">
                    {/* 출처 배지 */}
                    <div className={`flex items-center gap-1 px-2 py-1 rounded-full ${getSourceColor(result.source)}`}>
                      <span>{getSourceIcon(result.source)}</span>
                      <span className="font-medium">
                        {result.source.split('_')[0]?.charAt(0).toUpperCase() + result.source.split('_')[0]?.slice(1)}
                      </span>
                    </div>

                    {/* 프로바이더 정보 */}
                    {result.provider && (
                      <div className="px-2 py-1 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300 rounded-full font-medium">
                        {result.provider}
                      </div>
                    )}
                  </div>
                  
                  {/* 우측 메타 정보 */}
                  <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                    {/* 신뢰도 점수 */}
                    <div className="flex items-center gap-1">
                      <div className={`w-2 h-2 rounded-full ${
                        result.score >= 0.9 ? 'bg-green-500' :
                        result.score >= 0.8 ? 'bg-blue-500' :
                        result.score >= 0.7 ? 'bg-yellow-500' : 'bg-gray-400'
                      }`} />
                      <span className="font-medium">{Math.round(result.score * 100)}%</span>
                    </div>
                    
                    {/* 타임스탬프 */}
                    {result.timestamp && (
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        <span>{new Date(result.timestamp).toLocaleDateString('ko-KR')}</span>
                      </div>
                    )}
                  </div>
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