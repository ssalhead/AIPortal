/**
 * 현대적인 헤더 컴포넌트 - Gemini 스타일
 */

import React, { useState } from 'react';
import { ChevronDown, Zap } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

export const Header: React.FC = () => {
  const { user, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  return (
    <header className="sticky top-0 z-40 w-full bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-b border-slate-200/80 dark:border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* 로고 및 브랜딩 */}
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold bg-gradient-to-r from-primary-600 to-primary-700 text-transparent bg-clip-text">
                  AI Portal
                </h1>
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                  v2.0
                </span>
              </div>
            </div>
          </div>

          <div className="flex-1"></div>

          {/* 사용자 메뉴 */}
          <div className="flex items-center">

            {/* 사용자 프로필 */}
            {user && (
              <div className="relative">
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center space-x-2 p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white font-bold text-sm">
                    {user.name?.charAt(0) || 'U'}
                  </div>
                  <div className="hidden md:flex flex-col items-start">
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                      {user.name || 'User'}
                    </span>
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {user.email || 'user@email.com'}
                    </span>
                  </div>
                  <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
                </button>

                {showUserMenu && (
                  <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-slate-800 rounded-lg shadow-xl py-1 border border-slate-200 dark:border-slate-700 z-50">
                    <a href="#profile" className="block px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700">
                      프로필
                    </a>
                    <a href="#settings" className="block px-4 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700">
                      설정
                    </a>
                    <div className="border-t border-slate-200 dark:border-slate-700 my-1"></div>
                    <button 
                      onClick={logout}
                      className="w-full text-left block px-4 py-2 text-sm text-red-500 hover:bg-red-50 dark:hover:bg-red-900/50"
                    >
                      로그아웃
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};