/**
 * 고급 이미지 워크스페이스 컴포넌트
 * Request-Based Canvas 시스템과 통합된 CREATE/EDIT 모드 지원
 * 참조 이미지 기반 편집 및 Canvas 버전 관리 포함
 */

import React, { useState, useEffect } from 'react';
import { 
  Image as ImageIcon,
  Trash2, 
  Download,
  RefreshCw,
  Palette,
  Edit3,
  CheckCircle,
  Loader2,
  AlertCircle,
  Sparkles,
  Layers,
  GitBranch,
  Settings,
  Eye,
  Wand2
} from 'lucide-react';
import { useSimpleImageHistoryStore } from '../../stores/simpleImageHistoryStore';
import type { SimpleImageHistory } from '../../stores/simpleImageHistoryStore';

interface SimpleImageWorkspaceProps {
  conversationId: string;
  canvasId?: string; // Canvas ID (편집 전용)
  // Canvas는 편집 전용으로 운영됨
}

// Evolution 타입 확장 (Gemini 편집 포함)
type EvolutionType = 'variation' | 'modification' | 'extension' | 'based_on' | 'gemini_edit';

export const SimpleImageWorkspace: React.FC<SimpleImageWorkspaceProps> = ({ 
  conversationId,
  canvasId: initialCanvasId
}) => {
  // 기본 상태
  const [newPrompt, setNewPrompt] = useState('');
  const [evolutionType, setEvolutionType] = useState<EvolutionType>('based_on');
  
  // Gemini 편집 UI 상태
  const [selectedStyle, setSelectedStyle] = useState<string>('realistic');
  const [selectedSize, setSelectedSize] = useState<string>('1024x1024');
  const [currentCanvasId, setCurrentCanvasId] = useState<string | null>(initialCanvasId || null);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [optimizePrompt, setOptimizePrompt] = useState<boolean>(false);
  const [isOptimizingPrompt, setIsOptimizingPrompt] = useState<boolean>(false);
  
  // Canvas 관련 상태
  const [canvasVersions, setCanvasVersions] = useState<any[]>([]);
  const [activeCanvasVersion, setActiveCanvasVersion] = useState<number>(1);
  
  const {
    setSelectedImage,
    generateImage,
    evolveImage,
    deleteImage,
    loadHistory,
    hasImages,
    getImageCount,
    error,
    historyMap,
    selectedImageMap,
    loadingMap,
    lastUpdated
  } = useSimpleImageHistoryStore();
  
  // Store 상태를 직접 구독하여 변경 감지
  const images = historyMap.get(conversationId) || [];
  const selectedImageId = selectedImageMap.get(conversationId);
  const selectedImage = selectedImageId ? images.find(img => img.id === selectedImageId) || null : null;
  const loading = loadingMap.get(conversationId) || false;
  
  // Canvas는 항상 EDIT 모드로만 동작
  const currentMode = 'edit';
  
  // 이미지 목록 변경 감지 (디버깅용)
  useEffect(() => {
    console.log('🖼️ 이미지 목록 변경 감지:', {
      conversationId,
      imageCount: images.length,
      selectedImageId: selectedImage?.id,
      images: images.map(img => ({ id: img.id, prompt: img.prompt.substring(0, 30) + '...' }))
    });
  }, [images, selectedImage, conversationId]);
  
  // 컴포넌트 마운트 시 히스토리 로딩 및 Canvas ID 설정
  useEffect(() => {
    loadHistory(conversationId);
    
    // Canvas ID가 제공된 경우 설정
    if (initialCanvasId) {
      setCurrentCanvasId(initialCanvasId);
    }
  }, [conversationId, loadHistory, initialCanvasId]);
  
  // 선택된 이미지가 변경될 때 Canvas ID 설정
  useEffect(() => {
    if (selectedImage) {
      if (selectedImage.canvasId) {
        // 기존 Canvas ID 사용
        console.log('🎯 기존 Canvas ID 발견:', selectedImage.canvasId);
        setCurrentCanvasId(selectedImage.canvasId);
      } else {
        // Canvas ID가 없는 기존 이미지의 경우 자동 생성
        const autoCanvasId = `${conversationId}-image`;
        console.log('🔧 Canvas ID 자동 생성:', autoCanvasId, '(기존 이미지용)');
        setCurrentCanvasId(autoCanvasId);
      }
    } else {
      setCurrentCanvasId(null);
    }
  }, [selectedImage, conversationId]);
  
  // 이미지 업데이트 이벤트 리스너
  useEffect(() => {
    const handleImageUpdate = (event: CustomEvent) => {
      const { conversationId: eventConversationId, imageId, imageUrl } = event.detail;
      
      if (eventConversationId === conversationId) {
        console.log('🔄 이미지 업데이트 이벤트 수신:', { imageId, imageUrl });
        
        // 히스토리 강제 재로드
        loadHistory(conversationId, true);
        
        // 모든 이미지 요소에 캐시 버스팅 적용 (undefined 안전장치 포함)
        setTimeout(() => {
          // imageUrl 유효성 확인
          if (!imageUrl || imageUrl === 'undefined' || imageUrl === 'null') {
            console.warn('⚠️ Canvas 이미지 새로고침 생략 - 잘못된 URL:', imageUrl);
            return;
          }
          
          const baseUrl = imageUrl.split('?')[0];
          if (!baseUrl) {
            console.warn('⚠️ Canvas 이미지 새로고침 생략 - 기본 URL 추출 실패:', imageUrl);
            return;
          }
          
          const images = document.querySelectorAll('img');
          images.forEach((img) => {
            if (img.src && img.src.includes(baseUrl)) {
              const originalSrc = img.src.split('?')[0];
              img.src = `${originalSrc}?t=${Date.now()}`;
              console.log('🖼️ Canvas 이미지 강제 새로고침:', img.src);
            }
          });
        }, 100);
      }
    };

    // 이벤트 리스너 등록
    window.addEventListener('image-updated', handleImageUpdate as EventListener);
    
    // 정리 함수
    return () => {
      window.removeEventListener('image-updated', handleImageUpdate as EventListener);
    };
  }, [conversationId, loadHistory]);
  
  // Canvas는 편집 전용: 새 이미지는 채팅창에서 생성
  // handleGenerateImage 메서드 제거됨
  
  // 프롬프트 최적화 함수
  const handleOptimizePrompt = async () => {
    if (!newPrompt.trim()) {
      console.warn('⚠️ 최적화할 프롬프트가 없습니다');
      return;
    }
    
    setIsOptimizingPrompt(true);
    try {
      console.log('✨ 프롬프트 최적화 시작:', newPrompt);
      
      const response = await fetch('/api/v1/images/history/optimize-prompt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          prompt: newPrompt
        })
      });
      
      if (!response.ok) {
        throw new Error(`프롬프트 최적화 실패: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('✅ 프롬프트 최적화 완료:', result);
      
      // 최적화된 프롬프트로 교체
      setNewPrompt(result.optimized_prompt);
      
      // 사용자에게 개선 사항 알림 (간단한 콘솔 로그)
      if (result.improvement_notes) {
        console.log('📝 개선사항:', result.improvement_notes);
      }
      
    } catch (error) {
      console.error('❌ 프롬프트 최적화 실패:', error);
    } finally {
      setIsOptimizingPrompt(false);
    }
  };

  // Gemini 기반 이미지 편집 핸들러
  const handleEditImage = async () => {
    console.log('🔍 Canvas 편집 버튼 클릭됨');
    console.log('🔍 상태 확인:', {
      selectedImage: !!selectedImage,
      selectedImageId: selectedImage?.id,
      newPrompt: newPrompt.trim(),
      currentCanvasId,
      conversationId
    });
    
    if (!selectedImage || !newPrompt.trim() || !currentCanvasId) {
      console.warn('⚠️ 편집 조건 불만족:', {
        hasSelectedImage: !!selectedImage,
        hasPrompt: !!newPrompt.trim(),
        hasCanvasId: !!currentCanvasId
      });
      return;
    }
    
    try {
      console.log('✏️ Gemini 편집 모드 - Canvas 내 이미지 편집 시작');
      console.log(`Canvas ID: ${currentCanvasId}, 참조 이미지: ${selectedImage.id}`);
      console.log('📋 편집 요청 데이터:', {
        conversationId,
        selectedImageId: selectedImage.id,
        newPrompt: newPrompt,
        evolutionType: 'gemini_edit',
        optimizePrompt,
        source: 'canvas',
        workflowMode: 'gemini_edit',
        canvasId: currentCanvasId,
        referenceImageId: selectedImage.id,
        style: selectedStyle,
        size: selectedSize
      });
      
      const result = await evolveImage({
        conversationId,
        selectedImageId: selectedImage.id,
        newPrompt: newPrompt,
        evolutionType: 'gemini_edit' as any,
        optimizePrompt,
        source: 'canvas', // REQUEST SOURCE: CANVAS  
        workflowMode: 'gemini_edit',
        canvasId: currentCanvasId,
        referenceImageId: selectedImage.id,
        style: selectedStyle,
        size: selectedSize
      });
      
      console.log('✅ evolveImage 호출 완료:', result);
      
      setNewPrompt('');
      
      console.log(`✅ Gemini 이미지 편집이 완료되었으며 새 버전이 생성되었습니다!`);
      if (optimizePrompt) {
        console.log(`📈 프롬프트 최적화 기능이 적용되었습니다.`);
      }
      
    } catch (error) {
      console.error('❌ Gemini 이미지 편집 실패:', error);
      
      if (error instanceof Error && error.message.includes('500')) {
        console.error('⚠️ 서버에서 Gemini 이미지 편집 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
      } else {
        console.error('⚠️ 예상치 못한 오류가 발생했습니다. 네트워크 상태나 API 키를 확인해주세요.');
      }
    }
  };
  
  // Canvas는 편집만 가능 (새 이미지 생성은 채팅창에서만)
  const handleImageGeneration = async () => {
    await handleEditImage();
  };
  
  // 이미지 삭제 핸들러
  const handleDeleteImage = async (imageId: string) => {
    if (!confirm('이 이미지를 삭제하시겠습니까?')) return;
    
    try {
      await deleteImage(conversationId, imageId);
    } catch (error) {
      console.error('이미지 삭제 실패:', error);
    }
  };
  
  // 이미지 다운로드 핸들러
  const handleDownloadImage = async (imageUrl: string, prompt: string) => {
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      const a = document.createElement('a');
      a.href = url;
      a.download = `image-${prompt.slice(0, 20)}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('이미지 다운로드 실패:', error);
    }
  };
  
  return (
    <div className="h-full bg-white flex flex-col">
      {/* 헤더 */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Edit3 className="w-5 h-5 text-purple-600" />
            <div>
              <h2 className="text-lg font-semibold">
                Canvas 편집 모드
              </h2>
              {currentCanvasId && (
                <p className="text-xs text-gray-500">
                  Canvas ID: {currentCanvasId.slice(0, 8)}... | 버전: v{activeCanvasVersion}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3 text-sm text-gray-500">
            <div className="flex items-center gap-1">
              <span className="px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-700">
                EDIT
              </span>
            </div>
            <div>{getImageCount(conversationId)}개 이미지</div>
          </div>
        </div>
      </div>
      
      {/* 오류 표시 */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}
      
      {/* 이미지 생성/진화 폼 */}
      <div className="p-4 border-b border-gray-100 bg-gray-50">
        <div className="space-y-4">
          {/* 참조 이미지 표시 */}
          {selectedImage && (
            <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Eye className="w-4 h-4 text-purple-600" />
                <span className="text-sm font-medium text-purple-800">참조 이미지</span>
              </div>
              <div className="flex gap-3">
                <img 
                  key={`ref-${selectedImage.id}-${selectedImage.updatedAt || selectedImage.createdAt}`}
                  src={`${selectedImage.primaryImageUrl || ''}${selectedImage.primaryImageUrl?.includes('?') ? '&' : '?'}t=${lastUpdated || Date.now()}`}
                  alt="참조 이미지"
                  className="w-16 h-16 rounded object-cover border"
                />
                <div className="flex-1">
                  <p className="text-xs text-purple-700 line-clamp-2">
                    {selectedImage.prompt}
                  </p>
                  <p className="text-xs text-purple-600 mt-1">
                    {selectedImage.style} • {selectedImage.size}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* 편집 지시사항 입력 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              📝 편집 지시사항 (참조 이미지를 어떻게 수정할까요?)
            </label>
            <textarea
              value={newPrompt}
              onChange={(e) => setNewPrompt(e.target.value)}
              placeholder="예: '배경을 바다로 바꿔주세요', '빨간색 모자를 추가해주세요', '전체적으로 더 밝게 만들어주세요'"
              className="w-full h-24 px-3 py-2 border border-gray-300 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm"
            />
            
            {/* 프롬프트 최적화 버튼과 옵션 */}
            <div className="flex items-center justify-between mt-2">
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={optimizePrompt}
                    onChange={(e) => setOptimizePrompt(e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-600">편집 시 프롬프트 최적화</span>
                </label>
              </div>
              
              <button
                onClick={handleOptimizePrompt}
                disabled={!newPrompt.trim() || isOptimizingPrompt}
                className="flex items-center gap-1 px-3 py-1 text-sm text-purple-600 hover:text-purple-800 border border-purple-200 hover:border-purple-300 rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isOptimizingPrompt ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>최적화 중...</span>
                  </>
                ) : (
                  <>
                    <Wand2 className="w-4 h-4" />
                    <span>✨ 프롬프트 개선</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* 단순화된 편집 안내 */}
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
            <div className="flex items-center gap-2 mb-2">
              <Wand2 className="w-5 h-5 text-purple-600" />
              <span className="font-medium text-purple-800">스마트 이미지 편집</span>
            </div>
            <p className="text-sm text-purple-700">
              선택된 이미지를 기반으로 새로운 버전을 생성합니다. 원하는 변경사항을 구체적으로 설명해주세요.
            </p>
          </div>

          {/* 고급 옵션 토글 */}
          <div>
            <button
              onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-800 mb-2"
            >
              <Settings className="w-4 h-4" />
              <span>고급 옵션</span>
              <span className={`transform transition-transform ${showAdvancedOptions ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>

            {showAdvancedOptions && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-3 bg-white border border-gray-200 rounded-lg">
                {/* 스타일 선택 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    이미지 스타일
                  </label>
                  <select
                    value={selectedStyle}
                    onChange={(e) => setSelectedStyle(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  >
                    <option value="realistic">사실적 (Realistic)</option>
                    <option value="artistic">예술적 (Artistic)</option>
                    <option value="cartoon">만화 (Cartoon)</option>
                    <option value="abstract">추상적 (Abstract)</option>
                    <option value="3d">3D</option>
                    <option value="anime">애니메이션 (Anime)</option>
                  </select>
                </div>

                {/* 크기 선택 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    이미지 크기
                  </label>
                  <select
                    value={selectedSize}
                    onChange={(e) => setSelectedSize(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  >
                    <option value="1024x1024">정사각형 (1024×1024)</option>
                    <option value="1024x768">가로형 (1024×768)</option>
                    <option value="768x1024">세로형 (768×1024)</option>
                    <option value="1920x1080">와이드 (1920×1080)</option>
                    <option value="1080x1920">세로 와이드 (1080×1920)</option>
                  </select>
                </div>
              </div>
            )}
          </div>
          
          {/* 액션 버튼들 */}
          <div className="flex flex-wrap gap-2">
            {/* 편집 버튼 */}
            <button
              onClick={handleImageGeneration}
              disabled={loading || !newPrompt.trim() || !selectedImage}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">편집 중...</span>
                </>
              ) : (
                <>
                  <Wand2 className="w-4 h-4" />
                  <span>이미지 편집</span>
                </>
              )}
            </button>

            {/* 새 이미지 생성은 채팅창에서만 가능하다는 안내 */}
            <div className="text-xs text-gray-500 bg-blue-50 px-3 py-2 rounded-md border border-blue-200">
              💡 새 이미지 생성은 채팅창에서만 가능합니다. Canvas에서는 기존 이미지를 편집할 수 있습니다.
            </div>

            {/* Canvas 정보 버튼 */}
            {currentCanvasId && (
              <button
                onClick={() => {
                  // Canvas 버전 히스토리 표시 토글 기능
                  console.log('Canvas 정보:', { 
                    canvasId: currentCanvasId, 
                    version: activeCanvasVersion,
                    mode: currentMode
                  });
                }}
                className="flex items-center gap-2 px-3 py-2 bg-gray-50 text-gray-600 border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
                title="Canvas 정보 보기"
              >
                <Layers className="w-4 h-4" />
                <span className="text-sm">Canvas 정보</span>
              </button>
            )}
            
            {/* 새로고침 버튼 */}
            <button
              onClick={() => loadHistory(conversationId, true)}
              disabled={loading}
              className="flex items-center gap-2 px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span className="text-sm">새로고침</span>
            </button>
          </div>

          {/* 도움말 */}
          <div className="text-xs text-gray-500 bg-white p-3 rounded border">
            <div>
              <span className="font-medium text-purple-600">🎨 스마트 편집 모드:</span> 
              Gemini 2.5 Flash Image Preview를 사용하여 자연어 프롬프트로 간편한 이미지 편집을 제공합니다. 
              "색상을 더 따뜻하게", "배경을 파란 하늘로" 등 구체적으로 설명해주세요.
            </div>
          </div>
        </div>
      </div>
      
      {/* 이미지 히스토리 */}
      <div className="flex-1 overflow-auto">
        {loading && images.length === 0 ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            <span className="ml-2 text-gray-500">히스토리를 불러오는 중...</span>
          </div>
        ) : !hasImages(conversationId) ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500">
            <Edit3 className="w-12 h-12 mb-2" />
            <p>편집할 이미지가 없습니다.</p>
            <p className="text-sm">채팅창에서 이미지를 먼저 생성해주세요.</p>
          </div>
        ) : (
          <div className="p-4 space-y-4">
            {images.map((image) => (
              <ImageHistoryCard
                key={image.id}
                image={image}
                isSelected={selectedImage?.id === image.id}
                onSelect={() => setSelectedImage(conversationId, image.id)}
                onDelete={() => handleDeleteImage(image.id)}
                onDownload={() => handleDownloadImage(image.primaryImageUrl, image.prompt)}
                lastUpdated={lastUpdated}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// 개별 이미지 히스토리 카드 컴포넌트
interface ImageHistoryCardProps {
  image: SimpleImageHistory;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onDownload: () => void;
  lastUpdated?: number;
}

const ImageHistoryCard: React.FC<ImageHistoryCardProps> = ({
  image,
  isSelected,
  lastUpdated,
  onSelect,
  onDelete,
  onDownload
}) => {
  const formatDate = (date: string | Date | undefined) => {
    try {
      if (!date) {
        return '방금 전';
      }
      const dateObj = typeof date === 'string' ? new Date(date) : date;
      if (isNaN(dateObj.getTime())) {
        return '방금 전';
      }
      return new Intl.DateTimeFormat('ko-KR', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      }).format(dateObj);
    } catch (error) {
      console.error('날짜 포맷팅 오류:', error, '원본 데이터:', date);
      return '방금 전';
    }
  };
  
  return (
    <div 
      className={`border rounded-lg overflow-hidden cursor-pointer transition-all ${
        isSelected 
          ? 'border-blue-500 ring-2 ring-blue-200 shadow-md' 
          : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
      }`}
      onClick={onSelect}
    >
      {/* 이미지 */}
      <div className="aspect-square bg-gray-100 relative">
        <img
          key={`gallery-${image.id}-${image.updatedAt || image.createdAt}`}
          src={`${image.primaryImageUrl || ''}${image.primaryImageUrl?.includes('?') ? '&' : '?'}t=${lastUpdated || Date.now()}`}
          alt={image.prompt}
          className="w-full h-full object-cover"
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            // 이미지 로딩 실패 시 회색 placeholder 사용
            target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNDAwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iI2Y1ZjVmNSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTgiIGZpbGw9IiM5OTk5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj7snbTrr7jsp4Ag7JuA64+EIF+pLE8gNDAwOjQwMDwvdGV4dD48L3N2Zz4=';
          }}
        />
        
        {/* 선택 표시 */}
        {isSelected && (
          <div className="absolute top-2 right-2 bg-blue-600 text-white rounded-full p-1">
            <CheckCircle className="w-4 h-4" />
          </div>
        )}
        
        {/* 액션 버튼들 */}
        <div className="absolute bottom-2 right-2 flex gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDownload();
            }}
            className="p-1.5 bg-black/50 text-white rounded hover:bg-black/70 transition-colors"
            title="이미지 다운로드"
          >
            <Download className="w-3 h-3" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1.5 bg-red-500/80 text-white rounded hover:bg-red-600 transition-colors"
            title="이미지 삭제"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>
      
      {/* 메타데이터 */}
      <div className="p-3 space-y-2">
        <div className="text-sm text-gray-900 line-clamp-2 leading-tight">
          {image.prompt}
        </div>
        
        <div className="space-y-1">
          {/* Canvas 정보 (있는 경우) */}
          {(image.canvasId || image.canvasVersion || image.editMode) && (
            <div className="flex items-center gap-1 text-xs">
              <Layers className="w-3 h-3 text-gray-400" />
              <span className="text-gray-500">
                {image.canvasId && `Canvas: ${image.canvasId.slice(0, 6)}...`}
                {image.canvasVersion && ` v${image.canvasVersion}`}
              </span>
              {image.editMode && (
                <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                  image.editMode === 'EDIT' 
                    ? 'bg-purple-100 text-purple-700'
                    : 'bg-blue-100 text-blue-700'
                }`}>
                  {image.editMode}
                </span>
              )}
            </div>
          )}
          
          {/* 기존 메타데이터 */}
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{formatDate(image.createdAt)}</span>
            <div className="flex items-center gap-2">
              <span>{image.style}</span>
              <span>•</span>
              <span>{image.size}</span>
              {image.evolutionType && (
                <>
                  <span>•</span>
                  <span className={`font-medium ${
                    image.evolutionType === 'reference_edit' || image.evolutionType === 'gemini_edit' ? 'text-purple-600' : 'text-green-600'
                  }`}>
                    {image.evolutionType}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimpleImageWorkspace;