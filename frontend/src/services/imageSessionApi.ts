/**
 * 이미지 세션 API 클라이언트
 * 백엔드 DB와 실시간 동기화를 위한 서비스 계층
 */

import type { ImageVersion, ImageGenerationSession } from '../types/imageSession';

const API_BASE_URL = '/api/v1/image-sessions';

// API 요청/응답 타입
export interface CreateSessionRequest {
  user_id: string;
  conversation_id: string;
  theme: string;
  base_prompt: string;
  evolution_history?: string[];
}

export interface AddVersionRequest {
  user_id: string;
  session_id: string;
  prompt: string;
  negative_prompt?: string;
  style?: string;
  size?: string;
  image_url?: string;
  parent_version_id?: string;
  status?: string;
}

export interface UpdateVersionRequest {
  user_id: string;
  version_id: string;
  image_url?: string;
  status?: string;
}

export interface SelectVersionRequest {
  user_id: string;
  session_id: string;
  version_id: string;
}

export interface DeleteVersionRequest {
  user_id: string;
  session_id: string;
  version_id: string;
}

// API 응답 타입 (백엔드와 매칭)
export interface ApiImageVersion {
  id: string;
  session_id: string;
  version_number: number;
  parent_version_id?: string;
  prompt: string;
  negative_prompt: string;
  style: string;
  size: string;
  image_url?: string;
  status: string;
  is_selected: boolean;
  created_at: string;
  updated_at: string;
}

export interface ApiImageSession {
  id: string;
  user_id: string;
  conversation_id: string;
  theme: string;
  base_prompt: string;
  evolution_history: string[];
  selected_version_id?: string;
  versions: ApiImageVersion[];
  created_at: string;
  updated_at: string;
}

// API 클라이언트 클래스
export class ImageSessionApiClient {
  
  /**
   * UUID 형식 검증
   */
  private static isValidUUID(uuid: string): boolean {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return uuidRegex.test(uuid);
  }
  
  /**
   * 새 이미지 세션 생성
   */
  static async createSession(request: CreateSessionRequest): Promise<ApiImageSession> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // Mock 인증이 활성화된 경우 헤더에 사용자 ID 추가
    if (request.user_id) {
      headers['X-Mock-User-ID'] = request.user_id;
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/sessions`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          conversation_id: request.conversation_id,
          theme: request.theme,
          base_prompt: request.base_prompt,
          evolution_history: request.evolution_history
        }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        // HTML 에러 페이지 감지
        if (errorText.includes('<!doctype') || errorText.includes('<html>')) {
          throw new Error(`서버 오류 (HTML 응답): ${response.status} ${response.statusText}`);
        }
        throw new Error(`세션 생성 실패: ${response.statusText}`);
      }
      
      const responseText = await response.text();
      
      // JSON 파싱 전에 HTML 응답 검사
      if (responseText.includes('<!doctype') || responseText.includes('<html>')) {
        throw new Error(`예상치 못한 HTML 응답 (JSON 대신): ${responseText.substring(0, 100)}...`);
      }
      
      return JSON.parse(responseText);
    } catch (error) {
      if (error instanceof SyntaxError && error.message.includes('Unexpected token')) {
        throw new Error(`JSON 파싱 오류 - 서버가 HTML을 반환했습니다: ${error.message}`);
      }
      throw error;
    }
  }
  
  /**
   * 대화 ID로 세션 조회
   */
  static async getSessionByConversation(conversationId: string, userId: string): Promise<ApiImageSession | null> {
    // UUID 형식 검증
    if (!this.isValidUUID(conversationId)) {
      throw new Error(`잘못된 Conversation ID 형식: ${conversationId} (UUID 형식이어야 합니다)`);
    }
    
    if (userId && !this.isValidUUID(userId)) {
      throw new Error(`잘못된 User ID 형식: ${userId} (UUID 형식이어야 합니다)`);
    }
    
    // 임시 사용자 ID를 헤더로 전송 (Mock 인증 시스템에서 사용)
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // Mock 인증이 활성화된 경우 헤더에 사용자 ID 추가
    if (userId) {
      headers['X-Mock-User-ID'] = userId;
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/session`, {
        method: 'GET',
        headers
      });
      
      if (response.status === 404) {
        return null; // 세션이 없음
      }
      
      if (!response.ok) {
        const errorText = await response.text();
        // HTML 에러 페이지 감지
        if (errorText.includes('<!doctype') || errorText.includes('<html>')) {
          throw new Error(`서버 오류 (HTML 응답): ${response.status} ${response.statusText}`);
        }
        throw new Error(`세션 조회 실패: ${response.statusText}`);
      }
      
      const responseText = await response.text();
      
      // JSON 파싱 전에 HTML 응답 검사
      if (responseText.includes('<!doctype') || responseText.includes('<html>')) {
        throw new Error(`예상치 못한 HTML 응답 (JSON 대신): ${responseText.substring(0, 100)}...`);
      }
      
      // null 응답 처리
      if (responseText.trim() === 'null') {
        return null;
      }
      
