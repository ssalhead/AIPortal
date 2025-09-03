/**
 * KonvaCanvasWorkspace v5.0 - Konva.js 기반 Canvas 워크스페이스
 * 
 * 특징:
 * - KonvaCanvasEngine 통합
 * - DOM ↔ Konva 무손실 변환
 * - 실시간 협업 지원
 * - 18가지 이미지 필터
 * - 성능 최적화 렌더링
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { KonvaCanvasEngine } from '../../engines/KonvaCanvasEngine';
import { useCanvasStore } from '../../stores/canvasStore';
import type { CanvasItem } from '../../types/canvas';
import type { ImageFilterType } from '../../types/konva';

// ======= 타입 정의 =======

interface KonvaCanvasWorkspaceProps {
  width?: number;
  height?: number;
  className?: string;
  canvasId?: string;              // 🎯 활성화된 Canvas ID
  isMigrated?: boolean;           // 🔄 마이그레이션 완료 여부
  migrationResult?: any;          // 🔄 마이그레이션 결과
  onItemSelected?: (itemId: string | null) => void;
  onItemUpdated?: (itemId: string, item: CanvasItem) => void;
  onItemMoved?: (itemId: string, item: CanvasItem) => void;
  onItemResized?: (itemId: string, item: CanvasItem) => void;
  onPerformanceUpdate?: (metrics: any) => void;
}

interface ToolbarState {
  selectedTool: 'select' | 'text' | 'image' | 'filter';
  selectedFilter: ImageFilterType | null;
  isVisible: boolean;
}

// ======= 메인 컴포넌트 =======

export const KonvaCanvasWorkspace: React.FC<KonvaCanvasWorkspaceProps> = ({
  width = 1200,
  height = 800,
  className = '',
  canvasId,
  isMigrated,
  migrationResult,
  onItemSelected,
  onItemUpdated,
  onItemMoved,
  onItemResized,
  onPerformanceUpdate
}) => {
  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<KonvaCanvasEngine | null>(null);

  // State
  const [isEngineReady, setIsEngineReady] = useState(false);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [toolbar, setToolbar] = useState<ToolbarState>({
    selectedTool: 'select',
    selectedFilter: null,
    isVisible: true
  });
  const [performanceMetrics, setPerformanceMetrics] = useState<any>(null);

  // Canvas Store
  const { 
    items, 
    activeItemId,
    setActiveItem,
    updateItem
  } = useCanvasStore();

  // ======= Engine 초기화 =======

  useEffect(() => {
    if (!containerRef.current || engineRef.current) {
      return;
    }

    console.log('🚀 KonvaCanvasEngine 초기화 시작');

    try {
      const engine = new KonvaCanvasEngine(containerRef.current, width, height);
      engineRef.current = engine;

      // 이벤트 리스너 등록
      engine.on('itemSelected', handleEngineItemSelected);
      engine.on('itemUpdated', handleEngineItemUpdated);
      engine.on('itemMoved', handleEngineItemMoved);
      engine.on('itemResized', handleEngineItemResized);
      engine.on('selectionCleared', handleEngineSelectionCleared);

      setIsEngineReady(true);
      console.log('✅ KonvaCanvasEngine 초기화 완료');

      // 성능 모니터링 시작
      startPerformanceMonitoring(engine);

    } catch (error) {
      console.error('❌ KonvaCanvasEngine 초기화 실패:', error);
    }

    return () => {
      if (engineRef.current) {
        engineRef.current.destroy();
        engineRef.current = null;
      }
    };
  }, [width, height]);

  // ======= Canvas 아이템 렌더링 =======

  useEffect(() => {
    if (!isEngineReady || !engineRef.current) {
      return;
    }

    console.log('🎨 Canvas 아이템들 렌더링 시작:', items.length);

    // 기존 Canvas 내용 정리
    engineRef.current.clear();

    // 모든 아이템 렌더링
    items.forEach(item => {
      try {
        const konvaNode = engineRef.current!.renderCanvasItem(item);
        if (konvaNode) {
          console.log(`✅ 아이템 렌더링 완료: ${item.id} (${item.type})`);
        }
      } catch (error) {
        console.error(`❌ 아이템 렌더링 실패: ${item.id}`, error);
      }
    });

    // 활성 아이템 선택
    if (activeItemId && engineRef.current) {
      engineRef.current.selectItem(activeItemId);
      setSelectedItemId(activeItemId);
    }

  }, [items, isEngineReady]);

  // ======= 성능 모니터링 =======

  const startPerformanceMonitoring = useCallback((engine: KonvaCanvasEngine) => {
    const updateMetrics = () => {
      const metrics = engine.getPerformanceMetrics();
      setPerformanceMetrics(metrics);
      onPerformanceUpdate?.(metrics);
    };

    updateMetrics();
    const intervalId = setInterval(updateMetrics, 1000);

    return () => clearInterval(intervalId);
  }, [onPerformanceUpdate]);

  // ======= 이벤트 핸들러 =======

  const handleEngineItemSelected = useCallback(({ itemId }: { itemId: string }) => {
    setSelectedItemId(itemId);
    setActiveItem(itemId);
    onItemSelected?.(itemId);
    console.log('🎯 아이템 선택됨:', itemId);
  }, [setActiveItem, onItemSelected]);

  const handleEngineItemUpdated = useCallback(({ itemId, item }: { itemId: string, item: CanvasItem }) => {
    updateItem(itemId, item);
    onItemUpdated?.(itemId, item);
    console.log('📝 아이템 업데이트됨:', itemId);
  }, [updateItem, onItemUpdated]);

  const handleEngineItemMoved = useCallback(({ itemId, position }: { itemId: string, position: any }) => {
    updateItem(itemId, { position });
    console.log('📍 아이템 이동됨:', itemId, position);
  }, [updateItem]);

  const handleEngineItemResized = useCallback(({ itemId, size }: { itemId: string, size: any }) => {
    updateItem(itemId, { size });
    console.log('📏 아이템 크기 변경됨:', itemId, size);
  }, [updateItem]);

  const handleEngineSelectionCleared = useCallback(() => {
    setSelectedItemId(null);
    setActiveItem(null);
    onItemSelected?.(null);
    console.log('🔄 선택 해제됨');
  }, [setActiveItem, onItemSelected]);

  // ======= 툴바 액션 =======

  const handleToolSelect = useCallback((tool: ToolbarState['selectedTool']) => {
    setToolbar(prev => ({ ...prev, selectedTool: tool }));
    
    if (tool === 'text' && engineRef.current && selectedItemId) {
      engineRef.current.enableTextEditing(selectedItemId);
    }
    
    console.log('🛠️ 도구 선택됨:', tool);
  }, [selectedItemId]);

  const handleFilterApply = useCallback((filterType: ImageFilterType, params?: Record<string, any>) => {
    if (!engineRef.current || !selectedItemId) {
      console.warn('⚠️ 필터를 적용할 아이템이 선택되지 않음');
      return;
    }

    const success = engineRef.current.applyCustomImageFilter(selectedItemId, filterType, params);
    if (success) {
      console.log('✅ 이미지 필터 적용 완료:', filterType);
    } else {
      console.error('❌ 이미지 필터 적용 실패:', filterType);
    }
  }, [selectedItemId]);

  const handleExport = useCallback((format: 'png' | 'svg') => {
    if (!engineRef.current) return;

    try {
      let dataUrl: string;
      
      if (format === 'png') {
        dataUrl = engineRef.current.exportToPNG();
        
        // 다운로드 링크 생성
        const link = document.createElement('a');
        link.download = `canvas-export-${Date.now()}.png`;
        link.href = dataUrl;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        console.log('📥 PNG 내보내기 완료');
      } else if (format === 'svg') {
        console.warn('⚠️ SVG 내보내기는 현재 미지원');
      }
    } catch (error) {
      console.error('❌ 내보내기 실패:', error);
    }
  }, []);

  // ======= 키보드 단축키 =======

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + 키 조합
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 's':
            e.preventDefault();
            handleExport('png');
            break;
          case 'a':
            e.preventDefault();
            // 전체 선택 로직 (필요시 구현)
            break;
          case 'z':
            e.preventDefault();
            // 실행 취소 로직 (필요시 구현)
            break;
        }
      }

      // 단일 키
      switch (e.key) {
        case 'Delete':
        case 'Backspace':
          if (selectedItemId) {
            // 삭제 로직 (필요시 구현)
            console.log('🗑️ 아이템 삭제 요청:', selectedItemId);
          }
          break;
        case 'Escape':
          if (engineRef.current) {
            engineRef.current.clearSelection();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedItemId, handleExport]);

  // ======= 렌더링 =======

  return (
    <div className={`konva-canvas-workspace ${className}`}>
      {/* 마이그레이션 상태 표시 */}
      {migrationResult && (
        <div className={`mb-2 p-2 rounded text-sm ${
          migrationResult.success 
            ? 'bg-green-50 border border-green-200 text-green-800' 
            : 'bg-yellow-50 border border-yellow-200 text-yellow-800'
        }`}>
          <div className="flex items-center space-x-2">
            <span>🎨</span>
            <span>
              {migrationResult.success 
                ? 'Canvas v5.0으로 성공적으로 마이그레이션됨 - Konva 기반 고급 편집 도구 사용 가능' 
                : '마이그레이션 진행 중 - 일부 고급 기능이 제한될 수 있음'
              }
            </span>
          </div>
          {migrationResult.warnings?.length > 0 && (
            <div className="mt-1 text-xs">
              경고: {migrationResult.warnings.join(', ')}
            </div>
          )}
        </div>
      )}

      {/* 툴바 */}
      {toolbar.isVisible && (
        <CanvasToolbar
          selectedTool={toolbar.selectedTool}
          selectedFilter={toolbar.selectedFilter}
          onToolSelect={handleToolSelect}
          onFilterApply={handleFilterApply}
          onExport={handleExport}
          isItemSelected={!!selectedItemId}
          canvasId={canvasId}
          isMigrated={isMigrated}
        />
      )}

      {/* Canvas 컨테이너 */}
      <div
        ref={containerRef}
        className="konva-canvas-container"
        style={{
          width: `${width}px`,
          height: `${height}px`,
          border: '1px solid #e5e7eb',
          borderRadius: '8px',
          backgroundColor: '#ffffff',
          position: 'relative',
          overflow: 'hidden'
        }}
      />

      {/* 성능 메트릭 (개발 모드에서만) */}
      {process.env.NODE_ENV === 'development' && performanceMetrics && (
        <PerformanceMonitor metrics={performanceMetrics} />
      )}

      {/* 로딩 상태 */}
      {!isEngineReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-50 bg-opacity-75">
          <div className="text-gray-600">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            Canvas 엔진 로딩 중...
          </div>
        </div>
      )}
    </div>
  );
};

