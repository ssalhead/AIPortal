/**
 * Canvas Persistence v5.0 - 영구 보존 시스템
 * 데이터 영속성 및 자동 저장 기능 제공
 */

import type { CanvasState, SyncTask } from './CanvasCore';
import type { CanvasItem, CanvasToolType } from '../../types/canvas';
import { CANVAS_DEFAULTS } from './CanvasCore';
import { ConversationCanvasManager } from '../../services/conversationCanvasManager';
import { CanvasShareStrategy } from '../../services/CanvasShareStrategy';
import { CanvasContinuity } from '../../services/CanvasContinuity';
import { CanvasAutoSave } from '../../services/CanvasAutoSave';

// Canvas Auto Save 콜백 함수 정의
const canvasAutoSaveCallback = async (canvasId: string, canvasData: any) => {
  try {
    console.log('📁 Canvas Auto Save 실행:', { canvasId, dataKeys: Object.keys(canvasData) });
    // 실제 자동 저장 로직은 여기에 구현
    // await ConversationCanvasManager.saveCanvas(canvasId, canvasData);
  } catch (error) {
    console.error('❌ Canvas Auto Save 실패:', error);
  }
};

// Canvas Auto Save 시스템 초기화
const canvasAutoSave = new CanvasAutoSave(canvasAutoSaveCallback);

/**
 * Canvas 영구 보존 시스템 구현부
 * Zustand Store에 mixin될 메서드들을 제공
 */
