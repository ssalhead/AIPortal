/**
 * 단순화된 이미지 히스토리 관리 Store
 * 복잡한 세션 관리를 제거하고 conversationId 기반 단순한 이미지 히스토리 관리
 */

import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';

// 향상된 이미진 접근성 확인 함수 - 더 정교한 검증 및 로깅
const waitForImageAvailability = async (imageUrl: string, maxRetries: number = 30): Promise<boolean> => {
  // undefined 또는 null URL 체크
  if (!imageUrl || imageUrl === 'undefined' || imageUrl === 'null') {
    console.warn(`⚠️ 이미지 접근성 확인 생략 - 잘못된 URL: ${imageUrl}`);
    return false;
  }
  
  console.log(`🔍 이미지 접근성 확인 시작: ${imageUrl}`);
  
  for (let i = 0; i < maxRetries; i++) {
    try {
      // 캐시 버스팅과 unique 파라미터 추가
      const timestamp = Date.now();
      const uniqueId = Math.random().toString(36).substring(7);
      const timestampedUrl = `${imageUrl}?t=${timestamp}&retry=${i}&uid=${uniqueId}`;
      
      const response = await fetch(timestampedUrl, { 
        method: 'HEAD',
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
          'If-None-Match': '*'
        }
      });
      
      if (response.ok && response.status === 200) {
        const contentLength = response.headers.get('content-length');
        console.log(`✅ 이미지 접근 가능 확인: ${imageUrl} (시도: ${i + 1}, 크기: ${contentLength || 'unknown'})`);
        
        // 추가 검증: 실제 이미지 로딩 테스트
        return await verifyImageLoading(timestampedUrl);
      }
      
      console.log(`⏳ 이미지 대기 중: ${response.status} ${response.statusText} (${i + 1}/${maxRetries})`);
    } catch (error) {
      console.log(`❌ 이미지 접근 오류 (${i + 1}/${maxRetries}):`, error instanceof Error ? error.message : error);
    }
    
    // 적응형 대기 시간: 더 세밀한 조정
    let delay;
    if (i < 3) delay = 100;  // 첫 3번은 100ms (빠른 확인)
    else if (i < 8) delay = 300;  // 다음 5번은 300ms
    else if (i < 15) delay = 800;  // 다음 7번은 800ms
    else if (i < 22) delay = 1500;  // 다음 7번은 1.5초
    else delay = 2500;  // 나머지는 2.5초
    
    await new Promise(resolve => setTimeout(resolve, delay));
  }
  
  console.warn(`⚠️ 이미지 접근성 확인 최종 실패: ${imageUrl} (${maxRetries}번 시도 완료)`);
  return false;
};

// 실제 이미지 로딩 검증 함수
const verifyImageLoading = async (imageUrl: string): Promise<boolean> => {
  return new Promise((resolve) => {
    const img = new Image();
    const timeout = setTimeout(() => {
      console.warn(`⚠️ 이미진 로딩 타임아웃: ${imageUrl}`);
      resolve(false);
    }, 3000);
    
    img.onload = () => {
      clearTimeout(timeout);
      console.log(`✅ 실제 이미진 로딩 성공: ${imageUrl} (${img.width}x${img.height})`);
      resolve(true);
    };
    
    img.onerror = () => {
      clearTimeout(timeout);
      console.warn(`❌ 실제 이미진 로딩 실패: ${imageUrl}`);
      resolve(false);
    };
    
    img.src = imageUrl;
  });
};

