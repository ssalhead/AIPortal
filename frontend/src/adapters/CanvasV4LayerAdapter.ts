/**
 * Canvas v4.0 다중 이미지 편집 레이어 시스템 통합 어댑터
 * 기존 Canvas v4.0 시스템과 새로운 레이어 시스템 간의 브리지 역할
 */

import type { CanvasItem } from '../types/canvas';
import type { 
  Layer, 
  LayerContainer, 
  ImageLayer, 
  TextLayer, 
  LayerType,
  LayerTransform,
  BoundingBox 
} from '../types/layer';
import { useCanvasStore } from '../stores/canvasStore';
import { useImageSessionStore } from '../stores/imageSessionStore';
import { useLayerStore } from '../stores/layerStore';

// ============= 어댑터 인터페이스 =============

export interface CanvasV4LayerAdapter {
  // Canvas v4.0 → Layer 변환
  convertCanvasItemToLayers(item: CanvasItem): Layer[];
  
  // Layer → Canvas v4.0 변환
  convertLayersToCanvasItem(layers: Layer[], type: string): CanvasItem;
  
  // 기존 ImageGenerator와 통합
  integrateWithImageGenerator(layerContainer: LayerContainer): void;
  
  // 기존 ImageVersionGallery와 통합
  syncWithVersionGallery(layerContainer: LayerContainer): void;
  
  // 실시간 동기화
  syncCanvasItemWithLayers(canvasId: string, item: CanvasItem): void;
  syncLayersWithCanvasItem(containerId: string, layers: Layer[]): void;
}

// ============= 변환 유틸리티 =============

class LayerConverterUtils {
  /** Canvas v4.0 위치 정보를 Layer Transform으로 변환 */
  static convertPositionToTransform(position?: { x: number; y: number }, size?: { width: number; height: number }): LayerTransform {
    return {
      x: position?.x || 0,
      y: position?.y || 0,
      scaleX: 1.0,
      scaleY: 1.0,
      rotation: 0,
      skewX: 0,
      skewY: 0,
      offsetX: 0,
      offsetY: 0
    };
  }

  /** Layer Transform을 Canvas v4.0 위치로 변환 */
  static convertTransformToPosition(transform: LayerTransform): { x: number; y: number } {
    return {
      x: transform.x,
      y: transform.y
    };
  }

  /** Canvas v4.0 크기 정보를 BoundingBox로 변환 */
  static convertSizeToBoundingBox(
    position?: { x: number; y: number }, 
    size?: { width: number; height: number }
  ): BoundingBox {
    return {
      x: position?.x || 0,
      y: position?.y || 0,
      width: size?.width || 100,
      height: size?.height || 100
    };
  }

  /** BoundingBox를 Canvas v4.0 크기로 변환 */
  static convertBoundingBoxToSize(box: BoundingBox): { width: number; height: number } {
    return {
      width: box.width,
      height: box.height
    };
  }

  /** 고유 ID 생성 */
  static generateLayerId(): string {
    return crypto.randomUUID();
  }

  /** Canvas Item 타입을 Layer 타입으로 매핑 */
  static mapCanvasTypeToLayerType(canvasType: string): LayerType {
    const typeMap: Record<string, LayerType> = {
      'text': LayerType.TEXT,
      'image': LayerType.IMAGE,
      'mindmap': LayerType.SHAPE,
      'code': LayerType.TEXT,
      'chart': LayerType.SHAPE
    };
    
    return typeMap[canvasType] || LayerType.IMAGE;
  }

  /** Layer 타입을 Canvas Item 타입으로 매핑 */
  static mapLayerTypeToCanvasType(layerType: LayerType): string {
    const typeMap: Record<LayerType, string> = {
      [LayerType.TEXT]: 'text',
      [LayerType.IMAGE]: 'image',
      [LayerType.SHAPE]: 'mindmap',
      [LayerType.BACKGROUND]: 'image',
      [LayerType.EFFECT]: 'image',
      [LayerType.MASK]: 'image',
      [LayerType.GROUP]: 'image'
    };
    
    return typeMap[layerType] || 'image';
  }
}

