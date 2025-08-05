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
}

// 채팅 응답 타입
export interface ChatResponse {
  response: string;
  agent_used: string;
  model_used: string;
  timestamp: string;
  user_id: string;
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

// LLM 모델 타입
export type LLMModel = 'gemini' | 'claude';

// 에이전트 타입
export type AgentType = 'web_search' | 'deep_research' | 'multimodal_rag';

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