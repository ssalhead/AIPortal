/**
 * 개별 이미지 편집 인터페이스
 * 
 * 시리즈 내 개별 이미지를 수정, 재생성, 교체할 수 있는 고급 편집 인터페이스
 * - 인라인 편집 모드
 * - 프롬프트 수정 및 재생성
 * - 이미지 교체 및 버전 관리
 * - 실시간 미리보기
 */

import React, { useState, useEffect } from 'react';
import {
  Edit3,
  RefreshCw,
  Save,
  X,
  Copy,
  Trash2,
  Eye,
  Download,
  Settings,
  Wand2,
  History,
  ArrowLeft,
  ArrowRight,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

import { SeriesImage } from '../../types/imageSeries';
import { imageSeriesService } from '../../services/imageSeriesService';

interface ImageEditorProps {
  image: SeriesImage;
  seriesId: string;
  onImageUpdated: (updatedImage: SeriesImage) => void;
  onClose: () => void;
  className?: string;
}

interface EditableFields {
  prompt: string;
  style: string;
  size: string;
}

const ImageEditor: React.FC<ImageEditorProps> = ({
  image,
  seriesId,
  onImageUpdated,
  onClose,
  className = ''
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [editFields, setEditFields] = useState<EditableFields>({
    prompt: image.prompt,
    style: 'realistic', // TODO: 실제 스타일 정보 가져오기
    size: '1024x1024'  // TODO: 실제 크기 정보 가져오기
  });
  const [previewImage, setPreviewImage] = useState<string>(image.image_url);
  const [showVersionHistory, setShowVersionHistory] = useState(false);

  // 스타일 옵션
  const styleOptions = [
    { value: 'realistic', label: '사실적', icon: '📷' },
    { value: 'artistic', label: '예술적', icon: '🎨' },
    { value: 'cartoon', label: '만화', icon: '🎭' },
    { value: 'abstract', label: '추상적', icon: '🌀' },
    { value: '3d', label: '3D', icon: '🎮' },
    { value: 'anime', label: '애니메이션', icon: '✨' }
  ];

  // 크기 옵션
  const sizeOptions = [
    { value: '1024x1024', label: '1K 정사각형 (1:1)' },
    { value: '1152x896', label: '1K 가로형 (4:3)' },
    { value: '896x1152', label: '1K 세로형 (3:4)' },
    { value: '1344x768', label: '1K 와이드 (16:9)' },
    { value: '768x1344', label: '1K 세로 (9:16)' }
  ];

  // 편집 모드 토글
  const handleEditToggle = () => {
    if (isEditing) {
      // 편집 취소 - 원래 값으로 복원
      setEditFields({
        prompt: image.prompt,
        style: 'realistic',
        size: '1024x1024'
      });
    }
    setIsEditing(!isEditing);
  };

  // 변경사항 저장
  const handleSave = async () => {
    try {
      // TODO: 실제 API 호출로 이미지 메타데이터 업데이트
      const updatedImage: SeriesImage = {
        ...image,
        prompt: editFields.prompt
      };
      
      onImageUpdated(updatedImage);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to save changes:', error);
      alert('변경사항 저장에 실패했습니다.');
    }
  };

  // 이미지 재생성
  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      // TODO: 실제 이미지 재생성 API 호출
      // const result = await imageSeriesService.regenerateImage(seriesId, image.id, editFields);
      
      // 임시로 딜레이 후 성공 처리
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      const updatedImage: SeriesImage = {
        ...image,
        prompt: editFields.prompt,
        // image_url: result.image_url (실제 구현 시)
      };
      
      onImageUpdated(updatedImage);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to regenerate image:', error);
      alert('이미지 재생성에 실패했습니다.');
    } finally {
      setIsRegenerating(false);
    }
  };

  // 이미지 복사
  const handleCopyImage = async () => {
    try {
      if (navigator.clipboard && 'write' in navigator.clipboard) {
        // 이미지를 blob으로 변환하여 클립보드에 복사
        const response = await fetch(image.image_url);
        const blob = await response.blob();
        await navigator.clipboard.write([
          new ClipboardItem({ [blob.type]: blob })
        ]);
        alert('이미지가 클립보드에 복사되었습니다.');
      } else {
        // 대체 방법: 이미지 URL 복사
        await navigator.clipboard.writeText(image.image_url);
        alert('이미지 URL이 클립보드에 복사되었습니다.');
      }
    } catch (error) {
      console.error('Failed to copy image:', error);
      alert('이미지 복사에 실패했습니다.');
    }
  };

  // 이미지 다운로드
  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = image.image_url;
    a.download = `series-${seriesId}-image-${image.series_index}.png`;
    a.click();
  };

  // 프롬프트 복사
  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(editFields.prompt);
      alert('프롬프트가 클립보드에 복사되었습니다.');
    } catch (error) {
      console.error('Failed to copy prompt:', error);
    }
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden ${className}`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-medium">
            {image.series_index}
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
              이미지 편집
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              시리즈 #{image.series_index}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* 편집 모드 토글 */}
          <button
            onClick={handleEditToggle}
            className={`
              p-2 rounded-lg transition-colors
              ${isEditing 
                ? 'bg-blue-500 text-white' 
                : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              }
            `}
            title={isEditing ? '편집 취소' : '편집 모드'}
          >
            {isEditing ? <X className="w-4 h-4" /> : <Edit3 className="w-4 h-4" />}
          </button>

          {/* 버전 히스토리 */}
          <button
            onClick={() => setShowVersionHistory(!showVersionHistory)}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            title="버전 히스토리"
          >
            <History className="w-4 h-4" />
          </button>

          {/* 닫기 */}
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            title="닫기"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-4 space-y-6">
        {/* 이미지 미리보기 */}
        <div className="relative">
          <div className="aspect-square bg-gray-100 dark:bg-gray-900 rounded-lg overflow-hidden">
            {image.status === 'generating' ? (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center">
                  <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">생성 중...</p>
                </div>
              </div>
            ) : image.status === 'failed' ? (
              <div className="w-full h-full flex items-center justify-center">
                <div className="text-center">
                  <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                  <p className="text-sm text-red-600 dark:text-red-400">생성 실패</p>
                </div>
              </div>
            ) : (
              <img
                src={previewImage}
                alt={`Series image ${image.series_index}`}
                className="w-full h-full object-cover"
                onError={(e) => {
                  console.error('Image loading failed:', previewImage);
                  (e.target as HTMLImageElement).src = '/placeholder-image.svg';
                }}
              />
            )}

            {/* 상태 오버레이 */}
            {isRegenerating && (
              <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
                <div className="bg-white dark:bg-gray-800 rounded-lg p-4 text-center">
                  <Loader2 className="w-6 h-6 text-blue-500 animate-spin mx-auto mb-2" />
                  <p className="text-sm text-gray-900 dark:text-gray-100">재생성 중...</p>
                </div>
              </div>
            )}
          </div>

          {/* 이미지 액션 버튼들 */}
          {!isEditing && image.status === 'completed' && (
            <div className="absolute top-3 right-3 flex items-center gap-1 opacity-0 hover:opacity-100 transition-opacity">
              <button
                onClick={handleCopyImage}
                className="p-2 bg-black bg-opacity-70 text-white rounded-lg hover:bg-opacity-80 transition-colors"
                title="이미지 복사"
              >
                <Copy className="w-3 h-3" />
              </button>
              <button
                onClick={handleDownload}
                className="p-2 bg-black bg-opacity-70 text-white rounded-lg hover:bg-opacity-80 transition-colors"
                title="다운로드"
              >
                <Download className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {/* 편집 인터페이스 */}
        {isEditing ? (
          <div className="space-y-4">
            {/* 프롬프트 편집 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">
                  프롬프트
                </label>
                <button
                  onClick={handleCopyPrompt}
                  className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  title="프롬프트 복사"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </div>
              <textarea
                value={editFields.prompt}
                onChange={(e) => setEditFields(prev => ({ ...prev, prompt: e.target.value }))}
                className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
                rows={4}
                placeholder="이미지에 대한 설명을 입력하세요..."
              />
            </div>

            {/* 스타일 선택 */}
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                스타일
              </label>
              <div className="grid grid-cols-3 gap-2">
                {styleOptions.map(option => (
                  <button
                    key={option.value}
                    onClick={() => setEditFields(prev => ({ ...prev, style: option.value }))}
                    className={`
                      p-2 rounded-lg border text-sm transition-colors
                      ${editFields.style === option.value
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-900 dark:text-blue-100'
                        : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                      }
                    `}
                  >
                    <span className="mr-1">{option.icon}</span>
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 크기 선택 */}
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                크기
              </label>
              <select
                value={editFields.size}
                onChange={(e) => setEditFields(prev => ({ ...prev, size: e.target.value }))}
                className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              >
                {sizeOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 편집 액션 버튼들 */}
            <div className="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={handleSave}
                disabled={editFields.prompt.trim() === ''}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors
                  ${editFields.prompt.trim() 
                    ? 'bg-green-500 text-white hover:bg-green-600' 
                    : 'bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed'
                  }
                `}
              >
                <Save className="w-4 h-4" />
                저장
              </button>

              <button
                onClick={handleRegenerate}
                disabled={editFields.prompt.trim() === '' || isRegenerating}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors
                  ${editFields.prompt.trim() && !isRegenerating
                    ? 'bg-blue-500 text-white hover:bg-blue-600' 
                    : 'bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed'
                  }
                `}
              >
                {isRegenerating ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Wand2 className="w-4 h-4" />
                )}
                {isRegenerating ? '재생성 중...' : '재생성'}
              </button>

              <button
                onClick={handleEditToggle}
                className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <X className="w-4 h-4" />
                취소
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* 현재 프롬프트 표시 */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100">
                  현재 프롬프트
                </label>
                <button
                  onClick={handleCopyPrompt}
                  className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  title="프롬프트 복사"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg text-sm text-gray-700 dark:text-gray-300">
                {image.prompt || '프롬프트가 없습니다.'}
              </div>
            </div>

            {/* 이미지 정보 */}
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                이미지 정보
              </label>
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <p><strong>상태:</strong> {getStatusLabel(image.status)}</p>
                <p><strong>생성일:</strong> {new Date(image.created_at).toLocaleString('ko-KR')}</p>
                <p><strong>시리즈 순서:</strong> {image.series_index}</p>
              </div>
            </div>

            {/* 액션 버튼들 */}
            <div className="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                <Edit3 className="w-4 h-4" />
                편집
              </button>

              {image.status === 'completed' && (
                <>
                  <button
                    onClick={handleDownload}
                    className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    다운로드
                  </button>

                  <button
                    onClick={handleCopyImage}
                    className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    <Copy className="w-4 h-4" />
                    복사
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {/* 버전 히스토리 (확장된 경우) */}
        {showVersionHistory && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
              버전 히스토리
            </h4>
            <div className="space-y-2">
              <div className="flex items-center gap-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <div className="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded overflow-hidden">
                  <img
                    src={image.image_url}
                    alt="Current version"
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    현재 버전
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    {new Date(image.created_at).toLocaleString('ko-KR')}
                  </p>
                </div>
                <div className="text-blue-500">
                  <CheckCircle className="w-4 h-4" />
                </div>
              </div>
              
              {/* TODO: 이전 버전들 표시 */}
              <div className="text-center py-4 text-sm text-gray-500 dark:text-gray-400">
                이전 버전이 없습니다.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// 상태 라벨 헬퍼 함수
function getStatusLabel(status: string): string {
  switch (status) {
    case 'generating': return '생성 중';
    case 'completed': return '완성됨';
    case 'failed': return '실패';
    default: return status;
  }
}

export default ImageEditor;