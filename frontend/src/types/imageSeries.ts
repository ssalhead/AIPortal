/**
 * 이미지 시리즈 관련 TypeScript 타입 정의
 */

export interface ImageSeries {
  id: string;
  title: string;
  series_type: SeriesType;
  current_count: number;
  target_count: number;
  progress_percentage: number;
  completion_status: CompletionStatus;
  created_at: string;
  updated_at: string;
  description?: string;
  base_style?: string;
  consistency_prompt?: string;
  template_config?: SeriesTemplateConfig;
}

export interface SeriesImage {
  id: string;
  image_url: string;
  series_index: number;
  prompt: string;
  status: string;
  created_at: string;
  metadata?: any;
}

export interface SeriesTemplate {
  id: string;
  name: string;
  series_type: SeriesType;
  description?: string;
  category?: string;
  default_target_count: number;
  recommended_style: string;
  rating: number;
  usage_count: number;
  tags: string[];
  template_config?: SeriesTemplateConfig;
  prompt_templates?: string[];
}

export interface SeriesTemplateConfig {
  layout?: string;
  aspect_ratio?: string;
  panel_count?: number[];
  slide_count?: number[];
  brand_elements?: string[];
  step_indicators?: boolean;
  scene_progression?: boolean;
  style_consistency?: 'low' | 'medium' | 'high' | 'very_high';
  [key: string]: any;
}

export interface SeriesCreationRequest {
  title: string;
  series_type: SeriesType;
  target_count: number;
  base_style: string;
  consistency_prompt?: string;
  template_id?: string;
  custom_config?: SeriesTemplateConfig;
  base_prompts: string[];
  character_descriptions?: Record<string, string>;
}

export interface SeriesGenerationProgress {
  status: 'generating' | 'completed' | 'failed' | 'series_completed' | 'series_failed';
  series_id: string;
  current_index?: number;
  total_count?: number;
  prompt?: string;
  progress?: number;
  image_id?: string;
  image_url?: string;
  series_index?: number;
  error?: string;
  completion_time?: string;
  total_generated?: number;
}

export type SeriesType = 'webtoon' | 'instagram' | 'brand' | 'educational' | 'story' | 'custom';

export type CompletionStatus = 'planning' | 'generating' | 'completed' | 'failed' | 'paused';

export interface SeriesTypeConfig {
  name: string;
  description: string;
  recommended_count: number[];
  aspect_ratios: string[];
  features: string[];
  icon: string;
  color: string;
}

export const SERIES_TYPE_CONFIGS: Record<SeriesType, SeriesTypeConfig> = {
  webtoon: {
    name: '웹툰 페이지',
    description: '세로형 패널 구성의 웹툰 페이지 시리즈',
    recommended_count: [4, 6, 8],
    aspect_ratios: ['3:4', '2:3'],
    features: ['character_consistency', 'panel_layout', 'story_flow'],
    icon: '📚',
    color: 'bg-purple-500'
  },
  instagram: {
    name: '인스타그램 캐러셀',
    description: '소셜 미디어용 정사각형 이미지 시리즈',
    recommended_count: [3, 4, 5, 6],
    aspect_ratios: ['1:1'],
    features: ['brand_consistency', 'social_optimized', 'swipe_friendly'],
    icon: '📱',
    color: 'bg-pink-500'
  },
  brand: {
    name: '브랜드 시리즈',
    description: '일관된 브랜드 아이덴티티를 가진 마케팅 자료',
    recommended_count: [3, 4, 5],
    aspect_ratios: ['1:1', '16:9', '4:3'],
    features: ['brand_colors', 'logo_integration', 'professional_style'],
    icon: '🏢',
    color: 'bg-blue-500'
  },
  educational: {
    name: '교육용 단계별',
    description: '학습을 위한 단계별 설명 이미지',
    recommended_count: [3, 4, 5, 6],
    aspect_ratios: ['16:9', '4:3'],
    features: ['step_indicators', 'clear_diagrams', 'instructional_design'],
    icon: '📖',
    color: 'bg-green-500'
  },
  story: {
    name: '스토리보드',
    description: '영화나 애니메이션용 스토리보드',
    recommended_count: [4, 6, 8, 12],
    aspect_ratios: ['16:9', '21:9'],
    features: ['cinematic_style', 'scene_continuity', 'character_consistency'],
    icon: '🎬',
    color: 'bg-yellow-500'
  },
  custom: {
    name: '커스텀 시리즈',
    description: '사용자 정의 설정을 가진 시리즈',
    recommended_count: [2, 3, 4, 5, 6, 8, 10],
    aspect_ratios: ['1:1', '4:3', '3:4', '16:9', '9:16'],
    features: ['flexible_layout', 'custom_style', 'user_defined'],
    icon: '⚙️',
    color: 'bg-gray-500'
  }
};