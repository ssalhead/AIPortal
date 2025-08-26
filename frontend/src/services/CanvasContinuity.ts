/**
 * Canvas 연속성 시스템 (v4.0)
 * 이전 Canvas를 참조한 연속 작업 지원
 */

import type { CanvasItem, CanvasToolType } from '../types/canvas';
import { CanvasShareStrategy } from './CanvasShareStrategy';

export interface ContinuityContext {
  /** 기반이 되는 Canvas ID */
  baseCanvasId: string;
  /** 기반 Canvas 타입 */
  baseCanvasType: CanvasToolType;
  /** 기반 Canvas 내용 요약 */
  baseSummary: string;
  /** 연속성 관계 타입 */
  relationshipType: 'extension' | 'modification' | 'variation' | 'reference';
  /** 사용자 요청 */
  userRequest: string;
}

export interface ContinuityCanvasData {
  /** 새 Canvas 데이터 */
  canvasData: any;
  /** 연속성 메타데이터 */
  continuityMeta: {
    baseCanvasId: string;
    relationshipType: string;
    referenceDescription: string;
    inheritedElements: string[];
  };
}

export class CanvasContinuity {
  /**
   * 참조 가능한 Canvas 검색
   */
  static findReferencableCanvas(
    canvasItems: CanvasItem[],
    conversationId: string,
    targetType: CanvasToolType,
    excludeCanvasId?: string
  ): CanvasItem[] {
    console.log('🔍 Canvas 연속성 - 참조 가능한 Canvas 검색:', {
      conversationId,
      targetType,
      excludeCanvasId,
      totalItems: canvasItems.length
    });

    const referencableCanvas = canvasItems.filter(item => {
      // 1. 같은 대화에 속하는지 확인
      const itemConversationId = (item.content as any)?.conversationId;
      if (itemConversationId !== conversationId) {
        return false;
      }

      // 2. 제외할 Canvas ID가 아닌지 확인
      if (excludeCanvasId && item.id === excludeCanvasId) {
        return false;
      }

      // 3. 연속성을 지원하는 Canvas 타입인지 확인
      if (!CanvasShareStrategy.supportsContinuity(item.type)) {
        return false;
      }

      // 4. 같은 타입이거나 호환 가능한 타입인지 확인
      if (this.isCompatibleType(item.type, targetType)) {
        return true;
      }

      return false;
    });

    // 생성 시간순으로 정렬 (최신순)
    const sortedCanvas = referencableCanvas.sort((a, b) => {
      const timeA = new Date(a.createdAt).getTime();
      const timeB = new Date(b.createdAt).getTime();
      return timeB - timeA;
    });

    console.log('✅ 참조 가능한 Canvas 검색 완료:', {
      foundCount: sortedCanvas.length,
      canvasList: sortedCanvas.map(item => ({
        id: item.id,
        type: item.type,
        createdAt: item.createdAt
      }))
    });

    return sortedCanvas;
  }

  /**
   * 연속성 Canvas 생성
   */
  static async createContinuityCanvas(
    baseCanvas: CanvasItem,
    userRequest: string,
    targetType: CanvasToolType,
    conversationId: string
  ): Promise<ContinuityCanvasData> {
    console.log('🔗 Canvas 연속성 - 연속성 Canvas 생성:', {
      baseCanvasId: baseCanvas.id,
      baseCanvasType: baseCanvas.type,
      targetType,
      userRequest: userRequest.substring(0, 100) + '...'
    });

    try {
      // 1. 연속성 관계 분석
      const relationshipType = this.analyzeRelationshipType(userRequest);
      
      // 2. 기반 Canvas 내용 요약
      const baseSummary = this.summarizeCanvasContent(baseCanvas);
      
      // 3. 연속성 컨텍스트 생성
      const continuityContext: ContinuityContext = {
        baseCanvasId: baseCanvas.id,
        baseCanvasType: baseCanvas.type,
        baseSummary,
        relationshipType,
        userRequest
      };

      // 4. 새 Canvas 내용 생성
      const newCanvasContent = await this.generateContinuityContent(
        baseCanvas,
        continuityContext,
        targetType
      );

      // 5. 연속성 메타데이터 생성
      const continuityMeta = {
        baseCanvasId: baseCanvas.id,
        relationshipType,
        referenceDescription: this.generateReferenceDescription(baseCanvas, relationshipType),
        inheritedElements: this.extractInheritedElements(baseCanvas, targetType)
      };

      const result: ContinuityCanvasData = {
        canvasData: {
          type: targetType,
          title: CanvasShareStrategy.generateCanvasTitle(targetType, newCanvasContent),
          description: `${relationshipType} of ${baseCanvas.content?.title || baseCanvas.type}`,
          content: newCanvasContent,
          metadata: {
            ...CanvasShareStrategy.createCanvasMetadata(targetType, conversationId),
            continuity: continuityMeta,
            basedOn: baseCanvas.id,
            generatedFromRequest: userRequest
          }
        },
        continuityMeta
      };

      console.log('✅ 연속성 Canvas 생성 완료:', {
        relationshipType,
        inheritedElementsCount: continuityMeta.inheritedElements.length
      });

      return result;

    } catch (error) {
      console.error('❌ 연속성 Canvas 생성 실패:', error);
      throw error;
    }
  }

