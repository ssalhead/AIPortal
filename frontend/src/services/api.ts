/**
 * API 서비스
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import type { 
  ChatMessage, 
  ChatResponse, 
  ConversationHistory, 
  AgentInfo, 
  AgentExecuteRequest, 
  AgentExecuteResponse 
} from '../types';

class ApiService {
  private client: AxiosInstance;

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
      (response: AxiosResponse) => {
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

  // 채팅 메시지 전송
  async sendChatMessage(message: ChatMessage): Promise<ChatResponse> {
    const response = await this.client.post('/chat', message);
    return response.data;
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
}

// 싱글톤 인스턴스
export const apiService = new ApiService();
export default apiService;