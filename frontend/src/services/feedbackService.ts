/**
 * 피드백 서비스
 */

import { apiService } from './api';
import type {
  FeedbackSubmitRequest,
  MessageFeedback,
  UserFeedbackProfile,
  FeedbackStatistics,
  RecentFeedback,
  FeedbackCategoryInfo,
  FeedbackTypeInfo
} from '../types/feedback';

export class FeedbackService {
  /**
   * 피드백 제출
   */
  async submitFeedback(feedback: FeedbackSubmitRequest): Promise<{ message: string; feedback_id: string }> {
    try {
      const response = await apiService.httpClient.post('/feedback/submit', feedback);
      return response.data;
    } catch (error) {
      console.error('피드백 제출 실패:', error);
      throw error;
    }
  }

  /**
   * 내 피드백 목록 조회
   */
  async getMyFeedbacks(
    limit: number = 20,
    skip: number = 0,
    feedbackType?: string,
    category?: string
  ): Promise<{
    feedbacks: MessageFeedback[];
    total: number;
    skip: number;
    limit: number;
  }> {
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        skip: skip.toString(),
      });

      if (feedbackType) params.append('feedback_type', feedbackType);
      if (category) params.append('category', category);

      const response = await apiService.httpClient.get(`/feedback/my?${params}`);
      return response.data;
    } catch (error) {
      console.error('피드백 목록 조회 실패:', error);
      throw error;
    }
  }

  /**
   * 특정 메시지의 피드백 조회
   */
  async getMessageFeedback(messageId: string): Promise<MessageFeedback | null> {
    try {
      const response = await apiService.httpClient.get(`/feedback/message/${messageId}`);
      return response.data.feedback;
    } catch (error) {
      console.error('메시지 피드백 조회 실패:', error);
      throw error;
    }
  }

  /**
   * 내 피드백 프로파일 조회
   */
  async getMyProfile(): Promise<UserFeedbackProfile> {
    try {
      const response = await apiService.httpClient.get('/feedback/profile');
      return response.data;
    } catch (error) {
      console.error('피드백 프로파일 조회 실패:', error);
      throw error;
    }
  }

  /**
   * 피드백 통계 조회
   */
  async getStatistics(
    days: number = 30,
    agentType?: string,
    modelUsed?: string
  ): Promise<FeedbackStatistics> {
    try {
      const params = new URLSearchParams({
        days: days.toString(),
      });

      if (agentType) params.append('agent_type', agentType);
      if (modelUsed) params.append('model_used', modelUsed);

      const response = await apiService.httpClient.get(`/feedback/statistics?${params}`);
      return response.data;
    } catch (error) {
      console.error('피드백 통계 조회 실패:', error);
      throw error;
    }
  }

  /**
   * 최근 피드백 조회 (관리자용)
   */
  async getRecentFeedbacks(
    limit: number = 50,
    hours: number = 24,
    priorityOnly: boolean = false
  ): Promise<{
    feedbacks: RecentFeedback[];
    total: number;
    filters: {
      hours: number;
      priority_only: boolean;
    };
  }> {
    try {
      const params = new URLSearchParams({
        limit: limit.toString(),
        hours: hours.toString(),
        priority_only: priorityOnly.toString(),
      });

      const response = await apiService.httpClient.get(`/feedback/recent?${params}`);
      return response.data;
    } catch (error) {
      console.error('최근 피드백 조회 실패:', error);
      throw error;
    }
  }

  /**
   * 피드백 카테고리 목록 조회
   */
  async getCategories(): Promise<FeedbackCategoryInfo[]> {
    try {
      const response = await apiService.httpClient.get('/feedback/categories');
      return response.data.categories;
    } catch (error) {
      console.error('피드백 카테고리 조회 실패:', error);
      throw error;
    }
  }

  /**
   * 피드백 타입 목록 조회
   */
  async getTypes(): Promise<FeedbackTypeInfo[]> {
    try {
      const response = await apiService.httpClient.get('/feedback/types');
      return response.data.types;
    } catch (error) {
      console.error('피드백 타입 조회 실패:', error);
      throw error;
    }
  }

  /**
   * 일간 분석 데이터 생성 (관리자용)
   */
  async generateDailyAnalytics(date?: string): Promise<any> {
    try {
      const params = date ? new URLSearchParams({ date }) : '';
      const response = await apiService.httpClient.post(`/feedback/analytics/generate?${params}`);
      return response.data;
    } catch (error) {
      console.error('분석 데이터 생성 실패:', error);
      throw error;
    }
  }

  /**
   * 간단한 좋아요/싫어요 피드백 제출
   */
  async submitThumbsFeedback(
    messageId: string,
    isPositive: boolean,
    context?: {
      conversationId?: string;
      agentType?: string;
      modelUsed?: string;
      responseTimeMs?: number;
      userQuery?: string;
      aiResponse?: string;
    }
  ): Promise<string> {
    const feedback: FeedbackSubmitRequest = {
      message_id: messageId,
      feedback_type: 'thumbs',
      is_positive: isPositive,
      category: 'overall',
      ...context,
    };

    const result = await this.submitFeedback(feedback);
    return result.feedback_id;
  }

  /**
   * 별점 피드백 제출
   */
  async submitRatingFeedback(
    messageId: string,
    rating: number,
    category: string = 'overall',
    context?: {
      conversationId?: string;
      agentType?: string;
      modelUsed?: string;
      responseTimeMs?: number;
      userQuery?: string;
      aiResponse?: string;
    }
  ): Promise<string> {
    const feedback: FeedbackSubmitRequest = {
      message_id: messageId,
      feedback_type: 'rating',
      rating,
      category: category as any,
      ...context,
    };

    const result = await this.submitFeedback(feedback);
    return result.feedback_id;
  }

  /**
   * 상세 피드백 제출
   */
  async submitDetailedFeedback(
    messageId: string,
    title: string,
    content: string,
    suggestions?: string,
    rating?: number,
    category: string = 'overall',
    context?: {
      conversationId?: string;
      agentType?: string;
      modelUsed?: string;
      responseTimeMs?: number;
      userQuery?: string;
      aiResponse?: string;
    }
  ): Promise<string> {
    const feedback: FeedbackSubmitRequest = {
      message_id: messageId,
      feedback_type: 'detailed',
      title,
      content,
      suggestions,
      rating,
      category: category as any,
      ...context,
    };

    const result = await this.submitFeedback(feedback);
    return result.feedback_id;
  }
}

// 전역 피드백 서비스 인스턴스
export const feedbackService = new FeedbackService();