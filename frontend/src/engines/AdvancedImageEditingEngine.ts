/**
 * AdvancedImageEditingEngine v1.0 - 전문가급 이미지 편집 엔진
 * 
 * 특징:
 * - Konva.js 기반 고성능 렌더링
 * - 크롭, 변형, 필터, 인페인팅 도구
 * - AI 기반 배경 제거 및 객체 감지
 * - 레이어 시스템 및 편집 히스토리
 * - 실시간 프리뷰 및 성능 최적화
 */

import Konva from 'konva';
import type { 
  EditTool, 
  CropMode, 
  CropArea, 
  SelectionArea,
  TransformMode,
  TransformMatrix,
  ImageFilter,
  FilterCategory,
  BrushSettings,
  EditingLayer,
  EditAction,
  EditHistory,
  EditingState,
  ExportOptions,
  ImageEditingEngine,
  AIToolSettings
} from '../types/imageEditing';

// ======= 편집 엔진 클래스 =======

export class AdvancedImageEditingEngine implements ImageEditingEngine {
  // Konva 관련
  private stage: Konva.Stage;
  private layers: Map<string, Konva.Layer> = new Map();
  private editingLayers: Map<string, EditingLayer> = new Map();
  
  // 이미지 및 캔버스
  private sourceImage: HTMLImageElement | null = null;
  private workingCanvas: HTMLCanvasElement;
  private workingContext: CanvasRenderingContext2D;
  
  // 편집 상태
  private state: EditingState;
  private history: EditHistory;
  
  // 도구 관련
  private currentTool: EditTool = 'select';
  private cropOverlay: Konva.Group | null = null;
  private selectionArea: SelectionArea | null = null;
  private transformer: Konva.Transformer;
  
  // AI 도구
  private aiSettings: AIToolSettings;
  
  // 이벤트 시스템
  private eventListeners: Map<string, Function[]> = new Map();
  
  // 성능 관리
  private performanceMode: 'high-quality' | 'fast' = 'high-quality';
  private renderTimeout: number | null = null;

  constructor(container: HTMLDivElement, width: number = 1200, height: number = 800) {
    console.log('🎨 AdvancedImageEditingEngine 초기화 시작');
    
    // Konva Stage 초기화
    this.stage = new Konva.Stage({
      container,
      width,
      height,
      draggable: false
    });
    
    // 작업 캔버스 초기화
    this.workingCanvas = document.createElement('canvas');
    this.workingCanvas.width = width;
    this.workingCanvas.height = height;
    this.workingContext = this.workingCanvas.getContext('2d')!;
    
    // 편집 상태 초기화
    this.state = this.createInitialState();
    this.history = this.createInitialHistory();
    this.aiSettings = this.createDefaultAISettings();
    
    // 레이어 시스템 초기화
    this.initializeLayers();
    
    // Transformer 초기화
    this.initializeTransformer();
    
    // 이벤트 핸들러 설정
    this.setupEventHandlers();
    
    console.log('✅ AdvancedImageEditingEngine 초기화 완료');
  }

  // ======= 초기화 메서드 =======

  private createInitialState(): EditingState {
    return {
      currentTool: 'select',
      activeLayer: null,
      selection: null,
      cropArea: null,
      transformMode: null,
      brushSettings: {
        size: 20,
        hardness: 80,
        opacity: 100,
        flow: 100,
        spacing: 25,
        pressure: false,
        color: '#000000',
        blendMode: 'normal'
      },
      filterPreview: null,
      showGrid: false,
      showRulers: false,
      snapToGrid: false,
      zoomLevel: 1.0,
      highQualityPreview: true,
      realTimePreview: true
    };
  }

  private createInitialHistory(): EditHistory {
    return {
      actions: [],
      currentIndex: -1,
      maxHistorySize: 50
    };
  }

  private createDefaultAISettings(): AIToolSettings {
    return {
      backgroundRemoval: {
        model: 'u2net',
        threshold: 0.5,
        smoothEdges: true
      },
      objectDetection: {
        model: 'yolo',
        confidence: 0.5,
        includeLabels: []
      },
      inpainting: {
        model: 'lama',
        guidanceScale: 7.5,
        iterations: 20
      },
      enhancement: {
        model: 'real-esrgan',
        scaleFactor: 2,
        preserveDetails: true
      }
    };
  }

