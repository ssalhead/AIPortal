/**
 * 전문가급 이미지 편집 도구 타입 정의
 */

// ======= 편집 도구 타입 =======

export type EditTool = 
  | 'select'          // 기본 선택
  | 'crop'           // 크롭 도구
  | 'magic-wand'     // 마법봉 (색상 기반 선택)
  | 'lasso'          // 올가미 도구
  | 'transform'      // 자유 변형
  | 'perspective'    // 원근 변형
  | 'distort'        // 왜곡 변형
  | 'brush'          // 브러시
  | 'eraser'         // 지우개
  | 'clone'          // 클론 스탬프
  | 'healing'        // 스팟 힐링
  | 'patch'          // 패치 도구
  | 'text'           // 텍스트 도구
  | 'shape'          // 도형 도구
  | 'filter';        // 필터 적용

// ======= 크롭 모드 =======

export type CropMode = 
  | 'free'           // 자유 크롭
  | 'square'         // 1:1 정사각형
  | 'landscape'      // 16:9 가로
  | 'portrait'       // 9:16 세로
  | 'photo'          // 4:3 사진
  | 'circle'         // 원형 크롭
  | 'polygon';       // 다각형 크롭

export interface CropArea {
  x: number;
  y: number;
  width: number;
  height: number;
  rotation?: number;
}

// ======= 선택 영역 =======

export interface SelectionArea {
  type: 'rectangle' | 'circle' | 'polygon' | 'freehand';
  points: number[];
  feathering?: number;    // 가장자리 부드럽게
  antiAlias?: boolean;
}

// ======= 변형 모드 =======

export type TransformMode =
  | 'resize'         // 크기 조정
  | 'rotate'         // 회전
  | 'skew'          // 기울이기
  | 'perspective'    // 원근
  | 'distort'       // 자유 변형
  | 'warp';         // 워프

export interface TransformMatrix {
  a: number;  // 가로 크기
  b: number;  // 가로 기울기
  c: number;  // 세로 기울기  
  d: number;  // 세로 크기
  e: number;  // 가로 이동
  f: number;  // 세로 이동
}

// ======= 필터 및 효과 =======

export type FilterCategory = 
  | 'basic'          // 기본 (밝기, 대비, 채도)
  | 'artistic'       // 예술적 효과
  | 'stylize'        // 스타일화
  | 'blur'           // 블러 효과
  | 'noise'          // 노이즈 효과
  | 'distort'        // 왜곡 효과
  | 'color';         // 색상 보정

export interface FilterParams {
  name: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
}

export interface ImageFilter {
  id: string;
  name: string;
  category: FilterCategory;
  params: FilterParams[];
  previewUrl?: string;
}

// ======= 브러시 도구 =======

export interface BrushSettings {
  size: number;           // 브러시 크기
  hardness: number;       // 가장자리 경도 (0-100)
  opacity: number;        // 투명도 (0-100)
  flow: number;          // 유량 (0-100)
  spacing: number;        // 간격 (0-100)
  pressure: boolean;      // 압력 감지
  color: string;         // 브러시 색상
  blendMode: BlendMode;  // 블렌드 모드
}

export type BlendMode =
  | 'normal'
  | 'multiply'
  | 'screen' 
  | 'overlay'
  | 'soft-light'
  | 'hard-light'
  | 'color-dodge'
  | 'color-burn'
  | 'darken'
  | 'lighten'
  | 'difference'
  | 'exclusion';

// ======= 레이어 시스템 =======

export interface EditingLayer {
  id: string;
  name: string;
  type: 'image' | 'adjustment' | 'text' | 'shape' | 'effect';
  visible: boolean;
  opacity: number;        // 0-100
  blendMode: BlendMode;
  locked: boolean;
  maskData?: ImageData;   // 레이어 마스크
  effects: LayerEffect[]; // 레이어 효과
  bounds?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface LayerEffect {
  id: string;
  type: 'drop-shadow' | 'inner-shadow' | 'glow' | 'stroke' | 'bevel';
  enabled: boolean;
  params: Record<string, any>;
}

// ======= 편집 히스토리 =======

export interface EditAction {
  id: string;
  type: string;
  timestamp: number;
  description: string;
  beforeState?: any;      // 이전 상태
  afterState?: any;       // 이후 상태
  canUndo: boolean;
  canRedo: boolean;
}

export interface EditHistory {
  actions: EditAction[];
  currentIndex: number;
  maxHistorySize: number;
}

// ======= 편집 상태 =======

export interface EditingState {
  currentTool: EditTool;
  activeLayer: string | null;
  selection: SelectionArea | null;
  cropArea: CropArea | null;
  transformMode: TransformMode | null;
  brushSettings: BrushSettings;
  filterPreview: {
    filterId: string;
    params: Record<string, any>;
  } | null;
  
  // UI 상태
  showGrid: boolean;
  showRulers: boolean;
  snapToGrid: boolean;
  zoomLevel: number;      // 0.1 - 5.0
  
  // 성능 설정
  highQualityPreview: boolean;
  realTimePreview: boolean;
}

// ======= 내보내기 옵션 =======

export interface ExportOptions {
  format: 'png' | 'jpg' | 'webp' | 'svg' | 'pdf';
  quality?: number;       // JPG/WebP용 (0-100)
  width?: number;         // 커스텀 크기
  height?: number;
  dpi?: number;          // 인쇄용 DPI
  colorSpace?: 'sRGB' | 'AdobeRGB' | 'P3';
  includeMetadata?: boolean;
}

// ======= 이벤트 타입 =======

export interface EditingEvent {
  type: 'tool-changed' | 'selection-changed' | 'layer-changed' | 'filter-applied' | 'action-performed';
  payload: any;
  timestamp: number;
}

// ======= AI 기반 도구 설정 =======

export interface AIToolSettings {
  backgroundRemoval: {
    model: 'u2net' | 'silueta' | 'deep-lab';
    threshold: number;
    smoothEdges: boolean;
  };
  
  objectDetection: {
    model: 'yolo' | 'coco' | 'custom';
    confidence: number;
    includeLabels: string[];
  };
  
  inpainting: {
    model: 'lama' | 'coherent' | 'edge-connect';
    guidanceScale: number;
    iterations: number;
  };
  
  enhancement: {
    model: 'esrgan' | 'real-esrgan' | 'srcnn';
    scaleFactor: number;
    preserveDetails: boolean;
  };
}

// ======= 편집 엔진 인터페이스 =======

export interface ImageEditingEngine {
  // 기본 기능
  loadImage(source: string | File | ImageData): Promise<void>;
  exportImage(options: ExportOptions): Promise<Blob>;
  
  // 도구 관리
  setActiveTool(tool: EditTool): void;
  getActiveTool(): EditTool;
  
  // 선택/크롭
  createSelection(area: SelectionArea): void;
  cropToSelection(area: CropArea): void;
  clearSelection(): void;
  
  // 변형
  transform(matrix: TransformMatrix): void;
  rotate(angle: number): void;
  resize(width: number, height: number): void;
  
  // 필터
  applyFilter(filter: ImageFilter, params: Record<string, any>): void;
  removeFilter(filterId: string): void;
  
  // 레이어
  createLayer(type: EditingLayer['type']): EditingLayer;
  deleteLayer(layerId: string): void;
  mergeDown(layerId: string): void;
  
  // 히스토리
  undo(): boolean;
  redo(): boolean;
  getHistory(): EditHistory;
  
  // 이벤트
  on(event: string, callback: (data: any) => void): void;
  off(event: string, callback: (data: any) => void): void;
}