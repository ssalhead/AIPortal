/**
 * 시리즈 내보내기 모달 컴포넌트
 * 
 * 완성된 이미지 시리즈를 다양한 형태로 내보내는 고급 인터페이스
 * - 개별 이미지 다운로드
 * - ZIP 파일 일괄 다운로드
 * - PDF 형태 내보내기
 * - 소셜 미디어 최적화 형태
 * - 웹 갤러리 공유
 */

import React, { useState, useEffect } from 'react';
import {
  X,
  Download,
  FileArchive,
  FileText,
  Share2,
  Image as ImageIcon,
  Grid3X3,
  Layers,
  Settings,
  Check,
  Copy,
  ExternalLink,
  Instagram,
  Twitter,
  Facebook,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';

import { ImageSeries, SeriesImage, SERIES_TYPE_CONFIGS } from '../../types/imageSeries';

interface SeriesExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  series: ImageSeries;
  images: SeriesImage[];
}

interface ExportFormat {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  requirements: string[];
  options: ExportOption[];
}

interface ExportOption {
  id: string;
  name: string;
  description: string;
  type: 'boolean' | 'select' | 'number' | 'text';
  defaultValue: any;
  options?: { value: any; label: string }[];
  min?: number;
  max?: number;
}

const SeriesExportModal: React.FC<SeriesExportModalProps> = ({
  isOpen,
  onClose,
  series,
  images
}) => {
  const [selectedFormat, setSelectedFormat] = useState<string>('individual');
  const [exportOptions, setExportOptions] = useState<Record<string, any>>({});
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [exportStatus, setExportStatus] = useState<'idle' | 'exporting' | 'completed' | 'error'>('idle');
  const [shareUrl, setShareUrl] = useState<string | null>(null);

  // 내보내기 형식 정의
  const exportFormats: ExportFormat[] = [
    {
      id: 'individual',
      name: '개별 이미지',
      description: '각 이미지를 개별 파일로 다운로드',
      icon: <ImageIcon className="w-5 h-5" />,
      requirements: ['완성된 이미지가 1개 이상 필요'],
      options: [
        {
          id: 'format',
          name: '파일 형식',
          description: '저장할 파일 형식',
          type: 'select',
          defaultValue: 'png',
          options: [
            { value: 'png', label: 'PNG (고품질)' },
            { value: 'jpg', label: 'JPG (압축)' },
            { value: 'webp', label: 'WebP (최적화)' }
          ]
        },
        {
          id: 'quality',
          name: '품질',
          description: 'JPG/WebP 압축 품질 (1-100)',
          type: 'number',
          defaultValue: 90,
          min: 1,
          max: 100
        },
        {
          id: 'includeIndex',
          name: '순서 번호 포함',
          description: '파일명에 시리즈 순서 번호 포함',
          type: 'boolean',
          defaultValue: true
        }
      ]
    },
    {
      id: 'zip',
      name: 'ZIP 아카이브',
      description: '모든 이미지를 ZIP 파일로 압축',
      icon: <FileArchive className="w-5 h-5" />,
      requirements: ['완성된 이미지가 1개 이상 필요'],
      options: [
        {
          id: 'format',
          name: '파일 형식',
          description: '저장할 파일 형식',
          type: 'select',
          defaultValue: 'png',
          options: [
            { value: 'png', label: 'PNG (고품질)' },
            { value: 'jpg', label: 'JPG (압축)' },
            { value: 'webp', label: 'WebP (최적화)' }
          ]
        },
        {
          id: 'includeMetadata',
          name: '메타데이터 포함',
          description: '프롬프트와 설정 정보를 텍스트 파일로 포함',
          type: 'boolean',
          defaultValue: true
        },
        {
          id: 'folderStructure',
          name: '폴더 구조',
          description: 'ZIP 내부 폴더 구조',
          type: 'select',
          defaultValue: 'flat',
          options: [
            { value: 'flat', label: '단일 폴더' },
            { value: 'numbered', label: '번호별 폴더' },
            { value: 'named', label: '이름별 폴더' }
          ]
        }
      ]
    },
    {
      id: 'pdf',
      name: 'PDF 문서',
      description: '이미지들을 PDF 문서로 결합',
      icon: <FileText className="w-5 h-5" />,
      requirements: ['완성된 이미지가 1개 이상 필요'],
      options: [
        {
          id: 'layout',
          name: '레이아웃',
          description: 'PDF 페이지 레이아웃',
          type: 'select',
          defaultValue: 'one-per-page',
          options: [
            { value: 'one-per-page', label: '페이지당 1개 이미지' },
            { value: 'two-per-page', label: '페이지당 2개 이미지' },
            { value: 'four-per-page', label: '페이지당 4개 이미지' },
            { value: 'grid', label: '그리드 레이아웃' }
          ]
        },
        {
          id: 'pageSize',
          name: '페이지 크기',
          description: 'PDF 페이지 크기',
          type: 'select',
          defaultValue: 'A4',
          options: [
            { value: 'A4', label: 'A4' },
            { value: 'A3', label: 'A3' },
            { value: 'Letter', label: 'Letter' },
            { value: 'Legal', label: 'Legal' }
          ]
        },
        {
          id: 'includeInfo',
          name: '정보 페이지 포함',
          description: '시리즈 정보와 프롬프트를 별도 페이지로 추가',
          type: 'boolean',
          defaultValue: true
        }
      ]
    },
    {
      id: 'social',
      name: '소셜 미디어',
      description: '소셜 미디어 플랫폼에 최적화된 형태',
      icon: <Share2 className="w-5 h-5" />,
      requirements: ['완성된 이미지가 1개 이상 필요'],
      options: [
        {
          id: 'platform',
          name: '플랫폼',
          description: '최적화할 소셜 미디어 플랫폼',
          type: 'select',
          defaultValue: 'instagram',
          options: [
            { value: 'instagram', label: 'Instagram (1080x1080)' },
            { value: 'twitter', label: 'Twitter (1200x675)' },
            { value: 'facebook', label: 'Facebook (1200x630)' },
            { value: 'linkedin', label: 'LinkedIn (1200x627)' }
          ]
        },
        {
          id: 'collage',
          name: '콜라주 만들기',
          description: '여러 이미지를 하나의 콜라주로 결합',
          type: 'boolean',
          defaultValue: false
        },
        {
          id: 'watermark',
          name: '워터마크 추가',
          description: '시리즈 제목을 워터마크로 추가',
          type: 'boolean',
          defaultValue: false
        }
      ]
    },
    {
      id: 'web',
      name: '웹 갤러리',
      description: '온라인으로 공유 가능한 웹 갤러리 생성',
      icon: <Grid3X3 className="w-5 h-5" />,
      requirements: ['완성된 이미지가 1개 이상 필요'],
      options: [
        {
          id: 'theme',
          name: '테마',
          description: '웹 갤러리 테마',
          type: 'select',
          defaultValue: 'minimal',
          options: [
            { value: 'minimal', label: '미니멀' },
            { value: 'grid', label: '그리드' },
            { value: 'carousel', label: '캐러셀' },
            { value: 'masonry', label: '메이슨리' }
          ]
        },
        {
          id: 'privacy',
          name: '공개 범위',
          description: '갤러리 접근 권한',
          type: 'select',
          defaultValue: 'private',
          options: [
            { value: 'public', label: '공개 (누구나 접근 가능)' },
            { value: 'unlisted', label: '비공개 (링크로만 접근)' },
            { value: 'private', label: '개인 전용' }
          ]
        },
        {
          id: 'allowDownload',
          name: '다운로드 허용',
          description: '방문자가 이미지를 다운로드할 수 있도록 허용',
          type: 'boolean',
          defaultValue: false
        }
      ]
    }
  ];

  // 선택된 형식의 기본 옵션 설정
  useEffect(() => {
    const format = exportFormats.find(f => f.id === selectedFormat);
    if (format) {
      const defaultOptions: Record<string, any> = {};
      format.options.forEach(option => {
        defaultOptions[option.id] = option.defaultValue;
      });
      setExportOptions(defaultOptions);
    }
  }, [selectedFormat]);

  // 모달 리셋
  useEffect(() => {
    if (isOpen) {
      setSelectedFormat('individual');
      setExportStatus('idle');
      setExportProgress(0);
      setShareUrl(null);
    }
  }, [isOpen]);

  // 내보내기 실행
  const handleExport = async () => {
    setIsExporting(true);
    setExportStatus('exporting');
    setExportProgress(0);

    try {
      // 진행률 시뮬레이션
      const progressInterval = setInterval(() => {
        setExportProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      // 실제 내보내기 로직 (각 형식별로 다르게 구현)
      await performExport(selectedFormat, exportOptions);

      clearInterval(progressInterval);
      setExportProgress(100);
      setExportStatus('completed');

      // 웹 갤러리인 경우 공유 URL 생성
      if (selectedFormat === 'web') {
        const url = generateShareUrl(series.id);
        setShareUrl(url);
      }

    } catch (error) {
      console.error('Export failed:', error);
      setExportStatus('error');
    } finally {
      setIsExporting(false);
    }
  };

  // 실제 내보내기 로직
  const performExport = async (format: string, options: Record<string, any>) => {
    const completedImages = images.filter(img => img.status === 'completed');

    switch (format) {
      case 'individual':
        await exportIndividualImages(completedImages, options);
        break;
      case 'zip':
        await exportAsZip(completedImages, options);
        break;
      case 'pdf':
        await exportAsPDF(completedImages, options);
        break;
      case 'social':
        await exportForSocial(completedImages, options);
        break;
      case 'web':
        await createWebGallery(completedImages, options);
        break;
      default:
        throw new Error('Unknown export format');
    }
  };

  // 개별 이미지 내보내기
  const exportIndividualImages = async (imgs: SeriesImage[], options: Record<string, any>) => {
    for (const image of imgs) {
      const filename = options.includeIndex 
        ? `${series.title}-${String(image.series_index).padStart(2, '0')}`
        : `${series.title}-${image.id.substring(0, 8)}`;
      
      await downloadImage(image.image_url, `${filename}.${options.format}`);
      await new Promise(resolve => setTimeout(resolve, 500)); // 다운로드 간 딜레이
    }
  };

  // ZIP 아카이브 내보내기
  const exportAsZip = async (imgs: SeriesImage[], options: Record<string, any>) => {
    // TODO: JSZip 라이브러리를 사용하여 ZIP 파일 생성
    console.log('Exporting as ZIP:', imgs, options);
    
    // 임시 구현 - 실제로는 ZIP 라이브러리 사용
    const zipFilename = `${series.title}.zip`;
    
    // 메타데이터 파일 생성 (옵션이 활성화된 경우)
    if (options.includeMetadata) {
      const metadata = generateMetadataFile();
      console.log('Including metadata:', metadata);
    }
  };

  // PDF 내보내기
  const exportAsPDF = async (imgs: SeriesImage[], options: Record<string, any>) => {
    // TODO: jsPDF 라이브러리를 사용하여 PDF 생성
    console.log('Exporting as PDF:', imgs, options);
    
    const pdfFilename = `${series.title}.pdf`;
    // PDF 생성 로직 구현
  };

  // 소셜 미디어 최적화 내보내기
  const exportForSocial = async (imgs: SeriesImage[], options: Record<string, any>) => {
    console.log('Exporting for social media:', imgs, options);
    
    // 플랫폼별 최적화 크기로 리사이즈
    // 콜라주 생성 (옵션이 활성화된 경우)
    // 워터마크 추가 (옵션이 활성화된 경우)
  };

  // 웹 갤러리 생성
  const createWebGallery = async (imgs: SeriesImage[], options: Record<string, any>) => {
    console.log('Creating web gallery:', imgs, options);
    
    // 웹 갤러리 생성 및 업로드
    // 공유 URL 반환
  };

  // 이미지 다운로드 헬퍼
  const downloadImage = async (url: string, filename: string) => {
    const response = await fetch(url);
    const blob = await response.blob();
    
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    
    URL.revokeObjectURL(a.href);
  };

  // 메타데이터 파일 생성
  const generateMetadataFile = () => {
    const metadata = {
      series: {
        title: series.title,
        type: series.series_type,
        created_at: series.created_at,
        total_images: series.target_count,
        completed_images: series.current_count
      },
      images: images.map(img => ({
        index: img.series_index,
        prompt: img.prompt,
        status: img.status,
        created_at: img.created_at
      }))
    };
    
    return JSON.stringify(metadata, null, 2);
  };

  // 공유 URL 생성
  const generateShareUrl = (seriesId: string) => {
    return `${window.location.origin}/gallery/${seriesId}`;
  };

  // URL 복사
  const handleCopyUrl = async () => {
    if (shareUrl) {
      try {
        await navigator.clipboard.writeText(shareUrl);
        alert('URL이 클립보드에 복사되었습니다.');
      } catch (error) {
        console.error('Failed to copy URL:', error);
      }
    }
  };

  // 옵션 변경
  const handleOptionChange = (optionId: string, value: any) => {
    setExportOptions(prev => ({
      ...prev,
      [optionId]: value
    }));
  };

  if (!isOpen) return null;

  const selectedFormatConfig = exportFormats.find(f => f.id === selectedFormat)!;
  const completedImages = images.filter(img => img.status === 'completed');
  const canExport = completedImages.length > 0 && !isExporting;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg">
              <Download className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                시리즈 내보내기
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {series.title} • {completedImages.length}개 이미지
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* 콘텐츠 */}
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 내보내기 형식 선택 */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                내보내기 형식
              </h2>
              <div className="space-y-3">
                {exportFormats.map(format => (
                  <button
                    key={format.id}
                    onClick={() => setSelectedFormat(format.id)}
                    disabled={isExporting}
                    className={`
                      w-full p-4 text-left rounded-lg border-2 transition-all
                      ${selectedFormat === format.id
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      }
                      ${isExporting ? 'opacity-50 cursor-not-allowed' : ''}
                    `}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      {format.icon}
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                        {format.name}
                      </h3>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                      {format.description}
                    </p>
                    <div className="text-xs text-gray-500 dark:text-gray-500">
                      {format.requirements.join(', ')}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* 내보내기 옵션 */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                내보내기 옵션
              </h2>
              <div className="space-y-4">
                {selectedFormatConfig.options.map(option => (
                  <div key={option.id}>
                    <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
                      {option.name}
                    </label>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                      {option.description}
                    </p>
                    
                    {option.type === 'boolean' ? (
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={exportOptions[option.id] || false}
                          onChange={(e) => handleOptionChange(option.id, e.target.checked)}
                          disabled={isExporting}
                          className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">
                          활성화
                        </span>
                      </label>
                    ) : option.type === 'select' ? (
                      <select
                        value={exportOptions[option.id] || option.defaultValue}
                        onChange={(e) => handleOptionChange(option.id, e.target.value)}
                        disabled={isExporting}
                        className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      >
                        {option.options?.map(opt => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : option.type === 'number' ? (
                      <input
                        type="number"
                        value={exportOptions[option.id] || option.defaultValue}
                        onChange={(e) => handleOptionChange(option.id, parseInt(e.target.value))}
                        disabled={isExporting}
                        min={option.min}
                        max={option.max}
                        className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      />
                    ) : (
                      <input
                        type="text"
                        value={exportOptions[option.id] || option.defaultValue}
                        onChange={(e) => handleOptionChange(option.id, e.target.value)}
                        disabled={isExporting}
                        className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 진행률 및 상태 */}
          {exportStatus !== 'idle' && (
            <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="flex items-center gap-3 mb-3">
                {exportStatus === 'exporting' && (
                  <>
                    <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                    <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      내보내기 진행 중... ({exportProgress}%)
                    </span>
                  </>
                )}
                {exportStatus === 'completed' && (
                  <>
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="text-sm font-medium text-green-700 dark:text-green-400">
                      내보내기 완료!
                    </span>
                  </>
                )}
                {exportStatus === 'error' && (
                  <>
                    <AlertCircle className="w-5 h-5 text-red-500" />
                    <span className="text-sm font-medium text-red-700 dark:text-red-400">
                      내보내기 실패
                    </span>
                  </>
                )}
              </div>

              {exportStatus === 'exporting' && (
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${exportProgress}%` }}
                  />
                </div>
              )}

              {exportStatus === 'completed' && shareUrl && (
                <div className="mt-3">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    공유 URL:
                  </p>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={shareUrl}
                      readOnly
                      className="flex-1 px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm"
                    />
                    <button
                      onClick={handleCopyUrl}
                      className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                      title="URL 복사"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                    <a
                      href={shareUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                      title="새 창에서 열기"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 푸터 */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {completedImages.length}개 완성된 이미지 • {selectedFormatConfig.name}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              disabled={isExporting}
              className="px-4 py-2 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              취소
            </button>
            <button
              onClick={handleExport}
              disabled={!canExport}
              className={`
                flex items-center gap-2 px-6 py-2 rounded-lg font-medium transition-colors
                ${canExport
                  ? 'bg-blue-500 text-white hover:bg-blue-600'
                  : 'bg-gray-300 dark:bg-gray-700 text-gray-500 cursor-not-allowed'
                }
              `}
            >
              {isExporting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  내보내는 중...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  내보내기
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SeriesExportModal;