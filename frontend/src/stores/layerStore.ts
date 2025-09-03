/**
 * Canvas v4.0 다중 이미지 편집 레이어 시스템 상태 관리
 * Zustand 기반 레이어 스토어
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import type {
  Layer,
  LayerContainer,
  LayerType,
  BlendMode,
  LayerTransform,
  BoundingBox,
  EditTool,
  EditOperation,
  LayerCache,
  RenderSettings,
  LayerEvent,
  LayerEventListener
} from '../types/layer';

// ============= 상태 인터페이스 =============

interface LayerState {
  // 레이어 컨테이너 관리
  containers: Record<string, LayerContainer>;
  activeContainerId: string | null;
  
  // 현재 활성 상태
  selectedLayerIds: string[];
  activeEditTool: EditTool;
  clipboard: Layer[];
  
  // 편집 히스토리 (Undo/Redo)
  editHistory: EditOperation[];
  historyIndex: number;
  maxHistorySize: number;
  
  // 캐시 관리
  layerCaches: Record<string, LayerCache>;
  cacheStats: {
    totalSize: number;
    hitRate: number;
    lastCleanup: string;
  };
  
  // 렌더링 상태
  renderSettings: RenderSettings;
  renderQueue: string[]; // 렌더링 대기 중인 레이어 ID들
  isRendering: boolean;
  
  // 이벤트 시스템
  eventListeners: Map<string, LayerEventListener[]>;
  
  // 성능 모니터링
  performanceMetrics: {
    renderTime: number;
    layerCount: number;
    memoryUsage: number;
    lastUpdate: string;
  };
  
  // 동기화 상태
  syncStatus: Record<string, 'idle' | 'syncing' | 'error'>;
  lastSyncTime: Record<string, string>;
}

interface LayerActions {
  // ============= 컨테이너 관리 =============
  
  /** 새 레이어 컨테이너 생성 */
  createContainer: (canvasId: string, conversationId?: string, name?: string) => string;
  
  /** 컨테이너 로드 */
  loadContainer: (containerId: string) => Promise<LayerContainer | null>;
  
  /** 컨테이너 저장 */
  saveContainer: (containerId: string) => Promise<boolean>;
  
  /** 컨테이너 삭제 */
  deleteContainer: (containerId: string) => Promise<boolean>;
  
  /** 활성 컨테이너 설정 */
  setActiveContainer: (containerId: string) => void;
  
  /** 컨테이너 복제 */
  cloneContainer: (containerId: string, newName: string) => Promise<string>;
  
  // ============= 레이어 관리 =============
  
  /** 새 레이어 추가 */
  addLayer: (
    containerId: string,
    type: LayerType,
    content: any,
    parentId?: string,
    position?: { x: number; y: number }
  ) => string;
  
  /** 레이어 업데이트 */
  updateLayer: (containerId: string, layerId: string, updates: Partial<Layer>) => void;
  
  /** 레이어 삭제 */
  deleteLayer: (containerId: string, layerId: string) => void;
  
  /** 레이어 복제 */
  cloneLayer: (containerId: string, layerId: string, newName?: string) => string;
  
  /** 레이어 순서 변경 */
  reorderLayer: (containerId: string, layerId: string, newIndex: number) => void;
  
  /** 레이어 그룹화 */
  groupLayers: (containerId: string, layerIds: string[], groupName: string) => string;
  
  /** 그룹 해제 */
  ungroupLayers: (containerId: string, groupId: string) => void;
  
  // ============= 선택 및 변형 =============
  
  /** 레이어 선택 */
  selectLayers: (layerIds: string[], addToSelection?: boolean) => void;
  
  /** 모든 선택 해제 */
  clearSelection: () => void;
  
  /** 레이어 변형 적용 */
  transformLayer: (containerId: string, layerId: string, transform: Partial<LayerTransform>) => void;
  
  /** 다중 레이어 변형 */
  transformMultipleLayers: (containerId: string, layerIds: string[], transform: Partial<LayerTransform>) => void;
  
  /** 경계 박스 업데이트 */
  updateBoundingBox: (containerId: string, layerId: string, box: BoundingBox) => void;
  
  // ============= 편집 도구 =============
  
  /** 활성 편집 도구 설정 */
  setEditTool: (tool: EditTool) => void;
  
  /** 레이어 잘라내기 */
  cutLayers: (layerIds: string[]) => void;
  
  /** 레이어 복사 */
  copyLayers: (layerIds: string[]) => void;
  
  /** 레이어 붙여넣기 */
  pasteLayers: (containerId: string, position?: { x: number; y: number }) => string[];
  
  /** 레이어 병합 */
  mergeLayers: (containerId: string, layerIds: string[]) => string;
  
  // ============= 히스토리 관리 (Undo/Redo) =============
  
  /** 편집 작업 기록 */
  recordOperation: (operation: Omit<EditOperation, 'id' | 'timestamp'>) => void;
  
  /** 실행 취소 */
  undo: () => boolean;
  
  /** 다시 실행 */
  redo: () => boolean;
  
  /** 히스토리 정리 */
  clearHistory: () => void;
  
  /** 히스토리 크기 제한 적용 */
  trimHistory: () => void;
  
  // ============= 캐시 관리 =============
  
  /** 레이어 캐시 생성 */
  createLayerCache: (layerId: string, cacheData: Partial<LayerCache>) => void;
  
  /** 캐시 무효화 */
  invalidateCache: (layerId: string) => void;
  
  /** 캐시 정리 */
  cleanupCache: () => void;
  
  /** 캐시 통계 업데이트 */
  updateCacheStats: () => void;
  
  // ============= 렌더링 관리 =============
  
  /** 렌더링 설정 업데이트 */
  updateRenderSettings: (settings: Partial<RenderSettings>) => void;
  
  /** 레이어 렌더링 요청 */
  requestRender: (layerIds: string[]) => void;
  
  /** 렌더링 큐 처리 */
  processRenderQueue: () => Promise<void>;
  
  /** 렌더링 상태 설정 */
  setRenderingState: (isRendering: boolean) => void;
  
  // ============= 이벤트 시스템 =============
  
  /** 이벤트 리스너 등록 */
  addEventListener: (eventType: string, listener: LayerEventListener) => void;
  
  /** 이벤트 리스너 제거 */
  removeEventListener: (eventType: string, listener: LayerEventListener) => void;
  
  /** 이벤트 발생 */
  emitEvent: (event: LayerEvent) => void;
  
  // ============= Canvas v4.0 호환성 =============
  
  /** Canvas v4.0 아이템을 레이어로 변환 */
  convertCanvasItemToLayers: (canvasItem: any, containerId: string) => string[];
  
  /** 레이어들을 Canvas v4.0 아이템으로 변환 */
  convertLayersToCanvasItem: (containerId: string, layerIds: string[], itemType: string) => any;
  
  /** ImageGenerator와 동기화 */
  syncWithImageGenerator: (containerId: string, imageData: any) => void;
  
  /** ImageVersionGallery와 동기화 */
  syncWithVersionGallery: (containerId: string, versionData: any) => void;
  
  // ============= 실시간 동기화 =============
  
  /** 서버와 동기화 */
  syncWithServer: (containerId: string) => Promise<boolean>;
  
  /** 실시간 협업 데이터 적용 */
  applyRealtimeUpdate: (containerId: string, update: any) => void;
  
  /** 동기화 상태 설정 */
  setSyncStatus: (containerId: string, status: 'idle' | 'syncing' | 'error') => void;
  
  // ============= 성능 최적화 =============
  
  /** 성능 메트릭 업데이트 */
  updatePerformanceMetrics: (metrics: Partial<LayerState['performanceMetrics']>) => void;
  
  /** 메모리 최적화 */
  optimizeMemory: () => void;
  
  /** 백그라운드 정리 작업 */
  runMaintenanceTasks: () => Promise<void>;
}

