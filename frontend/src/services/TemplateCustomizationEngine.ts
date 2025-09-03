// Template Customization Engine
// AIPortal Canvas Template Library - 템플릿 커스터마이징 엔진

import { 
  TemplateResponse, 
  TemplateDetailResponse,
  CustomizableElement,
  ColorPalette,
  TemplateCustomization,
  TemplateCustomizationSession
} from '../types/template';

// Konva 요소 타입 정의
interface KonvaElement {
  id: string;
  className: string;
  attrs: Record<string, any>;
  children?: KonvaElement[];
}

interface KonvaLayer {
  className: 'Layer';
  attrs: Record<string, any>;
  children: KonvaElement[];
}

interface KonvaStage {
  className: 'Stage';
  attrs: {
    width: number;
    height: number;
    [key: string]: any;
  };
  children: KonvaLayer[];
}

// 색상 변환 유틸리티
class ColorUtils {
  static hexToHsl(hex: string): [number, number, number] {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;

    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let h: number, s: number;
    const l = (max + min) / 2;

    if (max === min) {
      h = s = 0; // achromatic
    } else {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = (g - b) / d + (g < b ? 6 : 0); break;
        case g: h = (b - r) / d + 2; break;
        case b: h = (r - g) / d + 4; break;
        default: h = 0;
      }
      h /= 6;
    }

    return [h * 360, s * 100, l * 100];
  }

  static hslToHex(h: number, s: number, l: number): string {
    h /= 360;
    s /= 100;
    l /= 100;

    const hue2rgb = (p: number, q: number, t: number) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };

    let r: number, g: number, b: number;

    if (s === 0) {
      r = g = b = l; // achromatic
    } else {
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      r = hue2rgb(p, q, h + 1/3);
      g = hue2rgb(p, q, h);
      b = hue2rgb(p, q, h - 1/3);
    }

    const toHex = (c: number) => {
      const hex = Math.round(c * 255).toString(16);
      return hex.length === 1 ? '0' + hex : hex;
    };

    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
  }

  static generateColorVariations(baseColor: string, count: number = 5): string[] {
    const [h, s, l] = ColorUtils.hexToHsl(baseColor);
    const variations: string[] = [];

    for (let i = 0; i < count; i++) {
      const lightness = Math.max(10, Math.min(90, l + (i - count/2) * 15));
      variations.push(ColorUtils.hslToHex(h, s, lightness));
    }

    return variations;
  }

  static getContrastColor(backgroundColor: string): string {
    const [, , l] = ColorUtils.hexToHsl(backgroundColor);
    return l > 50 ? '#000000' : '#ffffff';
  }
}

// 폰트 관리 클래스
class FontManager {
  private static readonly FONT_FAMILIES = [
    'Arial', 'Helvetica', 'Georgia', 'Times New Roman', 'Verdana',
    'Tahoma', 'Trebuchet MS', 'Impact', 'Comic Sans MS', 'Palatino',
    'Garamond', 'Bookman', 'Courier New', 'Monaco', 'Lucida Console'
  ];

  private static readonly KOREAN_FONTS = [
    'Noto Sans KR', 'Nanum Gothic', 'Nanum Myeongjo', 'Malgun Gothic',
    'Dotum', 'Gulim', 'Batang', 'Gungsuh', 'Apple SD Gothic Neo'
  ];

  static getAllFonts(): string[] {
    return [...FontManager.FONT_FAMILIES, ...FontManager.KOREAN_FONTS];
  }

  static getSimilarFonts(fontFamily: string): string[] {
    const allFonts = FontManager.getAllFonts();
    
    // 현재 폰트와 유사한 카테고리 찾기
    const isSerif = ['Georgia', 'Times New Roman', 'Palatino', 'Garamond', 'Bookman', 'Batang', 'Nanum Myeongjo'].includes(fontFamily);
    const isMonospace = ['Courier New', 'Monaco', 'Lucida Console'].includes(fontFamily);
    const isKorean = FontManager.KOREAN_FONTS.includes(fontFamily);

    return allFonts.filter(font => {
      if (font === fontFamily) return false;
      
      if (isMonospace) {
        return ['Courier New', 'Monaco', 'Lucida Console'].includes(font);
      } else if (isSerif) {
        return ['Georgia', 'Times New Roman', 'Palatino', 'Garamond', 'Bookman', 'Batang', 'Nanum Myeongjo'].includes(font);
      } else if (isKorean) {
        return FontManager.KOREAN_FONTS.includes(font);
      } else {
        return !['Courier New', 'Monaco', 'Lucida Console', 'Georgia', 'Times New Roman', 'Palatino', 'Garamond', 'Bookman'].includes(font);
      }
    }).slice(0, 5);
  }
}