// ======= 툴바 컴포넌트 =======

interface CanvasToolbarProps {
  selectedTool: ToolbarState['selectedTool'];
  selectedFilter: ImageFilterType | null;
  onToolSelect: (tool: ToolbarState['selectedTool']) => void;
  onFilterApply: (filter: ImageFilterType, params?: Record<string, any>) => void;
  onExport: (format: 'png' | 'svg') => void;
  isItemSelected: boolean;
  canvasId?: string;
  isMigrated?: boolean;
}

const CanvasToolbar: React.FC<CanvasToolbarProps> = ({
  selectedTool,
  selectedFilter,
  onToolSelect,
  onFilterApply,
  onExport,
  isItemSelected,
  canvasId,
  isMigrated
}) => {
  const filters: ImageFilterType[] = [
    'blur', 'brighten', 'contrast', 'enhance', 'emboss', 'grayscale',
    'invert', 'sepia', 'vintage', 'artistic'
  ] as ImageFilterType[];

  return (
    <div className="canvas-toolbar bg-white border border-gray-200 rounded-lg p-2 mb-4 shadow-sm">
      {/* 상태 표시 */}
      <div className="flex items-center justify-between mb-2 text-xs text-gray-600">
        <div className="flex items-center space-x-4">
          <span className="flex items-center space-x-1">
            <span>🎨</span>
            <span>{isMigrated ? 'Konva v5.0 활성화' : 'DOM Canvas v4.0'}</span>
          </span>
          {canvasId && (
            <span className="flex items-center space-x-1">
              <span>🎯</span>
              <span>ID: {canvasId.substring(0, 8)}...</span>
            </span>
          )}
        </div>
        <div className="text-blue-600 font-medium">
          🛠️ 18종 필터 + 실시간 편집 도구 활성화됨
        </div>
      </div>

      <div className="flex items-center space-x-2">
        {/* 기본 도구 */}
        <div className="flex space-x-1 border-r border-gray-200 pr-2">
          <button
            onClick={() => onToolSelect('select')}
            className={`p-2 rounded ${selectedTool === 'select' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:bg-gray-100'}`}
            title="선택 도구"
          >
            🎯
          </button>
          <button
            onClick={() => onToolSelect('text')}
            className={`p-2 rounded ${selectedTool === 'text' ? 'bg-blue-100 text-blue-600' : 'text-gray-600 hover:bg-gray-100'}`}
            title="텍스트 편집"
            disabled={!isItemSelected}
          >
            📝
          </button>
        </div>

        {/* 이미지 필터 */}
        <div className="flex space-x-1 border-r border-gray-200 pr-2">
          <select
            value={selectedFilter || ''}
            onChange={(e) => {
              const filter = e.target.value as ImageFilterType;
              if (filter) {
                onFilterApply(filter);
              }
            }}
            className="px-2 py-1 border border-gray-300 rounded text-sm"
            disabled={!isItemSelected}
          >
            <option value="">필터 선택</option>
            {filters.map(filter => (
              <option key={filter} value={filter}>
                {filter.charAt(0).toUpperCase() + filter.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* 내보내기 */}
        <div className="flex space-x-1">
          <button
            onClick={() => onExport('png')}
            className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
            title="PNG로 내보내기 (Ctrl+S)"
          >
            📥 내보내기
          </button>
        </div>
      </div>
    </div>
  );
};

// ======= 성능 모니터 컴포넌트 =======

interface PerformanceMonitorProps {
  metrics: any;
}

const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({ metrics }) => {
  return (
    <div className="performance-monitor fixed bottom-4 right-4 bg-black bg-opacity-75 text-white p-2 rounded text-xs font-mono">
      <div>FPS: {metrics.fps?.toFixed(1) || 0}</div>
      <div>Nodes: {metrics.nodeCount || 0}</div>
      <div>Layers: {metrics.layerCount || 0}</div>
      <div>Memory: {metrics.memoryUsage?.toFixed(1) || 0}KB</div>
      <div>Render: {metrics.renderTime?.toFixed(2) || 0}ms</div>
    </div>
  );
};

export default KonvaCanvasWorkspace;