/**
 * 리사이저 컴포넌트 - 패널 크기 조절
 */

import React, { useRef, useCallback } from 'react';
import { GripVertical } from 'lucide-react';

interface ResizerProps {
  onResize: (leftWidth: number) => void;
  initialLeftWidth: number;
  minLeftWidth?: number;
  maxLeftWidth?: number;
  containerWidth: number;
}

export const Resizer: React.FC<ResizerProps> = ({
  onResize,
  initialLeftWidth,
  minLeftWidth = 300,
  maxLeftWidth = 800,
  containerWidth,
}) => {
  const isDragging = useRef(false);
  const startX = useRef(0);
  const startLeftWidth = useRef(initialLeftWidth);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    startX.current = e.clientX;
    startLeftWidth.current = initialLeftWidth;

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
  }, [initialLeftWidth]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging.current) return;

    const deltaX = e.clientX - startX.current;
    const newLeftWidth = startLeftWidth.current + deltaX;

    // 제한 범위 내에서만 리사이즈
    const clampedWidth = Math.max(
      minLeftWidth,
      Math.min(maxLeftWidth, Math.min(newLeftWidth, containerWidth - 400)) // Canvas 최소 400px 보장
    );

    onResize(clampedWidth);
  }, [minLeftWidth, maxLeftWidth, containerWidth, onResize]);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }, [handleMouseMove]);

  return (
    <div
      className="relative w-1 bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 cursor-ew-resize transition-colors duration-200 group"
      onMouseDown={handleMouseDown}
    >
      {/* 리사이저 핸들 */}
      <div className="absolute inset-y-0 -left-1 -right-1 flex items-center justify-center">
        <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-slate-400 dark:bg-slate-500 rounded-full p-1">
          <GripVertical className="w-3 h-3 text-white" />
        </div>
      </div>

      {/* 드래그 중일 때 표시되는 가이드라인 */}
      <div className="absolute top-0 bottom-0 w-px bg-primary-500 opacity-0 group-active:opacity-100 transition-opacity duration-200" />
    </div>
  );
};