      return JSON.parse(responseText);
    } catch (error) {
      if (error instanceof SyntaxError && error.message.includes('Unexpected token')) {
        throw new Error(`JSON 파싱 오류 - 서버가 HTML을 반환했습니다: ${error.message}`);
      }
      throw error;
    }
  }
  
  /**
   * 세션에 새 버전 추가
   */
  static async addVersion(request: AddVersionRequest): Promise<ApiImageVersion> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // Mock 인증이 활성화된 경우 헤더에 사용자 ID 추가
    if (request.user_id) {
      headers['X-Mock-User-ID'] = request.user_id;
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/sessions/${request.session_id}/versions`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          prompt: request.prompt,
          negative_prompt: request.negative_prompt,
          style: request.style,
          size: request.size,
          image_url: request.image_url,
          parent_version_id: request.parent_version_id,
          status: request.status
        }),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        // HTML 에러 페이지 감지
        if (errorText.includes('<!doctype') || errorText.includes('<html>')) {
          throw new Error(`서버 오류 (HTML 응답): ${response.status} ${response.statusText}`);
        }
        throw new Error(`버전 추가 실패: ${response.statusText}`);
      }
      
      const responseText = await response.text();
      
      // JSON 파싱 전에 HTML 응답 검사
      if (responseText.includes('<!doctype') || responseText.includes('<html>')) {
        throw new Error(`예상치 못한 HTML 응답 (JSON 대신): ${responseText.substring(0, 100)}...`);
      }
      
      return JSON.parse(responseText);
    } catch (error) {
      if (error instanceof SyntaxError && error.message.includes('Unexpected token')) {
        throw new Error(`JSON 파싱 오류 - 서버가 HTML을 반환했습니다: ${error.message}`);
      }
      throw error;
    }
  }
  
  /**
   * 버전 업데이트
   */
  static async updateVersion(request: UpdateVersionRequest): Promise<ApiImageVersion> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // Mock 인증이 활성화된 경우 헤더에 사용자 ID 추가
    if (request.user_id) {
      headers['X-Mock-User-ID'] = request.user_id;
    }
    
    const response = await fetch(`${API_BASE_URL}/versions/${request.version_id}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({
        image_url: request.image_url,
        status: request.status
      }),
    });
    
    if (!response.ok) {
      throw new Error(`버전 업데이트 실패: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  /**
   * 버전 선택
   */
  static async selectVersion(request: SelectVersionRequest): Promise<ApiImageVersion> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // Mock 인증이 활성화된 경우 헤더에 사용자 ID 추가
    if (request.user_id) {
      headers['X-Mock-User-ID'] = request.user_id;
    }
    
    const response = await fetch(`${API_BASE_URL}/sessions/${request.session_id}/versions/${request.version_id}/select`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({}), // 빈 바디
    });
    
    if (!response.ok) {
      throw new Error(`버전 선택 실패: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  /**
   * 버전 삭제
   */
  static async deleteVersion(request: DeleteVersionRequest): Promise<{ success: boolean; deleted_version_id: string; deleted_image_url?: string; new_selected_version?: ApiImageVersion }> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // Mock 인증이 활성화된 경우 헤더에 사용자 ID 추가
    if (request.user_id) {
      headers['X-Mock-User-ID'] = request.user_id;
    }
    
    const response = await fetch(`${API_BASE_URL}/sessions/${request.session_id}/versions/${request.version_id}`, {
      method: 'DELETE',
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`버전 삭제 실패: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  /**
   * 대화에서 삭제된 이미지 URL 목록 조회
   */
  static async getDeletedImageUrls(conversationId: string, userId: string): Promise<string[]> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // Mock 인증이 활성화된 경우 헤더에 사용자 ID 추가
    if (userId) {
      headers['X-Mock-User-ID'] = userId;
    }
    
    const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/deleted-images`, {
      method: 'GET',
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`삭제된 이미지 URL 조회 실패: ${response.statusText}`);
    }
    
    const result = await response.json();
    return result.deleted_image_urls || [];
  }
}

// 유틸리티: API 응답을 Store 타입으로 변환
export class ApiResponseConverter {
  
  /**
   * API ImageSession을 Store ImageGenerationSession으로 변환
   */
  static toStoreSession(apiSession: ApiImageSession): ImageGenerationSession {
    return {
      conversationId: apiSession.conversation_id,
      theme: apiSession.theme,
      versions: apiSession.versions.map(this.toStoreVersion),
      selectedVersionId: apiSession.selected_version_id || '',
      basePrompt: apiSession.base_prompt,
      evolutionHistory: apiSession.evolution_history,
      createdAt: apiSession.created_at,
      updatedAt: apiSession.updated_at,
    };
  }
  
  /**
   * API ImageVersion을 Store ImageVersion으로 변환
   */
  static toStoreVersion(apiVersion: ApiImageVersion): ImageVersion {
    return {
      id: apiVersion.id,
      versionNumber: apiVersion.version_number,
      prompt: apiVersion.prompt,
      negativePrompt: apiVersion.negative_prompt,
      style: apiVersion.style,
      size: apiVersion.size,
      imageUrl: apiVersion.image_url || '',
      parentVersionId: apiVersion.parent_version_id,
      createdAt: apiVersion.created_at,
      isSelected: apiVersion.is_selected,
      status: apiVersion.status as 'generating' | 'completed' | 'failed',
    };
  }
}