type LayerStore = LayerState & LayerActions;

// ============= 기본값 정의 =============

const DEFAULT_RENDER_SETTINGS: RenderSettings = {
  quality: 'normal',
  useWebGL: true,
  enableCache: true,
  maxCacheSize: 100 * 1024 * 1024, // 100MB
  enableAntiAlias: true,
  enableBilinearFiltering: true,
  maxTextureSize: 4096
};

const DEFAULT_PERFORMANCE_METRICS = {
  renderTime: 0,
  layerCount: 0,
  memoryUsage: 0,
  lastUpdate: new Date().toISOString()
};

const DEFAULT_CACHE_STATS = {
  totalSize: 0,
  hitRate: 0.0,
  lastCleanup: new Date().toISOString()
};

// ============= 유틸리티 함수 =============

/** UUID 생성 */
const generateId = (): string => {
  return crypto.randomUUID();
};

/** 레이어 템플릿 생성 */
const createLayerTemplate = (type: LayerType, content: any, position?: { x: number; y: number }): Omit<Layer, 'id'> => {
  const baseLayer = {
    name: `새로운 ${type} 레이어`,
    type,
    parentId: null,
    childrenIds: [],
    zIndex: 0,
    transform: {
      x: position?.x || 0,
      y: position?.y || 0,
      scaleX: 1,
      scaleY: 1,
      rotation: 0,
      skewX: 0,
      skewY: 0,
      offsetX: 0,
      offsetY: 0
    },
    boundingBox: {
      x: position?.x || 0,
      y: position?.y || 0,
      width: 100,
      height: 100
    },
    state: {
      visible: true,
      locked: false,
      selected: false,
      collapsed: false,
      opacity: 1.0,
      blendMode: BlendMode.NORMAL
    },
    metadata: {
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      source: 'user' as const,
      tags: []
    },
    content
  };

  return baseLayer as any; // 타입 단언으로 임시 해결
};

