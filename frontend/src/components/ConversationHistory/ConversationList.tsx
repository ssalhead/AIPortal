/**
 * 대화 목록 컴포넌트
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Filter, RotateCcw, Plus, AlertCircle, Loader2 } from 'lucide-react';
import { ConversationListItem } from './ConversationListItem';
import type { 
  ConversationSummary
} from '../../services/conversationHistoryService';
import { conversationHistoryService } from '../../services/conversationHistoryService';
import { useToast } from '../ui/Toast';

interface ConversationListProps {
  selectedConversationId?: string;
  onSelectConversation: (conversation: ConversationSummary) => void;
  onCreateNew?: () => void;
  className?: string;
}

export const ConversationList: React.FC<ConversationListProps> = ({
  selectedConversationId,
  onSelectConversation,
  onCreateNew,
  className = ''
}) => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<'all' | 'ACTIVE' | 'ARCHIVED'>('ACTIVE');
  
  const { showError, showSuccess, showInfo } = useToast();
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const searchTimeoutRef = useRef<number>();

  // 초기 대화 목록 로드
  useEffect(() => {
    loadConversations(true);
  }, [statusFilter]);

  // 검색 디바운싱
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    searchTimeoutRef.current = setTimeout(() => {
      if (searchTerm.trim()) {
        performSearch();
      } else {
        loadConversations(true);
      }
    }, 300);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchTerm]);

  const loadConversations = async (reset: boolean = false) => {
    try {
      setIsLoading(true);
      setError(null);

      const params = {
        skip: reset ? 0 : conversations.length,
        limit: 20,
        status: statusFilter === 'all' ? undefined : statusFilter as 'ACTIVE' | 'ARCHIVED'
      };

      const response = await conversationHistoryService.getConversations(params);

      if (reset) {
        setConversations(response.conversations);
      } else {
        setConversations(prev => [...prev, ...response.conversations]);
      }

      setHasMore(response.has_more);
    } catch (error) {
      console.error('대화 목록 로드 실패:', error);
      setError('대화 목록을 불러오는데 실패했습니다.');
      showError('대화 목록을 불러오는데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const performSearch = async () => {
    try {
      setIsSearching(true);
      setError(null);

      const response = await conversationHistoryService.searchConversations({
        q: searchTerm.trim(),
        limit: 50
      });

      setConversations(response.results);
      setHasMore(false); // 검색 결과는 페이지네이션 안 함
    } catch (error) {
      console.error('대화 검색 실패:', error);
      setError('검색에 실패했습니다.');
      showError('검색에 실패했습니다.');
    } finally {
      setIsSearching(false);
    }
  };

  // 무한 스크롤 처리
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container || isLoading || !hasMore || searchTerm.trim()) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const threshold = 100; // 100px 전에 로드

    if (scrollHeight - (scrollTop + clientHeight) < threshold) {
      loadConversations(false);
    }
  }, [isLoading, hasMore, searchTerm, conversations.length]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  const handleEditConversation = async (conversation: ConversationSummary) => {
    const newTitle = prompt('새 제목을 입력하세요:', conversation.title);
    if (newTitle && newTitle !== conversation.title) {
      try {
        await conversationHistoryService.updateConversation(conversation.id, {
          title: newTitle
        });
        
        setConversations(prev => 
          prev.map(c => 
            c.id === conversation.id 
              ? { ...c, title: newTitle }
              : c
          )
        );
        
        showSuccess('대화 제목이 수정되었습니다.');
      } catch (error) {
        showError('대화 제목 수정에 실패했습니다.');
      }
    }
  };

  const handleArchiveConversation = async (conversation: ConversationSummary) => {
    try {
      await conversationHistoryService.updateConversation(conversation.id, {
        status: 'ARCHIVED'
      });
      
      setConversations(prev => prev.filter(c => c.id !== conversation.id));
      showSuccess('대화가 보관되었습니다.');
    } catch (error) {
      showError('대화 보관에 실패했습니다.');
    }
  };

  const handleDeleteConversation = async (conversation: ConversationSummary) => {
    if (confirm('정말로 이 대화를 삭제하시겠습니까?')) {
      try {
        await conversationHistoryService.deleteConversation(conversation.id);
        
        setConversations(prev => prev.filter(c => c.id !== conversation.id));
        showSuccess('대화가 삭제되었습니다.');
      } catch (error) {
        showError('대화 삭제에 실패했습니다.');
      }
    }
  };

  const groupedConversations = conversationHistoryService.groupConversationsByDate(conversations);

  return (
    <div className={`flex flex-col h-full bg-white dark:bg-gray-900 ${className}`}>
      {/* 헤더 */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            대화 기록
          </h2>
          
          {onCreateNew && (
            <button
              onClick={onCreateNew}
              className="
                flex items-center px-3 py-1.5 bg-blue-600 text-white rounded-md
                hover:bg-blue-700 transition-colors text-sm
              "
            >
              <Plus className="w-4 h-4 mr-1" />
              새 대화
            </button>
          )}
        </div>

        {/* 검색 바 */}
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            type="text"
            placeholder="대화 검색..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="
              w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600
              rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
              placeholder-gray-500 dark:placeholder-gray-400
              focus:ring-2 focus:ring-blue-500 focus:border-transparent
            "
          />
          {(isSearching || isLoading) && (
            <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4 animate-spin" />
          )}
        </div>

        {/* 필터 */}
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as any)}
            className="
              text-sm border border-gray-300 dark:border-gray-600 rounded
              bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
              px-2 py-1 focus:ring-2 focus:ring-blue-500 focus:border-transparent
            "
          >
            <option value="ACTIVE">활성 대화</option>
            <option value="ARCHIVED">보관된 대화</option>
            <option value="all">모든 대화</option>
          </select>

          <button
            onClick={() => loadConversations(true)}
            disabled={isLoading}
            className="
              p-1 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200
              disabled:opacity-50 disabled:cursor-not-allowed transition-colors
            "
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 대화 목록 */}
      <div 
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto"
      >
        {error && (
          <div className="p-4 text-center text-red-600 dark:text-red-400">
            <AlertCircle className="w-5 h-5 mx-auto mb-2" />
            {error}
          </div>
        )}

        {conversations.length === 0 && !isLoading && !error && (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            {searchTerm ? (
              <>
                <Search className="w-8 h-8 mx-auto mb-3 opacity-50" />
                <p>'{searchTerm}'에 대한 검색 결과가 없습니다.</p>
              </>
            ) : (
              <>
                <p>아직 대화 기록이 없습니다.</p>
                {onCreateNew && (
                  <button
                    onClick={onCreateNew}
                    className="mt-2 text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    첫 대화를 시작해보세요
                  </button>
                )}
              </>
            )}
          </div>
        )}

        {/* 그룹화된 대화 목록 */}
        {Object.entries(groupedConversations).map(([dateGroup, groupConversations]) => (
          <div key={dateGroup}>
            <div className="sticky top-0 bg-gray-50 dark:bg-gray-800 px-4 py-2 text-xs font-medium text-gray-600 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
              {dateGroup}
            </div>
            
            {groupConversations.map((conversation) => (
              <ConversationListItem
                key={conversation.id}
                conversation={conversation}
                isSelected={conversation.id === selectedConversationId}
                onSelect={onSelectConversation}
                onEdit={handleEditConversation}
                onArchive={statusFilter === 'ACTIVE' ? handleArchiveConversation : undefined}
                onDelete={handleDeleteConversation}
              />
            ))}
          </div>
        ))}

        {/* 로딩 표시 */}
        {isLoading && (
          <div className="p-4 text-center">
            <Loader2 className="w-5 h-5 mx-auto animate-spin text-gray-400" />
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              대화를 불러오는 중...
            </p>
          </div>
        )}

        {/* 더 불러올 데이터가 있을 때의 안내 */}
        {hasMore && !isLoading && !searchTerm && conversations.length > 0 && (
          <div className="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
            스크롤하여 더 많은 대화를 확인하세요
          </div>
        )}
      </div>
    </div>
  );
};