// 강제 이미진 새로고침 함수 (undefined URL 안전장치 포함)
const forceImageRefresh = async (imageUrl: string, retries: number = 3): Promise<void> => {
  // undefined 또는 null URL 체크
  if (!imageUrl || imageUrl === 'undefined' || imageUrl === 'null') {
    console.warn(`⚠️ 이미진 새로고침 생략 - 잘못된 URL: ${imageUrl}`);
    return;
  }
  
  console.log(`🔄 이미진 강제 새로고침 시작: ${imageUrl}`);
  
  for (let i = 0; i < retries; i++) {
    try {
      // DOM에서 해당 이미진들 찾기
      const imageElements = document.querySelectorAll('img') as NodeListOf<HTMLImageElement>;
      let refreshCount = 0;
      
      const baseUrl = imageUrl.split('?')[0];
      if (!baseUrl) {
        console.warn(`⚠️ 기본 URL 추출 실패: ${imageUrl}`);
        break;
      }
      
      imageElements.forEach((img) => {
        if (img.src && img.src.includes(baseUrl)) {
          const originalSrc = img.src.split('?')[0];
          const newSrc = `${originalSrc}?t=${Date.now()}&refresh=${i}&uid=${Math.random().toString(36).substring(7)}`;
          
          // 이미진 로딩 상태 추적
          img.onload = () => {
            console.log(`✅ 이미진 새로고침 성공: ${newSrc}`);
          };
          
          img.onerror = () => {
            console.warn(`❌ 이미진 새로고침 실패: ${newSrc}`);
          };
          
          img.src = newSrc;
          refreshCount++;
        }
      });
      
      if (refreshCount > 0) {
        console.log(`🔄 ${refreshCount}개 이미진 새로고침 적용 (${i + 1}/${retries})`);
        await new Promise(resolve => setTimeout(resolve, 500)); // 로딩 대기
      }
      
    } catch (error) {
      console.warn(`⚠️ 이미진 새로고침 중 오류 (${i + 1}/${retries}):`, error);
    }
  }
};

// 단순화된 타입 정의
export interface SimpleImageHistory {
  id: string;
  conversationId: string;
  prompt: string;
  imageUrls: string[];
  primaryImageUrl: string;
  style: string;
  size: string;
  parentImageId?: string;
  evolutionType?: string;
  canvasId?: string;
  requestCanvasId?: string;
  canvasVersion?: number;
  editMode?: string;
  referenceImageId?: string;
  isSelected: boolean;
  isEvolution: boolean;
  safetyScore: number;
  fileSizeBytes: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface ImageHistoryCreateRequest {
  conversationId: string;
  prompt: string;
  imageUrls: string[];
  style?: string;
  size?: string;
  parentImageId?: string;
  evolutionType?: string;
}

export interface ImageEvolutionRequest {
  conversationId: string;
  selectedImageId: string;
  newPrompt: string;
  evolutionType: 'variation' | 'modification' | 'extension' | 'based_on' | 'reference_edit' | 'gemini_edit';
  // Canvas 특수 파라미터들
  source?: string;
  workflowMode?: string;
  canvasId?: string;
  referenceImageId?: string;
  editModeType?: string;
  optimizePrompt?: boolean;
  style?: string;
  size?: string;
}

interface SimpleImageHistoryState {
  // conversationId별 이미지 히스토리 맵
  historyMap: Map<string, SimpleImageHistory[]>;
  
  // 로딩 상태
  loadingMap: Map<string, boolean>;
  
  // 에러 상태
  error: string | null;
  
  // 현재 선택된 이미지 ID (conversationId별)
  selectedImageMap: Map<string, string>;
  
  // 마지막 업데이트 시간 (강제 새로고침용)
  lastUpdated?: number;
  
  // Actions
  getConversationImages: (conversationId: string) => SimpleImageHistory[];
  getSelectedImage: (conversationId: string) => SimpleImageHistory | null;
  setSelectedImage: (conversationId: string, imageId: string) => void;
  
  // 새 이미지 생성
  generateImage: (request: ImageHistoryCreateRequest) => Promise<SimpleImageHistory>;
  
  // 선택된 이미지 기반 진화 이미지 생성
  evolveImage: (request: ImageEvolutionRequest) => Promise<SimpleImageHistory>;
  
  // 이미지 삭제
  deleteImage: (conversationId: string, imageId: string) => Promise<void>;
  
  // 히스토리 로딩
  loadHistory: (conversationId: string, forceReload?: boolean) => Promise<void>;
  
  // 상태 조회
  isLoading: (conversationId: string) => boolean;
  hasImages: (conversationId: string) => boolean;
  getImageCount: (conversationId: string) => number;
  
