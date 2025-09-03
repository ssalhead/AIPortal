/**
 * GraphicsToolsEngine v1.0 - 텍스트 및 그래픽 도구 엔진
 * 
 * 특징:
 * - 고급 텍스트 편집 (폰트, 스타일, 효과)
 * - 벡터 도형 도구 (원, 사각형, 화살표, 자유형)
 * - 브러시 및 페인팅 도구
 * - 스티커 및 이모티콘 시스템
 * - 워터마크 및 로고 추가
 * - 레이어 기반 편집
 */

import Konva from 'konva';
import type { 
  BrushSettings,
  BlendMode,
  EditingLayer
} from '../types/imageEditing';

// ======= 텍스트 도구 타입 =======

export interface TextStyle {
  fontFamily: string;
  fontSize: number;
  fontWeight: 'normal' | 'bold' | '100' | '200' | '300' | '400' | '500' | '600' | '700' | '800' | '900';
  fontStyle: 'normal' | 'italic' | 'oblique';
  textDecoration: 'none' | 'underline' | 'line-through' | 'overline';
  color: string;
  backgroundColor: string;
  opacity: number;
  letterSpacing: number;
  lineHeight: number;
  textAlign: 'left' | 'center' | 'right' | 'justify';
  verticalAlign: 'top' | 'middle' | 'bottom';
  padding: number;
  borderRadius: number;
  shadow: TextShadow | null;
  stroke: TextStroke | null;
  gradient: TextGradient | null;
}

export interface TextShadow {
  offsetX: number;
  offsetY: number;
  blur: number;
  color: string;
}

export interface TextStroke {
  width: number;
  color: string;
}

export interface TextGradient {
  type: 'linear' | 'radial';
  colors: string[];
  stops: number[];
  angle?: number; // linear용
  centerX?: number; // radial용
  centerY?: number; // radial용
  radius?: number; // radial용
}

// ======= 도형 도구 타입 =======

export type ShapeType = 
  | 'rectangle'
  | 'circle'
  | 'ellipse'
  | 'triangle'
  | 'pentagon'
  | 'hexagon'
  | 'star'
  | 'arrow'
  | 'line'
  | 'curve'
  | 'polygon'
  | 'heart'
  | 'diamond';

export interface ShapeStyle {
  fill: string;
  stroke: string;
  strokeWidth: number;
  strokeDashArray: number[];
  opacity: number;
  cornerRadius?: number; // rectangle용
  innerRadius?: number; // star용
  numPoints?: number; // star, polygon용
  startAngle?: number; // arc, star용
  endAngle?: number; // arc용
  gradient?: ShapeGradient | null;
  shadow?: ShapeShadow | null;
}

export interface ShapeGradient {
  type: 'linear' | 'radial';
  colors: string[];
  stops: number[];
  angle?: number;
  centerX?: number;
  centerY?: number;
  radius?: number;
}

export interface ShapeShadow {
  offsetX: number;
  offsetY: number;
  blur: number;
  color: string;
}

// ======= 브러시 도구 타입 =======

export type BrushType = 
  | 'round'        // 둥근 브러시
  | 'square'       // 사각 브러시
  | 'texture'      // 텍스처 브러시
  | 'spray'        // 에어브러시
  | 'calligraphy'  // 캘리그래피
  | 'marker'       // 마커
  | 'pencil'       // 연필
  | 'charcoal';    // 차콜

export interface BrushStroke {
  id: string;
  type: BrushType;
  points: number[]; // x, y, pressure 반복
  settings: BrushSettings;
  timestamp: number;
}

// ======= 스티커 시스템 타입 =======

export interface Sticker {
  id: string;
  name: string;
  category: 'emoji' | 'decoration' | 'frame' | 'badge' | 'custom';
  url: string;
  width: number;
  height: number;
  tags: string[];
  animated?: boolean;
}

export interface StickerCategory {
  id: string;
  name: string;
  icon: string;
  stickers: Sticker[];
}

// ======= 메인 그래픽스 엔진 =======

export class GraphicsToolsEngine {
  // Konva 관련
  private stage: Konva.Stage;
  private layers: Map<string, Konva.Layer> = new Map();
  
  // 도구 상태
  private currentTool: 'text' | 'shape' | 'brush' | 'sticker' = 'text';
  private isDrawing: boolean = false;
  private currentStroke: BrushStroke | null = null;
  
  // 스타일 설정
  private textStyle: TextStyle;
  private shapeStyle: ShapeStyle;
  private brushSettings: BrushSettings;
  
  // 스티커 시스템
  private stickerCategories: Map<string, StickerCategory> = new Map();
  private loadedStickers: Map<string, HTMLImageElement> = new Map();
  
  // 활성 요소 관리
  private activeElements: Map<string, Konva.Node> = new Map();
  private transformer: Konva.Transformer;
  
  // 이벤트 시스템
  private eventListeners: Map<string, Function[]> = new Map();
  
