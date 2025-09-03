/**
 * 이미지 시리즈 갤러리 컴포넌트
 * 
 * 연속성 있는 이미지 시리즈를 표시하고 관리하는 고급 갤러리
 * - 시리즈별 그룹화된 표시
 * - 드래그 앤 드롭 재배치
 * - 실시간 생성 진행 상황 표시
 * - 시리즈 템플릿 관리
 */

import React, { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable, DropResult } from 'react-beautiful-dnd';
import {
  Grid3X3,
  Play,
  Pause,
  Download,
  Share2,
  Copy,
  Trash2,
  Settings,
  Plus,
  Eye,
  EyeOff,
  MoreHorizontal,
  RefreshCw,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2
} from 'lucide-react';

import { 
  ImageSeries, 
  SeriesImage, 
  SeriesGenerationProgress, 
  SERIES_TYPE_CONFIGS,
  SeriesType,
  CompletionStatus
} from '../../types/imageSeries';
import { imageSeriesService } from '../../services/imageSeriesService';

interface ImageSeriesGalleryProps {
  conversationId: string;
  className?: string;
}

interface SeriesCardProps {
  series: ImageSeries;
  images: SeriesImage[];
  onRefresh: (seriesId: string) => void;
  onDelete: (seriesId: string) => void;
  onExport: (seriesId: string) => void;
  onShare: (seriesId: string) => void;
}

interface SeriesImageItemProps {
  image: SeriesImage;
  index: number;
  seriesId: string;
  isDragging?: boolean;
  onImageClick: (image: SeriesImage) => void;
}

const SeriesImageItem: React.FC<SeriesImageItemProps> = ({
  image,
  index,
  seriesId,
  isDragging,
  onImageClick
}) => (
  <Draggable draggableId={`${seriesId}-${image.id}`} index={index}>
    {(provided, snapshot) => (
      <div
        ref={provided.innerRef}
        {...provided.draggableProps}
        {...provided.dragHandleProps}
        className={`
          relative group cursor-pointer rounded-lg overflow-hidden border-2 transition-all
          ${snapshot.isDragging ? 'shadow-xl scale-105 z-50' : 'shadow-sm hover:shadow-md'}
          ${image.status === 'generating' ? 'border-blue-400' : 
            image.status === 'failed' ? 'border-red-400' : 'border-gray-200 dark:border-gray-600'}
        `}
        onClick={() => onImageClick(image)}
      >
        {/* 이미지 */}
        <div className="aspect-square bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
          {image.status === 'generating' ? (
            <div className="flex flex-col items-center justify-center p-4">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-2" />
              <div className="text-xs text-gray-500 text-center">생성 중...</div>
            </div>
          ) : image.status === 'failed' ? (
            <div className="flex flex-col items-center justify-center p-4 text-red-500">
              <AlertCircle className="w-8 h-8 mb-2" />
              <div className="text-xs text-center">실패</div>
            </div>
          ) : image.image_url ? (
            <img
              src={image.image_url}
              alt={`Series image ${image.series_index}`}
              className="w-full h-full object-cover"
              onError={(e) => {
                console.error('Image loading failed:', image.image_url);
                (e.target as HTMLImageElement).src = '/placeholder-image.svg';
              }}
            />
          ) : (
            <div className="flex flex-col items-center justify-center p-4 text-gray-400">
              <Grid3X3 className="w-8 h-8 mb-2" />
              <div className="text-xs text-center">대기 중</div>
            </div>
          )}
        </div>

        {/* 시리즈 인덱스 */}
        <div className="absolute top-2 left-2 bg-black bg-opacity-70 text-white px-2 py-1 rounded text-xs font-medium">
          {image.series_index}
        </div>

        {/* 상태 표시 */}
        {image.status === 'completed' && (
          <div className="absolute top-2 right-2 bg-green-500 text-white rounded-full p-1">
            <CheckCircle className="w-3 h-3" />
          </div>
        )}

        {/* 드래그 핸들 */}
        <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="bg-black bg-opacity-70 text-white p-1 rounded">
            <Grid3X3 className="w-3 h-3" />
          </div>
        </div>
      </div>
    )}
  </Draggable>
);

