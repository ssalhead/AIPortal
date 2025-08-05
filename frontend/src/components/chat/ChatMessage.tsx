/**
 * 채팅 메시지 컴포넌트
 */

import React from 'react';

interface ChatMessageProps {
  message: string;
  isUser: boolean;
  timestamp?: string;
  agentType?: string;
  model?: string;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isUser,
  timestamp,
  agentType,
  model,
}) => {
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-white border border-gray-200 text-gray-900'
        }`}
      >
        <div className="text-sm">{message}</div>
        
        {/* 메타데이터 (AI 응답에만 표시) */}
        {!isUser && (agentType || model || timestamp) && (
          <div className="text-xs text-gray-500 mt-2 pt-2 border-t border-gray-100">
            {agentType && (
              <span className="inline-block bg-gray-100 text-gray-600 px-2 py-1 rounded mr-2 mb-1">
                {agentType}
              </span>
            )}
            {model && (
              <span className="inline-block bg-blue-100 text-blue-600 px-2 py-1 rounded mr-2 mb-1">
                {model}
              </span>
            )}
            {timestamp && (
              <div className="text-gray-400 text-xs mt-1">
                {new Date(timestamp).toLocaleTimeString('ko-KR')}
              </div>
            )}
          </div>
        )}
        
        {/* 사용자 메시지 타임스탬프 */}
        {isUser && timestamp && (
          <div className="text-xs text-blue-100 mt-1">
            {new Date(timestamp).toLocaleTimeString('ko-KR')}
          </div>
        )}
      </div>
    </div>
  );
};