// 메인 커스터마이징 엔진 클래스
export class TemplateCustomizationEngine {
  private template: TemplateDetailResponse;
  private originalCanvasData: KonvaStage;
  private currentCanvasData: KonvaStage;
  private customizations: TemplateCustomization[] = [];
  private session: TemplateCustomizationSession;

  constructor(template: TemplateDetailResponse) {
    this.template = template;
    this.originalCanvasData = JSON.parse(JSON.stringify(template.canvas_data));
    this.currentCanvasData = JSON.parse(JSON.stringify(template.canvas_data));
    
    this.session = {
      template_id: template.id,
      session_id: this.generateSessionId(),
      customizations: [],
      started_at: new Date().toISOString(),
      last_updated: new Date().toISOString(),
      is_saved: false
    };
  }

  // ===== 색상 커스터마이징 =====

  /**
   * 전체 색상 팔레트 변경
   */
  changeColorPalette(newPalette: ColorPalette): KonvaStage {
    const oldColors = this.extractColorsFromCanvas();
    const colorMapping = this.createColorMapping(oldColors, newPalette.colors);

    this.currentCanvasData = this.applyColorMapping(this.currentCanvasData, colorMapping);
    
    this.addCustomization({
      element_id: 'global',
      property: 'colorPalette',
      old_value: oldColors,
      new_value: newPalette,
      timestamp: new Date().toISOString()
    });

    return this.currentCanvasData;
  }

  /**
   * 특정 요소의 색상 변경
   */
  changeElementColor(elementId: string, newColor: string): KonvaStage {
    const element = this.findElement(elementId);
    if (!element) {
      throw new Error(`Element with ID ${elementId} not found`);
    }

    const oldColor = element.attrs.fill || element.attrs.stroke || '';
    
    // 색상 속성 업데이트
    if (element.attrs.fill) {
      element.attrs.fill = newColor;
    }
    if (element.attrs.stroke) {
      element.attrs.stroke = newColor;
    }

    this.addCustomization({
      element_id: elementId,
      property: 'color',
      old_value: oldColor,
      new_value: newColor,
      timestamp: new Date().toISOString()
    });

    return this.currentCanvasData;
  }

  /**
   * 자동 색상 조화 생성
   */
  generateColorHarmony(baseColor: string, harmonyType: 'complementary' | 'triadic' | 'analogous' | 'monochromatic'): string[] {
    const [h, s, l] = ColorUtils.hexToHsl(baseColor);
    const colors: string[] = [baseColor];

    switch (harmonyType) {
      case 'complementary':
        colors.push(ColorUtils.hslToHex((h + 180) % 360, s, l));
        break;
        
      case 'triadic':
        colors.push(ColorUtils.hslToHex((h + 120) % 360, s, l));
        colors.push(ColorUtils.hslToHex((h + 240) % 360, s, l));
        break;
        
      case 'analogous':
        colors.push(ColorUtils.hslToHex((h + 30) % 360, s, l));
        colors.push(ColorUtils.hslToHex((h - 30 + 360) % 360, s, l));
        break;
        
      case 'monochromatic':
        colors.push(...ColorUtils.generateColorVariations(baseColor, 4).slice(1));
        break;
    }

    return colors;
  }

  // ===== 텍스트 커스터마이징 =====

  /**
   * 텍스트 내용 변경
   */
  changeText(elementId: string, newText: string): KonvaStage {
    const element = this.findElement(elementId);
    if (!element || element.className !== 'Text') {
      throw new Error(`Text element with ID ${elementId} not found`);
    }

    const oldText = element.attrs.text || '';
    element.attrs.text = newText;

    this.addCustomization({
      element_id: elementId,
      property: 'text',
      old_value: oldText,
      new_value: newText,
      timestamp: new Date().toISOString()
    });

    return this.currentCanvasData;
  }

  /**
   * 폰트 변경
   */
  changeFont(elementId: string, fontFamily: string): KonvaStage {
    const element = this.findElement(elementId);
    if (!element || element.className !== 'Text') {
      throw new Error(`Text element with ID ${elementId} not found`);
    }

    const oldFont = element.attrs.fontFamily || 'Arial';
    element.attrs.fontFamily = fontFamily;

    this.addCustomization({
      element_id: elementId,
      property: 'fontFamily',
      old_value: oldFont,
      new_value: fontFamily,
      timestamp: new Date().toISOString()
    });

    return this.currentCanvasData;
  }