  // 초기화
  reset: () => void;
  clearConversationHistory: (conversationId: string) => void;
}

export const useSimpleImageHistoryStore = create<SimpleImageHistoryState>((set, get) => ({
  historyMap: new Map(),
  loadingMap: new Map(),
  error: null,
  selectedImageMap: new Map(),
  
  getConversationImages: (conversationId: string) => {
    return get().historyMap.get(conversationId) || [];
  },
  
  getSelectedImage: (conversationId: string) => {
    const selectedId = get().selectedImageMap.get(conversationId);
    if (!selectedId) return null;
    
    const images = get().getConversationImages(conversationId);
    return images.find(img => img.id === selectedId) || null;
  },
  
  setSelectedImage: (conversationId: string, imageId: string) => {
    set(state => ({
      selectedImageMap: new Map(state.selectedImageMap).set(conversationId, imageId)
    }));
  },
  
  generateImage: async (request: ImageHistoryCreateRequest): Promise<SimpleImageHistory> => {
    const { conversationId } = request;
    
    // 로딩 시작
    set(state => ({
      loadingMap: new Map(state.loadingMap).set(conversationId, true),
      error: null
    }));
    
    try {
      // API 호출
      const response = await fetch('/api/v1/images/history/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_id: request.conversationId,
          prompt: request.prompt,
          style: request.style || 'realistic',
          size: request.size || '1024x1024',
          parent_image_id: request.parentImageId,
          evolution_type: request.evolutionType
        })
      });
      
      if (!response.ok) {
        throw new Error(`이미지 생성 실패: ${response.statusText}`);
      }
      
      const newImage: SimpleImageHistory = await response.json();
      
      // Store에 추가
      set(state => {
        const newHistoryMap = new Map(state.historyMap);
        const existingImages = newHistoryMap.get(conversationId) || [];
        newHistoryMap.set(conversationId, [newImage, ...existingImages]);
        
        const newSelectedMap = new Map(state.selectedImageMap);
        newSelectedMap.set(conversationId, newImage.id);
        
        return {
          historyMap: newHistoryMap,
          selectedImageMap: newSelectedMap
        };
      });
      
      return newImage;
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류';
      set({ error: errorMessage });
      throw error;
    } finally {
      // 로딩 종료
      set(state => ({
        loadingMap: new Map(state.loadingMap).set(conversationId, false)
      }));
    }
  },
  
