/**
 * 대화별 Canvas 관리 서비스 (v2.0)
 * - 하나의 대화 = 하나의 Canvas = 다중 이미지 버전 히스토리
 * - ImageSession Store와 완전 통합
 * - 이미지 진화 시스템 지원
 */

import { v4 as uuidv4 } from 'uuid';
import type { CanvasItem, CanvasToolType, TextNote, ImageGeneration, MindMapNode } from '../types/canvas';
import type { ImageGenerationSession, ImageVersion } from '../types/imageSession';

// Canvas 고유 식별자 생성
export class ConversationCanvasManager {
  /**
   * 대화 + 타입별 Canvas 고유 ID 생성
   */
  static getCanvasId(conversationId: string, type: CanvasToolType): string {
    return `${conversationId}-${type}`;
  }

  /**
   * Canvas 아이템에서 conversationId 추출
   */
  static getConversationId(item: CanvasItem): string | null {
    const content = item.content as any;
    return content?.conversationId || null;
  }

  /**
   * Canvas 아이템 타입별 기본 콘텐츠 생성
   */
  static createDefaultContent(type: CanvasToolType, conversationId: string): any {
    const baseContent = { conversationId };
    
    switch (type) {
      case 'text':
        return {
          ...baseContent,
          title: '새 노트',
          content: '',
          formatting: {}
        } as TextNote;
        
      case 'image':
        return {
          ...baseContent,
          prompt: '',
          negativePrompt: '',
          style: 'realistic',
          size: '1K_1:1',
          status: 'idle',
          imageUrl: '',
          generation_result: null,
          // 새로운 버전 관리 필드
          selectedVersionId: '',
          versions: [],
          theme: '',
          evolutionHistory: []
        } as ImageGeneration;
        
      case 'mindmap':
        return {
          ...baseContent,
          id: 'root',
          label: '새 마인드맵',
          children: []
        } as MindMapNode;
        
      case 'code':
        return {
          ...baseContent,
          language: 'javascript',
          code: '',
          title: '새 코드'
        };
        
      case 'chart':
        return {
          ...baseContent,
          type: 'bar',
          data: [],
          title: '새 차트'
        };
        
      default:
        return baseContent;
    }
  }

