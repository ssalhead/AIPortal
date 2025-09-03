/**
 * 이미지 생성 컴포넌트
 */

import React, { useState, useEffect } from 'react';
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
import { useImageGenerationStore } from '../../stores/imageGenerationStore';
import { useImageSessionStore } from '../../stores/imageSessionStore';
import { useCanvasStore } from '../../stores/canvasStore';
import { ConversationCanvasManager } from '../../services/conversationCanvasManager';
import ImageVersionGallery from './ImageVersionGallery';

// 기존 Canvas 시스템용 인터페이스
interface CanvasImageGeneratorProps {
  item: CanvasItem;
  onUpdate: (updates: Partial<CanvasItem>) => void;
  conversationId?: string; // 진화형 시스템용
}

// 새로운 Workspace 시스템용 인터페이스  
interface WorkspaceImageGeneratorProps {
  onImageGenerated: (imageData: string) => void;
  conversationId: string; // 필수 필드
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
  
  // conversationId 추출 및 경로 추적
  const conversationId = isCanvas 
    ? props.conversationId 
    : props.conversationId;
    
  // 🔍 conversationId 전달 경로 추적 로깅
  console.log('🔍 [ROUTE] ImageGenerator conversationId 전달 경로:');
  console.log('🔍 [ROUTE] - isCanvas:', isCanvas);
  console.log('🔍 [ROUTE] - props.conversationId:', props.conversationId);
  console.log('🔍 [ROUTE] - 최종 conversationId:', conversationId);
  
  // 진화형 이미지 세션 Store
  const {
    getSession,
    hasSession,
    createSession,
    addVersion,
    updateVersion,
    selectVersion,
    deleteVersion,
    deleteAllVersions,
    getSelectedVersion,
    extractTheme,
    evolvePrompt,
    // 하이브리드 메서드들 추가
    createSessionHybrid,
    addVersionHybrid,
    deleteVersionHybrid,
    selectVersionHybrid,
  } = useImageSessionStore();
  
  // 현재 세션 정보
  const session = conversationId ? getSession(conversationId) : null;
  const selectedVersion = conversationId ? getSelectedVersion(conversationId) : null;
  
  const [prompt, setPrompt] = useState(
    selectedVersion?.prompt || 
    (isCanvas ? props.item.content.prompt || '' : '')
  );
  const [negativePrompt, setNegativePrompt] = useState(
    selectedVersion?.negativePrompt || 
    (isCanvas ? props.item.content.negativePrompt || '' : '')
  );
  const [selectedStyle, setSelectedStyle] = useState(
    selectedVersion?.style || 
    (isCanvas ? props.item.content.style || 'realistic' : 'realistic')
  );
  const [selectedSize, setSelectedSize] = useState(
    selectedVersion?.size || 
    (isCanvas ? props.item.content.size || '1K_1:1' : '1K_1:1')
  );
  // 글로벌 이미지 생성 상태 사용
  const { 
    isGenerating: globalIsGenerating, 
    getJobByArtifactId,
    startGeneration,
    updateProgress,
    completeGeneration,
    failGeneration
  } = useImageGenerationStore();
  
  // 로컬 상태 (글로벌 상태로 대체)
  const [generationHistory, setGenerationHistory] = useState<string[]>([]);
  
  // Canvas 모드에서 글로벌 상태 확인
  const artifactId = isCanvas ? props.item.id : null;
  const currentJob = artifactId ? getJobByArtifactId(artifactId) : null;
  const isGenerating = currentJob ? currentJob.status === 'generating' : false;

  // Canvas 모드에서 전달된 이미지 정보 로깅
  if (isCanvas) {
    console.log('🖼️ ImageGenerator 초기화:', {
      itemId: props.item.id,
      content: props.item.content,
      imageUrl: props.item.content.imageUrl,
      status: props.item.content.status
    });
  }
  
