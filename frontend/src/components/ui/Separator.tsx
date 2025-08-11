/**
 * 분할선 컴포넌트
 */

import React from 'react';

interface SeparatorProps {
  orientation?: 'horizontal' | 'vertical';
  className?: string;
}

export const Separator: React.FC<SeparatorProps> = ({ 
  orientation = 'horizontal', 
  className = '' 
}) => {
  const baseClasses = orientation === 'horizontal' 
    ? 'h-px w-full bg-gray-200' 
    : 'w-px h-full bg-gray-200';
    
  return <div className={`${baseClasses} ${className}`} />;
};