  /**
   * 폰트 크기 변경
   */
  changeFontSize(elementId: string, fontSize: number): KonvaStage {
    const element = this.findElement(elementId);
    if (!element || element.className !== 'Text') {
      throw new Error(`Text element with ID ${elementId} not found`);
    }

    const oldSize = element.attrs.fontSize || 16;
    element.attrs.fontSize = fontSize;

    this.addCustomization({
      element_id: elementId,
      property: 'fontSize',
      old_value: oldSize,
      new_value: fontSize,
      timestamp: new Date().toISOString()
    });

    return this.currentCanvasData;
  }

  /**
   * 전체 폰트 변경
   */
  changeAllFonts(fontFamily: string): KonvaStage {
    const textElements = this.findAllTextElements();
    const changes: Array<{elementId: string, oldFont: string}> = [];

    textElements.forEach(element => {
      const oldFont = element.attrs.fontFamily || 'Arial';
      element.attrs.fontFamily = fontFamily;
      changes.push({ elementId: element.id, oldFont });
    });

    this.addCustomization({
      element_id: 'global',
      property: 'fontFamily',
      old_value: changes,
      new_value: fontFamily,
      timestamp: new Date().toISOString()
    });

    return this.currentCanvasData;
  }

  // ===== 이미지 커스터마이징 =====

  /**
   * 이미지 교체
   */
  changeImage(elementId: string, newImageUrl: string): KonvaStage {
    const element = this.findElement(elementId);
    if (!element || element.className !== 'Image') {
      throw new Error(`Image element with ID ${elementId} not found`);
    }

    const oldImage = element.attrs.src || element.attrs.image || '';
    element.attrs.src = newImageUrl;

    this.addCustomization({
      element_id: elementId,
      property: 'image',
      old_value: oldImage,
      new_value: newImageUrl,
      timestamp: new Date().toISOString()
    });

    return this.currentCanvasData;
  }

  // ===== 배치 및 크기 조정 =====

  /**
   * 요소 위치 변경
   */
  moveElement(elementId: string, x: number, y: number): KonvaStage {
    const element = this.findElement(elementId);
    if (!element) {
      throw new Error(`Element with ID ${elementId} not found`);
    }

    const oldPosition = { x: element.attrs.x || 0, y: element.attrs.y || 0 };
    element.attrs.x = x;
    element.attrs.y = y;

    this.addCustomization({
      element_id: elementId,
      property: 'position',
      old_value: oldPosition,
      new_value: { x, y },
      timestamp: new Date().toISOString()
    });

    return this.currentCanvasData;
  }

  /**
   * 요소 크기 변경
   */
  resizeElement(elementId: string, width: number, height: number): KonvaStage {
    const element = this.findElement(elementId);
    if (!element) {
      throw new Error(`Element with ID ${elementId} not found`);
    }

    const oldSize = { 
      width: element.attrs.width || 0, 
      height: element.attrs.height || 0 
    };
    
    element.attrs.width = width;
    element.attrs.height = height;

    this.addCustomization({
      element_id: elementId,
      property: 'size',
      old_value: oldSize,
      new_value: { width, height },
      timestamp: new Date().toISOString()
    });

    return this.currentCanvasData;
  }

  // ===== 프리셋 시스템 =====

  /**
   * 커스터마이징 프리셋 적용
   */
  applyPreset(presetConfig: Record<string, any>): KonvaStage {
    const oldState = JSON.parse(JSON.stringify(this.currentCanvasData));

    // 프리셋 설정 적용
    Object.entries(presetConfig).forEach(([elementId, changes]) => {
      if (typeof changes === 'object') {
        Object.entries(changes).forEach(([property, value]) => {
          this.applyCustomizationByProperty(elementId, property, value);
        });
      }
    });

    this.addCustomization({
      element_id: 'global',
      property: 'preset',
      old_value: oldState,
      new_value: presetConfig,
      timestamp: new Date().toISOString()
    });

    return this.currentCanvasData;
  }

  /**
   * 현재 상태를 프리셋으로 저장
   */
  createPreset(name: string, description?: string): Record<string, any> {
    const preset: Record<string, any> = {
      name,
      description: description || `${this.template.name}의 커스터마이징 프리셋`,
      template_id: this.template.id,
      created_at: new Date().toISOString(),
      config: {}
    };

    // 변경된 요소들만 프리셋에 포함
    this.customizations.forEach(customization => {
      if (customization.element_id !== 'global') {
        if (!preset.config[customization.element_id]) {
          preset.config[customization.element_id] = {};
        }
        preset.config[customization.element_id][customization.property] = customization.new_value;
      }
    });

    return preset;
  }

