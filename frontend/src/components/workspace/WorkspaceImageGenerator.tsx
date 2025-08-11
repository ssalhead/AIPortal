/**
 * 워크스페이스용 이미지 생성 컴포넌트
 */

import React, { useState } from 'react';
import { Image, Wand2, RefreshCw, AlertCircle, Loader2 } from 'lucide-react';

interface WorkspaceImageGeneratorProps {
  onImageGenerated: (imageData: string) => void;
  readOnly?: boolean;
}

const STYLE_PRESETS = [
  { id: 'realistic', name: '사실적', icon: '📷' },
  { id: 'artistic', name: '예술적', icon: '🎨' },
  { id: 'cartoon', name: '만화', icon: '🎭' },
  { id: 'abstract', name: '추상적', icon: '🌀' },
  { id: '3d', name: '3D', icon: '🎮' },
  { id: 'anime', name: '애니메이션', icon: '✨' }
];

const SIZE_OPTIONS = [
  { id: '256x256', name: '256×256' },
  { id: '512x512', name: '512×512' },
  { id: '1024x1024', name: '1024×1024' }
];

export const WorkspaceImageGenerator: React.FC<WorkspaceImageGeneratorProps> = ({
  onImageGenerated,
  readOnly = false
}) => {
  const [prompt, setPrompt] = useState('');
  const [selectedStyle, setSelectedStyle] = useState('realistic');
  const [selectedSize, setSelectedSize] = useState('512x512');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!prompt.trim() || readOnly) return;
    
    setIsGenerating(true);
    setError(null);
    
    try {
      // Mock 이미지 생성 (실제 API 연동 필요)
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const mockImageUrl = `https://via.placeholder.com/${selectedSize.replace('x', '/')}/4A90E2/FFFFFF?text=Generated+Image`;
      
      setGeneratedImage(mockImageUrl);
      onImageGenerated(mockImageUrl);
    } catch (err) {
      setError('이미지 생성에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-white rounded-lg">
      {/* 설정 패널 */}
      <div className="p-4 border-b border-gray-200">
        <div className="space-y-4">
          {/* 프롬프트 입력 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              이미지 설명
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={readOnly}
              placeholder="생성하고 싶은 이미지를 설명해주세요..."
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:opacity-50"
              rows={3}
            />
          </div>

          {/* 스타일 선택 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              스타일
            </label>
            <div className="grid grid-cols-3 gap-2">
              {STYLE_PRESETS.map((style) => (
                <button
                  key={style.id}
                  onClick={() => setSelectedStyle(style.id)}
                  disabled={readOnly}
                  className={`p-2 rounded-lg border text-sm transition-colors disabled:opacity-50 ${
                    selectedStyle === style.id
                      ? 'bg-blue-50 border-blue-200 text-blue-700'
                      : 'bg-white border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="text-lg mb-1">{style.icon}</div>
                  {style.name}
                </button>
              ))}
            </div>
          </div>

          {/* 크기 선택 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              크기
            </label>
            <select
              value={selectedSize}
              onChange={(e) => setSelectedSize(e.target.value)}
              disabled={readOnly}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {SIZE_OPTIONS.map((size) => (
                <option key={size.id} value={size.id}>
                  {size.name}
                </option>
              ))}
            </select>
          </div>

          {/* 생성 버튼 */}
          <button
            onClick={handleGenerate}
            disabled={!prompt.trim() || isGenerating || readOnly}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                생성 중...
              </>
            ) : (
              <>
                <Wand2 className="w-4 h-4" />
                이미지 생성
              </>
            )}
          </button>
        </div>
      </div>

      {/* 결과 영역 */}
      <div className="flex-1 p-4">
        {error ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
              <p className="text-sm text-red-600">{error}</p>
              <button
                onClick={handleGenerate}
                disabled={readOnly}
                className="mt-3 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50"
              >
                <RefreshCw className="w-4 h-4 mr-2 inline" />
                다시 시도
              </button>
            </div>
          </div>
        ) : generatedImage ? (
          <div className="h-full flex flex-col">
            <img
              src={generatedImage}
              alt="Generated"
              className="flex-1 w-full object-contain rounded-lg"
            />
            <div className="mt-3 text-xs text-gray-500 text-center">
              스타일: {STYLE_PRESETS.find(s => s.id === selectedStyle)?.name} • 
              크기: {selectedSize}
            </div>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-gray-500">
              <Image className="w-12 h-12 mx-auto mb-3" />
              <p className="text-sm">이미지를 생성해보세요</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};