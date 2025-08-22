/**
 * Canvas 상태 관리 Store
 */

import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type { CanvasItem, CanvasToolType, TextNote, ImageGeneration, MindMapNode } from '../types/canvas';

// 백엔드 크기 포맷 → 프론트엔드 SIZE_OPTIONS 포맷 변환
function convertBackendSizeToFrontend(backendSize: string): string {
  const sizeMap: Record<string, string> = {
    '512x512': '1K_1:1',
    '1024x1024': '1K_1:1',
    '1024x768': '1K_4:3',
    '768x1024': '1K_3:4',
    '1920x1080': '1K_16:9',
    '1080x1920': '1K_9:16',
    // 2K 추가 매핑
    '2048x2048': '2K_1:1',
    '2048x1536': '2K_4:3',
    '1536x2048': '2K_3:4'
  };
  
  return sizeMap[backendSize] || '1K_1:1'; // 기본값
}

interface CanvasState {
  items: CanvasItem[];
  activeItemId: string | null;
  isCanvasOpen: boolean;
  
  // Actions - AI 주도 Canvas 관리
  addItem: (type: CanvasToolType, content: any) => void;
  updateItem: (id: string, updates: Partial<CanvasItem>) => void;
  deleteItem: (id: string) => void;
  clearCanvas: () => void;
  setActiveItem: (id: string | null) => void;
  
  // 조건부 Canvas 활성화 (빈 Canvas 방지)
  openWithArtifact: (artifactId: string) => void;
  autoActivateCanvas: (canvasData: any) => string; // Canvas 데이터로 자동 활성화, 아이템 ID 반환
  closeCanvas: () => void;
  
  // Helper methods
  getItemById: (id: string) => CanvasItem | undefined;
  hasActiveContent: () => boolean; // Canvas에 활성 콘텐츠가 있는지 확인
  exportCanvas: () => string;
  importCanvas: (data: string) => void;
}

export const useCanvasStore = create<CanvasState>((set, get) => ({
  items: [],
  activeItemId: null,
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
    });
  },
  
  setActiveItem: (id) => {
    set({ activeItemId: id });
  },
  
  // 조건부 Canvas 활성화 함수들
  openWithArtifact: (artifactId) => {
    const item = get().getItemById(artifactId);
    if (item) {
      set({ 
        isCanvasOpen: true,
        activeItemId: artifactId 
      });
    }
  },
  
  autoActivateCanvas: (canvasData) => {
    // Canvas 데이터에서 타입과 콘텐츠 추출
    const { type, title, description, image_data } = canvasData;
    
    let content;
    let canvasType: CanvasToolType = 'text'; // 기본값
    
    if (type === 'image' && image_data) {
      canvasType = 'image';
      
      // 이미지 URL 추출 - 백엔드에서 여러 방식으로 올 수 있음
      let imageUrl = null;
      
      // 1. 직접 image_urls 배열에서 추출 (새로운 방식)
      if (image_data.image_urls && image_data.image_urls.length > 0) {
        imageUrl = image_data.image_urls[0];
      }
      // 2. images 배열에서 URL 추출 (문자열 URL 직접 지원)
      else if (image_data.images && image_data.images.length > 0) {
        // images 배열에 URL 문자열이 직접 들어있는 경우와 객체인 경우 모두 지원
        const firstImage = image_data.images[0];
        imageUrl = typeof firstImage === 'string' 
          ? firstImage  // 문자열 URL 직접 사용
          : firstImage?.url;  // 객체인 경우 .url 속성 사용
      }
      // 3. generation_result에서 추출 (fallback, 동일한 로직 적용)
      else if (image_data.generation_result?.images?.[0]) {
        const firstImage = image_data.generation_result.images[0];
        imageUrl = typeof firstImage === 'string'
          ? firstImage  // 문자열 URL 직접 사용
          : firstImage?.url;  // 객체인 경우 .url 속성 사용
      }
      
      console.log('🖼️ Canvas Store - 이미지 URL 추출:', {
        image_urls: image_data.image_urls,
        images: image_data.images,
        generation_result: image_data.generation_result,
        finalUrl: imageUrl,
        imageUrlFound: !!imageUrl,
        imageUrlSource: imageUrl ? 
          (image_data.image_urls?.length > 0 ? 'image_urls' :
           image_data.images?.length > 0 ? 'images' : 'generation_result') : 'none'
      });
      
      if (!imageUrl) {
        console.warn('⚠️ Canvas Store - 이미지 URL을 찾을 수 없습니다! 자동 이미지 표시가 되지 않을 수 있습니다.');
      } else {
        console.log('✅ Canvas Store - 이미지 URL 추출 성공:', imageUrl);
      }
      
      // 백엔드 크기 포맷 → 프론트엔드 SIZE_OPTIONS 포맷 변환
      const backendSize = image_data.size || '1024x1024';
      const frontendSize = convertBackendSizeToFrontend(backendSize);
      
      content = {
        prompt: image_data.prompt || title,
        negativePrompt: '',
        style: image_data.style || 'realistic',
        size: frontendSize,
        status: image_data.status || 'completed',
        imageUrl: imageUrl,
        generation_result: image_data.generation_result
      };
    } else if (type === 'mindmap') {
      canvasType = 'mindmap';
      content = canvasData.elements || { id: 'root', label: title, children: [] };
    } else {
      // 기본적으로 텍스트 노트로 처리
      canvasType = 'text';
      content = {
        title: title || '새 노트',
        content: description || '',
        formatting: {}
      };
    }
    
    // 새 아이템 생성
    const newItem: CanvasItem = {
      id: uuidv4(),
      type: canvasType,
      content,
      position: { x: 50, y: 50 },
      size: canvasType === 'text' ? { width: 300, height: 200 } : { width: 400, height: 300 },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    // Canvas 자동 활성화
    set((state) => ({
      items: [...state.items, newItem],
      activeItemId: newItem.id,
      isCanvasOpen: true
    }));
    
    return newItem.id;
  },
  
  closeCanvas: () => {
    set({ 
      isCanvasOpen: false,
      activeItemId: null 
    });
  },
  
  getItemById: (id) => {
    return get().items.find((item) => item.id === id);
  },
  
  hasActiveContent: () => {
    const state = get();
    return state.activeItemId !== null && state.items.length > 0;
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