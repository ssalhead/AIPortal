/**
 * 헤더 컴포넌트
 */

import React from 'react';
import { useAuth } from '../../contexts/AuthContext';

export const Header: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold text-gray-900">
            AI Portal
          </h1>
          <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
            v0.1.0
          </span>
        </div>
        
        <div className="flex items-center space-x-4">
          {user && (
            <>
              <div className="text-sm">
                <span className="text-gray-600">안녕하세요,</span>
                <span className="font-medium text-gray-900 ml-1">{user.name}</span>
              </div>
              <button
                onClick={logout}
                className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                로그아웃
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
};