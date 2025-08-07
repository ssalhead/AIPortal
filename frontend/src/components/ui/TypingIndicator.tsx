/**
 * 타이핑 인디케이터 컴포넌트
 */

import React from 'react';

interface TypingIndicatorProps {
  /** 표시할 메시지 (기본: "AI가 응답을 작성 중입니다...") */
  message?: string;
  /** 모델 이름 표시 */
  model?: string;
  /** 크기 (small, medium, large) */
  size?: 'small' | 'medium' | 'large';
  /** 테마 (light, dark) */
  theme?: 'light' | 'dark';
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  message = 'AI가 응답을 작성 중입니다...',
  model,
  size = 'medium',
  theme = 'light',
}) => {
  const sizeClasses = {
    small: {
      container: 'max-w-xs px-3 py-2',
      dot: 'w-1.5 h-1.5',
      text: 'text-xs',
      gap: 'gap-1'
    },
    medium: {
      container: 'max-w-sm px-4 py-3',
      dot: 'w-2 h-2',
      text: 'text-sm',
      gap: 'gap-1.5'
    },
    large: {
      container: 'max-w-md px-5 py-4',
      dot: 'w-2.5 h-2.5',
      text: 'text-base',
      gap: 'gap-2'
    }
  };

  const themeClasses = {
    light: {
      container: 'bg-gray-100 border border-gray-200',
      text: 'text-gray-600',
      dot: 'bg-gray-400',
      modelBadge: 'bg-blue-100 text-blue-600'
    },
    dark: {
      container: 'bg-gray-800 border border-gray-700',
      text: 'text-gray-300',
      dot: 'bg-gray-500',
      modelBadge: 'bg-blue-900 text-blue-300'
    }
  };

  const currentSize = sizeClasses[size];
  const currentTheme = themeClasses[theme];

  return (
    <div className="flex justify-start mb-4">
      <div
        className={`
          ${currentSize.container} 
          ${currentTheme.container} 
          rounded-lg shadow-sm
        `}
      >
        {/* 타이핑 애니메이션 */}
        <div className={`flex items-center ${currentSize.gap} mb-2`}>
          <div className={`flex items-center space-x-1`}>
            {[0, 1, 2].map((index) => (
              <div
                key={index}
                className={`
                  ${currentSize.dot} 
                  ${currentTheme.dot} 
                  rounded-full animate-pulse
                `}
                style={{
                  animationDelay: `${index * 0.2}s`,
                  animationDuration: '1s',
                  animationIterationCount: 'infinite'
                }}
              />
            ))}
          </div>
          <span className={`${currentTheme.text} ${currentSize.text} ml-2`}>
            {message}
          </span>
        </div>

        {/* 모델 정보 */}
        {model && (
          <div className="flex items-center">
            <span 
              className={`
                inline-block px-2 py-1 rounded text-xs font-medium
                ${currentTheme.modelBadge}
              `}
            >
              {model}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * 점 애니메이션 타이핑 인디케이터 (더 고급 버전)
 */
export const DotTypingIndicator: React.FC<{
  size?: 'small' | 'medium' | 'large';
  color?: string;
}> = ({ 
  size = 'medium', 
  color = 'bg-gray-400' 
}) => {
  const dotSizes = {
    small: 'w-1 h-1',
    medium: 'w-1.5 h-1.5',
    large: 'w-2 h-2'
  };

  return (
    <div className="flex items-center space-x-1 p-2">
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className={`${dotSizes[size]} ${color} rounded-full`}
          style={{
            animation: `typing 1.4s infinite ease-in-out both`,
            animationDelay: `${index * 0.16}s`
          }}
        />
      ))}
      
      <style jsx>{`
        @keyframes typing {
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
 * 파동 효과 타이핑 인디케이터
 */
export const WaveTypingIndicator: React.FC<{
  color?: string;
  size?: number;
}> = ({ 
  color = '#6B7280', 
  size = 8 
}) => {
  return (
    <div className="flex items-center space-x-1 p-3">
      {[0, 1, 2, 3, 4].map((index) => (
        <div
          key={index}
          style={{
            width: `${size}px`,
            height: `${size * 3}px`,
            backgroundColor: color,
            borderRadius: `${size / 2}px`,
            animation: `wave 1.2s infinite ease-in-out`,
            animationDelay: `${index * 0.1}s`
          }}
        />
      ))}
      
      <style jsx>{`
        @keyframes wave {
          0%, 40%, 100% {
            transform: scaleY(0.4);
          }
          20% {
            transform: scaleY(1.0);
          }
        }
      `}</style>
    </div>
  );
};