  /**
   * 새로운 Canvas 아이템 생성
   */
  static createCanvasItem(conversationId: string, type: CanvasToolType, customContent?: any): CanvasItem {
    const canvasId = this.getCanvasId(conversationId, type);
    const defaultContent = this.createDefaultContent(type, conversationId);
    
    // 커스텀 콘텐츠가 있으면 병합, conversationId는 항상 보장
    const finalContent = customContent ? {
      ...defaultContent,
      ...customContent,
      conversationId // conversationId는 항상 유지
    } : defaultContent;

    const newItem: CanvasItem = {
      id: canvasId, // 고유 ID 사용 (중복 방지)
      type,
      content: finalContent,
      position: { x: 50, y: 50 },
      size: type === 'text' ? { width: 300, height: 200 } : { width: 400, height: 300 },
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    console.log('✨ Canvas Manager - 새 Canvas 아이템 생성:', {
      canvasId,
      conversationId,
      type,
      hasCustomContent: !!customContent
    });

    return newItem;
  }

  /**
   * Canvas 아이템이 특정 대화에 속하는지 확인
   */
  static belongsToConversation(item: CanvasItem, conversationId: string): boolean {
    const itemConversationId = this.getConversationId(item);
    return itemConversationId === conversationId;
  }

  /**
   * Canvas 아이템이 특정 타입인지 확인
   */
  static isCanvasType(item: CanvasItem, type: CanvasToolType): boolean {
    return item.type === type;
  }

  /**
   * 대화의 모든 Canvas 타입 목록 반환
   */
  static getConversationCanvasTypes(items: CanvasItem[], conversationId: string): CanvasToolType[] {
    const types = items
      .filter(item => this.belongsToConversation(item, conversationId))
      .map(item => item.type);
    
    return [...new Set(types)]; // 중복 제거
  }

  /**
   * 대화별 Canvas 아이템 필터링
   */
  static getConversationCanvases(items: CanvasItem[], conversationId: string): CanvasItem[] {
    return items.filter(item => this.belongsToConversation(item, conversationId));
  }

  /**
   * 특정 대화의 특정 타입 Canvas 찾기
   */
  static findCanvas(items: CanvasItem[], conversationId: string, type: CanvasToolType): CanvasItem | null {
    const canvasId = this.getCanvasId(conversationId, type);
    return items.find(item => item.id === canvasId) || null;
  }

  /**
   * Canvas 데이터에서 적절한 타입 추론
   */
  static inferCanvasType(canvasData: any): CanvasToolType {
    if (canvasData.type) {
      return canvasData.type as CanvasToolType;
    }
    
    // 데이터 구조로 타입 추론
    if (canvasData.image_data || canvasData.prompt) {
      return 'image';
    } else if (canvasData.elements || canvasData.nodes) {
      return 'mindmap';
    } else if (canvasData.code || canvasData.language) {
      return 'code';
    } else if (canvasData.chartType || canvasData.data) {
      return 'chart';
    } else {
      return 'text'; // 기본값
    }
  }

  /**
   * Canvas 데이터를 Canvas 콘텐츠로 변환
   */
  static convertCanvasDataToContent(canvasData: any, conversationId: string): { type: CanvasToolType; content: any } {
    const type = this.inferCanvasType(canvasData);
    const baseContent = { conversationId };

    switch (type) {
      case 'image':
        const { image_data } = canvasData;
        if (image_data) {
          // 이미지 URL 추출 로직 (기존과 동일)
          let imageUrl = null;
          if (image_data.image_urls && image_data.image_urls.length > 0) {
            imageUrl = image_data.image_urls[0];
          } else if (image_data.images && image_data.images.length > 0) {
            const firstImage = image_data.images[0];
            imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
          } else if (image_data.generation_result?.images?.[0]) {
            const firstImage = image_data.generation_result.images[0];
            imageUrl = typeof firstImage === 'string' ? firstImage : firstImage?.url;
          }

          return {
            type: 'image',
            content: {
              ...baseContent,
              prompt: image_data.prompt || canvasData.title || '',
              negativePrompt: image_data.negativePrompt || '',
              style: image_data.style || 'realistic',
              size: image_data.size || '1K_1:1',
              status: imageUrl ? 'completed' : 'generating',
              imageUrl: imageUrl || '',
              generation_result: image_data.generation_result
            }
          };
        }
        break;
        
      case 'mindmap':
        return {
          type: 'mindmap',
          content: {
            ...baseContent,
            ...(canvasData.elements || { id: 'root', label: canvasData.title || '새 마인드맵', children: [] })
          }
        };
        
      case 'text':
      default:
        return {
          type: 'text',
          content: {
            ...baseContent,
            title: canvasData.title || '새 노트',
            content: canvasData.description || canvasData.content || '',
            formatting: canvasData.formatting || {}
          }
        };
    }

    // fallback
    return {
      type: 'text',
      content: {
        ...baseContent,
        title: canvasData.title || '새 노트',
        content: canvasData.description || '',
        formatting: {}
      }
    };
  }

  /**
   * ImageSession 데이터를 Canvas 컨텐츠로 완전 통합 (v2.0)
   */
  static integrateImageSession(conversationId: string, imageSession: ImageGenerationSession, selectedVersionId?: string): { type: CanvasToolType; content: any } {
    // 선택된 버전 결정 로직 강화
    const selectedVersion = selectedVersionId 
      ? imageSession.versions.find(v => v.id === selectedVersionId)
      : imageSession.versions.find(v => v.isSelected) 
        || imageSession.versions[imageSession.versions.length - 1]; // 최신 버전 우선
    
    console.log('🔗 Canvas Manager - ImageSession 완전 통합 v2.0:', {
      conversationId,
      theme: imageSession.theme,
      totalVersions: imageSession.versions.length,
      selectedVersionId: selectedVersion?.id,
      selectedVersionNumber: selectedVersion?.versionNumber,
      allVersions: imageSession.versions.map(v => ({ 
        id: v.id.substring(0, 8), 
        versionNumber: v.versionNumber, 
        hasImage: !!v.imageUrl,
        status: v.status 
      }))
    });

    // 🚀 모든 버전을 포함한 완전 통합 컨텐츠
    const integratedContent = {
      conversationId,
      
      // 현재 선택된 버전의 메인 표시 정보
      prompt: selectedVersion?.prompt || '',
      negativePrompt: selectedVersion?.negativePrompt || '',
      style: selectedVersion?.style || 'realistic',
      size: selectedVersion?.size || '1K_1:1',
      status: selectedVersion?.status || 'idle',
      imageUrl: selectedVersion?.imageUrl || '',
      generation_result: null, // TODO: 필요시 추가
      
      // 🎯 완전 통합 버전 관리 시스템
      selectedVersionId: selectedVersion?.id || '',
      versions: imageSession.versions.map(version => ({
        ...version,
        // 버전별 메타데이터 추가
        isCurrentlySelected: version.id === (selectedVersion?.id || ''),
        canvasDisplayOrder: version.versionNumber
      })),
      theme: imageSession.theme,
      evolutionHistory: imageSession.evolutionHistory,
      
      // Canvas 통합 메타데이터
      canvasIntegratedAt: new Date().toISOString(),
      totalVersionCount: imageSession.versions.length,
      completedVersionCount: imageSession.versions.filter(v => v.status === 'completed').length
    };

    console.log('✅ Canvas Manager - 통합 컨텐츠 생성 완료:', {
      selectedImageUrl: integratedContent.imageUrl,
      totalVersions: integratedContent.totalVersionCount,
      completedVersions: integratedContent.completedVersionCount
    });

    return {
      type: 'image',
      content: integratedContent
    };
  }

  /**
   * Canvas 컨텐츠에서 현재 선택된 버전 정보 추출
   */
  static getSelectedVersionFromCanvas(canvasItem: CanvasItem): ImageVersion | null {
    if (canvasItem.type !== 'image') return null;
    
    const content = canvasItem.content as any;
    const selectedVersionId = content.selectedVersionId;
    const versions = content.versions || [];
    
    return versions.find((v: ImageVersion) => v.id === selectedVersionId) || null;
  }

  /**
   * Canvas가 ImageSession 통합 버전인지 확인
   */
  static isImageSessionIntegrated(canvasItem: CanvasItem): boolean {
    if (canvasItem.type !== 'image') return false;
    
    const content = canvasItem.content as any;
    return Array.isArray(content.versions) && content.versions.length > 0;
  }

  /**
   * 디버깅용 - 현재 Canvas 상태 로깅
   */
  static logCanvasState(items: CanvasItem[], conversationId?: string): void {
    console.log('🔍 Canvas Manager - 현재 상태:', {
      totalItems: items.length,
      conversationId,
      items: items.map(item => ({
        id: item.id,
        type: item.type,
        conversationId: this.getConversationId(item),
        belongsToConversation: conversationId ? this.belongsToConversation(item, conversationId) : null,
        isImageSessionIntegrated: this.isImageSessionIntegrated(item),
        versionsCount: item.type === 'image' ? (item.content as any).versions?.length || 0 : 0
      }))
    });
  }
}

export default ConversationCanvasManager;