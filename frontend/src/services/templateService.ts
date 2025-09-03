// Template Service API Client
// AIPortal Canvas Template Library - 템플릿 API 클라이언트 서비스

import {
  TemplateResponse,
  TemplateDetailResponse,
  TemplateSearchRequest,
  TemplateSearchResponse,
  TemplateCreateRequest,
  TemplateUpdateRequest,
  TemplateApplyRequest,
  TemplateCustomizationRequest,
  TemplateReviewRequest,
  TemplateReviewResponse,
  CollectionResponse,
  CollectionCreateRequest,
  CollectionUpdateRequest,
  CollectionItemRequest,
  CustomizationPresetResponse,
  CustomizationPresetRequest,
  TemplateAnalyticsResponse,
  CategoryResponse,
  TagResponse
} from '../types/template';

import { apiClient } from './apiClient';

// ===== API 엔드포인트 상수 =====

const ENDPOINTS = {
  TEMPLATES: '/api/v1/templates',
  SEARCH: '/api/v1/templates/search',
  FEATURED: '/api/v1/templates/featured',
  TRENDING: '/api/v1/templates/trending',
  FAVORITES: '/api/v1/templates/favorites',
  CATEGORIES: '/api/v1/templates/categories',
  TAGS: '/api/v1/templates/tags',
  COLLECTIONS: '/api/v1/collections',
  PRESETS: '/api/v1/presets',
  ANALYTICS: '/api/v1/analytics'
} as const;

// ===== 타입 정의 =====

interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// ===== 유틸리티 함수 =====

const buildQueryString = (params: Record<string, any>): string => {
  const query = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      if (Array.isArray(value)) {
        value.forEach(v => query.append(key, String(v)));
      } else {
        query.append(key, String(value));
      }
    }
  });
  
  return query.toString();
};

const handleApiError = (error: any): never => {
  const message = error.response?.data?.message || 
                 error.response?.data?.detail || 
                 error.message || 
                 'An unexpected error occurred';
  
  console.error('API Error:', error);
  throw new Error(message);
};

// ===== 메인 템플릿 서비스 클래스 =====

class TemplateService {
  // ===== 템플릿 검색 및 브라우징 =====

