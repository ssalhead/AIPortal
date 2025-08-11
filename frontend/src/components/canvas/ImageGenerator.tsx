/**
 * 이미지 생성 컴포넌트
 */

import React, { useState } from 'react';
import { 
  Image, 
  Wand2, 
  Download, 
  RefreshCw, 
  Palette,
  Sparkles,
  Copy,
  Loader2,
  AlertCircle
} from 'lucide-react';
import type { CanvasItem } from '../../types/canvas';

// 기존 Canvas 시스템용 인터페이스
interface CanvasImageGeneratorProps {
  item: CanvasItem;
  onUpdate: (updates: Partial<CanvasItem>) => void;
}

// 새로운 Workspace 시스템용 인터페이스  
interface WorkspaceImageGeneratorProps {
  onImageGenerated: (imageData: string) => void;
  readOnly?: boolean;
}

type ImageGeneratorProps = CanvasImageGeneratorProps | WorkspaceImageGeneratorProps;

const STYLE_PRESETS = [
  { id: 'realistic', name: '사실적', icon: '📷' },
  { id: 'artistic', name: '예술적', icon: '🎨' },
  { id: 'cartoon', name: '만화', icon: '🎭' },
  { id: 'abstract', name: '추상적', icon: '🌀' },
  { id: '3d', name: '3D', icon: '🎮' },
  { id: 'anime', name: '애니메이션', icon: '✨' }
];

const SIZE_OPTIONS = [
  { id: '256x256', name: '256×256', aspect: '1:1' },
  { id: '512x512', name: '512×512', aspect: '1:1' },
  { id: '1024x1024', name: '1024×1024', aspect: '1:1' },
  { id: '1024x768', name: '1024×768', aspect: '4:3' },
  { id: '1920x1080', name: '1920×1080', aspect: '16:9' }
];

