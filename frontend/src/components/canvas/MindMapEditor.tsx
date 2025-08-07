/**
 * 마인드맵 편집기 컴포넌트
 */

import React, { useState, useRef, useEffect } from 'react';
import { 
  GitBranch, 
  Plus, 
  Minus,
  Edit3,
  Trash2,
  Download,
  ZoomIn,
  ZoomOut,
  Maximize,
  ChevronRight,
  ChevronDown,
  Circle,
  Square,
  Hexagon
} from 'lucide-react';
import type { CanvasItem, MindMapNode } from '../../types/canvas';

interface MindMapEditorProps {
  item: CanvasItem;
  onUpdate: (updates: Partial<CanvasItem>) => void;
}

const NODE_COLORS = [
  '#3B82F6', // blue
  '#10B981', // green
  '#F59E0B', // yellow
  '#EF4444', // red
  '#8B5CF6', // purple
  '#EC4899', // pink
  '#06B6D4', // cyan
  '#F97316', // orange
];

const NODE_SHAPES = ['circle', 'square', 'hexagon'];

export const MindMapEditor: React.FC<MindMapEditorProps> = ({ item, onUpdate }) => {
  const [rootNode, setRootNode] = useState<MindMapNode>(item.content || {
    id: 'root',
    label: '중심 주제',
    children: []
  });
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState('');
  const [zoom, setZoom] = useState(100);
  const canvasRef = useRef<HTMLDivElement>(null);
  
  const handleAddNode = (parentId: string) => {
    const newNode: MindMapNode = {
      id: `node-${Date.now()}`,
      label: '새 노드',
      children: [],
      color: NODE_COLORS[Math.floor(Math.random() * NODE_COLORS.length)]
    };
    
    const addToParent = (node: MindMapNode): MindMapNode => {
      if (node.id === parentId) {
        return {
          ...node,
          children: [...(node.children || []), newNode]
        };
      }
      return {
        ...node,
        children: node.children?.map(child => addToParent(child))
      };
    };
    
    const updatedRoot = addToParent(rootNode);
    setRootNode(updatedRoot);
    onUpdate({ content: updatedRoot });
    setEditingNodeId(newNode.id);
    setEditingLabel('새 노드');
  };
  
  const handleDeleteNode = (nodeId: string) => {
    if (nodeId === 'root') {
      alert('루트 노드는 삭제할 수 없습니다.');
      return;
    }
    
    const deleteFromTree = (node: MindMapNode): MindMapNode | null => {
      if (node.children) {
        const filteredChildren = node.children
          .map(child => child.id === nodeId ? null : deleteFromTree(child))
          .filter(child => child !== null) as MindMapNode[];
        return { ...node, children: filteredChildren };
      }
      return node;
    };
    
    const updatedRoot = deleteFromTree(rootNode);
    if (updatedRoot) {
      setRootNode(updatedRoot);
      onUpdate({ content: updatedRoot });
    }
    setSelectedNodeId(null);
  };
  
  const handleUpdateNodeLabel = (nodeId: string, newLabel: string) => {
    const updateInTree = (node: MindMapNode): MindMapNode => {
      if (node.id === nodeId) {
        return { ...node, label: newLabel };
      }
      return {
        ...node,
        children: node.children?.map(child => updateInTree(child))
      };
    };
    
    const updatedRoot = updateInTree(rootNode);
    setRootNode(updatedRoot);
    onUpdate({ content: updatedRoot });
    setEditingNodeId(null);
    setEditingLabel('');
  };
  
  const handleToggleCollapse = (nodeId: string) => {
    const toggleInTree = (node: MindMapNode): MindMapNode => {
      if (node.id === nodeId) {
        return { ...node, collapsed: !node.collapsed };
      }
      return {
        ...node,
        children: node.children?.map(child => toggleInTree(child))
      };
    };
    
    const updatedRoot = toggleInTree(rootNode);
    setRootNode(updatedRoot);
    onUpdate({ content: updatedRoot });
  };
  
  const handleExport = () => {
    const exportData = {
      type: 'mindmap',
      data: rootNode,
      exportedAt: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mindmap-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };
  
  const renderNode = (node: MindMapNode, level: number = 0): JSX.Element => {
    const hasChildren = node.children && node.children.length > 0;
    const isEditing = editingNodeId === node.id;
    const isSelected = selectedNodeId === node.id;
    
    return (
      <div key={node.id} className={`${level > 0 ? 'ml-8' : ''}`}>
        <div className="flex items-center gap-2 mb-2">
          {hasChildren && (
            <button
              onClick={() => handleToggleCollapse(node.id)}
              className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
            >
              {node.collapsed ? (
                <ChevronRight className="w-4 h-4 text-slate-500" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-500" />
              )}
            </button>
          )}
          
          <div
            onClick={() => setSelectedNodeId(node.id)}
            className={`
              inline-flex items-center gap-2 px-4 py-2 rounded-lg cursor-pointer transition-all
              ${isSelected 
                ? 'ring-2 ring-blue-500 ring-offset-2 dark:ring-offset-slate-800' 
                : ''
              }
            `}
            style={{ 
              backgroundColor: node.color || NODE_COLORS[level % NODE_COLORS.length] + '20',
              borderLeft: `3px solid ${node.color || NODE_COLORS[level % NODE_COLORS.length]}`
            }}
          >
            {isEditing ? (
              <input
                type="text"
                value={editingLabel}
                onChange={(e) => setEditingLabel(e.target.value)}
                onBlur={() => handleUpdateNodeLabel(node.id, editingLabel)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleUpdateNodeLabel(node.id, editingLabel);
                  } else if (e.key === 'Escape') {
                    setEditingNodeId(null);
                    setEditingLabel('');
                  }
                }}
                className="bg-transparent border-none outline-none font-medium text-slate-800 dark:text-slate-200"
                autoFocus
              />
            ) : (
              <span 
                className="font-medium text-slate-800 dark:text-slate-200"
                onDoubleClick={() => {
                  setEditingNodeId(node.id);
                  setEditingLabel(node.label);
                }}
              >
                {node.label}
              </span>
            )}
            
            {node.children && node.children.length > 0 && (
              <span className="text-xs text-slate-500 dark:text-slate-400">
                ({node.children.length})
              </span>
            )}
          </div>
          
          {isSelected && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => handleAddNode(node.id)}
                className="p-1 text-green-600 hover:bg-green-100 dark:hover:bg-green-900/20 rounded transition-colors"
                title="자식 노드 추가"
              >
                <Plus className="w-4 h-4" />
              </button>
              <button
                onClick={() => {
                  setEditingNodeId(node.id);
                  setEditingLabel(node.label);
                }}
                className="p-1 text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/20 rounded transition-colors"
                title="편집"
              >
                <Edit3 className="w-4 h-4" />
              </button>
              {node.id !== 'root' && (
                <button
                  onClick={() => handleDeleteNode(node.id)}
                  className="p-1 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/20 rounded transition-colors"
                  title="삭제"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          )}
        </div>
        
        {!node.collapsed && node.children && node.children.length > 0 && (
          <div className="border-l-2 border-slate-200 dark:border-slate-700 ml-2 pl-2">
            {node.children.map(child => renderNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  };
  
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg h-full flex flex-col">
      {/* 헤더 */}
      <div className="border-b border-slate-200 dark:border-slate-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-green-500 to-teal-500 rounded-lg">
              <GitBranch className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                마인드맵
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                아이디어를 시각적으로 정리합니다
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setZoom(Math.max(50, zoom - 10))}
              className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              title="축소"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-sm text-slate-600 dark:text-slate-400 w-12 text-center">
              {zoom}%
            </span>
            <button
              onClick={() => setZoom(Math.min(200, zoom + 10))}
              className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              title="확대"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom(100)}
              className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              title="원본 크기"
            >
              <Maximize className="w-4 h-4" />
            </button>
            <div className="w-px h-6 bg-slate-300 dark:bg-slate-600" />
            <button
              onClick={handleExport}
              className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              title="내보내기"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
      
      {/* 도구 모음 */}
      <div className="flex items-center gap-2 p-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
        <button
          onClick={() => handleAddNode('root')}
          className="px-3 py-1 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          <span className="text-sm font-medium">루트에 추가</span>
        </button>
        
        <div className="ml-auto text-xs text-slate-500 dark:text-slate-400">
          팁: 노드를 더블클릭하여 편집, 선택 후 + 버튼으로 자식 노드 추가
        </div>
      </div>
      
      {/* 마인드맵 캔버스 */}
      <div 
        ref={canvasRef}
        className="flex-1 overflow-auto p-8 bg-slate-50 dark:bg-slate-900"
        style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top left' }}
      >
        {renderNode(rootNode)}
      </div>
      
      {/* 상태 바 */}
      <div className="border-t border-slate-200 dark:border-slate-700 px-4 py-2">
        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-4">
            <span>총 {countNodes(rootNode)} 노드</span>
            <span>깊이 {getTreeDepth(rootNode)} 레벨</span>
          </div>
          <div>
            마지막 저장: {new Date(item.updatedAt).toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
};

// 헬퍼 함수들
function countNodes(node: MindMapNode): number {
  let count = 1;
  if (node.children) {
    node.children.forEach(child => {
      count += countNodes(child);
    });
  }
  return count;
}

function getTreeDepth(node: MindMapNode, currentDepth: number = 0): number {
  if (!node.children || node.children.length === 0) {
    return currentDepth;
  }
  return Math.max(...node.children.map(child => getTreeDepth(child, currentDepth + 1)));
}