/**
 * AI 레이아웃 서비스 v1.0
 * Canvas AI 레이아웃 시스템 클라이언트
 */

// import { CanvasItem } from '../types/canvas';

export interface AILayoutAnalysis {
  elements: AIElementAnalysis[];
  composition: CompositionAnalysis;
  llm_insights: LLMAnalysis;
  optimization_suggestions: OptimizationSuggestion[];
  analyzed_at: string;
}

export interface AIElementAnalysis {
  id: string;
  node_type: string;
  element_type: string;
  importance: 'primary' | 'secondary' | 'tertiary' | 'decorative';
  visual_properties: VisualProperties;
  spatial_properties: SpatialProperties;
  relationships: ElementRelationships;
}

export interface CompositionAnalysis {
  distribution: {
    center_of_mass: { x: number; y: number };
    balance_score: number;
    balance: 'balanced' | 'unbalanced' | 'moderate';
  };
  grid_alignment: {
    aligned: boolean;
    x_alignment_score: number;
    y_alignment_score: number;
    overall_score: number;
  };
  visual_hierarchy: {
    hierarchy_groups: Record<string, number>;
    hierarchy_score: number;
    has_clear_hierarchy: boolean;
  };
  color_harmony: {
    color_count: number;
    colors: string[];
    harmony_score: number;
    is_harmonious: boolean;
  };
  spacing_density: {
    density_ratio: number;
    density: 'sparse' | 'balanced' | 'dense' | 'overcrowded';
    spacing_score: number;
  };
  design_principles_score: Record<string, number>;
}

export interface LLMAnalysis {
  overall_score: number;
  design_principles: {
    hierarchy: number;
    balance: number;
    contrast: number;
    alignment: number;
  };
  strengths: string[];
  weaknesses: string[];
  improvements: OptimizationSuggestion[];
  recommended_templates: string[];
  user_experience_insights: string;
}

export interface OptimizationSuggestion {
  id: string;
  type: 'layout_optimization' | 'alignment_fix' | 'color_harmony' | 'typography_improvement' | 'spacing_adjustment' | 'hierarchy_enhancement' | 'template_suggestion' | 'content_optimization';
  priority: 'critical' | 'high' | 'medium' | 'low' | 'optional';
  title: string;
  description: string;
  action: string;
  expected_improvement: string;
  confidence: number;
  auto_fix_available: boolean;
  fix_options?: FixOption[];
  palette_options?: ColorPalette[];
  typography_sets?: string[];
  template_recommendations?: TemplateRecommendation[];
}

export interface FixOption {
  type: string;
  name: string;
}

export interface ColorPalette {
  name: string;
  colors: string[];
}

export interface TemplateRecommendation {
  template_id: string;
  name: string;
  preview: any;
}

export interface VisualProperties {
  color: {
    fill?: string;
    stroke?: string;
    stroke_width: number;
  };
  typography: {
    font_family?: string;
    font_size?: number;
    font_style?: string;
    text_align?: string;
  };
  effects: {
    opacity: number;
    shadow: boolean;
    blur: number;
  };
}

export interface SpatialProperties {
  position: { x: number; y: number };
  size: { width?: number; height?: number };
  transform: {
    scale_x: number;
    scale_y: number;
    rotation: number;
    skew_x: number;
    skew_y: number;
  };
  bounds: {
    left: number;
    top: number;
    right: number;
    bottom: number;
  };
  center: { x: number; y: number };
}

export interface ElementRelationships {
  parent_id?: string;
  layer_index: number;
  z_index: number;
  is_grouped: boolean;
}

export interface SmartGrid {
  type: 'uniform' | 'golden_ratio' | 'rule_of_thirds' | 'fibonacci' | 'dynamic';
  vertical_lines: number[];
  horizontal_lines: number[];
  focal_points?: FocalPoint[];
  zones?: GridZone[];
  snap_points?: SnapPoint[];
}

export interface FocalPoint {
  x: number;
  y: number;
  importance: number;
}

export interface GridZone {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  priority: number;
  recommended_content: string[];
}

export interface SnapPoint {
  x: number;
  y: number;
}

export interface Template {
  template_id: string;
  name: string;
  category: string;
  industry: string;
  style: string;
  canvas_size: { width: number; height: number };
  preview_elements: TemplateElement[];
  match_score?: number;
}

export interface TemplateElement {
  type: string;
  position: { x: number; y: number };
  size: { width: number; height: number };
  preview_content: string;
}

export interface AILayoutHint {
  type: 'positioning' | 'typography' | 'color_harmony' | 'spacing';
  title: string;
  description: string;
  position?: { x: number; y: number };
  suggested_font_size?: number;
  suggested_colors?: string[];
}

export class AILayoutService {
  private baseUrl = '/api/v1/canvas/ai-layout';

