/**
 * InpaintingToolsEngine v1.0 - AI 기반 인페인팅 및 수정 도구
 * 
 * 특징:
 * - 스팟 힐링 브러시 (작은 결함 제거)
 * - 클론 스탬프 (영역 복사)
 * - 패치 도구 (영역 대체)
 * - AI 기반 배경 제거
 * - AI 기반 객체 제거
 * - 인페인팅 (누락된 영역 복원)
 * - 스마트 확장 (이미지 영역 확장)
 */

import type { 
  BrushSettings, 
  SelectionArea, 
  AIToolSettings 
} from '../types/imageEditing';

// ======= 인페인팅 도구 타입 =======

export type InpaintingTool = 
  | 'spot-healing'    // 스팟 힐링
  | 'clone-stamp'     // 클론 스탬프
  | 'patch-tool'      // 패치 도구
  | 'content-aware'   // 콘텐츠 인식 채우기
  | 'background-remove' // 배경 제거
  | 'object-remove'   // 객체 제거
  | 'smart-expand';   // 스마트 확장

export interface InpaintingContext {
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  radius: number;
  feathering: number;
  strength: number;
  sampleArea?: SelectionArea;
}

export interface RepairTask {
  id: string;
  tool: InpaintingTool;
  context: InpaintingContext;
  mask: ImageData;
  originalData: ImageData;
  timestamp: number;
  completed: boolean;
}

// ======= AI 서비스 인터페이스 =======

interface AIServiceConfig {
  backgroundRemoval: {
    endpoint: string;
    apiKey?: string;
    model: 'u2net' | 'silueta' | 'deep-lab';
  };
  inpainting: {
    endpoint: string;
    apiKey?: string;
    model: 'lama' | 'coherent' | 'edge-connect';
  };
  objectDetection: {
    endpoint: string;
    apiKey?: string;
    model: 'yolo' | 'coco' | 'custom';
  };
}

// ======= 메인 인페인팅 엔진 =======

export class InpaintingToolsEngine {
  // 캔버스 및 컨텍스트
  private canvas: HTMLCanvasElement;
  private context: CanvasRenderingContext2D;
  private workingCanvas: HTMLCanvasElement;
  private workingContext: CanvasRenderingContext2D;
  private maskCanvas: HTMLCanvasElement;
  private maskContext: CanvasRenderingContext2D;
  
  // 현재 도구 및 설정
  private currentTool: InpaintingTool = 'spot-healing';
  private brushSettings: BrushSettings;
  private aiSettings: AIToolSettings;
  private aiServiceConfig: AIServiceConfig;
  
  // 작업 관리
  private repairTasks: Map<string, RepairTask> = new Map();
  private isProcessing: boolean = false;
  
  // 클론 스탬프용 소스 포인트
  private cloneSource: { x: number; y: number } | null = null;
  
  // 이벤트 시스템
  private eventListeners: Map<string, Function[]> = new Map();

  constructor() {
    console.log('🔧 InpaintingToolsEngine 초기화 시작');
    
    // 캔버스들 초기화
    this.initializeCanvases();
    
    // 기본 설정 초기화
    this.initializeSettings();
    
    // AI 서비스 설정
    this.initializeAIServices();
    
    console.log('✅ InpaintingToolsEngine 초기화 완료');
  }

  // ======= 초기화 메서드 =======

  private initializeCanvases(): void {
    // 메인 작업 캔버스
    this.canvas = document.createElement('canvas');
    this.context = this.canvas.getContext('2d')!;
    
    // 임시 작업용 캔버스
    this.workingCanvas = document.createElement('canvas');
    this.workingContext = this.workingCanvas.getContext('2d')!;
    
    // 마스크용 캔버스
    this.maskCanvas = document.createElement('canvas');
    this.maskContext = this.maskCanvas.getContext('2d')!;
  }

