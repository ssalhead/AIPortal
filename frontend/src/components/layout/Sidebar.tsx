/**
 * 사이드바 컴포넌트 - Gemini 스타일
 */

import React, { useState } from 'react';
import { MessageSquare, Plus, PanelLeftClose, PanelLeftOpen, Trash2, History, X } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

interface ChatHistoryItem {
  id: string;
  title: string;
  timestamp: string;
}

interface SidebarProps {
  isOpen?: boolean;
  onToggle?: () => void;
  onNewChat?: () => void;
  chatHistory?: ChatHistoryItem[];
  onSelectChat?: (chatId: string) => void;
  onDeleteChat?: (chatId: string) => void;
  isMobile?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen = true,
  onToggle,
  onNewChat,
  chatHistory = [
    { id: '1', title: 'React 상태 관리 전략', timestamp: '2024-01-07T10:30:00Z' },
    { id: '2', title: 'Tailwind CSS 최적화 방법', timestamp: '2024-01-07T09:15:00Z' },
    { id: '3', title: '점심 메뉴 추천', timestamp: '2024-01-06T12:20:00Z' },
  ],
  onSelectChat,
  onDeleteChat,
  isMobile = false,
}) => {
  const [hoveredChat, setHoveredChat] = useState<string | null>(null);
  const location = useLocation();

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return '방금 전';
    if (diffInHours < 24) return `${diffInHours}시간 전`;
    if (diffInHours < 48) return '어제';
    return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  };

  return (
    <div 
      className={`flex flex-col bg-slate-100 dark:bg-slate-800/50 border-r border-slate-200 dark:border-slate-700/50 transition-all duration-300 ${
        isMobile 
          ? 'w-64 h-full' 
          : (isOpen ? 'w-64' : 'w-16')
      }`}
    >
      {/* Header */}
      <div className={`p-4 flex-shrink-0 ${isMobile ? 'flex items-center justify-between' : ''}`}>
        {isMobile && (
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">
            AI Portal
          </h2>
        )}
        
        {isMobile && (
          <button
            onClick={onToggle}
            className="p-2 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
          >
            <X className="w-5 h-5 text-slate-600 dark:text-slate-400" />
          </button>
        )}
        
      </div>
      
      {/* 새 대화 버튼 */}
      <div className="px-4 pb-4 flex-shrink-0">
        <button
          onClick={onNewChat}
          className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200
            bg-white dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-600 
            border border-slate-200 dark:border-slate-600 shadow-sm hover:shadow-md`}
          title={!isOpen && !isMobile ? '새 대화' : undefined}
        >
          <Plus className="w-4 h-4 flex-shrink-0" />
          {(isOpen || isMobile) && <span>새 대화</span>}
        </button>
      </div>

      {/* Navigation Menu */}
      <div className="px-4 pb-4 flex-shrink-0">
        <nav className="flex flex-col gap-1">
          <Link
            to="/chat"
            className={`flex items-center gap-3 p-3 rounded-xl transition-all duration-200 ${
              location.pathname === '/chat' || location.pathname === '/'
                ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                : 'hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300'
            }`}
            title={!isOpen && !isMobile ? '채팅' : undefined}
          >
            <MessageSquare className="w-5 h-5 flex-shrink-0" />
            {(isOpen || isMobile) && <span className="text-sm font-medium">채팅</span>}
          </Link>
          
          <Link
            to="/history"
            className={`flex items-center gap-3 p-3 rounded-xl transition-all duration-200 ${
              location.pathname === '/history'
                ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                : 'hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300'
            }`}
            title={!isOpen && !isMobile ? '대화 이력' : undefined}
          >
            <History className="w-5 h-5 flex-shrink-0" />
            {(isOpen || isMobile) && <span className="text-sm font-medium">대화 이력</span>}
          </Link>
        </nav>
      </div>

      {/* Chat History */}
      <div className="flex-grow overflow-y-auto px-4">
        <nav className="flex flex-col gap-1">
          {chatHistory.map((chat) => (
            <div
              key={chat.id}
              className="group relative"
              onMouseEnter={() => setHoveredChat(chat.id)}
              onMouseLeave={() => setHoveredChat(null)}
            >
              <button
                onClick={() => onSelectChat?.(chat.id)}
                className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 
                  transition-all duration-200 text-left"
                title={!isOpen && !isMobile ? chat.title : undefined}
              >
                <MessageSquare className="w-5 h-5 text-slate-500 dark:text-slate-400 flex-shrink-0" />
                {(isOpen || isMobile) && (
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium text-slate-700 dark:text-slate-300">
                      {chat.title}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      {formatTime(chat.timestamp)}
                    </p>
                  </div>
                )}
                {(isOpen || isMobile) && hoveredChat === chat.id && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteChat?.(chat.id);
                    }}
                    className="flex-shrink-0 p-1.5 rounded-lg hover:bg-error-100 dark:hover:bg-error-900/20 
                      text-slate-400 hover:text-error-600 dark:hover:text-error-400 transition-colors"
                    title="대화 삭제"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </button>
            </div>
          ))}
        </nav>
      </div>

      {/* Footer - Toggle Button (데스크톱만) */}
      {!isMobile && (
        <div className="p-4 flex-shrink-0 border-t border-slate-200 dark:border-slate-700/50">
          <button
            onClick={onToggle}
            className="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-700 
              transition-colors text-slate-600 dark:text-slate-400"
            title={isOpen ? '사이드바 접기' : '사이드바 펼치기'}
          >
            {isOpen ? (
              <PanelLeftClose className="w-5 h-5 flex-shrink-0" />
            ) : (
              <PanelLeftOpen className="w-5 h-5 flex-shrink-0" />
            )}
            {isOpen && <span className="text-sm font-medium">사이드바 접기</span>}
          </button>
        </div>
      )}
    </div>
  );
};