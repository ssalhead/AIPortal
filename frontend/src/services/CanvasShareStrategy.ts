/**
 * Canvas 공유 전략 관리자 (v4.0)
 * 기능별 차별화된 Canvas 공유 모델 구현
 */

import type { CanvasToolType, CanvasItem } from '../types/canvas';

export interface CanvasShareConfig {
  /** Canvas 공유 전략 타입 */
  shareType: 'conversation' | 'request' | 'hybrid';
  /** 영구 보존 여부 */
  persistent: boolean;
  /** 자동 저장 여부 */
  autoSave: boolean;
  /** 버전 관리 여부 */
  versionControl: boolean;
  /** 연속성 작업 지원 여부 */
  continuitySupport: boolean;
}

export class CanvasShareStrategy {
  /**
   * 기능별 Canvas 공유 전략 설정
   */
  private static readonly CANVAS_CONFIGS: Record<CanvasToolType, CanvasShareConfig> = {
    // 이미지 생성: 요청별 개별 Canvas + 완전한 버전 관리
    image: {
      shareType: 'request',
      persistent: true,
      autoSave: true,
      versionControl: true,
      continuitySupport: true
    },
    
    // 텍스트 노트: 요청별 개별 Canvas + 연속성 지원
    text: {
      shareType: 'request',
      persistent: true,
      autoSave: true,
      versionControl: false,
      continuitySupport: true
    },
    
    // 마인드맵: 요청별 개별 Canvas + 연속성 지원
    mindmap: {
      shareType: 'request',
      persistent: true,
      autoSave: true,
      versionControl: false,
      continuitySupport: true
    },
    
    // 코드: 요청별 개별 Canvas + 연속성 지원
    code: {
      shareType: 'request',
      persistent: true,
      autoSave: true,
      versionControl: false,
      continuitySupport: true
    },
    
    // 차트: 요청별 개별 Canvas + 연속성 지원
    chart: {
      shareType: 'request',
      persistent: true,
      autoSave: true,
      versionControl: false,
      continuitySupport: true
    }
  };

  /**
   * Canvas ID 생성 (기능별 전략 적용)
   */
  static getCanvasId(
    conversationId: string, 
    type: CanvasToolType, 
    requestId?: string
  ): string {
    const config = this.getCanvasConfig(type);
    
    switch (config.shareType) {
      case 'conversation':
        // 대화별 단일 Canvas (이미지 등)
        return `${conversationId}-${type}`;
        
      case 'request':
        // 요청별 개별 Canvas (텍스트, 마인드맵 등)
        const timestamp = Date.now();
        const uniqueId = requestId || `${timestamp}`;
        return `${conversationId}-${type}-${uniqueId}`;
        
      case 'hybrid':
        // 하이브리드 전략 (미래 확장용)
        return `${conversationId}-${type}-${requestId || Date.now()}`;
        
      default:
        return `${conversationId}-${type}-${Date.now()}`;
    }
  }

  /**
   * Canvas 공유 설정 조회
   */
  static getCanvasConfig(type: CanvasToolType): CanvasShareConfig {
    return this.CANVAS_CONFIGS[type];
  }

  /**
   * Canvas가 영구 보존되어야 하는지 확인
   */
  static shouldPreserveCanvas(type: CanvasToolType): boolean {
    return this.getCanvasConfig(type).persistent;
  }

  /**
   * Canvas가 자동 저장되어야 하는지 확인
   */
  static shouldAutoSave(type: CanvasToolType): boolean {
    return this.getCanvasConfig(type).autoSave;
  }

  /**
   * Canvas가 버전 관리를 지원하는지 확인
   */
  static supportsVersionControl(type: CanvasToolType): boolean {
    return this.getCanvasConfig(type).versionControl;
  }

  /**
   * Canvas가 연속성 작업을 지원하는지 확인
   */
  static supportsContinuity(type: CanvasToolType): boolean {
    return this.getCanvasConfig(type).continuitySupport;
  }

  /**
   * Canvas 공유 타입 확인 (대화별 vs 요청별)
   */
  static isConversationShared(type: CanvasToolType): boolean {
    return this.getCanvasConfig(type).shareType === 'conversation';
  }

  /**
   * Canvas가 동일한 공유 그룹에 속하는지 확인
   */
  static isSameShareGroup(canvas1: CanvasItem, canvas2: CanvasItem): boolean {
    if (canvas1.type !== canvas2.type) {
      return false;
    }

    const config = this.getCanvasConfig(canvas1.type);
    
    if (config.shareType === 'conversation') {
      // 대화별 공유: 같은 대화의 같은 타입이면 동일 그룹
      const conv1 = (canvas1.content as any)?.conversationId;
      const conv2 = (canvas2.content as any)?.conversationId;
      return conv1 === conv2;
    } else {
      // 요청별 공유: Canvas ID가 같아야 동일 그룹
      return canvas1.id === canvas2.id;
    }
  }

  /**
   * Canvas 메타데이터 생성
   */
  static createCanvasMetadata(
    type: CanvasToolType,
    conversationId: string,
    customData?: Record<string, any>
  ): Record<string, any> {
    const config = this.getCanvasConfig(type);
    
    return {
      // 기본 메타데이터
      canvasType: type,
      conversationId,
      shareStrategy: config.shareType,
      persistent: config.persistent,
      autoSave: config.autoSave,
      versionControl: config.versionControl,
      continuitySupport: config.continuitySupport,
      
      // 생성 정보
      createdAt: new Date().toISOString(),
      createdBy: 'canvas_share_strategy_v4',
      
      // 버전 정보
      version: 1,
      schemaVersion: '4.0',
      
      // 커스텀 데이터
      ...customData
    };
  }

  /**
   * Canvas 제목 생성 (타입별 기본값)
   */
  static generateCanvasTitle(type: CanvasToolType, content?: any): string {
    const typeNames = {
      image: '이미지',
      text: '텍스트 노트',
      mindmap: '마인드맵',
      code: '코드',
      chart: '차트'
    };

    const typeName = typeNames[type] || type;
    
    // 콘텐츠 기반 제목 생성 시도
    if (content) {
      switch (type) {
        case 'image':
          const prompt = content.prompt || content.title;
          return prompt ? `${typeName}: ${prompt.substring(0, 30)}...` : `새 ${typeName}`;
          
        case 'text':
          const title = content.title;
          return title || `새 ${typeName}`;
          
        case 'mindmap':
          const label = content.label || content.title;
          return label ? `${typeName}: ${label}` : `새 ${typeName}`;
          
        case 'code':
          const language = content.language || 'JavaScript';
          return `${typeName} (${language})`;
          
        case 'chart':
          const chartType = content.type || 'bar';
          return `${typeName} (${chartType})`;
      }
    }
    
    return `새 ${typeName}`;
  }

  /**
   * Canvas 디버깅 정보 생성
   */
  static getDebugInfo(canvasId: string, type: CanvasToolType): Record<string, any> {
    const config = this.getCanvasConfig(type);
    
    return {
      canvasId,
      type,
      config,
      timestamp: new Date().toISOString(),
      strategVersion: '4.0'
    };
  }
}

export default CanvasShareStrategy;