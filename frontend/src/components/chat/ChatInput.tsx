/**
 * 채팅 입력 컴포넌트 - Gemini 스타일
 */

import React, { useState, useRef, useMemo } from 'react';
import type { LLMModel, AgentType, LLMProvider } from '../../types';
import { MODEL_MAP, AGENT_TYPE_MAP } from '../../types';
import { useLoading } from '../../contexts/LoadingContext';
import { useResponsive } from '../../hooks/useResponsive';
import { Send, Paperclip, ChevronDown, Star, Zap, X } from 'lucide-react';
import { fileService } from '../../services/fileService';

interface ChatInputProps {
  onSendMessage: (message: string, model: LLMModel, agentType: AgentType) => void;
  isLoading?: boolean;
  placeholder?: string;
  selectedProvider: LLMProvider;
  selectedModel: LLMModel;
  selectedAgent: AgentType;
  onProviderChange: (provider: LLMProvider) => void;
  onModelChange: (model: LLMModel) => void;
  onAgentChange: (agent: AgentType) => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading = false,
  placeholder = "메시지를 입력하세요... (Shift+Enter로 줄바꿈)",
  selectedProvider,
  selectedModel,
  selectedAgent,
  onProviderChange,
  onModelChange,
  onAgentChange,
}) => {
  const { isTyping } = useLoading();
  const { isMobile } = useResponsive();
  const [message, setMessage] = useState('');
  const [showModelSelector, setShowModelSelector] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownButtonRef = useRef<HTMLButtonElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // 모바일용 플레이스홀더
  const mobilePlaceholder = isMobile ? "메시지 입력..." : placeholder;

  // 선택된 제공업체의 모델 목록 계산
  const availableModels = useMemo(() => {
    return MODEL_MAP[selectedProvider] || [];
  }, [selectedProvider]);

  // 제공업체 변경 시 첫 번째 모델로 자동 설정
  const handleProviderChange = (provider: LLMProvider) => {
    onProviderChange(provider);
    const firstModel = MODEL_MAP[provider]?.[0];
    if (firstModel) {
      onModelChange(firstModel.id);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((message.trim() || attachedFiles.length > 0) && !isLoading && !isTyping) {
      let messageToSend = message.trim();
      
      // 파일이 첨부된 경우 파일 업로드 먼저 수행
      if (attachedFiles.length > 0) {
        try {
          const uploadResults = await fileService.uploadFiles(attachedFiles);
          const fileList = uploadResults.map(result => 
            `📎 ${result.original_name} (${fileService.formatFileSize(result.file_size)})`
          ).join('\n');
          
          messageToSend = messageToSend 
            ? `${messageToSend}\n\n첨부 파일:\n${fileList}`
            : `첨부 파일:\n${fileList}`;
          
          setAttachedFiles([]);
        } catch (error) {
          console.error('파일 업로드 실패:', error);
          alert('파일 업로드에 실패했습니다.');
          return;
        }
      }
      
      onSendMessage(messageToSend, selectedModel, selectedAgent);
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
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

  // 파일 선택 핸들러
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const newFiles = Array.from(files);
      setAttachedFiles(prev => [...prev, ...newFiles]);
    }
    // 입력 값 리셋
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // 파일 제거 핸들러
  const removeFile = (index: number) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index));
  };

  // 파일 첨부 버튼 클릭
  const handleAttachClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div className="px-6 py-3">
      {/* 선택된 모델 정보 및 기능 정보 - 컴팩한 표시 */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-4">
            {/* 모델 표시 */}
            <div className="flex items-center space-x-2">
              {selectedProvider === 'claude' ? (
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 rounded-full text-sm font-medium">
                  <Star className="w-3.5 h-3.5" />
                  <span>Claude</span>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium">
                  <Zap className="w-3.5 h-3.5" />
                  <span>Gemini</span>
                </div>
              )}
              
              {/* 에이전트 표시 */}
              {selectedAgent && selectedAgent !== 'none' && (
                <div className={`px-3 py-1.5 rounded-full text-sm font-medium ${
                  selectedAgent === 'web_search' 
                    ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300'
                    : selectedAgent === 'deep_research'
                    ? 'bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300'
                    : 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300'
                }`}>
                  {AGENT_TYPE_MAP[selectedAgent]?.name}
                </div>
              )}
            </div>
          </div>
          
          {/* 상태 표시 */}
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              isTyping ? 'bg-amber-400 animate-pulse' : 'bg-green-400'
            }`}></div>
            <span className="text-slate-500 dark:text-slate-400 text-sm">
              {isTyping ? 'AI 응답 중...' : '대화 준비됨'}
            </span>
          </div>
        </div>
      </div>

      {/* 첨부된 파일 미리보기 */}
      {attachedFiles.length > 0 && (
        <div className="mb-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              첨부 파일 ({attachedFiles.length})
            </span>
          </div>
          
          <div className="space-y-2">
            {attachedFiles.map((file, index) => (
              <div key={index} className="flex items-center justify-between bg-white dark:bg-slate-700 rounded-md p-2">
                <div className="flex items-center space-x-2 flex-1 min-w-0">
                  <Paperclip className="w-4 h-4 text-slate-400 flex-shrink-0" />
                  <span className="text-sm text-slate-700 dark:text-slate-300 truncate">
                    {file.name}
                  </span>
                  <span className="text-xs text-slate-500 dark:text-slate-400 flex-shrink-0">
                    ({fileService.formatFileSize(file.size)})
                  </span>
                </div>
                
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  className="text-slate-400 hover:text-red-500 transition-colors flex-shrink-0 ml-2"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 메시지 입력 영역 - Gemini 스타일 */}
      <form onSubmit={handleSubmit}>
        <div className="relative bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-all duration-200 focus-within:border-primary-500 dark:focus-within:border-primary-400 focus-within:ring-4 focus-within:ring-primary-500/10">
          {/* 텍스트 입력 */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder={isTyping ? 'AI가 생각 중입니다...' : '무엇이든 물어보세요...'}
            className="w-full px-6 py-4 text-slate-900 dark:text-slate-100 bg-transparent border-none resize-none focus:outline-none placeholder:text-slate-400 dark:placeholder:text-slate-500 pr-20"
            style={{ 
              minHeight: '56px', 
              maxHeight: '200px',
              fontSize: '16px',
              lineHeight: '1.5'
            }}
            disabled={isLoading || isTyping}
          />

          {/* 하단 액션 바 */}
          <div className={`flex items-center justify-between ${
            isMobile ? 'px-3 py-2' : 'px-4 py-3'
          } border-t border-slate-100 dark:border-slate-700`}>
            {/* 왼쪽: 도구들 */}
            <div className={`flex items-center ${isMobile ? 'space-x-1' : 'space-x-2'}`}>
              {/* 파일 업로드 버튼 - 모바일에서는 숨김 */}
              {!isMobile && (
                <button
                  type="button"
                  onClick={handleAttachClick}
                  className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition-all duration-200"
                  disabled={isLoading || isTyping}
                  title="파일 첨부"
                >
                  <Paperclip className="w-5 h-5" />
                </button>
              )}
              
              {/* 모델/기능 선택 버튼 */}
              <div className="relative">
                <button
                  type="button"
                  ref={dropdownButtonRef}
                  onClick={() => setShowModelSelector(!showModelSelector)}
                  className={`flex items-center space-x-2 ${
                    isMobile ? 'px-2 py-1' : 'px-3 py-1.5'
                  } text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition-all duration-200 ${
                    isMobile ? 'text-xs' : 'text-sm'
                  }`}
                  title="모델 및 기능 선택"
                >
                  <span>{isMobile ? 'AI' : 'AI 설정'}</span>
                  <ChevronDown className={`${isMobile ? 'w-3 h-3' : 'w-4 h-4'} transition-transform ${showModelSelector ? 'rotate-180' : ''}`} />
                </button>
                
                {/* 모델 선택 드롭다운 */}
                {showModelSelector && (
                  <div className={`absolute bottom-full mb-2 ${
                    isMobile ? 'right-0 left-0' : 'right-0'
                  } bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 ${
                    isMobile ? 'p-3' : 'p-4'
                  } ${
                    isMobile ? 'w-full' : 'w-80'
                  } z-50 max-h-96 overflow-y-auto`}
                >
                  <div className="space-y-4">
                      {/* Provider 선택 */}
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          AI 모델
                        </label>
                        <div className="flex bg-slate-100 dark:bg-slate-700 p-1 rounded-xl">
                          <button
                            type="button"
                            onClick={() => handleProviderChange('claude')}
                            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                              selectedProvider === 'claude'
                                ? 'bg-white dark:bg-slate-600 text-orange-700 dark:text-orange-300 shadow-sm' 
                                : 'text-slate-600 dark:text-slate-400'
                            }`}
                          >
                            <Star className="w-4 h-4" />
                            Claude
                          </button>
                          <button
                            type="button"
                            onClick={() => handleProviderChange('gemini')}
                            className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                              selectedProvider === 'gemini'
                                ? 'bg-white dark:bg-slate-600 text-blue-700 dark:text-blue-300 shadow-sm' 
                                : 'text-slate-600 dark:text-slate-400'
                            }`}
                          >
                            <Zap className="w-4 h-4" />
                            Gemini
                          </button>
                        </div>
                      </div>

                      {/* 모델 상세 선택 */}
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          모델 버전
                        </label>
                        <div className="space-y-2">
                          {availableModels.map((model) => (
                            <button
                              key={model.id}
                              type="button"
                              onClick={() => onModelChange(model.id)}
                              className={`w-full text-left p-3 rounded-xl transition-all ${
                                selectedModel === model.id
                                  ? 'bg-primary-50 dark:bg-primary-900/20 border-2 border-primary-200 dark:border-primary-700'
                                  : 'bg-slate-50 dark:bg-slate-700/50 border-2 border-transparent hover:border-slate-200 dark:hover:border-slate-600'
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-slate-900 dark:text-slate-100">
                                  {model.name}
                                </span>
                                <div className="flex items-center space-x-1">
                                  {model.isRecommended && <Star className="w-4 h-4 text-amber-500" />}
                                  {model.speed === 'fast' && <Zap className="w-4 h-4 text-green-500" />}
                                </div>
                              </div>
                              <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                                {model.description}
                              </p>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* 기능 선택 */}
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          기능 (선택사항)
                        </label>
                        <div className="grid grid-cols-2 gap-2">
                          {Object.values(AGENT_TYPE_MAP).map((agent) => (
                            <button
                              key={agent.id}
                              type="button"
                              onClick={() => onAgentChange(agent.id)}
                              className={`p-3 rounded-xl text-left transition-all ${
                                selectedAgent === agent.id
                                  ? 'bg-primary-50 dark:bg-primary-900/20 border-2 border-primary-200 dark:border-primary-700'
                                  : 'bg-slate-50 dark:bg-slate-700/50 border-2 border-transparent hover:border-slate-200 dark:hover:border-slate-600'
                              }`}
                            >
                              <div className="flex items-center space-x-2 mb-1">
                                <span className="text-lg">{agent.icon}</span>
                                <span className="font-medium text-sm text-slate-900 dark:text-slate-100">
                                  {agent.name}
                                </span>
                              </div>
                              <p className="text-xs text-slate-600 dark:text-slate-400">
                                {agent.description}
                              </p>
                            </button>
                          ))}
                        </div>
                      </div>
                      
                      {/* 닫기 버튼 */}
                      <div className="pt-2 border-t border-slate-200 dark:border-slate-700">
                        <button
                          type="button"
                          onClick={() => setShowModelSelector(false)}
                          className="w-full bg-primary-600 hover:bg-primary-700 text-white py-2 px-4 rounded-xl transition-all duration-200 text-sm font-medium"
                        >
                          설정 완료
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            {/* 오른쪽: 전송 버튼 및 정보 */}
            <div className="flex items-center space-x-3">
              {/* 글자 수 표시 */}
              {message.length > 0 && (
                <span className="text-xs text-slate-400 dark:text-slate-500">
                  {message.length}자
                </span>
              )}
              
              {/* 전송 버튼 */}
              <button
                type="submit"
                disabled={!message.trim() || isLoading || isTyping}
                className={`p-2.5 rounded-xl transition-all duration-200 ${
                  message.trim() && !isLoading && !isTyping
                    ? 'bg-primary-600 hover:bg-primary-700 dark:bg-primary-700 dark:hover:bg-primary-600 text-white shadow-lg hover:shadow-xl hover:scale-105 active:scale-95' 
                    : 'bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed'
                }`}
                title="메시지 전송 (Enter)"
              >
                {(isLoading || isTyping) ? (
                  <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
        </div>
        
        {/* 도움말 텍스트 - 컴팩트 버전 */}
        <div className="flex items-center justify-center mt-2 text-xs text-slate-400 dark:text-slate-500 space-x-3">
          <span>Enter로 전송</span>
          <div className="w-0.5 h-0.5 bg-slate-300 dark:bg-slate-600 rounded-full"></div>
          <span>Shift+Enter로 줄바꿈</span>
        </div>
      </form>
      
      {/* 숨겨진 파일 입력 */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".txt,.pdf,.docx,.xlsx,.xls,.csv,.jpg,.jpeg,.png,.gif,.webp,.json,.md,.html,.py,.js,.ts"
        onChange={handleFileSelect}
        className="hidden"
      />
      
      {/* 모델/기능 선택 모달 - 필요시 추가 */}
      {/* TODO: 모델 선택 모달 구현 */}
    </div>
  );
};