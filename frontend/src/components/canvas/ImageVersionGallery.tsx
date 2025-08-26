/**
 * 이미지 버전 갤러리 컴포넌트 (v2.0)
 * Canvas-ImageSession 통합 시스템 지원
 * 썸네일 그리드로 버전 히스토리를 표시하고 선택/삭제 기능 제공
 */

import React, { useState } from 'react';
import type { ImageVersion } from '../../types/imageSession';
import { useCanvasStore } from '../../stores/canvasStore';
import { useImageSessionStore } from '../../stores/imageSessionStore';

interface ImageVersionGalleryProps {
  conversationId: string;
  versions?: ImageVersion[]; // 옵션으로 변경 (Canvas 컨텐츠에서 추출 가능)
  selectedVersionId?: string; // 옵션으로 변경
  compact?: boolean; // 간단한 모드 (기본 false)
}

const ImageVersionGallery: React.FC<ImageVersionGalleryProps> = ({
  conversationId,
  versions: propVersions,
  selectedVersionId: propSelectedVersionId,
  compact = false,
}) => {
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  
  // Store에서 데이터 가져오기 (props 우선)
  const canvasStore = useCanvasStore();
  const imageSessionStore = useImageSessionStore();
  
  // Canvas 또는 ImageSession에서 데이터 추출
  const session = imageSessionStore.getSession(conversationId);
  
  // ImageSession이 없지만 Canvas에 이미지가 있는 경우 자동으로 세션 생성
  React.useEffect(() => {
    if (!session && conversationId) {
      // Canvas Store에서 해당 대화의 이미지 Canvas 찾기
      const canvasItems = canvasStore.items.filter(item => 
        item.type === 'image' && 
        (item.content as any)?.conversationId === conversationId
      );
      
      if (canvasItems.length > 0) {
        console.log('🔄 ImageVersionGallery - Canvas 데이터 기반 ImageSession 자동 생성:', conversationId);
        
        // Canvas에서 첫 번째 이미지의 정보로 세션 생성
        const firstCanvas = canvasItems[0];
        const imageContent = firstCanvas.content as any;
        
        const theme = imageContent.style || '이미지 생성';
        const basePrompt = imageContent.prompt || '사용자 요청';
        
        // 임시 세션 생성 (비동기이므로 즉시 반영되지는 않음)
        imageSessionStore.createSession(conversationId, theme, basePrompt);
        
        // Canvas의 각 이미지를 버전으로 추가
        canvasItems.forEach((canvas, index) => {
          const content = canvas.content as any;
          imageSessionStore.addVersion(conversationId, {
            prompt: content.prompt || '이미지 생성',
            negativePrompt: content.negativePrompt || '',
            style: content.style || 'realistic',
            size: content.size || '1K_1:1',
            imageUrl: content.imageUrl || '',
            status: content.status === 'completed' ? 'completed' : 'generating',
            isSelected: index === 0 // 첫 번째를 기본 선택
          });
        });
      }
    }
  }, [conversationId, session, canvasStore.items, imageSessionStore]);
  
  const versions = propVersions || session?.versions || [];
  const selectedVersionId = propSelectedVersionId || session?.selectedVersionId || '';
  
  // Canvas Store에서도 이미지 정보 확인 (실시간 반영용)
  const canvasItems = canvasStore.items.filter(item => 
    item.type === 'image' && 
    (item.content as any)?.conversationId === conversationId
  );
  
  console.log('🆼 ImageVersionGallery - 데이터 상태:', {
    conversationId,
    versionsCount: versions.length,
    canvasItemsCount: canvasItems.length,
    selectedVersionId,
    hasSession: !!session,
    canvasImages: canvasItems.map(item => ({
      id: item.id,
      hasImage: !!(item.content as any)?.imageUrl
    }))
  });

  // 버전 번호 순으로 정렬
  const sortedVersions = [...versions].sort((a, b) => a.versionNumber - b.versionNumber);

  // 버전 선택 핸들러
  const handleVersionSelect = (versionId: string) => {
    console.log('🎯 ImageVersionGallery - 버전 선택:', { conversationId, versionId });
    
    // Canvas Store를 통해 선택 (자동으로 ImageSession도 동기화)
    canvasStore.selectVersionInCanvas(conversationId, versionId);
  };
  
  const handleDeleteClick = (versionId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // 버전 선택 방지
    setDeleteTargetId(versionId);
    setDeleteConfirmOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTargetId) return;
    
    console.log('🗑️ ImageVersionGallery - 버전 삭제:', { conversationId, versionId: deleteTargetId });
    
    try {
      // ImageSession Store의 하이브리드 메서드 사용 (DB + 메모리 동시 삭제)
      await imageSessionStore.deleteVersionHybrid(conversationId, deleteTargetId);
      
      // Canvas 자동 동기화
      canvasStore.syncCanvasWithImageSession(conversationId);
      
      console.log('✅ ImageVersionGallery - 버전 삭제 완료');
    } catch (error) {
      console.error('❌ ImageVersionGallery - 버전 삭제 실패:', error);
      alert('이미지 삭제에 실패했습니다. 다시 시도해 주세요.');
    }
    
    setDeleteConfirmOpen(false);
    setDeleteTargetId(null);
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmOpen(false);
    setDeleteTargetId(null);
  };

  const handleDeleteAllClick = async () => {
    if (versions.length === 0) return;
    
    const confirmMessage = `모든 이미지를 삭제하시겠습니까? (총 ${versions.length}개 이미지)`;
    if (!window.confirm(confirmMessage)) return;
    
    console.log('🗑️ ImageVersionGallery - 전체 버전 삭제:', conversationId);
    
    try {
      // 모든 버전 순차 삭제
      for (const version of versions) {
        await imageSessionStore.deleteVersionHybrid(conversationId, version.id);
      }
      
      // Canvas 자동 동기화
      canvasStore.syncCanvasWithImageSession(conversationId);
      
      console.log('✅ ImageVersionGallery - 전체 버전 삭제 완료');
    } catch (error) {
      console.error('❌ ImageVersionGallery - 전체 버전 삭제 실패:', error);
      alert('이미지 삭제에 실패했습니다. 다시 시도해 주세요.');
    }
  };

  if (versions.length === 0) {
    return (
      <div className="mt-4 p-6 border-2 border-dashed border-gray-300 rounded-lg text-center">
        <div className="text-gray-500 text-sm">
          아직 생성된 이미지가 없습니다.
          <br />
          채팅에서 이미지를 요청하면 여기에 표시됩니다.
        </div>
      </div>
    );
  }

  return (
    <div className="mt-4">
      {/* 헤더 */}
      <div className="flex justify-between items-center mb-3">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
          버전 히스토리 ({versions.length}개)
        </h4>
        <button
          onClick={handleDeleteAllClick}
          className="text-xs text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 
                   hover:bg-red-50 dark:hover:bg-red-900/20 px-2 py-1 rounded transition-colors"
          title="모든 이미지 삭제"
        >
          전체 삭제
        </button>
      </div>

      {/* 썸네일 그리드 - compact 모드 지원 */}
      <div className={`grid gap-2 ${
        compact 
          ? 'grid-cols-4' // compact 모드: 4열
          : 'grid-cols-6' // 기본 모드: 6열
      }`}>
        {sortedVersions.map((version) => (
          <div
            key={version.id}
            className={`
              relative group cursor-pointer rounded-lg overflow-hidden border-2 transition-all
              ${version.id === selectedVersionId 
                ? 'border-blue-500 shadow-lg transform scale-105' 
                : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
              }
            `}
            onClick={() => handleVersionSelect(version.id)}
            title={`그림 ${version.versionNumber}: ${version.prompt}`}
          >
            {/* 썸네일 이미지 - 1/4 크기 */}
            <div className="aspect-square bg-gray-100 dark:bg-gray-800 flex items-center justify-center h-16 w-16">
              {version.status === 'generating' ? (
                <div className="flex flex-col items-center justify-center p-1">
                  <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-500 mb-1" />
                  <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
                    생성 중
                  </div>
                </div>
              ) : version.status === 'failed' ? (
                <div className="flex flex-col items-center justify-center p-1 text-red-500">
                  <div className="text-sm mb-1">⚠️</div>
                  <div className="text-xs text-center">실패</div>
                </div>
              ) : version.imageUrl ? (
                <img
                  src={version.imageUrl}
                  alt={`그림 ${version.versionNumber}`}
                  className="w-full h-full object-cover rounded"
                  onError={(e) => {
                    console.error('이미지 로딩 실패:', version.imageUrl);
                    (e.target as HTMLImageElement).src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzlDQTNBRiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPuydtOuvuOyngCDsl5Drk6A8L3RleHQ+PC9zdmc+';
                  }}
                />
              ) : (
                <div className="flex flex-col items-center justify-center p-1 text-gray-400">
                  <div className="text-sm mb-1">🖼️</div>
                  <div className="text-xs text-center">없음</div>
                </div>
              )}
            </div>

            {/* 버전 라벨 */}
            <div className={`
              absolute top-1 left-1 px-1 py-0.5 rounded text-xs font-medium
              ${version.id === selectedVersionId
                ? 'bg-blue-500 text-white shadow-md'
                : 'bg-black/60 text-white'
              }
            `}>
              {version.versionNumber}
            </div>

            {/* 삭제 버튼 */}
            <button
              onClick={(e) => handleDeleteClick(version.id, e)}
              className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity
                       bg-red-500 hover:bg-red-600 text-white rounded-full w-4 h-4 flex items-center justify-center text-xs"
              title="이 버전 삭제"
            >
              ×
            </button>

            {/* 선택된 아이템 표시 */}
            {version.id === selectedVersionId && (
              <div className="absolute bottom-1 right-1">
                <div className="bg-blue-500 text-white rounded-full w-3 h-3 flex items-center justify-center">
                  <div className="text-xs">✓</div>
                </div>
              </div>
            )}

            {/* 로딩 오버레이 */}
            {version.status === 'generating' && (
              <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
                <div className="bg-white/90 rounded-full p-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500" />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 삭제 확인 모달 */}
      {deleteConfirmOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={handleDeleteCancel}>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-sm mx-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
              이미지 삭제 확인
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
              선택한 이미지를 삭제하시겠습니까?
              <br />
              이 작업은 되돌릴 수 없습니다.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={handleDeleteCancel}
                className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200
                         border border-gray-300 dark:border-gray-600 rounded-md hover:border-gray-400 dark:hover:border-gray-500 transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="px-4 py-2 text-sm text-white bg-red-500 hover:bg-red-600 rounded-md transition-colors"
              >
                삭제
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 갤러리 사용 팁 - 간소화 */}
      {versions.length > 0 && (
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          💡 클릭하여 해당 버전 설정을 불러올 수 있습니다.
        </div>
      )}
    </div>
  );
};

export default ImageVersionGallery;