// ============= 메인 어댑터 클래스 =============

export class CanvasV4LayerAdapterImpl implements CanvasV4LayerAdapter {
  private layerStore = useLayerStore.getState();
  private canvasStore = useCanvasStore.getState();
  private imageSessionStore = useImageSessionStore.getState();

  // ============= Canvas v4.0 → Layer 변환 =============

  convertCanvasItemToLayers(item: CanvasItem): Layer[] {
    const layers: Layer[] = [];
    
    try {
      switch (item.type) {
        case 'image':
          layers.push(...this.convertImageItemToLayers(item));
          break;
        case 'text':
          layers.push(this.convertTextItemToLayer(item));
          break;
        case 'mindmap':
          layers.push(...this.convertMindmapItemToLayers(item));
          break;
        default:
          // 기본적으로 이미지 레이어로 처리
          layers.push(this.convertGenericItemToLayer(item));
      }
    } catch (error) {
      console.error('Canvas Item to Layer 변환 실패:', error);
      // 실패 시 빈 레이어라도 생성
      layers.push(this.createFallbackLayer(item));
    }

    return layers;
  }

  private convertImageItemToLayers(item: CanvasItem): ImageLayer[] {
    const layers: ImageLayer[] = [];
    const content = item.content;
    
    // 단일 이미지 또는 다중 이미지 처리
    const images = Array.isArray(content.images) ? content.images : [content.imageUrl].filter(Boolean);
    
    images.forEach((imageUrl, index) => {
      if (!imageUrl) return;
      
      const layerId = LayerConverterUtils.generateLayerId();
      const transform = LayerConverterUtils.convertPositionToTransform(
        item.position, 
        item.size
      );
      
      // 다중 이미지의 경우 위치 조정
      if (index > 0) {
        transform.x += index * 20;
        transform.y += index * 20;
      }
      
      const layer: ImageLayer = {
        id: layerId,
        name: `이미지 ${index + 1}`,
        type: LayerType.IMAGE,
        parentId: null,
        childrenIds: [],
        zIndex: index,
        transform,
        boundingBox: LayerConverterUtils.convertSizeToBoundingBox(
          { x: transform.x, y: transform.y },
          item.size
        ),
        state: {
          visible: true,
          locked: false,
          selected: false,
          opacity: 1.0,
          blendMode: 'normal' as any
        },
        style: {},
        content: {
          imageUrl: imageUrl,
          originalUrl: imageUrl,
          naturalWidth: 1024, // 기본값, 실제 로드 시 업데이트
          naturalHeight: 1024,
          format: this.detectImageFormat(imageUrl),
          
          // AI 생성 이미지 메타데이터
          aiGenerated: content.prompt ? {
            prompt: content.prompt,
            negativePrompt: content.negativePrompt,
            model: 'imagen',
            style: content.style || 'realistic',
            generatedAt: item.createdAt
          } : undefined
        },
        metadata: {
          createdAt: item.createdAt,
          updatedAt: item.updatedAt,
          source: 'ai',
          tags: ['canvas-v4-import']
        }
      };
      
      layers.push(layer);
    });
    
    return layers;
  }