export const createCanvasPersistenceSlice = (
  set: (partial: Partial<CanvasState>) => void,
  get: () => CanvasState
) => ({
  // ======= 영구 보존 시스템 초기 상태 =======
  isPersistenceEnabled: true,
  autoSaveEnabled: true,
  
  // ======= 영구 보존 시스템 메서드 =======
  
  /**
   * 영구 Canvas 생성
   * 백엔드와 연동하여 Canvas 데이터를 영구적으로 저장
   */
  createPermanentCanvas: async (
    conversationId: string, 
    type: CanvasToolType, 
    canvasData?: any
  ): Promise<string> => {
    const state = get();
    
    try {
      console.log('🚀 영구 Canvas 생성 시작:', { conversationId, type, canvasData });
      
      // 1. Canvas 데이터 검증 및 정규화
      const normalizedData = canvasData || {};
      
      // 2. ConversationCanvasManager를 통한 영구 저장
      let canvasItem: CanvasItem;
      
      if (type === 'text') {
        canvasItem = await ConversationCanvasManager.createTextCanvas(
          conversationId, 
          normalizedData.text || '새 텍스트 노트'
        );
      } else if (type === 'image') {
        canvasItem = await ConversationCanvasManager.createImageCanvas(
          conversationId, 
          normalizedData.images || [],
          normalizedData.prompt || ''
        );
      } else if (type === 'mindmap') {
        canvasItem = await ConversationCanvasManager.createMindMapCanvas(
          conversationId, 
          normalizedData.nodes || []
        );
      } else {
        throw new Error(`지원하지 않는 Canvas 타입: ${type}`);
      }
      
      // 3. 로컬 상태에 추가
      set(state => ({
        items: [...state.items, canvasItem],
        activeItemId: canvasItem.id,
        lastConversationId: conversationId,
        isCanvasOpen: true
      }));
      
      // 4. Canvas 공유 전략 적용 (CanvasShareStrategy)
      if (state.isPersistenceEnabled) {
        try {
          await CanvasShareStrategy.shareCanvas(canvasItem.id, conversationId);
          console.log('✅ Canvas 공유 전략 적용 완료:', canvasItem.id);
        } catch (shareError) {
          console.warn('⚠️ Canvas 공유 전략 적용 실패:', shareError);
        }
      }
      
      // 5. Auto Save 등록
      if (state.autoSaveEnabled) {
        canvasAutoSave.registerCanvas(canvasItem.id, canvasItem);
      }
      
      console.log('✅ 영구 Canvas 생성 완료:', canvasItem.id);
      return canvasItem.id;
      
    } catch (error) {
      console.error('❌ 영구 Canvas 생성 실패:', error);
      throw error;
    }
  },
  
  /**
   * 영구 Canvas 로드
   * 백엔드에서 Canvas 데이터를 불러와 복원
   */
  loadPermanentCanvas: async (canvasId: string): Promise<CanvasItem | null> => {
    try {
      console.log('📂 영구 Canvas 로드 시작:', canvasId);
      
      const canvasItem = await ConversationCanvasManager.getCanvas(canvasId);
      
      if (canvasItem) {
        // 로컬 상태에 추가 (중복 방지)
        set(state => {
          const existingIndex = state.items.findIndex(item => item.id === canvasId);
          if (existingIndex >= 0) {
            // 기존 아이템 업데이트
            const updatedItems = [...state.items];
            updatedItems[existingIndex] = canvasItem;
            return { items: updatedItems };
          } else {
            // 새 아이템 추가
            return { items: [...state.items, canvasItem] };
          }
        });
        
        console.log('✅ 영구 Canvas 로드 완료:', canvasId);
      }
      
      return canvasItem;
      
    } catch (error) {
      console.error('❌ 영구 Canvas 로드 실패:', error);
      return null;
    }
  },
  
  /**
   * 영구 Canvas 삭제
   * 백엔드와 로컬 상태에서 Canvas 제거
   */
  deletePermanentCanvas: async (canvasId: string): Promise<boolean> => {
    try {
      console.log('🗑️ 영구 Canvas 삭제 시작:', canvasId);
      
      // 1. 백엔드에서 삭제
      await ConversationCanvasManager.deleteCanvas(canvasId);
      
      // 2. 로컬 상태에서 제거
      set(state => ({
        items: state.items.filter(item => item.id !== canvasId),
        activeItemId: state.activeItemId === canvasId ? null : state.activeItemId
      }));
      
      // 3. Auto Save 해제
      canvasAutoSave.unregisterCanvas(canvasId);
      
      console.log('✅ 영구 Canvas 삭제 완료:', canvasId);
      return true;
      
    } catch (error) {
      console.error('❌ 영구 Canvas 삭제 실패:', error);
      return false;
    }
  },
  
  /**
   * 영구 보존 활성화
   */
  enablePersistence: () => {
    console.log('🔒 Canvas 영구 보존 활성화');
    set({ isPersistenceEnabled: true });
  },
  
  /**
   * 영구 보존 비활성화
   */
  disablePersistence: () => {
    console.log('🔓 Canvas 영구 보존 비활성화');
    set({ isPersistenceEnabled: false });
  },
  
  /**
   * 대화별 Canvas 저장
   * 로컬 스토리지에 Canvas 데이터 저장
   */
  saveCanvasToStorage: (conversationId: string) => {
    const state = get();
    const conversationItems = state.items.filter(item => 
      item.metadata?.conversationId === conversationId
    );
    
    if (conversationItems.length > 0) {
      const storageKey = `${CANVAS_DEFAULTS.STORAGE_KEY_PREFIX}${conversationId}`;
      try {
        localStorage.setItem(storageKey, JSON.stringify(conversationItems));
        console.log('💾 Canvas 로컬 저장 완료:', { conversationId, itemCount: conversationItems.length });
      } catch (error) {
        console.error('❌ Canvas 로컬 저장 실패:', error);
      }
    }
  },
  
  /**
   * 대화별 Canvas 로드
   * 로컬 스토리지에서 Canvas 데이터 복원
   */
  loadCanvasForConversation: (conversationId: string) => {
    const storageKey = `${CANVAS_DEFAULTS.STORAGE_KEY_PREFIX}${conversationId}`;
    
    try {
      const storedData = localStorage.getItem(storageKey);
      if (storedData) {
        const canvasItems: CanvasItem[] = JSON.parse(storedData);
        
        set(state => {
          // 기존 해당 대화의 아이템들 제거 후 새로 추가
          const otherItems = state.items.filter(item => 
            item.metadata?.conversationId !== conversationId
          );
          
          return {
            items: [...otherItems, ...canvasItems],
            lastConversationId: conversationId
          };
        });
        
        console.log('📂 Canvas 로컬 로드 완료:', { conversationId, itemCount: canvasItems.length });
      }
    } catch (error) {
      console.error('❌ Canvas 로컬 로드 실패:', error);
    }
  },
  
  /**
   * 대화별 Canvas 삭제
   */
  deleteConversationCanvas: (conversationId: string) => {
    const storageKey = `${CANVAS_DEFAULTS.STORAGE_KEY_PREFIX}${conversationId}`;
    
    try {
      // 로컬 스토리지에서 제거
      localStorage.removeItem(storageKey);
      
      // 상태에서 해당 대화의 아이템들 제거
      set(state => ({
        items: state.items.filter(item => 
          item.metadata?.conversationId !== conversationId
        ),
        activeItemId: null,
        lastConversationId: state.lastConversationId === conversationId 
          ? null 
          : state.lastConversationId
      }));
      
      console.log('🗑️ 대화별 Canvas 삭제 완료:', conversationId);
    } catch (error) {
      console.error('❌ 대화별 Canvas 삭제 실패:', error);
    }
  },
  
  /**
   * Canvas 미리보기 생성
   * 대화 목록에서 사용할 Canvas 요약 정보 반환
   */
  getCanvasPreview: (conversationId: string): string | null => {
    const state = get();
    const conversationItems = state.items.filter(item => 
      item.metadata?.conversationId === conversationId
    );
    
    if (conversationItems.length === 0) {
      return null;
    }
    
    // 가장 최근 아이템의 요약 생성
    const latestItem = conversationItems
      .sort((a, b) => new Date(b.updatedAt || 0).getTime() - new Date(a.updatedAt || 0).getTime())[0];
    
    switch (latestItem.type) {
      case 'text':
        const textContent = latestItem.content.text || '';
        return textContent.length > 50 ? textContent.slice(0, 50) + '...' : textContent;
      
      case 'image':
        const imageCount = latestItem.content.images?.length || 0;
        return `이미지 ${imageCount}개 생성`;
      
      case 'mindmap':
        const nodeCount = latestItem.content.nodes?.length || 0;
        return `마인드맵 노드 ${nodeCount}개`;
      
      default:
        return `${latestItem.type} Canvas`;
    }
  }
});

