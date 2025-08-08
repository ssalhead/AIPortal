/**
 * 대화 이력 관리 서비스
 */

import { apiService } from './api';

export interface ConversationSummary {
  id: string;
  title: string;
  model?: string;
  agent_type?: string;
  status: 'active' | 'archived' | 'deleted';
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message_at?: string;
  last_message_preview?: string;
}

export interface ConversationDetail {
  id: string;
  title: string;
  description?: string;
  model?: string;
  agent_type?: string;
  status: 'active' | 'archived' | 'deleted';
  metadata_: Record<string, any>;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
  message_pagination: {
    total: number;
    skip: number;
    limit: number;
    has_more: boolean;
  };
}

export interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  model?: string;
  tokens_input?: number;
  tokens_output?: number;
  latency_ms?: number;
  metadata_: Record<string, any>;
  attachments: any[];
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export interface ConversationSearchResponse {
  query: string;
  results: Array<ConversationSummary & {
    rank: number;
    highlight: string;
  }>;
  total: number;
  limit: number;
}

export interface ConversationStatistics {
  period_days: number;
  conversation_count: number;
  message_count: number;
  active_days: number;
  avg_input_tokens: number;
  avg_output_tokens: number;
  avg_latency_ms: number;
  user_messages: number;
  assistant_messages: number;
}

export interface CreateConversationRequest {
  title: string;
  description?: string;
  model?: string;
  agent_type?: string;
  metadata_?: Record<string, any>;
}

export interface UpdateConversationRequest {
  title?: string;
  description?: string;
  status?: 'active' | 'archived' | 'deleted';
  metadata_?: Record<string, any>;
}

export interface CreateMessageRequest {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  model?: string;
  tokens_input?: number;
  tokens_output?: number;
  latency_ms?: number;
  metadata_?: Record<string, any>;
  attachments?: any[];
}

class ConversationHistoryService {
  /**
   * 사용자 대화 목록 조회
   */
  async getConversations(params: {
    skip?: number;
    limit?: number;
    status?: 'active' | 'archived' | 'deleted';
  } = {}): Promise<ConversationListResponse> {
    const response = await apiService.httpClient.get('/history/conversations', { params });
    return response.data;
  }

  /**
   * 대화 상세 정보 조회
   */
  async getConversationDetail(
    conversationId: string,
    params: {
      message_skip?: number;
      message_limit?: number;
    } = {}
  ): Promise<ConversationDetail> {
    const response = await apiService.httpClient.get(`/history/conversations/${conversationId}`, { params });
    return response.data;
  }

  /**
   * 대화 검색
   */
  async searchConversations(params: {
    q: string;
    limit?: number;
  }): Promise<ConversationSearchResponse> {
    const response = await apiService.httpClient.get('/history/conversations/search', { params });
    return response.data;
  }

  /**
   * 새 대화 생성
   */
  async createConversation(data: CreateConversationRequest): Promise<ConversationSummary> {
    const response = await apiService.httpClient.post('/history/conversations', data);
    return response.data;
  }

  /**
   * 대화 정보 수정
   */
  async updateConversation(
    conversationId: string,
    data: UpdateConversationRequest
  ): Promise<ConversationSummary> {
    const response = await apiService.httpClient.put(`/history/conversations/${conversationId}`, data);
    return response.data;
  }

  /**
   * 대화 삭제
   */
  async deleteConversation(
    conversationId: string,
    hardDelete: boolean = false
  ): Promise<{ message: string; conversation_id: string }> {
    const response = await apiService.httpClient.delete(`/history/conversations/${conversationId}`, {
      params: { hard_delete: hardDelete }
    });
    return response.data;
  }

  /**
   * 메시지 추가
   */
  async addMessage(
    conversationId: string,
    data: CreateMessageRequest
  ): Promise<ConversationMessage> {
    const response = await apiService.httpClient.post(`/history/conversations/${conversationId}/messages`, data);
    return response.data;
  }

  /**
   * 대화 통계 조회
   */
  async getStatistics(days: number = 30): Promise<ConversationStatistics> {
    const response = await apiService.httpClient.get('/history/conversations/statistics', {
      params: { days }
    });
    return response.data;
  }

