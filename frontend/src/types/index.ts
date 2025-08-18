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
  metadata?: {
    search_queries?: string[];
    original_query?: string;
    context_integrated_queries?: string[];
    has_conversation_context?: boolean;
    [key: string]: any;
  };
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
  metadata?: Record<string, any>;
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
export type LLMModel = 'claude-4' | 'claude-3.7' | 'claude-3.5' | 'claude-haiku' | 'gemini-pro' | 'gemini-flash' | 'gemini-1.0';

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
      id: 'gemini-pro',
      name: 'Gemini 1.5 Pro',
      description: '고성능 멀티모달 모델',
      provider: 'gemini',
      speed: 'medium',
      capabilities: ['reasoning', 'multimodal', 'analysis', 'creative'],
      isRecommended: true,
    },
    {
      id: 'gemini-flash',
      name: 'Gemini 1.5 Flash',
      description: '빠르고 효율적인 모델',
      provider: 'gemini',
      speed: 'fast',
      capabilities: ['reasoning', 'quick_tasks', 'multimodal'],
    },
    {
      id: 'gemini-1.0',
      name: 'Gemini 1.0 Pro',
      description: '안정적인 기본 모델',
      provider: 'gemini',
      speed: 'medium',
      capabilities: ['reasoning', 'analysis'],
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