  async searchTemplates(request: TemplateSearchRequest): Promise<TemplateSearchResponse> {
    try {
      const queryString = buildQueryString({
        query: request.query,
        category: request.category,
        subcategory: request.subcategory,
        tags: request.tags?.join(','),
        license_type: request.license_type,
        difficulty_level: request.difficulty_level,
        is_featured: request.is_featured,
        min_rating: request.min_rating,
        created_after: request.created_after,
        created_before: request.created_before,
        sort_by: request.sort_by,
        page: request.page,
        page_size: request.page_size
      });

      const response = await apiClient.get<TemplateSearchResponse>(
        `${ENDPOINTS.SEARCH}?${queryString}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async getFeaturedTemplates(limit = 20): Promise<TemplateResponse[]> {
    try {
      const response = await apiClient.get<TemplateResponse[]>(
        `${ENDPOINTS.FEATURED}?limit=${limit}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async getTrendingTemplates(limit = 20, days = 7): Promise<TemplateResponse[]> {
    try {
      const response = await apiClient.get<TemplateResponse[]>(
        `${ENDPOINTS.TRENDING}?limit=${limit}&days=${days}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 템플릿 CRUD =====

  async getTemplate(id: string): Promise<TemplateDetailResponse> {
    try {
      const response = await apiClient.get<TemplateDetailResponse>(
        `${ENDPOINTS.TEMPLATES}/${id}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async createTemplate(request: TemplateCreateRequest): Promise<TemplateDetailResponse> {
    try {
      const response = await apiClient.post<TemplateDetailResponse>(
        ENDPOINTS.TEMPLATES,
        request
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async updateTemplate(id: string, request: TemplateUpdateRequest): Promise<TemplateDetailResponse> {
    try {
      const response = await apiClient.put<TemplateDetailResponse>(
        `${ENDPOINTS.TEMPLATES}/${id}`,
        request
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async deleteTemplate(id: string): Promise<void> {
    try {
      await apiClient.delete(`${ENDPOINTS.TEMPLATES}/${id}`);
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 템플릿 적용 및 커스터마이징 =====

  async applyTemplate(id: string, request: TemplateApplyRequest): Promise<any> {
    try {
      const response = await apiClient.post<any>(
        `${ENDPOINTS.TEMPLATES}/${id}/apply`,
        request
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async customizeTemplate(id: string, request: TemplateCustomizationRequest): Promise<any> {
    try {
      const response = await apiClient.post<any>(
        `${ENDPOINTS.TEMPLATES}/${id}/customize`,
        request
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 즐겨찾기 =====

  async toggleFavorite(id: string): Promise<{ is_favorite: boolean; message: string }> {
    try {
      const response = await apiClient.post<{ is_favorite: boolean; message: string }>(
        `${ENDPOINTS.TEMPLATES}/${id}/favorite`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async getFavorites(page = 1, pageSize = 20): Promise<TemplateSearchResponse> {
    try {
      const response = await apiClient.get<TemplateSearchResponse>(
        `${ENDPOINTS.FAVORITES}/my?page=${page}&page_size=${pageSize}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 리뷰 시스템 =====

  async addReview(id: string, review: TemplateReviewRequest): Promise<void> {
    try {
      await apiClient.post(
        `${ENDPOINTS.TEMPLATES}/${id}/reviews`,
        review
      );
    } catch (error) {
      handleApiError(error);
    }
  }

  async getReviews(id: string, page = 1, pageSize = 20): Promise<PaginatedResponse<TemplateReviewResponse>> {
    try {
      const response = await apiClient.get<PaginatedResponse<TemplateReviewResponse>>(
        `${ENDPOINTS.TEMPLATES}/${id}/reviews?page=${page}&page_size=${pageSize}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 컬렉션 시스템 =====

  async createCollection(name: string, description?: string): Promise<CollectionResponse> {
    try {
      const request: CollectionCreateRequest = {
        name,
        description,
        is_public: false
      };

      const response = await apiClient.post<CollectionResponse>(
        ENDPOINTS.COLLECTIONS,
        request
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async getCollections(page = 1, pageSize = 20): Promise<PaginatedResponse<CollectionResponse>> {
    try {
      const response = await apiClient.get<PaginatedResponse<CollectionResponse>>(
        `${ENDPOINTS.COLLECTIONS}?page=${page}&page_size=${pageSize}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async getCollection(id: string): Promise<CollectionResponse> {
    try {
      const response = await apiClient.get<CollectionResponse>(
        `${ENDPOINTS.COLLECTIONS}/${id}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async updateCollection(id: string, request: CollectionUpdateRequest): Promise<CollectionResponse> {
    try {
      const response = await apiClient.put<CollectionResponse>(
        `${ENDPOINTS.COLLECTIONS}/${id}`,
        request
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async deleteCollection(id: string): Promise<void> {
    try {
      await apiClient.delete(`${ENDPOINTS.COLLECTIONS}/${id}`);
    } catch (error) {
      handleApiError(error);
    }
  }

  async addToCollection(collectionId: string, templateId: string): Promise<void> {
    try {
      const request: CollectionItemRequest = {
        template_id: templateId
      };

      await apiClient.post(
        `${ENDPOINTS.COLLECTIONS}/${collectionId}/items`,
        request
      );
    } catch (error) {
      handleApiError(error);
    }
  }

  async removeFromCollection(collectionId: string, templateId: string): Promise<void> {
    try {
      await apiClient.delete(
        `${ENDPOINTS.COLLECTIONS}/${collectionId}/items/${templateId}`
      );
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 커스터마이징 프리셋 =====

  async createPreset(templateId: string, request: CustomizationPresetRequest): Promise<CustomizationPresetResponse> {
    try {
      const response = await apiClient.post<CustomizationPresetResponse>(
        `${ENDPOINTS.TEMPLATES}/${templateId}/presets`,
        request
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async getPresets(templateId: string): Promise<CustomizationPresetResponse[]> {
    try {
      const response = await apiClient.get<CustomizationPresetResponse[]>(
        `${ENDPOINTS.TEMPLATES}/${templateId}/presets`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async applyPreset(templateId: string, presetId: string): Promise<any> {
    try {
      const response = await apiClient.post<any>(
        `${ENDPOINTS.TEMPLATES}/${templateId}/presets/${presetId}/apply`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 메타데이터 및 분류 =====

  async getCategories(): Promise<any[]> {
    try {
      const response = await apiClient.get<any[]>(ENDPOINTS.CATEGORIES);
      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async getPopularTags(limit = 50): Promise<string[]> {
    try {
      const response = await apiClient.get<string[]>(
        `${ENDPOINTS.TAGS}/popular?limit=${limit}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async getTagSuggestions(query: string, category?: string, limit = 10): Promise<any[]> {
    try {
      const queryString = buildQueryString({
        q: query,
        category,
        limit
      });

      const response = await apiClient.get<any[]>(
        `${ENDPOINTS.TAGS}/suggestions?${queryString}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async getTrendingTags(days = 7, limit = 20): Promise<any[]> {
    try {
      const response = await apiClient.get<any[]>(
        `${ENDPOINTS.TAGS}/trending?days=${days}&limit=${limit}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 분석 및 통계 =====

  async getTemplateAnalytics(id: string, period = 'month'): Promise<TemplateAnalyticsResponse> {
    try {
      const response = await apiClient.get<TemplateAnalyticsResponse>(
        `${ENDPOINTS.ANALYTICS}/templates/${id}?period=${period}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async getTemplateStats(): Promise<any> {
    try {
      const response = await apiClient.get<any>(
        `${ENDPOINTS.TEMPLATES}/stats/overview`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 템플릿 메타데이터 추출 =====

  async extractMetadata(name: string, description?: string, canvasData?: any): Promise<any> {
    try {
      // This would be a separate service endpoint for metadata extraction
      const response = await apiClient.post<any>(
        '/api/v1/templates/extract-metadata',
        {
          name,
          description,
          canvas_data: canvasData
        }
      );

      return response.data;
    } catch (error) {
      console.error('Failed to extract metadata:', error);
      return {};
    }
  }

  // ===== 파일 업로드 =====

  async uploadThumbnail(file: File): Promise<string> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.post<{ url: string }>(
        '/api/v1/upload/thumbnail',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      return response.data.url;
    } catch (error) {
      handleApiError(error);
    }
  }

  async uploadPreviewImages(files: File[]): Promise<string[]> {
    try {
      const formData = new FormData();
      files.forEach((file, index) => {
        formData.append(`files[${index}]`, file);
      });

      const response = await apiClient.post<{ urls: string[] }>(
        '/api/v1/upload/preview-images',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      return response.data.urls;
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 사용자 템플릿 =====

  async getMyTemplates(page = 1, pageSize = 20): Promise<TemplateSearchResponse> {
    try {
      const response = await apiClient.get<TemplateSearchResponse>(
        `/api/v1/templates/my?page=${page}&page_size=${pageSize}`
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  async publishTemplate(id: string): Promise<void> {
    try {
      await apiClient.post(`${ENDPOINTS.TEMPLATES}/${id}/publish`);
    } catch (error) {
      handleApiError(error);
    }
  }

  async unpublishTemplate(id: string): Promise<void> {
    try {
      await apiClient.post(`${ENDPOINTS.TEMPLATES}/${id}/unpublish`);
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 템플릿 복제 =====

  async duplicateTemplate(id: string, name?: string): Promise<TemplateDetailResponse> {
    try {
      const response = await apiClient.post<TemplateDetailResponse>(
        `${ENDPOINTS.TEMPLATES}/${id}/duplicate`,
        { name }
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 템플릿 공유 =====

  async shareTemplate(id: string, options: { public?: boolean; expiration?: string }): Promise<{ share_url: string }> {
    try {
      const response = await apiClient.post<{ share_url: string }>(
        `${ENDPOINTS.TEMPLATES}/${id}/share`,
        options
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 템플릿 내보내기 =====

  async exportTemplate(id: string, format: 'json' | 'pdf' | 'png' | 'svg' = 'json'): Promise<Blob> {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.TEMPLATES}/${id}/export?format=${format}`,
        {
          responseType: 'blob'
        }
      );

      return response.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  // ===== 인기도 추적 =====

  async trackTemplateView(id: string): Promise<void> {
    try {
      // Fire and forget - don't block UI for analytics
      apiClient.post(`${ENDPOINTS.TEMPLATES}/${id}/track-view`).catch(console.error);
    } catch (error) {
      // Silently fail for tracking
      console.error('Failed to track view:', error);
    }
  }

  async trackTemplateDownload(id: string): Promise<void> {
    try {
      apiClient.post(`${ENDPOINTS.TEMPLATES}/${id}/track-download`).catch(console.error);
    } catch (error) {
      console.error('Failed to track download:', error);
    }
  }

  // ===== 검색 자동완성 =====

  async getSearchSuggestions(query: string, limit = 10): Promise<string[]> {
    try {
      const response = await apiClient.get<string[]>(
        `/api/v1/search/suggestions?q=${encodeURIComponent(query)}&limit=${limit}`
      );

      return response.data;
    } catch (error) {
      console.error('Failed to get search suggestions:', error);
      return [];
    }
  }
}

// ===== 싱글톤 인스턴스 생성 =====

export const templateService = new TemplateService();

// ===== 기본 내보내기 =====

export default templateService;