  // 성능 설정
  private enableOptimizations: boolean = true;
  private maxBrushPoints: number = 1000;

  constructor(container: HTMLDivElement, width: number = 1200, height: number = 800) {
    console.log('🎨 GraphicsToolsEngine 초기화 시작');
    
    // Konva Stage 초기화
    this.stage = new Konva.Stage({
      container,
      width,
      height,
      draggable: false
    });
    
    // 레이어 초기화
    this.initializeLayers();
    
    // 기본 스타일 설정
    this.initializeStyles();
    
    // Transformer 초기화
    this.initializeTransformer();
    
    // 이벤트 핸들러 설정
    this.setupEventHandlers();
    
    // 스티커 시스템 초기화
    this.initializeStickerSystem();
    
    console.log('✅ GraphicsToolsEngine 초기화 완료');
  }

  // ======= 초기화 메서드 =======

  private initializeLayers(): void {
    const layerConfigs = [
      { name: 'background', listening: false },
      { name: 'shapes', listening: true },
      { name: 'brush-strokes', listening: false },
      { name: 'text', listening: true },
      { name: 'stickers', listening: true },
      { name: 'ui', listening: true }
    ];

    layerConfigs.forEach(config => {
      const layer = new Konva.Layer({
        name: config.name,
        listening: config.listening
      });
      this.layers.set(config.name, layer);
      this.stage.add(layer);
    });

    this.stage.draw();
  }

  private initializeStyles(): void {
    // 기본 텍스트 스타일
    this.textStyle = {
      fontFamily: 'Inter, Arial, sans-serif',
      fontSize: 24,
      fontWeight: 'normal',
      fontStyle: 'normal',
      textDecoration: 'none',
      color: '#000000',
      backgroundColor: 'transparent',
      opacity: 1,
      letterSpacing: 0,
      lineHeight: 1.2,
      textAlign: 'left',
      verticalAlign: 'middle',
      padding: 10,
      borderRadius: 0,
      shadow: null,
      stroke: null,
      gradient: null
    };

    // 기본 도형 스타일
    this.shapeStyle = {
      fill: '#3B82F6',
      stroke: '#1E40AF',
      strokeWidth: 2,
      strokeDashArray: [],
      opacity: 1,
      cornerRadius: 0,
      gradient: null,
      shadow: null
    };

    // 기본 브러시 설정
    this.brushSettings = {
      size: 10,
      hardness: 80,
      opacity: 100,
      flow: 100,
      spacing: 25,
      pressure: false,
      color: '#000000',
      blendMode: 'normal'
    };
  }

  private initializeTransformer(): void {
    this.transformer = new Konva.Transformer({
      enabledAnchors: ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'middle-left', 'middle-right', 'top-center', 'bottom-center'],
      boundBoxFunc: (oldBox, newBox) => {
        if (newBox.width < 10 || newBox.height < 10) {
          return oldBox;
        }
        return newBox;
      }
    });

