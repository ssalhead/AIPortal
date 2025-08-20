/**
 * API 서비스
 */

import axios from 'axios';
import type { 
  ChatMessage, 
  ChatResponse, 
  ConversationHistory, 
  AgentInfo, 
  AgentExecuteRequest, 
  AgentExecuteResponse 
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
        console.log(`API 요청: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('API 요청 에러:', error);
        return Promise.reject(error);
      }
    );

    // 응답 인터셉터
    this.client.interceptors.response.use(
      (response) => {
        console.log(`API 응답: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        console.error('API 응답 에러:', error.response?.data || error.message);
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
    console.log('API 응답 받음:', response.data);
    return response.data;
  }

  // 실시간 진행 상태와 함께 채팅 메시지 전송 (SSE) - 청크 스트리밍 지원
  async sendChatMessageWithProgress(
    message: ChatMessage,
    onProgress: (step: string, progress: number, metadata?: any) => void,
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
                  console.log('채팅 시작:', eventData.data.message);
                  break;
                  
                case 'context':
                  // 대화 컨텍스트 정보 수신
                  console.log('🧠 컨텍스트 분석 완료:', eventData.data);
                  if (eventData.data.has_context) {
                    console.log('✅ 이전 대화 맥락 적용됨');
                  } else {
                    console.log('ℹ️ 새로운 대화 시작');
                  }
                  break;
                  
                case 'progress':
                  onProgress(eventData.data.step, eventData.data.progress, eventData.data.metadata);
                  break;
                  
                case 'metadata':
                  // 메타데이터 수신 - 스트리밍 준비
                  console.log('📊 메타데이터 수신:', eventData.data);
                  if (eventData.data.context_applied) {
                    console.log('✅ 대화 컨텍스트가 적용되었습니다');
                  }
                  break;
                  
                case 'chunk':
                  // 청크 데이터 수신 - 타이핑 효과로 표시
                  const chunkData = eventData.data;
                  console.log('📝 청크 수신:', chunkData.text, '(인덱스:', chunkData.index, ', 마지막:', chunkData.is_final, ')');
                  onChunk(chunkData.text, chunkData.index === 0, chunkData.is_final);
                  break;
                  
                case 'result':
                  console.log('🎯 스트리밍 result 이벤트 (정상 완료):', eventData.data);
                  // result 이벤트는 정상 완료를 의미하므로 onResult 콜백 호출
                  onResult(eventData.data);
                  break;
                  
                case 'end':
                  console.log('채팅 완료:', eventData.data.message);
                  // end 이벤트에서 스트리밍 완료
                  return;
                  
                case 'error':
                  console.error('❌ 스트리밍 에러 이벤트:', eventData.data);
                  onError(eventData.data.message);
                  return;
                  
                default:
                  console.log('Unknown event type:', eventData.type);
              }
            } catch (parseError) {
              console.error('SSE 메시지 파싱 오류:', parseError);
            }
          }
        }
      }
    } catch (error) {
      console.error('SSE 연결 오류:', error);
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