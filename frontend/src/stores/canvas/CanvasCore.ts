/**
 * Canvas Core v5.0 - 기본 상태 및 타입 정의
 * UnifiedCanvasStore 아키텍처의 핵심 모듈
 */

import { v4 as uuidv4 } from 'uuid';
import type { CanvasItem, CanvasToolType, TextNote, ImageGeneration, MindMapNode } from '../../types/canvas';

// ======= 타입 정의 =======

/** 동기화 작업 타입 */
export type SyncTask = {
  id: string;
  conversationId: string;
  type: 'canvas_to_session' | 'session_to_canvas' | 'version_select';
  data: any;
  timestamp: number;
};

/** Canvas 상태 인터페이스 */
export interface CanvasState {
  // 기본 상태
  items: CanvasItem[];
  activeItemId: string | null;
  isCanvasOpen: boolean;
  lastConversationId: string | null;
  
  // 영구 보존 시스템
  isPersistenceEnabled: boolean;
  autoSaveEnabled: boolean;
  
  // 동기화 시스템
  syncQueue: SyncTask[];
  isProcessingSyncQueue: boolean;
  syncInProgress: Record<string, boolean>;
  processedCanvasItems: Record<string, Set<string>>;
  debounceTimers: Record<string, NodeJS.Timeout>;
  
  // 메서드 시그니처 (실제 구현은 각 모듈에서)
  getOrCreateCanvasV4: (conversationId: string, type: CanvasToolType, canvasData?: any, requestId?: string) => Promise<string>;
  getOrCreateCanvas: (conversationId: string, type: CanvasToolType, canvasData?: any) => Promise<string>;
  activateConversationCanvas: (conversationId: string, type: CanvasToolType) => string;
  updateConversationCanvas: (conversationId: string, type: CanvasToolType, updates: any) => string;
  
  // 아이템 관리
  addItem: (type: CanvasToolType, content: any) => string;
  updateItem: (id: string, updates: Partial<CanvasItem>) => void;
  deleteItem: (id: string) => void;
  clearCanvas: () => void;
  setActiveItem: (id: string | null) => void;
  
  // Canvas 상태 관리
  openWithArtifact: (artifactId: string) => void;
  autoActivateCanvas: (canvasData: any, conversationId?: string) => string;
  closeCanvas: () => void;
  
  // 대화별 Canvas 관리
  loadCanvasForConversation: (conversationId: string) => void;
  saveCanvasToStorage: (conversationId: string) => void;
  deleteConversationCanvas: (conversationId: string) => void;
  getCanvasPreview: (conversationId: string) => string | null;
  
  // 영구 보존 시스템
  createPermanentCanvas: (conversationId: string, type: CanvasToolType, canvasData?: any) => Promise<string>;
  loadPermanentCanvas: (canvasId: string) => Promise<CanvasItem | null>;
  deletePermanentCanvas: (canvasId: string) => Promise<boolean>;
  enablePersistence: () => void;
  disablePersistence: () => void;
  
  // 동기화 시스템
  enqueueSyncTask: (task: SyncTask) => void;
  processSyncQueue: () => Promise<void>;
  clearSyncQueue: () => void;
  syncCanvasWithImageSession: (conversationId: string) => Promise<void>;
  selectImageVersion: (conversationId: string, sessionId: string, versionIndex: number) => void;
}

// ======= 유틸리티 함수 =======

/** UUID 충돌 방지 고유 ID 생성 */
export function generateUniqueCanvasId(existingItems: CanvasItem[]): string {
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

/** 백엔드 크기 포맷 → 프론트엔드 SIZE_OPTIONS 포맷 변환 */
export function convertBackendSizeToFrontend(backendSize: string): string {
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

/** Canvas 아이템 유효성 검증 */
export function validateCanvasItem(item: Partial<CanvasItem>): boolean {
  if (!item.id || !item.type || !item.content) {
    return false;
  }
  
  // 타입별 추가 검증
  switch (item.type) {
    case 'text':
      return typeof item.content.text === 'string';
    case 'image':
      return Array.isArray(item.content.images) && item.content.images.length > 0;
    case 'mindmap':
      return Array.isArray(item.content.nodes);
    default:
      return true;
  }
}

/** Canvas 데이터 해시 생성 (중복 방지용) */
export function generateCanvasDataHash(canvasData: any): string {
  const normalizedData = {
    type: canvasData.type || 'unknown',
    content: typeof canvasData.content === 'string' 
      ? canvasData.content.slice(0, 100) 
      : JSON.stringify(canvasData.content).slice(0, 100),
    timestamp: Math.floor(Date.now() / (5 * 60 * 1000)) // 5분 단위 그룹화
  };
  
  return btoa(JSON.stringify(normalizedData))
    .replace(/[+/=]/g, '')
    .slice(0, 16);
}

/** 디바운스 함수 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(null, args), delay);
  };
}

// ======= 상수 정의 =======

/** 기본 설정값 */
export const CANVAS_DEFAULTS = {
  AUTO_SAVE_DELAY: 2000, // 2초
  SYNC_DEBOUNCE_DELAY: 1000, // 1초
  MAX_SYNC_RETRIES: 3,
  STORAGE_KEY_PREFIX: 'canvas_v5_',
  MAX_HISTORY_ITEMS: 100,
} as const;

/** Canvas 아이템 템플릿 */
export const CANVAS_TEMPLATES = {
  text: (content: string = ''): Partial<TextNote> => ({
    text: content,
    fontSize: 14,
    fontFamily: 'Inter, sans-serif',
    color: '#333333',
    backgroundColor: 'transparent',
    textAlign: 'left',
    fontWeight: 'normal',
    fontStyle: 'normal',
    textDecoration: 'none'
  }),
  
  image: (urls: string[] = []): Partial<ImageGeneration> => ({
    prompt: '',
    images: urls,
    style: 'realistic',
    aspectRatio: '1:1',
    size: '1K_1:1'
  }),
  
  mindmap: (rootText: string = '중심 주제'): Partial<{ nodes: MindMapNode[] }> => ({
    nodes: [{
      id: uuidv4(),
      text: rootText,
      x: 0,
      y: 0,
      level: 0,
      parentId: null,
      children: []
    }]
  })
} as const;