  // ===== 실행 취소/다시 실행 =====

  /**
   * 마지막 변경사항 실행 취소
   */
  undo(): KonvaStage | null {
    if (this.customizations.length === 0) {
      return null;
    }

    const lastCustomization = this.customizations.pop()!;
    this.applyCustomizationByProperty(
      lastCustomization.element_id,
      lastCustomization.property,
      lastCustomization.old_value
    );

    this.updateSession();
    return this.currentCanvasData;
  }

  /**
   * 모든 변경사항 초기화
   */
  reset(): KonvaStage {
    this.currentCanvasData = JSON.parse(JSON.stringify(this.originalCanvasData));
    this.customizations = [];
    this.updateSession();
    return this.currentCanvasData;
  }

  // ===== 내보내기 및 적용 =====

  /**
   * 현재 커스터마이징 상태 가져오기
   */
  getCurrentState(): {
    canvas_data: KonvaStage;
    customizations: TemplateCustomization[];
    session: TemplateCustomizationSession;
  } {
    return {
      canvas_data: this.currentCanvasData,
      customizations: this.customizations,
      session: this.session
    };
  }

  /**
   * Canvas에 적용할 수 있는 형태로 데이터 내보내기
   */
  exportForCanvas(): Record<string, any> {
    return JSON.parse(JSON.stringify(this.currentCanvasData));
  }

  /**
   * 커스터마이징 요약 생성
   */
  getSummary(): {
    total_changes: number;
    changed_elements: number;
    categories: Record<string, number>;
    preview_url?: string;
  } {
    const categories: Record<string, number> = {};
    const changedElements = new Set<string>();

    this.customizations.forEach(customization => {
      changedElements.add(customization.element_id);
      categories[customization.property] = (categories[customization.property] || 0) + 1;
    });

    return {
      total_changes: this.customizations.length,
      changed_elements: changedElements.size,
      categories,
      preview_url: undefined // TODO: 미리보기 이미지 생성
    };
  }

  // ===== 내부 유틸리티 메서드 =====

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private findElement(elementId: string): KonvaElement | null {
    const findRecursive = (elements: KonvaElement[]): KonvaElement | null => {
      for (const element of elements) {
        if (element.id === elementId) {
          return element;
        }
        if (element.children) {
          const found = findRecursive(element.children);
          if (found) return found;
        }
      }
      return null;
    };

    for (const layer of this.currentCanvasData.children) {
      const found = findRecursive(layer.children);
      if (found) return found;
    }

    return null;
  }

  private findAllTextElements(): KonvaElement[] {
    const textElements: KonvaElement[] = [];

    const findRecursive = (elements: KonvaElement[]) => {
      elements.forEach(element => {
        if (element.className === 'Text') {
          textElements.push(element);
        }
        if (element.children) {
          findRecursive(element.children);
        }
      });
    };

    this.currentCanvasData.children.forEach(layer => {
      findRecursive(layer.children);
    });

    return textElements;
  }

  private extractColorsFromCanvas(): string[] {
    const colors = new Set<string>();

    const extractRecursive = (elements: KonvaElement[]) => {
      elements.forEach(element => {
        if (element.attrs.fill && element.attrs.fill !== 'transparent') {
          colors.add(element.attrs.fill);
        }
        if (element.attrs.stroke) {
          colors.add(element.attrs.stroke);
        }
        if (element.children) {
          extractRecursive(element.children);
        }
      });
    };

    this.currentCanvasData.children.forEach(layer => {
      extractRecursive(layer.children);
    });

    return Array.from(colors);
  }

  private createColorMapping(oldColors: string[], newColors: string[]): Record<string, string> {
    const mapping: Record<string, string> = {};
    
    oldColors.forEach((oldColor, index) => {
      const newColorIndex = Math.min(index, newColors.length - 1);
      mapping[oldColor] = newColors[newColorIndex];
    });

    return mapping;
  }

  private applyColorMapping(canvasData: KonvaStage, colorMapping: Record<string, string>): KonvaStage {
    const applyRecursive = (elements: KonvaElement[]) => {
      elements.forEach(element => {
        if (element.attrs.fill && colorMapping[element.attrs.fill]) {
          element.attrs.fill = colorMapping[element.attrs.fill];
        }
        if (element.attrs.stroke && colorMapping[element.attrs.stroke]) {
          element.attrs.stroke = colorMapping[element.attrs.stroke];
        }
        if (element.children) {
          applyRecursive(element.children);
        }
      });
    };

    canvasData.children.forEach(layer => {
      applyRecursive(layer.children);
    });

    return canvasData;
  }