  // 🔄 conversationId 변경 감지 및 컴포넌트 재초기화
  useEffect(() => {
    if (!conversationId) return;
    
    console.log('🔄 ImageGenerator - conversationId 변경 감지:', {
      newConversationId: conversationId,
      sessionExists: hasSession(conversationId),
      isCanvas
    });
    
    // Canvas 모드에서 conversationId가 변경되면 상태 리셋
    if (isCanvas) {
      // 프롬프트와 설정값들 초기화 (현재 활성화된 Canvas의 설정값으로 초기화)
      const currentItem = props.item;
      setPrompt(currentItem.content.prompt || '');
      setNegativePrompt(currentItem.content.negativePrompt || '');
      setSelectedStyle(currentItem.content.style || 'realistic');
      setSelectedSize(currentItem.content.size || '1K_1:1');
      
      console.log('✅ ImageGenerator - Canvas 모드 상태 리셋 완료:', {
        prompt: currentItem.content.prompt || '',
        style: currentItem.content.style || 'realistic',
        size: currentItem.content.size || '1K_1:1'
      });
    }
  }, [conversationId, hasSession, isCanvas]);
  
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
  
  // 이미지 생성 완료 처리 - 진화형 시스템 통합 (하이브리드)
  const handleImageGenerated = async (imageUrl: string) => {
    console.log('🖼️ 이미지 생성 완료:', imageUrl);
    console.log('🎨 Canvas 모드:', isCanvas);
    console.log('🔄 세션 모드:', !!conversationId);
    
    // === 🔍 강화된 상태 디버깅 로깅 ===
    console.log('🔍 [DEBUG] handleImageGenerated 상태 점검:');
    console.log('🔍 [DEBUG] - conversationId:', conversationId);
    console.log('🔍 [DEBUG] - prompt:', prompt);
    console.log('🔍 [DEBUG] - selectedStyle:', selectedStyle);
    console.log('🔍 [DEBUG] - selectedSize:', selectedSize);
    console.log('🔍 [DEBUG] - negativePrompt:', negativePrompt);
    
    // ImageSessionStore 전체 상태 확인
    const { sessions } = useImageSessionStore.getState();
    console.log('🔍 [DEBUG] ImageSessionStore 전체 세션 목록:');
    sessions.forEach((session, id) => {
      console.log(`🔍 [DEBUG] - 세션 ${id}: ${session.versions.length}개 버전`);
    });
    
    // 1. 진화형 세션 시스템 업데이트
    // 실시간으로 세션 재조회 (createSession 후에도 정확한 세션 정보 확보)
    let currentSession = conversationId ? getSession(conversationId) : null;
    console.log('🔍 [DEBUG] 실시간 세션 조회 결과:', currentSession ? {
      id: currentSession.conversationId,
      theme: currentSession.theme,
      versionsCount: currentSession.versions.length,
      selectedVersionId: currentSession.selectedVersionId
    } : 'null');
    
    // 🛡️ 이중 안전장치: 세션이 없으면 즉석에서 생성 (하이브리드)
    if (conversationId && !currentSession) {
      console.log('🛡️ [SAFETY] 세션이 없어서 handleImageGenerated에서 즉석 생성 (하이브리드)');
      const theme = extractTheme(prompt);
      try {
        const emergencySession = await createSessionHybrid(conversationId, theme, prompt);
        console.log('🛡️ [SAFETY] 응급 세션 생성 완료 (하이브리드):', {
          conversationId,
          theme,
          newSessionId: emergencySession.conversationId
        });
        
        // 즉시 재조회하여 세션 존재 확인
        currentSession = getSession(conversationId);
        console.log('🛡️ [SAFETY] 응급 세션 생성 후 재조회:', currentSession ? 'success' : 'failed');
      } catch (error) {
        console.error('❌ [SAFETY] 응급 세션 생성 실패:', error);
        // 에러 시 기존 메서드로 폴백
        const emergencySession = createSession(conversationId, theme, prompt);
        currentSession = getSession(conversationId);
      }
    }
    
    if (conversationId && currentSession) {
      console.log('🔍 [DEBUG] 버전 추가 실행 중...');
      console.log('🔍 [DEBUG] 추가할 버전 데이터:', {
        prompt,
        negativePrompt,
        style: selectedStyle,
        size: selectedSize,
        imageUrl,
        status: 'completed'
      });
      
      // 새 버전 추가 (하이브리드)
      const newVersionId = await addVersionHybrid(conversationId, {
        prompt,
        negativePrompt,
        style: selectedStyle,
        size: selectedSize,
        imageUrl,
        status: 'completed',
      });
      
      console.log('🔍 [DEBUG] addVersion 호출 완료, 반환된 versionId:', newVersionId);
      
      // 추가 후 즉시 세션 상태 재확인
      const updatedSession = getSession(conversationId);
      console.log('🔍 [DEBUG] 버전 추가 후 세션 상태:', updatedSession ? {
        versionsCount: updatedSession.versions.length,
        selectedVersionId: updatedSession.selectedVersionId,
        lastVersion: updatedSession.versions[updatedSession.versions.length - 1]
      } : 'null');
      
      console.log('✨ 새 이미지 버전 추가됨:', {
        conversationId,
        versionId: newVersionId,
        versionNumber: currentSession.versions.length + 1,
      });
      
      // 버전 추가 후 Canvas Store와 동기화 (타이밍 최적화)
      console.log('🔄 Canvas Store와 동기화 시작... (지연 실행으로 Zustand 업데이트 보장)');
      
      // ⚡ 타이밍 최적화: setTimeout으로 Zustand store 업데이트 완료 후 동기화
      setTimeout(() => {
        console.log('⚡ [TIMING] Canvas 동기화 실행 (Zustand 업데이트 완료 후)');
        
        // ConversationCanvasManager를 사용한 통합 Canvas 업데이트
        const { updateConversationCanvas } = useCanvasStore.getState();
        const canvasData = {
          prompt,
          negativePrompt,
          style: selectedStyle,
          size: selectedSize,
          imageUrl: imageUrl,
          status: 'completed',
          generation_result: { images: [imageUrl] }
        };
        const updatedCanvasId = updateConversationCanvas(conversationId, 'image', canvasData);
        console.log('✅ Canvas Store 동기화 완료 (중복 방지), Canvas ID:', updatedCanvasId);
        
        // 동기화 완료 후 최종 상태 확인
        const finalSession = getSession(conversationId);
        console.log('⚡ [TIMING] 동기화 완료 후 최종 상태:', finalSession ? {
          versionsCount: finalSession.versions.length,
          selectedVersionId: finalSession.selectedVersionId
        } : 'null');
      }, 100); // 100ms 지연으로 React 상태 업데이트 사이클 고려
    } else if (conversationId) {
      console.error('❌ [ERROR] 세션이 없어 버전 추가 실패 - 이중 안전장치도 실패');
      console.error('❌ [ERROR] - conversationId:', conversationId);
      console.error('❌ [ERROR] - sessionExists:', !!currentSession);
      console.error('❌ [ERROR] - ImageSessionStore 전체 상태:');
      const { sessions } = useImageSessionStore.getState();
      sessions.forEach((session, id) => {
        console.error(`❌ [ERROR] - 세션 ${id}: ${session.versions.length}개 버전`);
      });
    } else {
      console.warn('⚠️ [WARNING] conversationId가 없어서 세션 시스템을 사용하지 않습니다');
    }
    
    // 2. 기존 Canvas 시스템 업데이트 (하위 호환성)
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
    
    // 1. 진화형 세션 확인 및 생성 (세션이 없을 때만)
    // 실시간으로 세션 조회 (최신 상태 반영)
    const currentSessionForGenerate = conversationId ? getSession(conversationId) : null;
    console.log('🔍 [DEBUG] handleGenerate 세션 생성 전 상태:');
    console.log('🔍 [DEBUG] - conversationId:', conversationId);
    console.log('🔍 [DEBUG] - currentSessionForGenerate:', currentSessionForGenerate ? 'exists' : 'null');
    
    if (conversationId && !currentSessionForGenerate) {
      console.log('🔍 [DEBUG] 세션이 없어서 새로 생성합니다...');
      
      // 새 세션 생성 (하이브리드)
      const theme = extractTheme(prompt);
      console.log('🔍 [DEBUG] 추출된 테마:', theme);
      
      try {
        const newSession = await createSessionHybrid(conversationId, theme, prompt);
        console.log('🎨 ImageGenerator - 새 이미지 세션 생성 (하이브리드):', {
          conversationId,
          theme,
          prompt,
          새세션ID: newSession.conversationId
        });
      } catch (error) {
        console.error('❌ 세션 생성 실패, 기존 방식으로 폴백:', error);
        const newSession = createSession(conversationId, theme, prompt);
        console.log('🔄 폴백: 기존 방식 세션 생성 완료:', newSession.conversationId);
      }
      
      // 생성 후 즉시 확인
      const verifySession = getSession(conversationId);
      console.log('🔍 [DEBUG] 세션 생성 후 즉시 확인:', verifySession ? {
        id: verifySession.conversationId,
        theme: verifySession.theme,
        versionsCount: verifySession.versions.length
      } : 'null');
    } else if (conversationId && currentSessionForGenerate) {
      console.log('🔄 ImageGenerator - 기존 이미지 세션 사용:', {
        conversationId,
        기존버전수: currentSessionForGenerate.versions.length,
        선택된버전: currentSessionForGenerate.selectedVersionId
      });
    }
    
    // 🎨 글로벌 이미지 생성 상태 시작
    const jobId = `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    if (artifactId) {
      console.log('🎨 글로벌 이미지 생성 시작:', { jobId, artifactId, prompt });
      startGeneration(jobId, artifactId, prompt, selectedStyle, selectedSize);
    }
    
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
        const apiJobId = result.job_id;
        await pollJobStatus(apiJobId);
      } else if (result.status === 'completed' && result.images.length > 0) {
        const imageUrl = result.images[0];
        
        // 🎨 글로벌 상태 완료 처리
        if (artifactId) {
          completeGeneration(jobId, imageUrl);
        }
        
        await handleImageGenerated(imageUrl);
      } else {
        throw new Error('이미지 생성에 실패했습니다.');
      }
    } catch (error) {
      console.error('Image generation failed:', error);
      
      // 🎨 글로벌 상태 실패 처리
      if (artifactId) {
        failGeneration(jobId, error instanceof Error ? error.message : '이미지 생성 실패');
      }
      
      // 진화형 세션에서 실패 처리
      const currentSessionForError = conversationId ? getSession(conversationId) : null;
      if (conversationId && currentSessionForError) {
        // 실패한 버전을 세션에 추가 (디버깅용)
        addVersion(conversationId, {
          prompt,
          negativePrompt,
          style: selectedStyle,
          size: selectedSize,
          imageUrl: '',
          status: 'failed',
        });
      }
      
      if (isCanvas) {
        props.onUpdate({
          content: {
            ...props.item.content,
            status: 'error',
            error: '이미지 생성에 실패했습니다. 다시 시도해주세요.'
          }
        });
      }
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
    <div className="flex flex-col h-full bg-slate-50 dark:bg-slate-900 p-4 gap-3">
      {/* 상단 이미지 미리보기 영역 - 나머지 높이를 동적으로 차지 */}
      <div className="flex-1 min-h-0 bg-white dark:bg-slate-800 rounded-xl shadow-lg overflow-hidden">
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
      
      {/* 중간 버전 히스토리 영역 - 고정 높이 */}
      {(() => {
        // Canvas Store에서 해당 대화의 이미지 Canvas 확인
        const canvasItems = useCanvasStore.getState().items.filter(item => 
          item.type === 'image' && 
          (item.content as any)?.conversationId === conversationId
        );
        const hasCanvasImages = canvasItems.length > 0;
        const hasSessionVersions = session && session.versions.length > 0;
        
        console.log('🎨 ImageGenerator - 히스토리 표시 조건 확인:', {
          conversationId,
          hasSessionVersions,
          hasCanvasImages,
          sessionVersionsCount: session?.versions.length || 0,
          canvasImagesCount: canvasItems.length,
          shouldShow: conversationId && (hasSessionVersions || hasCanvasImages)
        });
        
        return conversationId && (hasSessionVersions || hasCanvasImages);
      })() && (
        <div className="h-32 bg-white dark:bg-slate-800 rounded-xl shadow-lg p-3">
          <ImageVersionGallery
            conversationId={conversationId}
            compact={true}
            onVersionSelect={(versionId) => {
              selectVersion(conversationId, versionId);
              const selectedVer = session.versions.find(v => v.id === versionId);
              if (selectedVer) {
                setPrompt(selectedVer.prompt);
                setNegativePrompt(selectedVer.negativePrompt);
                setSelectedStyle(selectedVer.style);
                setSelectedSize(selectedVer.size);
                
                // Canvas 아이템도 업데이트 (Canvas 모드인 경우)
                if (isCanvas) {
                  props.onUpdate({
                    content: {
                      ...props.item.content,
                      prompt: selectedVer.prompt,
                      negativePrompt: selectedVer.negativePrompt,
                      style: selectedVer.style,
                      size: selectedVer.size,
                      imageUrl: selectedVer.imageUrl,
                      status: selectedVer.status,
                    }
                  });
                }
              }
            }}
            onVersionDelete={async (versionId) => {
              try {
                // 하이브리드 삭제 (DB + 메모리)
                await deleteVersionHybrid(conversationId, versionId);
                
                // 삭제 후 선택된 버전이 변경되었으면 UI 업데이트
                const newSelectedVersion = getSelectedVersion(conversationId);
                if (newSelectedVersion) {
                  setPrompt(newSelectedVersion.prompt);
                  setNegativePrompt(newSelectedVersion.negativePrompt);
                  setSelectedStyle(newSelectedVersion.style);
                  setSelectedSize(newSelectedVersion.size);
                }
                
                console.log('✅ 이미지 버전 삭제 완료 (하이브리드):', versionId);
                
                // 🔄 전체 컴포넌트 리렌더링 트리거 (인라인 링크 상태 동기화)
                // 이는 상위 컴포넌트에서 메시지 목록을 다시 렌더링하게 하여
                // ChatMessage의 isInlineLinkDisabled가 새로운 삭제 상태를 반영하도록 합니다.
                window.dispatchEvent(new CustomEvent('imageVersionDeleted', {
                  detail: { conversationId, deletedVersionId: versionId }
                }));
                
              } catch (error) {
                console.error('❌ 이미지 버전 삭제 실패:', error);
              }
            }}
            onDeleteAll={() => {
              deleteAllVersions(conversationId);
              // 모든 이미지 삭제 후 기본값으로 리셋
              setPrompt('');
              setNegativePrompt('');
              setSelectedStyle('realistic');
              setSelectedSize('1K_1:1');
              
              if (isCanvas) {
                props.onUpdate({
                  content: {
                    ...props.item.content,
                    prompt: '',
                    negativePrompt: '',
                    style: 'realistic',
                    size: '1K_1:1',
                    imageUrl: '',
                    status: 'idle',
                  }
                });
              }
            }}
          />
        </div>
      )}
      
      {/* 하단 설정 패널 - 고정 높이 */}
      <div className="h-48 bg-white dark:bg-slate-800 rounded-xl shadow-lg flex flex-col">
        {/* 설정 헤더 */}
        <div className="border-b border-slate-200 dark:border-slate-700 p-3">
          <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
            이미지 생성 설정
          </h3>
        </div>
        
        {/* 설정 폼 */}
        <div className="flex-1 p-3">
          <div className="grid grid-cols-3 gap-3 h-full">
            {/* 프롬프트 영역 (상하 배치) */}
            <div className="col-span-2 flex flex-col gap-2">
              {/* 프롬프트 입력 */}
              <div className="flex-1">
                <label className="block text-xs font-medium text-slate-900 dark:text-slate-200 mb-1">
                  프롬프트
                </label>
                <div className="relative h-10">
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="생성하고 싶은 이미지를 자세히 설명해주세요..."
                    className="w-full h-full px-2 py-1.5 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all resize-none text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-500 dark:placeholder:text-slate-400"
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
                  className="w-full h-10 px-2 py-1.5 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all resize-none text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-500 dark:placeholder:text-slate-400"
                  disabled={isGenerating}
                />
              </div>
            </div>
            
            {/* 설정 및 버튼 */}
            <div className="col-span-1 flex flex-col gap-1.5">
              {/* 스타일 선택 */}
              <div>
                <label className="block text-xs font-medium text-slate-900 dark:text-slate-200 mb-1">
                  스타일
                </label>
                <select
                  value={selectedStyle}
                  onChange={(e) => setSelectedStyle(e.target.value)}
                  disabled={isGenerating}
                  className="w-full px-2 py-1.5 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-xs text-slate-900 dark:text-slate-100"
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
                  className="w-full px-2 py-1.5 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all text-xs text-slate-900 dark:text-slate-100"
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
                  px-3 py-2 rounded-lg font-medium transition-all flex items-center justify-center gap-1.5 text-xs mt-1
                  ${isGenerating
                    ? 'bg-slate-300 dark:bg-slate-700 text-slate-500 cursor-not-allowed'
                    : 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600'
                  }
                `}
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span>생성 중</span>
                  </>
                ) : (
                  <>
                    <Wand2 className="w-3 h-3" />
                    <span>이미지 생성</span>
                  </>
                )}
              </button>
              
              {/* 다운로드 버튼 */}
              {(isCanvas && props.item.content.imageUrl) && (
                <button
                  onClick={handleDownload}
                  className="w-full px-3 py-1.5 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors flex items-center justify-center gap-1.5 text-xs"
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