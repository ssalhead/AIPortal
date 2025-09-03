/**
 * SimpleCanvasWorkspace - 간소한 Canvas 워크스페이스 (협업 기능 제거)
 * Konva.js 기반 단독 사용자 Canvas 시스템
 */

import React from 'react';
import { KonvaCanvasWorkspace } from './KonvaCanvasWorkspace';
import type { CanvasItem } from '../../types/canvas';

interface CollaborativeCanvasWorkspaceProps {
  conversationId: string;
  canvasId: string;
  width?: number;
  height?: number;
  className?: string;
  userId?: string;
  userName?: string;
  onItemSelected?: (itemId: string | null) => void;
  onItemUpdated?: (itemId: string, item: CanvasItem) => void;
  onPerformanceUpdate?: (metrics: any) => void;
  enableCollaboration?: boolean;
  showUserCursors?: boolean;
  showUserSelections?: boolean;
}

/**
 * 단순한 Canvas 워크스페이스 컴포넌트
 * 웹소켓과 협업 기능을 완전히 제거하고 기본 Canvas 기능만 제공
 */
export const CollaborativeCanvasWorkspace: React.FC<CollaborativeCanvasWorkspaceProps> = ({
  conversationId,
  canvasId,
  width = 800,
  height = 600,
  className = '',
  onItemSelected,
  onItemUpdated,
  onPerformanceUpdate
}) => {
  return (
    <div className={`canvas-workspace ${className}`}>
      <KonvaCanvasWorkspace
        conversationId={conversationId}
        canvasId={canvasId}
        width={width}
        height={height}
        onItemSelected={onItemSelected}
        onItemUpdated={onItemUpdated}
        onPerformanceUpdate={onPerformanceUpdate}
      />
    </div>
  );
};

export default CollaborativeCanvasWorkspace;