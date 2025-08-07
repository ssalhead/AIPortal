/**
 * Canvas 상태 관리 Store
 */

import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type { CanvasItem, CanvasToolType, TextNote, ImageGeneration, MindMapNode } from '../types/canvas';

interface CanvasState {
  items: CanvasItem[];
  activeItemId: string | null;
  selectedTool: CanvasToolType | null;
  isCanvasOpen: boolean;
  
  // Actions
  addItem: (type: CanvasToolType, content: any) => void;
  updateItem: (id: string, updates: Partial<CanvasItem>) => void;
  deleteItem: (id: string) => void;
  clearCanvas: () => void;
  setActiveItem: (id: string | null) => void;
  setSelectedTool: (tool: CanvasToolType | null) => void;
  toggleCanvas: () => void;
  setCanvasOpen: (open: boolean) => void;
  
  // Helper methods
  getItemById: (id: string) => CanvasItem | undefined;
  exportCanvas: () => string;
  importCanvas: (data: string) => void;
}

export const useCanvasStore = create<CanvasState>((set, get) => ({
  items: [],
  activeItemId: null,
  selectedTool: null,
  isCanvasOpen: false,
  
  addItem: (type, content) => {
    const newItem: CanvasItem = {
      id: uuidv4(),
      type,
      content,
      position: { x: 50, y: 50 },
      size: type === 'text' ? { width: 300, height: 200 } : { width: 400, height: 300 },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    set((state) => ({
      items: [...state.items, newItem],
      activeItemId: newItem.id,
    }));
    
    return newItem.id;
  },
  
  updateItem: (id, updates) => {
    set((state) => ({
      items: state.items.map((item) =>
        item.id === id
          ? { ...item, ...updates, updatedAt: new Date().toISOString() }
          : item
      ),
    }));
  },
  
  deleteItem: (id) => {
    set((state) => ({
      items: state.items.filter((item) => item.id !== id),
      activeItemId: state.activeItemId === id ? null : state.activeItemId,
    }));
  },
  
  clearCanvas: () => {
    set({
      items: [],
      activeItemId: null,
      selectedTool: null,
    });
  },
  
  setActiveItem: (id) => {
    set({ activeItemId: id });
  },
  
  setSelectedTool: (tool) => {
    set({ selectedTool: tool });
  },
  
  toggleCanvas: () => {
    set((state) => ({ isCanvasOpen: !state.isCanvasOpen }));
  },
  
  setCanvasOpen: (open) => {
    set({ isCanvasOpen: open });
  },
  
  getItemById: (id) => {
    return get().items.find((item) => item.id === id);
  },
  
  exportCanvas: () => {
    const state = get();
    const exportData = {
      items: state.items,
      exportedAt: new Date().toISOString(),
      version: '1.0.0',
    };
    return JSON.stringify(exportData, null, 2);
  },
  
  importCanvas: (data) => {
    try {
      const parsed = JSON.parse(data);
      if (parsed.items && Array.isArray(parsed.items)) {
        set({
          items: parsed.items,
          activeItemId: null,
          selectedTool: null,
        });
      }
    } catch (error) {
      console.error('Failed to import canvas data:', error);
    }
  },
}));