  private initializeSettings(): void {
    this.brushSettings = {
      size: 20,
      hardness: 80,
      opacity: 100,
      flow: 100,
      spacing: 25,
      pressure: false,
      color: '#000000',
      blendMode: 'normal'
    };

    this.aiSettings = {
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

  private initializeAIServices(): void {
    // 실제 환경에서는 환경변수나 설정파일에서 로드
    this.aiServiceConfig = {
      backgroundRemoval: {
        endpoint: '/api/ai/background-removal',
        model: 'u2net'
      },
      inpainting: {
        endpoint: '/api/ai/inpainting',
        model: 'lama'
      },
      objectDetection: {
        endpoint: '/api/ai/object-detection',
        model: 'yolo'
      }
    };
  }

  // ======= 이미지 로드 =======

  public loadImage(imageData: ImageData): void {
    console.log('📸 인페인팅 이미지 로드');
    
    const { width, height } = imageData;
    
    // 모든 캔버스 크기 설정
    [this.canvas, this.workingCanvas, this.maskCanvas].forEach(canvas => {
      canvas.width = width;
      canvas.height = height;
    });
    
    // 메인 이미지 데이터 설정
    this.context.putImageData(imageData, 0, 0);
    
    // 마스크 캔버스 초기화 (투명)
    this.maskContext.clearRect(0, 0, width, height);
  }

  // ======= 스팟 힐링 브러시 =======

  public applySpotHealing(x: number, y: number, radius: number = 20): Promise<void> {
    console.log(`🎯 스팟 힐링 적용: (${x}, ${y}), 반지름: ${radius}`);
    
    return new Promise((resolve) => {
      const context: InpaintingContext = {
        sourceX: x,
        sourceY: y,
        targetX: x,
        targetY: y,
        radius,
        feathering: radius * 0.3,
        strength: 1
      };
      
      // 힐링 마스크 생성
      const mask = this.createCircularMask(x, y, radius);
      
      // 주변 텍스처 분석 및 합성
      this.performSpotHealing(context, mask);
      
      // 작업 기록
      this.recordRepairTask('spot-healing', context, mask);
      
      resolve();
    });
  }

  private createCircularMask(centerX: number, centerY: number, radius: number): ImageData {
    const diameter = radius * 2;
    const maskCanvas = document.createElement('canvas');
    maskCanvas.width = diameter;
    maskCanvas.height = diameter;
    const maskCtx = maskCanvas.getContext('2d')!;
    
    // 그라디언트 마스크 생성 (가장자리 페더링)
    const gradient = maskCtx.createRadialGradient(
      radius, radius, 0,
      radius, radius, radius
    );
    gradient.addColorStop(0, 'rgba(255,255,255,1)');
    gradient.addColorStop(0.8, 'rgba(255,255,255,1)');
    gradient.addColorStop(1, 'rgba(255,255,255,0)');
    
    maskCtx.fillStyle = gradient;
    maskCtx.fillRect(0, 0, diameter, diameter);
    
    return maskCtx.getImageData(0, 0, diameter, diameter);
  }

  private performSpotHealing(context: InpaintingContext, mask: ImageData): void {
    const { sourceX, sourceY, radius } = context;
    
    // 현재 이미지 데이터 가져오기
    const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
    
    // 힐링 영역 주변의 텍스처 샘플링
    const samples = this.sampleAroundArea(imageData, sourceX, sourceY, radius * 1.5, radius * 2.5);
    
    // 텍스처 합성으로 결함 채우기
    const healedData = this.synthesizeTexture(imageData, samples, sourceX, sourceY, radius);
    
    // 마스크를 사용하여 부드럽게 블렌딩
    this.blendWithMask(imageData, healedData, mask, sourceX - radius, sourceY - radius);
    
    // 결과 적용
    this.context.putImageData(imageData, 0, 0);
  }

  private sampleAroundArea(
    imageData: ImageData, 
    centerX: number, 
    centerY: number, 
    innerRadius: number, 
    outerRadius: number
  ): ImageData[] {
    const samples: ImageData[] = [];
    const sampleSize = 32; // 샘플 크기
    const numSamples = 16; // 샘플 개수
    
    for (let i = 0; i < numSamples; i++) {
      const angle = (i / numSamples) * 2 * Math.PI;
      const distance = innerRadius + Math.random() * (outerRadius - innerRadius);
      
      const sampleX = centerX + Math.cos(angle) * distance;
      const sampleY = centerY + Math.sin(angle) * distance;
      
      // 경계 체크
      if (sampleX >= sampleSize/2 && sampleX < this.canvas.width - sampleSize/2 &&
          sampleY >= sampleSize/2 && sampleY < this.canvas.height - sampleSize/2) {
        
        const sample = this.context.getImageData(
          sampleX - sampleSize/2,
          sampleY - sampleSize/2,
          sampleSize,
          sampleSize
        );
        samples.push(sample);
      }
    }
    
    return samples;
  }

  private synthesizeTexture(
    imageData: ImageData,
    samples: ImageData[],
    centerX: number,
    centerY: number,
    radius: number
  ): ImageData {
    const synthesized = new ImageData(radius * 2, radius * 2);
    
    // 간단한 텍스처 합성 - 가장 유사한 샘플들을 블렌딩
    for (let y = 0; y < radius * 2; y++) {
      for (let x = 0; x < radius * 2; x++) {
        let totalR = 0, totalG = 0, totalB = 0, totalA = 0;
        let totalWeight = 0;
        
        // 각 샘플에서 해당 위치의 색상을 가져와 블렌딩
        samples.forEach((sample, index) => {
          if (sample.width > x && sample.height > y) {
            const sampleIndex = (y * sample.width + x) * 4;
            const weight = 1 / (index + 1); // 거리 기반 가중치
            
            totalR += sample.data[sampleIndex] * weight;
            totalG += sample.data[sampleIndex + 1] * weight;
            totalB += sample.data[sampleIndex + 2] * weight;
            totalA += sample.data[sampleIndex + 3] * weight;
            totalWeight += weight;
          }
        });
        
        if (totalWeight > 0) {
          const outputIndex = (y * synthesized.width + x) * 4;
          synthesized.data[outputIndex] = totalR / totalWeight;
          synthesized.data[outputIndex + 1] = totalG / totalWeight;
          synthesized.data[outputIndex + 2] = totalB / totalWeight;
          synthesized.data[outputIndex + 3] = totalA / totalWeight;
        }
      }
    }
    
    return synthesized;
  }

  // ======= 클론 스탬프 =======

  public setCloneSource(x: number, y: number): void {
    this.cloneSource = { x, y };
    console.log(`📍 클론 소스 설정: (${x}, ${y})`);
    this.emit('clone-source-set', { x, y });
  }

  public applyCloneStamp(x: number, y: number, radius: number = 20): void {
    if (!this.cloneSource) {
      console.warn('⚠️ 클론 소스가 설정되지 않았습니다');
      return;
    }
    
    console.log(`📋 클론 스탬프 적용: (${x}, ${y}), 반지름: ${radius}`);
    
    const { x: sourceX, y: sourceY } = this.cloneSource;
    
    // 소스 영역에서 이미지 데이터 복사
    const sourceData = this.context.getImageData(
      sourceX - radius,
      sourceY - radius,
      radius * 2,
      radius * 2
    );
    
    // 브러시 마스크 생성
    const mask = this.createBrushMask(radius, this.brushSettings.hardness, this.brushSettings.opacity);
    
    // 마스크 적용하여 대상 영역에 합성
    this.applyCloneWithMask(sourceData, mask, x - radius, y - radius);
    
    // 작업 기록
    const context: InpaintingContext = {
      sourceX,
      sourceY,
      targetX: x,
      targetY: y,
      radius,
      feathering: radius * (100 - this.brushSettings.hardness) / 100,
      strength: this.brushSettings.opacity / 100
    };
    
    this.recordRepairTask('clone-stamp', context, mask);
  }

  private createBrushMask(radius: number, hardness: number, opacity: number): ImageData {
    const diameter = radius * 2;
    const maskCanvas = document.createElement('canvas');
    maskCanvas.width = diameter;
    maskCanvas.height = diameter;
    const maskCtx = maskCanvas.getContext('2d')!;
    
    const gradient = maskCtx.createRadialGradient(
      radius, radius, 0,
      radius, radius, radius
    );
    
    const hardnessPoint = hardness / 100;
    const alpha = opacity / 100;
    
    gradient.addColorStop(0, `rgba(255,255,255,${alpha})`);
    gradient.addColorStop(hardnessPoint, `rgba(255,255,255,${alpha})`);
    gradient.addColorStop(1, 'rgba(255,255,255,0)');
    
    maskCtx.fillStyle = gradient;
    maskCtx.fillRect(0, 0, diameter, diameter);
    
    return maskCtx.getImageData(0, 0, diameter, diameter);
  }

  private applyCloneWithMask(sourceData: ImageData, mask: ImageData, targetX: number, targetY: number): void {
    // 현재 캔버스의 대상 영역 가져오기
    const targetData = this.context.getImageData(targetX, targetY, sourceData.width, sourceData.height);
    
    // 마스크를 사용하여 소스와 대상 블렌딩
    this.blendWithMask(targetData, sourceData, mask, 0, 0);
    
    // 결과를 캔버스에 적용
    this.context.putImageData(targetData, targetX, targetY);
  }

  private blendWithMask(
    target: ImageData, 
    source: ImageData, 
    mask: ImageData, 
    offsetX: number, 
    offsetY: number
  ): void {
    for (let y = 0; y < mask.height; y++) {
      for (let x = 0; x < mask.width; x++) {
        const maskIndex = (y * mask.width + x) * 4;
        const maskAlpha = mask.data[maskIndex + 3] / 255; // 알파 값 사용
        
        const targetIndex = ((offsetY + y) * target.width + (offsetX + x)) * 4;
        const sourceIndex = (y * source.width + x) * 4;
        
        if (targetIndex >= 0 && targetIndex < target.data.length &&
            sourceIndex >= 0 && sourceIndex < source.data.length) {
          
          // 알파 블렌딩
          target.data[targetIndex] = target.data[targetIndex] * (1 - maskAlpha) + source.data[sourceIndex] * maskAlpha;
          target.data[targetIndex + 1] = target.data[targetIndex + 1] * (1 - maskAlpha) + source.data[sourceIndex + 1] * maskAlpha;
          target.data[targetIndex + 2] = target.data[targetIndex + 2] * (1 - maskAlpha) + source.data[sourceIndex + 2] * maskAlpha;
        }
      }
    }
  }

  // ======= 패치 도구 =======

  public applyPatchTool(
    sourceArea: SelectionArea,
    targetX: number,
    targetY: number
  ): Promise<void> {
    console.log('🔧 패치 도구 적용');
    
    return new Promise((resolve) => {
      // 소스 영역에서 패치 데이터 추출
      const patchData = this.extractPatchFromSelection(sourceArea);
      
      if (!patchData) {
        console.error('❌ 패치 데이터 추출 실패');
        resolve();
        return;
      }
      
      // 대상 위치에 패치 적용
      this.applyPatch(patchData, targetX, targetY);
      
      // 작업 기록
      const context: InpaintingContext = {
        sourceX: sourceArea.points[0],
        sourceY: sourceArea.points[1],
        targetX,
        targetY,
        radius: Math.max(patchData.width, patchData.height) / 2,
        feathering: 10,
        strength: 1,
        sampleArea: sourceArea
      };
      
      this.recordRepairTask('patch-tool', context, patchData);
      resolve();
    });
  }

  private extractPatchFromSelection(selection: SelectionArea): ImageData | null {
    if (selection.points.length < 4) return null;
    
    // 선택 영역의 경계 박스 계산
    let minX = selection.points[0];
    let minY = selection.points[1];
    let maxX = selection.points[0];
    let maxY = selection.points[1];
    
    for (let i = 2; i < selection.points.length; i += 2) {
      minX = Math.min(minX, selection.points[i]);
      maxX = Math.max(maxX, selection.points[i]);
      minY = Math.min(minY, selection.points[i + 1]);
      maxY = Math.max(maxY, selection.points[i + 1]);
    }
    
    const width = maxX - minX;
    const height = maxY - minY;
    
    // 경계 박스 영역 추출
    return this.context.getImageData(minX, minY, width, height);
  }

  private applyPatch(patchData: ImageData, targetX: number, targetY: number): void {
    // 페더링된 마스크 생성
    const mask = this.createFeatheredMask(patchData.width, patchData.height, 10);
    
    // 현재 캔버스의 대상 영역
    const targetData = this.context.getImageData(targetX, targetY, patchData.width, patchData.height);
    
    // 마스크를 사용하여 패치 블렌딩
    this.blendWithMask(targetData, patchData, mask, 0, 0);
    
    // 결과 적용
    this.context.putImageData(targetData, targetX, targetY);
  }

  private createFeatheredMask(width: number, height: number, featherSize: number): ImageData {
    const maskCanvas = document.createElement('canvas');
    maskCanvas.width = width;
    maskCanvas.height = height;
    const maskCtx = maskCanvas.getContext('2d')!;
    
    // 중앙은 불투명, 가장자리는 페더링
    const gradient = maskCtx.createRadialGradient(
      width / 2, height / 2, 0,
      width / 2, height / 2, Math.min(width, height) / 2
    );
    
    const featherRatio = 1 - (featherSize / Math.min(width, height));
    gradient.addColorStop(0, 'rgba(255,255,255,1)');
    gradient.addColorStop(featherRatio, 'rgba(255,255,255,1)');
    gradient.addColorStop(1, 'rgba(255,255,255,0)');
    
    maskCtx.fillStyle = gradient;
    maskCtx.fillRect(0, 0, width, height);
    
    return maskCtx.getImageData(0, 0, width, height);
  }

  // ======= AI 기반 배경 제거 =======

  public async removeBackground(): Promise<ImageData | null> {
    console.log('🤖 AI 배경 제거 시작');
    
    if (this.isProcessing) {
      console.warn('⚠️ 다른 AI 처리가 진행 중입니다');
      return null;
    }
    
    this.isProcessing = true;
    
    try {
      // 현재 이미지 데이터를 Blob으로 변환
      const imageBlob = await this.canvasToBlob();
      
      // AI 서비스에 요청
      const result = await this.callAIService('backgroundRemoval', imageBlob);
      
      if (result) {
        // 결과를 ImageData로 변환
        const resultImageData = await this.blobToImageData(result);
        
        // 캔버스에 적용
        if (resultImageData) {
          this.context.putImageData(resultImageData, 0, 0);
          this.emit('background-removed', { success: true });
          return resultImageData;
        }
      }
      
    } catch (error) {
      console.error('❌ 배경 제거 실패:', error);
      this.emit('background-removed', { success: false, error });
    } finally {
      this.isProcessing = false;
    }
    
    return null;
  }

  // ======= AI 기반 객체 제거 =======

  public async removeObject(selectionMask: ImageData): Promise<boolean> {
    console.log('🤖 AI 객체 제거 시작');
    
    if (this.isProcessing) {
      console.warn('⚠️ 다른 AI 처리가 진행 중입니다');
      return false;
    }
    
    this.isProcessing = true;
    
    try {
      // 현재 이미지와 마스크를 준비
      const imageBlob = await this.canvasToBlob();
      const maskBlob = await this.imageDataToBlob(selectionMask);
      
      // AI 인페인팅 서비스 호출
      const result = await this.callAIInpainting(imageBlob, maskBlob);
      
      if (result) {
        const resultImageData = await this.blobToImageData(result);
        
        if (resultImageData) {
          this.context.putImageData(resultImageData, 0, 0);
          this.emit('object-removed', { success: true });
          return true;
        }
      }
      
    } catch (error) {
      console.error('❌ 객체 제거 실패:', error);
      this.emit('object-removed', { success: false, error });
    } finally {
      this.isProcessing = false;
    }
    
    return false;
  }

  // ======= AI 서비스 호출 =======

  private async callAIService(service: keyof AIServiceConfig, imageBlob: Blob): Promise<Blob | null> {
    const config = this.aiServiceConfig[service];
    
    const formData = new FormData();
    formData.append('image', imageBlob);
    formData.append('model', config.model);
    
    // 서비스별 추가 파라미터
    if (service === 'backgroundRemoval') {
      formData.append('threshold', this.aiSettings.backgroundRemoval.threshold.toString());
      formData.append('smoothEdges', this.aiSettings.backgroundRemoval.smoothEdges.toString());
    }
    
    try {
      const response = await fetch(config.endpoint, {
        method: 'POST',
        body: formData,
        headers: config.apiKey ? {
          'Authorization': `Bearer ${config.apiKey}`
        } : {}
      });
      
      if (!response.ok) {
        throw new Error(`AI 서비스 오류: ${response.status}`);
      }
      
      return await response.blob();
      
    } catch (error) {
      console.error(`❌ AI 서비스 호출 실패 (${service}):`, error);
      return null;
    }
  }

  private async callAIInpainting(imageBlob: Blob, maskBlob: Blob): Promise<Blob | null> {
    const config = this.aiServiceConfig.inpainting;
    
    const formData = new FormData();
    formData.append('image', imageBlob);
    formData.append('mask', maskBlob);
    formData.append('model', config.model);
    formData.append('guidanceScale', this.aiSettings.inpainting.guidanceScale.toString());
    formData.append('iterations', this.aiSettings.inpainting.iterations.toString());
    
    try {
      const response = await fetch(config.endpoint, {
        method: 'POST',
        body: formData,
        headers: config.apiKey ? {
          'Authorization': `Bearer ${config.apiKey}`
        } : {}
      });
      
      if (!response.ok) {
        throw new Error(`인페인팅 서비스 오류: ${response.status}`);
      }
      
      return await response.blob();
      
    } catch (error) {
      console.error('❌ 인페인팅 서비스 호출 실패:', error);
      return null;
    }
  }

  // ======= 유틸리티 메서드 =======

  private async canvasToBlob(): Promise<Blob> {
    return new Promise((resolve) => {
      this.canvas.toBlob((blob) => {
        resolve(blob!);
      }, 'image/png');
    });
  }

  private async imageDataToBlob(imageData: ImageData): Promise<Blob> {
    const canvas = document.createElement('canvas');
    canvas.width = imageData.width;
    canvas.height = imageData.height;
    const ctx = canvas.getContext('2d')!;
    ctx.putImageData(imageData, 0, 0);
    
    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        resolve(blob!);
      }, 'image/png');
    });
  }

  private async blobToImageData(blob: Blob): Promise<ImageData | null> {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d')!;
        ctx.drawImage(img, 0, 0);
        resolve(ctx.getImageData(0, 0, canvas.width, canvas.height));
      };
      img.onerror = () => resolve(null);
      img.src = URL.createObjectURL(blob);
    });
  }

  // ======= 작업 기록 =======

  private recordRepairTask(
    tool: InpaintingTool, 
    context: InpaintingContext, 
    mask: ImageData
  ): void {
    const task: RepairTask = {
      id: this.generateTaskId(),
      tool,
      context,
      mask,
      originalData: this.context.getImageData(0, 0, this.canvas.width, this.canvas.height),
      timestamp: Date.now(),
      completed: true
    };
    
    this.repairTasks.set(task.id, task);
    this.emit('repair-task-completed', task);
  }

  private generateTaskId(): string {
    return `repair-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  // ======= 설정 관리 =======

  public setCurrentTool(tool: InpaintingTool): void {
    this.currentTool = tool;
    console.log(`🛠️ 인페인팅 도구 변경: ${tool}`);
    this.emit('tool-changed', { tool });
  }

  public getCurrentTool(): InpaintingTool {
    return this.currentTool;
  }

  public setBrushSettings(settings: Partial<BrushSettings>): void {
    this.brushSettings = { ...this.brushSettings, ...settings };
    console.log('🖌️ 브러시 설정 업데이트:', settings);
    this.emit('brush-settings-changed', this.brushSettings);
  }

  public setAISettings(settings: Partial<AIToolSettings>): void {
    this.aiSettings = { ...this.aiSettings, ...settings };
    console.log('🤖 AI 설정 업데이트:', settings);
    this.emit('ai-settings-changed', this.aiSettings);
  }

  // ======= 내보내기 =======

  public exportResult(): ImageData {
    return this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
  }

  public getRepairHistory(): RepairTask[] {
    return Array.from(this.repairTasks.values()).sort((a, b) => a.timestamp - b.timestamp);
  }

  // ======= 이벤트 시스템 =======

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

  // ======= 정리 =======

  public destroy(): void {
    console.log('💀 InpaintingToolsEngine 정리');
    
    this.repairTasks.clear();
    this.eventListeners.clear();
    this.cloneSource = null;
    this.isProcessing = false;
  }
}