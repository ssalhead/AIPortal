/**
 * 인용 정보 표시 컴포넌트
 */

import React, { useState } from 'react';
import type { Citation, Source } from '../../types';

// 컴포넌트용 타입 별칭
export type CitationData = Citation;
export type SourceData = Source;

interface CitationProps {
  citation: CitationData;
  source: SourceData;
  index: number;
  showTooltip?: boolean;
}

export const Citation: React.FC<CitationProps> = ({
  citation,
  source,
  index,
  showTooltip = true,
}) => {
  const [showDetails, setShowDetails] = useState(false);

  const getReliabilityColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600 bg-green-50 border-green-200';
    if (score >= 0.6) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-red-600 bg-red-50 border-red-200';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('ko-KR');
  };

  return (
    <span className="relative inline-block">
      <sup
        className="inline-flex items-center px-1 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded-full cursor-pointer hover:bg-blue-200 transition-colors"
        onClick={() => setShowDetails(!showDetails)}
        onMouseEnter={() => showTooltip && setShowDetails(true)}
        onMouseLeave={() => showTooltip && setShowDetails(false)}
      >
        {index}
      </sup>

      {/* 인용 세부 정보 툴팁 */}
      {showDetails && (
        <div className="absolute z-10 bottom-full left-0 mb-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg p-4">
          {/* 헤더 */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-gray-900 line-clamp-2">
                {source.title}
              </h4>
              {source.domain && (
                <p className="text-xs text-gray-500 mt-1">{source.domain}</p>
              )}
            </div>
            <button
              onClick={() => setShowDetails(false)}
              className="text-gray-400 hover:text-gray-600 ml-2"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>

          {/* 설명 */}
          {source.description && (
            <p className="text-xs text-gray-700 mb-3 line-clamp-3">
              {source.description}
            </p>
          )}

          {/* 메타데이터 */}
          <div className="space-y-2 mb-3">
            {source.author && (
              <div className="flex items-center text-xs text-gray-600">
                <span className="font-medium">저자:</span>
                <span className="ml-1">{source.author}</span>
              </div>
            )}
            
            {source.publishedDate && (
              <div className="flex items-center text-xs text-gray-600">
                <span className="font-medium">발행일:</span>
                <span className="ml-1">{formatDate(source.publishedDate)}</span>
              </div>
            )}

            <div className="flex items-center text-xs text-gray-600">
              <span className="font-medium">접근일:</span>
              <span className="ml-1">{formatDate(source.accessedDate)}</span>
            </div>
          </div>

          {/* 신뢰도 및 신뢰도 점수 */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getReliabilityColor(source.reliabilityScore)}`}>
                신뢰도: {Math.round(source.reliabilityScore * 100)}%
              </span>
              <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700">
                {source.sourceType}
              </span>
            </div>
          </div>

          {/* 인용 신뢰도 */}
          <div className="flex items-center mb-3">
            <span className="text-xs font-medium text-gray-700 mr-2">인용 정확도:</span>
            <div className="flex-1 bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${getConfidenceColor(citation.confidence)}`}
                style={{ width: `${citation.confidence * 100}%` }}
              />
            </div>
            <span className="text-xs text-gray-600 ml-2">
              {Math.round(citation.confidence * 100)}%
            </span>
          </div>

          {/* 인용 맥락 */}
          {citation.context && (
            <div className="mb-3">
              <p className="text-xs font-medium text-gray-700 mb-1">인용 맥락:</p>
              <p className="text-xs text-gray-600 bg-gray-50 p-2 rounded italic">
                "{citation.context}"
              </p>
            </div>
          )}

          {/* 링크 */}
          {source.url && (
            <div className="pt-3 border-t border-gray-100">
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                원문 보기
                <svg className="w-3 h-3 ml-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </a>
            </div>
          )}
        </div>
      )}
    </span>
  );
};

/**
 * 인용 미리보기 컴포넌트 (호버시 간단한 정보만 표시)
 */
interface CitationPreviewProps {
  citation: CitationData;
  source: SourceData;
  index: number;
}

export const CitationPreview: React.FC<CitationPreviewProps> = ({
  citation,
  source,
  index,
}) => {
  return (
    <span className="group relative">
      <sup className="inline-flex items-center px-1 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded-full cursor-pointer hover:bg-blue-200 transition-colors">
        {index}
      </sup>
      
      {/* 간단한 미리보기 툴팁 */}
      <div className="absolute z-10 bottom-full left-0 mb-1 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
        <div className="bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap">
          {source.title}
        </div>
        <div className="absolute top-full left-2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
      </div>
    </span>
  );
};