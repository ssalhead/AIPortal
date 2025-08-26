/**
 * Canvas 히스토리 패널 컴포넌트 (v4.0)
 * 대화별 모든 Canvas 작업 히스토리 표시 및 관리
 */

import React, { useState, useEffect, useMemo } from 'react';
import { 
  Clock, 
  Search, 
  Filter, 
  RotateCcw, 
  Copy, 
  Trash2, 
  ExternalLink,
  Image,
  FileText,
  Zap,
  Code,
  BarChart3,
  ArrowRight
} from 'lucide-react';
import type { CanvasItem, CanvasToolType } from '../../types/canvas';
import { useCanvasStore } from '../../stores/canvasStore';
import { CanvasShareStrategy } from '../../services/CanvasShareStrategy';
import { CanvasContinuity } from '../../services/CanvasContinuity';

interface CanvasHistoryPanelProps {
  conversationId: string;
  isOpen: boolean;
  onClose: () => void;
  className?: string;
}

interface CanvasHistoryItem {
  canvas: CanvasItem;
  shareType: 'conversation' | 'request';
  canRestore: boolean;
  isActive: boolean;
  continuityInfo?: {
    baseCanvasId?: string;
    derivedCanvases: string[];
    relationshipType?: string;
  };
}

const CanvasHistoryPanel: React.FC<CanvasHistoryPanelProps> = ({
  conversationId,
  isOpen,
  onClose,
  className = ''
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<CanvasToolType | 'all'>('all');
  const [showOnlyActive, setShowOnlyActive] = useState(false);
  
  const { 
    items, 
    activeItemId,
    getOrCreateCanvasV4,
    restoreCanvasState,
    createContinuityCanvas,
    findReferencableCanvas
  } = useCanvasStore();

  // Canvas 히스토리 데이터 필터링 및 정리
  const canvasHistory = useMemo((): CanvasHistoryItem[] => {
    console.log('📋 Canvas 히스토리 계산:', { conversationId, totalItems: items.length });

    // 해당 대화의 Canvas만 필터링
    const conversationCanvas = items.filter(item => {
      const itemConversationId = (item.content as any)?.conversationId;
      return itemConversationId === conversationId;
    });

    console.log('🔍 대화 Canvas 필터링 결과:', conversationCanvas.length);

    // 연속성 관계 맵핑
    const continuityMap = CanvasContinuity.generateContinuityVisualization(items, conversationId);

    // 히스토리 아이템으로 변환
    const historyItems: CanvasHistoryItem[] = conversationCanvas.map(canvas => {
      const shareConfig = CanvasShareStrategy.getCanvasConfig(canvas.type);
      const isActive = canvas.id === activeItemId;
      
      // 연속성 정보 추출
      const continuityInfo = {
        baseCanvasId: canvas.metadata?.continuity?.baseCanvasId,
        derivedCanvases: continuityMap[canvas.id]?.derivatives.map((d: any) => d.canvasId) || [],
        relationshipType: canvas.metadata?.continuity?.relationshipType
      };

      return {
        canvas,
        shareType: shareConfig.shareType,
        canRestore: shareConfig.persistent,
        isActive,
        continuityInfo
      };
    });

    // 검색 필터 적용
    let filteredItems = historyItems;
    if (searchQuery) {
      filteredItems = historyItems.filter(item => {
        const canvas = item.canvas;
        const title = (canvas.content as any)?.title || '';
        const prompt = (canvas.content as any)?.prompt || '';
        const description = canvas.metadata?.description || '';
        
        const searchText = `${title} ${prompt} ${description}`.toLowerCase();
        return searchText.includes(searchQuery.toLowerCase());
      });
    }

    // 타입 필터 적용
    if (filterType !== 'all') {
      filteredItems = filteredItems.filter(item => item.canvas.type === filterType);
    }

    // 활성 상태 필터 적용
    if (showOnlyActive) {
      filteredItems = filteredItems.filter(item => item.isActive);
    }

    // 생성 시간순 정렬 (최신순)
    filteredItems.sort((a, b) => {
      return new Date(b.canvas.createdAt).getTime() - new Date(a.canvas.createdAt).getTime();
    });

    console.log('✅ 최종 Canvas 히스토리:', filteredItems.length);
    return filteredItems;
  }, [items, conversationId, activeItemId, searchQuery, filterType, showOnlyActive]);

  // Canvas 타입별 아이콘
  const getCanvasIcon = (type: CanvasToolType) => {
    switch (type) {
      case 'image': return <Image className="w-4 h-4" />;
      case 'text': return <FileText className="w-4 h-4" />;
      case 'mindmap': return <Zap className="w-4 h-4" />;
      case 'code': return <Code className="w-4 h-4" />;
      case 'chart': return <BarChart3 className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  // Canvas 타입별 색상
  const getCanvasTypeColor = (type: CanvasToolType) => {
    switch (type) {
      case 'image': return 'text-purple-600 bg-purple-50 dark:text-purple-400 dark:bg-purple-900/20';
      case 'text': return 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/20';
      case 'mindmap': return 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-900/20';
      case 'code': return 'text-orange-600 bg-orange-50 dark:text-orange-400 dark:bg-orange-900/20';
      case 'chart': return 'text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-900/20';
      default: return 'text-gray-600 bg-gray-50 dark:text-gray-400 dark:bg-gray-900/20';
    }
  };

  // Canvas 복원
  const handleRestoreCanvas = async (canvas: CanvasItem) => {
    try {
      console.log('🔄 Canvas 복원:', canvas.id);
      await getOrCreateCanvasV4(conversationId, canvas.type, canvas.content);
    } catch (error) {
      console.error('❌ Canvas 복원 실패:', error);
    }
  };

  // 연속성 Canvas 생성
  const handleCreateContinuity = async (baseCanvasId: string, targetType: CanvasToolType) => {
    try {
      const userRequest = prompt(`${targetType} Canvas를 생성하기 위한 요청을 입력해주세요:`);
      if (!userRequest) return;

      console.log('🔗 연속성 Canvas 생성:', { baseCanvasId, targetType, userRequest });
      const newCanvasId = await createContinuityCanvas(baseCanvasId, userRequest, targetType);
      console.log('✅ 연속성 Canvas 생성 완료:', newCanvasId);
    } catch (error) {
      console.error('❌ 연속성 Canvas 생성 실패:', error);
    }
  };

  if (!isOpen) return null;

  return (
    <div className={`fixed inset-y-0 right-0 w-96 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 shadow-xl z-50 flex flex-col ${className}`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <Clock className="w-5 h-5 text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Canvas 히스토리
          </h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          ✕
        </button>
      </div>

      {/* 검색 및 필터 */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 space-y-3">
        {/* 검색 */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Canvas 검색..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 
                     focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
        </div>

        {/* 필터 */}
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as CanvasToolType | 'all')}
            className="flex-1 px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm"
          >
            <option value="all">모든 타입</option>
            <option value="image">이미지</option>
            <option value="text">텍스트</option>
            <option value="mindmap">마인드맵</option>
            <option value="code">코드</option>
            <option value="chart">차트</option>
          </select>
          
          <label className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
            <input
              type="checkbox"
              checked={showOnlyActive}
              onChange={(e) => setShowOnlyActive(e.target.checked)}
              className="rounded border-gray-300"
            />
            <span>활성만</span>
          </label>
        </div>
      </div>

      {/* Canvas 목록 */}
      <div className="flex-1 overflow-y-auto">
        {canvasHistory.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>Canvas 히스토리가 없습니다</p>
            <p className="text-sm mt-2">Canvas 작업을 시작하면 여기에 표시됩니다</p>
          </div>
        ) : (
          <div className="p-4 space-y-3">
            {canvasHistory.map((item, index) => {
              const { canvas, shareType, canRestore, isActive, continuityInfo } = item;
              const typeColor = getCanvasTypeColor(canvas.type);
              
              return (
                <div
                  key={canvas.id}
                  className={`
                    p-4 rounded-lg border transition-all duration-200 hover:shadow-md
                    ${isActive 
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-500' 
                      : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900/50'
                    }
                  `}
                >
                  {/* Canvas 기본 정보 */}
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className={`p-2 rounded-lg ${typeColor}`}>
                        {getCanvasIcon(canvas.type)}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-900 dark:text-gray-100 text-sm">
                          {CanvasShareStrategy.generateCanvasTitle(canvas.type, canvas.content)}
                        </h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {shareType === 'conversation' ? '대화 공유' : '개별 작업'} • 
                          {new Date(canvas.createdAt).toLocaleDateString('ko-KR', {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </p>
                      </div>
                      {isActive && (
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                      )}
                    </div>
                  </div>

                  {/* 연속성 정보 */}
                  {continuityInfo?.baseCanvasId && (
                    <div className="mb-3 p-2 bg-amber-50 dark:bg-amber-900/20 rounded-md border border-amber-200 dark:border-amber-800">
                      <div className="flex items-center space-x-2 text-amber-700 dark:text-amber-400 text-xs">
                        <ArrowRight className="w-3 h-3" />
                        <span>
                          이전 Canvas를 {continuityInfo.relationshipType || '참조'}하여 생성
                        </span>
                      </div>
                    </div>
                  )}

                  {/* 액션 버튼들 */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {canRestore && (
                        <button
                          onClick={() => handleRestoreCanvas(canvas)}
                          className="flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400
                                   bg-blue-50 dark:bg-blue-900/20 rounded-md hover:bg-blue-100 dark:hover:bg-blue-900/40 
                                   transition-colors"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>복원</span>
                        </button>
                      )}

                      {CanvasShareStrategy.supportsContinuity(canvas.type) && (
                        <div className="flex items-center space-x-1">
                          {(['text', 'mindmap', 'code', 'chart'] as CanvasToolType[])
                            .filter(type => type !== canvas.type)
                            .slice(0, 2)
                            .map(targetType => (
                              <button
                                key={targetType}
                                onClick={() => handleCreateContinuity(canvas.id, targetType)}
                                className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 
                                         hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                                title={`${targetType} Canvas로 연속성 작업`}
                              >
                                {getCanvasIcon(targetType)}
                              </button>
                            ))
                          }
                        </div>
                      )}
                    </div>

                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => navigator.clipboard.writeText(canvas.id)}
                        className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 
                                 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                        title="Canvas ID 복사"
                      >
                        <Copy className="w-3 h-3" />
                      </button>
                      
                      <button
                        className="p-1.5 text-gray-400 hover:text-red-500 
                                 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                        title="Canvas 삭제"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 하단 통계 */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
          총 {canvasHistory.length}개 Canvas • 
          활성 {canvasHistory.filter(item => item.isActive).length}개 • 
          영구 보존 {canvasHistory.filter(item => item.canRestore).length}개
        </div>
      </div>
    </div>
  );
};

export default CanvasHistoryPanel;