  private applyCustomizationByProperty(elementId: string, property: string, value: any): void {
    if (elementId === 'global') {
      // 전역 변경사항 처리
      switch (property) {
        case 'colorPalette':
          if (Array.isArray(value)) {
            this.currentCanvasData = this.applyColorMapping(this.currentCanvasData, value);
          }
          break;
        case 'fontFamily':
          if (typeof value === 'string') {
            this.findAllTextElements().forEach(element => {
              element.attrs.fontFamily = value;
            });
          }
          break;
      }
    } else {
      const element = this.findElement(elementId);
      if (element) {
        switch (property) {
          case 'color':
            if (element.attrs.fill) element.attrs.fill = value;
            if (element.attrs.stroke) element.attrs.stroke = value;
            break;
          case 'text':
            element.attrs.text = value;
            break;
          case 'fontFamily':
            element.attrs.fontFamily = value;
            break;
          case 'fontSize':
            element.attrs.fontSize = value;
            break;
          case 'position':
            element.attrs.x = value.x;
            element.attrs.y = value.y;
            break;
          case 'size':
            element.attrs.width = value.width;
            element.attrs.height = value.height;
            break;
          case 'image':
            element.attrs.src = value;
            break;
          default:
            element.attrs[property] = value;
        }
      }
    }
  }

  private addCustomization(customization: TemplateCustomization): void {
    this.customizations.push(customization);
    this.updateSession();
  }

  private updateSession(): void {
    this.session.customizations = [...this.customizations];
    this.session.last_updated = new Date().toISOString();
    this.session.is_saved = false;
  }
}

// 커스터마이징 헬퍼 유틸리티
export class CustomizationUtils {
  /**
   * 색상 팔레트에서 주요 색상 추출
   */
  static extractDominantColors(colors: string[], maxColors: number = 5): string[] {
    // 색상 빈도 계산 (실제로는 더 복잡한 알고리즘 필요)
    const colorCounts = colors.reduce((acc, color) => {
      acc[color] = (acc[color] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(colorCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, maxColors)
      .map(([color]) => color);
  }

  /**
   * 두 색상의 대비율 계산
   */
  static calculateContrastRatio(color1: string, color2: string): number {
    const getLuminance = (color: string): number => {
      const [, , l] = ColorUtils.hexToHsl(color);
      return l / 100;
    };

    const l1 = getLuminance(color1);
    const l2 = getLuminance(color2);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);

    return (lighter + 0.05) / (darker + 0.05);
  }

  /**
   * 접근성 요구사항에 맞는 색상 조합 확인
   */
  static isAccessibleColorCombination(backgroundColor: string, textColor: string): {
    isAccessible: boolean;
    contrastRatio: number;
    level: 'AA' | 'AAA' | 'FAIL';
  } {
    const contrastRatio = CustomizationUtils.calculateContrastRatio(backgroundColor, textColor);

    let level: 'AA' | 'AAA' | 'FAIL' = 'FAIL';
    if (contrastRatio >= 7) {
      level = 'AAA';
    } else if (contrastRatio >= 4.5) {
      level = 'AA';
    }

    return {
      isAccessible: level !== 'FAIL',
      contrastRatio,
      level
    };
  }

  /**
   * 템플릿 복잡도 기반 권장 커스터마이징 레벨 계산
   */
  static getRecommendedCustomizationLevel(template: TemplateDetailResponse): 'minimal' | 'moderate' | 'extensive' {
    const complexity = template.dimensions.width * template.dimensions.height;
    const elementCount = this.estimateElementCount(template.canvas_data);

    if (elementCount < 5 && complexity < 500000) {
      return 'minimal';
    } else if (elementCount < 15 && complexity < 2000000) {
      return 'moderate';
    } else {
      return 'extensive';
    }
  }

  private static estimateElementCount(canvasData: any): number {
    let count = 0;
    
    const countRecursive = (obj: any) => {
      if (obj && typeof obj === 'object') {
        if (obj.className && ['Text', 'Rect', 'Circle', 'Image', 'Line', 'Path'].includes(obj.className)) {
          count++;
        }
        if (obj.children && Array.isArray(obj.children)) {
          obj.children.forEach(countRecursive);
        }
        if (Array.isArray(obj)) {
          obj.forEach(countRecursive);
        } else {
          Object.values(obj).forEach(countRecursive);
        }
      }
    };

    countRecursive(canvasData);
    return count;
  }
}

export { ColorUtils, FontManager };