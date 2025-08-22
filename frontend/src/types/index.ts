/**
 * AI 포탈 타입 정의
 */

// 사용자 타입
export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  is_superuser?: boolean;
  created_at: string;
}

// 채팅 메시지 타입
export interface ChatMessage {
  id?: string;
  message: string;
  model: string;
  agent_type: string;
  timestamp?: string;
  user_id?: string;
  session_id?: string;
  include_citations?: boolean;
  max_sources?: number;
  min_confidence?: number;
}

// 채팅 응답 타입
export interface ChatResponse {
  response: string;
  agent_used: string;
  model_used: string;
  timestamp: string;
  user_id: string;
  session_id?: string;
  citations?: Citation[];
  sources?: Source[];
  citation_stats?: CitationStats;
  metadata?: ChatMetadata;
  canvas_data?: CanvasData; // Canvas 데이터 추가
}

// Canvas 데이터 타입
export interface CanvasData {
  type: string; // "image", "mindmap", "diagram", etc.
  title: string;
  description: string;
  image_data?: {
    job_id: string;
    prompt: string;
    style: string;
    size: string;
    num_images: number;
    generation_result: {
      status: string;
      images: string[];
      estimated_completion_time?: string;
      metadata?: any;
    };
  };
  elements?: any[];
  connections?: any[];
  metadata?: {
    created_by: string;
    canvas_type: string;
    [key: string]: any;
  };
}

// Canvas Artifact 타입 - Artifact 링크 시스템용
export interface CanvasArtifact {
  id: string;
  type: 'image' | 'mindmap' | 'diagram' | 'text' | 'code';
  title: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  canvas_data: CanvasData;
  created_at: string;
  updated_at: string;
  message_id: string; // 연결된 메시지 ID
  conversation_id?: string; // 대화 ID
}

// 채팅 메타데이터 타입
export interface ChatMetadata {
  search_queries?: string[];
  original_query?: string;
  context_integrated_queries?: string[];
  has_conversation_context?: boolean;
  needs_more_info?: boolean;
  information_gaps?: InformationGap[];
  suggested_questions?: string[];
  context_applied?: boolean;
  search_results_count?: number;
  processing_time_ms?: number;
  model_confidence?: number;
  [key: string]: unknown;
}

// 스트리밍 진행 메타데이터 타입
export interface StreamingProgressMetadata {
  step: string;
  progress: number;
  total_steps?: number;
  current_operation?: string;
  estimated_time_remaining?: number;
  search_query?: string;
  sources_found?: number;
  [key: string]: unknown;
}

// 대화 메시지 타입 (UI용)
export interface Message {
  id: string;
  content: string; // ChatPage에서 사용하는 필드명
  text?: string;   // ChatMessage 컴포넌트에서 사용하는 필드명 
  isUser: boolean;
  timestamp: string;
  model?: string;
  agentType?: string;
  citations?: Citation[];
  sources?: Source[];
  searchResults?: SearchResult[];
  searchQuery?: string;
  originalQuery?: string;
  hasContext?: boolean;
  isTyping?: boolean;
  isLoading?: boolean;
  searchStatus?: {
    isSearching: boolean;
    currentStep: string;
    progress: number;
  };
  streamingChunk?: string;
  isStreamingMode?: boolean;
  canvas_artifacts?: CanvasArtifact[]; // 연결된 Canvas 작업들
  canvasData?: CanvasData; // 직접 연결된 Canvas 데이터
}

// 검색 결과 타입
export interface SearchResult {
  id: string;
  title: string;
  url: string;
  snippet: string;
  domain: string;
  publishedDate?: string;
  relevanceScore?: number;
  thumbnail?: string;
}

// 인용 타입
export interface Citation {
  id: string;
  text: string;
  sourceId: string;
  startPosition: number;
  endPosition: number;
  confidence: number;
  context?: string;
  createdAt: string;
}

// 출처 타입
export interface Source {
  id: string;
  title: string;
  url?: string;
  sourceType: string;
  author?: string;
  publishedDate?: string;
  accessedDate: string;
  domain?: string;
  description?: string;
  thumbnail?: string;
  language?: string;
  reliabilityScore: number;
  metadata?: Record<string, unknown>;
}

// 인용 통계 타입
export interface CitationStats {
  totalCitations: number;
  uniqueSources: number;
  avgConfidence: number;
  sourceTypeDistribution: Record<string, number>;
  mostCitedSources: Source[];
  citationTrends?: Record<string, any>;
}

// 정보 부족 분석 관련 타입
export interface InformationGap {
  type: 'temporal' | 'spatial' | 'conditional' | 'preferential' | 'quantitative' | 'categorical';
  field: string;
  description: string;
  urgency: 'critical' | 'high' | 'medium' | 'low';
  question: string;
  suggestions: string[];
  context_hint?: string;
}

