/**
 * 스트리밍 관련 공통 유틸리티
 */

export interface StreamingConfig {
  /** 청크 크기 범위 */
  chunkSizeRange: [number, number];
  /** 기본 타이핑 속도 범위 (ms) */
  baseDelayRange: [number, number];
  /** 글자당 추가 딜레이 (ms) */
  characterDelay: number;
  /** 단어 간 일시정지 (ms) */
  wordPause: number;
  /** 문장 끝 일시정지 (ms) */
  sentencePause: number;
  /** 단락 끝 일시정지 (ms) */
  paragraphPause: number;
  /** 스르륵 흐름 가속 효과 */
  flowAcceleration: boolean;
  /** 적응형 속도 조절 */
  adaptiveSpeed: boolean;
}

export const DEFAULT_STREAMING_CONFIG: StreamingConfig = {
  chunkSizeRange: [3, 8],
  baseDelayRange: [10, 30],
  characterDelay: 2,
  wordPause: 5,
  sentencePause: 30,
  paragraphPause: 60,
  flowAcceleration: true,
  adaptiveSpeed: true
};

/**
 * 텍스트를 자연스러운 청크로 분할
 */
export function splitTextIntoChunks(text: string, config: StreamingConfig = DEFAULT_STREAMING_CONFIG): string[] {
  if (!text.trim()) {
    return [];
  }

  const [minSize, maxSize] = config.chunkSizeRange;
  const chunks: string[] = [];
  let start = 0;

  while (start < text.length) {
    let chunkEnd = start + maxSize;
    
    // 텍스트 끝을 넘지 않도록 조정
    if (chunkEnd >= text.length) {
      chunkEnd = text.length;
    } else {
      // 자연스러운 분할점 찾기
      const textSegment = text.slice(start, chunkEnd + 20);
      let bestSplit = chunkEnd;
      
      // 1. 한글 음절 경계 우선
      for (let i = minSize; i < Math.min(textSegment.length, maxSize); i++) {
        const char = textSegment[i];
        if (char && char.charCodeAt(0) >= 0xAC00 && char.charCodeAt(0) <= 0xD7A3) {
          const candidatePos = start + i + 1;
          if (candidatePos <= text.length && (i + 1) >= minSize) {
            bestSplit = candidatePos;
            break;
          }
        }
      }
      
      // 2. 구두점 찾기
      if (bestSplit === chunkEnd) {
        const patterns = [', ', '、 ', ' '];
        for (const pattern of patterns) {
          const patternPos = textSegment.lastIndexOf(pattern, Math.max(1, Math.floor(minSize / 3)));
          if (patternPos !== -1) {
            const candidatePos = start + patternPos + pattern.length;
            if (candidatePos <= text.length) {
              bestSplit = candidatePos;
              break;
            }
          }
        }
      }
      
      // 3. 영문 단어 경계
      if (bestSplit === chunkEnd) {
        for (let i = minSize; i < Math.min(textSegment.length, maxSize); i++) {
          const char = textSegment[i];
          if (char && (char === ' ' || !/[a-zA-Z0-9]/.test(char))) {
            const candidatePos = start + i + 1;
            if (candidatePos <= text.length) {
              bestSplit = candidatePos;
              break;
            }
          }
        }
      }
      
      chunkEnd = Math.min(bestSplit, text.length);
    }
    
    const chunk = text.slice(start, chunkEnd);
    if (chunk) {
      chunks.push(chunk);
    }
    
    start = chunkEnd;
  }

  return chunks;
}

/**
 * 스트리밍 지연 시간 계산
 */
export function calculateDelay(chunk: string, config: StreamingConfig = DEFAULT_STREAMING_CONFIG): number {
  const baseDelay = config.baseDelayRange[0] + 
    Math.random() * (config.baseDelayRange[1] - config.baseDelayRange[0]);
  
  const characterDelay = chunk.length * config.characterDelay;
  
  // 단어 수 계산
  const wordCount = chunk.split(/\s+/).length;
  const wordDelay = wordCount * config.wordPause;
  
  // 문장 끝 체크
  const sentenceEndDelay = /[.!?]$/.test(chunk.trim()) ? config.sentencePause : 0;
  
  // 단락 끝 체크
  const paragraphEndDelay = chunk.includes('\n\n') ? config.paragraphPause : 0;
  
  return baseDelay + characterDelay + wordDelay + sentenceEndDelay + paragraphEndDelay;
}

/**
 * 청크 유형 감지
 */
export enum ChunkType {
  TEXT = 'text',
  CODE = 'code',
  QUOTE = 'quote',
  HEADER = 'header',
  LIST = 'list'
}

export function detectChunkType(chunk: string): ChunkType {
  const trimmed = chunk.trim();
  
  if (trimmed.startsWith('```') || trimmed.includes('`')) {
    return ChunkType.CODE;
  }
  
  if (trimmed.startsWith('>')) {
    return ChunkType.QUOTE;
  }
  
  if (trimmed.startsWith('#')) {
    return ChunkType.HEADER;
  }
  
  if (/^[-*+]\s/.test(trimmed) || /^\d+\.\s/.test(trimmed)) {
    return ChunkType.LIST;
  }
  
  return ChunkType.TEXT;
}

/**
 * 스트리밍 상태 관리를 위한 클래스
 */
export class StreamingManager {
  private chunks: string[] = [];
  private currentIndex: number = 0;
  private isComplete: boolean = false;
  private config: StreamingConfig;
  
  constructor(config: StreamingConfig = DEFAULT_STREAMING_CONFIG) {
    this.config = config;
  }
  
  setText(text: string): void {
    this.chunks = splitTextIntoChunks(text, this.config);
    this.currentIndex = 0;
    this.isComplete = false;
  }
  
  getNextChunk(): string | null {
    if (this.currentIndex >= this.chunks.length) {
      this.isComplete = true;
      return null;
    }
    
    return this.chunks[this.currentIndex++];
  }
  
  hasMore(): boolean {
    return !this.isComplete && this.currentIndex < this.chunks.length;
  }
  
  getProgress(): number {
    return this.chunks.length === 0 ? 0 : (this.currentIndex / this.chunks.length) * 100;
  }
  
  reset(): void {
    this.chunks = [];
    this.currentIndex = 0;
    this.isComplete = false;
  }
  
  isCompleted(): boolean {
    return this.isComplete;
  }
}