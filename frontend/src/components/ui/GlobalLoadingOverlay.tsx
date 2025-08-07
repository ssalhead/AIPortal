/**
 * 전역 로딩 오버레이 컴포넌트
 */

import React from 'react';
import { useLoading } from '../../contexts/LoadingContext';
import { LoadingSpinner } from './LoadingSpinner';

export const GlobalLoadingOverlay: React.FC = () => {
  const { isLoading, loadingMessage } = useLoading();

  if (!isLoading) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 shadow-xl max-w-sm w-full mx-4">
        <div className="flex flex-col items-center space-y-4">
          <LoadingSpinner size="lg" color="primary" />
          <div className="text-center">
            <p className="text-gray-900 font-medium">
              {loadingMessage || '처리 중입니다...'}
            </p>
            <p className="text-gray-500 text-sm mt-1">
              잠시만 기다려주세요
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * 페이지 내 로딩 컴포넌트 (오버레이 없이)
 */
export const InlineLoading: React.FC<{
  message?: string;
  size?: 'sm' | 'md' | 'lg';
}> = ({ 
  message = '로딩 중...', 
  size = 'md' 
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-8 space-y-4">
      <LoadingSpinner size={size} color="primary" />
      <p className="text-gray-600 text-sm">{message}</p>
    </div>
  );
};