/**
 * Canvas 상태 관리 Store v4.0 - 완전한 영구 보존 및 공유 전략 통합
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';
import type { CanvasItem, CanvasToolType, TextNote, ImageGeneration, MindMapNode } from '../types/canvas';
import { useImageSessionStore } from './imageSessionStore';
import { ConversationCanvasManager } from '../services/conversationCanvasManager';
import { CanvasShareStrategy } from '../services/CanvasShareStrategy';
import { CanvasContinuity } from '../services/CanvasContinuity';
import { CanvasAutoSave } from '../services/CanvasAutoSave';

// UUID 충돌 방지 헬퍼 함수 (v4.5 추가)
function generateUniqueCanvasId(existingItems: CanvasItem[]): string {
  const existingIds = new Set(existingItems.map(item => item.id));
  let attempts = 0;
  let newId: string;
  
  do {
    newId = uuidv4();
    attempts++;
    if (attempts > 10) {
      console.warn('⚠️ Canvas UUID 충돌 방지 - 10회 시도 후 강제 진행:', newId);
      break;
    }
  } while (existingIds.has(newId));
  
  return newId;
}

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

// 🔄 동기화 작업 타입 정의
type SyncTask = {
  id: string;
  conversationId: string;
  type: 'canvas_to_session' | 'session_to_canvas' | 'version_select';
  data: any;
  timestamp: number;
};

interface CanvasState {
  items: CanvasItem[];
  activeItemId: string | null;
  isCanvasOpen: boolean;
  lastConversationId: string | null;
  
  // 🚀 v4.0 영구 보존 및 공유 전략 시스템
  isPersistenceEnabled: boolean;
  autoSaveEnabled: boolean;
  
  // 🚀 순차 동기화 시스템 (기존 유지)
  syncQueue: SyncTask[];
  isProcessingSyncQueue: boolean;
  
  // 🚫 중복 실행 방지 시스템
  syncInProgress: Record<string, boolean>; // conversationId별 동기화 진행 상태
  processedCanvasItems: Record<string, Set<string>>; // conversationId별 처리된 Canvas 아이템 ID들
  
  // ⏱️ API 디바운싱 시스템 (v4.5 추가)
  debounceTimers: Record<string, NodeJS.Timeout>; // conversationId별 디바운싱 타이머
  
  // 🎯 v4.0 핵심 통합 메서드 - 영구 보존 및 공유 전략 적용
  getOrCreateCanvasV4: (conversationId: string, type: CanvasToolType, canvasData?: any, requestId?: string) => Promise<string>;
  getOrCreateCanvas: (conversationId: string, type: CanvasToolType, canvasData?: any) => Promise<string>; // 하위 호환
  activateConversationCanvas: (conversationId: string, type: CanvasToolType) => string; // 활성화 로직 단일화  
  updateConversationCanvas: (conversationId: string, type: CanvasToolType, updates: any) => string; // 업데이트 로직 통일화
  
  // 기존 메서드들 (하위 호환성 유지)
  addItem: (type: CanvasToolType, content: any) => string;
  updateItem: (id: string, updates: Partial<CanvasItem>) => void;
  deleteItem: (id: string) => void;
  clearCanvas: () => void;
  setActiveItem: (id: string | null) => void;
  
  // Canvas 상태 관리
  openWithArtifact: (artifactId: string) => void;
  autoActivateCanvas: (canvasData: any, conversationId?: string) => string; // → getOrCreateCanvasV4로 리팩토링
  closeCanvas: () => void;
  
  // 대화별 Canvas 관리
  loadCanvasForConversation: (conversationId: string) => void;
  clearCanvasForNewConversation: () => void;
  
  // 🎯 v4.0 영구 보존 시스템
  saveCanvasToPersistence: (canvasId: string, canvasData: any) => Promise<void>;
  loadCanvasFromPersistence: (conversationId: string, canvasType?: CanvasToolType) => Promise<CanvasItem[]>;
  restoreCanvasState: (conversationId: string) => Promise<void>;
  
  // 🔗 v4.0 연속성 시스템
  createContinuityCanvas: (baseCanvasId: string, userRequest: string, targetType: CanvasToolType) => Promise<string>;
  findReferencableCanvas: (conversationId: string, targetType: CanvasToolType) => CanvasItem[];
  
  // 🔄 v4.0 자동 저장 시스템
  enableAutoSave: (canvasId: string, canvasType: CanvasToolType) => void;
  disableAutoSave: (canvasId: string) => void;
  
  // 🎨 Request-based Canvas Evolution System (Phase 4.2)
  evolveCanvasImage: (conversationId: string, canvasId: string, referenceImageId: string, newPrompt: string, evolutionParams?: {
    evolutionType?: string;
    editMode?: string;
    style?: string;
    size?: string;
  }) => Promise<{ success: boolean; data?: any; error?: string }>;
  
  // 🔄 Backend Workflow Integration
  dispatchImageRequest: (request: {
    conversationId: string;
    userId: string;
    prompt: string;
    source: 'chat' | 'canvas' | 'api';
    canvasId?: string;
    referenceImageId?: string;
    evolutionType?: string;
    editMode?: string;
    style?: string;
    size?: string;
  }) => Promise<{ success: boolean; data?: any; error?: string; workflowMode?: string }>;
  
  // 🎯 Canvas-Backend Synchronization
  syncCanvasWithBackend: (canvasId: string) => Promise<void>;
  loadCanvasHistory: (conversationId: string, canvasId: string) => Promise<any[]>;
  notifyCanvasChange: (canvasId: string, canvasData: any) => void;
  
  // Helper methods
  getItemById: (id: string) => CanvasItem | undefined;
  hasActiveContent: () => boolean;
  shouldActivateForConversation: (messages: any[]) => boolean;
  updateCanvasWithCompletedImage: (canvasData: any) => string | null;
  
  // 진화형 이미지 시스템 통합
  activateSessionCanvas: (conversationId: string) => string; // → activateConversationCanvas로 리팩토링 예정
  syncWithImageSession: (conversationId: string) => void;
  
  // 🚀 순차 동기화 시스템 메서드 - v3.0 강화
  addSyncTask: (task: Omit<SyncTask, 'id' | 'timestamp'>) => void;
  processSyncQueue: () => Promise<void>;
  clearSyncQueue: (conversationId?: string) => void;
  _executeSyncImageToSessionStore: (conversationId: string, canvasData: any) => Promise<any>;
  
  // Canvas 버전 선택 시스템 - v3.0 즉시 처리
  selectVersionInCanvas: (conversationId: string, versionId: string) => Promise<void>;
  
  // ImageSession 연동 보장 - v3.0 완전 통합
  ensureImageSession: (conversationId: string, canvasData: any) => Promise<void>;
  
  // Canvas → ImageSession 역방향 동기화 (v4.1 새 기능)
  syncCanvasToImageSession: (conversationId: string, canvasItems?: CanvasItem[]) => Promise<{ action: string; versionsAdded: number; }>;
  
  // 🚫 중복 실행 방지 메서드들
  isSyncInProgress: (conversationId: string) => boolean;
  setSyncInProgress: (conversationId: string, inProgress: boolean) => void;
  isCanvasProcessed: (conversationId: string, canvasId: string) => boolean;
  markCanvasAsProcessed: (conversationId: string, canvasId: string) => void;
  clearProcessedCanvasItems: (conversationId: string) => void;
  
  // ⏱️ API 디바운싱 메서드들 (v4.5)
  debouncedSyncCanvasToImageSession: (conversationId: string, canvasItems?: CanvasItem[], delayMs?: number) => Promise<{ action: string; versionsAdded: number; }>;
  clearDebounceTimer: (conversationId: string) => void;
  
  exportCanvas: () => string;
  importCanvas: (data: string) => void;
}

// Canvas Auto Save 콜백 함수 정의
const canvasAutoSaveCallback = async (canvasId: string, canvasData: any) => {
  console.log('💾 Canvas 자동 저장 콜백 실행:', canvasId);
  try {
    const store = useCanvasStore.getState();
    await store.saveCanvasToPersistence(canvasId, canvasData);
  } catch (error) {
    console.error('❌ Canvas 자동 저장 콜백 실패:', error);
  }
};

// Canvas Auto Save 시스템 초기화
if (typeof window !== 'undefined') {
  CanvasAutoSave.initialize(canvasAutoSaveCallback);
}

export const useCanvasStore = create<CanvasState>()(persist((set, get) => ({
  items: [],
  activeItemId: null,
  isCanvasOpen: false,
  lastConversationId: null,
  
  // 🚀 v4.0 영구 보존 시스템 초기 상태
  isPersistenceEnabled: true,
  autoSaveEnabled: true,
  
  // 🚀 순차 동기화 시스템 초기 상태 (기존 유지)
  syncQueue: [],
  isProcessingSyncQueue: false,
  
  // 🚫 중복 실행 방지 시스템 초기 상태
  syncInProgress: {},
  processedCanvasItems: {},
  
  // ⏱️ API 디바운싱 시스템 초기 상태 (v4.5)
  debounceTimers: {},
  
  // 🎯 v4.0 핵심 통합 메서드 - 영구 보존 및 공유 전략 적용
  getOrCreateCanvasV4: async (conversationId, type, canvasData, requestId) => {
    console.log('🎨 Canvas Store v4.0 - 영구 보존 및 공유 전략 적용:', { 
      conversationId, 
      type, 
      hasCanvasData: !!canvasData,
      requestId,
      shareStrategy: CanvasShareStrategy.getCanvasConfig(type).shareType
    });

    try {
      // 1. Canvas ID 생성 (공유 전략 적용)
      const canvasId = CanvasShareStrategy.getCanvasId(conversationId, type, requestId);
      const shareConfig = CanvasShareStrategy.getCanvasConfig(type);
      
      console.log('📋 Canvas ID 생성:', { canvasId, shareConfig });

      // 2. 기존 Canvas 검색 (ID 기반 + 이미지 중복 방지)
      let existingCanvas = get().items.find(item => item.id === canvasId);
      
      // 🚫 이미지 Canvas 중복 생성 방지: 동일한 이미지URL 검증
      if (!existingCanvas && type === 'image' && canvasData?.imageUrl) {
        const duplicateImageCanvas = get().items.find(item => 
          item.type === 'image' && 
          (item.content as any)?.conversationId === conversationId &&
          (item.content as any)?.imageUrl === canvasData.imageUrl
        );
        
        if (duplicateImageCanvas) {
          console.log('🚫 Canvas Store - 동일한 이미지 URL의 Canvas 이미 존재, 중복 생성 방지:', {
            existingCanvasId: duplicateImageCanvas.id,
            imageUrl: canvasData.imageUrl.substring(0, 50) + '...',
            conversationId
          });
          
          // 기존 Canvas 활성화하고 ID 반환
          get().setActiveCanvas(duplicateImageCanvas.id);
          return duplicateImageCanvas.id;
        }
      }
      
      if (existingCanvas) {
        console.log('✅ 기존 Canvas 발견, 업데이트:', canvasId);
        
        // Canvas 업데이트
        if (canvasData) {
          get().updateItem(existingCanvas.id, {
            content: {
              ...existingCanvas.content,
              ...canvasData,
              conversationId
            },
            updatedAt: new Date().toISOString()
          });
          
          // 자동 저장 알림
          if (shareConfig.autoSave) {
            get().notifyCanvasChange(canvasId, canvasData);
          }
        }
        
        // Canvas 활성화
        set({
          activeItemId: existingCanvas.id,
          isCanvasOpen: true,
          lastConversationId: conversationId
        });
        
        return existingCanvas.id;
      }
      
      // 3. 새 Canvas 생성
      console.log('✨ 새 Canvas 생성 (v4.0):', canvasId);
      
      const canvasMetadata = CanvasShareStrategy.createCanvasMetadata(type, conversationId, {
        requestId,
        createdByVersion: '4.0'
      });
      
      const newCanvas = {
        id: canvasId,
        type,
        content: {
          ...ConversationCanvasManager.createDefaultContent(type, conversationId),
          ...canvasData,
          conversationId
        },
        position: { x: 50, y: 50 },
        size: type === 'text' ? { width: 300, height: 200 } : { width: 400, height: 300 },
        metadata: canvasMetadata,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      
      // Canvas Store에 추가
      set(state => ({
        items: [...state.items, newCanvas],
        activeItemId: newCanvas.id,
        isCanvasOpen: true,
        lastConversationId: conversationId
      }));
      
      // 자동 저장 시작
      if (shareConfig.autoSave) {
        get().enableAutoSave(canvasId, type);
      }
      
      // 영구 저장
      if (shareConfig.persistent) {
        await get().saveCanvasToPersistence(canvasId, newCanvas);
      }
      
      console.log('✅ 새 Canvas 생성 완료 (v4.0):', canvasId);
      return canvasId;
      
    } catch (error) {
      console.error('❌ Canvas 생성/업데이트 실패:', error);
      throw error;
    }
  },

  // 🔄 하위 호환성을 위한 기존 메서드 (getOrCreateCanvasV4로 리다이렉트)
  getOrCreateCanvas: async (conversationId, type, canvasData) => {
    console.log('🔄 Canvas Store - getOrCreateCanvas (하위 호환) → v4.0으로 리다이렉트');
    return get().getOrCreateCanvasV4(conversationId, type, canvasData);
    console.log('📊 Canvas Store - 현재 Items 상태:', { 
      totalItems: get().items.length,
      items: get().items.map(item => ({ id: item.id, type: item.type, conversationId: (item.content as any)?.conversationId }))
    });
    
    const currentItems = get().items;
    const imageSessionStore = useImageSessionStore.getState();
    const session = imageSessionStore.getSession(conversationId);
    
    // 1. 기존 Canvas 검색 (ConversationCanvasManager 사용)
    const existingCanvas = ConversationCanvasManager.findCanvas(currentItems, conversationId, type);
    
    if (existingCanvas) {
      console.log('✅ Canvas Store - 기존 Canvas 발견, 완전 통합 업데이트 시작:', existingCanvas.id);
      
      if (type === 'image') {
        console.log('🔗 Canvas Store - 이미지 Canvas 완전 통합 모드');
        
        // 🚀 Step 1: 새로운 이미지 데이터가 있으면 먼저 ImageSession에 추가
        if (canvasData?.image_data) {
          console.log('📋 Canvas Store - 새 이미지 데이터 ImageSession 동기화 진행');
          await get().ensureImageSession(conversationId, canvasData);
        }
        
        // 🚀 Step 2: 최신 ImageSession 데이터로 Canvas 완전 통합
        const updatedSession = imageSessionStore.getSession(conversationId);
        
        if (updatedSession && updatedSession.versions.length > 0) {
          console.log('🔗 Canvas Store - 최신 ImageSession 전체 버전으로 Canvas 통합:', {
            versionsCount: updatedSession.versions.length,
            selectedVersionId: updatedSession.selectedVersionId
          });
          
          // 모든 버전을 포함한 완전 통합 컨텐츠 생성
          const { content: integratedContent } = ConversationCanvasManager.integrateImageSession(
            conversationId, 
            updatedSession, 
            updatedSession.selectedVersionId
          );
          
          // 기존 Canvas 컨텐츠와 병합하되 버전 정보는 완전 교체
          get().updateItem(existingCanvas.id, {
            content: {
              ...existingCanvas.content, // 기존 속성 유지
              ...integratedContent,       // 새로운 통합 데이터로 덮어쓰기
              conversationId              // conversationId 보장
            }
          });
          
          console.log('✅ Canvas Store - Canvas 완전 통합 업데이트 완료:', {
            versionsCount: integratedContent.versions?.length || 0,
            selectedVersionId: integratedContent.selectedVersionId,
            currentImageUrl: integratedContent.imageUrl
          });
        }
      } else if (canvasData) {
        // 다른 타입: 기존 로직 유지
        const { content } = ConversationCanvasManager.convertCanvasDataToContent(canvasData, conversationId);
        
        get().updateItem(existingCanvas.id, {
          content: {
            ...existingCanvas.content,
            ...content,
            conversationId
          }
        });
        
        console.log('🔄 Canvas Store - 기존 Canvas 업데이트 완료 (비이미지)');
      }
      
      // Canvas 활성화
      set({
        activeItemId: existingCanvas.id,
        isCanvasOpen: true,
        lastConversationId: conversationId
      });
      
      // 🔗 실시간 Canvas ↔ ImageSession 양방향 동기화 완료
      if (type === 'image') {
        console.log('🔄 Canvas Store - Canvas-ImageSession 양방향 동기화 완료');
      }
      
      return existingCanvas.id;
    }
    
    // 2. 새로운 Canvas 생성 (완전 통합 우선)
    console.log('✨ Canvas Store - 새 Canvas 생성 (완전 통합 모드)');
    
    let customContent = null;
    
    if (type === 'image') {
      // 🚀 이미지 타입: 완전 통합 전략
      
      // Step 1: 새로운 이미지 데이터가 있으면 먼저 ImageSession에 추가
      if (canvasData?.image_data) {
        console.log('📋 Canvas Store - 새 Canvas용 이미지 데이터 ImageSession 동기화');
        await get().ensureImageSession(conversationId, canvasData);
      }
      
      // Step 2: 최신 ImageSession 데이터 확인
      const updatedSession = imageSessionStore.getSession(conversationId);
      
      if (updatedSession && updatedSession.versions.length > 0) {
        console.log('🔗 Canvas Store - 최신 ImageSession 전체 버전으로 새 Canvas 생성:', {
          versionsCount: updatedSession.versions.length,
          selectedVersionId: updatedSession.selectedVersionId
        });
        
        const { content: integratedContent } = ConversationCanvasManager.integrateImageSession(
          conversationId, 
          updatedSession, 
          updatedSession.selectedVersionId
        );
        customContent = integratedContent;
      } else if (canvasData) {
        console.log('📄 Canvas Store - canvasData로 새 Canvas 생성 (폴백)');
        const converted = ConversationCanvasManager.convertCanvasDataToContent(canvasData, conversationId);
        customContent = converted.content;
      }
    } else if (canvasData) {
      // 다른 타입: 기존 로직 사용
      const converted = ConversationCanvasManager.convertCanvasDataToContent(canvasData, conversationId);
      customContent = converted.content;
    }
    
    const newCanvas = ConversationCanvasManager.createCanvasItem(conversationId, type, customContent);
    
    // Canvas Store에 추가
    set((state) => ({
      items: [...state.items, newCanvas],
      activeItemId: newCanvas.id,
      isCanvasOpen: true,
      lastConversationId: conversationId
    }));
    
    // 🔗 새로운 Canvas도 ImageSession과 완전 동기화 완료
    if (type === 'image') {
      console.log('🔄 Canvas Store - 새 Canvas ImageSession 동기화 완료');
    }
    
    console.log('✅ Canvas Store - 새 Canvas 생성 완료:', newCanvas.id);
    return newCanvas.id;
  },
  
  activateConversationCanvas: (conversationId, type) => {
    console.log('🎯 Canvas Store - activateConversationCanvas:', { conversationId, type });
    
    const currentItems = get().items;
    const existingCanvas = ConversationCanvasManager.findCanvas(currentItems, conversationId, type);
    
    if (existingCanvas) {
      console.log('✅ Canvas Store - Canvas 활성화:', existingCanvas.id);
      
      set({
        activeItemId: existingCanvas.id,
        isCanvasOpen: true,
        lastConversationId: conversationId
      });
      
      return existingCanvas.id;
    }
    
    console.warn('⚠️ Canvas Store - 활성화할 Canvas가 없음, 기본 Canvas 생성');
    return get().getOrCreateCanvas(conversationId, type);
  },
  
  updateConversationCanvas: (conversationId, type, updates) => {
    console.log('🔄 Canvas Store - updateConversationCanvas:', { conversationId, type, updates });
    
    const currentItems = get().items;
    const existingCanvas = ConversationCanvasManager.findCanvas(currentItems, conversationId, type);
    
    if (existingCanvas) {
      get().updateItem(existingCanvas.id, {
        content: {
          ...existingCanvas.content,
          ...updates,
          conversationId // conversationId는 항상 보장
        }
      });
      
      // ImageSession 자동 동기화 (이미지 타입인 경우)
      if (type === 'image' && updates.imageUrl) {
        console.log('🔗 Canvas Store - ImageSession 동기화 (업데이트)');
        const canvasData = {
          image_data: {
            prompt: updates.prompt || '',
            negativePrompt: updates.negativePrompt || '',
            style: updates.style || 'realistic',
            size: updates.size || '1K_1:1',
            images: [updates.imageUrl]
          }
        };
        get().ensureImageSession(conversationId, canvasData).catch(error => {
          console.error('❌ ImageSession 연동 실패:', error);
        });
      }
      
      console.log('✅ Canvas Store - Canvas 업데이트 완료:', existingCanvas.id);
      return existingCanvas.id;
    }
    
    console.warn('⚠️ Canvas Store - 업데이트할 Canvas가 없음');
    return '';
  },
  
  // ImageSession 연동 보장 v3.0 (완전 통합 최적화)
  ensureImageSession: async (conversationId, canvasData) => {
    console.log('🔗 Canvas Store - ensureImageSession v3.0 (완전 통합):', { conversationId, hasImageData: !!canvasData?.image_data });
    
    const imageSessionStore = useImageSessionStore.getState();
    
    // 1. DB + 메모리에서 최신 세션 확인 (하이브리드 로딩)
    let session = await imageSessionStore.loadSessionFromDB(conversationId);
    
    if (!session) {
      console.log('🔗 Canvas Store - 새 ImageSession 생성 (완전 통합)');
      const theme = imageSessionStore.extractTheme(canvasData.image_data?.prompt || 'AI Image');
      session = await imageSessionStore.createSessionHybrid(conversationId, theme, canvasData.image_data?.prompt || '');
    } else {
      console.log('✅ Canvas Store - 기존 ImageSession 발견:', { 
        conversationId, 
        versionsCount: session.versions.length,
        theme: session.theme,
        selectedVersionId: session.selectedVersionId
      });
    }
    
    // 2. 이미지 데이터가 있으면 스마트 버전 추가 (강화된 중복 방지)
    if (canvasData.image_data) {
      const { image_data } = canvasData;
      
      // 🔍 다중 경로 이미지 URL 추출
      let imageUrl = null;
      if (image_data.image_urls && image_data.image_urls.length > 0) {
        imageUrl = image_data.image_urls[0];
      } else if (image_data.images && image_data.images.length > 0) {
        const firstImage = image_data.images[0];
        imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
      } else if (image_data.generation_result?.images?.[0]) {
        const firstImage = image_data.generation_result.images[0];
        imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
      }
      
      console.log('🔍 Canvas Store - 이미지 URL 추출 결과:', {
        imageUrl: imageUrl ? imageUrl.slice(0, 60) + '...' : 'null',
        prompt: image_data.prompt?.slice(0, 30) + '...',
        style: image_data.style,
        size: image_data.size
      });
      
      if (imageUrl && imageUrl.length > 10) { // 유효한 URL인지 확인
        // 🔍 최신 세션에서 강화된 중복 검사
        const currentSession = imageSessionStore.getSession(conversationId);
        
        if (currentSession) {
          // 정교한 중복 판정: URL 완전 일치 + 프롬프트 유사도 검사
          const duplicateVersion = currentSession.versions.find(version => {
            const urlMatch = version.imageUrl === imageUrl;
            const promptSimilar = version.prompt.trim().toLowerCase() === (image_data.prompt || '').trim().toLowerCase();
            const styleSame = version.style === (image_data.style || 'realistic');
            
            console.log('🔍 Canvas Store - 중복 검사:', {
              versionId: version.id.substring(0, 8),
              urlMatch,
              promptSimilar,
              styleSame,
              isDuplicate: urlMatch && (promptSimilar || styleSame)
            });
            
            return urlMatch && (promptSimilar || styleSame);
          });
          
          if (!duplicateVersion) {
            console.log('🖼️ Canvas Store - 새 버전 ImageSession 추가 (완전 통합)');
            
            const newVersionId = await imageSessionStore.addVersionHybrid(conversationId, {
              prompt: image_data.prompt || '',
              negativePrompt: image_data.negativePrompt || '',
              style: image_data.style || 'realistic',
              size: image_data.size || '1K_1:1',
              imageUrl: imageUrl,
              status: 'completed',
              isSelected: true // 새로 추가되는 버전을 기본 선택
            });
            
            console.log('✅ Canvas Store - 새 버전 추가 완료:', { 
              newVersionId: newVersionId.substring(0, 8),
              totalVersions: (imageSessionStore.getSession(conversationId)?.versions.length || 0)
            });
            
          } else {
            console.log('🔄 Canvas Store - 중복 버전 발견, 기존 버전 선택으로 변경:', {
              existingVersionId: duplicateVersion.id.substring(0, 8),
              versionNumber: duplicateVersion.versionNumber
            });
            
            // 중복인 경우 기존 버전을 선택 상태로 변경
            await imageSessionStore.selectVersionHybrid(conversationId, duplicateVersion.id);
          }
        }
      } else {
        console.log('⚠️ Canvas Store - 유효하지 않은 이미지 URL, 버전 추가 스킵');
      }
    } else {
      console.log('⚠️ Canvas Store - 이미지 데이터 없음, 버전 추가 스킵');
    }
  },
  // 🔥 첫 번째 중복된 syncCanvasWithImageSession 제거 - 539라인의 메서드 사용
  
  addItem: (type, content) => {
    console.log('⚠️ Canvas Store - addItem 호출됨 (deprecated, getOrCreateCanvas 사용 권장)');
    
    // 🛡️ UUID 충돌 방지 - 기존 Canvas 아이템 ID와 중복되지 않도록 보장 (v4.5)
    const existingItems = get().items;
    const safeId = generateUniqueCanvasId(existingItems);
    
    const newItem: CanvasItem = {
      id: safeId,
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
      isCanvasOpen: true
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
  
  autoActivateCanvas: (canvasData, conversationId) => {
    console.log('⚠️ Canvas Store - autoActivateCanvas 호출됨 (deprecated)');
    console.log('🔄 Canvas Store - getOrCreateCanvasV4로 리다이렉트 (v4.0)');
    
    if (!conversationId) {
      console.warn('⚠️ Canvas Store - conversationId가 없어 Canvas 생성 실패');
      return '';
    }
    
    // ConversationCanvasManager를 사용하여 타입 추론
    const inferredType = ConversationCanvasManager.inferCanvasType(canvasData);
    
    // getOrCreateCanvasV4로 리다이렉트
    const canvasIdPromise = get().getOrCreateCanvasV4(conversationId, inferredType, canvasData);
    
    // async 결과를 처리하기 위해 Promise 사용
    canvasIdPromise.then(canvasId => {
      console.log('✅ autoActivateCanvas v4.0 리다이렉트 완료:', canvasId);
    }).catch(error => {
      console.error('❌ autoActivateCanvas v4.0 리다이렉트 실패:', error);
    });
    
    // 동기 호환성을 위해 임시 ID 반환 (실제로는 Promise에서 처리됨)
    return CanvasShareStrategy.getCanvasId(conversationId, inferredType);
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
  
  shouldActivateForConversation: (messages) => {
    // 🚫 대화 이력 클릭 시 Canvas 자동 활성화 방지
    // Canvas는 인라인 링크 클릭을 통해서만 활성화되도록 함
    console.log('🚫 Canvas 자동 활성화 방지: 인라인 링크 클릭으로만 활성화');
    return false;
  },
  
  updateCanvasWithCompletedImage: (canvasData) => {
    // 이미지 생성이 완료된 Canvas 데이터로 기존 아이템 업데이트
    const { type, image_data } = canvasData;
    
    if (type !== 'image' || !image_data) {
      console.warn('🎨 Canvas 이미지 업데이트 실패: 올바르지 않은 데이터 타입');
      return null;
    }
    
    // 현재 활성화된 Canvas 아이템 찾기 (가장 최근에 생성된 이미지 아이템)
    const state = get();
    const imageItems = state.items.filter(item => item.type === 'image');
    
    if (imageItems.length === 0) {
      console.warn('🎨 Canvas 이미지 업데이트 실패: 업데이트할 이미지 아이템이 없음');
      return null;
    }
    
    // 가장 최근 이미지 아이템 (generating 상태인 것 우선)
    const targetItem = imageItems.find(item => item.content.status === 'generating') 
                      || imageItems[imageItems.length - 1];
    
    if (!targetItem) {
      console.warn('🎨 Canvas 이미지 업데이트 실패: 대상 아이템을 찾을 수 없음');
      return null;
    }
    
    // 이미지 URL 추출 (autoActivateCanvas와 동일한 로직)
    let imageUrl = null;
    if (image_data.image_urls && image_data.image_urls.length > 0) {
      imageUrl = image_data.image_urls[0];
    } else if (image_data.images && image_data.images.length > 0) {
      const firstImage = image_data.images[0];
      imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
    } else if (image_data.generation_result?.images?.[0]) {
      const firstImage = image_data.generation_result.images[0];
      imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
    }
    
    console.log('🎨 Canvas 이미지 업데이트:', {
      targetItemId: targetItem.id,
      imageUrl,
      oldStatus: targetItem.content.status,
      newStatus: 'completed'
    });
    
    // 아이템 업데이트
    const updateFn = get().updateItem;
    updateFn(targetItem.id, {
      content: {
        ...targetItem.content,
        status: 'completed',
        imageUrl: imageUrl,
        generation_result: image_data.generation_result
      }
    });
    
    return targetItem.id;
  },
  
  // Canvas를 ImageSession과 동기화 (단방향: ImageSession → Canvas)
  syncCanvasWithImageSession: (conversationId) => {
    console.log('🔄 Canvas Store - Canvas ↔ ImageSession 동기화:', conversationId);
    
    const currentItems = get().items;
    const imageSessionStore = useImageSessionStore.getState();
    const session = imageSessionStore.getSession(conversationId);
    
    console.log('🔍 syncCanvasWithImageSession 상태 확인:', {
      conversationId,
      hasSession: !!session,
      sessionVersions: session?.versions?.length || 0,
      allCanvasItems: currentItems.length,
      imageCanvasItems: currentItems.filter(item => 
        item.type === 'image' && (item.content as any)?.conversationId === conversationId
      ).length
    });
    
    if (!session || !session.versions.length) {
      console.log('❌ ImageSession이 없거나 버전이 없음');
      return;
    }
    
    // 모든 이미지 Canvas 아이템들을 ImageSession과 동기화
    const imageCanvasItems = currentItems.filter(item => 
      item.type === 'image' && (item.content as any)?.conversationId === conversationId
    );
    
    console.log('🔍 발견된 이미지 Canvas 아이템들:', imageCanvasItems.map(item => ({
      id: item.id,
      conversationId: (item.content as any)?.conversationId,
      hasImageUrl: !!(item.content as any)?.imageUrl
    })));
    
    // ImageSession의 모든 버전을 Canvas로 변환
    session.versions.forEach((version, index) => {
      console.log(`🔍 버전 ${index + 1} 처리:`, {
        versionId: version.id,
        versionNumber: version.versionNumber,
        hasImageUrl: !!version.imageUrl,
        isSelected: version.isSelected
      });
      
      // 해당 버전에 대응하는 Canvas 아이템 찾기
      let existingCanvas = imageCanvasItems.find(canvas => {
        const content = canvas.content as any;
        return content?.selectedVersionId === version.id ||
               content?.versionId === version.id ||
               content?.imageUrl === version.imageUrl;
      });
      
      if (!existingCanvas && version.imageUrl) {
        // 대응하는 Canvas가 없으면 새로 생성
        console.log(`🆕 버전 ${version.versionNumber}에 대한 Canvas 생성`);
        
        const newCanvasContent = {
          conversationId,
          imageUrl: version.imageUrl,
          prompt: version.prompt,
          negativePrompt: version.negativePrompt,
          style: version.style,
          size: version.size,
          status: version.status,
          selectedVersionId: version.id,
          versionId: version.id,
          versionNumber: version.versionNumber
        };
        
        const newCanvas: CanvasItem = {
          id: `canvas_${conversationId}_${version.id}`,
          type: 'image',
          content: newCanvasContent,
          position: { x: 50 + (index * 20), y: 50 + (index * 20) },
          size: { width: 400, height: 300 },
          createdAt: version.createdAt,
          updatedAt: new Date().toISOString(),
          metadata: { fromImageSession: true }
        };
        
        set(state => ({
          items: [...state.items, newCanvas]
        }));
        
        console.log(`✅ 새 Canvas 생성 완료:`, newCanvas.id);
      } else if (existingCanvas) {
        // 기존 Canvas 업데이트
        console.log(`🔄 기존 Canvas 업데이트: ${existingCanvas.id}`);
        
        const updatedContent = {
          ...existingCanvas.content,
          conversationId,
          imageUrl: version.imageUrl,
          prompt: version.prompt,
          negativePrompt: version.negativePrompt,
          style: version.style,
          size: version.size,
          status: version.status,
          selectedVersionId: version.id,
          versionId: version.id,
          versionNumber: version.versionNumber
        };
        
        get().updateItem(existingCanvas.id, { content: updatedContent });
        console.log(`✅ Canvas 업데이트 완료: ${existingCanvas.id}`);
      }
    });
    
    // 선택된 버전이 있으면 해당 Canvas를 활성화하고 메인 이미지로 설정
    if (session.selectedVersionId) {
      const selectedVersion = session.versions.find(v => v.id === session.selectedVersionId);
      const selectedCanvas = get().items.find(item => 
        item.type === 'image' && 
        (item.content as any)?.conversationId === conversationId &&
        ((item.content as any)?.selectedVersionId === session.selectedVersionId ||
         (item.content as any)?.versionId === session.selectedVersionId)
      );
      
      if (selectedCanvas && selectedVersion) {
        console.log('🎯 선택된 버전의 Canvas 활성화 및 메인 이미지 업데이트:', {
          canvasId: selectedCanvas.id,
          versionId: selectedVersion.id,
          versionNumber: selectedVersion.versionNumber,
          imageUrl: selectedVersion.imageUrl
        });
        
        // Canvas의 메인 컨텐츠를 선택된 버전으로 업데이트
        get().updateItem(selectedCanvas.id, {
          content: {
            ...selectedCanvas.content,
            conversationId,
            imageUrl: selectedVersion.imageUrl,
            prompt: selectedVersion.prompt,
            negativePrompt: selectedVersion.negativePrompt,
            style: selectedVersion.style,
            size: selectedVersion.size,
            status: selectedVersion.status,
            selectedVersionId: selectedVersion.id,
            versionId: selectedVersion.id,
            versionNumber: selectedVersion.versionNumber
          }
        });
        
        // Canvas 활성화
        set({
          activeItemId: selectedCanvas.id,
          isCanvasOpen: true
        });
      }
    }
    
    console.log('✅ Canvas ↔ ImageSession 동기화 완료');
  },

  // ImageSession Store 변경 감지 시 Canvas 자동 업데이트
  onImageSessionChanged: (conversationId) => {
    console.log('📢 Canvas Store - ImageSession 변경 감지:', conversationId);
    get().syncCanvasWithImageSession(conversationId);
  },

  // 🚀 즉시 동기화 시스템 (큐 대신 바로 실행)
  syncImageToSessionStore: async (conversationId, canvasData) => {
    console.log('📋 Canvas Store - 즉시 동기화 시스템으로 바로 실행:', conversationId);
    
    try {
      // 즉시 동기화 실행
      const result = await get()._executeSyncImageToSessionStore(conversationId, canvasData);
      
      // 기존 큐도 처리 (다른 대기 중인 작업들)
      const canvasStore = get();
      canvasStore.processSyncQueue().catch(error => {
        console.error('❌ Canvas Store - 기존 큐 처리 실패 (백그라운드):', error);
      });
      
      console.log('✅ Canvas Store - 즉시 동기화 완료:', result);
      return result;
      
    } catch (error) {
      console.error('❌ Canvas Store - 즉시 동기화 실패:', error);
      
      // 실패 시 폴백: 큐에 추가
      console.log('🔄 Canvas Store - 폴백: 큐에 추가');
      get().addSyncTask({
        conversationId,
        type: 'canvas_to_session',
        data: { canvasData }
      });
      
      return { action: 'fallback_queued', reason: 'immediate_sync_failed', error: error.message };
    }
  },
  
  // Canvas에서 버전 선택 시 즉시 동기화 (v2.0 - Canvas 완전 통합)
  selectVersionInCanvas: async (conversationId, versionId) => {
    console.log('🎯 Canvas Store - 즉시 버전 선택 시스템:', { conversationId, versionId });
    
    const currentItems = get().items;
    const existingCanvas = ConversationCanvasManager.findCanvas(currentItems, conversationId, 'image');
    
    if (!existingCanvas) {
      console.warn('⚠️ Canvas Store - 버전 선택할 Canvas가 없음');
      return;
    }
    
    try {
      // 🚀 Step 1: ImageSession Store에서 버전 선택 즉시 실행
      const imageSessionStore = useImageSessionStore.getState();
      await imageSessionStore.selectVersionHybrid(conversationId, versionId);
      
      console.log('✅ Canvas Store - ImageSession 버전 선택 완료');
      
      // 🚀 Step 2: 최신 ImageSession 데이터로 Canvas 즉시 업데이트
      const updatedSession = imageSessionStore.getSession(conversationId);
      
      if (updatedSession) {
        console.log('🔗 Canvas Store - Canvas 즉시 업데이트:', {
          selectedVersionId: updatedSession.selectedVersionId,
          versionsCount: updatedSession.versions.length
        });
        
        // 선택된 버전 정보 직접 가져오기
        const selectedVersion = updatedSession.versions.find(v => v.id === versionId);
        
        if (selectedVersion) {
          console.log('🔍 Canvas Store - 선택된 버전 정보:', {
            versionId: selectedVersion.id,
            versionNumber: selectedVersion.versionNumber,
            imageUrl: selectedVersion.imageUrl,
            prompt: selectedVersion.prompt.substring(0, 50) + '...'
          });
          
          // Canvas Store의 기존 아이템을 선택된 버전으로 직접 업데이트
          const updatedContent = {
            ...existingCanvas.content,
            conversationId,
            imageUrl: selectedVersion.imageUrl,
            prompt: selectedVersion.prompt,
            negativePrompt: selectedVersion.negativePrompt,
            style: selectedVersion.style,
            size: selectedVersion.size,
            status: selectedVersion.status,
            selectedVersionId: selectedVersion.id,
            versionId: selectedVersion.id,
            versionNumber: selectedVersion.versionNumber,
            // 강제 리렌더링을 위한 타임스탬프 추가
            lastUpdated: new Date().toISOString()
          };
          
          get().updateItem(existingCanvas.id, {
            content: updatedContent,
            updatedAt: new Date().toISOString()
          });
        } else {
          console.warn('⚠️ Canvas Store - 선택된 버전을 찾을 수 없음:', versionId);
        }
        
        console.log('✅ Canvas Store - Canvas 메인 이미지 즉시 전환 완료:', {
          newImageUrl: selectedVersion?.imageUrl,
          newSelectedVersionId: selectedVersion?.id
        });
        
        // Canvas가 활성화되어 있지 않거나 다른 Canvas가 활성화되어 있으면 활성화
        const currentState = get();
        if (!currentState.isCanvasOpen || currentState.activeItemId !== existingCanvas.id) {
          console.log('🎯 Canvas 활성화 (버전 선택과 함께):', {
            wasOpen: currentState.isCanvasOpen,
            previousActive: currentState.activeItemId,
            newActive: existingCanvas.id
          });
          
          set({
            activeItemId: existingCanvas.id,
            isCanvasOpen: true,
            lastConversationId: conversationId
          });
        }
      }
      
    } catch (error) {
      console.error('❌ Canvas Store - 즉시 버전 선택 실패:', error);
      
      // 실패 시 폴백: 큐 시스템 사용
      console.log('🔄 Canvas Store - 폴백: 큐 시스템으로 처리');
      get().addSyncTask({
        conversationId,
        type: 'version_select',
        data: { versionId }
      });
      get().addSyncTask({
        conversationId,
        type: 'session_to_canvas',
        data: {}
      });
    }
  },
  
  // === 진화형 이미지 시스템 통합 (레거시 - 호환성 유지) ===
  activateSessionCanvas: (conversationId) => {
    console.log('🎨 Canvas Store - activateSessionCanvas (개선된 다중 버전 지원):', conversationId);
    
    // 🚨 RACE CONDITION 방지: DB 로딩 중이면 기다리거나 기존 Canvas 반환
    const imageSessionStore = useImageSessionStore.getState();
    
    // DB 로딩 중인지 확인
    if (imageSessionStore.isLoadingSession(conversationId)) {
      console.log('⏸️ DB 로딩 중이므로 activateSessionCanvas 지연');
      
      // 기존 Canvas가 있으면 반환, 없으면 빈 ID
      const existingCanvas = get().items.find(item => 
        item.type === 'image' && 
        (item.content as any)?.conversationId === conversationId
      );
      
      if (existingCanvas) {
        console.log('✅ 기존 Canvas 반환 (DB 로딩 중):', existingCanvas.id);
        return existingCanvas.id;
      } else {
        console.log('⚠️ DB 로딩 중이고 기존 Canvas 없음, 빈 ID 반환');
        return '';
      }
    }
    
    // 🛡️ DB 로딩이 끝났지만 세션이 없는 경우 처리
    if (!imageSessionStore.hasSession(conversationId)) {
      console.log('⚠️ Canvas Store - DB 로딩 완료했지만 이미지 세션이 존재하지 않음:', conversationId);
      
      // 기존 Canvas 찾아서 반환 (Canvas Store 우선)
      const existingCanvas = get().items.find(item => 
        item.type === 'image' && 
        (item.content as any)?.conversationId === conversationId
      );
      
      if (existingCanvas) {
        console.log('✅ 기존 Canvas 반환 (세션 없음):', existingCanvas.id);
        return existingCanvas.id;
      } else {
        return '';
      }
    }
    
    const session = imageSessionStore.getSession(conversationId);
    if (!session || !session.versions.length) {
      console.warn('⚠️ Canvas Store - 세션이 없거나 버전이 없음');
      
      // 기존 Canvas 찾아서 반환 (Canvas Store 우선)
      const existingCanvas = get().items.find(item => 
        item.type === 'image' && 
        (item.content as any)?.conversationId === conversationId
      );
      
      if (existingCanvas) {
        console.log('✅ 기존 Canvas 반환 (버전 없음):', existingCanvas.id);
        return existingCanvas.id;
      } else {
        return '';
      }
    }
    
    console.log('🔍 Canvas Store - ImageSession 상태:', {
      conversationId,
      versionsCount: session.versions.length,
      selectedVersionId: session.selectedVersionId,
      versions: session.versions.map(v => ({
        id: v.id,
        versionNumber: v.versionNumber,
        hasImageUrl: !!v.imageUrl,
        isSelected: v.isSelected
      }))
    });
    
    // 🚀 Step 1: 모든 버전을 Canvas로 동기화 (이미 구현된 syncCanvasWithImageSession 사용)
    console.log('🔄 Canvas Store - 모든 이미지 버전을 Canvas로 동기화 시작');
    get().syncCanvasWithImageSession(conversationId);
    
    // 🚀 Step 2: 선택된 버전 또는 최신 버전으로 Canvas 활성화
    const selectedVersion = imageSessionStore.getSelectedVersion(conversationId) 
                          || imageSessionStore.getLatestVersion(conversationId);
    
    if (!selectedVersion) {
      console.warn('⚠️ Canvas Store - 선택된 버전이 없음');
      return '';
    }
    
    console.log('🎯 Canvas Store - 활성화할 버전:', {
      id: selectedVersion.id,
      versionNumber: selectedVersion.versionNumber,
      prompt: selectedVersion.prompt.substring(0, 50) + '...',
      imageUrl: selectedVersion.imageUrl
    });
    
    // 🚀 Step 3: 해당 버전에 대응하는 Canvas 찾기 및 활성화
    const currentItems = get().items;
    const targetCanvas = currentItems.find(item => 
      item.type === 'image' && 
      (item.content as any)?.conversationId === conversationId &&
      ((item.content as any)?.selectedVersionId === selectedVersion.id ||
       (item.content as any)?.versionId === selectedVersion.id ||
       (item.content as any)?.imageUrl === selectedVersion.imageUrl)
    );
    
    if (targetCanvas) {
      console.log('🎯 Canvas Store - 대상 Canvas 활성화:', targetCanvas.id);
      set({
        activeItemId: targetCanvas.id,
        isCanvasOpen: true,
        lastConversationId: conversationId
      });
      return targetCanvas.id;
    }
    
    // 🚀 Step 4: Canvas가 없으면 새로 생성 (폴백)
    console.log('🆕 Canvas Store - 새 Canvas 생성 (폴백)');
    const newCanvasContent = {
      conversationId,
      imageUrl: selectedVersion.imageUrl,
      prompt: selectedVersion.prompt,
      negativePrompt: selectedVersion.negativePrompt,
      style: selectedVersion.style,
      size: selectedVersion.size,
      status: selectedVersion.status,
      selectedVersionId: selectedVersion.id,
      versionId: selectedVersion.id,
      versionNumber: selectedVersion.versionNumber
    };
    
    const newCanvas: CanvasItem = {
      id: `canvas_${conversationId}_${selectedVersion.id}`,
      type: 'image',
      content: newCanvasContent,
      position: { x: 50, y: 50 },
      size: { width: 400, height: 300 },
      createdAt: selectedVersion.createdAt,
      updatedAt: new Date().toISOString(),
      metadata: { fromActivateSessionCanvas: true }
    };
    
    set(state => ({
      items: [...state.items, newCanvas],
      activeItemId: newCanvas.id,
      isCanvasOpen: true,
      lastConversationId: conversationId
    }));
    
    console.log('✅ Canvas Store - activateSessionCanvas 완료 (새 Canvas):', newCanvas.id);
    return newCanvas.id;
  },
  
  syncWithImageSession: (conversationId) => {
    console.log('⚠️ Canvas Store - syncWithImageSession (레거시 메서드, 새 메서드로 리다이렉트)');
    // 새로운 통합 메서드로 리다이렉트
    get().syncCanvasWithImageSession(conversationId);
  },
  
  // 🎯 v4.0 영구 보존 시스템 구현
  saveCanvasToPersistence: async (canvasId, canvasData) => {
    console.log('💾 Canvas 영구 저장:', canvasId);
    try {
      // TODO: 백엔드 API 연동
      // 현재는 localStorage에 백업
      const persistenceKey = `canvas_backup_${canvasId}`;
      localStorage.setItem(persistenceKey, JSON.stringify({
        canvasId,
        canvasData,
        timestamp: Date.now(),
        version: '4.0'
      }));
      
      console.log('✅ Canvas 영구 저장 완료 (로컬 백업):', canvasId);
    } catch (error) {
      console.error('❌ Canvas 영구 저장 실패:', error);
    }
  },

  loadCanvasFromPersistence: async (conversationId, canvasType) => {
    console.log('📂 Canvas 영구 저장소에서 로드:', { conversationId, canvasType });
    try {
      // TODO: 백엔드 API 연동
      // 현재는 localStorage에서 복원
      const restoredItems: CanvasItem[] = [];
      
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key?.startsWith('canvas_backup_') && key.includes(conversationId)) {
          const data = localStorage.getItem(key);
          if (data) {
            try {
              const parsed = JSON.parse(data);
              if (parsed.canvasData && (!canvasType || parsed.canvasData.type === canvasType)) {
                restoredItems.push(parsed.canvasData);
              }
            } catch (e) {
              console.warn('Canvas 백업 파싱 실패:', key, e);
            }
          }
        }
      }
      
      console.log('✅ Canvas 영구 저장소 로드 완료:', restoredItems.length);
      return restoredItems;
    } catch (error) {
      console.error('❌ Canvas 영구 저장소 로드 실패:', error);
      return [];
    }
  },

  restoreCanvasState: async (conversationId) => {
    console.log('🔄 Canvas 상태 복원:', conversationId);
    try {
      const restoredItems = await get().loadCanvasFromPersistence(conversationId);
      if (restoredItems.length > 0) {
        // 복원된 Canvas들을 Store에 병합
        set(state => ({
          items: [...state.items.filter(item => 
            (item.content as any)?.conversationId !== conversationId
          ), ...restoredItems]
        }));
        
        console.log('✅ Canvas 상태 복원 완료:', restoredItems.length);
      }
    } catch (error) {
      console.error('❌ Canvas 상태 복원 실패:', error);
    }
  },

  // 🔗 v4.0 연속성 시스템 구현
  createContinuityCanvas: async (baseCanvasId, userRequest, targetType) => {
    console.log('🔗 연속성 Canvas 생성:', { baseCanvasId, userRequest: userRequest.substring(0, 50), targetType });
    
    try {
      const baseCanvas = get().items.find(item => item.id === baseCanvasId);
      if (!baseCanvas) {
        throw new Error(`기반 Canvas를 찾을 수 없음: ${baseCanvasId}`);
      }
      
      const conversationId = (baseCanvas.content as any)?.conversationId;
      if (!conversationId) {
        throw new Error('기반 Canvas에 conversationId가 없음');
      }
      
      // 연속성 Canvas 데이터 생성
      const continuityData = await CanvasContinuity.createContinuityCanvas(
        baseCanvas,
        userRequest,
        targetType,
        conversationId
      );
      
      // 새 Canvas 생성 (연속성 메타데이터 포함)
      const requestId = `continuity_${Date.now()}`;
      const newCanvasId = await get().getOrCreateCanvasV4(
        conversationId,
        targetType,
        continuityData.canvasData,
        requestId
      );
      
      console.log('✅ 연속성 Canvas 생성 완료:', newCanvasId);
      return newCanvasId;
      
    } catch (error) {
      console.error('❌ 연속성 Canvas 생성 실패:', error);
      throw error;
    }
  },

  findReferencableCanvas: (conversationId, targetType) => {
    console.log('🔍 참조 가능한 Canvas 검색:', { conversationId, targetType });
    return CanvasContinuity.findReferencableCanvas(
      get().items,
      conversationId,
      targetType
    );
  },

  // 🔄 v4.0 자동 저장 시스템 구현
  enableAutoSave: (canvasId, canvasType) => {
    console.log('⚡ Canvas 자동 저장 활성화:', { canvasId, canvasType });
    const conversationId = canvasId.split('-')[0]; // ID에서 conversationId 추출
    
    CanvasAutoSave.startAutoSave(
      canvasId,
      canvasType,
      conversationId,
      undefined, // 초기 데이터
      { autoSaveInterval: 5000 } // 5초 간격
    );
  },

  disableAutoSave: (canvasId) => {
    console.log('⏹️ Canvas 자동 저장 비활성화:', canvasId);
    CanvasAutoSave.stopAutoSave(canvasId, true);
  },

  notifyCanvasChange: (canvasId, canvasData) => {
    if (get().autoSaveEnabled) {
      CanvasAutoSave.notifyChange(canvasId, canvasData);
    }
  },

  exportCanvas: () => {
    const state = get();
    const exportData = {
      items: state.items,
      exportedAt: new Date().toISOString(),
      version: '4.0.0',
      persistenceEnabled: state.isPersistenceEnabled,
      autoSaveEnabled: state.autoSaveEnabled
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
  
  loadCanvasForConversation: (conversationId) => {
    console.log('🔄 Canvas Store - loadCanvasForConversation:', conversationId);
    
    const state = get();
    
    // ConversationCanvasManager를 사용하여 대화의 Canvas 아이템들 조회
    const conversationCanvases = ConversationCanvasManager.getConversationCanvases(state.items, conversationId);
    
    console.log('🔍 Canvas Store - 대화의 Canvas 목록:', {
      conversationId,
      canvasCount: conversationCanvases.length,
      canvases: conversationCanvases.map(item => ({
        id: item.id,
        type: item.type
      }))
    });
    
    // 이미 같은 대화의 Canvas가 로드되어 있다면 첫 번째 Canvas 활성화
    if (state.lastConversationId === conversationId) {
      console.log('✅ Canvas Store - 이미 동일한 대화가 로드됨');
      
      if (conversationCanvases.length > 0) {
        console.log('🎨 Canvas Store - 기존 대화의 Canvas 활성화:', conversationCanvases[0].id);
        set({
          activeItemId: conversationCanvases[0].id,
          isCanvasOpen: true
        });
      }
      
      return;
    }
    
    // 대화 전환 처리
    console.log('🔄 Canvas Store - 대화 전환:', {
      from: state.lastConversationId,
      to: conversationId
    });
    
    if (conversationCanvases.length > 0) {
      // 해당 대화의 Canvas가 있으면 첫 번째 것을 활성화
      console.log('🎨 Canvas Store - 기존 대화 Canvas 복원:', conversationCanvases[0].id);
      
      // ✅ Canvas Item의 conversationId 정확성 검증 및 보정
      const targetCanvas = conversationCanvases[0];
      if (targetCanvas.content.conversationId !== conversationId) {
        console.log('🔧 Canvas Store - Canvas conversationId 불일치 감지 및 보정:', {
          canvasId: targetCanvas.id,
          currentConversationId: targetCanvas.content.conversationId,
          expectedConversationId: conversationId
        });
        
        // Canvas Item의 conversationId 보정
        set(state => ({
          items: state.items.map(item => 
            item.id === targetCanvas.id 
              ? { ...item, content: { ...item.content, conversationId } }
              : item
          ),
          activeItemId: targetCanvas.id,
          isCanvasOpen: true,
          lastConversationId: conversationId
        }));
      } else {
        set({
          activeItemId: conversationCanvases[0].id,
          isCanvasOpen: true,
          lastConversationId: conversationId
        });
      }
    } else {
      // 해당 대화의 Canvas가 없으면 Canvas 닫기
      console.log('📪 Canvas Store - 새 대화에 Canvas 없음, Canvas 닫기');
      set({
        activeItemId: null,
        isCanvasOpen: false,
        lastConversationId: conversationId
      });
    }
  },
  
  // 🚀 순차 동기화 시스템 메서드 구현
  addSyncTask: (task) => {
    const newTask: SyncTask = {
      id: `sync_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      ...task
    };
    
    set(state => ({
      syncQueue: [...state.syncQueue, newTask]
    }));
    
    console.log('📋 Canvas Store - 동기화 작업 추가:', newTask);
    
    // 큐 처리 시작 (비동기)
    const processQueue = async () => {
      await get().processSyncQueue();
    };
    processQueue();
  },
  
  processSyncQueue: async () => {
    const state = get();
    
    // 이미 처리 중이면 스킵
    if (state.isProcessingSyncQueue || state.syncQueue.length === 0) {
      return;
    }
    
    console.log('⚙️ Canvas Store - 동기화 큐 처리 시작:', state.syncQueue.length, '개 작업');
    
    set({ isProcessingSyncQueue: true });
    
    try {
      while (state.syncQueue.length > 0) {
        const task = state.syncQueue[0];
        console.log('🔄 Canvas Store - 동기화 작업 실행:', task);
        
        try {
          const imageSessionStore = useImageSessionStore.getState();
          
          switch (task.type) {
            case 'canvas_to_session':
              // 원래 syncImageToSessionStore 로직을 여기서 실행
              if (task.data && task.data.canvasData) {
                await get()._executeSyncImageToSessionStore(task.conversationId, task.data.canvasData);
              }
              break;
              
            case 'session_to_canvas':
              // syncCanvasWithImageSession 로직 실행
              get().syncCanvasWithImageSession(task.conversationId);
              break;
              
            case 'version_select':
              // 버전 선택 로직 실행
              if (task.data && task.data.versionId) {
                imageSessionStore.selectVersionHybrid(task.conversationId, task.data.versionId);
              }
              break;
          }
          
          console.log('✅ Canvas Store - 동기화 작업 완료:', task.id);
          
        } catch (error) {
          console.error('❌ Canvas Store - 동기화 작업 실패:', task.id, error);
        }
        
        // 완료된 작업을 큐에서 제거
        set(state => ({
          syncQueue: state.syncQueue.slice(1)
        }));
        
        // 다음 작업을 위한 상태 갱신
        const updatedState = get();
        if (updatedState.syncQueue.length === 0) {
          break;
        }
      }
    } finally {
      set({ isProcessingSyncQueue: false });
      console.log('✅ Canvas Store - 동기화 큐 처리 완료');
    }
  },
  
  clearSyncQueue: (conversationId) => {
    if (conversationId) {
      // 특정 대화의 작업만 제거
      set(state => ({
        syncQueue: state.syncQueue.filter(task => task.conversationId !== conversationId)
      }));
      console.log('🧹 Canvas Store - 동기화 큐 정리 (대화별):', conversationId);
    } else {
      // 전체 큐 초기화
      set({ syncQueue: [] });
      console.log('🧹 Canvas Store - 동기화 큐 전체 초기화');
    }
  },
  
  // 🔧 내부 동기화 로직 (큐에서 순차 실행)
  _executeSyncImageToSessionStore: async (conversationId, canvasData) => {
    console.log('🔄 Canvas Store - 내부 이미지 동기화 실행:', conversationId);
    
    if (!canvasData || canvasData.type !== 'image') {
      console.warn('⚠️ Canvas Store - 이미지가 아닌 데이터는 동기화 스킵');
      return { action: 'skipped', reason: 'not_image' };
    }
    
    const imageSessionStore = useImageSessionStore.getState();
    const { image_data } = canvasData;
    
    if (!image_data || !image_data.prompt) {
      console.warn('⚠️ Canvas Store - 이미지 데이터가 없어서 동기화 스킵');
      return { action: 'skipped', reason: 'no_data' };
    }
    
    try {
      // 🎯 강화된 중복 감지: SHA-256 기반 컨텐츠 해시 + 타임스탬프 윈도우
      const contentData = {
        prompt: image_data.prompt.trim(),
        style: image_data.style || 'realistic',
        size: image_data.size || '1K_1:1',
        aspectRatio: image_data.aspect_ratio || '1:1'
      };
      
      // SHA-256 해시 생성 (강력한 중복 감지)
      const contentString = JSON.stringify(contentData);
      const encoder = new TextEncoder();
      const data = encoder.encode(contentString);
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      const contentHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      
      console.log('🔐 Canvas Store - 강화된 컨텐츠 해시 생성:', {
        contentData,
        hash: contentHash.substring(0, 16) + '...'
      });
      
      // 이미지 URL 추출 (중복 확인용) - 개선된 URL 추출 로직
      let imageUrl = '';
      if (image_data.imageUrl) {
        // 직접 imageUrl 속성이 있는 경우
        imageUrl = image_data.imageUrl;
      } else if (image_data.images && image_data.images.length > 0) {
        const firstImage = image_data.images[0];
        imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url || '';
      } else if (image_data.generation_result?.images?.[0]) {
        const firstImage = image_data.generation_result.images[0];
        imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url || '';
      }
      
      console.log('🔗 Canvas Store - 추출된 이미지 URL:', imageUrl ? imageUrl.substring(0, 50) + '...' : 'URL 없음');
      
      // 🚨 DB 로딩 중이면 대기 (Race Condition 방지)
      if (imageSessionStore.isLoadingSession(conversationId)) {
        console.log('⏸️ DB 로딩 중이므로 Canvas→Session 동기화 대기');
        let waitCount = 0;
        while (imageSessionStore.isLoadingSession(conversationId) && waitCount < 10) {
          await new Promise(resolve => setTimeout(resolve, 100)); // 100ms 대기
          waitCount++;
        }
        console.log(`🔄 DB 로딩 대기 완료 (${waitCount * 100}ms)`);
      }
      
      // 세션이 없으면 생성 (DB 로딩 완료 후)
      if (!imageSessionStore.hasSession(conversationId)) {
        console.log('🆕 Canvas Store - 새 ImageSession 생성 시작:', conversationId);
        const theme = imageSessionStore.extractTheme(image_data.prompt);
        await imageSessionStore.createSessionHybrid(conversationId, theme, image_data.prompt);
        console.log('✅ Canvas Store - 새 ImageSession 생성 완료');
      } else {
        console.log('ℹ️ Canvas Store - 기존 ImageSession 발견:', {
          conversationId,
          versionsCount: imageSessionStore.getSession(conversationId)?.versions.length || 0
        });
      }
      
      // 🔍 정교한 중복 버전 검색 (강화된 기준 적용)
      const session = imageSessionStore.getSession(conversationId);
      if (session) {
        console.log('🔍 Canvas Store - 중복 검사 시작:', {
          conversationId,
          existingVersions: session.versions.length,
          searchPrompt: image_data.prompt.substring(0, 40),
          searchImageUrl: imageUrl ? imageUrl.substring(-30) : 'URL 없음'
        });
        
        const existingVersion = session.versions.find(version => {
          // 🔐 1단계: 컨텐츠 해시 기반 정확한 중복 감지 (최고 신뢰도)
          if (version.metadata?.contentHash === contentHash) {
            console.log('🔐 Canvas Store - 해시 기반 정확한 중복 감지:', {
              versionId: version.id.substring(0, 8),
              hash: contentHash.substring(0, 16) + '...'
            });
            return true;
          }
          
          // 🔗 2단계: URL 매칭 (높은 신뢰도)
          const hasValidUrl = imageUrl && imageUrl.length > 20 && version.imageUrl && version.imageUrl.length > 20;
          if (hasValidUrl && version.imageUrl === imageUrl) {
            console.log('🔗 Canvas Store - URL 기반 중복 감지:', {
              versionId: version.id.substring(0, 8),
              url: imageUrl.substring(-30)
            });
            return true;
          }
          
          // ⏰ 3단계: 시간 기반 중복 방지 (Race Condition 해결)
          if (version.createdAt) {
            const versionTime = new Date(version.createdAt).getTime();
            const currentTime = Date.now();
            const timeDiff = currentTime - versionTime;
            
            // 10초 이내 생성 + 동일한 프롬프트면 중복으로 간주 (더 엄격한 기준)
            if (timeDiff < 10000 && version.prompt.trim() === image_data.prompt.trim()) {
              console.log('⏰ Canvas Store - 시간 기반 중복 감지 (Race Condition 방지):', {
                versionId: version.id.substring(0, 8),
                timeDiff: `${timeDiff}ms`,
                thresholdMs: 10000
              });
              return true;
            }
          }
          
          return false;
        });
        
        if (existingVersion) {
          console.log('🎯 Canvas Store - 실제 중복 버전 발견, 선택으로 변경:', {
            versionId: existingVersion.id,
            versionNumber: existingVersion.versionNumber,
            prompt: existingVersion.prompt.substring(0, 40)
          });
          
          // 🛡️ DB 동기화 오류 방지를 위한 안전한 선택
          try {
            await imageSessionStore.selectVersionHybrid(conversationId, existingVersion.id);
            return { action: 'selected_existing', versionId: existingVersion.id, reason: 'duplicate_detected_and_selected' };
          } catch (selectError) {
            console.warn('⚠️ Canvas Store - 기존 버전 선택 실패, 새 버전 생성으로 fallback:', selectError);
            // 선택 실패 시 새 버전 생성으로 계속 진행
          }
        } else {
          console.log('🆕 Canvas Store - 중복 없음 확인, 새 버전 생성 진행');
        }
      }
      
      // 🆕 새 버전 추가 (중복이 아닌 경우에만) - DB 동기화 오류 방지
      try {
        console.log('🎨 Canvas Store - 새 버전 생성 시작:', {
          conversationId,
          prompt: image_data.prompt.substring(0, 40),
          style: image_data.style || 'realistic',
          size: image_data.size || '1K_1:1',
          hasImageUrl: !!imageUrl
        });
        
        const versionId = await imageSessionStore.addVersionHybrid(conversationId, {
          prompt: image_data.prompt,
          negativePrompt: image_data.negative_prompt || '',
          style: image_data.style || 'realistic',
          size: image_data.size || '1K_1:1',
          imageUrl: imageUrl,
          status: image_data.status === 'completed' ? 'completed' : 'generating',
          metadata: {
            source: 'canvas_integration',
            canvasSync: true,
            contentHash: contentHash,     // 🔐 컨텐츠 해시 저장으로 정확한 중복 감지
            contentData: contentData,     // 📊 원본 컨텐츠 데이터 보존
            deduplicationVersion: '5.0'   // 🏷️ 중복 감지 버전 태그
          },
          isSelected: true
        });
        
        console.log('✅ Canvas Store - 새 버전 생성 완료:', versionId);
        return { action: 'created_new', versionId, reason: 'unique_content' };
        
      } catch (versionCreateError) {
        console.error('❌ Canvas Store - 새 버전 생성 실패:', versionCreateError);
        
        // 🛡️ Graceful Fallback: 메모리에서만 처리
        console.log('🔄 Canvas Store - DB 동기화 실패, 메모리 전용 모드로 fallback');
        
        try {
          // 메모리에서만 버전 생성
          const fallbackVersionId = imageSessionStore.addVersion(conversationId, {
            prompt: image_data.prompt,
            negativePrompt: image_data.negative_prompt || '',
            style: image_data.style || 'realistic',
            size: image_data.size || '1K_1:1',
            imageUrl: imageUrl,
            status: image_data.status === 'completed' ? 'completed' : 'generating',
            metadata: {
              source: 'canvas_integration_fallback',
              canvasSync: false,
              contentHash: contentHash,     // 🔐 fallback에서도 해시 저장
              contentData: contentData,     // 📊 원본 데이터 보존
              deduplicationVersion: '5.0'   // 🏷️ 중복 감지 버전 태그
            },
            isSelected: true
          });
          
          console.log('✅ Canvas Store - 메모리 전용 버전 생성 완료:', fallbackVersionId);
          return { action: 'created_fallback', versionId: fallbackVersionId, reason: 'db_sync_failed_memory_only' };
          
        } catch (fallbackError) {
          console.error('❌ Canvas Store - 메모리 전용 버전 생성도 실패:', fallbackError);
          return { action: 'error', reason: `DB 및 메모리 버전 생성 모두 실패: ${fallbackError.message}` };
        }
      }
      
    } catch (error) {
      console.error('❌ Canvas Store - 내부 ImageSession Store 동기화 실패:', error);
      
      // 🛡️ Final Graceful Fallback
      return { action: 'error', reason: `동기화 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`, fallback: true };
    }
  },
  
  clearCanvasForNewConversation: () => {
    console.log('🆕 Canvas Store - 새 대화를 위한 Canvas 초기화');
    set({
      items: [],
      activeItemId: null,
      isCanvasOpen: false,
      lastConversationId: null,
      // 동기화 큐도 함께 초기화
      syncQueue: [],
      isProcessingSyncQueue: false
    });
  },

  // v4.0 자동 저장 상태 조회
  getAutoSaveStatus: (canvasId: string) => {
    try {
      return CanvasAutoSave.getAutoSaveStatus(canvasId);
    } catch (error) {
      console.error('❌ Canvas Store - 자동 저장 상태 조회 실패:', error);
      return null;
    }
  },
  
  // 🔄 Canvas → ImageSession 역방향 동기화 (v4.1)
  syncCanvasToImageSession: async (conversationId, canvasItems) => {
    console.log('🔄 Canvas Store - Canvas → ImageSession 역방향 동기화 시작:', conversationId);
    
    const imageSessionStore = useImageSessionStore.getState();
    
    // Canvas 아이템 필터링 (파라미터로 전달되지 않은 경우 Store에서 추출)
    const targetCanvasItems = canvasItems || get().items.filter(item => 
      item.type === 'image' && 
      (item.content as any)?.conversationId === conversationId
    );
    
    console.log('🔍 Canvas Store - 역방향 동기화 대상:', {
      conversationId,
      canvasItemsCount: targetCanvasItems.length,
      canvasItems: targetCanvasItems.map(item => ({
        id: item.id,
        hasImageUrl: !!(item.content as any)?.imageUrl,
        versionNumber: (item.content as any)?.versionNumber || 'unknown'
      }))
    });
    
    if (targetCanvasItems.length === 0) {
      console.log('ℹ️ Canvas Store - 동기화할 Canvas 아이템 없음');
      return { action: 'no_items', versionsAdded: 0 };
    }
    
    try {
      let versionsAdded = 0;
      
      // 세션이 없으면 생성
      if (!imageSessionStore.hasSession(conversationId)) {
        console.log('🆕 Canvas Store - ImageSession 생성 (역방향 동기화용)');
        const firstCanvas = targetCanvasItems[0];
        const firstContent = firstCanvas.content as any;
        
        const theme = firstContent.style || '이미지 생성';
        const basePrompt = firstContent.prompt || '사용자 요청';
        
        await imageSessionStore.createSessionHybrid(conversationId, theme, basePrompt);
        console.log('✅ Canvas Store - 역방향 동기화용 ImageSession 생성 완료');
      }
      
      const session = imageSessionStore.getSession(conversationId);
      if (!session) {
        console.error('❌ Canvas Store - ImageSession 생성 실패');
        return { action: 'session_creation_failed', versionsAdded: 0 };
      }
      
      // Canvas 아이템들을 versionNumber 순으로 정렬
      const sortedCanvasItems = targetCanvasItems.sort((a, b) => {
        const aVersionNumber = (a.content as any)?.versionNumber || 1;
        const bVersionNumber = (b.content as any)?.versionNumber || 1;
        return aVersionNumber - bVersionNumber;
      });
      
      // Canvas 아이템을 ImageVersion으로 변환 및 추가
      for (const [index, canvasItem] of sortedCanvasItems.entries()) {
        const canvasContent = canvasItem.content as any;
        
        // 🔍 중복 확인: 이미 존재하는 버전인지 체크
        const existingVersion = session.versions.find(version => {
          // URL 기반 매칭 (가장 확실한 방법)
          const urlMatch = version.imageUrl && canvasContent.imageUrl && 
                          version.imageUrl === canvasContent.imageUrl;
          
          // 프롬프트 + 스타일 + 크기 기반 매칭
          const contentMatch = version.prompt.trim() === (canvasContent.prompt || '').trim() &&
                              version.style === (canvasContent.style || 'realistic') &&
                              version.size === (canvasContent.size || '1K_1:1');
          
          return urlMatch || contentMatch;
        });
        
        if (existingVersion) {
          console.log(`⚠️ Canvas Store - Canvas 아이템 ${index + 1} 이미 존재하는 버전:`, existingVersion.id);
          continue; // 중복이므로 건너뜀
        }
        
        // 🆕 새로운 버전으로 추가
        console.log(`🆕 Canvas Store - Canvas 아이템 ${index + 1}를 ImageVersion으로 변환 중`);
        
        try {
          const newVersionId = await imageSessionStore.addVersionHybrid(conversationId, {
            prompt: canvasContent.prompt || '이미지 생성',
            negativePrompt: canvasContent.negativePrompt || '',
            style: canvasContent.style || 'realistic',
            size: canvasContent.size || '1K_1:1',
            imageUrl: canvasContent.imageUrl || '',
            status: (canvasContent.status === 'completed') ? 'completed' : 'generating',
            isSelected: false // 나중에 선택 처리
          });
          
          versionsAdded++;
          console.log(`✅ Canvas Store - 새 ImageVersion 생성 완료: ${newVersionId} (${index + 1}/${sortedCanvasItems.length})`);
          
        } catch (versionAddError) {
          console.error(`❌ Canvas Store - Canvas 아이템 ${index + 1} 변환 실패:`, versionAddError);
          // 실패해도 계속 진행
        }
      }
      
      // 🎯 가장 최신 버전 선택
      if (versionsAdded > 0) {
        const updatedSession = imageSessionStore.getSession(conversationId);
        if (updatedSession && updatedSession.versions.length > 0) {
          const latestVersion = updatedSession.versions.reduce((latest, current) =>
            latest.versionNumber > current.versionNumber ? latest : current
          );
          
          try {
            await imageSessionStore.selectVersionHybrid(conversationId, latestVersion.id);
            console.log('🎯 Canvas Store - 최신 버전 자동 선택:', latestVersion.versionNumber);
          } catch (selectError) {
            console.warn('⚠️ Canvas Store - 최신 버전 선택 실패 (무시 가능):', selectError);
          }
        }
      }
      
      console.log('✅ Canvas Store - Canvas → ImageSession 역방향 동기화 완료:', {
        conversationId,
        totalCanvasItems: targetCanvasItems.length,
        versionsAdded,
        finalVersionCount: imageSessionStore.getSession(conversationId)?.versions.length || 0
      });
      
      return { 
        action: versionsAdded > 0 ? 'versions_added' : 'all_existed', 
        versionsAdded 
      };
      
    } catch (error) {
      console.error('❌ Canvas Store - Canvas → ImageSession 역방향 동기화 실패:', error);
      return { 
        action: 'error', 
        versionsAdded: 0,
        error: error instanceof Error ? error.message : '알 수 없는 오류'
      };
    }
  },

  // 🚫 중복 실행 방지 시스템 (v4.1)
  isSyncInProgress: (conversationId) => {
    return get().syncInProgress[conversationId] || false;
  },

  setSyncInProgress: (conversationId, inProgress) => {
    set(state => ({
      syncInProgress: {
        ...state.syncInProgress,
        [conversationId]: inProgress
      }
    }));
    console.log(`🔄 Canvas Store - 동기화 상태 설정: ${conversationId} = ${inProgress}`);
  },

  isCanvasProcessed: (conversationId, canvasId) => {
    const processedSet = get().processedCanvasItems[conversationId];
    return processedSet ? processedSet.has(canvasId) : false;
  },

  markCanvasAsProcessed: (conversationId, canvasId) => {
    set(state => {
      const currentSet = state.processedCanvasItems[conversationId] || new Set<string>();
      const newSet = new Set(currentSet);
      newSet.add(canvasId);
      
      return {
        processedCanvasItems: {
          ...state.processedCanvasItems,
          [conversationId]: newSet
        }
      };
    });
    console.log(`✅ Canvas Store - Canvas 처리 완료 표시: ${conversationId} / ${canvasId}`);
  },

  clearProcessedCanvasItems: (conversationId) => {
    set(state => {
      const { [conversationId]: removed, ...remaining } = state.processedCanvasItems;
      return {
        processedCanvasItems: remaining,
        syncInProgress: {
          ...state.syncInProgress,
          [conversationId]: false
        }
      };
    });
    console.log(`🗑️ Canvas Store - 처리된 Canvas 아이템 초기화: ${conversationId}`);
  },

  // ⏱️ API 디바운싱 메서드들 (v4.5 추가)
  debouncedSyncCanvasToImageSession: async (conversationId, canvasItems, delayMs = 200) => {
    console.log(`⏱️ Canvas Store - 디바운싱 동기화 요청 (${delayMs}ms 지연):`, conversationId);
    
    // 기존 타이머 클리어
    const currentTimer = get().debounceTimers[conversationId];
    if (currentTimer) {
      clearTimeout(currentTimer);
      console.log(`⏹️ Canvas Store - 기존 타이머 취소:`, conversationId);
    }
    
    return new Promise((resolve, reject) => {
      const timer = setTimeout(async () => {
        try {
          console.log(`🚀 Canvas Store - 디바운싱 지연 완료, 실제 동기화 실행:`, conversationId);
          const result = await get().syncCanvasToImageSession(conversationId, canvasItems);
          
          // 타이머 정리
          set((state) => ({
            debounceTimers: {
              ...state.debounceTimers,
              [conversationId]: undefined
            }
          }));
          
          resolve(result);
        } catch (error) {
          console.error('❌ Canvas Store - 디바운싱 동기화 실패:', error);
          reject(error);
        }
      }, delayMs);
      
      // 타이머 저장
      set((state) => ({
        debounceTimers: {
          ...state.debounceTimers,
          [conversationId]: timer
        }
      }));
    });
  },
  
  clearDebounceTimer: (conversationId) => {
    const timer = get().debounceTimers[conversationId];
    if (timer) {
      clearTimeout(timer);
      set((state) => ({
        debounceTimers: {
          ...state.debounceTimers,
          [conversationId]: undefined
        }
      }));
      console.log(`🗑️ Canvas Store - 디바운싱 타이머 클리어:`, conversationId);
    }
  },

}), {
  name: 'canvas-store', // LocalStorage 키 이름
  storage: createJSONStorage(() => localStorage),
  
  // 특정 필드만 지속화 (activeItemId, isCanvasOpen은 세션별로 초기화)
  partialize: (state) => ({
    items: state.items,
    lastConversationId: state.lastConversationId,
  }),
  
  // 상태 복원 시 실행
  onRehydrateStorage: () => (state) => {
    if (state) {
      console.log('🔄 Canvas Store - LocalStorage에서 상태 복원 완료:', {
        itemsCount: state.items.length,
        lastConversationId: state.lastConversationId
      });
      
      // Canvas 상태는 항상 닫힌 상태로 시작
      state.activeItemId = null;
      state.isCanvasOpen = false;
    }
  },
  
  // 🎨 Request-based Canvas Evolution System Implementation (Phase 4.2)
  evolveCanvasImage: async (conversationId, canvasId, referenceImageId, newPrompt, evolutionParams = {}) => {
    console.log('🎨 Canvas Store - 이미지 진화 시작:', {
      conversationId,
      canvasId,
      referenceImageId,
      newPrompt: newPrompt.slice(0, 30) + '...',
      evolutionParams
    });
    
    try {
      // 사용자 정보 가져오기 (인증 상태에서)
      // TODO: 실제 인증 시스템에서 userId 가져오기
      const userId = 'temp-user-id'; // 임시값
      
      const request = {
        conversationId,
        userId,
        prompt: newPrompt,
        source: 'canvas' as const,
        canvasId,
        referenceImageId,
        evolutionType: evolutionParams.evolutionType || 'variation',
        editMode: 'EDIT_MODE_DEFAULT', // Context7 표준 마스크 프리 모드
        style: evolutionParams.style,
        size: evolutionParams.size
      };
      
      const result = await get().dispatchImageRequest(request);
      
      if (result.success && result.data) {
        // 성공 시 Canvas Store 및 ImageSession Store 동기화
        await get().ensureImageSession(conversationId, result.data);
        await get().syncCanvasWithBackend(canvasId);
        
        console.log('✅ Canvas 이미지 진화 완료:', {
          newImageUrl: result.data.imageUrl,
          canvasVersion: result.data.canvas_version
        });
      }
      
      return result;
      
    } catch (error) {
      console.error('❌ Canvas 이미지 진화 실패:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '이미지 진화 중 오류가 발생했습니다'
      };
    }
  },
  
  // 🔄 Backend Workflow Integration Implementation
  dispatchImageRequest: async (request) => {
    console.log('🔄 Canvas Store - 백엔드 워크플로우 디스패치:', {
      source: request.source,
      hasCanvasId: !!request.canvasId,
      hasReferenceImageId: !!request.referenceImageId
    });
    
    try {
      // 백엔드 Canvas 워크플로우 디스패처 API 호출
      const response = await fetch('/api/v1/canvas/dispatch-image-request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // TODO: Authorization 헤더 추가
        },
        body: JSON.stringify(request)
      });
      
      if (!response.ok) {
        throw new Error(`API 요청 실패: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      
      console.log('✅ Canvas Store - 백엔드 워크플로우 응답:', {
        success: result.success,
        workflowMode: result.workflow_mode,
        hasData: !!result.data
      });
      
      return {
        success: result.success,
        data: result.data,
        error: result.error,
        workflowMode: result.workflow_mode
      };
      
    } catch (error) {
      console.error('❌ Canvas Store - 백엔드 워크플로우 디스패치 실패:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '워크플로우 디스패치 중 오류가 발생했습니다'
      };
    }
  },
  
  // 🎯 Canvas-Backend Synchronization Implementation
  syncCanvasWithBackend: async (canvasId) => {
    console.log('🎯 Canvas Store - 백엔드 동기화 시작:', canvasId);
    
    try {
      const canvas = get().items.find(item => item.id === canvasId);
      if (!canvas) {
        console.warn('⚠️ 동기화할 Canvas를 찾을 수 없음:', canvasId);
        return;
      }
      
      const conversationId = (canvas.content as any)?.conversationId;
      if (!conversationId) {
        console.warn('⚠️ Canvas에 conversationId가 없음:', canvasId);
        return;
      }
      
      // 백엔드에서 최신 Canvas 히스토리 가져오기
      const history = await get().loadCanvasHistory(conversationId, canvasId);
      
      if (history.length > 0) {
        // Canvas Store와 ImageSession Store 동기화
        await get().ensureImageSession(conversationId, {
          image_data: {
            images: history.map(h => h.image_url).filter(Boolean)
          }
        });
        
        console.log('✅ Canvas-백엔드 동기화 완료:', {
          canvasId,
          historyCount: history.length
        });
      }
      
    } catch (error) {
      console.error('❌ Canvas-백엔드 동기화 실패:', error);
    }
  },
  
  loadCanvasHistory: async (conversationId, canvasId) => {
    console.log('📚 Canvas Store - 히스토리 로드:', { conversationId, canvasId });
    
    try {
      // 백엔드 Canvas 히스토리 API 호출
      const response = await fetch(`/api/v1/canvas/history/${conversationId}/${canvasId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          // TODO: Authorization 헤더 추가
        }
      });
      
      if (!response.ok) {
        throw new Error(`히스토리 로드 실패: ${response.status} ${response.statusText}`);
      }
      
      const result = await response.json();
      
      console.log('✅ Canvas 히스토리 로드 완료:', {
        historyCount: result.history?.length || 0,
        hasAnalysis: !!result.analysis
      });
      
      return result.history || [];
      
    } catch (error) {
      console.error('❌ Canvas 히스토리 로드 실패:', error);
      return [];
    }
  }
}));