/**
 * Canvas 자동 저장 관련 유틸리티
 */
export const CanvasPersistenceUtils = {
  /**
   * 모든 대화의 Canvas 데이터 Export
   */
  exportAllCanvasData: (): Record<string, CanvasItem[]> => {
    const result: Record<string, CanvasItem[]> = {};
    
    // localStorage에서 모든 Canvas 데이터 수집
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(CANVAS_DEFAULTS.STORAGE_KEY_PREFIX)) {
        const conversationId = key.replace(CANVAS_DEFAULTS.STORAGE_KEY_PREFIX, '');
        try {
          const data = localStorage.getItem(key);
          if (data) {
            result[conversationId] = JSON.parse(data);
          }
        } catch (error) {
          console.error(`Canvas 데이터 Export 실패: ${conversationId}`, error);
        }
      }
    }
    
    return result;
  },
  
  /**
   * Canvas 데이터 Import
   */
  importCanvasData: (data: Record<string, CanvasItem[]>): boolean => {
    try {
      Object.entries(data).forEach(([conversationId, items]) => {
        const storageKey = `${CANVAS_DEFAULTS.STORAGE_KEY_PREFIX}${conversationId}`;
        localStorage.setItem(storageKey, JSON.stringify(items));
      });
      
      console.log('✅ Canvas 데이터 Import 완료:', Object.keys(data).length);
      return true;
    } catch (error) {
      console.error('❌ Canvas 데이터 Import 실패:', error);
      return false;
    }
  },
  
  /**
   * Canvas 스토리지 정리
   * 오래된 데이터 제거 및 최적화
   */
  cleanupStorage: (maxAge: number = 30 * 24 * 60 * 60 * 1000): void => {
    const now = Date.now();
    const keysToRemove: string[] = [];
    
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(CANVAS_DEFAULTS.STORAGE_KEY_PREFIX)) {
        try {
          const data = localStorage.getItem(key);
          if (data) {
            const items: CanvasItem[] = JSON.parse(data);
            const latestUpdate = Math.max(
              ...items.map(item => new Date(item.updatedAt || 0).getTime())
            );
            
            if (now - latestUpdate > maxAge) {
              keysToRemove.push(key);
            }
          }
        } catch (error) {
          // 잘못된 데이터는 제거
          keysToRemove.push(key);
        }
      }
    }
    
    keysToRemove.forEach(key => localStorage.removeItem(key));
    console.log(`🧹 Canvas 스토리지 정리 완료: ${keysToRemove.length}개 항목 제거`);
  }
};