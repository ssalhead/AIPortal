/**
 * Canvas v4.0 다중 이미지 편집 레이어 시스템 타입 정의
 * 기존 Canvas v4.0과 호환되는 확장형 레이어 아키텍처
 */

import type { CanvasItem } from './canvas';

// ============= 레이어 시스템 핵심 타입 =============

/** 레이어 타입 열거형 */
export enum LayerType {
  BACKGROUND = 'background',
  IMAGE = 'image',
  TEXT = 'text',
  SHAPE = 'shape',
  EFFECT = 'effect',
  MASK = 'mask',
  GROUP = 'group'
}

/** 블렌드 모드 열거형 */
export enum BlendMode {
  NORMAL = 'normal',
  MULTIPLY = 'multiply',
  SCREEN = 'screen',
  OVERLAY = 'overlay',
  SOFT_LIGHT = 'soft_light',
  HARD_LIGHT = 'hard_light',
  COLOR_DODGE = 'color_dodge',
  COLOR_BURN = 'color_burn',
  DARKEN = 'darken',
  LIGHTEN = 'lighten',
  DIFFERENCE = 'difference',
  EXCLUSION = 'exclusion'
}

/** 변형 정보 인터페이스 */
export interface LayerTransform {
  x: number;
  y: number;
  scaleX: number;
  scaleY: number;
  rotation: number; // degrees
  skewX: number;
  skewY: number;
  offsetX: number;
  offsetY: number;
}

/** 경계 박스 정보 */
export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** 레이어 가시성 및 상태 */
export interface LayerState {
  visible: boolean;
  locked: boolean;
  selected: boolean;
  collapsed?: boolean; // 그룹 레이어용
  opacity: number; // 0.0 ~ 1.0
  blendMode: BlendMode;
}

/** 레이어 스타일 설정 */
export interface LayerStyle {
  filters?: {
    blur?: number;
    brightness?: number;
    contrast?: number;
    saturation?: number;
    hue?: number;
  };
  shadow?: {
    offsetX: number;
    offsetY: number;
    blur: number;
    color: string;
  };
  border?: {
    width: number;
    color: string;
    style: 'solid' | 'dashed' | 'dotted';
  };
}

/** 마스크 정보 */
export interface LayerMask {
  type: 'alpha' | 'clipping' | 'vector';
  data: string | Path2D; // base64 image data or Path2D for vector masks
  inverted: boolean;
  feather: number; // edge softness
}

// ============= 핵심 레이어 인터페이스 =============

/** 베이스 레이어 인터페이스 */
export interface BaseLayer {
  id: string;
  name: string;
  type: LayerType;
  
  // 계층 구조
  parentId: string | null;
  childrenIds: string[];
  zIndex: number; // 렌더링 순서
  
  // 변형 및 위치
  transform: LayerTransform;
  boundingBox: BoundingBox;
  
  // 상태 및 가시성
  state: LayerState;
  
  // 스타일링
  style?: LayerStyle;
  mask?: LayerMask;
  
  // 메타데이터
  metadata: {
    createdAt: string;
    updatedAt: string;
    source?: 'user' | 'ai' | 'import'; // 레이어 생성 출처
    tags?: string[];
  };
}

/** 이미지 레이어 전용 인터페이스 */
export interface ImageLayer extends BaseLayer {
  type: LayerType.IMAGE;
  content: {
    imageUrl: string;
    originalUrl?: string; // 원본 이미지 URL (압축 전)
    thumbnailUrl?: string; // 썸네일 URL
    naturalWidth: number;
    naturalHeight: number;
    format: 'jpeg' | 'png' | 'webp' | 'svg';
    fileSize?: number; // bytes
    
    // AI 생성 이미지 메타데이터
    aiGenerated?: {
      prompt: string;
      negativePrompt?: string;
      model: string;
      style: string;
      seed?: number;
      generatedAt: string;
    };
    
    // 편집 히스토리
    editHistory?: {
      originalTransform: LayerTransform;
      crops?: BoundingBox[];
      adjustments?: any[];
    };
  };
}

/** 텍스트 레이어 인터페이스 */
export interface TextLayer extends BaseLayer {
  type: LayerType.TEXT;
  content: {
    text: string;
    fontFamily: string;
    fontSize: number;
    fontWeight: 'normal' | 'bold' | '100' | '200' | '300' | '400' | '500' | '600' | '700' | '800' | '900';
    fontStyle: 'normal' | 'italic';
    textAlign: 'left' | 'center' | 'right' | 'justify';
    color: string;
    backgroundColor?: string;
    
    // 고급 텍스트 속성
    lineHeight?: number;
    letterSpacing?: number;
    textDecoration?: 'none' | 'underline' | 'overline' | 'line-through';
    textShadow?: string;
  };
}

/** 그룹 레이어 인터페이스 */
export interface GroupLayer extends BaseLayer {
  type: LayerType.GROUP;
  content: {
    name: string;
    description?: string;
    color?: string; // 그룹 식별 색상
  };
}