    const uiLayer = this.layers.get('ui');
    if (uiLayer) {
      uiLayer.add(this.transformer);
    }
  }

  // ======= 텍스트 도구 =======

  public addText(x: number, y: number, text: string = '텍스트를 입력하세요'): string {
    console.log(`📝 텍스트 추가: "${text}" at (${x}, ${y})`);
    
    const textId = this.generateElementId('text');
    
    // 텍스트 노드 생성
    const textNode = new Konva.Text({
      id: textId,
      x,
      y,
      text,
      fontSize: this.textStyle.fontSize,
      fontFamily: this.textStyle.fontFamily,
      fontStyle: this.getFontStyle(),
      textDecoration: this.textStyle.textDecoration,
      fill: this.textStyle.color,
      opacity: this.textStyle.opacity,
      align: this.textStyle.textAlign,
      verticalAlign: this.textStyle.verticalAlign,
      padding: this.textStyle.padding,
      lineHeight: this.textStyle.lineHeight,
      letterSpacing: this.textStyle.letterSpacing,
      draggable: true
    });

    // 배경색 적용 (필요시)
    if (this.textStyle.backgroundColor && this.textStyle.backgroundColor !== 'transparent') {
      const background = new Konva.Rect({
        x: textNode.x(),
        y: textNode.y(),
        width: textNode.width(),
        height: textNode.height(),
        fill: this.textStyle.backgroundColor,
        cornerRadius: this.textStyle.borderRadius
      });

      const group = new Konva.Group({
        id: textId,
        draggable: true
      });
      group.add(background);
      group.add(textNode);

      this.addTextEffects(textNode);
      
      const textLayer = this.layers.get('text');
      if (textLayer) {
        textLayer.add(group);
        textLayer.draw();
      }
      
      this.activeElements.set(textId, group);
      this.setupElementEvents(group, textId);
      
      return textId;
    }

    // 텍스트 효과 적용
    this.addTextEffects(textNode);

    // 레이어에 추가
    const textLayer = this.layers.get('text');
    if (textLayer) {
      textLayer.add(textNode);
      textLayer.draw();
    }

    this.activeElements.set(textId, textNode);
    this.setupElementEvents(textNode, textId);

    this.emit('text-added', { id: textId, text, x, y });
    return textId;
  }

  private getFontStyle(): string {
    const weight = this.textStyle.fontWeight === 'bold' || parseInt(this.textStyle.fontWeight) > 500 ? 'bold' : 'normal';
    const style = this.textStyle.fontStyle;
    return style === 'italic' ? (weight === 'bold' ? 'bold italic' : 'italic') : weight;
  }

  private addTextEffects(textNode: Konva.Text): void {
    const effects: Konva.Filter[] = [];

    // 그림자 효과
    if (this.textStyle.shadow) {
      textNode.shadowOffsetX(this.textStyle.shadow.offsetX);
      textNode.shadowOffsetY(this.textStyle.shadow.offsetY);
      textNode.shadowBlur(this.textStyle.shadow.blur);
      textNode.shadowColor(this.textStyle.shadow.color);
    }

    // 테두리 효과
    if (this.textStyle.stroke) {
      textNode.stroke(this.textStyle.stroke.color);
      textNode.strokeWidth(this.textStyle.stroke.width);
    }

    // 그라디언트 효과
    if (this.textStyle.gradient) {
      const gradient = this.createTextGradient(textNode, this.textStyle.gradient);
      textNode.fillLinearGradientColorStops(gradient.colorStops);
      if (gradient.start && gradient.end) {
        textNode.fillLinearGradientStartPoint(gradient.start);
        textNode.fillLinearGradientEndPoint(gradient.end);
      }
    }

    if (effects.length > 0) {
      textNode.filters(effects);
      textNode.cache();
    }
  }

  private createTextGradient(textNode: Konva.Text, gradient: TextGradient) {
    const bounds = textNode.getClientRect();
    const colorStops: number[] = [];
    
    for (let i = 0; i < gradient.colors.length; i++) {
      colorStops.push(gradient.stops[i] || i / (gradient.colors.length - 1));
      colorStops.push(...this.hexToRgb(gradient.colors[i]));
    }

    let start, end;
    if (gradient.type === 'linear') {
      const angle = gradient.angle || 0;
      const angleRad = angle * Math.PI / 180;
      const diagonal = Math.sqrt(bounds.width * bounds.width + bounds.height * bounds.height);
      
      start = {
        x: bounds.width / 2 - Math.cos(angleRad) * diagonal / 2,
        y: bounds.height / 2 - Math.sin(angleRad) * diagonal / 2
      };
      end = {
        x: bounds.width / 2 + Math.cos(angleRad) * diagonal / 2,
        y: bounds.height / 2 + Math.sin(angleRad) * diagonal / 2
      };
    }

    return { colorStops, start, end };
  }

  public editText(textId: string): void {
    const textElement = this.activeElements.get(textId);
    if (!textElement) return;

    let textNode: Konva.Text;
    if (textElement instanceof Konva.Group) {
      textNode = textElement.findOne('Text') as Konva.Text;
    } else if (textElement instanceof Konva.Text) {
      textNode = textElement;
    } else {
      return;
    }

    this.createTextEditor(textNode, textId);
  }

  private createTextEditor(textNode: Konva.Text, textId: string): void {
    const stageBox = this.stage.container().getBoundingClientRect();
    const textPosition = textNode.absolutePosition();
    
    // HTML textarea 생성
    const textarea = document.createElement('textarea');
    textarea.value = textNode.text();
    textarea.style.position = 'absolute';
    textarea.style.top = (stageBox.top + textPosition.y) + 'px';
    textarea.style.left = (stageBox.left + textPosition.x) + 'px';
    textarea.style.width = Math.max(textNode.width(), 100) + 'px';
    textarea.style.height = Math.max(textNode.height(), 30) + 'px';
    textarea.style.fontSize = textNode.fontSize() + 'px';
    textarea.style.fontFamily = textNode.fontFamily();
    textarea.style.color = textNode.fill();
    textarea.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
    textarea.style.border = '2px solid #3B82F6';
    textarea.style.borderRadius = '4px';
    textarea.style.padding = '5px';
    textarea.style.resize = 'none';
    textarea.style.outline = 'none';
    textarea.style.zIndex = '10000';

    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();

    // 편집 완료 핸들러
    const finishEditing = () => {
      const newText = textarea.value;
      textNode.text(newText);
      textNode.getLayer()?.draw();
      
      document.body.removeChild(textarea);
      
      this.emit('text-edited', { id: textId, text: newText });
      console.log(`✏️ 텍스트 편집 완료: "${newText}"`);
    };

    textarea.addEventListener('blur', finishEditing);
    textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        finishEditing();
      } else if (e.key === 'Escape') {
        document.body.removeChild(textarea);
      }
    });
  }

  // ======= 도형 도구 =======

  public addShape(type: ShapeType, x: number, y: number, width: number = 100, height: number = 100): string {
    console.log(`🔷 도형 추가: ${type} at (${x}, ${y})`);
    
    const shapeId = this.generateElementId('shape');
    let shapeNode: Konva.Shape;

    switch (type) {
      case 'rectangle':
        shapeNode = new Konva.Rect({
          id: shapeId,
          x, y, width, height,
          cornerRadius: this.shapeStyle.cornerRadius
        });
        break;
        
      case 'circle':
        shapeNode = new Konva.Circle({
          id: shapeId,
          x: x + width/2,
          y: y + height/2,
          radius: Math.min(width, height) / 2
        });
        break;
        
      case 'ellipse':
        shapeNode = new Konva.Ellipse({
          id: shapeId,
          x: x + width/2,
          y: y + height/2,
          radiusX: width / 2,
          radiusY: height / 2
        });
        break;
        
      case 'triangle':
        shapeNode = new Konva.RegularPolygon({
          id: shapeId,
          x: x + width/2,
          y: y + height/2,
          sides: 3,
          radius: Math.min(width, height) / 2
        });
        break;
        
      case 'star':
        shapeNode = new Konva.Star({
          id: shapeId,
          x: x + width/2,
          y: y + height/2,
          numPoints: this.shapeStyle.numPoints || 5,
          innerRadius: this.shapeStyle.innerRadius || Math.min(width, height) / 4,
          outerRadius: Math.min(width, height) / 2
        });
        break;
        
      case 'arrow':
        shapeNode = this.createArrowShape(shapeId, x, y, width, height);
        break;
        
      case 'heart':
        shapeNode = this.createHeartShape(shapeId, x, y, width, height);
        break;
        
      default:
        console.warn(`⚠️ 지원하지 않는 도형 타입: ${type}`);
        return '';
    }

    // 스타일 적용
    this.applyShapeStyle(shapeNode);
    
    // 드래그 가능하게 설정
    shapeNode.draggable(true);

    // 레이어에 추가
    const shapesLayer = this.layers.get('shapes');
    if (shapesLayer) {
      shapesLayer.add(shapeNode);
      shapesLayer.draw();
    }

    this.activeElements.set(shapeId, shapeNode);
    this.setupElementEvents(shapeNode, shapeId);

    this.emit('shape-added', { id: shapeId, type, x, y, width, height });
    return shapeId;
  }

  private createArrowShape(id: string, x: number, y: number, width: number, height: number): Konva.Shape {
    const arrowPoints = [
      0, height/2,              // 시작점
      width*0.7, height/2,      // 화살대 끝
      width*0.7, height*0.2,    // 화살촉 위
      width, height/2,          // 화살촉 끝
      width*0.7, height*0.8,    // 화살촉 아래
      width*0.7, height/2       // 화살대 시작
    ];

    return new Konva.Line({
      id,
      x,
      y,
      points: arrowPoints,
      closed: true
    });
  }

  private createHeartShape(id: string, x: number, y: number, width: number, height: number): Konva.Shape {
    // 베지어 곡선을 사용한 하트 모양
    const centerX = width / 2;
    const centerY = height / 3;

    return new Konva.Path({
      id,
      x,
      y,
      data: `M${centerX},${height*0.8} 
             C${centerX},${height*0.8} ${0},${centerY} ${0},${centerY*0.7}
             C${0},${centerY*0.5} ${centerX*0.5},${centerY*0.5} ${centerX},${centerY}
             C${centerX*1.5},${centerY*0.5} ${width},${centerY*0.5} ${width},${centerY*0.7}
             C${width},${centerY} ${centerX},${height*0.8} ${centerX},${height*0.8} Z`
    });
  }

  private applyShapeStyle(shapeNode: Konva.Shape): void {
    shapeNode.fill(this.shapeStyle.fill);
    shapeNode.stroke(this.shapeStyle.stroke);
    shapeNode.strokeWidth(this.shapeStyle.strokeWidth);
    shapeNode.opacity(this.shapeStyle.opacity);
    
    if (this.shapeStyle.strokeDashArray.length > 0) {
      shapeNode.dash(this.shapeStyle.strokeDashArray);
    }

    // 그라디언트 적용
    if (this.shapeStyle.gradient) {
      this.applyShapeGradient(shapeNode, this.shapeStyle.gradient);
    }

    // 그림자 적용
    if (this.shapeStyle.shadow) {
      shapeNode.shadowOffsetX(this.shapeStyle.shadow.offsetX);
      shapeNode.shadowOffsetY(this.shapeStyle.shadow.offsetY);
      shapeNode.shadowBlur(this.shapeStyle.shadow.blur);
      shapeNode.shadowColor(this.shapeStyle.shadow.color);
    }
  }

  private applyShapeGradient(shapeNode: Konva.Shape, gradient: ShapeGradient): void {
    const bounds = shapeNode.getClientRect();
    const colorStops: number[] = [];
    
    for (let i = 0; i < gradient.colors.length; i++) {
      colorStops.push(gradient.stops[i] || i / (gradient.colors.length - 1));
      colorStops.push(...this.hexToRgb(gradient.colors[i]));
    }

    if (gradient.type === 'linear') {
      const angle = gradient.angle || 0;
      const angleRad = angle * Math.PI / 180;
      
      shapeNode.fillLinearGradientColorStops(colorStops);
      shapeNode.fillLinearGradientStartPoint({
        x: bounds.width / 2 - Math.cos(angleRad) * bounds.width / 2,
        y: bounds.height / 2 - Math.sin(angleRad) * bounds.height / 2
      });
      shapeNode.fillLinearGradientEndPoint({
        x: bounds.width / 2 + Math.cos(angleRad) * bounds.width / 2,
        y: bounds.height / 2 + Math.sin(angleRad) * bounds.height / 2
      });
    } else if (gradient.type === 'radial') {
      shapeNode.fillRadialGradientColorStops(colorStops);
      shapeNode.fillRadialGradientStartPoint({
        x: gradient.centerX || bounds.width / 2,
        y: gradient.centerY || bounds.height / 2
      });
      shapeNode.fillRadialGradientEndPoint({
        x: gradient.centerX || bounds.width / 2,
        y: gradient.centerY || bounds.height / 2
      });
      shapeNode.fillRadialGradientStartRadius(0);
      shapeNode.fillRadialGradientEndRadius(gradient.radius || Math.min(bounds.width, bounds.height) / 2);
    }
  }

  // ======= 브러시 도구 =======

  public startBrushStroke(x: number, y: number, pressure: number = 1): void {
    if (this.isDrawing) return;

    console.log(`🖌️ 브러시 스트로크 시작: (${x}, ${y})`);
    
    this.isDrawing = true;
    this.currentStroke = {
      id: this.generateElementId('brush'),
      type: 'round', // 기본값
      points: [x, y, pressure],
      settings: { ...this.brushSettings },
      timestamp: Date.now()
    };

    this.emit('brush-stroke-started', this.currentStroke);
  }

  public continueBrushStroke(x: number, y: number, pressure: number = 1): void {
    if (!this.isDrawing || !this.currentStroke) return;

    // 포인트 추가
    this.currentStroke.points.push(x, y, pressure);

    // 성능 최적화: 포인트 수 제한
    if (this.enableOptimizations && this.currentStroke.points.length > this.maxBrushPoints * 3) {
      // 포인트 간소화
      this.currentStroke.points = this.simplifyPoints(this.currentStroke.points);
    }

    // 실시간 렌더링
    this.renderCurrentBrushStroke();
  }

  public endBrushStroke(): void {
    if (!this.isDrawing || !this.currentStroke) return;

    console.log(`🖌️ 브러시 스트로크 완료: ${this.currentStroke.points.length / 3}개 포인트`);
    
    // 최종 브러시 스트로크 렌더링
    const strokeNode = this.createBrushStrokeNode(this.currentStroke);
    
    const brushLayer = this.layers.get('brush-strokes');
    if (brushLayer) {
      brushLayer.add(strokeNode);
      brushLayer.draw();
    }

    this.activeElements.set(this.currentStroke.id, strokeNode);
    
    this.emit('brush-stroke-completed', this.currentStroke);
    
    // 상태 리셋
    this.isDrawing = false;
    this.currentStroke = null;
  }

  private renderCurrentBrushStroke(): void {
    if (!this.currentStroke) return;

    // 임시 렌더링을 위한 캔버스 사용
    // 실제 구현에서는 성능 최적화된 방법 사용
    this.drawBrushPreview(this.currentStroke);
  }

  private createBrushStrokeNode(stroke: BrushStroke): Konva.Line {
    const line = new Konva.Line({
      id: stroke.id,
      points: this.convertBrushPointsToKonva(stroke.points),
      stroke: stroke.settings.color,
      strokeWidth: stroke.settings.size,
      opacity: stroke.settings.opacity / 100,
      lineCap: 'round',
      lineJoin: 'round',
      tension: 0.5
    });

    // 브러시 타입에 따른 추가 설정
    this.applyBrushEffects(line, stroke);

    return line;
  }

  private convertBrushPointsToKonva(points: number[]): number[] {
    const konvaPoints: number[] = [];
    for (let i = 0; i < points.length; i += 3) {
      konvaPoints.push(points[i], points[i + 1]);
    }
    return konvaPoints;
  }

  private applyBrushEffects(line: Konva.Line, stroke: BrushStroke): void {
    const effects: Konva.Filter[] = [];

    // 압력 감지 효과
    if (stroke.settings.pressure && stroke.points.length >= 9) {
      // 압력에 따른 선 두께 변화 구현
      // 실제로는 더 복잡한 압력 처리 필요
    }

    // 블렌드 모드 적용
    if (stroke.settings.blendMode !== 'normal') {
      line.globalCompositeOperation(this.getKonvaBlendMode(stroke.settings.blendMode));
    }

    if (effects.length > 0) {
      line.filters(effects);
      line.cache();
    }
  }

  private getKonvaBlendMode(blendMode: BlendMode): GlobalCompositeOperation {
    const blendModeMap: Record<BlendMode, GlobalCompositeOperation> = {
      'normal': 'source-over',
      'multiply': 'multiply',
      'screen': 'screen',
      'overlay': 'overlay',
      'soft-light': 'soft-light',
      'hard-light': 'hard-light',
      'color-dodge': 'color-dodge',
      'color-burn': 'color-burn',
      'darken': 'darken',
      'lighten': 'lighten',
      'difference': 'difference',
      'exclusion': 'exclusion'
    };

    return blendModeMap[blendMode] || 'source-over';
  }

  private simplifyPoints(points: number[]): number[] {
    // Douglas-Peucker 알고리즘의 간단한 버전
    const simplified: number[] = [];
    const tolerance = 2;

    for (let i = 0; i < points.length; i += 3) {
      if (i === 0 || i >= points.length - 3) {
        // 첫 점과 마지막 점은 항상 유지
        simplified.push(points[i], points[i + 1], points[i + 2]);
      } else {
        // 이전 점과의 거리 체크
        const prevX = simplified[simplified.length - 3];
        const prevY = simplified[simplified.length - 2];
        const distance = Math.sqrt(
          Math.pow(points[i] - prevX, 2) + 
          Math.pow(points[i + 1] - prevY, 2)
        );
        
        if (distance > tolerance) {
          simplified.push(points[i], points[i + 1], points[i + 2]);
        }
      }
    }

    return simplified;
  }

  private drawBrushPreview(stroke: BrushStroke): void {
    // 실시간 브러시 프리뷰 렌더링
    // 성능을 위해 최소한의 포인트만 사용
    const recentPoints = stroke.points.slice(-30); // 최근 10개 포인트만
    
    if (recentPoints.length >= 6) {
      // 임시 라인 그리기
      const previewLine = new Konva.Line({
        points: this.convertBrushPointsToKonva(recentPoints),
        stroke: stroke.settings.color,
        strokeWidth: stroke.settings.size,
        opacity: stroke.settings.opacity / 100 * 0.7, // 프리뷰는 약간 투명
        lineCap: 'round',
        lineJoin: 'round'
      });

      // UI 레이어에 임시 추가
      const uiLayer = this.layers.get('ui');
      if (uiLayer) {
        // 기존 프리뷰 제거
        uiLayer.find('.brush-preview').destroy();
        
        previewLine.name('brush-preview');
        uiLayer.add(previewLine);
        uiLayer.draw();
      }
    }
  }

  // ======= 스티커 시스템 =======

  private async initializeStickerSystem(): Promise<void> {
    console.log('🌟 스티커 시스템 초기화');
    
    // 기본 이모지 스티커들
    const emojiStickers: Sticker[] = [
      { id: 'emoji-smile', name: '😀', category: 'emoji', url: '', width: 64, height: 64, tags: ['happy', 'smile'] },
      { id: 'emoji-heart', name: '❤️', category: 'emoji', url: '', width: 64, height: 64, tags: ['love', 'heart'] },
      { id: 'emoji-fire', name: '🔥', category: 'emoji', url: '', width: 64, height: 64, tags: ['hot', 'fire'] },
      { id: 'emoji-star', name: '⭐', category: 'emoji', url: '', width: 64, height: 64, tags: ['star', 'favorite'] }
    ];

    const emojiCategory: StickerCategory = {
      id: 'emoji',
      name: '이모지',
      icon: '😀',
      stickers: emojiStickers
    };

    this.stickerCategories.set('emoji', emojiCategory);

    // 장식 스티커들 (실제 환경에서는 서버에서 로드)
    await this.loadDecorationStickers();
  }

  private async loadDecorationStickers(): Promise<void> {
    // 실제 환경에서는 서버 API에서 스티커 목록을 가져옴
    const decorationStickers: Sticker[] = [
      { id: 'star-1', name: '별 1', category: 'decoration', url: '/stickers/star1.png', width: 100, height: 100, tags: ['star', 'decoration'] },
      { id: 'frame-1', name: '프레임 1', category: 'frame', url: '/stickers/frame1.png', width: 200, height: 200, tags: ['frame', 'border'] }
    ];

    const decorationCategory: StickerCategory = {
      id: 'decoration',
      name: '장식',
      icon: '✨',
      stickers: decorationStickers
    };

    this.stickerCategories.set('decoration', decorationCategory);
  }

  public async addSticker(stickerId: string, x: number, y: number): Promise<string | null> {
    console.log(`🌟 스티커 추가: ${stickerId} at (${x}, ${y})`);
    
    const sticker = this.findStickerById(stickerId);
    if (!sticker) {
      console.error(`❌ 스티커를 찾을 수 없습니다: ${stickerId}`);
      return null;
    }

    const elementId = this.generateElementId('sticker');

    if (sticker.category === 'emoji') {
      // 이모지 스티커는 텍스트로 처리
      return this.addEmojiSticker(elementId, sticker, x, y);
    } else {
      // 이미지 스티커 처리
      return await this.addImageSticker(elementId, sticker, x, y);
    }
  }

  private addEmojiSticker(elementId: string, sticker: Sticker, x: number, y: number): string {
    const emojiText = new Konva.Text({
      id: elementId,
      x,
      y,
      text: sticker.name,
      fontSize: sticker.height,
      draggable: true
    });

    const stickersLayer = this.layers.get('stickers');
    if (stickersLayer) {
      stickersLayer.add(emojiText);
      stickersLayer.draw();
    }

    this.activeElements.set(elementId, emojiText);
    this.setupElementEvents(emojiText, elementId);

    this.emit('sticker-added', { id: elementId, stickerId: sticker.id, x, y });
    return elementId;
  }

  private async addImageSticker(elementId: string, sticker: Sticker, x: number, y: number): Promise<string | null> {
    try {
      // 이미지 로드
      const imageElement = await this.loadStickerImage(sticker);
      
      const stickerImage = new Konva.Image({
        id: elementId,
        x,
        y,
        image: imageElement,
        width: sticker.width,
        height: sticker.height,
        draggable: true
      });

      const stickersLayer = this.layers.get('stickers');
      if (stickersLayer) {
        stickersLayer.add(stickerImage);
        stickersLayer.draw();
      }

      this.activeElements.set(elementId, stickerImage);
      this.setupElementEvents(stickerImage, elementId);

      this.emit('sticker-added', { id: elementId, stickerId: sticker.id, x, y });
      return elementId;
      
    } catch (error) {
      console.error(`❌ 스티커 이미지 로드 실패: ${sticker.id}`, error);
      return null;
    }
  }

  private async loadStickerImage(sticker: Sticker): Promise<HTMLImageElement> {
    // 캐시 확인
    if (this.loadedStickers.has(sticker.id)) {
      return this.loadedStickers.get(sticker.id)!;
    }

    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        this.loadedStickers.set(sticker.id, img);
        resolve(img);
      };
      img.onerror = () => reject(new Error(`스티커 이미지 로드 실패: ${sticker.url}`));
      img.src = sticker.url;
    });
  }

  private findStickerById(stickerId: string): Sticker | null {
    for (const category of this.stickerCategories.values()) {
      const sticker = category.stickers.find(s => s.id === stickerId);
      if (sticker) return sticker;
    }
    return null;
  }

  // ======= 워터마크 및 로고 =======

  public async addWatermark(
    imageUrl: string, 
    position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center',
    opacity: number = 0.5,
    scale: number = 1
  ): Promise<string | null> {
    console.log(`🏷️ 워터마크 추가: ${position}, 투명도: ${opacity}`);
    
    try {
      const watermarkImage = await this.loadImage(imageUrl);
      const elementId = this.generateElementId('watermark');
      
      // 위치 계산
      const stageWidth = this.stage.width();
      const stageHeight = this.stage.height();
      const watermarkWidth = watermarkImage.width * scale;
      const watermarkHeight = watermarkImage.height * scale;
      
      let x: number, y: number;
      const margin = 20;
      
      switch (position) {
        case 'top-left':
          x = margin;
          y = margin;
          break;
        case 'top-right':
          x = stageWidth - watermarkWidth - margin;
          y = margin;
          break;
        case 'bottom-left':
          x = margin;
          y = stageHeight - watermarkHeight - margin;
          break;
        case 'bottom-right':
          x = stageWidth - watermarkWidth - margin;
          y = stageHeight - watermarkHeight - margin;
          break;
        case 'center':
          x = (stageWidth - watermarkWidth) / 2;
          y = (stageHeight - watermarkHeight) / 2;
          break;
        default:
          x = margin;
          y = margin;
      }
      
      const watermarkNode = new Konva.Image({
        id: elementId,
        x,
        y,
        image: watermarkImage,
        width: watermarkWidth,
        height: watermarkHeight,
        opacity,
        draggable: true
      });

      const stickersLayer = this.layers.get('stickers');
      if (stickersLayer) {
        stickersLayer.add(watermarkNode);
        stickersLayer.draw();
      }

      this.activeElements.set(elementId, watermarkNode);
      this.setupElementEvents(watermarkNode, elementId);

      this.emit('watermark-added', { id: elementId, position, opacity, scale });
      return elementId;
      
    } catch (error) {
      console.error('❌ 워터마크 추가 실패:', error);
      return null;
    }
  }

  private async loadImage(url: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error(`이미지 로드 실패: ${url}`));
      img.src = url;
    });
  }

  // ======= 요소 관리 =======

  private setupElementEvents(element: Konva.Node, elementId: string): void {
    // 클릭 이벤트
    element.on('click', () => {
      this.selectElement(elementId);
    });

    // 드래그 이벤트
    element.on('dragend', () => {
      this.emit('element-moved', {
        id: elementId,
        x: element.x(),
        y: element.y()
      });
    });

    // 더블클릭 이벤트 (텍스트 편집용)
    element.on('dblclick', () => {
      if (element instanceof Konva.Text || 
          (element instanceof Konva.Group && element.findOne('Text'))) {
        this.editText(elementId);
      }
    });
  }

  public selectElement(elementId: string): void {
    const element = this.activeElements.get(elementId);
    if (!element) return;

    this.transformer.nodes([element]);
    this.transformer.getLayer()?.draw();

    this.emit('element-selected', { id: elementId });
    console.log(`🎯 요소 선택됨: ${elementId}`);
  }

  public deleteElement(elementId: string): void {
    const element = this.activeElements.get(elementId);
    if (!element) return;

    element.destroy();
    element.getLayer()?.draw();
    
    this.activeElements.delete(elementId);
    
    // Transformer에서도 제거
    if (this.transformer.nodes().includes(element)) {
      this.transformer.nodes([]);
      this.transformer.getLayer()?.draw();
    }

    this.emit('element-deleted', { id: elementId });
    console.log(`🗑️ 요소 삭제됨: ${elementId}`);
  }

  public clearSelection(): void {
    this.transformer.nodes([]);
    this.transformer.getLayer()?.draw();
    this.emit('selection-cleared');
  }

  // ======= 스타일 설정 =======

  public setTextStyle(style: Partial<TextStyle>): void {
    this.textStyle = { ...this.textStyle, ...style };
    this.emit('text-style-changed', this.textStyle);
    console.log('✏️ 텍스트 스타일 업데이트:', style);
  }

  public setShapeStyle(style: Partial<ShapeStyle>): void {
    this.shapeStyle = { ...this.shapeStyle, ...style };
    this.emit('shape-style-changed', this.shapeStyle);
    console.log('🔷 도형 스타일 업데이트:', style);
  }

  public setBrushSettings(settings: Partial<BrushSettings>): void {
    this.brushSettings = { ...this.brushSettings, ...settings };
    this.emit('brush-settings-changed', this.brushSettings);
    console.log('🖌️ 브러시 설정 업데이트:', settings);
  }

  // ======= 유틸리티 메서드 =======

  private generateElementId(type: string): string {
    return `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private hexToRgb(hex: string): [number, number, number] {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? [
      parseInt(result[1], 16),
      parseInt(result[2], 16),
      parseInt(result[3], 16)
    ] : [0, 0, 0];
  }

  // ======= 이벤트 핸들러 설정 =======

  private setupEventHandlers(): void {
    // 스테이지 클릭 - 선택 해제
    this.stage.on('click tap', (e) => {
      if (e.target === this.stage) {
        this.clearSelection();
      }
    });

    // 브러시 도구 이벤트
    this.stage.on('mousedown touchstart', (e) => {
      if (this.currentTool === 'brush') {
        const pos = this.stage.getPointerPosition();
        if (pos) {
          this.startBrushStroke(pos.x, pos.y);
        }
      }
    });

    this.stage.on('mousemove touchmove', (e) => {
      if (this.currentTool === 'brush' && this.isDrawing) {
        const pos = this.stage.getPointerPosition();
        if (pos) {
          this.continueBrushStroke(pos.x, pos.y);
        }
      }
    });

    this.stage.on('mouseup touchend', () => {
      if (this.currentTool === 'brush' && this.isDrawing) {
        this.endBrushStroke();
      }
    });
  }

  // ======= 공개 API =======

  public setCurrentTool(tool: 'text' | 'shape' | 'brush' | 'sticker'): void {
    this.currentTool = tool;
    console.log(`🛠️ 활성 도구 변경: ${tool}`);
    this.emit('current-tool-changed', { tool });
  }

  public getCurrentTool(): string {
    return this.currentTool;
  }

  public getStickerCategories(): StickerCategory[] {
    return Array.from(this.stickerCategories.values());
  }

  public getAllElements(): Map<string, Konva.Node> {
    return new Map(this.activeElements);
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
    console.log('💀 GraphicsToolsEngine 정리');
    
    this.activeElements.clear();
    this.stickerCategories.clear();
    this.loadedStickers.clear();
    this.eventListeners.clear();
    
    this.isDrawing = false;
    this.currentStroke = null;
    
    this.stage.destroy();
  }
}