  /**
   * 캐시 통계 조회 (개발/디버깅용)
   */
  async getCacheStats(): Promise<any> {
    const response = await apiService.httpClient.get('/history/cache/stats');
    return response.data;
  }

  /**
   * 대화 목록을 페이지네이션으로 로드
   */
  async loadMoreConversations(
    currentConversations: ConversationSummary[],
    limit: number = 20
  ): Promise<ConversationListResponse> {
    const skip = currentConversations.length;
    return this.getConversations({ skip, limit });
  }

  /**
   * 대화의 더 많은 메시지 로드
   */
  async loadMoreMessages(
    conversationId: string,
    currentMessageCount: number,
    limit: number = 50
  ): Promise<ConversationDetail> {
    return this.getConversationDetail(conversationId, {
      message_skip: currentMessageCount,
      message_limit: limit
    });
  }

  /**
   * 대화 제목 자동 생성 (첫 번째 사용자 메시지 기반)
   */
  generateConversationTitle(firstMessage: string): string {
    // 첫 50자 이내에서 문장 단위로 자르기
    const maxLength = 50;
    
    if (firstMessage.length <= maxLength) {
      return firstMessage;
    }
    
    // 문장 끝에서 자르기 시도
    const sentences = firstMessage.match(/[^.!?]*[.!?]/g);
    if (sentences && sentences[0] && sentences[0].length <= maxLength) {
      return sentences[0].trim();
    }
    
    // 단어 단위로 자르기
    const words = firstMessage.split(' ');
    let title = '';
    
    for (const word of words) {
      if ((title + ' ' + word).length > maxLength) {
        break;
      }
      title += (title ? ' ' : '') + word;
    }
    
    return title + (title.length < firstMessage.length ? '...' : '');
  }

  /**
   * 대화 날짜별 그룹화
   */
  groupConversationsByDate(conversations: ConversationSummary[]): Record<string, ConversationSummary[]> {
    const groups: Record<string, ConversationSummary[]> = {};
    
    for (const conversation of conversations) {
      const date = new Date(conversation.updated_at);
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      
      let groupKey: string;
      
      if (date.toDateString() === today.toDateString()) {
        groupKey = '오늘';
      } else if (date.toDateString() === yesterday.toDateString()) {
        groupKey = '어제';
      } else if (date.getTime() > today.getTime() - 7 * 24 * 60 * 60 * 1000) {
        groupKey = '이번 주';
      } else if (date.getTime() > today.getTime() - 30 * 24 * 60 * 60 * 1000) {
        groupKey = '이번 달';
      } else {
        groupKey = date.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long' });
      }
      
      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(conversation);
    }
    
    return groups;
  }

  /**
   * 메시지 검색 하이라이트
   */
  highlightSearchTerm(text: string, searchTerm: string): string {
    if (!searchTerm) return text;
    
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }

  /**
   * 대화 내보내기 (텍스트 형식)
   */
  exportConversationAsText(conversation: ConversationDetail): string {
    const lines: string[] = [];
    
    lines.push(`대화: ${conversation.title}`);
    lines.push(`생성일: ${new Date(conversation.created_at).toLocaleString('ko-KR')}`);
    lines.push(`모델: ${conversation.model || '알 수 없음'}`);
    if (conversation.agent_type) {
      lines.push(`에이전트: ${conversation.agent_type}`);
    }
    lines.push('');
    
    for (const message of conversation.messages) {
      const timestamp = new Date(message.created_at).toLocaleString('ko-KR');
      const role = message.role === 'user' ? '사용자' : '어시스턴트';
      
      lines.push(`[${timestamp}] ${role}:`);
      lines.push(message.content);
      lines.push('');
    }
    
    return lines.join('\n');
  }

  /**
   * 대화 내보내기 (JSON 형식)
   */
  exportConversationAsJson(conversation: ConversationDetail): string {
    return JSON.stringify(conversation, null, 2);
  }
}

export const conversationHistoryService = new ConversationHistoryService();