  evolveImage: async (request: ImageEvolutionRequest): Promise<SimpleImageHistory> => {
    const { conversationId } = request;
    
    // Canvas 요청인지 감지 (Gemini 편집 포함)
    const isCanvasEdit = request.evolutionType === 'gemini_edit' || 
                        (request.source === 'canvas' && (request.workflowMode === 'edit' || request.workflowMode === 'gemini_edit'));
    
    console.log('🔄 이미지 진화 시작:', { 
      conversationId, 
      selectedImageId: request.selectedImageId, 
      newPrompt: request.newPrompt,
      isCanvasEdit,
      source: request.source,
      workflowMode: request.workflowMode
    });
    
    // 로딩 시작
    set(state => ({
      loadingMap: new Map(state.loadingMap).set(conversationId, true),
      error: null
    }));
    
    try {
      let response;
      
      if (isCanvasEdit) {
        // Canvas 편집: /edit 엔드포인트 사용 (Gemini 2.5 Flash 기반)
        console.log('✏️ Canvas 편집 모드 - /edit 엔드포인트 호출');
        response = await fetch('/api/v1/images/history/edit', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            reference_image_id: request.selectedImageId,
            prompt: request.newPrompt,
            optimize_prompt: request.optimizePrompt || false
          })
        });
      } else {
        // 일반 진화: /evolve 엔드포인트 사용
        console.log('🔄 일반 진화 모드 - /evolve 엔드포인트 호출');
        response = await fetch('/api/v1/images/history/evolve', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            parent_image_id: request.selectedImageId,
            new_prompt: request.newPrompt,
            evolution_type: request.evolutionType
          })
        });
      }
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ evolve API 응답 오류:', { status: response.status, statusText: response.statusText, body: errorText });
        throw new Error(`이미지 진화 생성 실패: ${response.status} ${response.statusText}`);
      }
      
      const newImage: SimpleImageHistory = await response.json();
      console.log('✅ 진화 이미지 생성 성공:', newImage);
      
      // 백엔드 응답이 snake_case이므로 primaryImageUrl 매핑 보정
      const primaryImageUrl = newImage.primaryImageUrl || (newImage as any).primary_image_url;
      console.log('🔍 이미지 접근성 확인 시작:', primaryImageUrl);
      
      // primaryImageUrl이 없으면 image_urls 배열에서 첫 번째 사용
      const finalImageUrl = primaryImageUrl || (newImage.imageUrls && newImage.imageUrls[0]) || ((newImage as any).image_urls && (newImage as any).image_urls[0]);
      console.log('🔍 최종 이미지 URL:', finalImageUrl);
      
      const isImageAccessible = await waitForImageAvailability(finalImageUrl);
      
      if (isImageAccessible) {
        console.log('✅ 이미지 접근 가능 확인됨, Store 업데이트 진행');
      } else {
        console.warn('⚠️ 이미지 접근 실패했지만 Store 업데이트는 진행 (UI에서 재시도 가능)');
      }
      
      // Store에 추가 (primaryImageUrl 보정 포함)
      set(state => {
        // primaryImageUrl 보정된 이미지 객체 생성
        const correctedImage = {
          ...newImage,
          primaryImageUrl: finalImageUrl  // 보정된 URL 사용
        };
        
        const newHistoryMap = new Map(state.historyMap);
        const existingImages = newHistoryMap.get(conversationId) || [];
        const updatedImages = [correctedImage, ...existingImages];
        newHistoryMap.set(conversationId, updatedImages);
        
        const newSelectedMap = new Map(state.selectedImageMap);
        newSelectedMap.set(conversationId, newImage.id);
        
        console.log('📊 Store 업데이트 완료:', {
          conversationId,
          newImageId: newImage.id,
          totalImages: updatedImages.length,
          selectedImageId: newImage.id,
          storeUpdated: true,
          imageAccessible: isImageAccessible
        });
        
        return {
          historyMap: newHistoryMap,
          selectedImageMap: newSelectedMap,
          // 강제 새로고침을 위한 timestamp 업데이트
          lastUpdated: Date.now()
        };
      });
      
      // 강화된 이미진 새로고침 메커니즘
      try {
        console.log('🔄 강화된 이미진 새로고침 시작');
        
        // 비동기 강제 새로고침 실행
        await forceImageRefresh(finalImageUrl);
        
        // Canvas 컴포넌트 강제 리렌더링을 위한 커스텀 이벤트 발생
        window.dispatchEvent(new CustomEvent('image-updated', { 
          detail: { 
            conversationId, 
            imageId: newImage.id, 
            imageUrl: finalImageUrl,
            timestamp: Date.now(),
            source: 'evolve-image'
          } 
        }));
        
        // 지연된 추가 새로고침 (이미진가 늤늘게 로드되는 경우 대비)
        setTimeout(() => {
          console.log('🔄 지연된 추가 새로고침 실행');
          forceImageRefresh(finalImageUrl, 2);
        }, 2000);
        
      } catch (error) {
        console.warn('⚠️ 이미짇 새로고침 중 오류:', error);
      }
      
      // 채팅 히스토리 실시간 업데이트 알림 
      try {
        console.log('🔄 진화 완료! 채팅 히스토리에 자동 기록됩니다');
        
        // 사용자에게 채팅 확인 알림 (간단한 방법)
        setTimeout(() => {
          console.log('✅ 채팅 탭을 확인하시면 진화 내용이 기록되어 있습니다!');
        }, 1000);
        
      } catch (error) {
        console.warn('⚠️ 알림 처리 중 오류:', error);
      }
      
      return newImage;
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류';
      console.error('❌ Canvas 이미지 진화 실패:', errorMessage);
      set({ error: errorMessage });
      throw error;
    } finally {
      // 로딩 종료
      set(state => ({
        loadingMap: new Map(state.loadingMap).set(conversationId, false)
      }));
    }
  },
  
  deleteImage: async (conversationId: string, imageId: string): Promise<void> => {
    try {
      // API 호출
      const response = await fetch(`/api/v1/images/history/${imageId}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error(`이미지 삭제 실패: ${response.statusText}`);
      }
      
      // Store에서 제거
      set(state => {
        const newHistoryMap = new Map(state.historyMap);
        const existingImages = newHistoryMap.get(conversationId) || [];
        const filteredImages = existingImages.filter(img => img.id !== imageId);
        newHistoryMap.set(conversationId, filteredImages);
        
        // 선택된 이미지가 삭제된 경우 선택 해제
        const newSelectedMap = new Map(state.selectedImageMap);
        if (newSelectedMap.get(conversationId) === imageId) {
          if (filteredImages.length > 0) {
            newSelectedMap.set(conversationId, filteredImages[0].id);
          } else {
            newSelectedMap.delete(conversationId);
          }
        }
        
        return {
          historyMap: newHistoryMap,
          selectedImageMap: newSelectedMap
        };
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류';
      set({ error: errorMessage });
      throw error;
    }
  },
  
  loadHistory: async (conversationId: string, forceReload = false): Promise<void> => {
    const { historyMap, loadingMap } = get();
    
    // 이미 로딩 중이면 건너뛰기
    if (loadingMap.get(conversationId)) {
      return;
    }
    
    // 이미 데이터가 있고 강제 재로딩이 아니면 건너뛰기
    if (!forceReload && historyMap.has(conversationId)) {
      return;
    }
    
    // 로딩 시작
    set(state => ({
      loadingMap: new Map(state.loadingMap).set(conversationId, true),
      error: null
    }));
    
    try {
      // API 호출
      const response = await fetch(`/api/v1/images/history/${conversationId}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          // 히스토리가 없는 경우 빈 배열로 설정
          set(state => ({
            historyMap: new Map(state.historyMap).set(conversationId, [])
          }));
          return;
        }
        throw new Error(`히스토리 로딩 실패: ${response.statusText}`);
      }
      
      const data = await response.json();
      const images: SimpleImageHistory[] = (data.images || []).map((apiImage: any) => ({
        id: apiImage.id,
        conversationId: apiImage.conversation_id,
        prompt: apiImage.prompt,
        imageUrls: apiImage.image_urls,
        primaryImageUrl: apiImage.primary_image_url,
        style: apiImage.style,
        size: apiImage.size,
        parentImageId: apiImage.parent_image_id,
        evolutionType: apiImage.evolution_type,
        canvasId: apiImage.canvas_id,
        requestCanvasId: apiImage.request_canvas_id,
        canvasVersion: apiImage.canvas_version,
        editMode: apiImage.edit_mode,
        referenceImageId: apiImage.reference_image_id,
        isSelected: apiImage.is_selected,
        isEvolution: apiImage.is_evolution,
        safetyScore: apiImage.safety_score,
        fileSizeBytes: apiImage.file_size_bytes,
        createdAt: new Date(apiImage.created_at),
        updatedAt: new Date(apiImage.created_at) // API에서 updated_at이 없다면 created_at 사용
      }));
      
      // Store에 저장
      set(state => {
        const newHistoryMap = new Map(state.historyMap);
        newHistoryMap.set(conversationId, images);
        
        // 선택된 이미지 설정 (가장 최근 생성된 이미지 또는 is_selected=true인 이미지)
        const newSelectedMap = new Map(state.selectedImageMap);
        const selectedImage = images.find(img => img.isSelected) || images[0];
        if (selectedImage) {
          newSelectedMap.set(conversationId, selectedImage.id);
        }
        
        return {
          historyMap: newHistoryMap,
          selectedImageMap: newSelectedMap
        };
      });
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '알 수 없는 오류';
      set({ error: errorMessage });
      console.error('❌ 이미지 히스토리 로딩 실패:', error);
    } finally {
      // 로딩 종료
      set(state => ({
        loadingMap: new Map(state.loadingMap).set(conversationId, false)
      }));
    }
  },
  
  isLoading: (conversationId: string) => {
    return get().loadingMap.get(conversationId) || false;
  },
  
  hasImages: (conversationId: string) => {
    const images = get().getConversationImages(conversationId);
    return images.length > 0;
  },
  
  getImageCount: (conversationId: string) => {
    return get().getConversationImages(conversationId).length;
  },
  
  reset: () => {
    set({
      historyMap: new Map(),
      loadingMap: new Map(),
      error: null,
      selectedImageMap: new Map()
    });
  },
  
  clearConversationHistory: (conversationId: string) => {
    set(state => {
      const newHistoryMap = new Map(state.historyMap);
      newHistoryMap.delete(conversationId);
      
      const newSelectedMap = new Map(state.selectedImageMap);
      newSelectedMap.delete(conversationId);
      
      return {
        historyMap: newHistoryMap,
        selectedImageMap: newSelectedMap
      };
    });
  }
}));

export default useSimpleImageHistoryStore;