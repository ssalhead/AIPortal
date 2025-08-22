/**
 * API 서비스
 */

import axios from 'axios';
import { loggers } from '../utils/logger';
import type { 
  ChatMessage, 
  ChatResponse, 
  ConversationHistory, 
  AgentInfo, 
  AgentExecuteRequest, 
  AgentExecuteResponse,
  StreamingProgressMetadata
} from '../types';

export interface ChatMessageWithSession extends ChatMessage {
  session_id?: string | null;
}

export interface ChatResponseWithSession extends ChatResponse {
  session_id?: string | null;
}

class ApiService {
  private client: ReturnType<typeof axios.create>;

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_V1_URL || 'http://localhost:8000/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 요청 인터셉터
    this.client.interceptors.request.use(
      (config) => {
        loggers.api(config.method || 'unknown', config.url || '', 'ApiService');
        return config;
      },
      (error) => {
        loggers.error('API 요청 에러', error, 'ApiService');
        return Promise.reject(error);
      }
    );

    // 응답 인터셉터
    this.client.interceptors.response.use(
      (response) => {
        loggers.debug(`API 응답: ${response.status}`, undefined, 'ApiService');
        return response;
      },
      (error) => {
        loggers.error('API 응답 에러', error, 'ApiService');
        return Promise.reject(error);
      }
    );
  }

  // 헬스 체크
  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }

  // 상세 헬스 체크
  async detailedHealthCheck() {
    const response = await this.client.get('/health/detailed');
    return response.data;
  }

  // 채팅 메시지 전송 (세션 지원)
  async sendChatMessage(message: ChatMessageWithSession): Promise<ChatResponseWithSession> {
    const response = await this.client.post('/chat', message);
    loggers.debug('채팅 응답 받음', response.data, 'ApiService');
    return response.data;
  }

  // 실시간 진행 상태와 함께 채팅 메시지 전송 (SSE) - 청크 스트리밍 지원
  async sendChatMessageWithProgress(
    message: ChatMessage,
    onProgress: (step: string, progress: number, metadata?: StreamingProgressMetadata) => void,
    onChunk: (text: string, isFirst: boolean, isFinal: boolean) => void,
    onResult: (result: ChatResponse) => void,
    onError: (error: string) => void
  ): Promise<void> {
    const url = `${this.client.defaults.baseURL}/chat/stream`;
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(message),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        // SSE 메시지 파싱
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 마지막 불완전한 줄은 버퍼에 보관

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.substring(6));
              
              switch (eventData.type) {
                case 'start':
                  loggers.info('채팅 시작', 'ApiService');
                  break;
                  
                case 'context':
                  // 대화 컨텍스트 정보 수신
                  loggers.info('컨텍스트 분석 완료', 'ApiService');
                  if (eventData.data.has_context) {
                    loggers.debug('이전 대화 맥락 적용됨', undefined, 'ApiService');
                  } else {
                    loggers.debug('새로운 대화 시작', undefined, 'ApiService');
                  }
                  break;
                  
                case 'progress':
                  onProgress(eventData.data.step, eventData.data.progress, eventData.data.metadata);
                  break;
                  
                case 'metadata':
                  // 메타데이터 수신 - 스트리밍 준비
                  loggers.debug('메타데이터 수신', eventData.data, 'ApiService');
                  if (eventData.data.context_applied) {
                    loggers.info('대화 컨텍스트 적용 완료', 'ApiService');
                  }
                  break;
                  
                case 'chunk':
                  // 청크 데이터 수신 - 타이핑 효과로 표시 (빈도 제어된 로깅)
                  const chunkData = eventData.data;
                  loggers.stream(`청크 수신 [${chunkData.index}]`, { 
                    length: chunkData.text.length, 
                    final: chunkData.is_final 
                  }, 'ApiService');
                  onChunk(chunkData.text, chunkData.index === 0, chunkData.is_final);
                  break;
                  
                case 'result':
                  loggers.info('스트리밍 완료', 'ApiService');
                  // result 이벤트는 정상 완료를 의미하므로 onResult 콜백 호출
                  onResult(eventData.data);
                  break;
                  
                case 'end':
                  loggers.info('채팅 완료', 'ApiService');
                  // end 이벤트에서 스트리밍 완료
                  return;
                  
                case 'error':
                  loggers.error('스트리밍 에러', new Error(eventData.data.message), 'ApiService');
                  onError(eventData.data.message);
                  return;
                  
                default:
                  loggers.warn(`Unknown event type: ${eventData.type}`, 'ApiService');
              }
            } catch (parseError) {
              loggers.error('SSE 메시지 파싱 오류', parseError as Error, 'ApiService');
            }
          }
        }
      }
    } catch (error) {
      loggers.error('SSE 연결 오류', error as Error, 'ApiService');
      onError(error instanceof Error ? error.message : 'SSE 연결에 실패했습니다.');
    }
  }

  // 채팅 히스토리 조회
  async getChatHistory(limit: number = 20): Promise<ConversationHistory[]> {
    const response = await this.client.get(`/chat/history?limit=${limit}`);
    return response.data;
  }

  // 에이전트 목록 조회
  async getAgents(): Promise<AgentInfo[]> {
    const response = await this.client.get('/agents');
    return response.data;
  }

  // 특정 에이전트 정보 조회
  async getAgentInfo(agentId: string): Promise<AgentInfo> {
    const response = await this.client.get(`/agents/${agentId}`);
    return response.data;
  }

  // 에이전트 실행
  async executeAgent(request: AgentExecuteRequest): Promise<AgentExecuteResponse> {
    const response = await this.client.post('/agents/execute', request);
    return response.data;
  }

  // HTTP 클라이언트 노출 (다른 서비스에서 사용)
  get httpClient() {
    return this.client;
  }
}

// 싱글톤 인스턴스
export const apiService = new ApiService();
export default apiService;