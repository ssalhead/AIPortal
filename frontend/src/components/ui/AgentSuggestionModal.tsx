/**
 * 에이전트 제안 모달 컴포넌트
 */

import React from 'react';
import { Bot, ArrowRight, X, Sparkles } from 'lucide-react';
import type { AgentType } from '../../types';
import { AGENT_TYPE_MAP } from '../../types';

interface AgentSuggestion {
  suggested_agent: AgentType;
  reason: string;
  confidence: number;
  current_agent: AgentType;
}

interface AgentSuggestionModalProps {
  suggestion: AgentSuggestion;
  onAccept: () => void;
  onDecline: () => void;
  isVisible: boolean;
}

export const AgentSuggestionModal: React.FC<AgentSuggestionModalProps> = ({
  suggestion,
  onAccept,
  onDecline,
  isVisible
}) => {
  if (!isVisible) return null;

  const currentAgentInfo = AGENT_TYPE_MAP[suggestion.current_agent];
  const suggestedAgentInfo = AGENT_TYPE_MAP[suggestion.suggested_agent];
  
  // 신뢰도에 따른 색상 결정
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 dark:text-green-400';
    if (confidence >= 0.6) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-orange-600 dark:text-orange-400';
  };

  const getConfidenceText = (confidence: number) => {
    if (confidence >= 0.8) return '매우 높음';
    if (confidence >= 0.6) return '높음';
    return '보통';
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-md w-full mx-4 
        transform transition-all duration-300 scale-100 opacity-100">
        
        {/* 헤더 */}
        <div className="p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900/20 
                flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  더 나은 도구 제안
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  AI가 분석한 추천 사항
                </p>
              </div>
            </div>
            <button
              onClick={onDecline}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 
                transition-colors text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* 본문 */}
        <div className="p-6 space-y-4">
          {/* 제안 이유 */}
          <div className="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4">
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
              {suggestion.reason}
            </p>
          </div>

          {/* 에이전트 전환 시각화 */}
          <div className="flex items-center space-x-3">
            {/* 현재 에이전트 */}
            <div className="flex-1 text-center">
              <div className="text-2xl mb-2">{currentAgentInfo.icon}</div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {currentAgentInfo.name}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                현재 사용 중
              </p>
            </div>

            {/* 화살표 */}
            <div className="flex-shrink-0">
              <ArrowRight className="w-6 h-6 text-blue-500" />
            </div>

            {/* 제안 에이전트 */}
            <div className="flex-1 text-center">
              <div className="text-2xl mb-2">{suggestedAgentInfo.icon}</div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                {suggestedAgentInfo.name}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                제안됨
              </p>
            </div>
          </div>

          {/* 신뢰도 표시 */}
          <div className="flex items-center justify-between bg-slate-50 dark:bg-slate-700/50 rounded-lg p-3">
            <span className="text-sm text-slate-600 dark:text-slate-400">
              제안 신뢰도
            </span>
            <div className="flex items-center space-x-2">
              <div className="flex-1 bg-slate-200 dark:bg-slate-600 rounded-full h-2 w-16">
                <div 
                  className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${suggestion.confidence * 100}%` }}
                />
              </div>
              <span className={`text-sm font-medium ${getConfidenceColor(suggestion.confidence)}`}>
                {getConfidenceText(suggestion.confidence)}
              </span>
            </div>
          </div>
        </div>

        {/* 액션 버튼 */}
        <div className="p-6 pt-0 flex space-x-3">
          <button
            onClick={onDecline}
            className="flex-1 px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 
              text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 
              transition-colors font-medium"
          >
            현재 도구 유지
          </button>
          <button
            onClick={onAccept}
            className="flex-1 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 
              text-white transition-colors font-medium shadow-lg hover:shadow-xl"
          >
            {suggestedAgentInfo.name} 사용
          </button>
        </div>
      </div>
    </div>
  );
};