// ============= Zustand 스토어 생성 =============

export const useLayerStore = create<LayerStore>()(
  devtools(
    subscribeWithSelector(
      immer((set, get) => ({
        // ===== 초기 상태 =====
        containers: {},
        activeContainerId: null,
        selectedLayerIds: [],
        activeEditTool: EditTool.SELECT,
        clipboard: [],
        editHistory: [],
        historyIndex: -1,
        maxHistorySize: 100,
        layerCaches: {},
        cacheStats: DEFAULT_CACHE_STATS,
        renderSettings: DEFAULT_RENDER_SETTINGS,
        renderQueue: [],
        isRendering: false,
        eventListeners: new Map(),
        performanceMetrics: DEFAULT_PERFORMANCE_METRICS,
        syncStatus: {},
        lastSyncTime: {},

        // ===== 컨테이너 관리 액션 =====
        
        createContainer: (canvasId: string, conversationId?: string, name?: string): string => {
          const containerId = generateId();
          const container: LayerContainer = {
            id: containerId,
            canvasId,
            conversationId,
            layers: {},
            layerOrder: [],
            selectedLayerIds: [],
            canvas: {
              width: 1920,
              height: 1080,
              backgroundColor: '#ffffff',
              dpi: 72
            },
            viewport: {
              zoom: 1.0,
              panX: 0.0,
              panY: 0.0,
              rotation: 0.0
            },
            metadata: {
              name: name || `새 캔버스 ${Date.now()}`,
              description: undefined,
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              version: 1
            }
          };

          set((state) => {
            state.containers[containerId] = container;
            if (!state.activeContainerId) {
              state.activeContainerId = containerId;
            }
          });

          get().emitEvent({ type: 'container:created', containerId });
          return containerId;
        },

        loadContainer: async (containerId: string): Promise<LayerContainer | null> => {
          // TODO: 서버에서 컨테이너 데이터 로드
          // 현재는 로컬 상태에서만 반환
          const state = get();
          return state.containers[containerId] || null;
        },

        saveContainer: async (containerId: string): Promise<boolean> => {
          // TODO: 서버에 컨테이너 데이터 저장
          get().emitEvent({ type: 'container:saved', containerId });
          return true;
        },

        deleteContainer: async (containerId: string): Promise<boolean> => {
          set((state) => {
            delete state.containers[containerId];
            if (state.activeContainerId === containerId) {
              const remainingIds = Object.keys(state.containers);
              state.activeContainerId = remainingIds.length > 0 ? remainingIds[0] : null;
            }
          });
          return true;
        },

        setActiveContainer: (containerId: string): void => {
          set((state) => {
            if (state.containers[containerId]) {
              state.activeContainerId = containerId;
              state.selectedLayerIds = state.containers[containerId].selectedLayerIds;
            }
          });
        },

        cloneContainer: async (containerId: string, newName: string): Promise<string> => {
          const state = get();
          const originalContainer = state.containers[containerId];
          if (!originalContainer) {
            throw new Error('Container not found');
          }

          const newContainerId = generateId();
          const clonedContainer: LayerContainer = {
            ...originalContainer,
            id: newContainerId,
            metadata: {
              ...originalContainer.metadata,
              name: newName,
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              version: 1
            }
          };

          set((state) => {
            state.containers[newContainerId] = clonedContainer;
          });

          return newContainerId;
        },

        // ===== 레이어 관리 액션 =====
        
        addLayer: (
          containerId: string,
          type: LayerType,
          content: any,
          parentId?: string,
          position?: { x: number; y: number }
        ): string => {
          const layerId = generateId();
          const layer = {
            id: layerId,
            ...createLayerTemplate(type, content, position)
          } as Layer;

          set((state) => {
            const container = state.containers[containerId];
            if (container) {
              container.layers[layerId] = layer;
              container.layerOrder.push(layerId);
              
              if (parentId && container.layers[parentId]) {
                layer.parentId = parentId;
                container.layers[parentId].childrenIds.push(layerId);
              }
              
              container.metadata.updatedAt = new Date().toISOString();
              container.metadata.version += 1;
            }
          });

          get().emitEvent({ type: 'layer:created', layerId, layer });
          return layerId;
        },

        updateLayer: (containerId: string, layerId: string, updates: Partial<Layer>): void => {
          set((state) => {
            const container = state.containers[containerId];
            if (container && container.layers[layerId]) {
              Object.assign(container.layers[layerId], updates);
              container.layers[layerId].metadata.updatedAt = new Date().toISOString();
              container.metadata.updatedAt = new Date().toISOString();
              container.metadata.version += 1;
            }
          });

          get().emitEvent({ type: 'layer:updated', layerId, changes: updates });
        },

        deleteLayer: (containerId: string, layerId: string): void => {
          set((state) => {
            const container = state.containers[containerId];
            if (container && container.layers[layerId]) {
              const layer = container.layers[layerId];
              
              // 부모-자식 관계 정리
              if (layer.parentId && container.layers[layer.parentId]) {
                const parentChildren = container.layers[layer.parentId].childrenIds;
                const index = parentChildren.indexOf(layerId);
                if (index > -1) {
                  parentChildren.splice(index, 1);
                }
              }
              
              // 자식 레이어들 처리 (재귀적 삭제 또는 부모 재할당)
              layer.childrenIds.forEach(childId => {
                if (container.layers[childId]) {
                  container.layers[childId].parentId = layer.parentId;
                }
              });
              
              // 레이어 삭제
              delete container.layers[layerId];
              
              // 순서 목록에서 제거
              const orderIndex = container.layerOrder.indexOf(layerId);
              if (orderIndex > -1) {
                container.layerOrder.splice(orderIndex, 1);
              }
              
              // 선택 목록에서 제거
              const selectedIndex = container.selectedLayerIds.indexOf(layerId);
              if (selectedIndex > -1) {
                container.selectedLayerIds.splice(selectedIndex, 1);
              }
              
              container.metadata.updatedAt = new Date().toISOString();
              container.metadata.version += 1;
            }
          });

          get().emitEvent({ type: 'layer:deleted', layerId });
        },

        cloneLayer: (containerId: string, layerId: string, newName?: string): string => {
          const state = get();
          const container = state.containers[containerId];
          const originalLayer = container?.layers[layerId];
          
          if (!originalLayer) {
            throw new Error('Layer not found');
          }

          const newLayerId = generateId();
          const clonedLayer: Layer = {
            ...originalLayer,
            id: newLayerId,
            name: newName || `${originalLayer.name} 복사본`,
            parentId: originalLayer.parentId,
            childrenIds: [], // 자식은 복사하지 않음
            metadata: {
              ...originalLayer.metadata,
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString()
            }
          };

          // 위치를 약간 이동
          clonedLayer.transform.x += 20;
          clonedLayer.transform.y += 20;
          clonedLayer.boundingBox.x += 20;
          clonedLayer.boundingBox.y += 20;

          set((state) => {
            const container = state.containers[containerId];
            if (container) {
              container.layers[newLayerId] = clonedLayer;
              container.layerOrder.push(newLayerId);
              
              if (clonedLayer.parentId && container.layers[clonedLayer.parentId]) {
                container.layers[clonedLayer.parentId].childrenIds.push(newLayerId);
              }
              
              container.metadata.updatedAt = new Date().toISOString();
              container.metadata.version += 1;
            }
          });

          get().emitEvent({ type: 'layer:created', layerId: newLayerId, layer: clonedLayer });
          return newLayerId;
        },

        reorderLayer: (containerId: string, layerId: string, newIndex: number): void => {
          set((state) => {
            const container = state.containers[containerId];
            if (container) {
              const oldIndex = container.layerOrder.indexOf(layerId);
              if (oldIndex > -1) {
                container.layerOrder.splice(oldIndex, 1);
                container.layerOrder.splice(newIndex, 0, layerId);
                
                // zIndex 업데이트
                container.layerOrder.forEach((id, index) => {
                  if (container.layers[id]) {
                    container.layers[id].zIndex = index;
                  }
                });
                
                container.metadata.updatedAt = new Date().toISOString();
                container.metadata.version += 1;
                
                get().emitEvent({ type: 'layer:reordered', oldIndex, newIndex });
              }
            }
          });
        },

        // ===== 추가 액션들 (간소화된 구현) =====
        // 실제 구현에서는 각 액션을 완전히 구현해야 함

        selectLayers: (layerIds: string[], addToSelection = false): void => {
          set((state) => {
            if (!addToSelection) {
              state.selectedLayerIds = [...layerIds];
            } else {
              const newSelection = new Set([...state.selectedLayerIds, ...layerIds]);
              state.selectedLayerIds = Array.from(newSelection);
            }
            
            // 활성 컨테이너의 선택 상태도 업데이트
            if (state.activeContainerId && state.containers[state.activeContainerId]) {
              state.containers[state.activeContainerId].selectedLayerIds = [...state.selectedLayerIds];
            }
          });
          
          get().emitEvent({ type: 'layer:selected', layerIds });
        },

        clearSelection: (): void => {
          get().selectLayers([]);
        },

        setEditTool: (tool: EditTool): void => {
          set((state) => {
            state.activeEditTool = tool;
          });
        },

        // 나머지 액션들은 실제 구현 시 추가...
        // 여기서는 기본 구조만 제공

        groupLayers: () => '',
        ungroupLayers: () => {},
        transformLayer: () => {},
        transformMultipleLayers: () => {},
        updateBoundingBox: () => {},
        cutLayers: () => {},
        copyLayers: () => {},
        pasteLayers: () => [],
        mergeLayers: () => '',
        recordOperation: () => {},
        undo: () => false,
        redo: () => false,
        clearHistory: () => {},
        trimHistory: () => {},
        createLayerCache: () => {},
        invalidateCache: () => {},
        cleanupCache: () => {},
        updateCacheStats: () => {},
        updateRenderSettings: () => {},
        requestRender: () => {},
        processRenderQueue: async () => {},
        setRenderingState: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        emitEvent: (event: LayerEvent) => {
          const listeners = get().eventListeners.get(event.type) || [];
          listeners.forEach(listener => listener(event));
        },
        convertCanvasItemToLayers: () => [],
        convertLayersToCanvasItem: () => ({}),
        syncWithImageGenerator: () => {},
        syncWithVersionGallery: () => {},
        syncWithServer: async () => false,
        applyRealtimeUpdate: () => {},
        setSyncStatus: () => {},
        updatePerformanceMetrics: () => {},
        optimizeMemory: () => {},
        runMaintenanceTasks: async () => {},
      }))
    ),
    { name: 'layer-store' }
  )
);

// ============= 편의 훅들 =============

/** 활성 컨테이너 훅 */
export const useActiveContainer = () => {
  return useLayerStore((state) => {
    if (state.activeContainerId) {
      return state.containers[state.activeContainerId];
    }
    return null;
  });
};

/** 선택된 레이어들 훅 */
export const useSelectedLayers = () => {
  return useLayerStore((state) => {
    const container = state.activeContainerId ? state.containers[state.activeContainerId] : null;
    if (!container) return [];
    
    return state.selectedLayerIds.map(id => container.layers[id]).filter(Boolean);
  });
};

/** 레이어 이벤트 훅 */
export const useLayerEvents = (eventType: string, listener: LayerEventListener) => {
  const { addEventListener, removeEventListener } = useLayerStore();
  
  React.useEffect(() => {
    addEventListener(eventType, listener);
    return () => removeEventListener(eventType, listener);
  }, [eventType, listener, addEventListener, removeEventListener]);
};

export default useLayerStore;