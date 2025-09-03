/**
 * 이미지 시리즈 API 서비스
 */

import { 
  ImageSeries, 
  SeriesImage, 
  SeriesTemplate, 
  SeriesCreationRequest, 
  SeriesGenerationProgress 
} from '../types/imageSeries';

class ImageSeriesService {
  private baseUrl = 'http://localhost:8000/api/v1';

  /**
   * 새 이미지 시리즈 생성
   */
  async createSeries(request: SeriesCreationRequest): Promise<ImageSeries> {
    const response = await fetch(`${this.baseUrl}/series`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create series');
    }

    return response.json();
  }

  /**
   * 시리즈 정보 조회
   */
  async getSeries(seriesId: string): Promise<ImageSeries> {
    const response = await fetch(`${this.baseUrl}/series/${seriesId}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get series');
    }

    return response.json();
  }

  /**
   * 시리즈 이미지 목록 조회
   */
  async getSeriesImages(seriesId: string, includeMetadata = false): Promise<SeriesImage[]> {
    const response = await fetch(`${this.baseUrl}/series/${seriesId}/images?include_metadata=${includeMetadata}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get series images');
    }

    return response.json();
  }

  /**
   * 시리즈 삭제
   */
  async deleteSeries(seriesId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/series/${seriesId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete series');
    }
  }

  /**
   * 시리즈 일괄 생성 (스트리밍)
   */
  async generateSeriesBatch(
    seriesId: string, 
    batchSize: number = 4,
    onProgress?: (progress: SeriesGenerationProgress) => void
  ): Promise<void> {
    const response = await fetch(`${this.baseUrl}/series/${seriesId}/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        series_id: seriesId,
        batch_size: batchSize,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start series generation');
    }

    if (!response.body) {
      throw new Error('No response body for streaming');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              if (onProgress) {
                onProgress(data);
              }
            } catch (e) {
              console.error('Failed to parse progress data:', e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  /**
   * 사용 가능한 템플릿 목록 조회
   */
  async getTemplates(seriesType?: string, featuredOnly = false): Promise<SeriesTemplate[]> {
    const params = new URLSearchParams();
    if (seriesType) params.append('series_type', seriesType);
    if (featuredOnly) params.append('featured_only', 'true');

    const response = await fetch(`${this.baseUrl}/templates?${params.toString()}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get templates');
    }

    return response.json();
  }

  /**
   * 새 템플릿 생성
   */
  async createTemplate(template: Omit<SeriesTemplate, 'id' | 'usage_count' | 'rating'>): Promise<SeriesTemplate> {
    const response = await fetch(`${this.baseUrl}/templates`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(template),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create template');
    }

    return response.json();
  }

  /**
   * 완성된 시리즈를 템플릿으로 복제
   */
  async duplicateAsTemplate(seriesId: string, templateName: string): Promise<SeriesTemplate> {
    const response = await fetch(`${this.baseUrl}/series/${seriesId}/template`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ template_name: templateName }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to duplicate as template');
    }

    return response.json();
  }

  /**
   * 지원하는 시리즈 타입 목록 조회
   */
  async getSeriesTypes(): Promise<Record<string, any>> {
    const response = await fetch(`${this.baseUrl}/series-types`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get series types');
    }

    return response.json();
  }
}

export const imageSeriesService = new ImageSeriesService();