  /**
   * 연속성 관계 분석
   */
  private static analyzeRelationshipType(userRequest: string): ContinuityContext['relationshipType'] {
    const request = userRequest.toLowerCase();

    // 수정 키워드
    if (request.includes('수정') || request.includes('변경') || request.includes('바꿔')) {
      return 'modification';
    }

    // 확장 키워드  
    if (request.includes('추가') || request.includes('확장') || request.includes('더')) {
      return 'extension';
    }

    // 변형 키워드
    if (request.includes('다른') || request.includes('새로운') || request.includes('변형')) {
      return 'variation';
    }

    // 기본값은 참조
    return 'reference';
  }

  /**
   * Canvas 내용 요약
   */
  private static summarizeCanvasContent(canvas: CanvasItem): string {
    const content = canvas.content as any;

    switch (canvas.type) {
      case 'text':
        return content.title || content.content?.substring(0, 100) || '텍스트 노트';

      case 'image':
        return content.prompt || content.title || '이미지 생성';

      case 'mindmap':
        const nodes = content.children?.length || 0;
        return `${content.label || '마인드맵'} (${nodes}개 노드)`;

      case 'code':
        return `${content.language || 'JavaScript'} 코드 - ${content.title || '코드 작업'}`;

      case 'chart':
        return `${content.type || 'bar'} 차트 - ${content.title || '차트 작업'}`;

      default:
        return `${canvas.type} 작업`;
    }
  }

  /**
   * 연속성 컨텐츠 생성
   */
  private static async generateContinuityContent(
    baseCanvas: CanvasItem,
    context: ContinuityContext,
    targetType: CanvasToolType
  ): Promise<any> {
    const baseContent = baseCanvas.content as any;

    // 타입별 연속성 컨텐츠 생성
    switch (targetType) {
      case 'text':
        return this.generateContinuityTextContent(baseContent, context);

      case 'image':
        return this.generateContinuityImageContent(baseContent, context);

      case 'mindmap':
        return this.generateContinuityMindmapContent(baseContent, context);

      case 'code':
        return this.generateContinuityCodeContent(baseContent, context);

      case 'chart':
        return this.generateContinuityChartContent(baseContent, context);

      default:
        return { ...baseContent };
    }
  }

  /**
   * 텍스트 연속성 컨텐츠 생성
   */
  private static generateContinuityTextContent(baseContent: any, context: ContinuityContext): any {
    return {
      title: `${context.relationshipType === 'modification' ? '수정된' : '확장된'} ${baseContent.title || '노트'}`,
      content: context.relationshipType === 'extension' 
        ? `${baseContent.content || ''}\n\n[${context.userRequest}에 따른 추가 내용]`
        : `[${context.userRequest}에 따른 수정 내용]`,
      formatting: baseContent.formatting || {},
      conversationId: context.baseCanvasId.split('-')[0] // conversationId 추출
    };
  }

  /**
   * 이미지 연속성 컨텐츠 생성
   */
  private static generateContinuityImageContent(baseContent: any, context: ContinuityContext): any {
    return {
      prompt: context.relationshipType === 'modification'
        ? `${baseContent.prompt}, ${context.userRequest}`
        : context.userRequest,
      negativePrompt: baseContent.negativePrompt || '',
      style: baseContent.style || 'realistic',
      size: baseContent.size || '1K_1:1',
      status: 'idle',
      imageUrl: '',
      conversationId: context.baseCanvasId.split('-')[0]
    };
  }