  private initializeLayers(): void {
    const layerConfigs = [
      { name: 'background', type: 'background' },
      { name: 'image', type: 'image' },
      { name: 'adjustment', type: 'adjustment' },
      { name: 'text', type: 'text' },
      { name: 'shapes', type: 'shape' },
      { name: 'effects', type: 'effect' },
      { name: 'ui', type: 'ui' }
    ];

    layerConfigs.forEach(config => {
      const layer = new Konva.Layer({ name: config.name });
      this.layers.set(config.name, layer);
      this.stage.add(layer);
    });

    this.stage.draw();
  }

  private initializeTransformer(): void {
    this.transformer = new Konva.Transformer({
      boundBoxFunc: (oldBox, newBox) => {
        if (newBox.width < 20 || newBox.height < 20) {
          return oldBox;
        }
        return newBox;
      },
      enabledAnchors: ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'middle-left', 'middle-right', 'top-center', 'bottom-center'],
      rotationSnaps: [0, 45, 90, 135, 180, 225, 270, 315]
    });

    const uiLayer = this.layers.get('ui');
    if (uiLayer) {
      uiLayer.add(this.transformer);
    }
  }

  // ======= 이미지 로드 =======

  public async loadImage(source: string | File | ImageData): Promise<void> {
    console.log('📸 이미지 로드 시작');
    
    try {
      let imageElement: HTMLImageElement;
      
      if (typeof source === 'string') {
        // URL에서 로드
        imageElement = await this.loadImageFromURL(source);
      } else if (source instanceof File) {
        // 파일에서 로드
        imageElement = await this.loadImageFromFile(source);
      } else {
        // ImageData에서 로드
        imageElement = await this.loadImageFromImageData(source);
      }
      
      this.sourceImage = imageElement;
      
      // 메인 이미지 레이어에 렌더링
      await this.renderImageToLayer(imageElement, 'image');
      
      // 편집 히스토리에 기록
      this.addHistoryAction({
        id: this.generateActionId(),
        type: 'load-image',
        timestamp: Date.now(),
        description: '이미지 로드',
        beforeState: null,
        afterState: { imageLoaded: true },
        canUndo: false,
        canRedo: false
      });
      
      console.log('✅ 이미지 로드 완료');
      this.emit('image-loaded', { image: imageElement });
      
    } catch (error) {
      console.error('❌ 이미지 로드 실패:', error);
      throw error;
    }
  }

  private async loadImageFromURL(url: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error(`이미지 로드 실패: ${url}`));
      img.src = url;
    });
  }

  private async loadImageFromFile(file: File): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error('파일에서 이미지 생성 실패'));
        img.src = e.target?.result as string;
      };
      reader.onerror = () => reject(new Error('파일 읽기 실패'));
      reader.readAsDataURL(file);
    });
  }

  private async loadImageFromImageData(imageData: ImageData): Promise<HTMLImageElement> {
    const canvas = document.createElement('canvas');
    canvas.width = imageData.width;
    canvas.height = imageData.height;
    const ctx = canvas.getContext('2d')!;
    ctx.putImageData(imageData, 0, 0);
    
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error('ImageData에서 이미지 생성 실패'));
      img.src = canvas.toDataURL();
    });
  }

  private async renderImageToLayer(image: HTMLImageElement, layerName: string): Promise<void> {
    const layer = this.layers.get(layerName);
    if (!layer) return;

    // 기존 이미지 제거
    layer.removeChildren();

    // 새 Konva Image 생성
    const konvaImage = new Konva.Image({
      image,
      width: image.width,
      height: image.height,
      x: (this.stage.width() - image.width) / 2,
      y: (this.stage.height() - image.height) / 2,
      draggable: true
    });

    layer.add(konvaImage);
    layer.draw();

    // 활성 레이어로 설정
    this.state.activeLayer = layerName;
  }

  // ======= 크롭 도구 =======

  public setCropMode(mode: CropMode): void {
    this.currentTool = 'crop';
    this.state.currentTool = 'crop';
    
    console.log(`🔲 크롭 모드 설정: ${mode}`);
    
    // 기존 크롭 오버레이 제거
    this.clearCropOverlay();
    
    // 새 크롭 오버레이 생성
    this.createCropOverlay(mode);
    
    this.emit('tool-changed', { tool: 'crop', mode });
  }

  private createCropOverlay(mode: CropMode): void {
    const uiLayer = this.layers.get('ui');
    if (!uiLayer) return;

    this.cropOverlay = new Konva.Group({ name: 'crop-overlay' });

    const stageWidth = this.stage.width();
    const stageHeight = this.stage.height();
    
    // 크롭 영역 초기 크기 계산
    let cropWidth = stageWidth * 0.6;
    let cropHeight = stageHeight * 0.6;
    
    // 비율에 따른 크기 조정
    switch (mode) {
      case 'square':
        cropHeight = cropWidth;
        break;
      case 'landscape':
        cropHeight = cropWidth * (9 / 16);
        break;
      case 'portrait':
        cropWidth = cropHeight * (9 / 16);
        break;
      case 'photo':
        cropHeight = cropWidth * (3 / 4);
        break;
    }

    const cropX = (stageWidth - cropWidth) / 2;
    const cropY = (stageHeight - cropHeight) / 2;

    if (mode === 'circle') {
      // 원형 크롭
      const radius = Math.min(cropWidth, cropHeight) / 2;
      this.createCircleCropOverlay(cropX + radius, cropY + radius, radius);
    } else if (mode === 'polygon') {
      // 다각형 크롭 (기본 6각형)
      this.createPolygonCropOverlay(cropX + cropWidth/2, cropY + cropHeight/2, Math.min(cropWidth, cropHeight) / 2, 6);
    } else {
      // 사각형 크롭
      this.createRectangleCropOverlay(cropX, cropY, cropWidth, cropHeight);
    }

    uiLayer.add(this.cropOverlay);
    uiLayer.draw();
  }

  private createRectangleCropOverlay(x: number, y: number, width: number, height: number): void {
    if (!this.cropOverlay) return;

    // 어두운 오버레이 (크롭 영역 외부)
    const darkOverlay = new Konva.Rect({
      x: 0,
      y: 0,
      width: this.stage.width(),
      height: this.stage.height(),
      fill: 'rgba(0, 0, 0, 0.5)',
      listening: false
    });

    // 크롭 영역 (투명)
    const cropRect = new Konva.Rect({
      x,
      y,
      width,
      height,
      fill: 'transparent',
      stroke: '#fff',
      strokeWidth: 2,
      dash: [5, 5],
      draggable: true
    });

    // 크롭 핸들들
    const handles = this.createCropHandles(x, y, width, height);

    this.cropOverlay.add(darkOverlay);
    this.cropOverlay.add(cropRect);
    handles.forEach(handle => this.cropOverlay!.add(handle));

    // 크롭 영역을 어두운 부분에서 제외 (globalCompositeOperation 사용)
    darkOverlay.globalCompositeOperation('source-over');
  }

  private createCircleCropOverlay(centerX: number, centerY: number, radius: number): void {
    if (!this.cropOverlay) return;

    // 어두운 오버레이
    const darkOverlay = new Konva.Rect({
      x: 0,
      y: 0,
      width: this.stage.width(),
      height: this.stage.height(),
      fill: 'rgba(0, 0, 0, 0.5)',
      listening: false
    });

    // 크롭 원
    const cropCircle = new Konva.Circle({
      x: centerX,
      y: centerY,
      radius,
      fill: 'transparent',
      stroke: '#fff',
      strokeWidth: 2,
      dash: [5, 5],
      draggable: true
    });

    this.cropOverlay.add(darkOverlay);
    this.cropOverlay.add(cropCircle);
  }

  private createPolygonCropOverlay(centerX: number, centerY: number, radius: number, sides: number): void {
    if (!this.cropOverlay) return;

    // 다각형 포인트 계산
    const points: number[] = [];
    for (let i = 0; i < sides; i++) {
      const angle = (i * 2 * Math.PI) / sides;
      points.push(centerX + radius * Math.cos(angle));
      points.push(centerY + radius * Math.sin(angle));
    }

    // 어두운 오버레이
    const darkOverlay = new Konva.Rect({
      x: 0,
      y: 0,
      width: this.stage.width(),
      height: this.stage.height(),
      fill: 'rgba(0, 0, 0, 0.5)',
      listening: false
    });

    // 크롭 다각형
    const cropPolygon = new Konva.Line({
      points,
      fill: 'transparent',
      stroke: '#fff',
      strokeWidth: 2,
      dash: [5, 5],
      closed: true,
      draggable: true
    });

    this.cropOverlay.add(darkOverlay);
    this.cropOverlay.add(cropPolygon);
  }

  private createCropHandles(x: number, y: number, width: number, height: number): Konva.Circle[] {
    const handleSize = 8;
    const handles: Konva.Circle[] = [];

    const handlePositions = [
      { x: x, y: y }, // 좌상
      { x: x + width, y: y }, // 우상  
      { x: x + width, y: y + height }, // 우하
      { x: x, y: y + height }, // 좌하
      { x: x + width/2, y: y }, // 상중
      { x: x + width/2, y: y + height }, // 하중
      { x: x, y: y + height/2 }, // 좌중
      { x: x + width, y: y + height/2 } // 우중
    ];

    handlePositions.forEach((pos, index) => {
      const handle = new Konva.Circle({
        x: pos.x,
        y: pos.y,
        radius: handleSize,
        fill: '#fff',
        stroke: '#666',
        strokeWidth: 1,
        draggable: true,
        name: `crop-handle-${index}`
      });

      handles.push(handle);
    });

    return handles;
  }

  public applyCrop(): void {
    if (!this.cropOverlay || !this.sourceImage) return;

    console.log('✂️ 크롭 적용 시작');

    // 크롭 영역 정보 추출
    const cropShape = this.cropOverlay.findOne((node) => 
      node.name() !== 'crop-overlay' && node.fill() === 'transparent'
    );

    if (!cropShape) return;

    let cropArea: CropArea;

    if (cropShape instanceof Konva.Rect) {
      cropArea = {
        x: cropShape.x(),
        y: cropShape.y(),
        width: cropShape.width(),
        height: cropShape.height(),
        rotation: cropShape.rotation()
      };
    } else if (cropShape instanceof Konva.Circle) {
      const radius = cropShape.radius();
      cropArea = {
        x: cropShape.x() - radius,
        y: cropShape.y() - radius,
        width: radius * 2,
        height: radius * 2,
        rotation: 0
      };
    } else {
      console.warn('⚠️ 지원하지 않는 크롭 형태');
      return;
    }

    // 히스토리에 기록
    this.addHistoryAction({
      id: this.generateActionId(),
      type: 'crop',
      timestamp: Date.now(),
      description: '이미지 크롭',
      beforeState: this.captureState(),
      afterState: null,
      canUndo: true,
      canRedo: false
    });

    // 실제 크롭 실행
    this.performCrop(cropArea);

    this.clearCropOverlay();
    this.currentTool = 'select';
    this.state.currentTool = 'select';

    this.emit('crop-applied', { cropArea });
    console.log('✅ 크롭 적용 완료');
  }

  private performCrop(cropArea: CropArea): void {
    if (!this.sourceImage) return;

    // 캔버스에서 크롭 영역 추출
    this.workingContext.clearRect(0, 0, this.workingCanvas.width, this.workingCanvas.height);
    this.workingContext.drawImage(this.sourceImage, 0, 0);

    const croppedImageData = this.workingContext.getImageData(
      cropArea.x,
      cropArea.y,
      cropArea.width,
      cropArea.height
    );

    // 새 캔버스에 크롭된 이미지 그리기
    const croppedCanvas = document.createElement('canvas');
    croppedCanvas.width = cropArea.width;
    croppedCanvas.height = cropArea.height;
    const croppedContext = croppedCanvas.getContext('2d')!;
    croppedContext.putImageData(croppedImageData, 0, 0);

    // 크롭된 이미지를 다시 로드
    const croppedImage = new Image();
    croppedImage.onload = () => {
      this.sourceImage = croppedImage;
      this.renderImageToLayer(croppedImage, 'image');
    };
    croppedImage.src = croppedCanvas.toDataURL();
  }

  private clearCropOverlay(): void {
    if (this.cropOverlay) {
      this.cropOverlay.destroy();
      this.cropOverlay = null;
      
      const uiLayer = this.layers.get('ui');
      if (uiLayer) {
        uiLayer.draw();
      }
    }
  }

  // ======= 마법봉 도구 (색상 기반 선택) =======

  public selectByColor(x: number, y: number, tolerance: number = 32): void {
    if (!this.sourceImage) return;

    console.log(`🪄 마법봉 도구 실행: (${x}, ${y}), tolerance: ${tolerance}`);

    // 이미지 데이터 가져오기
    this.workingContext.clearRect(0, 0, this.workingCanvas.width, this.workingCanvas.height);
    this.workingContext.drawImage(this.sourceImage, 0, 0);
    
    const imageData = this.workingContext.getImageData(0, 0, this.workingCanvas.width, this.workingCanvas.height);
    const pixels = imageData.data;

    // 클릭한 지점의 색상 가져오기
    const targetIndex = (y * imageData.width + x) * 4;
    const targetR = pixels[targetIndex];
    const targetG = pixels[targetIndex + 1];
    const targetB = pixels[targetIndex + 2];
    const targetA = pixels[targetIndex + 3];

    // Flood Fill 알고리즘으로 비슷한 색상 영역 선택
    const selectedPixels = this.floodFillSelection(
      imageData,
      x,
      y,
      targetR,
      targetG,
      targetB,
      targetA,
      tolerance
    );

    // 선택 영역 생성
    this.createSelectionFromPixels(selectedPixels, imageData.width, imageData.height);

    this.emit('selection-created', { method: 'magic-wand', area: this.selectionArea });
  }

  private floodFillSelection(
    imageData: ImageData,
    startX: number,
    startY: number,
    targetR: number,
    targetG: number,
    targetB: number,
    targetA: number,
    tolerance: number
  ): boolean[] {
    const width = imageData.width;
    const height = imageData.height;
    const pixels = imageData.data;
    const visited = new Array(width * height).fill(false);
    const selected = new Array(width * height).fill(false);
    const queue: [number, number][] = [[startX, startY]];

    while (queue.length > 0) {
      const [x, y] = queue.shift()!;
      
      if (x < 0 || x >= width || y < 0 || y >= height) continue;
      
      const index = y * width + x;
      if (visited[index]) continue;
      
      visited[index] = true;
      
      const pixelIndex = index * 4;
      const r = pixels[pixelIndex];
      const g = pixels[pixelIndex + 1];
      const b = pixels[pixelIndex + 2];
      const a = pixels[pixelIndex + 3];
      
      // 색상 유사도 검사
      const colorDistance = Math.sqrt(
        Math.pow(r - targetR, 2) +
        Math.pow(g - targetG, 2) +
        Math.pow(b - targetB, 2) +
        Math.pow(a - targetA, 2)
      );
      
      if (colorDistance <= tolerance) {
        selected[index] = true;
        
        // 인접 픽셀을 큐에 추가
        queue.push([x - 1, y], [x + 1, y], [x, y - 1], [x, y + 1]);
      }
    }

    return selected;
  }

  private createSelectionFromPixels(selectedPixels: boolean[], width: number, height: number): void {
    // 선택된 픽셀들의 경계선 찾기 (Marching Squares 알고리즘 사용)
    const contours = this.traceContours(selectedPixels, width, height);
    
    if (contours.length > 0) {
      this.selectionArea = {
        type: 'freehand',
        points: contours,
        feathering: 0,
        antiAlias: true
      };
      
      this.state.selection = this.selectionArea;
      this.renderSelectionOverlay();
    }
  }

  private traceContours(pixels: boolean[], width: number, height: number): number[] {
    // 간단한 경계선 추적 알고리즘
    const contours: number[] = [];
    
    for (let y = 0; y < height - 1; y++) {
      for (let x = 0; x < width - 1; x++) {
        const current = pixels[y * width + x];
        const right = pixels[y * width + x + 1];
        const bottom = pixels[(y + 1) * width + x];
        
        // 경계선 감지
        if (current !== right || current !== bottom) {
          contours.push(x, y);
        }
      }
    }
    
    return contours;
  }

  // ======= 도구 관리 =======

  public setActiveTool(tool: EditTool): void {
    this.currentTool = tool;
    this.state.currentTool = tool;
    
    console.log(`🛠️ 활성 도구 변경: ${tool}`);
    
    // 이전 도구 정리
    this.cleanupPreviousTool();
    
    // 새 도구 초기화
    this.initializeTool(tool);
    
    this.emit('tool-changed', { tool });
  }

  public getActiveTool(): EditTool {
    return this.currentTool;
  }

  private cleanupPreviousTool(): void {
    // 크롭 오버레이 정리
    this.clearCropOverlay();
    
    // 선택 영역 정리 (필요시)
    if (this.currentTool === 'select') {
      // 선택 도구가 아닌 경우에만 선택 해제
    }
    
    // Transformer 정리
    this.transformer.nodes([]);
    this.transformer.getLayer()?.draw();
  }

  private initializeTool(tool: EditTool): void {
    switch (tool) {
      case 'select':
        // 기본 선택 도구 - 특별한 초기화 없음
        break;
      case 'crop':
        // 크롭 도구는 setCropMode를 통해 초기화
        break;
      case 'magic-wand':
        // 마법봉 도구 - 클릭 대기 상태
        this.setupMagicWandTool();
        break;
      case 'lasso':
        // 올가미 도구 초기화
        this.setupLassoTool();
        break;
      case 'transform':
        // 변형 도구 초기화
        this.setupTransformTool();
        break;
      default:
        console.log(`도구 ${tool}는 아직 구현되지 않음`);
    }
  }

  private setupMagicWandTool(): void {
    // 마법봉 도구용 이벤트 리스너
    this.stage.off('click.magicwand');
    this.stage.on('click.magicwand', (e) => {
      if (this.currentTool === 'magic-wand') {
        const pos = this.stage.getPointerPosition();
        if (pos) {
          this.selectByColor(pos.x, pos.y, 32);
        }
      }
    });
  }

  private setupLassoTool(): void {
    console.log('🎯 올가미 도구 설정');
    
    let isDrawing = false;
    let points: number[] = [];
    
    this.stage.off('mousedown.lasso mousemove.lasso mouseup.lasso');
    
    this.stage.on('mousedown.lasso', () => {
      if (this.currentTool === 'lasso') {
        isDrawing = true;
        points = [];
        const pos = this.stage.getPointerPosition();
        if (pos) {
          points.push(pos.x, pos.y);
        }
      }
    });
    
    this.stage.on('mousemove.lasso', () => {
      if (this.currentTool === 'lasso' && isDrawing) {
        const pos = this.stage.getPointerPosition();
        if (pos) {
          points.push(pos.x, pos.y);
          this.drawLassoPreview(points);
        }
      }
    });
    
    this.stage.on('mouseup.lasso', () => {
      if (this.currentTool === 'lasso' && isDrawing) {
        isDrawing = false;
        this.createLassoSelection(points);
      }
    });
  }

  private drawLassoPreview(points: number[]): void {
    const uiLayer = this.layers.get('ui');
    if (!uiLayer) return;

    // 기존 프리뷰 제거
    const existingPreview = uiLayer.findOne('.lasso-preview');
    existingPreview?.destroy();

    // 새 프리뷰 생성
    const lassoLine = new Konva.Line({
      points: points,
      stroke: '#fff',
      strokeWidth: 2,
      dash: [5, 5],
      name: 'lasso-preview'
    });

    uiLayer.add(lassoLine);
    uiLayer.draw();
  }

  private createLassoSelection(points: number[]): void {
    if (points.length < 6) return; // 최소 3개 점 필요

    this.selectionArea = {
      type: 'freehand',
      points: points,
      feathering: 0,
      antiAlias: true
    };
    
    this.state.selection = this.selectionArea;
    this.renderSelectionOverlay();

    // 프리뷰 정리
    const uiLayer = this.layers.get('ui');
    const preview = uiLayer?.findOne('.lasso-preview');
    preview?.destroy();
    uiLayer?.draw();

    this.emit('selection-created', { method: 'lasso', area: this.selectionArea });
  }

  private setupTransformTool(): void {
    console.log('🔄 변형 도구 설정');
    
    // 활성 이미지 선택
    const imageLayer = this.layers.get('image');
    const imageNode = imageLayer?.children?.[0];
    
    if (imageNode) {
      this.transformer.nodes([imageNode]);
      this.transformer.getLayer()?.draw();
    }
  }

  // ======= 선택 영역 관리 =======

  public createSelection(area: SelectionArea): void {
    this.selectionArea = area;
    this.state.selection = area;
    this.renderSelectionOverlay();
    
    console.log('📋 선택 영역 생성:', area.type);
    this.emit('selection-changed', area);
  }

  public clearSelection(): void {
    this.selectionArea = null;
    this.state.selection = null;
    
    // 선택 오버레이 제거
    const uiLayer = this.layers.get('ui');
    const selectionOverlay = uiLayer?.findOne('.selection-overlay');
    selectionOverlay?.destroy();
    uiLayer?.draw();
    
    console.log('🚫 선택 영역 해제');
    this.emit('selection-cleared');
  }

  private renderSelectionOverlay(): void {
    if (!this.selectionArea) return;

    const uiLayer = this.layers.get('ui');
    if (!uiLayer) return;

    // 기존 선택 오버레이 제거
    const existingOverlay = uiLayer.findOne('.selection-overlay');
    existingOverlay?.destroy();

    let selectionShape: Konva.Shape;

    switch (this.selectionArea.type) {
      case 'rectangle':
        selectionShape = this.createRectangleSelection();
        break;
      case 'circle':
        selectionShape = this.createCircleSelection();
        break;
      case 'polygon':
      case 'freehand':
        selectionShape = this.createPolygonSelection();
        break;
      default:
        return;
    }

    selectionShape.setAttrs({
      name: 'selection-overlay',
      stroke: '#fff',
      strokeWidth: 1,
      dash: [5, 5],
      fill: 'transparent'
    });

    uiLayer.add(selectionShape);
    uiLayer.draw();
  }

  private createRectangleSelection(): Konva.Rect {
    const points = this.selectionArea!.points;
    return new Konva.Rect({
      x: points[0],
      y: points[1],
      width: points[2] - points[0],
      height: points[3] - points[1]
    });
  }

  private createCircleSelection(): Konva.Circle {
    const points = this.selectionArea!.points;
    const centerX = points[0];
    const centerY = points[1];
    const radius = Math.sqrt(Math.pow(points[2] - centerX, 2) + Math.pow(points[3] - centerY, 2));
    
    return new Konva.Circle({
      x: centerX,
      y: centerY,
      radius
    });
  }

  private createPolygonSelection(): Konva.Line {
    return new Konva.Line({
      points: this.selectionArea!.points,
      closed: true
    });
  }

  // ======= 크롭 기능 =======

  public cropToSelection(area: CropArea): void {
    if (!this.sourceImage) return;

    console.log('✂️ 선택 영역으로 크롭');
    
    this.addHistoryAction({
      id: this.generateActionId(),
      type: 'crop-to-selection',
      timestamp: Date.now(),
      description: '선택 영역 크롭',
      beforeState: this.captureState(),
      afterState: null,
      canUndo: true,
      canRedo: false
    });

    this.performCrop(area);
    this.clearSelection();
    
    this.emit('crop-applied', { cropArea: area });
  }

  // ======= 이벤트 시스템 =======

  private setupEventHandlers(): void {
    // 기본 클릭 이벤트
    this.stage.on('click tap', (e) => {
      if (e.target === this.stage) {
        // 빈 영역 클릭 시 선택 해제
        this.transformer.nodes([]);
        this.transformer.getLayer()?.draw();
      }
    });
  }

  public on(event: string, callback: (data: any) => void): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(callback);
  }

  public off(event: string, callback: (data: any) => void): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private emit(event: string, data?: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => callback(data));
    }
  }

  // ======= 히스토리 시스템 =======

  private addHistoryAction(action: EditAction): void {
    // 현재 위치 이후의 액션들 제거 (새로운 분기)
    this.history.actions = this.history.actions.slice(0, this.history.currentIndex + 1);
    
    // 새 액션 추가
    this.history.actions.push(action);
    this.history.currentIndex++;
    
    // 최대 히스토리 크기 제한
    if (this.history.actions.length > this.history.maxHistorySize) {
      this.history.actions.shift();
      this.history.currentIndex--;
    }
    
    console.log(`📝 히스토리 액션 추가: ${action.type} (${this.history.currentIndex + 1}/${this.history.actions.length})`);
  }

  public undo(): boolean {
    if (this.history.currentIndex < 0) {
      console.log('⏪ 실행 취소할 작업 없음');
      return false;
    }
    
    const action = this.history.actions[this.history.currentIndex];
    if (!action.canUndo) {
      console.log('⏪ 실행 취소할 수 없는 작업');
      return false;
    }
    
    console.log(`⏪ 실행 취소: ${action.description}`);
    
    // 이전 상태로 복원
    if (action.beforeState) {
      this.restoreState(action.beforeState);
    }
    
    this.history.currentIndex--;
    this.emit('action-undone', action);
    
    return true;
  }

  public redo(): boolean {
    if (this.history.currentIndex >= this.history.actions.length - 1) {
      console.log('⏩ 다시 실행할 작업 없음');
      return false;
    }
    
    const action = this.history.actions[this.history.currentIndex + 1];
    if (!action.canRedo) {
      console.log('⏩ 다시 실행할 수 없는 작업');
      return false;
    }
    
    console.log(`⏩ 다시 실행: ${action.description}`);
    
    // 이후 상태로 복원
    if (action.afterState) {
      this.restoreState(action.afterState);
    }
    
    this.history.currentIndex++;
    this.emit('action-redone', action);
    
    return true;
  }

  public getHistory(): EditHistory {
    return { ...this.history };
  }

  private captureState(): any {
    return {
      // 필요한 상태 정보 캡처
      imageData: this.sourceImage ? this.sourceImage.src : null,
      selection: this.selectionArea ? { ...this.selectionArea } : null,
      layers: Array.from(this.editingLayers.values()),
      timestamp: Date.now()
    };
  }

  private restoreState(state: any): void {
    if (state.imageData) {
      this.loadImage(state.imageData);
    }
    
    if (state.selection) {
      this.createSelection(state.selection);
    } else {
      this.clearSelection();
    }
    
    // 레이어 복원 등...
  }

  // ======= 유틸리티 메서드 =======

  private generateActionId(): string {
    return `action-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  // ======= 내보내기 =======

  public async exportImage(options: ExportOptions): Promise<Blob> {
    console.log('💾 이미지 내보내기:', options);
    
    return new Promise((resolve, reject) => {
      try {
        const dataUrl = this.stage.toDataURL({
          mimeType: options.format === 'jpg' ? 'image/jpeg' : `image/${options.format}`,
          quality: options.quality ? options.quality / 100 : 1,
          width: options.width,
          height: options.height,
          pixelRatio: window.devicePixelRatio || 1
        });
        
        // dataURL을 Blob으로 변환
        fetch(dataUrl)
          .then(res => res.blob())
          .then(blob => {
            console.log('✅ 이미지 내보내기 완료');
            resolve(blob);
          })
          .catch(reject);
          
      } catch (error) {
        console.error('❌ 이미지 내보내기 실패:', error);
        reject(error);
      }
    });
  }

  // ======= 아직 구현되지 않은 메서드들 (기본 구현) =======

  public transform(matrix: TransformMatrix): void {
    console.log('🔄 변형 적용:', matrix);
    // TODO: 매트릭스 변형 구현
  }

  public rotate(angle: number): void {
    console.log('🔄 회전:', angle);
    // TODO: 회전 구현
  }

  public resize(width: number, height: number): void {
    console.log('📏 크기 조정:', width, height);
    // TODO: 크기 조정 구현
  }

  public applyFilter(filter: ImageFilter, params: Record<string, any>): void {
    console.log('🎨 필터 적용:', filter.name);
    // TODO: 필터 적용 구현
  }

  public removeFilter(filterId: string): void {
    console.log('🚫 필터 제거:', filterId);
    // TODO: 필터 제거 구현
  }

  public createLayer(type: EditingLayer['type']): EditingLayer {
    const layer: EditingLayer = {
      id: this.generateActionId(),
      name: `${type} Layer`,
      type,
      visible: true,
      opacity: 100,
      blendMode: 'normal',
      locked: false,
      effects: []
    };
    
    this.editingLayers.set(layer.id, layer);
    console.log('➕ 레이어 생성:', layer.name);
    
    return layer;
  }

  public deleteLayer(layerId: string): void {
    this.editingLayers.delete(layerId);
    console.log('🗑️ 레이어 삭제:', layerId);
  }

  public mergeDown(layerId: string): void {
    console.log('⬇️ 레이어 병합:', layerId);
    // TODO: 레이어 병합 구현
  }

  // ======= 정리 =======

  public destroy(): void {
    console.log('💀 AdvancedImageEditingEngine 정리 시작');
    
    if (this.renderTimeout) {
      clearTimeout(this.renderTimeout);
    }
    
    this.stage.destroy();
    this.layers.clear();
    this.editingLayers.clear();
    this.eventListeners.clear();
    
    console.log('✅ AdvancedImageEditingEngine 정리 완료');
  }
}