  /**
   * Canvas 레이아웃 분석
   */
  async analyzeCanvas(canvasData: any): Promise<AILayoutAnalysis> {
    const response = await fetch(`${this.baseUrl}/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(canvasData),
    });

    if (!response.ok) {
      throw new Error(`레이아웃 분석 실패: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data.analysis;
  }

  /**
   * AI 제안 생성
   */
  async getSuggestions(canvasData: any, context?: any): Promise<{
    suggestions: OptimizationSuggestion[];
    analysis_summary: any;
    user_insights: any;
    performance_score: number;
    suggestion_count: number;
  }> {
    const response = await fetch(`${this.baseUrl}/suggestions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        canvas_data: canvasData,
        context: context || {}
      }),
    });

    if (!response.ok) {
      throw new Error(`AI 제안 생성 실패: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * 제안 피드백 전송
   */
  async recordFeedback(
    suggestionId: string, 
    feedback: 'accepted' | 'rejected' | 'modified', 
    rating?: number
  ): Promise<void> {
    const response = await fetch(`${this.baseUrl}/suggestions/${suggestionId}/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ feedback, rating }),
    });

    if (!response.ok) {
      throw new Error(`피드백 전송 실패: ${response.statusText}`);
    }
  }

  /**
   * 스마트 그리드 생성
   */
  async generateSmartGrid(
    stage: { width: number; height: number }, 
    gridType: 'uniform' | 'golden_ratio' | 'rule_of_thirds' | 'fibonacci' | 'dynamic' = 'dynamic'
  ): Promise<SmartGrid> {
    const response = await fetch(`${this.baseUrl}/grid/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        stage,
        grid_type: gridType
      }),
    });

    if (!response.ok) {
      throw new Error(`스마트 그리드 생성 실패: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data.grid;
  }

  /**
   * 요소 자동 정렬
   */
  async autoAlignElements(
    elements: any[], 
    grid: SmartGrid,
    strategy: 'auto_detect' | 'left_align' | 'center_align' | 'right_align' | 'distribute' = 'auto_detect'
  ): Promise<any[]> {
    const response = await fetch(`${this.baseUrl}/align`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        elements,
        grid,
        strategy
      }),
    });

    if (!response.ok) {
      throw new Error(`자동 정렬 실패: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data.aligned_elements;
  }

  /**
   * 레이아웃 최적화
   */
  async optimizeLayout(
    elements: any[], 
    stage: { width: number; height: number },
    optimizationType: 'minimize_overlap' | 'maximize_readability' | 'optimize_flow' | 'enhance_hierarchy' | 'balance_composition' = 'balance_composition'
  ): Promise<any[]> {
    const response = await fetch(`${this.baseUrl}/optimize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        elements,
        stage,
        optimization_type: optimizationType
      }),
    });

    if (!response.ok) {
      throw new Error(`레이아웃 최적화 실패: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data.optimized_elements;
  }

  /**
   * 템플릿 목록 조회
   */
  async getTemplates(filters?: {
    category?: string;
    industry?: string;
    style?: string;
  }): Promise<Template[]> {
    const params = new URLSearchParams();
    if (filters?.category) params.append('category', filters.category);
    if (filters?.industry) params.append('industry', filters.industry);
    if (filters?.style) params.append('style', filters.style);

    const response = await fetch(`${this.baseUrl}/templates?${params.toString()}`);

    if (!response.ok) {
      throw new Error(`템플릿 조회 실패: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data.templates;
  }

  /**
   * 템플릿 적용
   */
  async applyTemplate(
    templateId: string, 
    contentData: Record<string, any>,
    customizations?: {
      color_palette?: string;
      typography_set?: string;
    }
  ): Promise<any> {
    const response = await fetch(`${this.baseUrl}/templates/${templateId}/apply`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        content_data: contentData,
        customizations: customizations || {}
      }),
    });

    if (!response.ok) {
      throw new Error(`템플릿 적용 실패: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data.canvas;
  }

  /**
   * 템플릿 리소스 조회 (색상 팔레트, 타이포그래피 등)
   */
  async getTemplateResources(): Promise<{
    color_palettes: Record<string, any>;
    typography_sets: Record<string, any>;
    template_categories: string[];
    industry_types: string[];
    layout_styles: string[];
  }> {
    const response = await fetch(`${this.baseUrl}/templates/resources`);

    if (!response.ok) {
      throw new Error(`템플릿 리소스 조회 실패: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * 자동 수정 적용
   */
  async applyAutoFixes(canvasData: any, suggestionIds: string[]): Promise<void> {
    const response = await fetch(`${this.baseUrl}/auto-fix`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        canvas_data: canvasData,
        suggestion_ids: suggestionIds
      }),
    });

    if (!response.ok) {
      throw new Error(`자동 수정 적용 실패: ${response.statusText}`);
    }
  }

  /**
   * 실시간 레이아웃 힌트
   */
  async getRealtimeHints(
    canvasData: any, 
    currentOperation?: { type: string; [key: string]: any }
  ): Promise<AILayoutHint[]> {
    const response = await fetch(`${this.baseUrl}/hints`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        canvas_data: canvasData,
        current_operation: currentOperation || {}
      }),
    });

    if (!response.ok) {
      throw new Error(`실시간 힌트 생성 실패: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data.hints;
  }

  /**
   * 사용자 개인화 정보 조회
   */
  async getUserPersonalization(): Promise<{
    user_id: string;
    design_preferences: {
      preferred_styles: string[];
      color_preferences: string[];
      layout_patterns: string[];
    };
    experience_level: string;
    personalized_suggestions_enabled: boolean;
  }> {
    const response = await fetch(`${this.baseUrl}/personalization`);

    if (!response.ok) {
      throw new Error(`개인화 정보 조회 실패: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * AI 시스템 성능 지표 조회
   */
  async getPerformanceMetrics(): Promise<{
    suggestions_generated: number;
    suggestions_accepted: number;
    suggestions_rejected: number;
    user_satisfaction_score: number;
  }> {
    const response = await fetch(`${this.baseUrl}/performance`);

    if (!response.ok) {
      throw new Error(`성능 지표 조회 실패: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data.performance_metrics;
  }
}

// 전역 인스턴스
export const aiLayoutService = new AILayoutService();