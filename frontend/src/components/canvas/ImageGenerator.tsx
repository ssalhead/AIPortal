/**
 * 이미지 생성 컴포넌트
 */

import React, { useState } from 'react';
import { 
  Image, 
  Wand2, 
  Download, 
  RefreshCw, 
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
  { id: '1K_1:1', name: '1K 1:1', sample_image_size: '1K', aspect_ratio: '1:1' },
  { id: '1K_4:3', name: '1K 4:3', sample_image_size: '1K', aspect_ratio: '4:3' },
  { id: '1K_3:4', name: '1K 3:4', sample_image_size: '1K', aspect_ratio: '3:4' },
  { id: '1K_16:9', name: '1K 16:9', sample_image_size: '1K', aspect_ratio: '16:9' },
  { id: '1K_9:16', name: '1K 9:16', sample_image_size: '1K', aspect_ratio: '9:16' },
  { id: '2K_1:1', name: '2K 1:1', sample_image_size: '2K', aspect_ratio: '1:1' },
  { id: '2K_4:3', name: '2K 4:3', sample_image_size: '2K', aspect_ratio: '4:3' },
  { id: '2K_3:4', name: '2K 3:4', sample_image_size: '2K', aspect_ratio: '3:4' }
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
  const [selectedSize, setSelectedSize] = useState(isCanvas ? props.item.content.size || '1K_1:1' : '1K_1:1');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationHistory, setGenerationHistory] = useState<string[]>([]);

  // Canvas 모드에서 전달된 이미지 정보 로깅
  if (isCanvas) {
    console.log('🖼️ ImageGenerator 초기화:', {
      itemId: props.item.id,
      content: props.item.content,
      imageUrl: props.item.content.imageUrl,
      status: props.item.content.status
    });
  }
  
  // 작업 상태 폴링
  const pollJobStatus = async (jobId: string): Promise<void> => {
    const maxAttempts = 30; // 최대 30번 시도 (약 3분)
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/images/job/${jobId}`);
        if (!response.ok) {
          throw new Error('작업 상태 확인 실패');
        }
        
        const result = await response.json();
        
        if (result.status === 'completed' && result.images.length > 0) {
          handleImageGenerated(result.images[0]);
          return;
        } else if (result.status === 'failed') {
          throw new Error(result.error || '이미지 생성에 실패했습니다.');
        }
        
        // 6초 대기 후 재시도
        await new Promise(resolve => setTimeout(resolve, 6000));
        attempts++;
      } catch (error) {
        console.error('작업 상태 확인 오류:', error);
        attempts++;
        await new Promise(resolve => setTimeout(resolve, 6000));
      }
    }
    
    throw new Error('이미지 생성 시간이 초과되었습니다.');
  };
  
  // 이미지 생성 완료 처리
  const handleImageGenerated = (imageUrl: string) => {
    console.log('🖼️ 이미지 생성 완료:', imageUrl);
    console.log('🎨 Canvas 모드:', isCanvas);
    
    if (isCanvas) {
      console.log('📝 Canvas 업데이트 중...');
      props.onUpdate({
        content: {
          ...props.item.content,
          prompt,
          negativePrompt,
          style: selectedStyle,
          size: selectedSize,
          imageUrl: imageUrl,
          status: 'completed'
        }
      });
      console.log('✅ Canvas 업데이트 완료');
    } else {
      console.log('📋 일반 모드에서 이미지 생성 완료');
      props.onImageGenerated(imageUrl);
    }
    
    setGenerationHistory([...generationHistory, imageUrl]);
  };
  
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
      // 크기 옵션에서 size와 aspect_ratio 분리
      const sizeOption = SIZE_OPTIONS.find(opt => opt.id === selectedSize);
      if (!sizeOption) {
        throw new Error('유효하지 않은 크기 옵션입니다.');
      }
      
      // 이미지 생성 API 직접 호출 (올바른 백엔드 URL)
      const response = await fetch('http://localhost:8000/api/v1/images/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: prompt,
          style: selectedStyle,
          sample_image_size: sizeOption.sample_image_size,
          aspect_ratio: sizeOption.aspect_ratio,
          num_images: 1
        })
      });
      
      if (!response.ok) {
        throw new Error(`이미지 생성 실패: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (result.status === 'processing') {
        // 작업 상태를 주기적으로 확인
        const jobId = result.job_id;
        await pollJobStatus(jobId);
      } else if (result.status === 'completed' && result.images.length > 0) {
        const imageUrl = result.images[0];
        handleImageGenerated(imageUrl);
      } else {
        throw new Error('이미지 생성에 실패했습니다.');
      }
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
    <div className="flex flex-col h-full bg-slate-50 dark:bg-slate-900 p-4 gap-4">
      {/* 상단 이미지 미리보기 영역 */}
      <div className="flex-1 bg-white dark:bg-slate-800 rounded-xl shadow-lg overflow-hidden">
        {/* 미리보기 헤더 */}
        <div className="border-b border-slate-200 dark:border-slate-700 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg">
                <Image className="w-4 h-4 text-white" />
              </div>
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                이미지 미리보기
              </h3>
            </div>
            {((isCanvas && props.item.content.imageUrl) || generationHistory.length > 0) && !isGenerating && (
              <button
                onClick={handleGenerate}
                className="px-3 py-1.5 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors flex items-center gap-1 text-sm"
              >
                <RefreshCw className="w-3 h-3" />
                <span>재생성</span>
              </button>
            )}
          </div>
        </div>
        
        {/* 이미지 표시 영역 */}
        <div className="flex-1 p-4 flex flex-col">
          {isGenerating ? (
            <div className="flex-1 flex items-center justify-center bg-slate-50 dark:bg-slate-900 rounded-lg">
              <div className="text-center">
                <Loader2 className="w-16 h-16 text-blue-500 animate-spin mx-auto mb-4" />
                <p className="text-lg font-medium text-slate-600 dark:text-slate-400 mb-2">
                  이미지를 생성하고 있습니다...
                </p>
                <p className="text-sm text-slate-500 dark:text-slate-500">
                  약 10-30초 소요됩니다
                </p>
              </div>
            </div>
          ) : (isCanvas && props.item.content.status === 'error') ? (
            <div className="flex-1 flex items-center justify-center bg-slate-50 dark:bg-slate-900 rounded-lg">
              <div className="text-center">
                <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                <p className="text-lg font-medium text-red-600 dark:text-red-400 mb-2">
                  생성 실패
                </p>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                  {props.item.content.error || '이미지 생성에 실패했습니다'}
                </p>
                <button
                  onClick={handleGenerate}
                  className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center gap-2 mx-auto"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>다시 시도</span>
                </button>
              </div>
            </div>
          ) : ((isCanvas && props.item.content.imageUrl) || generationHistory.length > 0) ? (
            <div className="flex-1 flex flex-col">
              <div className="flex-1 bg-slate-50 dark:bg-slate-900 rounded-lg overflow-hidden flex items-center justify-center">
                <img
                  src={isCanvas ? props.item.content.imageUrl : generationHistory[generationHistory.length - 1]}
                  alt="Generated image"
                  className="max-w-full max-h-full object-contain rounded-lg"
                  onLoad={() => console.log('✅ 이미지 로드 성공:', isCanvas ? props.item.content.imageUrl : generationHistory[generationHistory.length - 1])}
                  onError={(e) => console.error('❌ 이미지 로드 실패:', e, isCanvas ? props.item.content.imageUrl : generationHistory[generationHistory.length - 1])}
                />
              </div>
              
              {/* 이미지 정보 */}
              <div className="mt-4 p-3 bg-slate-50 dark:bg-slate-900 rounded-lg">
                <div className="text-xs text-slate-600 dark:text-slate-400 space-y-1">
                  <p><span className="font-medium">스타일:</span> {STYLE_PRESETS.find(s => s.id === selectedStyle)?.name}</p>
                  <p><span className="font-medium">크기:</span> {SIZE_OPTIONS.find(s => s.id === selectedSize)?.name}</p>
                  <p><span className="font-medium">프롬프트:</span> {prompt.length > 50 ? prompt.substring(0, 50) + '...' : prompt}</p>
                </div>
              </div>
              
              {/* 생성 히스토리 */}
              {generationHistory.length > 1 && (
                <div className="mt-4">
                  <p className="text-xs font-medium text-slate-700 dark:text-slate-300 mb-2">
                    히스토리 ({generationHistory.length})
                  </p>
                  <div className="flex gap-2 overflow-x-auto">
                    {generationHistory.map((url, index) => (
                      <img
                        key={index}
                        src={url}
                        alt={`History ${index + 1}`}
                        className="w-16 h-16 object-cover rounded-lg border border-slate-200 dark:border-slate-700 cursor-pointer hover:opacity-80 transition-opacity flex-shrink-0"
                        onClick={() => {
                          if (isCanvas) {
                            props.onUpdate({
                              content: { ...props.item.content, imageUrl: url }
                            });
                          }
                        }}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center bg-slate-50 dark:bg-slate-900 rounded-lg">
              <div className="text-center">
                <Image className="w-16 h-16 text-slate-400 mx-auto mb-4" />
                <p className="text-lg font-medium text-slate-600 dark:text-slate-400 mb-2">
                  이미지 미리보기
                </p>
                <p className="text-sm text-slate-500 dark:text-slate-500">
                  프롬프트를 입력하고 '이미지 생성' 버튼을 클릭하세요
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* 하단 설정 패널 */}
      <div className="h-52 bg-white dark:bg-slate-800 rounded-xl shadow-lg flex flex-col">
        {/* 설정 헤더 */}
        <div className="border-b border-slate-200 dark:border-slate-700 p-3">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
            이미지 생성 설정
          </h3>
        </div>
        
        {/* 설정 폼 */}
        <div className="flex-1 p-4">
          <div className="grid grid-cols-3 gap-4 h-full">
            {/* 프롬프트 영역 (상하 배치) */}
            <div className="col-span-2 flex flex-col gap-2">
              {/* 프롬프트 입력 */}
              <div className="flex-1">
                <label className="block text-xs font-medium text-slate-900 dark:text-slate-200 mb-1">
                  프롬프트
                </label>
                <div className="relative h-12">
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="생성하고 싶은 이미지를 자세히 설명해주세요..."
                    className="w-full h-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all resize-none text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-500 dark:placeholder:text-slate-400"
                    disabled={isGenerating}
                  />
                  <button
                    onClick={handleCopyPrompt}
                    className="absolute top-1 right-1 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                    title="프롬프트 복사"
                  >
                    <Copy className="w-3 h-3" />
                  </button>
                </div>
              </div>
              
              {/* 네거티브 프롬프트 */}
              <div className="flex-1">
                <label className="block text-xs font-medium text-slate-900 dark:text-slate-200 mb-1">
                  네거티브 프롬프트
                </label>
                <textarea
                  value={negativePrompt}
                  onChange={(e) => setNegativePrompt(e.target.value)}
                  placeholder="제외하고 싶은 요소..."
                  className="w-full h-12 px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all resize-none text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-500 dark:placeholder:text-slate-400"
                  disabled={isGenerating}
                />
              </div>
            </div>
            
            {/* 설정 및 버튼 */}
            <div className="col-span-1 flex flex-col gap-2">
              {/* 스타일 선택 */}
              <div>
                <label className="block text-xs font-medium text-slate-900 dark:text-slate-200 mb-1">
                  스타일
                </label>
                <select
                  value={selectedStyle}
                  onChange={(e) => setSelectedStyle(e.target.value)}
                  disabled={isGenerating}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-sm text-slate-900 dark:text-slate-100"
                >
                  {STYLE_PRESETS.map((style) => (
                    <option key={style.id} value={style.id}>
                      {style.icon} {style.name}
                    </option>
                  ))}
                </select>
              </div>
              
              {/* 크기 선택 */}
              <div>
                <label className="block text-xs font-medium text-slate-900 dark:text-slate-200 mb-1">
                  크기
                </label>
                <select
                  value={selectedSize}
                  onChange={(e) => setSelectedSize(e.target.value)}
                  disabled={isGenerating}
                  className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-sm text-slate-900 dark:text-slate-100"
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
                disabled={isGenerating || !prompt.trim()}
                className={`
                  flex-1 px-4 py-2 rounded-lg font-medium transition-all flex items-center justify-center gap-2 text-sm mt-1
                  ${isGenerating
                    ? 'bg-slate-300 dark:bg-slate-700 text-slate-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600'
                  }
                `}
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>생성 중</span>
                  </>
                ) : (
                  <>
                    <Wand2 className="w-4 h-4" />
                    <span>이미지 생성</span>
                  </>
                )}
              </button>
              
              {/* 다운로드 버튼 */}
              {(isCanvas && props.item.content.imageUrl) && (
                <button
                  onClick={handleDownload}
                  className="w-full px-4 py-1.5 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors flex items-center justify-center gap-2 text-xs"
                >
                  <Download className="w-3 h-3" />
                  <span>다운로드</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};