const SeriesCard: React.FC<SeriesCardProps> = ({
  series,
  images,
  onRefresh,
  onDelete,
  onExport,
  onShare
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showActions, setShowActions] = useState(false);

  const typeConfig = SERIES_TYPE_CONFIGS[series.series_type as SeriesType];
  const statusConfig = getStatusConfig(series.completion_status as CompletionStatus);

  const handleReorder = (result: DropResult) => {
    if (!result.destination) return;

    // TODO: 실제 이미지 순서 변경 API 호출
    console.log('Reorder images:', {
      from: result.source.index,
      to: result.destination.index
    });
  };

  const handleImageClick = (image: SeriesImage) => {
    // TODO: 이미지 상세보기 모달 열기
    console.log('Image clicked:', image);
  };

  const handleGenerateNext = async () => {
    setIsGenerating(true);
    try {
      await imageSeriesService.generateSeriesBatch(series.id, 1, (progress) => {
        console.log('Generation progress:', progress);
        if (progress.status === 'completed' || progress.status === 'failed') {
          setIsGenerating(false);
          onRefresh(series.id);
        }
      });
    } catch (error) {
      console.error('Failed to generate next image:', error);
      setIsGenerating(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
      {/* 시리즈 헤더 */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          {/* 시리즈 정보 */}
          <div className="flex items-center gap-3">
            <div className={`p-2 ${typeConfig.color} rounded-lg`}>
              <span className="text-lg">{typeConfig.icon}</span>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-lg">
                {series.title}
              </h3>
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <span>{typeConfig.name}</span>
                <span>•</span>
                <span>{series.current_count}/{series.target_count}</span>
                <span>•</span>
                <div className="flex items-center gap-1">
                  {statusConfig.icon}
                  <span>{statusConfig.label}</span>
                </div>
              </div>
            </div>
          </div>

          {/* 액션 버튼들 */}
          <div className="flex items-center gap-2">
            {/* 진행률 표시 */}
            <div className="flex items-center gap-2">
              <div className="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className={`h-2 ${statusConfig.color} rounded-full transition-all duration-300`}
                  style={{ width: `${series.progress_percentage * 100}%` }}
                />
              </div>
              <span className="text-xs text-gray-500">
                {Math.round(series.progress_percentage * 100)}%
              </span>
            </div>

            {/* 다음 생성 버튼 */}
            {series.completion_status === 'generating' || series.current_count < series.target_count ? (
              <button
                onClick={handleGenerateNext}
                disabled={isGenerating}
                className={`
                  px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                  ${isGenerating 
                    ? 'bg-gray-200 dark:bg-gray-700 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-500 text-white hover:bg-blue-600'
                  }
                `}
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-1" />
                    생성 중
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-1" />
                    계속 생성
                  </>
                )}
              </button>
            ) : null}

            {/* 축소/확장 버튼 */}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              {isExpanded ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>

            {/* 더보기 메뉴 */}
            <div className="relative">
              <button
                onClick={() => setShowActions(!showActions)}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <MoreHorizontal className="w-4 h-4" />
              </button>

              {showActions && (
                <div className="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 z-10 min-w-32">
                  <button
                    onClick={() => { onRefresh(series.id); setShowActions(false); }}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 w-full text-left"
                  >
                    <RefreshCw className="w-4 h-4" />
                    새로고침
                  </button>
                  <button
                    onClick={() => { onExport(series.id); setShowActions(false); }}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 w-full text-left"
                  >
                    <Download className="w-4 h-4" />
                    내보내기
                  </button>
                  <button
                    onClick={() => { onShare(series.id); setShowActions(false); }}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 w-full text-left"
                  >
                    <Share2 className="w-4 h-4" />
                    공유
                  </button>
                  <hr className="my-1 border-gray-200 dark:border-gray-700" />
                  <button
                    onClick={() => { onDelete(series.id); setShowActions(false); }}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 w-full text-left"
                  >
                    <Trash2 className="w-4 h-4" />
                    삭제
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 이미지 그리드 */}
      {isExpanded && (
        <div className="p-4">
          <DragDropContext onDragEnd={handleReorder}>
            <Droppable droppableId={`series-${series.id}`} direction="horizontal">
              {(provided, snapshot) => (
                <div
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                  className={`
                    grid grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3
                    ${snapshot.isDraggingOver ? 'bg-blue-50 dark:bg-blue-900/20' : ''}
                    rounded-lg p-2 transition-colors
                  `}
                >
                  {images.map((image, index) => (
                    <SeriesImageItem
                      key={image.id}
                      image={image}
                      index={index}
                      seriesId={series.id}
                      onImageClick={handleImageClick}
                    />
                  ))}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>

          {/* 시리즈 정보 */}
          {series.description && (
            <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
              {series.description}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const ImageSeriesGallery: React.FC<ImageSeriesGalleryProps> = ({
  conversationId,
  className = ''
}) => {
  const [seriesList, setSeriesList] = useState<ImageSeries[]>([]);
  const [seriesImages, setSeriesImages] = useState<Record<string, SeriesImage[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 시리즈 목록 로드 (임시로 빈 배열)
  useEffect(() => {
    loadSeriesList();
  }, [conversationId]);

  const loadSeriesList = async () => {
    try {
      setLoading(true);
      // TODO: 실제 API 호출로 해당 대화의 시리즈 목록 조회
      // const series = await imageSeriesService.getSeriesByConversation(conversationId);
      const series: ImageSeries[] = []; // 임시로 빈 배열
      setSeriesList(series);

      // 각 시리즈의 이미지들 로드
      const imagesData: Record<string, SeriesImage[]> = {};
      for (const s of series) {
        try {
          const images = await imageSeriesService.getSeriesImages(s.id);
          imagesData[s.id] = images;
        } catch (error) {
          console.error(`Failed to load images for series ${s.id}:`, error);
          imagesData[s.id] = [];
        }
      }
      setSeriesImages(imagesData);
    } catch (error) {
      console.error('Failed to load series list:', error);
      setError('시리즈 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshSeries = async (seriesId: string) => {
    try {
      const [updatedSeries, updatedImages] = await Promise.all([
        imageSeriesService.getSeries(seriesId),
        imageSeriesService.getSeriesImages(seriesId)
      ]);

      setSeriesList(prev => 
        prev.map(s => s.id === seriesId ? updatedSeries : s)
      );
      setSeriesImages(prev => ({
        ...prev,
        [seriesId]: updatedImages
      }));
    } catch (error) {
      console.error('Failed to refresh series:', error);
    }
  };

  const handleDeleteSeries = async (seriesId: string) => {
    if (!confirm('이 시리즈를 삭제하시겠습니까?')) return;

    try {
      await imageSeriesService.deleteSeries(seriesId);
      setSeriesList(prev => prev.filter(s => s.id !== seriesId));
      setSeriesImages(prev => {
        const newImages = { ...prev };
        delete newImages[seriesId];
        return newImages;
      });
    } catch (error) {
      console.error('Failed to delete series:', error);
      alert('시리즈 삭제에 실패했습니다.');
    }
  };

  const handleExportSeries = (seriesId: string) => {
    // TODO: 시리즈 내보내기 구현
    console.log('Export series:', seriesId);
  };

  const handleShareSeries = (seriesId: string) => {
    // TODO: 시리즈 공유 구현
    console.log('Share series:', seriesId);
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">시리즈를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
          <button
            onClick={loadSeriesList}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  if (seriesList.length === 0) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <div className="text-center">
          <Grid3X3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            아직 생성된 시리즈가 없습니다
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            연속성 있는 이미지 시리즈를 만들어보세요
          </p>
          <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2 mx-auto">
            <Plus className="w-4 h-4" />
            시리즈 만들기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {seriesList.map(series => (
        <SeriesCard
          key={series.id}
          series={series}
          images={seriesImages[series.id] || []}
          onRefresh={handleRefreshSeries}
          onDelete={handleDeleteSeries}
          onExport={handleExportSeries}
          onShare={handleShareSeries}
        />
      ))}
    </div>
  );
};

// 상태별 설정
function getStatusConfig(status: CompletionStatus) {
  switch (status) {
    case 'planning':
      return {
        label: '계획 중',
        icon: <Clock className="w-4 h-4" />,
        color: 'bg-gray-400'
      };
    case 'generating':
      return {
        label: '생성 중',
        icon: <Loader2 className="w-4 h-4 animate-spin" />,
        color: 'bg-blue-500'
      };
    case 'completed':
      return {
        label: '완성됨',
        icon: <CheckCircle className="w-4 h-4" />,
        color: 'bg-green-500'
      };
    case 'failed':
      return {
        label: '실패',
        icon: <AlertCircle className="w-4 h-4" />,
        color: 'bg-red-500'
      };
    case 'paused':
      return {
        label: '일시정지',
        icon: <Pause className="w-4 h-4" />,
        color: 'bg-yellow-500'
      };
    default:
      return {
        label: '알 수 없음',
        icon: <AlertCircle className="w-4 h-4" />,
        color: 'bg-gray-400'
      };
  }
}

export default ImageSeriesGallery;