// 대화 히스토리 타입
export interface ConversationHistory {
  id: string;
  message: string;
  response: string;
  timestamp: string;
  agent_type: string;
  model: string;
}

// AI 에이전트 타입
export interface AgentInfo {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
  supported_models: string[];
  is_enabled: boolean;
}

// 에이전트 실행 요청 타입
export interface AgentExecuteRequest {
  agent_id: string;
  input_data: Record<string, any>;
  model: string;
}

// 에이전트 실행 응답 타입
export interface AgentExecuteResponse {
  agent_id: string;
  result: Record<string, any>;
  execution_time_ms: number;
  model_used: string;
}

// LLM 제공업체 타입
export type LLMProvider = 'claude' | 'gemini';

// LLM 모델 타입
export type LLMModel = 'claude-4' | 'claude-3.7' | 'claude-3.5' | 'claude-haiku' | 'gemini-2.5-pro' | 'gemini-2.5-flash' | 'gemini-2.0-pro' | 'gemini-2.0-flash';

// 에이전트 타입 (none 추가)
export type AgentType = 'none' | 'web_search' | 'deep_research' | 'canvas';

// 모델 정보 인터페이스
export interface ModelInfo {
  id: LLMModel;
  name: string;
  description: string;
  provider: LLMProvider;
  speed: 'fast' | 'medium' | 'slow';
  capabilities: string[];
  isRecommended?: boolean;
}

// 에이전트 정보 인터페이스
export interface AgentTypeInfo {
  id: AgentType;
  name: string;
  description: string;
  icon: string;
  color: string;
  isDefault?: boolean;
}

// 제공업체별 모델 맵
export const MODEL_MAP: Record<LLMProvider, ModelInfo[]> = {
  claude: [
    {
      id: 'claude-4',
      name: 'Claude 4.0 Sonnet',
      description: '가장 최신이고 강력한 모델',
      provider: 'claude',
      speed: 'medium',
      capabilities: ['reasoning', 'coding', 'analysis', 'creative'],
      isRecommended: true,
    },
    {
      id: 'claude-3.7',
      name: 'Claude 3.7 Sonnet',
      description: '균형잡힌 성능과 속도',
      provider: 'claude',
      speed: 'medium',
      capabilities: ['reasoning', 'coding', 'analysis'],
    },
    {
      id: 'claude-3.5',
      name: 'Claude 3.5 Sonnet',
      description: '안정적인 범용 모델',
      provider: 'claude',
      speed: 'medium',
      capabilities: ['reasoning', 'coding', 'analysis'],
    },
    {
      id: 'claude-haiku',
      name: 'Claude 3.5 Haiku',
      description: '빠른 응답 속도',
      provider: 'claude',
      speed: 'fast',
      capabilities: ['reasoning', 'quick_tasks'],
    },
  ],
  gemini: [
    {
      id: 'gemini-2.5-pro',
      name: 'Gemini 2.5 Pro',
      description: '최신 고성능 멀티모달 모델',
      provider: 'gemini',
      speed: 'medium',
      capabilities: ['reasoning', 'multimodal', 'analysis', 'creative'],
      isRecommended: true,
    },
    {
      id: 'gemini-2.5-flash',
      name: 'Gemini 2.5 Flash',
      description: '최신 고속 멀티모달 모델',
      provider: 'gemini',
      speed: 'fast',
      capabilities: ['reasoning', 'quick_tasks', 'multimodal'],
    },
    {
      id: 'gemini-2.0-pro',
      name: 'Gemini 2.0 Pro',
      description: '안정적인 고성능 모델',
      provider: 'gemini',
      speed: 'medium',
      capabilities: ['reasoning', 'analysis', 'multimodal'],
    },
    {
      id: 'gemini-2.0-flash',
      name: 'Gemini 2.0 Flash',
      description: '빠르고 효율적인 모델',
      provider: 'gemini',
      speed: 'fast',
      capabilities: ['reasoning', 'quick_tasks', 'multimodal'],
    },
  ],
};

// 에이전트 타입 정보
export const AGENT_TYPE_MAP: Record<AgentType, AgentTypeInfo> = {
  none: {
    id: 'none',
    name: '일반 채팅',
    description: '기본 AI 대화',
    icon: '💬',
    color: 'neutral',
    isDefault: true,
  },
  web_search: {
    id: 'web_search',
    name: '웹 검색',
    description: '실시간 정보 검색',
    icon: '🔍',
    color: 'success',
  },
  deep_research: {
    id: 'deep_research',
    name: '심층 리서치',
    description: '종합적인 분석과 연구',
    icon: '📊',
    color: 'info',
  },
  canvas: {
    id: 'canvas',
    name: 'Canvas',
    description: '인터랙티브 워크스페이스',
    icon: '🎨',
    color: 'warning',
  },
};

// API 응답 래퍼 타입
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  error?: string;
}

// 에러 타입
export interface ApiError {
  detail: string;
  status_code?: number;
}