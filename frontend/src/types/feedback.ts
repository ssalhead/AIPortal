/**
 * 피드백 관련 타입 정의
 */

export type FeedbackType = 'thumbs' | 'rating' | 'detailed';

export type FeedbackCategory = 
  | 'overall' 
  | 'accuracy' 
  | 'helpfulness' 
  | 'clarity' 
  | 'completeness' 
  | 'speed' 
  | 'relevance';

export interface FeedbackSubmitRequest {
  message_id: string;
  feedback_type: FeedbackType;
  category?: FeedbackCategory;
  rating?: number; // 1-5
  is_positive?: boolean;
  title?: string;
  content?: string;
  suggestions?: string;
  conversation_id?: string;
  agent_type?: string;
  model_used?: string;
  response_time_ms?: number;
  user_query?: string;
  ai_response?: string;
}

export interface MessageFeedback {
  id: string;
  message_id: string;
  conversation_id?: string;
  feedback_type: FeedbackType;
  category: FeedbackCategory;
  rating?: number;
  is_positive?: boolean;
  title?: string;
  content?: string;
  suggestions?: string;
  agent_type?: string;
  model_used?: string;
  created_at: string;
  updated_at: string;
}

export interface UserFeedbackProfile {
  user_id: string;
  total_feedbacks: number;
  positive_feedbacks: number;
  negative_feedbacks: number;
  detailed_feedbacks: number;
  avg_rating_given?: number;
  preferred_agents?: Record<string, number>;
  preferred_models?: Record<string, number>;
  feedback_frequency?: number;
  most_active_hours?: number[];
  common_categories?: Record<string, number>;
  helpful_feedback_count: number;
  feedback_quality_score?: number;
  last_feedback_at?: string;
  created_at: string;
  updated_at: string;
}

export interface FeedbackStatistics {
  period_days: number;
  statistics: {
    total_feedbacks: number;
    positive_count: number;
    negative_count: number;
    neutral_count: number;
    positive_rate: number;
    negative_rate: number;
    avg_rating?: number;
  };
  filters: {
    agent_type?: string;
    model_used?: string;
  };
}

export interface FeedbackCategoryInfo {
  value: FeedbackCategory;
  name: string;
  description: string;
}

export interface FeedbackTypeInfo {
  value: FeedbackType;
  name: string;
  description: string;
}

export interface RecentFeedback {
  id: string;
  user_id: string;
  message_id: string;
  feedback_type: FeedbackType;
  category: FeedbackCategory;
  rating?: number;
  is_positive?: boolean;
  title?: string;
  content?: string;
  agent_type?: string;
  model_used?: string;
  priority: number;
  is_reviewed: boolean;
  created_at: string;
}