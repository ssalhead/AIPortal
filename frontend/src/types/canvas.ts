/**
 * Canvas 관련 타입 정의
 */

export type CanvasToolType = 'text' | 'image' | 'mindmap' | 'code' | 'chart';

export interface CanvasItem {
  id: string;
  type: CanvasToolType;
  content: any;
  position?: { x: number; y: number };
  size?: { width: number; height: number };
  metadata?: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface TextNote {
  title: string;
  content: string;
  formatting?: {
    bold?: boolean;
    italic?: boolean;
    color?: string;
  };
}

export interface ImageGeneration {
  prompt: string;
  imageUrl?: string;
  status: 'pending' | 'generating' | 'completed' | 'error';
  error?: string;
}

export interface MindMapNode {
  id: string;
  label: string;
  children?: MindMapNode[];
  collapsed?: boolean;
  color?: string;
}