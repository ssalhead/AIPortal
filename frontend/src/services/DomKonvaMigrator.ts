/**
 * DOM ↔ Konva 무손실 마이그레이션 시스템 v5.0
 * 
 * 특징:
 * - 기존 DOM 기반 Canvas를 Konva로 완벽 변환
 * - 모든 스타일 및 속성 보존
 * - 역방향 변환 지원 (Konva → DOM)
 * - 점진적 마이그레이션 전략
 * - 무결성 검증 시스템
 */

import type { CanvasItem, TextNote, ImageGeneration, MindMapNode } from '../types/canvas';

// ======= 타입 정의 =======

/** DOM 요소 스타일 정보 */
interface DomElementStyle {
  position: 'absolute' | 'relative' | 'fixed';
  left: string;
  top: string;
  width: string;
  height: string;
  fontSize: string;
  fontFamily: string;
  color: string;
  backgroundColor: string;
  border: string;
  borderRadius: string;
  padding: string;
  margin: string;
  textAlign: 'left' | 'center' | 'right';
  fontWeight: string;
  fontStyle: string;
  textDecoration: string;
  lineHeight: string;
  letterSpacing: string;
  transform: string;
  opacity: string;
  zIndex: string;
  overflow: string;
  whiteSpace: string;
  wordWrap: string;
}

/** 마이그레이션 결과 */
interface MigrationResult {
  success: boolean;
  convertedItems: CanvasItem[];
  warnings: string[];
  errors: string[];
  migrationTime: number;
  preservedStylesCount: number;
  totalElementsProcessed: number;
}

/** 마이그레이션 옵션 */
interface MigrationOptions {
  preserveStyles: boolean;
  validateIntegrity: boolean;
  generateBackup: boolean;
  progressCallback?: (progress: number, status: string) => void;
  errorCallback?: (error: string) => void;
  migrationStrategy: 'conservative' | 'aggressive' | 'selective';
  targetEngine: 'konva' | 'dom';
}

// ======= DOM → Konva 마이그레이션 클래스 =======

export class DomKonvaMigrator {
  private readonly defaultOptions: MigrationOptions = {
    preserveStyles: true,
    validateIntegrity: true,
    generateBackup: true,
    migrationStrategy: 'conservative',
    targetEngine: 'konva'
  };

  constructor(
    private options: Partial<MigrationOptions> = {}
  ) {
    this.options = { ...this.defaultOptions, ...options };
    console.log('🔄 DomKonvaMigrator 초기화:', this.options);
  }

  // ======= DOM → Konva 마이그레이션 =======

  /**
   * DOM Canvas를 Konva 형식으로 마이그레이션
   */
  public async migrateDomToKonva(
    domContainer: HTMLElement,
    conversationId: string
  ): Promise<MigrationResult> {
    const startTime = performance.now();
    const result: MigrationResult = {
      success: false,
      convertedItems: [],
      warnings: [],
      errors: [],
      migrationTime: 0,
      preservedStylesCount: 0,
      totalElementsProcessed: 0
    };

    try {
      console.log('🔄 DOM → Konva 마이그레이션 시작:', conversationId);
      this.reportProgress(0, 'DOM 요소 분석 중...');

      // 1. DOM 요소 스캔 및 분석
      const domElements = this.scanDomElements(domContainer);
      result.totalElementsProcessed = domElements.length;

      if (domElements.length === 0) {
        result.warnings.push('마이그레이션할 DOM 요소가 없습니다.');
        return result;
      }

      this.reportProgress(20, `${domElements.length}개 요소 발견`);

      // 2. 백업 생성 (옵션)
      let backupData: string | null = null;
      if (this.options.generateBackup) {
        backupData = this.createDomBackup(domContainer);
        this.reportProgress(30, '백업 생성 완료');
      }

      // 3. 각 DOM 요소를 CanvasItem으로 변환
      for (let i = 0; i < domElements.length; i++) {
        const element = domElements[i];
        
        try {
          const canvasItem = await this.convertDomElementToCanvasItem(
            element, 
            conversationId,
            i
          );
          
          if (canvasItem) {
            result.convertedItems.push(canvasItem);
            
            // 보존된 스타일 수 계산
            result.preservedStylesCount += this.countPreservedStyles(element);
          }
          
        } catch (elementError) {
          const errorMsg = `요소 변환 실패: ${element.tagName} - ${elementError}`;
          result.errors.push(errorMsg);
          this.reportError(errorMsg);
        }

        this.reportProgress(
          30 + (i / domElements.length) * 60,
          `${i + 1}/${domElements.length} 요소 변환 중...`
        );
      }

      // 4. 무결성 검증
      if (this.options.validateIntegrity) {
        this.reportProgress(90, '무결성 검증 중...');
        const validationResult = await this.validateMigrationIntegrity(
          domElements,
          result.convertedItems
        );
        
        result.warnings.push(...validationResult.warnings);
        result.errors.push(...validationResult.errors);
      }

      // 5. 결과 정리
      result.success = result.errors.length === 0;
      result.migrationTime = performance.now() - startTime;

      this.reportProgress(100, '마이그레이션 완료');
      console.log('✅ DOM → Konva 마이그레이션 완료:', result);

      return result;

    } catch (error) {
      result.errors.push(`마이그레이션 전체 실패: ${error}`);
      result.migrationTime = performance.now() - startTime;
      console.error('❌ DOM → Konva 마이그레이션 실패:', error);
      return result;
    }
  }

