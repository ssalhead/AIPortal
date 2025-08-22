/**
 * Canvas 상태 관리 Store
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';
import type { CanvasItem, CanvasToolType, TextNote, ImageGeneration, MindMapNode } from '../types/canvas';
import { useImageSessionStore } from './imageSessionStore';

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
  lastConversationId: string | null; // 마지막으로 로드한 대화 ID
  
  // Actions - AI 주도 Canvas 관리
  addItem: (type: CanvasToolType, content: any) => void;
  updateItem: (id: string, updates: Partial<CanvasItem>) => void;
  deleteItem: (id: string) => void;
  clearCanvas: () => void;
  setActiveItem: (id: string | null) => void;
  
  // 조건부 Canvas 활성화 (빈 Canvas 방지)
  openWithArtifact: (artifactId: string) => void;
  autoActivateCanvas: (canvasData: any, conversationId?: string) => string; // Canvas 데이터로 자동 활성화, 아이템 ID 반환
  closeCanvas: () => void;
  
  // 지속성 관리
  loadCanvasForConversation: (conversationId: string) => void; // 특정 대화의 Canvas 상태 복원
  clearCanvasForNewConversation: () => void; // 새 대화 시작 시 Canvas 초기화
  
  // Helper methods
  getItemById: (id: string) => CanvasItem | undefined;
  hasActiveContent: () => boolean; // Canvas에 활성 콘텐츠가 있는지 확인
  shouldActivateForConversation: (messages: any[]) => boolean; // 대화에 Canvas 데이터가 있는지 확인
  updateCanvasWithCompletedImage: (canvasData: any) => string | null; // 완성된 이미지로 Canvas 업데이트
  
  // 진화형 이미지 시스템 통합
  activateSessionCanvas: (conversationId: string) => string; // 세션 기반 Canvas 활성화, 아이템 ID 반환
  syncWithImageSession: (conversationId: string) => void; // ImageSession과 동기화
  
  exportCanvas: () => string;
  importCanvas: (data: string) => void;
}

export const useCanvasStore = create<CanvasState>()(persist((set, get) => ({
  items: [],
  activeItemId: null,
  isCanvasOpen: false,
  lastConversationId: null,
  
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
  
  autoActivateCanvas: (canvasData, conversationId) => {
    console.log('🎨 Canvas Store - autoActivateCanvas 호출:', { canvasData, conversationId });
    
    // 진화형 이미지 시스템 적용: conversationId가 있으면 세션 기반 처리
    if (conversationId && canvasData.type === 'image') {
      console.log('🔍 Canvas Store - 진화형 이미지 시스템으로 처리 시작');
      
      // 1. 먼저 canvasData에서 이미지 정보 추출 및 ImageSessionStore에 버전 추가
      const { image_data } = canvasData;
      if (image_data) {
        console.log('🔍 Canvas Store - canvasData에서 이미지 정보 추출 중...');
        
        // 이미지 URL 추출
        let imageUrl = null;
        if (image_data.images && image_data.images.length > 0) {
          const firstImage = image_data.images[0];
          imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
        } else if (image_data.generation_result?.images?.[0]) {
          const firstImage = image_data.generation_result.images[0];
          imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
        }
        
        console.log('🔍 Canvas Store - 추출된 이미지 URL:', imageUrl);
        
        if (imageUrl) {
          // ImageSessionStore에 세션이 없으면 생성
          const imageSessionStore = useImageSessionStore.getState();
          if (!imageSessionStore.hasSession(conversationId)) {
            console.log('🔍 Canvas Store - 새 ImageSession 생성 중...');
            const theme = image_data.prompt?.substring(0, 20) || 'AI Image';
            imageSessionStore.createSession(conversationId, theme, image_data.prompt || '');
          }
          
          // 🛡️ 중복 방지: 동일한 이미지 URL이 이미 존재하는지 확인
          const session = imageSessionStore.getSession(conversationId);
          const existingVersion = session?.versions.find(version => version.imageUrl === imageUrl);
          
          if (existingVersion) {
            console.log('🛡️ Canvas Store - 동일한 이미지가 이미 존재함, 기존 버전 선택:', {
              existingVersionId: existingVersion.id,
              imageUrl: imageUrl
            });
            // 기존 버전을 선택된 상태로 설정
            imageSessionStore.selectVersion(conversationId, existingVersion.id);
          } else {
            console.log('🔍 Canvas Store - 새 이미지 발견, 하지만 인라인 링크는 미리보기 전용으로 처리');
            console.log('💡 Canvas Store - 사용자가 버전 히스토리를 직접 관리할 수 있도록 자동 추가하지 않음');
            
            // 🎨 인라인 링크 클릭은 미리보기 전용: 버전 히스토리에 추가하지 않음
            // 대신 기존 로직으로 넘어가서 임시 Canvas 아이템만 생성
            console.log('🔄 Canvas Store - 세션 기반 처리 중단, 기존 로직으로 fallback');
            
            // 이미지 정보를 sessionItemId 없이 반환하여 기존 로직이 처리하도록 함
            // 하지만 이렇게 하면 기존 로직이 실행되지 않으므로, 
            // 임시 Canvas 아이템을 직접 생성해야 함
            
            // 임시 Canvas 아이템 생성 (버전 히스토리에는 추가하지 않음)
            const tempItem = {
              id: `temp-${Date.now()}`,
              type: 'image' as const,
              title: `미리보기: ${image_data.prompt?.substring(0, 30) || 'AI 이미지'}`,
              content: {
                prompt: image_data.prompt || '',
                negativePrompt: '',
                style: image_data.style || 'realistic',
                size: image_data.size || '1024x1024',
                imageUrl: imageUrl,
                status: 'completed',
                conversationId: conversationId
              },
              x: 100,
              y: 100,
              width: 600,
              height: 400,
              zIndex: Date.now()
            };
            
            // Canvas Store에 임시 아이템 추가 (Zustand set 사용으로 React 리렌더링 트리거)
            set(state => ({
              ...state,
              items: [...state.items, tempItem],
              activeItemId: tempItem.id,
              isCanvasOpen: true
            }));
            
            console.log('🎨 Canvas Store - 임시 미리보기 아이템 생성 및 Canvas 활성화 완료:', tempItem.id);
            return tempItem.id;
          }
        }
      }
      
      // 2. 이제 activateSessionCanvas 호출
      const sessionItemId = get().activateSessionCanvas(conversationId);
      console.log('🎨 Canvas Store - 세션 기반 Canvas 활성화 완료:', sessionItemId);
      return sessionItemId; // early return으로 중복 생성 방지
    }
    
    // 기존 로직 유지 (하위 호환성)
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
      
      // 🎨 이미지 URL이 없으면 로딩 상태로 시작 (사용자가 원하는 플로우)
      const hasImage = imageUrl && imageUrl.length > 0;
      const actualStatus = hasImage ? (image_data.status || 'completed') : 'generating';
      
      console.log('🎨 Canvas 이미지 상태 결정:', {
        hasImage,
        imageUrl,
        originalStatus: image_data.status,
        actualStatus,
        userFlow: hasImage ? 'completed_image' : 'loading_state'
      });
      
      content = {
        prompt: image_data.prompt || title,
        negativePrompt: '',
        style: image_data.style || 'realistic',
        size: frontendSize,
        status: actualStatus, // 이미지가 없으면 'generating', 있으면 원래 상태
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
  
  // === 진화형 이미지 시스템 통합 ===
  activateSessionCanvas: (conversationId) => {
    console.log('🎨 Canvas Store - activateSessionCanvas:', conversationId);
    
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
    
    // 기존 Canvas 아이템 확인 (동일한 대화의 이미지 Canvas가 있는지)
    // conversationId를 기준으로 찾되, Canvas 아이템에 conversationId를 저장해야 함
    const currentItems = get().items;
    console.log('🔍 Canvas Store - 현재 아이템 목록:', currentItems.map(item => ({
      id: item.id,
      type: item.type,
      conversationId: (item.content as any).conversationId,
      prompt: item.type === 'image' ? (item.content as any).prompt : null
    })));
    console.log('🔍 Canvas Store - 찾고 있는 conversationId:', conversationId);
    
    const existingImageItem = currentItems.find(item => 
      item.type === 'image' && 
      (item.content as any).conversationId === conversationId
    );
    
    console.log('🔍 Canvas Store - 찾은 기존 아이템:', existingImageItem ? existingImageItem.id : 'none');
    
    if (existingImageItem) {
      console.log('🔄 Canvas Store - 기존 이미지 Canvas 아이템 활성화:', existingImageItem.id);
      
      // 기존 Canvas 업데이트
      get().updateItem(existingImageItem.id, {
        content: {
          ...existingImageItem.content,
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
        activeItemId: existingImageItem.id,
      });
      
      return existingImageItem.id;
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
      prompt: selectedVersion.prompt,
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
    console.log('🔄 Canvas Store - syncWithImageSession:', conversationId);
    
    const imageSessionStore = useImageSessionStore.getState();
    console.log('🔍 Canvas Store - ImageSessionStore 상태 확인');
    
    const session = imageSessionStore.getSession(conversationId);
    console.log('🔍 Canvas Store - 세션 조회 결과:', session ? {
      conversationId: session.conversationId,
      theme: session.theme,
      versionsCount: session.versions.length,
      selectedVersionId: session.selectedVersionId
    } : 'null');
    
    if (!session) {
      console.warn('⚠️ Canvas Store - 동기화할 세션이 없음');
      return;
    }
    
    // 세션의 모든 버전 로그
    console.log('🔍 Canvas Store - 세션 버전들:', session.versions.map(v => ({
      id: v.id,
      versionNumber: v.versionNumber,
      isSelected: v.isSelected,
      status: v.status,
      prompt: v.prompt.substring(0, 50) + '...'
    })));
    
    const selectedVersion = imageSessionStore.getSelectedVersion(conversationId);
    console.log('🔍 Canvas Store - 선택된 버전:', selectedVersion ? {
      id: selectedVersion.id,
      versionNumber: selectedVersion.versionNumber,
      isSelected: selectedVersion.isSelected,
      status: selectedVersion.status
    } : 'null');
    
    if (!selectedVersion) {
      console.warn('⚠️ Canvas Store - 동기화할 선택된 버전이 없음');
      // 대안: 최신 버전 시도
      const latestVersion = imageSessionStore.getLatestVersion(conversationId);
      console.log('🔄 Canvas Store - 최신 버전으로 대체 시도:', latestVersion ? latestVersion.id : 'null');
      
      if (!latestVersion) {
        return;
      }
      
      // 최신 버전으로 진행
      const versionToUse = latestVersion;
      console.log('✅ Canvas Store - 최신 버전 사용:', versionToUse.versionNumber);
      
      // 여기서 Canvas 아이템 업데이트 로직 계속...
      const activeItem = get().activeItemId ? get().getItemById(get().activeItemId) : null;
      
      if (activeItem && activeItem.type === 'image') {
        get().updateItem(activeItem.id, {
          content: {
            ...activeItem.content,
            prompt: versionToUse.prompt,
            negativePrompt: versionToUse.negativePrompt,
            style: versionToUse.style,
            size: versionToUse.size,
            imageUrl: versionToUse.imageUrl,
            status: versionToUse.status,
            conversationId: conversationId,
          }
        });
        
        console.log('✅ Canvas Store - Canvas 아이템 동기화 완료 (최신 버전):', {
          itemId: activeItem.id,
          versionNumber: versionToUse.versionNumber,
        });
      }
      return;
    }
    
    // 현재 활성 Canvas 아이템 업데이트
    const activeItem = get().activeItemId ? get().getItemById(get().activeItemId) : null;
    
    if (activeItem && activeItem.type === 'image') {
      get().updateItem(activeItem.id, {
        content: {
          ...activeItem.content,
          prompt: selectedVersion.prompt,
          negativePrompt: selectedVersion.negativePrompt,
          style: selectedVersion.style,
          size: selectedVersion.size,
          imageUrl: selectedVersion.imageUrl,
          status: selectedVersion.status,
        }
      });
      
      console.log('✅ Canvas Store - Canvas 아이템 동기화 완료:', {
        itemId: activeItem.id,
        versionNumber: selectedVersion.versionNumber,
      });
    }
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
  
  loadCanvasForConversation: (conversationId) => {
    console.log('🔄 Canvas Store - loadCanvasForConversation:', conversationId);
    
    const state = get();
    
    // 이미 같은 대화의 Canvas가 로드되어 있다면 아무것도 하지 않음
    if (state.lastConversationId === conversationId) {
      console.log('✅ Canvas Store - 이미 동일한 대화의 Canvas가 로드됨');
      return;
    }
    
    // 새로운 대화로 변경될 때 Canvas 초기화 (다른 대화의 Canvas 아이템 제거)
    if (state.lastConversationId && state.lastConversationId !== conversationId) {
      console.log('🧹 Canvas Store - 이전 대화 Canvas 정리:', state.lastConversationId);
      set({
        items: [],
        activeItemId: null,
        isCanvasOpen: false,
        lastConversationId: conversationId
      });
    } else {
      // 첫 로드인 경우
      set({
        lastConversationId: conversationId
      });
    }
  },
  
  clearCanvasForNewConversation: () => {
    console.log('🆕 Canvas Store - 새 대화를 위한 Canvas 초기화');
    set({
      items: [],
      activeItemId: null,
      isCanvasOpen: false,
      lastConversationId: null
    });
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