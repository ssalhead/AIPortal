/**
 * 로딩 스피너 컴포넌트
 */

import React from 'react';

interface LoadingSpinnerProps {
  /** 스피너 크기 */
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  /** 색상 */
  color?: 'primary' | 'secondary' | 'success' | 'danger' | 'warning' | 'info';
  /** 표시할 텍스트 */
  text?: string;
  /** 텍스트 위치 */
  textPosition?: 'bottom' | 'right';
  /** 전체 화면 오버레이 여부 */
  overlay?: boolean;
  /** 투명도 */
  opacity?: number;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  color = 'primary',
  text,
  textPosition = 'bottom',
  overlay = false,
  opacity = 0.8,
}) => {
  const sizeClasses = {
    xs: 'w-3 h-3',
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
    xl: 'w-12 h-12',
  };

  const colorClasses = {
    primary: 'border-blue-600',
    secondary: 'border-gray-600',
    success: 'border-green-600',
    danger: 'border-red-600',
    warning: 'border-yellow-600',
    info: 'border-blue-400',
  };

  const textSizeClasses = {
    xs: 'text-xs',
    sm: 'text-sm',
    md: 'text-sm',
    lg: 'text-base',
    xl: 'text-lg',
  };

  const spinnerElement = (
    <div
      className={`
        ${sizeClasses[size]} 
        border-2 border-gray-200 rounded-full animate-spin
        ${colorClasses[color]}
      `}
      style={{
        borderTopColor: 'transparent',
        borderRightColor: 'transparent',
      }}
    />
  );

  const content = (
    <div 
      className={`
        flex items-center justify-center
        ${textPosition === 'bottom' ? 'flex-col space-y-2' : 'flex-row space-x-2'}
      `}
    >
      {spinnerElement}
      {text && (
        <span 
          className={`
            ${textSizeClasses[size]} text-gray-600 font-medium
          `}
        >
          {text}
        </span>
      )}
    </div>
  );

  if (overlay) {
    return (
      <div
        className="fixed inset-0 bg-black flex items-center justify-center z-50"
        style={{ backgroundColor: `rgba(0, 0, 0, ${opacity})` }}
      >
        <div className="bg-white rounded-lg p-6 shadow-xl">
          {content}
        </div>
      </div>
    );
  }

  return content;
};

/**
 * 점들이 움직이는 로딩 애니메이션
 */
export const DotsLoadingSpinner: React.FC<{
  size?: 'sm' | 'md' | 'lg';
  color?: string;
}> = ({ 
  size = 'md', 
  color = 'bg-blue-600' 
}) => {
  const sizeClasses = {
    sm: 'w-1 h-1',
    md: 'w-1.5 h-1.5',
    lg: 'w-2 h-2',
  };

  return (
    <div className="flex items-center justify-center space-x-1">
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className={`${sizeClasses[size]} ${color} rounded-full`}
          style={{
            animation: `bounce 1.4s infinite ease-in-out both`,
            animationDelay: `${index * 0.16}s`
          }}
        />
      ))}
      
      <style jsx>{`
        @keyframes bounce {
          0%, 80%, 100% {
            transform: scale(0);
          }
          40% {
            transform: scale(1);
          }
        }
      `}</style>
    </div>
  );
};

/**
 * 펄스 효과 로딩 스피너
 */
export const PulseLoadingSpinner: React.FC<{
  size?: number;
  color?: string;
}> = ({ 
  size = 40, 
  color = '#3B82F6' 
}) => {
  return (
    <div className="flex items-center justify-center">
      <div
        className="rounded-full animate-pulse"
        style={{
          width: `${size}px`,
          height: `${size}px`,
          backgroundColor: color,
          animation: `pulse 2s infinite`
        }}
      />
      
      <style jsx>{`
        @keyframes pulse {
          0% {
            transform: scale(0.8);
            opacity: 0.5;
          }
          50% {
            transform: scale(1.2);
            opacity: 1;
          }
          100% {
            transform: scale(0.8);
            opacity: 0.5;
          }
        }
      `}</style>
    </div>
  );
};

/**
 * 프로그레스 바 형태 로딩
 */
export const ProgressLoadingBar: React.FC<{
  progress?: number;  // 0-100
  height?: number;
  color?: string;
  backgroundColor?: string;
  animated?: boolean;
}> = ({
  progress = 0,
  height = 4,
  color = '#3B82F6',
  backgroundColor = '#E5E7EB',
  animated = true
}) => {
  return (
    <div 
      className="w-full rounded-full overflow-hidden"
      style={{ 
        height: `${height}px`,
        backgroundColor 
      }}
    >
      <div
        className={`h-full rounded-full transition-all duration-300 ${
          animated ? 'animate-pulse' : ''
        }`}
        style={{
          width: `${progress}%`,
          backgroundColor: color
        }}
      />
    </div>
  );
};