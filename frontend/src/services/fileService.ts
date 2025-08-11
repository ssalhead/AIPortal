/**
 * 파일 관리 서비스
 */

import { apiService } from './api';

export interface FileUploadResponse {
  file_id: string;
  original_name: string;
  file_size: number;
  mime_type: string;
  file_extension: string;
  upload_path: string;
  status: string;
  checksum: string;
  created_at: string;
}

export interface FileMetadata {
  file_id: string;
  original_name: string;
  file_size: number;
  mime_type: string;
  file_extension: string;
  upload_path: string;
  status: string;
  checksum: string;
  processing_result?: any;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface FileListResponse {
  files: FileMetadata[];
  total: number;
  skip: number;
  limit: number;
}

class FileService {
  /**
   * 파일 업로드
   */
  async uploadFiles(
    files: File[],
    description?: string,
    tags?: string[]
  ): Promise<FileUploadResponse[]> {
    const formData = new FormData();
    
    // 파일들 추가
    files.forEach(file => {
      formData.append('files', file);
    });
    
    // 메타데이터 추가
    if (description) {
      formData.append('description', description);
    }
    if (tags && tags.length > 0) {
      formData.append('tags', tags.join(','));
    }
    
    const response = await apiService.httpClient.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  }
  
  /**
   * 단일 파일 업로드 (편의 메서드)
   */
  async uploadFile(
    file: File,
    description?: string,
    tags?: string[]
  ): Promise<FileUploadResponse> {
    const results = await this.uploadFiles([file], description, tags);
    return results[0];
  }
  
  /**
   * 사용자 파일 목록 조회
   */
  async getFiles(params: {
    skip?: number;
    limit?: number;
    file_type?: string;
    status?: string;
  } = {}): Promise<FileListResponse> {
    const response = await apiService.httpClient.get('/files', { params });
    return response.data;
  }
  
  /**
   * 파일 정보 조회
   */
  async getFileInfo(fileId: string): Promise<FileMetadata> {
    const response = await apiService.httpClient.get(`/files/${fileId}`);
    return response.data;
  }
  
  /**
   * 파일 다운로드 URL 생성
   */
  getDownloadUrl(fileId: string): string {
    return `${apiService.getBaseUrl()}/files/${fileId}/download`;
  }
  
  /**
   * 파일 다운로드
   */
  async downloadFile(fileId: string): Promise<Blob> {
    const response = await apiService.httpClient.get(`/files/${fileId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  }
  
  /**
   * 파일 삭제
   */
  async deleteFile(fileId: string): Promise<{ message: string }> {
    const response = await apiService.httpClient.delete(`/files/${fileId}`);
    return response.data;
  }
  
  /**
   * 파일 처리 시작
   */
  async processFile(
    fileId: string,
    processingType: string = 'auto'
  ): Promise<{ file_id: string; processing_type: string; status: string; message: string }> {
    const response = await apiService.httpClient.post(`/files/${fileId}/process`, {
      processing_type: processingType,
    });
    return response.data;
  }
  
  /**
   * 파일 크기 포맷팅
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
  
  /**
   * 파일 타입별 아이콘 클래스 반환
   */
  getFileTypeClass(mimeType: string): string {
    if (mimeType.startsWith('image/')) return 'text-purple-500';
    if (mimeType.includes('pdf')) return 'text-red-500';
    if (mimeType.includes('word') || mimeType.includes('document')) return 'text-blue-500';
    if (mimeType.includes('excel') || mimeType.includes('sheet')) return 'text-green-500';
    if (mimeType.includes('text')) return 'text-gray-500';
    if (mimeType.includes('python')) return 'text-green-600';
    if (mimeType.includes('javascript')) return 'text-yellow-600';
    if (mimeType.includes('typescript')) return 'text-blue-600';
    return 'text-gray-500';
  }
  
  /**
   * 파일 타입 레이블 반환
   */
  getFileTypeLabel(mimeType: string): string {
    const typeMap: Record<string, string> = {
      'text/plain': 'Text',
      'application/pdf': 'PDF',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel',
      'text/csv': 'CSV',
      'image/jpeg': 'JPEG',
      'image/png': 'PNG',
      'image/gif': 'GIF',
      'image/webp': 'WebP',
      'application/json': 'JSON',
      'text/markdown': 'Markdown',
      'application/x-python': 'Python',
      'text/x-python': 'Python',
      'application/javascript': 'JavaScript',
      'application/typescript': 'TypeScript',
    };
    
    return typeMap[mimeType] || 'Unknown';
  }
  
  /**
   * 파일이 이미지인지 확인
   */
  isImage(mimeType: string): boolean {
    return mimeType.startsWith('image/');
  }
  
  /**
   * 파일이 텍스트인지 확인  
   */
  isText(mimeType: string): boolean {
    return mimeType.startsWith('text/') || 
           mimeType.includes('json') ||
           mimeType.includes('javascript') ||
           mimeType.includes('python') ||
           mimeType.includes('typescript');
  }
  
  /**
   * 파일이 문서인지 확인
   */
  isDocument(mimeType: string): boolean {
    return mimeType.includes('pdf') ||
           mimeType.includes('word') ||
           mimeType.includes('document') ||
           mimeType.includes('excel') ||
           mimeType.includes('sheet') ||
           mimeType.includes('csv');
  }
}

export const fileService = new FileService();