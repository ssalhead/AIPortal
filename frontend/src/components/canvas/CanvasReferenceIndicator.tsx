/**
 * Canvas 참조 관계 표시 컴포넌트 (v4.0)
 * Canvas 간의 연속성 및 참조 관계를 시각적으로 표시
 */

import React, { useState } from 'react';
import { 
  ArrowRight, 
  ArrowLeft, 
  GitBranch, 
  Link2, 
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Info
} from 'lucide-react';
import type { CanvasItem, CanvasToolType } from '../../types/canvas';
import { useCanvasStore } from '../../stores/canvasStore';

interface CanvasReferenceIndicatorProps {
  currentCanvasId: string;
  conversationId: string;
  className?: string;
}

interface ReferenceInfo {
  baseCanvas?: CanvasItem;
  derivedCanvases: CanvasItem[];
  relationshipType?: string;
  referenceDescription?: string;
}

const CanvasReferenceIndicator: React.FC<CanvasReferenceIndicatorProps> = ({
  currentCanvasId,
  conversationId,
  className = ''
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const { items, getOrCreateCanvasV4 } = useCanvasStore();

  // 현재 Canvas 찾기
  const currentCanvas = items.find(item => item.id === currentCanvasId);
  if (!currentCanvas) return null;

  // 참조 관계 정보 추출
  const referenceInfo = React.useMemo((): ReferenceInfo => {
    const continuityMeta = currentCanvas.metadata?.continuity;
    
    let baseCanvas: CanvasItem | undefined;
    const derivedCanvases: CanvasItem[] = [];

    // 1. 기반이 되는 Canvas 찾기
    if (continuityMeta?.baseCanvasId) {
      baseCanvas = items.find(item => item.id === continuityMeta.baseCanvasId);
    }

    // 2. 현재 Canvas를 기반으로 한 파생 Canvas들 찾기
    items.forEach(item => {
      const itemContinuityMeta = item.metadata?.continuity;
      if (itemContinuityMeta?.baseCanvasId === currentCanvasId) {
        derivedCanvases.push(item);
      }
    });

    return {
      baseCanvas,
      derivedCanvases,
      relationshipType: continuityMeta?.relationshipType,
      referenceDescription: continuityMeta?.referenceDescription
    };
  }, [currentCanvas, items, currentCanvasId]);

  // Canvas 타입별 이모지
  const getCanvasEmoji = (type: CanvasToolType): string => {
    switch (type) {
      case 'image': return '🖼️';
      case 'text': return '📝';
      case 'mindmap': return '🧠';
      case 'code': return '💻';
      case 'chart': return '📊';
      default: return '📄';
    }
  };

  // 관계 타입별 설명
  const getRelationshipDescription = (type?: string): string => {
    switch (type) {
      case 'extension': return '확장하여 생성';
      case 'modification': return '수정하여 생성';
      case 'variation': return '변형하여 생성';
      case 'reference': return '참조하여 생성';
      default: return '기반으로 생성';
    }
  };

  // Canvas로 이동
  const handleNavigateToCanvas = async (canvasId: string, canvasType: CanvasToolType) => {
    try {
      console.log('🔗 Canvas 참조 이동:', { canvasId, canvasType });
      const targetCanvas = items.find(item => item.id === canvasId);
      if (targetCanvas) {
        await getOrCreateCanvasV4(conversationId, canvasType, targetCanvas.content);
      }
    } catch (error) {
      console.error('❌ Canvas 이동 실패:', error);
    }
  };

  // 참조 관계가 없으면 렌더링하지 않음
  if (!referenceInfo.baseCanvas && referenceInfo.derivedCanvases.length === 0) {
    return null;
  }

  return (
    <div className={`bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 ${className}`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <GitBranch className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
            Canvas 연결 관계
          </span>
        </div>
        
        {(referenceInfo.baseCanvas || referenceInfo.derivedCanvases.length > 0) && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-amber-100 dark:hover:bg-amber-900/40 rounded transition-colors"
          >
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            )}
          </button>
        )}
      </div>

      {/* 기반 Canvas 정보 */}
      {referenceInfo.baseCanvas && (
        <div className="mb-3">
          <div className="flex items-center space-x-2 text-sm text-amber-700 dark:text-amber-300">
            <ArrowLeft className="w-3 h-3" />
            <span>
              이 작업은 
              <button
                onClick={() => handleNavigateToCanvas(referenceInfo.baseCanvas!.id, referenceInfo.baseCanvas!.type)}
                className="mx-1 px-2 py-1 bg-amber-100 dark:bg-amber-900/40 rounded hover:bg-amber-200 dark:hover:bg-amber-900/60 
                         text-amber-800 dark:text-amber-200 font-medium transition-colors inline-flex items-center space-x-1"
              >
                <span>{getCanvasEmoji(referenceInfo.baseCanvas.type)}</span>
                <span>
                  {(referenceInfo.baseCanvas.content as any)?.title || 
                   `${referenceInfo.baseCanvas.type} Canvas`}
                </span>
                <ExternalLink className="w-3 h-3" />
              </button>
              를 {getRelationshipDescription(referenceInfo.relationshipType)}되었습니다
            </span>
          </div>
          
          {referenceInfo.referenceDescription && isExpanded && (
            <div className="mt-2 pl-5 text-xs text-amber-600 dark:text-amber-400 italic">
              {referenceInfo.referenceDescription}
            </div>
          )}
        </div>
      )}

      {/* 파생 Canvas 정보 */}
      {referenceInfo.derivedCanvases.length > 0 && (
        <div>
          <div className="flex items-center space-x-2 text-sm text-amber-700 dark:text-amber-300 mb-2">
            <ArrowRight className="w-3 h-3" />
            <span>
              이 작업을 기반으로 
              <span className="font-medium text-amber-800 dark:text-amber-200">
                {referenceInfo.derivedCanvases.length}개의 후속 작업
              </span>
              이 생성되었습니다
            </span>
          </div>

          {isExpanded && (
            <div className="pl-5 space-y-2">
              {referenceInfo.derivedCanvases.map(canvas => {
                const derivedContinuityMeta = canvas.metadata?.continuity;
                
                return (
                  <div key={canvas.id} className="flex items-center justify-between">
                    <button
                      onClick={() => handleNavigateToCanvas(canvas.id, canvas.type)}
                      className="flex items-center space-x-2 px-2 py-1 bg-amber-100 dark:bg-amber-900/40 rounded 
                               hover:bg-amber-200 dark:hover:bg-amber-900/60 text-amber-800 dark:text-amber-200 
                               transition-colors text-sm"
                    >
                      <span>{getCanvasEmoji(canvas.type)}</span>
                      <span>
                        {(canvas.content as any)?.title || `${canvas.type} Canvas`}
                      </span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                    
                    {derivedContinuityMeta?.relationshipType && (
                      <div className="text-xs text-amber-600 dark:text-amber-400">
                        ({getRelationshipDescription(derivedContinuityMeta.relationshipType)})
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 도움말 */}
      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-amber-200 dark:border-amber-800">
          <div className="flex items-start space-x-2 text-xs text-amber-600 dark:text-amber-400">
            <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium mb-1">Canvas 연결 관계란?</p>
              <ul className="space-y-1 list-disc list-inside ml-2">
                <li><strong>확장:</strong> 기존 내용에 새로운 요소 추가</li>
                <li><strong>수정:</strong> 기존 내용의 일부를 변경</li>
                <li><strong>변형:</strong> 기존 내용을 다른 형태로 변환</li>
                <li><strong>참조:</strong> 기존 내용을 참고하여 새로운 작업</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CanvasReferenceIndicator;