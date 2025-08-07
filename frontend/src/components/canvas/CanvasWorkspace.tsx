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
    selectedTool,
    addItem,
    updateItem,
    deleteItem,
    clearCanvas,
    setActiveItem,
    setSelectedTool,
    exportCanvas,
    importCanvas
  } = useCanvasStore();
  
  const [isFullscreen, setIsFullscreen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const activeItem = items.find(item => item.id === activeItemId);
  
  const handleToolSelect = (tool: CanvasToolType) => {
    if (selectedTool === tool) {
      setSelectedTool(null);
    } else {
      setSelectedTool(tool);
      // 도구 선택 시 바로 새 아이템 생성
      if (tool === 'text') {
        addItem('text', { title: '새 노트', content: '', formatting: {} });
      } else if (tool === 'image') {
        addItem('image', { prompt: '', status: 'pending' });
      } else if (tool === 'mindmap') {
        addItem('mindmap', { 
          id: 'root', 
          label: '중심 주제',
          children: []
        });
      }
    }
  };
  
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
      {/* Canvas 헤더 */}
      <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Canvas
          </h3>
          <div className="flex items-center gap-1 px-2 py-1 bg-orange-100 dark:bg-orange-900/20 text-orange-700 dark:text-orange-300 rounded-full text-xs font-medium">
            <Palette className="w-3 h-3" />
            <span>활성</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title="불러오기"
          >
            <Upload className="w-4 h-4" />
          </button>
          <button
            onClick={handleExport}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title="내보내기"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={clearCanvas}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title="전체 삭제"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title={isFullscreen ? '축소' : '전체화면'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
        
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={handleImport}
          className="hidden"
        />
      </div>
      
      {/* Canvas 도구 모음 */}
      <div className="flex items-center gap-2 p-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
        {(Object.keys(TOOL_ICONS) as CanvasToolType[]).map((tool) => (
          <button
            key={tool}
            onClick={() => handleToolSelect(tool)}
            disabled={tool === 'code' || tool === 'chart'} // 임시로 비활성화
            className={`
              flex items-center gap-2 px-3 py-2 rounded-lg transition-all
              ${selectedTool === tool 
                ? 'bg-blue-500 text-white' 
                : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
              }
              ${(tool === 'code' || tool === 'chart') ? 'opacity-50 cursor-not-allowed' : ''}
            `}
            title={TOOL_NAMES[tool]}
          >
            {TOOL_ICONS[tool]}
            <span className="text-sm font-medium">{TOOL_NAMES[tool]}</span>
            {(tool === 'code' || tool === 'chart') && (
              <span className="text-xs opacity-75">(준비중)</span>
            )}
          </button>
        ))}
      </div>
      
      {/* Canvas 작업 영역 */}
      <div className="flex-1 overflow-hidden bg-slate-100 dark:bg-slate-900">
        {items.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-4 bg-slate-200 dark:bg-slate-700 rounded-full flex items-center justify-center">
                <Plus className="w-10 h-10 text-slate-400" />
              </div>
              <p className="text-slate-600 dark:text-slate-400 font-medium mb-2">
                Canvas가 비어 있습니다
              </p>
              <p className="text-sm text-slate-500 dark:text-slate-500">
                위의 도구를 선택하여 시작하세요
              </p>
            </div>
          </div>
        ) : (
          <div className="h-full flex">
            {/* 아이템 목록 */}
            <div className="w-64 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 overflow-y-auto">
              <div className="p-3">
                <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Canvas 아이템 ({items.length})
                </h4>
                <div className="space-y-2">
                  {items.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => setActiveItem(item.id)}
                      className={`
                        p-3 rounded-lg cursor-pointer transition-all
                        ${activeItemId === item.id
                          ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700'
                          : 'bg-slate-50 dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-700'
                        }
                      `}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-slate-500 dark:text-slate-400">
                            {TOOL_ICONS[item.type]}
                          </span>
                          <div>
                            <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                              {item.type === 'text' && item.content.title}
                              {item.type === 'image' && (item.content.prompt || '이미지')}
                              {item.type === 'mindmap' && '마인드맵'}
                            </p>
                            <p className="text-xs text-slate-500 dark:text-slate-500">
                              {new Date(item.updatedAt).toLocaleTimeString()}
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteItem(item.id);
                          }}
                          className="p-1 text-slate-400 hover:text-red-500 transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            {/* 편집 영역 */}
            <div className="flex-1 p-6 overflow-y-auto">
              {activeItem ? (
                <div className="max-w-4xl mx-auto">
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
                  <p className="text-slate-500 dark:text-slate-400">
                    왼쪽에서 아이템을 선택하거나 새로 만드세요
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};