  /**
   * 마인드맵 연속성 컨텐츠 생성
   */
  private static generateContinuityMindmapContent(baseContent: any, context: ContinuityContext): any {
    return {
      id: 'root',
      label: context.relationshipType === 'extension' 
        ? `${baseContent.label} 확장`
        : `${baseContent.label} 수정`,
      children: baseContent.children || [],
      conversationId: context.baseCanvasId.split('-')[0]
    };
  }

  /**
   * 코드 연속성 컨텐츠 생성
   */
  private static generateContinuityCodeContent(baseContent: any, context: ContinuityContext): any {
    return {
      language: baseContent.language || 'javascript',
      code: baseContent.code || '',
      title: `${baseContent.title || 'Code'} - ${context.relationshipType}`,
      conversationId: context.baseCanvasId.split('-')[0]
    };
  }

  /**
   * 차트 연속성 컨텐츠 생성
   */
  private static generateContinuityChartContent(baseContent: any, context: ContinuityContext): any {
    return {
      type: baseContent.type || 'bar',
      data: baseContent.data || [],
      title: `${baseContent.title || 'Chart'} - ${context.relationshipType}`,
      conversationId: context.baseCanvasId.split('-')[0]
    };
  }

  /**
   * 참조 설명 생성
   */
  private static generateReferenceDescription(canvas: CanvasItem, relationshipType: string): string {
    const typeNames = {
      text: '텍스트 노트',
      image: '이미지',
      mindmap: '마인드맵', 
      code: '코드',
      chart: '차트'
    };

    const typeName = typeNames[canvas.type as CanvasToolType] || canvas.type;
    const relationshipNames = {
      extension: '확장',
      modification: '수정',
      variation: '변형',
      reference: '참조'
    };

    return `이전 ${typeName} 작업을 ${relationshipNames[relationshipType as keyof typeof relationshipNames]}하여 생성`;
  }

  /**
   * 상속된 요소 추출
   */
  private static extractInheritedElements(canvas: CanvasItem, targetType: CanvasToolType): string[] {
    const content = canvas.content as any;
    const elements: string[] = [];

    switch (canvas.type) {
      case 'text':
        if (content.title) elements.push('title');
        if (content.formatting) elements.push('formatting');
        break;

      case 'image':
        if (content.style) elements.push('style');
        if (content.size) elements.push('size');
        if (content.negativePrompt) elements.push('negativePrompt');
        break;

      case 'mindmap':
        if (content.children) elements.push('structure');
        break;

      case 'code':
        if (content.language) elements.push('language');
        break;

      case 'chart':
        if (content.type) elements.push('chartType');
        if (content.data) elements.push('data');
        break;
    }

    return elements;
  }

  /**
   * Canvas 타입 호환성 확인
   */
  private static isCompatibleType(sourceType: CanvasToolType, targetType: CanvasToolType): boolean {
    // 같은 타입은 항상 호환
    if (sourceType === targetType) {
      return true;
    }

    // 호환 가능한 타입 조합
    const compatibilityMatrix = {
      text: ['mindmap', 'code'],
      mindmap: ['text', 'chart'],
      code: ['text'],
      chart: ['mindmap'],
      image: ['image'] // 이미지는 이미지끼리만
    };

    const compatibleTypes = compatibilityMatrix[sourceType];
    return compatibleTypes ? compatibleTypes.includes(targetType) : false;
  }

  /**
   * 연속성 관계 시각화 정보 생성
   */
  static generateContinuityVisualization(
    canvasItems: CanvasItem[],
    conversationId: string
  ): Record<string, any> {
    const continuityMap: Record<string, any> = {};

    canvasItems
      .filter(item => (item.content as any)?.conversationId === conversationId)
      .forEach(item => {
        const metadata = item.metadata;
        if (metadata?.continuity) {
          const baseCanvasId = metadata.continuity.baseCanvasId;
          
          if (!continuityMap[baseCanvasId]) {
            continuityMap[baseCanvasId] = {
              baseCanvas: baseCanvasId,
              derivatives: []
            };
          }

          continuityMap[baseCanvasId].derivatives.push({
            canvasId: item.id,
            type: item.type,
            relationshipType: metadata.continuity.relationshipType,
            createdAt: item.createdAt
          });
        }
      });

    return continuityMap;
  }
}

export default CanvasContinuity;