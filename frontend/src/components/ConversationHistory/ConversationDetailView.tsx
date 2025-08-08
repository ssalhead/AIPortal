/**
 * 대화 상세 뷰 컴포넌트
 */

import React, { useState, useEffect, useRef } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';
import { 
  Download, 
  Copy, 
  Search, 
  ChevronDown, 
  ChevronUp,
  Clock,
  Zap,
  MessageSquare,
  FileText,
  AlertCircle,
  Loader2,
  RotateCcw
} from 'lucide-react';
import { 
  ConversationDetail, 
  ConversationMessage,
  conversationHistoryService 
} from '../../services/conversationHistoryService';
import { useToast } from '../ui/Toast';

interface ConversationDetailViewProps {
  conversationId: string;
  className?: string;
}

export const ConversationDetailView: React.FC<ConversationDetailViewProps> = ({
  conversationId,
  className = ''
}) => {
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showMetadata, setShowMetadata] = useState(false);
  
  const { showSuccess, showError } = useToast();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (conversationId) {
      loadConversationDetail();
    }
  }, [conversationId]);

  const loadConversationDetail = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const detail = await conversationHistoryService.getConversationDetail(conversationId);
      setConversation(detail);
    } catch (error) {
      console.error('대화 상세 정보 로드 실패:', error);
      setError('대화를 불러오는데 실패했습니다.');
      showError('대화를 불러오는데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadMoreMessages = async () => {
    if (!conversation || !conversation.message_pagination.has_more) return;

    try {
      setIsLoadingMore(true);
      
      const moreDetail = await conversationHistoryService.getConversationDetail(
        conversationId,
        {
          message_skip: conversation.messages.length,
          message_limit: 50
        }
      );

      setConversation(prev => {
        if (!prev) return null;
        
        return {
          ...prev,
          messages: [...prev.messages, ...moreDetail.messages],
          message_pagination: moreDetail.message_pagination
        };
      });
    } catch (error) {
      showError('추가 메시지를 불러오는데 실패했습니다.');
    } finally {
      setIsLoadingMore(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      showSuccess('클립보드에 복사되었습니다.');
    } catch (error) {
      showError('복사에 실패했습니다.');
    }
  };

  const exportConversation = (format: 'text' | 'json') => {
    if (!conversation) return;

    const content = format === 'text' 
      ? conversationHistoryService.exportConversationAsText(conversation)
      : conversationHistoryService.exportConversationAsJson(conversation);

    const blob = new Blob([content], { 
      type: format === 'text' ? 'text/plain' : 'application/json' 
    });
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-${conversation.id}.${format === 'text' ? 'txt' : 'json'}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showSuccess(`대화가 ${format.toUpperCase()} 형식으로 내보내졌습니다.`);
  };

  const filteredMessages = conversation?.messages.filter(message =>
    !searchTerm || 
    message.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
    message.role.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  const getMessageIcon = (role: string) => {
    switch (role) {
      case 'user':
        return '👤';
      case 'assistant':
        return '🤖';
      case 'system':
        return '⚙️';
      case 'tool':
        return '🔧';
      default:
        return '❓';
    }
  };

  const formatTokenCount = (input?: number, output?: number) => {
    const parts = [];
    if (input) parts.push(`입력 ${input.toLocaleString()}`);
    if (output) parts.push(`출력 ${output.toLocaleString()}`);
    return parts.join(' / ');
  };

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center">
          <Loader2 className="w-8 h-8 mx-auto mb-4 animate-spin text-blue-500" />
          <p className="text-gray-600 dark:text-gray-400">대화를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center">
          <AlertCircle className="w-8 h-8 mx-auto mb-4 text-red-500" />
          <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
          <button
            onClick={loadConversationDetail}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="text-center text-gray-500 dark:text-gray-400">
          <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>대화를 선택해주세요</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full bg-white dark:bg-gray-900 ${className}`}>
      {/* 헤더 */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 truncate">
              {conversation.title}
            </h1>
            
            {conversation.description && (
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                {conversation.description}
              </p>
            )}
          </div>

          {/* 액션 버튼들 */}
          <div className="flex items-center space-x-2 ml-4">
            <button
              onClick={() => exportConversation('text')}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
              title="텍스트로 내보내기"
            >
              <FileText className="w-4 h-4" />
            </button>
            
            <button
              onClick={() => exportConversation('json')}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
              title="JSON으로 내보내기"
            >
              <Download className="w-4 h-4" />
            </button>
            
            <button
              onClick={loadConversationDetail}
              disabled={isLoading}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50 transition-colors"
              title="새로고침"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 메타데이터 토글 */}
        <button
          onClick={() => setShowMetadata(!showMetadata)}
          className="w-full flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded-md text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <span>대화 정보</span>
          {showMetadata ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {/* 메타데이터 영역 */}
        {showMetadata && (
          <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">생성일:</span>
                <p className="text-gray-900 dark:text-gray-100">
                  {new Date(conversation.created_at).toLocaleString('ko-KR')}
                </p>
              </div>
              
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">최근 업데이트:</span>
                <p className="text-gray-900 dark:text-gray-100">
                  {formatDistanceToNow(new Date(conversation.updated_at), {
                    addSuffix: true,
                    locale: ko
                  })}
                </p>
              </div>
              
              {conversation.model && (
                <div>
                  <span className="font-medium text-gray-600 dark:text-gray-400">모델:</span>
                  <p className="text-gray-900 dark:text-gray-100">{conversation.model}</p>
                </div>
              )}
              
              {conversation.agent_type && (
                <div>
                  <span className="font-medium text-gray-600 dark:text-gray-400">에이전트:</span>
                  <p className="text-gray-900 dark:text-gray-100">{conversation.agent_type}</p>
                </div>
              )}
              
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">총 메시지:</span>
                <p className="text-gray-900 dark:text-gray-100">
                  {conversation.message_pagination.total}개
                </p>
              </div>
              
              <div>
                <span className="font-medium text-gray-600 dark:text-gray-400">상태:</span>
                <p className="text-gray-900 dark:text-gray-100">
                  {conversation.status === 'active' ? '활성' : 
                   conversation.status === 'archived' ? '보관' : '삭제됨'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 검색 바 */}
        <div className="relative mt-3">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            type="text"
            placeholder="메시지 검색..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="
              w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600
              rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
              placeholder-gray-500 dark:placeholder-gray-400 text-sm
              focus:ring-2 focus:ring-blue-500 focus:border-transparent
            "
          />
        </div>
      </div>

      {/* 메시지 목록 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 더 많은 메시지 로드 버튼 */}
        {conversation.message_pagination.has_more && (
          <div className="text-center">
            <button
              onClick={loadMoreMessages}
              disabled={isLoadingMore}
              className="
                px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300
                rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
            >
              {isLoadingMore ? (
                <>
                  <Loader2 className="w-4 h-4 inline mr-2 animate-spin" />
                  로딩 중...
                </>
              ) : (
                '이전 메시지 더 보기'
              )}
            </button>
          </div>
        )}

        {/* 필터링된 메시지들 */}
        {filteredMessages.map((message, index) => (
          <div
            key={message.id}
            className={`
              flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}
            `}
          >
            <div
              className={`
                max-w-[80%] rounded-lg p-4 shadow-sm
                ${message.role === 'user' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                }
              `}
            >
              {/* 메시지 헤더 */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="text-xs">
                    {getMessageIcon(message.role)}
                  </span>
                  <span className={`
                    text-xs font-medium
                    ${message.role === 'user' ? 'text-blue-100' : 'text-gray-600 dark:text-gray-400'}
                  `}>
                    {message.role === 'user' ? '사용자' : 
                     message.role === 'assistant' ? '어시스턴트' :
                     message.role === 'system' ? '시스템' : '도구'}
                  </span>
                  
                  {message.model && (
                    <span className={`
                      text-xs px-2 py-0.5 rounded
                      ${message.role === 'user' 
                        ? 'bg-blue-500 text-blue-100' 
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                      }
                    `}>
                      {message.model}
                    </span>
                  )}
                </div>
                
                <button
                  onClick={() => copyToClipboard(message.content)}
                  className={`
                    p-1 rounded hover:bg-opacity-20 hover:bg-black transition-colors
                    ${message.role === 'user' ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'}
                  `}
                  title="복사"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </div>

              {/* 메시지 내용 */}
              <div className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                {searchTerm ? 
                  <span 
                    dangerouslySetInnerHTML={{
                      __html: conversationHistoryService.highlightSearchTerm(message.content, searchTerm)
                    }}
                  />
                  : message.content
                }
              </div>

              {/* 메시지 메타데이터 */}
              <div className={`
                mt-3 pt-2 border-t flex items-center justify-between text-xs
                ${message.role === 'user' 
                  ? 'border-blue-500 text-blue-100' 
                  : 'border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400'
                }
              `}>
                <div className="flex items-center space-x-3">
                  <span className="flex items-center">
                    <Clock className="w-3 h-3 mr-1" />
                    {new Date(message.created_at).toLocaleString('ko-KR')}
                  </span>
                  
                  {(message.tokens_input || message.tokens_output) && (
                    <span className="flex items-center">
                      <Zap className="w-3 h-3 mr-1" />
                      {formatTokenCount(message.tokens_input, message.tokens_output)} 토큰
                    </span>
                  )}
                  
                  {message.latency_ms && (
                    <span>
                      {message.latency_ms}ms
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* 검색 결과 없음 */}
        {searchTerm && filteredMessages.length === 0 && (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <Search className="w-8 h-8 mx-auto mb-3 opacity-50" />
            <p>'{searchTerm}'에 대한 검색 결과가 없습니다.</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};