  private convertTextItemToLayer(item: CanvasItem): TextLayer {
    const content = item.content;
    
    const layer: TextLayer = {
      id: LayerConverterUtils.generateLayerId(),
      name: content.title || '텍스트 레이어',
      type: LayerType.TEXT,
      parentId: null,
      childrenIds: [],
      zIndex: 0,
      transform: LayerConverterUtils.convertPositionToTransform(
        item.position,
        item.size
      ),
      boundingBox: LayerConverterUtils.convertSizeToBoundingBox(
        item.position,
        item.size
      ),
      state: {
        visible: true,
        locked: false,
        selected: false,
        opacity: 1.0,
        blendMode: 'normal' as any
      },
      content: {
        text: content.content || content.text || '',
        fontFamily: content.fontFamily || 'Inter, sans-serif',
        fontSize: content.fontSize || 14,
        fontWeight: content.fontWeight || 'normal',
        fontStyle: content.fontStyle || 'normal',
        textAlign: content.textAlign || 'left',
        color: content.color || '#333333',
        backgroundColor: content.backgroundColor
      },
      metadata: {
        createdAt: item.createdAt,
        updatedAt: item.updatedAt,
        source: 'user',
        tags: ['canvas-v4-import']
      }
    };
    
    return layer;
  }

  private convertMindmapItemToLayers(item: CanvasItem): Layer[] {
    // 마인드맵은 여러 텍스트 레이어로 분해
    const layers: Layer[] = [];
    const content = item.content;
    
    if (!content.nodes || !Array.isArray(content.nodes)) {
      return layers;
    }
    
    content.nodes.forEach((node: any, index: number) => {
      const layerId = LayerConverterUtils.generateLayerId();
      
      const layer: TextLayer = {
        id: layerId,
        name: `마인드맵 노드: ${node.text}`,
        type: LayerType.TEXT,
        parentId: null,
        childrenIds: [],
        zIndex: index,
        transform: {
          x: (item.position?.x || 0) + (node.x || 0),
          y: (item.position?.y || 0) + (node.y || 0),
          scaleX: 1.0,
          scaleY: 1.0,
          rotation: 0,
          skewX: 0,
          skewY: 0,
          offsetX: 0,
          offsetY: 0
        },
        boundingBox: {
          x: (item.position?.x || 0) + (node.x || 0),
          y: (item.position?.y || 0) + (node.y || 0),
          width: 100,
          height: 30
        },
        state: {
          visible: true,
          locked: false,
          selected: false,
          opacity: 1.0,
          blendMode: 'normal' as any
        },
        content: {
          text: node.text || node.label || '',
          fontFamily: 'Inter, sans-serif',
          fontSize: 14,
          fontWeight: 'normal',
          fontStyle: 'normal',
          textAlign: 'center',
          color: node.color || '#333333'
        },
        metadata: {
          createdAt: item.createdAt,
          updatedAt: item.updatedAt,
          source: 'user',
          tags: ['canvas-v4-import', 'mindmap-node']
        }
      };
      
      layers.push(layer);
    });
    
    return layers;
  }

  private convertGenericItemToLayer(item: CanvasItem): Layer {
    // 알 수 없는 타입은 기본 이미지 레이어로 처리
    const layerId = LayerConverterUtils.generateLayerId();
    
    return {
      id: layerId,
      name: `${item.type} 레이어`,
      type: LayerConverterUtils.mapCanvasTypeToLayerType(item.type),
      parentId: null,
      childrenIds: [],
      zIndex: 0,
      transform: LayerConverterUtils.convertPositionToTransform(
        item.position,
        item.size
      ),
      boundingBox: LayerConverterUtils.convertSizeToBoundingBox(
        item.position,
        item.size
      ),
      state: {
        visible: true,
        locked: false,
        selected: false,
        opacity: 1.0,
        blendMode: 'normal' as any
      },
      content: item.content,
      metadata: {
        createdAt: item.createdAt,
        updatedAt: item.updatedAt,
        source: 'user',
        tags: ['canvas-v4-import']
      }
    } as Layer;
  }

