/**
 * 이미지 세션 관련 타입 정의
 * 순환 import 문제를 해결하기 위해 별도 파일로 분리
 */

// 이미지 버전 인터페이스
export interface ImageVersion {
  id: string;
  versionNumber: number;        // 1, 2, 3, 4...
  prompt: string;
  negativePrompt: string;
  style: string;
  size: string;
  imageUrl: string;
  parentVersionId?: string;     // 브랜치 추적용 (어떤 이미지를 기반으로 생성되었는지)
  createdAt: string;
  isSelected: boolean;          // 현재 선택된 베이스 이미지 여부
  status: 'generating' | 'completed' | 'failed';
}

// 이미지 생성 세션 인터페이스
export interface ImageGenerationSession {
  conversationId: string;
  theme: string;               // "강아지", "수영장" 등 추출된 주제
  versions: ImageVersion[];
  selectedVersionId: string;   // 현재 선택된 버전 ID
  basePrompt: string;          // 최초 프롬프트
  evolutionHistory: string[];  // 프롬프트 변화 히스토리
  createdAt: string;
  updatedAt: string;
}