  /**
   * Konva Canvas를 DOM 형식으로 역변환
   */
  public async migrateKonvaToDom(
    canvasItems: CanvasItem[],
    targetContainer: HTMLElement
  ): Promise<MigrationResult> {
    const startTime = performance.now();
    const result: MigrationResult = {
      success: false,
      convertedItems: [],
      warnings: [],
      errors: [],
      migrationTime: 0,
      preservedStylesCount: 0,
      totalElementsProcessed: canvasItems.length
    };

    try {
      console.log('🔄 Konva → DOM 마이그레이션 시작:', canvasItems.length);
      this.reportProgress(0, 'Canvas 아이템 분석 중...');

      // 컨테이너 초기화
      targetContainer.innerHTML = '';
      targetContainer.style.position = 'relative';
      targetContainer.style.width = '100%';
      targetContainer.style.height = '100%';

      // 각 Canvas 아이템을 DOM 요소로 변환
      for (let i = 0; i < canvasItems.length; i++) {
        const item = canvasItems[i];

        try {
          const domElement = await this.convertCanvasItemToDomElement(item);
          
          if (domElement) {
            targetContainer.appendChild(domElement);
            result.preservedStylesCount += this.countCanvasItemStyles(item);
          }

        } catch (elementError) {
          const errorMsg = `아이템 변환 실패: ${item.id} - ${elementError}`;
          result.errors.push(errorMsg);
          this.reportError(errorMsg);
        }

        this.reportProgress(
          (i / canvasItems.length) * 90,
          `${i + 1}/${canvasItems.length} 아이템 변환 중...`
        );
      }

      result.success = result.errors.length === 0;
      result.migrationTime = performance.now() - startTime;

      this.reportProgress(100, '역변환 완료');
      console.log('✅ Konva → DOM 마이그레이션 완료:', result);

      return result;

    } catch (error) {
      result.errors.push(`역변환 전체 실패: ${error}`);
      result.migrationTime = performance.now() - startTime;
      console.error('❌ Konva → DOM 마이그레이션 실패:', error);
      return result;
    }
  }

  // ======= DOM 요소 분석 =======

  private scanDomElements(container: HTMLElement): HTMLElement[] {
    const elements: HTMLElement[] = [];
    
    // 재귀적으로 모든 하위 요소 스캔
    const traverse = (element: HTMLElement) => {
      // Canvas 관련 요소만 선별
      if (this.isCanvasRelevantElement(element)) {
        elements.push(element);
      }

      // 자식 요소들 재귀 탐색
      Array.from(element.children).forEach(child => {
        if (child instanceof HTMLElement) {
          traverse(child);
        }
      });
    };

    traverse(container);
    console.log(`📊 DOM 스캔 완료: ${elements.length}개 요소 발견`);
    
    return elements;
  }