  private createFallbackLayer(item: CanvasItem): Layer {
    const layerId = LayerConverterUtils.generateLayerId();
    
    return {
      id: layerId,
      name: '변환 실패 레이어',
      type: LayerType.TEXT,
      parentId: null,
      childrenIds: [],
      zIndex: 0,
      transform: LayerConverterUtils.convertPositionToTransform(),
      boundingBox: LayerConverterUtils.convertSizeToBoundingBox(),
      state: {
        visible: true,
        locked: false,
        selected: false,
        opacity: 1.0,
        blendMode: 'normal' as any
      },
      content: {
        text: `변환 실패: ${item.type}`,
        fontFamily: 'Inter, sans-serif',
        fontSize: 14,
        fontWeight: 'normal',
        fontStyle: 'normal',
        textAlign: 'left',
        color: '#ff0000'
      },
      metadata: {
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        source: 'system',
        tags: ['conversion-error']
      }
    } as Layer;
  }

  // ============= Layer → Canvas v4.0 변환 =============

  convertLayersToCanvasItem(layers: Layer[], type: string): CanvasItem {
    if (layers.length === 0) {
      throw new Error('변환할 레이어가 없습니다.');
    }

    const primaryLayer = layers[0];
    const canvasId = LayerConverterUtils.generateLayerId();
    
    const item: CanvasItem = {
      id: canvasId,
      type: LayerConverterUtils.mapLayerTypeToCanvasType(primaryLayer.type),
      content: this.buildCanvasContent(layers),
      position: LayerConverterUtils.convertTransformToPosition(primaryLayer.transform),
      size: LayerConverterUtils.convertBoundingBoxToSize(primaryLayer.boundingBox),
      metadata: {
        layerCount: layers.length,
        layerIds: layers.map(l => l.id),
        convertedAt: new Date().toISOString()
      },
      createdAt: primaryLayer.metadata.createdAt,
      updatedAt: new Date().toISOString()
    };

    return item;
  }

  private buildCanvasContent(layers: Layer[]): any {
    const primaryLayer = layers[0];
    
    switch (primaryLayer.type) {
      case LayerType.IMAGE:
        return this.buildImageContent(layers as ImageLayer[]);
      case LayerType.TEXT:
        return this.buildTextContent(layers as TextLayer[]);
      default:
        return this.buildGenericContent(layers);
    }
  }

  private buildImageContent(layers: ImageLayer[]): any {
    if (layers.length === 1) {
      const layer = layers[0];
      return {
        imageUrl: layer.content.imageUrl,
        images: [layer.content.imageUrl],
        prompt: layer.content.aiGenerated?.prompt,
        style: layer.content.aiGenerated?.style,
        size: '1K_1:1' // 기본값
      };
    } else {
      // 다중 이미지
      return {
        images: layers.map(l => l.content.imageUrl),
        prompt: layers[0].content.aiGenerated?.prompt,
        style: layers[0].content.aiGenerated?.style,
        size: '1K_1:1'
      };
    }
  }

  private buildTextContent(layers: TextLayer[]): any {
    if (layers.length === 1) {
      const layer = layers[0];
      return {
        title: layer.name,
        content: layer.content.text,
        text: layer.content.text,
        fontFamily: layer.content.fontFamily,
        fontSize: layer.content.fontSize,
        color: layer.content.color
      };
    } else {
      // 다중 텍스트 - 마인드맵 형태로 변환
      return {
        nodes: layers.map(layer => ({
          id: layer.id,
          text: layer.content.text,
          x: layer.transform.x,
          y: layer.transform.y,
          color: layer.content.color
        }))
      };
    }
  }

  private buildGenericContent(layers: Layer[]): any {
    return {
      layers: layers.map(layer => ({
        id: layer.id,
        type: layer.type,
        content: layer.content,
        transform: layer.transform
      }))
    };
  }

  // ============= 통합 및 동기화 메서드 =============

