/**
 * Canvas Synchronization v5.0 - 동기화 시스템
 * ImageSessionStore와의 실시간 동기화 및 큐 관리
 */

import type { CanvasState, SyncTask } from './CanvasCore';
import type { CanvasItem, CanvasToolType } from '../../types/canvas';
import { generateUniqueCanvasId, generateCanvasDataHash, CANVAS_DEFAULTS } from './CanvasCore';
import { useImageSessionStore } from '../imageSessionStore';

/**
 * Canvas 동기화 시스템 구현부
 * Zustand Store에 mixin될 메서드들을 제공
 */
export const createCanvasSynchronizationSlice = (
  set: (partial: Partial<CanvasState>) => void,
  get: () => CanvasState
) => ({
  // ======= 동기화 시스템 초기 상태 =======
  syncQueue: [] as SyncTask[],
  isProcessingSyncQueue: false,
  syncInProgress: {} as Record<string, boolean>,
  processedCanvasItems: {} as Record<string, Set<string>>,
  debounceTimers: {} as Record<string, NodeJS.Timeout>,
  
  // ======= 동기화 시스템 메서드 =======
  
  /**
   * 동기화 작업 큐에 추가
   */
  enqueueSyncTask: (task: SyncTask) => {
    set(state => ({
      syncQueue: [...state.syncQueue, task]
    }));
    
    console.log('📝 동기화 작업 큐 추가:', task);
    
    // 자동으로 큐 처리 시작
    const state = get();
    if (!state.isProcessingSyncQueue) {
      state.processSyncQueue();
    }
  },
  
  /**
   * 동기화 큐 처리
   * 순차적으로 동기화 작업 실행
   */
  processSyncQueue: async (): Promise<void> => {
    const state = get();
    
    if (state.isProcessingSyncQueue || state.syncQueue.length === 0) {
      return;
    }
    
    console.log('🚀 동기화 큐 처리 시작:', state.syncQueue.length);
    
    set({ isProcessingSyncQueue: true });
    
    try {
      while (true) {
        const currentState = get();
        if (currentState.syncQueue.length === 0) {
          break;
        }
        
        const task = currentState.syncQueue[0];
        
        try {
          await processIndividualSyncTask(task, set, get);
          
          // 처리 완료된 작업 제거
          set(state => ({
            syncQueue: state.syncQueue.slice(1)
          }));
          
          console.log('✅ 동기화 작업 완료:', task.id);
          
        } catch (error) {
          console.error('❌ 동기화 작업 실패:', task.id, error);
          
          // 실패한 작업도 큐에서 제거 (무한 루프 방지)
          set(state => ({
            syncQueue: state.syncQueue.slice(1)
          }));
        }
        
        // 다음 작업 전 잠시 대기 (과부하 방지)
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
    } finally {
      set({ isProcessingSyncQueue: false });
      console.log('🏁 동기화 큐 처리 완료');
    }
  },
  
  /**
   * 동기화 큐 초기화
   */
  clearSyncQueue: () => {
    set({
      syncQueue: [],
      isProcessingSyncQueue: false
    });
    console.log('🗑️ 동기화 큐 초기화 완료');
  },
  
  /**
   * Canvas와 ImageSession 동기화
   * ImageSessionStore의 최신 데이터를 Canvas로 반영
   */
  syncCanvasWithImageSession: async (conversationId: string): Promise<void> => {
    const state = get();
    const imageSessionStore = useImageSessionStore.getState();
    
    // 중복 동기화 방지
    if (state.syncInProgress[conversationId]) {
      console.log('⚠️ 이미 동기화 진행 중:', conversationId);
      return;
    }
    
    console.log('🔄 Canvas-ImageSession 동기화 시작:', conversationId);
    
    // 동기화 진행 플래그 설정
    set(state => ({
      syncInProgress: { ...state.syncInProgress, [conversationId]: true }
    }));
    
    try {
      const imageSessions = imageSessionStore.getSessionsByConversation(conversationId);
      
      if (!imageSessions || imageSessions.length === 0) {
        console.log('📭 동기화할 ImageSession 없음:', conversationId);
        return;
      }
      
      // 처리된 아이템 추적 초기화
      if (!state.processedCanvasItems[conversationId]) {
        set(state => ({
          processedCanvasItems: {
            ...state.processedCanvasItems,
            [conversationId]: new Set<string>()
          }
        }));
      }
      
      for (const session of imageSessions) {
        try {
          await syncSingleImageSession(session, conversationId, set, get);
        } catch (sessionError) {
          console.error('❌ 개별 ImageSession 동기화 실패:', session.id, sessionError);
        }
      }
      
      console.log('✅ Canvas-ImageSession 동기화 완료:', conversationId);
      
    } finally {
      // 동기화 진행 플래그 해제
      set(state => ({
        syncInProgress: { ...state.syncInProgress, [conversationId]: false }
      }));
    }
  },
  
  /**
   * 이미지 버전 선택
   * ImageSession에서 특정 버전을 선택하고 Canvas에 반영
   */
  selectImageVersion: (conversationId: string, sessionId: string, versionIndex: number) => {
    console.log('🎯 이미지 버전 선택:', { conversationId, sessionId, versionIndex });
    
    // ImageSession Store에서 버전 선택 실행
    const imageSessionStore = useImageSessionStore.getState();
    imageSessionStore.selectVersion(sessionId, versionIndex);
    
    // Canvas 즉시 업데이트
    const session = imageSessionStore.sessions.find(s => s.id === sessionId);
    if (session && session.selectedVersion !== undefined) {
      const selectedImage = session.images[session.selectedVersion];
      
      if (selectedImage) {
        // Canvas에서 해당 이미지 아이템 찾아서 업데이트
        set(state => {
          const updatedItems = state.items.map(item => {
            if (
              item.type === 'image' && 
              item.metadata?.conversationId === conversationId &&
              item.metadata?.imageSessionId === sessionId
            ) {
              return {
                ...item,
                content: {
                  ...item.content,
                  images: [selectedImage.url],
                  selectedVersion: versionIndex
                },
                updatedAt: new Date().toISOString()
              };
            }
            return item;
          });
          
          return { items: updatedItems };
        });
        
        console.log('✅ Canvas 이미지 버전 업데이트 완료');
      }
    }
  }
});

/**
 * 개별 동기화 작업 처리
 */
async function processIndividualSyncTask(
  task: SyncTask,
  set: (partial: Partial<CanvasState>) => void,
  get: () => CanvasState
): Promise<void> {
  const { conversationId, type, data } = task;
  
  switch (type) {
    case 'canvas_to_session':
      await syncCanvasToImageSession(conversationId, data, set, get);
      break;
      
    case 'session_to_canvas':
      await syncImageSessionToCanvas(conversationId, data, set, get);
      break;
      
    case 'version_select':
      handleVersionSelection(conversationId, data, set, get);
      break;
      
    default:
      console.warn('⚠️ 알 수 없는 동기화 작업 타입:', type);
  }
}

/**
 * Canvas → ImageSession 동기화
 */
async function syncCanvasToImageSession(
  conversationId: string,
  data: any,
  set: (partial: Partial<CanvasState>) => void,
  get: () => CanvasState
): Promise<void> {
  console.log('📤 Canvas → ImageSession 동기화:', conversationId);
  
  const imageSessionStore = useImageSessionStore.getState();
  const state = get();
  
  // Canvas의 이미지 아이템들을 ImageSession으로 전송
  const imageItems = state.items.filter(item => 
    item.type === 'image' && item.metadata?.conversationId === conversationId
  );
  
  for (const item of imageItems) {
    try {
      if (item.content.images && item.content.images.length > 0) {
        const sessionId = item.metadata?.imageSessionId || `canvas_${item.id}`;
        
        // ImageSession에 이미지 등록
        imageSessionStore.addImageSession({
          id: sessionId,
          conversationId,
          prompt: item.content.prompt || '',
          images: item.content.images.map((url, index) => ({
            id: `${sessionId}_${index}`,
            url,
            prompt: item.content.prompt || '',
            timestamp: Date.now()
          })),
          selectedVersion: item.content.selectedVersion || 0,
          createdAt: new Date(item.createdAt || Date.now())
        });
      }
    } catch (error) {
      console.error('❌ 개별 Canvas → ImageSession 동기화 실패:', item.id, error);
    }
  }
}

/**
 * ImageSession → Canvas 동기화
 */
async function syncImageSessionToCanvas(
  conversationId: string,
  data: any,
  set: (partial: Partial<CanvasState>) => void,
  get: () => CanvasState
): Promise<void> {
  console.log('📥 ImageSession → Canvas 동기화:', conversationId);
  
  const imageSessionStore = useImageSessionStore.getState();
  const sessions = imageSessionStore.getSessionsByConversation(conversationId);
  
  for (const session of sessions) {
    await syncSingleImageSession(session, conversationId, set, get);
  }
}

/**
 * 단일 ImageSession Canvas 동기화
 */
async function syncSingleImageSession(
  session: any,
  conversationId: string,
  set: (partial: Partial<CanvasState>) => void,
  get: () => CanvasState
): Promise<void> {
  const state = get();
  
  // 중복 처리 방지 체크
  const processedItems = state.processedCanvasItems[conversationId] || new Set();
  const sessionHash = generateCanvasDataHash({
    type: 'image_session',
    content: session.id,
    images: session.images?.map((img: any) => img.url).join(',')
  });
  
  if (processedItems.has(sessionHash)) {
    return; // 이미 처리된 세션
  }
  
  // 해당 ImageSession에 대응하는 Canvas 아이템 찾기
  let existingItem = state.items.find(item => 
    item.metadata?.imageSessionId === session.id
  );
  
  if (existingItem) {
    // 기존 아이템 업데이트
    set(state => ({
      items: state.items.map(item => 
        item.id === existingItem!.id
          ? {
              ...item,
              content: {
                ...item.content,
                images: session.images?.map((img: any) => img.url) || [],
                prompt: session.prompt || item.content.prompt,
                selectedVersion: session.selectedVersion || 0
              },
              updatedAt: new Date().toISOString()
            }
          : item
      )
    }));
  } else {
    // 새 Canvas 아이템 생성
    const newCanvasItem: CanvasItem = {
      id: generateUniqueCanvasId(state.items),
      type: 'image',
      content: {
        prompt: session.prompt || '',
        images: session.images?.map((img: any) => img.url) || [],
        style: 'realistic',
        aspectRatio: '1:1',
        size: '1K_1:1',
        selectedVersion: session.selectedVersion || 0
      },
      position: { x: 100, y: 100 },
      size: { width: 400, height: 400 },
      metadata: {
        conversationId,
        imageSessionId: session.id,
        createdFromImageSession: true
      },
      createdAt: session.createdAt?.toISOString() || new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    set(state => ({
      items: [...state.items, newCanvasItem]
    }));
  }
  
  // 처리 완료 기록
  set(state => ({
    processedCanvasItems: {
      ...state.processedCanvasItems,
      [conversationId]: new Set([...processedItems, sessionHash])
    }
  }));
}

/**
 * 버전 선택 처리
 */
function handleVersionSelection(
  conversationId: string,
  data: any,
  set: (partial: Partial<CanvasState>) => void,
  get: () => CanvasState
): void {
  const { sessionId, versionIndex } = data;
  
  console.log('🎯 버전 선택 처리:', { conversationId, sessionId, versionIndex });
  
  // Canvas 아이템 업데이트
  set(state => ({
    items: state.items.map(item => 
      item.metadata?.imageSessionId === sessionId
        ? {
            ...item,
            content: {
              ...item.content,
              selectedVersion: versionIndex
            },
            updatedAt: new Date().toISOString()
          }
        : item
    )
  }));
}

/**
 * 디바운스된 동기화 유틸리티
 */
export const DebouncedSyncUtils = {
  /**
   * 디바운스된 Canvas 동기화
   */
  debouncedCanvasSync: (
    conversationId: string,
    syncFn: () => void,
    set: (partial: Partial<CanvasState>) => void,
    get: () => CanvasState
  ) => {
    const state = get();
    const existingTimer = state.debounceTimers[conversationId];
    
    if (existingTimer) {
      clearTimeout(existingTimer);
    }
    
    const newTimer = setTimeout(() => {
      syncFn();
      
      // 타이머 정리
      set(state => {
        const { [conversationId]: removed, ...remainingTimers } = state.debounceTimers;
        return { debounceTimers: remainingTimers };
      });
    }, CANVAS_DEFAULTS.SYNC_DEBOUNCE_DELAY);
    
    set(state => ({
      debounceTimers: {
        ...state.debounceTimers,
        [conversationId]: newTimer
      }
    }));
  }
};