/**
 * 에이전트 제안 서비스
 */

import type { AgentType } from '../types';

interface AgentSuggestionRequest {
  query: string;
  current_agent: string;
  model?: string;
}

interface AgentSuggestionResponse {
  needs_switch: boolean;
  suggested_agent?: AgentType;
  confidence?: number;
  reason?: string;
  current_agent?: string;
  error?: string;
}

class AgentSuggestionService {
  private baseUrl = 'http://localhost:8000/api/v1';

  /**
   * 에이전트 제안 분석 요청
   */
  async analyzeSuggestion(request: AgentSuggestionRequest): Promise<AgentSuggestionResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/agents/analyze-suggestion`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}` // 인증 토큰
        },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data;
      
    } catch (error) {
      console.error('에이전트 제안 분석 실패:', error);
      
      // 에러 발생 시 기본 응답 반환
      return {
        needs_switch: false,
        error: error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'
      };
    }
  }

  /**
   * 사용 가능한 에이전트 워커 정보 조회
   */
  async getAvailableWorkers(): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/agents/available-workers`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
      
    } catch (error) {
      console.error('사용 가능한 워커 정보 조회 실패:', error);
      throw error;
    }
  }

  /**
   * 에이전트 타입을 API 형식으로 변환
   */
  private convertAgentType(agentType: AgentType): string {
    // AgentType과 API에서 사용하는 문자열 매핑
    const typeMap: Record<AgentType, string> = {
      'none': 'none',
      'web_search': 'web_search',
      'deep_research': 'deep_research',
      'canvas': 'canvas'
    };

    return typeMap[agentType] || 'none';
  }

  /**
   * 편의 메서드: AgentType을 사용한 제안 분석
   */
  async analyzeSuggestionWithTypes(
    query: string, 
    currentAgent: AgentType, 
    model: string = 'gemini'
  ): Promise<AgentSuggestionResponse> {
    return this.analyzeSuggestion({
      query,
      current_agent: this.convertAgentType(currentAgent),
      model
    });
  }
}

export const agentSuggestionService = new AgentSuggestionService();