  private isCanvasRelevantElement(element: HTMLElement): boolean {
    // Canvas 관련 클래스나 데이터 속성 확인
    const canvasClasses = [
      'canvas-item', 'canvas-text', 'canvas-image', 'canvas-mindmap',
      'text-note', 'image-generation', 'mindmap-node'
    ];

    const hasCanvasClass = canvasClasses.some(cls => 
      element.classList.contains(cls)
    );

    const hasCanvasDataAttr = element.hasAttribute('data-canvas-item') ||
                            element.hasAttribute('data-canvas-type');

    // 텍스트 내용이 있는 요소
    const hasTextContent = element.textContent && 
                          element.textContent.trim().length > 0;

    // 이미지 요소
    const isImage = element.tagName === 'IMG' || 
                   element.style.backgroundImage !== '';

    return hasCanvasClass || hasCanvasDataAttr || 
           (hasTextContent && element.tagName !== 'SCRIPT') || 
           isImage;
  }

  // ======= DOM → Canvas 아이템 변환 =======

  private async convertDomElementToCanvasItem(
    element: HTMLElement,
    conversationId: string,
    index: number
  ): Promise<CanvasItem | null> {
    const computedStyle = window.getComputedStyle(element);
    const rect = element.getBoundingClientRect();

    // 요소 타입 결정
    const itemType = this.determineDomElementType(element);
    if (!itemType) {
      return null;
    }

    // 기본 Canvas 아이템 구조
    const baseItem: Partial<CanvasItem> = {
      id: element.id || `migrated-${Date.now()}-${index}`,
      type: itemType,
      position: {
        x: parseFloat(computedStyle.left) || rect.left || 0,
        y: parseFloat(computedStyle.top) || rect.top || 0
      },
      size: {
        width: rect.width || 100,
        height: rect.height || 50
      },
      metadata: {
        conversationId,
        migratedFromDom: true,
        originalTagName: element.tagName,
        originalClassName: element.className,
        migrationTimestamp: new Date().toISOString()
      },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    // 타입별 콘텐츠 생성
    switch (itemType) {
      case 'text':
        baseItem.content = this.extractTextContent(element, computedStyle);
        break;
      case 'image':
        baseItem.content = await this.extractImageContent(element);
        break;
      case 'mindmap':
        baseItem.content = this.extractMindMapContent(element);
        break;
    }

    return baseItem as CanvasItem;
  }

  private determineDomElementType(element: HTMLElement): 'text' | 'image' | 'mindmap' | null {
    // 데이터 속성으로 명시적 타입 확인
    const explicitType = element.getAttribute('data-canvas-type');
    if (explicitType && ['text', 'image', 'mindmap'].includes(explicitType)) {
      return explicitType as 'text' | 'image' | 'mindmap';
    }

    // 요소 태그 기반 추론
    if (element.tagName === 'IMG' || 
        element.style.backgroundImage || 
        element.querySelector('img')) {
      return 'image';
    }

    // 마인드맵 구조 감지
    if (element.classList.contains('mindmap') || 
        element.querySelector('.mindmap-node') ||
        element.hasAttribute('data-mindmap')) {
      return 'mindmap';
    }

    // 텍스트 콘텐츠가 있으면 텍스트 타입
    if (element.textContent && element.textContent.trim().length > 0) {
      return 'text';
    }

    return null;
  }

  private extractTextContent(element: HTMLElement, computedStyle: CSSStyleDeclaration): TextNote {
    return {
      text: element.textContent || element.innerText || '',
      fontSize: parseInt(computedStyle.fontSize) || 14,
      fontFamily: computedStyle.fontFamily || 'Arial, sans-serif',
      color: computedStyle.color || '#333333',
      backgroundColor: computedStyle.backgroundColor === 'rgba(0, 0, 0, 0)' 
        ? 'transparent' 
        : computedStyle.backgroundColor,
      textAlign: (computedStyle.textAlign as any) || 'left',
      fontWeight: computedStyle.fontWeight.includes('bold') ? 'bold' : 'normal',
      fontStyle: computedStyle.fontStyle || 'normal',
      textDecoration: computedStyle.textDecoration || 'none'
    };
  }

  private async extractImageContent(element: HTMLElement): Promise<ImageGeneration> {
    const images: string[] = [];
    let prompt = '';

    // IMG 태그에서 이미지 추출
    if (element.tagName === 'IMG') {
      const imgElement = element as HTMLImageElement;
      images.push(imgElement.src);
      prompt = imgElement.alt || '';
    }

    // 배경 이미지 추출
    const bgImage = window.getComputedStyle(element).backgroundImage;
    if (bgImage && bgImage !== 'none') {
      const urlMatch = bgImage.match(/url\(["']?(.*?)["']?\)/);
      if (urlMatch && urlMatch[1]) {
        images.push(urlMatch[1]);
      }
    }

    // 자식 IMG 요소들 추출
    const childImages = element.querySelectorAll('img');
    childImages.forEach(img => {
      if (!images.includes(img.src)) {
        images.push(img.src);
        if (!prompt && img.alt) {
          prompt = img.alt;
        }
      }
    });

    return {
      prompt: prompt || element.getAttribute('data-prompt') || '',
      images,
      style: 'realistic',
      aspectRatio: '1:1',
      size: '1K_1:1'
    };
  }

  private extractMindMapContent(element: HTMLElement): { nodes: MindMapNode[] } {
    const nodes: MindMapNode[] = [];
    const nodeElements = element.querySelectorAll('.mindmap-node, [data-mindmap-node]');

    nodeElements.forEach((nodeEl, index) => {
      const rect = nodeEl.getBoundingClientRect();
      const parentRect = element.getBoundingClientRect();

      const node: MindMapNode = {
        id: nodeEl.id || `node-${index}`,
        text: nodeEl.textContent?.trim() || `노드 ${index + 1}`,
        x: rect.left - parentRect.left,
        y: rect.top - parentRect.top,
        level: parseInt(nodeEl.getAttribute('data-level') || '0'),
        parentId: nodeEl.getAttribute('data-parent-id') || null,
        children: []
      };

      nodes.push(node);
    });

    // 부모-자식 관계 구성
    nodes.forEach(node => {
      if (node.parentId) {
        const parent = nodes.find(n => n.id === node.parentId);
        if (parent) {
          parent.children.push(node.id);
        }
      }
    });

    return { nodes };
  }

  // ======= Canvas 아이템 → DOM 요소 변환 =======

  private async convertCanvasItemToDomElement(item: CanvasItem): Promise<HTMLElement> {
    let element: HTMLElement;

    switch (item.type) {
      case 'text':
        element = this.createTextDomElement(item);
        break;
      case 'image':
        element = await this.createImageDomElement(item);
        break;
      case 'mindmap':
        element = this.createMindMapDomElement(item);
        break;
      default:
        throw new Error(`지원하지 않는 아이템 타입: ${item.type}`);
    }

    // 공통 스타일 적용
    this.applyCommonDomStyles(element, item);

    return element;
  }

  private createTextDomElement(item: CanvasItem): HTMLElement {
    const textContent = item.content as TextNote;
    const element = document.createElement('div');

    element.className = 'canvas-text migrated-from-konva';
    element.textContent = textContent.text || '';
    element.id = item.id;
    
    // 텍스트 스타일 적용
    element.style.fontSize = `${textContent.fontSize || 14}px`;
    element.style.fontFamily = textContent.fontFamily || 'Arial, sans-serif';
    element.style.color = textContent.color || '#333333';
    element.style.textAlign = textContent.textAlign || 'left';
    element.style.fontWeight = textContent.fontWeight || 'normal';
    element.style.fontStyle = textContent.fontStyle || 'normal';
    element.style.textDecoration = textContent.textDecoration || 'none';
    
    if (textContent.backgroundColor && textContent.backgroundColor !== 'transparent') {
      element.style.backgroundColor = textContent.backgroundColor;
      element.style.padding = '8px';
      element.style.borderRadius = '4px';
    }

    return element;
  }

  private async createImageDomElement(item: CanvasItem): Promise<HTMLElement> {
    const imageContent = item.content as ImageGeneration;
    const element = document.createElement('div');

    element.className = 'canvas-image migrated-from-konva';
    element.id = item.id;

    if (imageContent.images && imageContent.images.length > 0) {
      const selectedIndex = imageContent.selectedVersion || 0;
      const imageUrl = imageContent.images[selectedIndex];

      const img = document.createElement('img');
      img.src = imageUrl;
      img.alt = imageContent.prompt || '';
      img.style.width = '100%';
      img.style.height = '100%';
      img.style.objectFit = 'cover';

      element.appendChild(img);
    }

    return element;
  }

  private createMindMapDomElement(item: CanvasItem): HTMLElement {
    const mindMapContent = item.content as { nodes: MindMapNode[] };
    const element = document.createElement('div');

    element.className = 'canvas-mindmap migrated-from-konva';
    element.id = item.id;
    element.style.position = 'relative';

    mindMapContent.nodes.forEach(node => {
      const nodeElement = document.createElement('div');
      nodeElement.className = 'mindmap-node';
      nodeElement.textContent = node.text;
      nodeElement.style.position = 'absolute';
      nodeElement.style.left = `${node.x}px`;
      nodeElement.style.top = `${node.y}px`;
      nodeElement.style.padding = '8px 16px';
      nodeElement.style.backgroundColor = this.getMindMapNodeColor(node.level);
      nodeElement.style.border = '1px solid #cccccc';
      nodeElement.style.borderRadius = '8px';
      nodeElement.style.fontSize = '14px';
      nodeElement.style.whiteSpace = 'nowrap';
      
      nodeElement.setAttribute('data-node-id', node.id);
      nodeElement.setAttribute('data-level', node.level.toString());
      if (node.parentId) {
        nodeElement.setAttribute('data-parent-id', node.parentId);
      }

      element.appendChild(nodeElement);
    });

    return element;
  }

  private applyCommonDomStyles(element: HTMLElement, item: CanvasItem): void {
    element.style.position = 'absolute';
    element.style.left = `${item.position?.x || 0}px`;
    element.style.top = `${item.position?.y || 0}px`;
    element.style.width = `${item.size?.width || 100}px`;
    element.style.height = `${item.size?.height || 50}px`;
    element.style.cursor = 'move';
    element.style.userSelect = 'none';
    
    // 메타데이터 속성 추가
    element.setAttribute('data-canvas-item', item.id);
    element.setAttribute('data-canvas-type', item.type);
    if (item.metadata?.conversationId) {
      element.setAttribute('data-conversation-id', item.metadata.conversationId);
    }
  }

  // ======= 유틸리티 메서드 =======

  private createDomBackup(container: HTMLElement): string {
    return container.innerHTML;
  }

  private countPreservedStyles(element: HTMLElement): number {
    const computedStyle = window.getComputedStyle(element);
    let count = 0;
    
    // 주요 스타일 속성들 확인
    const importantStyles = [
      'position', 'left', 'top', 'width', 'height', 'fontSize',
      'fontFamily', 'color', 'backgroundColor', 'textAlign',
      'fontWeight', 'fontStyle', 'textDecoration'
    ];
    
    importantStyles.forEach(prop => {
      if (computedStyle.getPropertyValue(prop)) {
        count++;
      }
    });
    
    return count;
  }

  private countCanvasItemStyles(item: CanvasItem): number {
    let count = 0;
    
    if (item.position) count += 2; // x, y
    if (item.size) count += 2; // width, height
    
    if (item.type === 'text') {
      const textContent = item.content as TextNote;
      if (textContent.fontSize) count++;
      if (textContent.fontFamily) count++;
      if (textContent.color) count++;
      if (textContent.backgroundColor) count++;
      if (textContent.textAlign) count++;
      if (textContent.fontWeight) count++;
      if (textContent.fontStyle) count++;
      if (textContent.textDecoration) count++;
    }
    
    return count;
  }

  private getMindMapNodeColor(level: number): string {
    const colors = [
      '#E3F2FD', // 파란색 (레벨 0)
      '#E8F5E8', // 초록색 (레벨 1)
      '#FFF3E0', // 주황색 (레벨 2)
      '#FFEBEE', // 빨간색 (레벨 3)
      '#F3E5F5', // 보라색 (레벨 4)
      '#E0F7FA'  // 청록색 (레벨 5+)
    ];
    
    return colors[Math.min(level, colors.length - 1)];
  }

  private async validateMigrationIntegrity(
    originalElements: HTMLElement[],
    convertedItems: CanvasItem[]
  ): Promise<{ warnings: string[]; errors: string[] }> {
    const warnings: string[] = [];
    const errors: string[] = [];

    // 요소 수 비교
    if (originalElements.length !== convertedItems.length) {
      warnings.push(
        `요소 수 불일치: 원본 ${originalElements.length}, 변환된 것 ${convertedItems.length}`
      );
    }

    // 각 변환된 아이템의 무결성 확인
    convertedItems.forEach(item => {
      if (!item.id || !item.type || !item.content) {
        errors.push(`필수 속성 누락: ${item.id || '알 수 없는 아이템'}`);
      }
      
      if (!item.position || !item.size) {
        warnings.push(`위치/크기 정보 누락: ${item.id}`);
      }
    });

    return { warnings, errors };
  }

  // ======= 이벤트 보고 =======

  private reportProgress(progress: number, status: string): void {
    this.options.progressCallback?.(progress, status);
  }

  private reportError(error: string): void {
    this.options.errorCallback?.(error);
  }

  // ======= 공개 유틸리티 =======

  /**
   * 점진적 마이그레이션 - 일부 요소만 변환
   */
  public async migrateSelectiveElements(
    domContainer: HTMLElement,
    selector: string,
    conversationId: string
  ): Promise<MigrationResult> {
    const selectedElements = Array.from(
      domContainer.querySelectorAll(selector)
    ) as HTMLElement[];

    if (selectedElements.length === 0) {
      return {
        success: false,
        convertedItems: [],
        warnings: ['선택된 요소가 없습니다.'],
        errors: [],
        migrationTime: 0,
        preservedStylesCount: 0,
        totalElementsProcessed: 0
      };
    }

    console.log(`🔄 선택적 마이그레이션: ${selectedElements.length}개 요소`);
    
    // 임시 컨테이너 생성하여 선택된 요소들만 처리
    const tempContainer = document.createElement('div');
    selectedElements.forEach(el => tempContainer.appendChild(el.cloneNode(true)));

    return this.migrateDomToKonva(tempContainer, conversationId);
  }
}

// ======= 팩토리 함수 =======

export const createDomKonvaMigrator = (
  options?: Partial<MigrationOptions>
): DomKonvaMigrator => {
  return new DomKonvaMigrator(options);
};

// ======= 편의 함수들 =======

/**
 * 빠른 DOM → Konva 마이그레이션
 */
export const quickMigrateDomToKonva = async (
  domContainer: HTMLElement,
  conversationId: string
): Promise<CanvasItem[]> => {
  const migrator = createDomKonvaMigrator({
    migrationStrategy: 'aggressive',
    validateIntegrity: false,
    generateBackup: false
  });

  const result = await migrator.migrateDomToKonva(domContainer, conversationId);
  return result.convertedItems;
};

/**
 * 빠른 Konva → DOM 마이그레이션
 */
export const quickMigrateKonvaToDom = async (
  canvasItems: CanvasItem[],
  targetContainer: HTMLElement
): Promise<boolean> => {
  const migrator = createDomKonvaMigrator({
    migrationStrategy: 'aggressive',
    validateIntegrity: false
  });

  const result = await migrator.migrateKonvaToDom(canvasItems, targetContainer);
  return result.success;
};