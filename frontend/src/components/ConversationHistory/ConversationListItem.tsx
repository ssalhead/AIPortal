/**
 * 대화 목록 아이템 컴포넌트
 */

import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { ko } from 'date-fns/locale';
import { 
  MessageCircle, 
  Clock, 
  User, 
  Bot, 
  MoreVertical,
  Archive,
  Trash2,
  Edit3
} from 'lucide-react';
import { ConversationSummary } from '../../services/conversationHistoryService';

interface ConversationListItemProps {
  conversation: ConversationSummary;
  isSelected?: boolean;
  onSelect: (conversation: ConversationSummary) => void;
  onEdit?: (conversation: ConversationSummary) => void;
  onArchive?: (conversation: ConversationSummary) => void;
  onDelete?: (conversation: ConversationSummary) => void;
}

export const ConversationListItem: React.FC<ConversationListItemProps> = ({
  conversation,
  isSelected = false,
  onSelect,
  onEdit,
  onArchive,
  onDelete
}) => {
  const [showMenu, setShowMenu] = React.useState(false);
  const menuRef = React.useRef<HTMLDivElement>(null);

  // 메뉴 외부 클릭 감지
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const formatTimeAgo = (dateString: string) => {
    return formatDistanceToNow(new Date(dateString), {
      addSuffix: true,
      locale: ko
    });
  };

  const getAgentIcon = (agentType?: string) => {
    switch (agentType) {
      case 'web_search':
        return '🔍';
      case 'canvas':
        return '🎨';
      case 'multimodal_rag':
        return '📚';
      default:
        return <Bot className="w-4 h-4" />;
    }
  };

  const getModelBadgeColor = (model?: string) => {
    if (!model) return 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300';
    
    if (model.includes('claude')) {
      return 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300';
    } else if (model.includes('gemini')) {
      return 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300';
    } else {
      return 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300';
    }
  };

  const handleMenuAction = (action: string, event: React.MouseEvent) => {
    event.stopPropagation();
    setShowMenu(false);
    
    switch (action) {
      case 'edit':
        onEdit?.(conversation);
        break;
      case 'archive':
        onArchive?.(conversation);
        break;
      case 'delete':
        onDelete?.(conversation);
        break;
    }
  };

  return (
    <div
      className={`
        relative p-4 border-b border-gray-200 dark:border-gray-700 
        hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors
        ${isSelected ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-l-blue-500' : ''}
      `}
      onClick={() => onSelect(conversation)}
    >
      {/* 헤더 영역 */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
            {conversation.title || '제목 없는 대화'}
          </h3>
          
          {/* 메타 정보 */}
          <div className="flex items-center space-x-2 mt-1">
            {conversation.agent_type && (
              <span className="inline-flex items-center text-xs text-gray-500 dark:text-gray-400">
                {getAgentIcon(conversation.agent_type)}
                <span className="ml-1">{conversation.agent_type}</span>
              </span>
            )}
            
            {conversation.model && (
              <span className={`
                inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
                ${getModelBadgeColor(conversation.model)}
              `}>
                {conversation.model}
              </span>
            )}
          </div>
        </div>

        {/* 메뉴 버튼 */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            <MoreVertical className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          </button>

          {/* 드롭다운 메뉴 */}
          {showMenu && (
            <div className="
              absolute right-0 top-8 w-48 bg-white dark:bg-gray-800 
              border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10
            ">
              <div className="py-1">
                {onEdit && (
                  <button
                    onClick={(e) => handleMenuAction('edit', e)}
                    className="
                      w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300
                      hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center
                    "
                  >
                    <Edit3 className="w-4 h-4 mr-2" />
                    수정
                  </button>
                )}
                
                {onArchive && conversation.status === 'active' && (
                  <button
                    onClick={(e) => handleMenuAction('archive', e)}
                    className="
                      w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300
                      hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center
                    "
                  >
                    <Archive className="w-4 h-4 mr-2" />
                    보관
                  </button>
                )}
                
                {onDelete && (
                  <button
                    onClick={(e) => handleMenuAction('delete', e)}
                    className="
                      w-full text-left px-4 py-2 text-sm text-red-600 dark:text-red-400
                      hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center
                    "
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    삭제
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 마지막 메시지 미리보기 */}
      {conversation.last_message_preview && (
        <div className="mb-2">
          <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
            {conversation.last_message_preview}
          </p>
        </div>
      )}

      {/* 하단 정보 */}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center space-x-3">
          <span className="flex items-center">
            <MessageCircle className="w-3 h-3 mr-1" />
            {conversation.message_count}개 메시지
          </span>
          
          {conversation.last_message_at && (
            <span className="flex items-center">
              <Clock className="w-3 h-3 mr-1" />
              {formatTimeAgo(conversation.last_message_at)}
            </span>
          )}
        </div>

        {/* 상태 표시 */}
        {conversation.status === 'archived' && (
          <span className="text-yellow-600 dark:text-yellow-400 font-medium">
            보관됨
          </span>
        )}
      </div>

      {/* 선택된 상태 표시 */}
      {isSelected && (
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500 rounded-r"></div>
      )}
    </div>
  );
};