export const ImageGenerator: React.FC<ImageGeneratorProps> = (props) => {
  // 타입 가드 함수
  const isCanvasProps = (props: ImageGeneratorProps): props is CanvasImageGeneratorProps => {
    return 'item' in props && 'onUpdate' in props;
  };
  
  const isCanvas = isCanvasProps(props);
  const readOnly = isCanvas ? false : props.readOnly || false;
  
  const [prompt, setPrompt] = useState(isCanvas ? props.item.content.prompt || '' : '');
  const [negativePrompt, setNegativePrompt] = useState(isCanvas ? props.item.content.negativePrompt || '' : '');
  const [selectedStyle, setSelectedStyle] = useState(isCanvas ? props.item.content.style || 'realistic' : 'realistic');
  const [selectedSize, setSelectedSize] = useState(isCanvas ? props.item.content.size || '512x512' : '512x512');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationHistory, setGenerationHistory] = useState<string[]>([]);
  
  const handleGenerate = async () => {
    if (!prompt.trim()) {
      alert('프롬프트를 입력해주세요!');
      return;
    }
    
    setIsGenerating(true);
    
    // 상태 업데이트 (Canvas 전용)
    if (isCanvas) {
      props.onUpdate({
        content: {
          ...props.item.content,
          prompt,
          negativePrompt,
          style: selectedStyle,
          size: selectedSize,
          status: 'generating'
        }
      });
    }
    
    try {
      // TODO: 실제 이미지 생성 API 호출
      // const response = await apiService.generateImage({
      //   prompt,
      //   negativePrompt,
      //   style: selectedStyle,
      //   size: selectedSize
      // });
      
      // Mock: 임시 이미지 URL 사용
      await new Promise(resolve => setTimeout(resolve, 2000)); // 2초 대기 시뮬레이션
      
      const mockImageUrl = `https://via.placeholder.com/${selectedSize.replace('x', '/')}/4A90E2/FFFFFF?text=Generated+Image`;
      
      if (isCanvas) {
        props.onUpdate({
          content: {
            ...props.item.content,
            prompt,
            negativePrompt,
            style: selectedStyle,
            size: selectedSize,
            imageUrl: mockImageUrl,
            status: 'completed'
          }
        });
      } else {
        props.onImageGenerated(mockImageUrl);
      }
      
      setGenerationHistory([...generationHistory, mockImageUrl]);
    } catch (error) {
      console.error('Image generation failed:', error);
      
      if (isCanvas) {
        props.onUpdate({
          content: {
            ...props.item.content,
            status: 'error',
            error: '이미지 생성에 실패했습니다. 다시 시도해주세요.'
          }
        });
      }
    } finally {
      setIsGenerating(false);
    }
  };
  
  const handleDownload = () => {
    const imageUrl = isCanvas ? props.item.content.imageUrl : generationHistory[generationHistory.length - 1];
    if (!imageUrl) return;
    
    const a = document.createElement('a');
    a.href = imageUrl;
    a.download = `generated-image-${Date.now()}.png`;
    a.click();
  };
  
  const handleCopyPrompt = () => {
    navigator.clipboard.writeText(prompt);
    alert('프롬프트가 클립보드에 복사되었습니다!');
  };
  
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg">
      {/* 헤더 */}
      <div className="border-b border-slate-200 dark:border-slate-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg">
              <Image className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                AI 이미지 생성
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                텍스트로 이미지를 생성합니다
              </p>
            </div>
          </div>
          {item.content.imageUrl && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleDownload}
                className="p-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                title="다운로드"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* 프롬프트 입력 */}
      <div className="p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            프롬프트
          </label>
          <div className="relative">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="생성하고 싶은 이미지를 자세히 설명해주세요..."
              className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all resize-none"
              rows={3}
              disabled={isGenerating}
            />
            <button
              onClick={handleCopyPrompt}
              className="absolute top-3 right-3 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
              title="프롬프트 복사"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            네거티브 프롬프트 (선택사항)
          </label>
          <textarea
            value={negativePrompt}
            onChange={(e) => setNegativePrompt(e.target.value)}
            placeholder="제외하고 싶은 요소를 입력하세요..."
            className="w-full px-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all resize-none"
            rows={2}
            disabled={isGenerating}
          />
        </div>
        
        {/* 스타일 선택 */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            스타일
          </label>
          <div className="grid grid-cols-3 gap-2">
            {STYLE_PRESETS.map((style) => (
              <button
                key={style.id}
                onClick={() => setSelectedStyle(style.id)}
                disabled={isGenerating}
                className={`
                  p-3 rounded-lg border transition-all
                  ${selectedStyle === style.id
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-900'
                  }
                  ${isGenerating ? 'opacity-50 cursor-not-allowed' : ''}
                `}
              >
                <div className="text-2xl mb-1">{style.icon}</div>
                <div className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  {style.name}
                </div>
              </button>
            ))}
          </div>
        </div>
        
        {/* 크기 선택 */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            크기
          </label>
          <select
            value={selectedSize}
            onChange={(e) => setSelectedSize(e.target.value)}
            disabled={isGenerating}
            className="w-full px-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
          >
            {SIZE_OPTIONS.map((size) => (
              <option key={size.id} value={size.id}>
                {size.name} ({size.aspect})
              </option>
            ))}
          </select>
        </div>
        
        {/* 생성 버튼 */}
        <button
          onClick={handleGenerate}
          disabled={isGenerating || !prompt.trim()}
          className={`
            w-full px-6 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2
            ${isGenerating
              ? 'bg-slate-300 dark:bg-slate-700 text-slate-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600 transform hover:scale-[1.02]'
            }
          `}
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>생성 중...</span>
            </>
          ) : (
            <>
              <Wand2 className="w-5 h-5" />
              <span>이미지 생성</span>
            </>
          )}
        </button>
      </div>
      
      {/* 생성된 이미지 표시 */}
      {(item.content.imageUrl || isGenerating) && (
        <div className="border-t border-slate-200 dark:border-slate-700 p-6">
          <div className="relative bg-slate-100 dark:bg-slate-900 rounded-lg overflow-hidden">
            {isGenerating ? (
              <div className="aspect-square flex items-center justify-center">
                <div className="text-center">
                  <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-3" />
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    이미지를 생성하고 있습니다...
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                    약 10-30초 소요됩니다
                  </p>
                </div>
              </div>
            ) : (isCanvas && props.item.content.status === 'error') ? (
              <div className="aspect-square flex items-center justify-center">
                <div className="text-center">
                  <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {isCanvas ? props.item.content.error : '이미지 생성에 실패했습니다'}
                  </p>
                  <button
                    onClick={handleGenerate}
                    className="mt-3 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center gap-2 mx-auto"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span>다시 시도</span>
                  </button>
                </div>
              </div>
            ) : (
              <img
                src={item.content.imageUrl}
                alt="Generated image"
                className="w-full h-auto"
              />
            )}
          </div>
          
          {item.content.imageUrl && !isGenerating && (
            <div className="mt-4 flex items-center justify-between">
              <div className="text-xs text-slate-500 dark:text-slate-400">
                <p>스타일: {STYLE_PRESETS.find(s => s.id === item.content.style)?.name}</p>
                <p>크기: {item.content.size}</p>
              </div>
              <button
                onClick={handleGenerate}
                className="px-3 py-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" />
                <span className="text-sm">재생성</span>
              </button>
            </div>
          )}
        </div>
      )}
      
      {/* 생성 히스토리 */}
      {generationHistory.length > 0 && (
        <div className="border-t border-slate-200 dark:border-slate-700 p-4">
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
            생성 히스토리 ({generationHistory.length})
          </p>
          <div className="flex gap-2 overflow-x-auto">
            {generationHistory.map((url, index) => (
              <img
                key={index}
                src={url}
                alt={`History ${index + 1}`}
                className="w-20 h-20 object-cover rounded-lg border border-slate-200 dark:border-slate-700 cursor-pointer hover:opacity-80 transition-opacity"
                onClick={() => onUpdate({
                  content: { ...item.content, imageUrl: url }
                })}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
};