/**
 * 검색 진행 상태 표시 컴포넌트
 */

import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Brain, 
  Zap, 
  Globe, 
  Filter, 
  Trophy,
  CheckCircle, 
  Circle,
  Loader2,
  Clock,
  Target
} from 'lucide-react';

export interface SearchStep {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  startTime?: Date;
  endTime?: Date;
  progress?: number; // 0-100
  details?: string[];
  metadata?: Record<string, any>;
}

interface SearchProgressIndicatorProps {
  steps: SearchStep[];
  isVisible: boolean;
  onClose?: () => void;
  showDetails?: boolean;
  compact?: boolean;
  // 맥락 통합 정보 추가
  originalQuery?: string;
  contextIntegratedQuery?: string;
  hasContext?: boolean;
}

export const SearchProgressIndicator: React.FC<SearchProgressIndicatorProps> = ({
  steps,
  isVisible,
  onClose,
  showDetails = false,
  compact = false,
  originalQuery,
  contextIntegratedQuery,
  hasContext = false
}) => {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  useEffect(() => {
    // 진행 중인 단계는 자동으로 확장
    const inProgressSteps = steps
      .filter(step => step.status === 'in_progress')
      .map(step => step.id);
    
    setExpandedSteps(new Set(inProgressSteps));
  }, [steps]);

  if (!isVisible) return null;

  const getStepIcon = (step: SearchStep) => {
    const iconProps = { className: "w-4 h-4" };
    
    switch (step.id) {
      case 'query_analysis':
        return <Brain {...iconProps} />;
      case 'query_generation':
        return <Zap {...iconProps} />;
      case 'parallel_search':
        return <Globe {...iconProps} />;
      case 'result_filtering':
        return <Filter {...iconProps} />;
      case 'result_ranking':
        return <Trophy {...iconProps} />;
      case 'response_generation':
        return <Target {...iconProps} />;
      default:
        return <Search {...iconProps} />;
    }
  };

  const getStatusIcon = (status: SearchStep['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'in_progress':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'error':
        return <Circle className="w-4 h-4 text-red-500" />;
      default:
        return <Circle className="w-4 h-4 text-gray-300" />;
    }
  };

  const getStepDuration = (step: SearchStep): string => {
    if (!step.startTime) return '';
    
    const endTime = step.endTime || new Date();
    const duration = endTime.getTime() - step.startTime.getTime();
    
    if (duration < 1000) return `${duration}ms`;
    return `${(duration / 1000).toFixed(1)}s`;
  };

  const totalSteps = steps.length;
  const completedSteps = steps.filter(s => s.status === 'completed').length;
  const overallProgress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;

  const toggleStepExpansion = (stepId: string) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId);
    } else {
      newExpanded.add(stepId);
    }
    setExpandedSteps(newExpanded);
  };

  if (compact) {
    // 컴팩트 모드: 한 줄 진행률만 표시
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-3 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Search className="w-4 h-4 text-blue-500" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              검색 진행 중...
            </span>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {completedSteps}/{totalSteps}
            </span>
            <div className="w-16 h-1 bg-gray-200 dark:bg-gray-700 rounded-full">
              <div 
                className="h-1 bg-blue-500 rounded-full transition-all duration-300"
                style={{ width: `${overallProgress}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
      {/* 헤더 */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Search className="w-5 h-5 text-blue-500" />
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                검색 진행 상황
              </h3>
              <div className="flex items-center gap-2">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {completedSteps}/{totalSteps} 단계 완료
                </p>
                {hasContext && (
                  <div className="flex items-center gap-1">
                    <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-md text-xs font-medium">
                      맥락 통합
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {onClose && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
            >
              ✕
            </button>
          )}
        </div>
        
        {/* 전체 진행률 */}
        <div className="mt-3">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
            <span>전체 진행률</span>
            <span>{Math.round(overallProgress)}%</span>
          </div>
          <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full">
            <div 
              className="h-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-500"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
        </div>

        {/* 맥락 통합 정보 */}
        {hasContext && originalQuery && contextIntegratedQuery && (
          <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                맥락 통합 검색
              </span>
            </div>
            <div className="text-xs space-y-1">
              <div>
                <span className="text-gray-600 dark:text-gray-400">원본:</span>{' '}
                <span className="text-gray-800 dark:text-gray-200">"{originalQuery}"</span>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">통합:</span>{' '}
                <span className="text-blue-700 dark:text-blue-300 font-medium">"{contextIntegratedQuery}"</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 단계별 진행 상황 */}
      <div className="p-4 space-y-3">
        {steps.map((step, index) => (
          <div key={step.id} className="border border-gray-100 dark:border-gray-700 rounded-lg">
            <div 
              className={`
                p-3 cursor-pointer transition-colors
                ${showDetails ? 'hover:bg-gray-50 dark:hover:bg-gray-750' : ''}
              `}
              onClick={() => showDetails && toggleStepExpansion(step.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    {getStatusIcon(step.status)}
                  </div>
                  
                  <div className="flex items-center space-x-2 text-gray-500 dark:text-gray-400">
                    {getStepIcon(step)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {step.name}
                      </h4>
                      
                      {step.status === 'in_progress' && step.progress !== undefined && (
                        <span className="text-xs text-blue-600 dark:text-blue-400">
                          {step.progress}%
                        </span>
                      )}
                    </div>
                    
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                      {step.description}
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                  {step.startTime && (
                    <div className="flex items-center space-x-1">
                      <Clock className="w-3 h-3" />
                      <span>{getStepDuration(step)}</span>
                    </div>
                  )}
                  
                  {showDetails && (
                    <span className="text-gray-400">
                      {expandedSteps.has(step.id) ? '▼' : '▶'}
                    </span>
                  )}
                </div>
              </div>
              
              {/* 단계별 진행률 */}
              {step.status === 'in_progress' && step.progress !== undefined && (
                <div className="mt-2">
                  <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full">
                    <div 
                      className="h-1 bg-blue-500 rounded-full transition-all duration-300"
                      style={{ width: `${step.progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
            
            {/* 상세 정보 */}
            {showDetails && expandedSteps.has(step.id) && step.details && (
              <div className="px-3 pb-3 border-t border-gray-100 dark:border-gray-700">
                <div className="pt-2 space-y-1">
                  {step.details.map((detail, detailIndex) => (
                    <div 
                      key={detailIndex}
                      className="text-xs text-gray-600 dark:text-gray-400 pl-6"
                    >
                      • {detail}
                    </div>
                  ))}
                </div>
                
                {/* 메타데이터 */}
                {step.metadata && Object.keys(step.metadata).length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700">
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {Object.entries(step.metadata).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-gray-500 dark:text-gray-400">{key}:</span>
                          <span className="text-gray-700 dark:text-gray-300">
                            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};