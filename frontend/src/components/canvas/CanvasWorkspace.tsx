/**
 * Canvas 워크스페이스 컴포넌트
 */

import React, { useState, useRef, useEffect } from 'react';
import { 
  FileText, 
  Image, 
  GitBranch, 
  Code, 
  BarChart3,
  Plus,
  Trash2,
  Download,
  Upload,
  X,
  Save,
  Edit3,
  Palette,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { useCanvasStore } from '../../stores/canvasStore';
import type { CanvasToolType } from '../../types/canvas';
import { TextNoteEditor } from './TextNoteEditor';
import { ImageGenerator } from './ImageGenerator';
import { MindMapEditor } from './MindMapEditor';

const TOOL_ICONS: Record<CanvasToolType, React.ReactNode> = {
  text: <FileText className="w-4 h-4" />,
  image: <Image className="w-4 h-4" />,
  mindmap: <GitBranch className="w-4 h-4" />,
  code: <Code className="w-4 h-4" />,
  chart: <BarChart3 className="w-4 h-4" />
};

const TOOL_NAMES: Record<CanvasToolType, string> = {
  text: '텍스트 노트',
  image: '이미지 생성',
  mindmap: '마인드맵',
  code: '코드 편집기',
  chart: '차트'
};

export const CanvasWorkspace: React.FC = () => {
  const {
    items,
    activeItemId,
    updateItem,
    deleteItem,
    clearCanvas,
    setActiveItem,
    exportCanvas,
    importCanvas,
    hasActiveContent,
    closeCanvas
  } = useCanvasStore();
  
  const [isFullscreen, setIsFullscreen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const activeItem = items.find(item => item.id === activeItemId);
  
  // Canvas에 활성 콘텐츠가 없으면 렌더링하지 않음
  if (!hasActiveContent()) {
    return null;
  }
  
  const handleExport = () => {
    const data = exportCanvas();
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `canvas-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };
  
  const handleImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        importCanvas(content);
      };
      reader.readAsText(file);
    }
  };
  
  const handleDeleteItem = (id: string) => {
    if (confirm('이 아이템을 삭제하시겠습니까?')) {
      deleteItem(id);
    }
  };
  
  return (
    <div className={`flex flex-col h-full ${isFullscreen ? 'fixed inset-0 z-50' : ''}`}>
      {/* 최소화된 Canvas 헤더 */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            {activeItem ? (
              activeItem.type === 'text' ? activeItem.content.title :
              activeItem.type === 'image' ? '이미지 생성' :
              activeItem.type === 'mindmap' ? '마인드맵' :
              'Canvas'
            ) : 'Canvas'}
          </h3>
          <div className="flex items-center gap-1 px-2 py-1 bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-full text-xs font-medium">
            {TOOL_ICONS[activeItem?.type || 'text']}
            <span className="ml-1">{TOOL_NAMES[activeItem?.type || 'text']}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title={isFullscreen ? '축소' : '전체화면'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={closeCanvas}
            className="p-1.5 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title="Canvas 닫기"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      
      {/* Canvas 콘텐츠 영역 - 전체 화면 활용 */}
      <div className="flex-1 p-6 overflow-y-auto bg-slate-50 dark:bg-slate-900">
        {activeItem ? (
          <div className="max-w-6xl mx-auto">
            {activeItem.type === 'text' && (
              <TextNoteEditor
                item={activeItem}
                onUpdate={(updates) => updateItem(activeItem.id, updates)}
              />
            )}
            {activeItem.type === 'image' && (
              <ImageGenerator
                item={activeItem}
                onUpdate={(updates) => updateItem(activeItem.id, updates)}
              />
            )}
            {activeItem.type === 'mindmap' && (
              <MindMapEditor
                item={activeItem}
                onUpdate={(updates) => updateItem(activeItem.id, updates)}
              />
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 bg-slate-200 dark:bg-slate-700 rounded-full flex items-center justify-center">
                <Palette className="w-8 h-8 text-slate-400" />
              </div>
              <p className="text-slate-600 dark:text-slate-400 font-medium">
                Canvas가 준비되었습니다
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-500 mt-1">
                AI 작업 결과가 여기에 표시됩니다
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};