/** 통합 레이어 타입 */
export type Layer = ImageLayer | TextLayer | GroupLayer;

// ============= 레이어 컨테이너 및 매니저 =============

/** 레이어 컨테이너 인터페이스 */
export interface LayerContainer {
  id: string;
  canvasId: string; // Canvas v4.0 ID와 연결
  conversationId?: string; // 대화 컨텍스트
  
  layers: Record<string, Layer>; // layerId -> Layer 맵핑
  layerOrder: string[]; // 렌더링 순서 (하위 인덱스가 뒷면)
  selectedLayerIds: string[]; // 다중 선택 지원
  
  // 캔버스 설정
  canvas: {
    width: number;
    height: number;
    backgroundColor: string;
    dpi: number;
  };
  
  // 뷰포트 설정
  viewport: {
    zoom: number;
    panX: number;
    panY: number;
    rotation: number;
  };
  
  // 메타데이터
  metadata: {
    name: string;
    description?: string;
    createdAt: string;
    updatedAt: string;
    version: number; // 동시성 제어용
  };
}

// ============= 편집 도구 시스템 =============

/** 편집 도구 타입 */
export enum EditTool {
  SELECT = 'select',
  MOVE = 'move',
  ROTATE = 'rotate',
  SCALE = 'scale',
  CROP = 'crop',
  BRUSH = 'brush',
  ERASER = 'eraser',
  TEXT = 'text',
  RECTANGLE = 'rectangle',
  CIRCLE = 'circle',
  LINE = 'line',
  PEN = 'pen'
}

/** 선택 도구 타입 */
export enum SelectionTool {
  RECTANGLE = 'rectangle',
  LASSO = 'lasso',
  MAGIC_WAND = 'magic_wand',
  COLOR_RANGE = 'color_range'
}

/** 선택 영역 인터페이스 */
export interface Selection {
  id: string;
  type: SelectionTool;
  bounds: BoundingBox;
  path?: Path2D; // Lasso 선택용
  tolerance?: number; // Magic Wand용
  layerId: string;
  
  // 선택 옵션
  feather: number; // 경계 흐리기
  antiAlias: boolean;
}

/** 편집 작업 인터페이스 */
export interface EditOperation {
  id: string;
  type: 'transform' | 'style' | 'content' | 'layer_order' | 'layer_create' | 'layer_delete';
  layerIds: string[]; // 영향받는 레이어들
  
  // Before/After 상태 (Undo/Redo용)
  before: any;
  after: any;
  
  timestamp: string;
  userId?: string;
}

// ============= 성능 최적화 타입 =============

/** 레이어 캐시 정보 */
export interface LayerCache {
  layerId: string;
  cacheKey: string;
  imageData?: ImageData; // 렌더링된 레이어 데이터
  canvas?: HTMLCanvasElement; // 캐시된 캔버스
  webglTexture?: WebGLTexture; // WebGL 텍스처 캐시
  
  // 캐시 메타데이터
  createdAt: string;
  lastAccessed: string;
  size: number; // bytes
  dirty: boolean; // 재생성 필요 여부
}

/** 렌더링 설정 */
export interface RenderSettings {
  quality: 'draft' | 'normal' | 'high' | 'ultra';
  useWebGL: boolean;
  enableCache: boolean;
  maxCacheSize: number; // bytes
  
  // 성능 설정
  enableAntiAlias: boolean;
  enableBilinearFiltering: boolean;
  maxTextureSize: number;
}

// ============= Canvas v4.0 호환성 =============

/** Canvas v4.0 통합을 위한 어댑터 인터페이스 */
export interface CanvasV4LayerAdapter {
  // Canvas v4.0 CanvasItem → Layer 변환
  convertCanvasItemToLayers(item: CanvasItem): Layer[];
  
  // Layer → Canvas v4.0 CanvasItem 변환  
  convertLayersToCanvasItem(layers: Layer[], type: string): CanvasItem;
  
  // 기존 ImageGenerator와 통합
  integrateWithImageGenerator(layerContainer: LayerContainer): void;
  
  // 기존 ImageVersionGallery와 통합
  syncWithVersionGallery(layerContainer: LayerContainer): void;
}

// ============= 이벤트 시스템 =============

/** 레이어 이벤트 타입 */
export type LayerEvent = 
  | { type: 'layer:created'; layerId: string; layer: Layer }
  | { type: 'layer:updated'; layerId: string; changes: Partial<Layer> }
  | { type: 'layer:deleted'; layerId: string }
  | { type: 'layer:reordered'; oldIndex: number; newIndex: number }
  | { type: 'layer:selected'; layerIds: string[] }
  | { type: 'layer:transformed'; layerId: string; transform: LayerTransform }
  | { type: 'container:loaded'; containerId: string }
  | { type: 'container:saved'; containerId: string };

/** 이벤트 리스너 인터페이스 */
export interface LayerEventListener {
  (event: LayerEvent): void;
}

export default Layer;