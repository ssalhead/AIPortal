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

      // 2. 기존 Canvas 검색
      const existingCanvas = get().items.find(item => item.id === canvasId);
      
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
    // 메시지 배열에서 Canvas 데이터가 있는지 확인
    if (!Array.isArray(messages) || messages.length === 0) {
      return false;
    }
    
    // Canvas 데이터가 있는 메시지가 하나라도 있으면 true
    return messages.some(message => {
      // canvas_data 또는 canvasData 필드가 있는지 확인
      return message?.canvas_data || message?.canvasData;
    });
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
    const existingCanvas = ConversationCanvasManager.findCanvas(currentItems, conversationId, 'image');
    
    if (!existingCanvas) return;
    
    const imageSessionStore = useImageSessionStore.getState();
    const session = imageSessionStore.getSession(conversationId);
    
    if (!session) return;
    
    const { content: integratedContent } = ConversationCanvasManager.integrateImageSession(
      conversationId,
      session,
      session.selectedVersionId
    );
    
    get().updateItem(existingCanvas.id, { content: integratedContent });
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
        
        // 선택된 버전으로 Canvas 메인 컨텐츠 즉시 업데이트
        const { content: integratedContent } = ConversationCanvasManager.integrateImageSession(
          conversationId,
          updatedSession,
          updatedSession.selectedVersionId
        );
        
        // Canvas Store의 기존 아이템 즉시 업데이트
        get().updateItem(existingCanvas.id, {
          content: {
            ...existingCanvas.content,
            ...integratedContent,
            conversationId
          }
        });
        
        console.log('✅ Canvas Store - Canvas 메인 이미지 즉시 전환 완료:', {
          newImageUrl: integratedContent.imageUrl,
          newSelectedVersionId: integratedContent.selectedVersionId
        });
        
        // Canvas가 활성화되어 있지 않으면 활성화
        if (!get().isCanvasOpen) {
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
    console.log('🎨 Canvas Store - activateSessionCanvas:', conversationId);
    
    // 🎯 Step 1: 먼저 기존 Canvas 아이템 확인 (autoActivateCanvas와 동일한 로직)
    const currentItems = get().items;
    const existingConversationItem = currentItems.find(item => 
      (item.content as any).conversationId === conversationId
    );
    
    console.log('🔍 Canvas Store - activateSessionCanvas 기존 아이템 검색:', {
      conversationId,
      foundExisting: !!existingConversationItem,
      existingItemId: existingConversationItem?.id,
      totalItems: currentItems.length
    });
    
    // ImageSession Store 접근
    const imageSessionStore = useImageSessionStore.getState();
    
    // 세션이 이미 존재하는지 확인
    if (!imageSessionStore.hasSession(conversationId)) {
      console.warn('⚠️ Canvas Store - 이미지 세션이 존재하지 않음:', conversationId);
      return '';
    }
    
    const session = imageSessionStore.getSession(conversationId);
    if (!session) return '';
    
    // 선택된 버전 또는 최신 버전 가져오기
    const selectedVersion = imageSessionStore.getSelectedVersion(conversationId) 
                          || imageSessionStore.getLatestVersion(conversationId);
    
    if (!selectedVersion) {
      console.warn('⚠️ Canvas Store - 선택된 버전이 없음');
      return '';
    }
    
    console.log('🔍 Canvas Store - 사용할 버전:', {
      id: selectedVersion.id,
      versionNumber: selectedVersion.versionNumber,
      prompt: selectedVersion.prompt.substring(0, 50) + '...',
      imageUrl: selectedVersion.imageUrl
    });
    
    if (existingConversationItem) {
      console.log('🔄 Canvas Store - 기존 이미지 Canvas 아이템 업데이트 및 활성화:', existingConversationItem.id);
      
      // 기존 Canvas 아이템을 최신 버전으로 업데이트
      get().updateItem(existingConversationItem.id, {
        content: {
          ...existingConversationItem.content,
          imageUrl: selectedVersion.imageUrl,
          status: selectedVersion.status,
          prompt: selectedVersion.prompt,
          negativePrompt: selectedVersion.negativePrompt,
          style: selectedVersion.style,
          size: selectedVersion.size,
          conversationId: conversationId, // 대화 ID 유지
        }
      });
      
      set({
        isCanvasOpen: true,
        activeItemId: existingConversationItem.id,
      });
      
      return existingConversationItem.id;
    }
    
    // 새로운 Canvas 아이템 생성
    const content = {
      prompt: selectedVersion.prompt,
      negativePrompt: selectedVersion.negativePrompt,
      style: selectedVersion.style,
      size: selectedVersion.size,
      status: selectedVersion.status,
      imageUrl: selectedVersion.imageUrl,
      conversationId: conversationId, // 대화 ID 저장
    };
    
    const newItem: CanvasItem = {
      id: uuidv4(),
      type: 'image',
      content,
      position: { x: 50, y: 50 },
      size: { width: 400, height: 300 },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    console.log('✨ Canvas Store - 새로운 세션 Canvas 생성:', {
      conversationId,
      itemId: newItem.id,
      selectedVersion: selectedVersion.versionNumber,
      prompt: selectedVersion.prompt.substring(0, 50) + '...',
    });
    
    // Canvas 활성화
    set((state) => ({
      items: [...state.items, newItem],
      activeItemId: newItem.id,
      isCanvasOpen: true
    }));
    
    return newItem.id;
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
      set({
        activeItemId: conversationCanvases[0].id,
        isCanvasOpen: true,
        lastConversationId: conversationId
      });
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
      // 🎯 중복 감지: Canvas 데이터 기반 고유 식별자 생성
      const uniqueId = `${image_data.prompt}_${image_data.style || 'realistic'}_${image_data.size || '1K_1:1'}`;
      console.log('🔍 Canvas Store - 고유 식별자 생성:', uniqueId);
      
      // 이미지 URL 추출 (중복 확인용)
      let imageUrl = '';
      if (image_data.images && image_data.images.length > 0) {
        const firstImage = image_data.images[0];
        imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url || '';
      } else if (image_data.generation_result?.images?.[0]) {
        const firstImage = image_data.generation_result.images[0];
        imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url || '';
      }
      
      // 세션이 없으면 생성
      if (!imageSessionStore.hasSession(conversationId)) {
        const theme = imageSessionStore.extractTheme(image_data.prompt);
        await imageSessionStore.createSessionHybrid(conversationId, theme, image_data.prompt);
        console.log('✅ Canvas Store - 새 ImageSession 생성 완료');
      }
      
      // 🔍 정교한 중복 버전 검색 (엄격한 기준 적용)
      const session = imageSessionStore.getSession(conversationId);
      if (session) {
        const existingVersion = session.versions.find(version => {
          const versionId = `${version.prompt}_${version.style}_${version.size}`;
          const urlMatch = version.imageUrl === imageUrl && imageUrl !== '' && imageUrl.length > 10; // URL이 유효할 때만
          const contentMatch = versionId === uniqueId;
          
          // 더 엄격한 중복 판정: URL이 완전히 같거나, 내용이 완전히 동일할 때만
          const isRealDuplicate = (contentMatch && urlMatch) || // 내용과 URL 모두 동일
                                  (urlMatch && !contentMatch && version.prompt.trim() === image_data.prompt.trim()); // URL 같고 프롬프트도 동일
          
          console.log('🔍 Canvas Store - 중복 검사:', {
            versionId: version.id,
            versionPrompt: version.prompt.substring(0, 30),
            currentPrompt: image_data.prompt.substring(0, 30),
            contentMatch,
            urlMatch,
            isRealDuplicate
          });
          
          return isRealDuplicate;
        });
        
        if (existingVersion) {
          console.log('🎯 Canvas Store - 실제 중복 버전 발견, 선택으로 변경:', existingVersion.id);
          
          // 새 버전 생성 대신 기존 버전 선택
          imageSessionStore.selectVersionHybrid(conversationId, existingVersion.id);
          return { action: 'selected_existing', versionId: existingVersion.id, reason: 'real_duplicate_detected' };
        } else {
          console.log('🆕 Canvas Store - 중복 아님, 새 버전 생성 진행');
        }
      }
      
      // 🆕 새 버전 추가 (중복이 아닌 경우에만)
      const versionId = await imageSessionStore.addVersionHybrid(conversationId, {
        prompt: image_data.prompt,
        negativePrompt: image_data.negative_prompt || '',
        style: image_data.style || 'realistic',
        size: image_data.size || '1K_1:1',
        imageUrl: imageUrl,
        status: image_data.status === 'completed' ? 'completed' : 'generating',
        isSelected: true
      });
      
      console.log('✅ Canvas Store - 새 버전 생성 완료:', versionId);
      return { action: 'created_new', versionId, reason: 'unique_content' };
      
    } catch (error) {
      console.error('❌ Canvas Store - 내부 ImageSession Store 동기화 실패:', error);
      return { action: 'error', reason: error.message };
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

  // v4.0 Canvas 변경 알림
  notifyCanvasChange: (canvasId: string, canvasData: any) => {
    try {
      CanvasAutoSave.notifyChange(canvasId, canvasData);
    } catch (error) {
      console.error('❌ Canvas Store - Canvas 변경 알림 실패:', error);
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
  }
}));