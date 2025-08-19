/**
 * 정보 요청 카드 컴포넌트
 * 사용자에게 추가 정보를 요청할 때 표시되는 인터랙티브 카드
 */

import React, { useState } from 'react';
import type { InformationGap } from '../../types';

interface InformationRequestCardProps {
  gaps: InformationGap[];
  onSubmitInfo: (answers: Record<string, string>) => void;
  onSkip?: () => void;
  className?: string;
}

export const InformationRequestCard: React.FC<InformationRequestCardProps> = ({
  gaps,
  onSubmitInfo,
  onSkip,
  className = '',
}) => {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [selectedSuggestions, setSelectedSuggestions] = useState<Record<string, string>>({});

  const criticalGaps = gaps.filter(gap => gap.urgency === 'critical' || gap.urgency === 'high');
  const optionalGaps = gaps.filter(gap => gap.urgency === 'medium' || gap.urgency === 'low');

  const handleAnswerChange = (field: string, value: string) => {
    setAnswers(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSuggestionClick = (field: string, suggestion: string) => {
    const currentValue = answers[field] || '';
    const newValue = currentValue ? `${currentValue}, ${suggestion}` : suggestion;
    handleAnswerChange(field, newValue);
    
    setSelectedSuggestions(prev => ({
      ...prev,
      [field]: suggestion
    }));
  };

  const handleSubmit = () => {
    // 필수 정보가 모두 입력되었는지 확인
    const missingCritical = criticalGaps.filter(gap => !answers[gap.field]?.trim());
    
    if (missingCritical.length > 0) {
      alert('필수 정보를 모두 입력해주세요.');
      return;
    }

    onSubmitInfo(answers);
  };

  const canSkip = criticalGaps.length === 0;

  const getUrgencyIcon = (urgency: string) => {
    switch (urgency) {
      case 'critical': return '🔴';
      case 'high': return '🟡';
      case 'medium': return '🟠';
      case 'low': return '⚪';
      default: return '❓';
    }
  };

  const getUrgencyLabel = (urgency: string) => {
    switch (urgency) {
      case 'critical': return '필수';
      case 'high': return '중요';
      case 'medium': return '권장';
      case 'low': return '선택';
      default: return '기타';
    }
  };

  return (
    <div className={`bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 ${className}`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-blue-600 text-lg">💡</span>
        <h3 className="text-blue-800 font-semibold">추가 정보가 필요합니다</h3>
      </div>

      <p className="text-blue-700 text-sm mb-4">
        더 정확하고 유용한 답변을 제공하기 위해 몇 가지 정보를 알려주세요.
      </p>

      <div className="space-y-4">
        {/* 필수 정보 */}
        {criticalGaps.length > 0 && (
          <div>
            <h4 className="font-medium text-red-700 mb-2 flex items-center gap-1">
              🔴 필수 정보
            </h4>
            {criticalGaps.map((gap, index) => (
              <div key={`critical-${index}`} className="mb-3 p-3 bg-red-50 border border-red-200 rounded">
                <div className="flex items-center gap-2 mb-2">
                  <span>{getUrgencyIcon(gap.urgency)}</span>
                  <label className="font-medium text-red-800">
                    {gap.question}
                  </label>
                  <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                    {getUrgencyLabel(gap.urgency)}
                  </span>
                </div>
                
                {gap.description && (
                  <p className="text-sm text-red-600 mb-2">{gap.description}</p>
                )}

                <input
                  type="text"
                  value={answers[gap.field] || ''}
                  onChange={(e) => handleAnswerChange(gap.field, e.target.value)}
                  placeholder={gap.context_hint || '정보를 입력해주세요'}
                  className="w-full p-2 border border-red-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                />

                {gap.suggestions.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-red-600 mb-1">제안사항:</p>
                    <div className="flex flex-wrap gap-1">
                      {gap.suggestions.map((suggestion, suggIndex) => (
                        <button
                          key={suggIndex}
                          onClick={() => handleSuggestionClick(gap.field, suggestion)}
                          className={`px-2 py-1 text-xs rounded border ${
                            selectedSuggestions[gap.field] === suggestion
                              ? 'bg-red-200 border-red-400 text-red-800'
                              : 'bg-white border-red-300 text-red-700 hover:bg-red-100'
                          }`}
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* 선택적 정보 */}
        {optionalGaps.length > 0 && (
          <div>
            <h4 className="font-medium text-blue-700 mb-2 flex items-center gap-1">
              💙 선택적 정보 (더 나은 결과를 위해)
            </h4>
            {optionalGaps.map((gap, index) => (
              <div key={`optional-${index}`} className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded">
                <div className="flex items-center gap-2 mb-2">
                  <span>{getUrgencyIcon(gap.urgency)}</span>
                  <label className="font-medium text-blue-800">
                    {gap.question}
                  </label>
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                    {getUrgencyLabel(gap.urgency)}
                  </span>
                </div>
                
                {gap.description && (
                  <p className="text-sm text-blue-600 mb-2">{gap.description}</p>
                )}

                <input
                  type="text"
                  value={answers[gap.field] || ''}
                  onChange={(e) => handleAnswerChange(gap.field, e.target.value)}
                  placeholder={gap.context_hint || '선택사항입니다'}
                  className="w-full p-2 border border-blue-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />

                {gap.suggestions.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-blue-600 mb-1">제안사항:</p>
                    <div className="flex flex-wrap gap-1">
                      {gap.suggestions.map((suggestion, suggIndex) => (
                        <button
                          key={suggIndex}
                          onClick={() => handleSuggestionClick(gap.field, suggestion)}
                          className={`px-2 py-1 text-xs rounded border ${
                            selectedSuggestions[gap.field] === suggestion
                              ? 'bg-blue-200 border-blue-400 text-blue-800'
                              : 'bg-white border-blue-300 text-blue-700 hover:bg-blue-100'
                          }`}
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 액션 버튼 */}
      <div className="flex gap-2 mt-4">
        <button
          onClick={handleSubmit}
          disabled={criticalGaps.some(gap => !answers[gap.field]?.trim())}
          className="flex-1 bg-blue-600 text-white px-4 py-2 rounded font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          정보 제공하고 계속하기
        </button>
        
        {canSkip && onSkip && (
          <button
            onClick={onSkip}
            className="px-4 py-2 border border-blue-300 text-blue-700 rounded hover:bg-blue-50 transition-colors"
          >
            현재 정보로 진행
          </button>
        )}
      </div>

      <div className="mt-2 text-xs text-blue-600">
        💡 제공해주신 정보는 더 정확한 답변을 위해서만 사용됩니다.
      </div>
    </div>
  );
};

export default InformationRequestCard;