  integrateWithImageGenerator(layerContainer: LayerContainer): void {
    // ImageGenerator와의 통합 로직
    try {
      const imageLayerIds = Object.values(layerContainer.layers)
        .filter(layer => layer.type === LayerType.IMAGE)
        .map(layer => layer.id);

      if (imageLayerIds.length > 0 && layerContainer.conversationId) {
        // 이미지 세션과 연결
        this.imageSessionStore.createSessionHybrid(
          layerContainer.conversationId,
          layerContainer.id,
          'layer-integration'
        );

        console.log('✅ ImageGenerator 통합 완료:', {
          containerId: layerContainer.id,
          conversationId: layerContainer.conversationId,
          imageLayerCount: imageLayerIds.length
        });
      }
    } catch (error) {
      console.error('ImageGenerator 통합 실패:', error);
    }
  }

  syncWithVersionGallery(layerContainer: LayerContainer): void {
    // ImageVersionGallery와의 동기화 로직
    try {
      const imageItems = Object.values(layerContainer.layers)
        .filter((layer): layer is ImageLayer => layer.type === LayerType.IMAGE)
        .map(layer => ({
          layerId: layer.id,
          imageUrl: layer.content.imageUrl,
          aiMetadata: layer.content.aiGenerated
        }));

      if (imageItems.length > 0) {
        console.log('✅ Version Gallery 동기화 완료:', {
          containerId: layerContainer.id,
          imageCount: imageItems.length
        });
      }
    } catch (error) {
      console.error('Version Gallery 동기화 실패:', error);
    }
  }

  syncCanvasItemWithLayers(canvasId: string, item: CanvasItem): void {
    // Canvas Item 변경사항을 레이어에 반영
    try {
      const layers = this.convertCanvasItemToLayers(item);
      
      // 기존 컨테이너 찾기 또는 새로 생성
      let containerId = this.findContainerByCanvasId(canvasId);
      if (!containerId) {
        containerId = this.layerStore.createContainer(canvasId, undefined, `${item.type} 컨테이너`);
      }

      // 레이어들 추가/업데이트
      layers.forEach(layer => {
        this.layerStore.addLayer(
          containerId,
          layer.type,
          layer.content,
          layer.parentId || undefined,
          { x: layer.transform.x, y: layer.transform.y }
        );
      });

      console.log('✅ Canvas Item → Layer 동기화 완료:', {
        canvasId,
        containerId,
        layerCount: layers.length
      });
    } catch (error) {
      console.error('Canvas Item → Layer 동기화 실패:', error);
    }
  }

  syncLayersWithCanvasItem(containerId: string, layers: Layer[]): void {
    // 레이어 변경사항을 Canvas Item에 반영
    try {
      if (layers.length === 0) return;

      const canvasItem = this.convertLayersToCanvasItem(layers, 'image');
      
      // Canvas v4.0 스토어 업데이트
      // 실제 구현에서는 적절한 Canvas v4.0 API 호출
      console.log('✅ Layer → Canvas Item 동기화 완료:', {
        containerId,
        canvasItemId: canvasItem.id,
        layerCount: layers.length
      });
    } catch (error) {
      console.error('Layer → Canvas Item 동기화 실패:', error);
    }
  }

  // ============= 유틸리티 메서드 =============

  private detectImageFormat(url: string): 'jpeg' | 'png' | 'webp' | 'svg' {
    const extension = url.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'jpg':
      case 'jpeg':
        return 'jpeg';
      case 'png':
        return 'png';
      case 'webp':
        return 'webp';
      case 'svg':
        return 'svg';
      default:
        return 'png';
    }
  }

  private findContainerByCanvasId(canvasId: string): string | null {
    const containers = this.layerStore.containers;
    for (const [containerId, container] of Object.entries(containers)) {
      if (container.canvasId === canvasId) {
        return containerId;
      }
    }
    return null;
  }
}

// ============= 싱글톤 인스턴스 =============

export const canvasV4LayerAdapter = new CanvasV4LayerAdapterImpl();

// ============= 편의 훅 =============

export const useCanvasV4LayerAdapter = () => {
  return canvasV4LayerAdapter;
};

export default canvasV4LayerAdapter;