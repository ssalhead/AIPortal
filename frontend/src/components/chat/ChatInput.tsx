/**
 * 채팅 입력 컴포넌트 - Gemini 스타일
 */

import React, { useState, useRef, useMemo, useEffect } from 'react';
import type { LLMModel, AgentType, LLMProvider } from '../../types';
import { MODEL_MAP, AGENT_TYPE_MAP } from '../../types';
import { useLoading } from '../../contexts/LoadingContext';
import { useResponsive } from '../../hooks/useResponsive';
import { Send, Paperclip, ChevronDown, Star, Zap, X } from '../ui/Icons';
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
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // 모바일용 플레이스홀더
  const mobilePlaceholder = isMobile ? "메시지 입력..." : placeholder;

  // 선택된 제공업체의 모델 목록 계산
  const availableModels = useMemo(() => {
    return MODEL_MAP[selectedProvider] || [];
  }, [selectedProvider]);

  // 전체 모델 목록 (Claude + Gemini 통합)
  const allModels = useMemo(() => {
    return [...MODEL_MAP.claude, ...MODEL_MAP.gemini];
  }, []);

  // 현재 선택된 모델 정보
  const currentModel = useMemo(() => {
    return allModels.find(model => model.id === selectedModel);
  }, [allModels, selectedModel]);

  // 제공업체 변경 시 첫 번째 모델로 자동 설정
  const handleProviderChange = (provider: LLMProvider) => {
    onProviderChange(provider);
    const firstModel = MODEL_MAP[provider]?.[0];
    if (firstModel) {
      onModelChange(firstModel.id);
    }
  };

  // 모델 변경 시 자동으로 Provider도 변경
  const handleModelChange = (modelId: LLMModel) => {
    const model = allModels.find(m => m.id === modelId);
    if (model && model.provider !== selectedProvider) {
      onProviderChange(model.provider);
    }
    onModelChange(modelId);
    setShowModelDropdown(false);
  };

  // 에이전트 토글 핸들러 (단일 선택, 같은 것 클릭시 해제)
  const handleAgentToggle = (agentType: AgentType) => {
    // Canvas 버튼은 특별 처리 - 빈 Canvas 열기 차단
    if (agentType === 'canvas') {
      handleCanvasAction();
      return;
    }
    
    if (selectedAgent === agentType) {
      onAgentChange('none'); // 같은 버튼 클릭시 해제
    } else {
      onAgentChange(agentType); // 다른 버튼 클릭시 변경
    }
  };
  
  // Canvas 버튼 클릭 처리 - 빈 Canvas 대신 안내 또는 최근 작업 표시
  const handleCanvasAction = () => {
    // 현재는 안내 메시지만 표시 (향후 Canvas 히스토리 모달로 확장 가능)
    alert('Canvas는 AI가 시각적 콘텐츠를 생성할 때 자동으로 활성화됩니다.\n\n예시: "고양이 그려줘", "마인드맵 만들어줘"');
  };

  // 외부 클릭시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(event.target as Node)) {
        setShowModelDropdown(false);
      }
    };

    if (showModelDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [showModelDropdown]);

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
      {/* AI 상태 표시 */}
      <div className="mb-3 flex justify-end">
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${
            isTyping ? 'bg-amber-400 animate-pulse' : 'bg-green-400'
          }`}></div>
          <span className="text-slate-500 dark:text-slate-400 text-sm">
            {isTyping ? 'AI 응답 중...' : '대화 준비됨'}
          </span>
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
              
              {/* 모델 선택 드롭다운 */}
              <div className="relative" ref={modelDropdownRef}>
                <button
                  type="button"
                  onClick={() => setShowModelDropdown(!showModelDropdown)}
                  className={`flex items-center space-x-2 ${
                    isMobile ? 'px-2 py-1' : 'px-3 py-1.5'
                  } text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition-all duration-200 ${
                    isMobile ? 'text-xs' : 'text-sm'
                  }`}
                  title="모델 선택"
                >
                  {/* Provider 아이콘 */}
                  {currentModel?.provider === 'claude' ? (
                    <Star className="w-4 h-4 text-orange-500" />
                  ) : (
                    <Zap className="w-4 h-4 text-blue-500" />
                  )}
                  <span className="hidden sm:inline">{currentModel?.name?.replace(/Claude |Gemini /, '') || 'Model'}</span>
                  <ChevronDown className={`w-3 h-3 transition-transform ${
                    showModelDropdown ? 'rotate-180' : ''
                  }`} />
                </button>

                {/* 모델 드롭다운 메뉴 */}
                {showModelDropdown && (
                  <div className={`absolute bottom-full mb-2 ${
                    isMobile ? 'left-0 w-80' : 'left-0 w-80'
                  } bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 p-3 z-50 max-h-96 overflow-y-auto`}>
                    <div className="space-y-1">
                      {/* Claude 모델들 */}
                      <div className="px-2 py-1 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                        Claude
                      </div>
                      {MODEL_MAP.claude.map((model) => (
                        <button
                          key={model.id}
                          type="button"
                          onClick={() => handleModelChange(model.id)}
                          className={`w-full text-left p-3 rounded-lg transition-all ${
                            selectedModel === model.id
                              ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700'
                              : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <Star className="w-3 h-3 text-orange-500" />
                              <span className="font-medium text-sm text-slate-900 dark:text-slate-100">
                                {model.name.replace('Claude ', '')}
                              </span>
                            </div>
                            <div className="flex items-center space-x-1">
                              {model.isRecommended && <Star className="w-3 h-3 text-amber-500" />}
                              {model.speed === 'fast' && <Zap className="w-3 h-3 text-green-500" />}
                            </div>
                          </div>
                          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                            {model.description}
                          </p>
                        </button>
                      ))}
                      
                      {/* Gemini 모델들 */}
                      <div className="px-2 py-1 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mt-3">
                        Gemini
                      </div>
                      {MODEL_MAP.gemini.map((model) => (
                        <button
                          key={model.id}
                          type="button"
                          onClick={() => handleModelChange(model.id)}
                          className={`w-full text-left p-3 rounded-lg transition-all ${
                            selectedModel === model.id
                              ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700'
                              : 'hover:bg-slate-50 dark:hover:bg-slate-700/50'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <Zap className="w-3 h-3 text-blue-500" />
                              <span className="font-medium text-sm text-slate-900 dark:text-slate-100">
                                {model.name.replace('Gemini ', '')}
                              </span>
                            </div>
                            <div className="flex items-center space-x-1">
                              {model.isRecommended && <Star className="w-3 h-3 text-amber-500" />}
                              {model.speed === 'fast' && <Zap className="w-3 h-3 text-green-500" />}
                            </div>
                          </div>
                          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                            {model.description}
                          </p>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 에이전트 기능 토글 버튼들 */}
              <div className="flex space-x-1">
                {/* 웹 검색 버튼 */}
                <button
                  type="button"
                  onClick={() => handleAgentToggle('web_search')}
                  className={`flex items-center space-x-1 px-2 py-1.5 rounded-lg border transition-all duration-200 ${
                    selectedAgent === 'web_search'
                      ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700 text-green-700 dark:text-green-300'
                      : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-green-200 dark:hover:border-green-700 hover:bg-green-50 dark:hover:bg-green-900/10'
                  }`}
                  title="웹 검색 기능"
                >
                  <span className="text-sm">🔍</span>
                  <span className="text-xs font-medium hidden sm:inline">검색</span>
                </button>

                {/* 심층 리서치 버튼 */}
                <button
                  type="button"
                  onClick={() => handleAgentToggle('deep_research')}
                  className={`flex items-center space-x-1 px-2 py-1.5 rounded-lg border transition-all duration-200 ${
                    selectedAgent === 'deep_research'
                      ? 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-700 text-purple-700 dark:text-purple-300'
                      : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-purple-200 dark:hover:border-purple-700 hover:bg-purple-50 dark:hover:bg-purple-900/10'
                  }`}
                  title="심층 리서치 기능"
                >
                  <span className="text-sm">📊</span>
                  <span className="text-xs font-medium hidden sm:inline">리서치</span>
                </button>

                {/* Canvas 버튼 */}
                <button
                  type="button"
                  onClick={() => handleAgentToggle('canvas')}
                  className={`flex items-center space-x-1 px-2 py-1.5 rounded-lg border transition-all duration-200 ${
                    selectedAgent === 'canvas'
                      ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700 text-amber-700 dark:text-amber-300'
                      : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-amber-200 dark:hover:border-amber-700 hover:bg-amber-50 dark:hover:bg-amber-900/10'
                  }`}
                  title="Canvas 워크스페이스"
                >
                  <span className="text-sm">🎨</span>
                  <span className="text-xs font-medium hidden sm:inline">Canvas</span>
                </button>
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
    </div>
  );
};