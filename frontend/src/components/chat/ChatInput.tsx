/**
 * 채팅 입력 컴포넌트
 */

import React, { useState, useRef, KeyboardEvent } from 'react';
import type { LLMModel, AgentType } from '../../types';

interface ChatInputProps {
  onSendMessage: (message: string, model: LLMModel, agentType: AgentType) => void;
  isLoading?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading = false,
}) => {
  const [message, setMessage] = useState('');
  const [selectedModel, setSelectedModel] = useState<LLMModel>('gemini');
  const [selectedAgent, setSelectedAgent] = useState<AgentType>('web_search');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSendMessage(message.trim(), selectedModel, selectedAgent);
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    
    // 자동 높이 조절
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      {/* 모델 및 에이전트 선택 */}
      <div className="flex space-x-4 mb-3">
        <div className="flex-1">
          <label htmlFor="model-select" className="block text-xs font-medium text-gray-700 mb-1">
            모델 선택
          </label>
          <select
            id="model-select"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value as LLMModel)}
            className="w-full text-sm border border-gray-300 rounded-md px-3 py-1 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            <option value="gemini">Gemini</option>
            <option value="claude">Claude</option>
          </select>
        </div>
        
        <div className="flex-1">
          <label htmlFor="agent-select" className="block text-xs font-medium text-gray-700 mb-1">
            에이전트 선택
          </label>
          <select
            id="agent-select"
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value as AgentType)}
            className="w-full text-sm border border-gray-300 rounded-md px-3 py-1 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            <option value="web_search">웹 검색</option>
            <option value="deep_research">심층 리서치</option>
            <option value="multimodal_rag">멀티모달 RAG</option>
          </select>
        </div>
      </div>

      {/* 메시지 입력 폼 */}
      <form onSubmit={handleSubmit} className="flex space-x-3">
        <div className="flex-1">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="메시지를 입력하세요... (Shift+Enter로 줄바꿈)"
            className="w-full resize-none border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            style={{ minHeight: '40px', maxHeight: '120px' }}
            disabled={isLoading}
          />
        </div>
        
        <button
          type="submit"
          disabled={!message.trim() || isLoading}
          className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors duration-200 flex items-center space-x-2"
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>전송 중...</span>
            </>
          ) : (
            <span>전송</span>
          )}
        </button>
      </form>
    </div>
  );
};