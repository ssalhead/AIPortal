/**
 * Canvas 내보내기 다이얼로그
 * 전문가급 내보내기 옵션을 제공하는 UI 컴포넌트
 */

import React, { useState, useEffect } from 'react';
import {
  Download,
  Settings,
  Cloud,
  Image,
  FileText,
  Package,
  CheckCircle,
  AlertCircle,
  Loader,
  X,
  Monitor,
  Instagram,
  Twitter,
  Linkedin,
  Youtube,
  Facebook,
  Palette
} from 'lucide-react';

// 내보내기 타입 및 옵션 정의
export interface ExportFormat {
  id: 'png' | 'jpeg' | 'svg' | 'pdf' | 'webp';
  name: string;
  icon: React.ReactNode;
  description: string;
  supports_transparency: boolean;
  quality_adjustable: boolean;
}

export interface SocialPreset {
  id: string;
  name: string;
  icon: React.ReactNode;
  dimensions: [number, number];
  recommended_format: string;
}

export interface ExportOptions {
  format: string;
  resolution_multiplier: '1x' | '2x' | '4x';
  transparent_background: boolean;
  compression_level: 'low' | 'medium' | 'high';
  include_watermark: boolean;
  watermark_text?: string;
  watermark_position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';
  social_preset: string;
  custom_width?: number;
  custom_height?: number;
}

export interface ExportProgress {
  export_id: string;
  status: 'pending' | 'processing' | 'uploading' | 'completed' | 'failed';
  progress_percentage: number;
  current_step: string;
  file_size?: number;
  download_url?: string;
  cloud_url?: string;
  error_message?: string;
}

interface CanvasExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  canvasId: string;
  canvasName?: string;
  conversationId?: string;
  isSeriesMode?: boolean;
  canvasIds?: string[];
}

const EXPORT_FORMATS: ExportFormat[] = [
  {
    id: 'png',
    name: 'PNG',
    icon: <Image className="w-5 h-5" />,
    description: '고품질 래스터 이미지 (투명 배경 지원)',
    supports_transparency: true,
    quality_adjustable: false
  },
  {
    id: 'jpeg',
    name: 'JPEG',
    icon: <Image className="w-5 h-5" />,
    description: '압축된 이미지 (작은 파일 크기)',
    supports_transparency: false,
    quality_adjustable: true
  },
  {
    id: 'webp',
    name: 'WebP',
    icon: <Image className="w-5 h-5" />,
    description: '최신 웹 최적화 포맷',
    supports_transparency: true,
    quality_adjustable: true
  },
  {
    id: 'svg',
    name: 'SVG',
    icon: <FileText className="w-5 h-5" />,
    description: '벡터 그래픽 (무손실 확대 가능)',
    supports_transparency: true,
    quality_adjustable: false
  },
  {
    id: 'pdf',
    name: 'PDF',
    icon: <FileText className="w-5 h-5" />,
    description: '문서 형식 (인쇄 최적화)',
    supports_transparency: true,
    quality_adjustable: false
  }
];

const SOCIAL_PRESETS: SocialPreset[] = [
  {
    id: 'instagram_post',
    name: 'Instagram 포스트',
    icon: <Instagram className="w-4 h-4" />,
    dimensions: [1080, 1080],
    recommended_format: 'jpeg'
  },
  {
    id: 'instagram_story',
    name: 'Instagram 스토리',
    icon: <Instagram className="w-4 h-4" />,
    dimensions: [1080, 1920],
    recommended_format: 'jpeg'
  },
  {
    id: 'twitter_post',
    name: 'Twitter 포스트',
    icon: <Twitter className="w-4 h-4" />,
    dimensions: [1200, 675],
    recommended_format: 'webp'
  },
  {
    id: 'facebook_post',
    name: 'Facebook 포스트',
    icon: <Facebook className="w-4 h-4" />,
    dimensions: [1200, 630],
    recommended_format: 'webp'
  },
  {
    id: 'linkedin_post',
    name: 'LinkedIn 포스트',
    icon: <Linkedin className="w-4 h-4" />,
    dimensions: [1200, 627],
    recommended_format: 'webp'
  },
  {
    id: 'youtube_thumbnail',
    name: 'YouTube 썸네일',
    icon: <Youtube className="w-4 h-4" />,
    dimensions: [1280, 720],
    recommended_format: 'webp'
  },
  {
    id: 'custom',
    name: '커스텀 크기',
    icon: <Monitor className="w-4 h-4" />,
    dimensions: [0, 0],
    recommended_format: 'png'
  }
];

export const CanvasExportDialog: React.FC<CanvasExportDialogProps> = ({
  isOpen,
  onClose,
  canvasId,
  canvasName = 'Canvas',
  conversationId,
  isSeriesMode = false,
  canvasIds = []
}) => {
  const [activeTab, setActiveTab] = useState<'basic' | 'advanced' | 'cloud'>('basic');
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    format: 'png',
    resolution_multiplier: '2x',
    transparent_background: true,
    compression_level: 'medium',
    include_watermark: false,
    watermark_text: 'Created with AIPortal',
    watermark_position: 'bottom-right',
    social_preset: 'custom'
  });
  
  const [advancedOptions, setAdvancedOptions] = useState({
    jpeg_quality: 85,
    png_compression: 6,
    webp_quality: 80,
    webp_lossless: false,
    pdf_template: 'gallery',
    pdf_page_size: 'A4',
    pdf_orientation: 'portrait',
    pdf_margin: 20
  });
  
  const [cloudOptions, setCloudOptions] = useState({
    provider: 'none',
    generate_share_link: true,
    share_permissions: 'view',
    folder_path: '/AIPortal Exports'
  });
  
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState<ExportProgress | null>(null);
  const [showProgress, setShowProgress] = useState(false);

  // 선택된 포맷 정보
  const selectedFormat = EXPORT_FORMATS.find(f => f.id === exportOptions.format);
  const selectedPreset = SOCIAL_PRESETS.find(p => p.id === exportOptions.social_preset);

  // 포맷 변경 시 권장 설정 적용
  useEffect(() => {
    if (selectedPreset && selectedPreset.id !== 'custom') {
      const recommendedFormat = EXPORT_FORMATS.find(f => f.id === selectedPreset.recommended_format);
      if (recommendedFormat) {
        setExportOptions(prev => ({
          ...prev,
          format: recommendedFormat.id
        }));
      }
    }
  }, [exportOptions.social_preset]);

  const handleExport = async () => {
    setIsExporting(true);
    setShowProgress(true);
    
    try {
      // 내보내기 요청 구성
      const exportRequest = {
        canvas_id: canvasId,
        user_id: 'current_user_id', // TODO: 실제 사용자 ID
        conversation_id: conversationId,
        export_options: {
          ...exportOptions,
          custom_width: exportOptions.social_preset === 'custom' ? exportOptions.custom_width : undefined,
          custom_height: exportOptions.social_preset === 'custom' ? exportOptions.custom_height : undefined
        },
        // 포맷별 세부 옵션
        ...(exportOptions.format === 'jpeg' && {
          jpeg_options: {
            quality: advancedOptions.jpeg_quality,
            progressive: false,
            optimize: true
          }
        }),
        ...(exportOptions.format === 'png' && {
          png_options: {
            compression_level: advancedOptions.png_compression,
            interlaced: false
          }
        }),
        ...(exportOptions.format === 'webp' && {
          webp_options: {
            quality: advancedOptions.webp_quality,
            lossless: advancedOptions.webp_lossless,
            method: 4
          }
        }),
        ...(exportOptions.format === 'pdf' && {
          pdf_options: {
            template: advancedOptions.pdf_template,
            page_size: advancedOptions.pdf_page_size,
            orientation: advancedOptions.pdf_orientation,
            margin_mm: advancedOptions.pdf_margin,
            add_page_numbers: true,
            add_bookmarks: true,
            print_optimized: false
          }
        }),
        // 클라우드 옵션
        ...(cloudOptions.provider !== 'none' && {
          cloud_options: {
            provider: cloudOptions.provider,
            generate_share_link: cloudOptions.generate_share_link,
            share_permissions: cloudOptions.share_permissions,
            folder_path: cloudOptions.folder_path
          }
        })
      };

      // API 호출
      const endpoint = isSeriesMode ? '/api/v1/canvas-export/batch-export' : '/api/v1/canvas-export/export';
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify(isSeriesMode ? {
          conversation_id: conversationId,
          user_id: 'current_user_id',
          canvas_ids: canvasIds,
          ...exportRequest
        } : exportRequest)
      });

      if (!response.ok) {
        throw new Error(`내보내기 요청 실패: ${response.status}`);
      }

      const progressData: ExportProgress = await response.json();
      setExportProgress(progressData);

      // 진행 상황 폴링
      pollExportProgress(progressData.export_id);

    } catch (error) {
      console.error('내보내기 실패:', error);
      setIsExporting(false);
      setShowProgress(false);
      // TODO: 에러 토스트 표시
    }
  };

  const pollExportProgress = async (exportId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/canvas-export/progress/${exportId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
          }
        });

        if (response.ok) {
          const progress: ExportProgress = await response.json();
          setExportProgress(progress);

          if (progress.status === 'completed' || progress.status === 'failed') {
            clearInterval(pollInterval);
            setIsExporting(false);
            
            if (progress.status === 'completed' && progress.download_url) {
              // 자동 다운로드
              const downloadLink = document.createElement('a');
              downloadLink.href = progress.download_url;
              downloadLink.download = `${canvasName}_export.${exportOptions.format}`;
              downloadLink.click();
              
              // 성공 후 다이얼로그 닫기
              setTimeout(() => {
                setShowProgress(false);
                onClose();
              }, 2000);
            }
          }
        }
      } catch (error) {
        console.error('진행 상황 조회 실패:', error);
        clearInterval(pollInterval);
        setIsExporting(false);
        setShowProgress(false);
      }
    }, 1000);
  };

  const handleDownload = () => {
    if (exportProgress?.download_url) {
      window.open(exportProgress.download_url, '_blank');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        
        {/* 헤더 */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
              <Download className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                {isSeriesMode ? '시리즈 일괄 내보내기' : 'Canvas 내보내기'}
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {isSeriesMode 
                  ? `${canvasIds.length}개 Canvas를 다양한 형식으로 내보내세요`
                  : `${canvasName}을(를) 다양한 형식으로 내보내세요`
                }
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 진행 상황 오버레이 */}
        {showProgress && exportProgress && (
          <div className="absolute inset-0 bg-white dark:bg-slate-800 bg-opacity-95 flex items-center justify-center z-10">
            <div className="text-center p-8">
              <div className="w-16 h-16 mx-auto mb-4">
                {exportProgress.status === 'completed' ? (
                  <CheckCircle className="w-16 h-16 text-green-500" />
                ) : exportProgress.status === 'failed' ? (
                  <AlertCircle className="w-16 h-16 text-red-500" />
                ) : (
                  <Loader className="w-16 h-16 text-blue-500 animate-spin" />
                )}
              </div>
              
              <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
                {exportProgress.status === 'completed' ? '내보내기 완료!' :
                 exportProgress.status === 'failed' ? '내보내기 실패' :
                 '내보내는 중...'}
              </h3>
              
              <p className="text-slate-600 dark:text-slate-400 mb-4">
                {exportProgress.current_step}
              </p>

              {/* 진행 바 */}
              <div className="w-80 bg-slate-200 dark:bg-slate-700 rounded-full h-2 mb-4">
                <div 
                  className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${exportProgress.progress_percentage}%` }}
                />
              </div>

              <p className="text-sm text-slate-500 dark:text-slate-500 mb-6">
                {exportProgress.progress_percentage}% 완료
                {exportProgress.file_size && (
                  <span className="ml-2">
                    ({(exportProgress.file_size / 1024 / 1024).toFixed(1)} MB)
                  </span>
                )}
              </p>

              {/* 액션 버튼들 */}
              {exportProgress.status === 'completed' && (
                <div className="flex gap-3 justify-center">
                  <button
                    onClick={handleDownload}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    다운로드
                  </button>
                  {exportProgress.cloud_url && (
                    <button
                      onClick={() => window.open(exportProgress.cloud_url, '_blank')}
                      className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center gap-2"
                    >
                      <Cloud className="w-4 h-4" />
                      클라우드에서 열기
                    </button>
                  )}
                </div>
              )}

              {exportProgress.error_message && (
                <p className="text-red-500 text-sm mt-4">
                  {exportProgress.error_message}
                </p>
              )}
            </div>
          </div>
        )}

        {/* 탭 네비게이션 */}
        <div className="flex border-b border-slate-200 dark:border-slate-700">
          {[
            { id: 'basic', name: '기본 설정', icon: <Settings className="w-4 h-4" /> },
            { id: 'advanced', name: '고급 설정', icon: <Palette className="w-4 h-4" /> },
            { id: 'cloud', name: '클라우드 연동', icon: <Cloud className="w-4 h-4" /> }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors ${
                activeTab === tab.id
                  ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              {tab.icon}
              {tab.name}
            </button>
          ))}
        </div>

        {/* 탭 콘텐츠 */}
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          
          {/* 기본 설정 탭 */}
          {activeTab === 'basic' && (
            <div className="space-y-6">
              
              {/* 포맷 선택 */}
              <div>
                <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-4">
                  내보내기 포맷
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {EXPORT_FORMATS.map(format => (
                    <button
                      key={format.id}
                      onClick={() => setExportOptions(prev => ({ ...prev, format: format.id }))}
                      className={`p-4 border-2 rounded-lg transition-all ${
                        exportOptions.format === format.id
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                      }`}
                    >
                      <div className="flex flex-col items-center gap-2">
                        <div className={`${exportOptions.format === format.id ? 'text-blue-600 dark:text-blue-400' : 'text-slate-600 dark:text-slate-400'}`}>
                          {format.icon}
                        </div>
                        <span className={`font-medium ${exportOptions.format === format.id ? 'text-blue-900 dark:text-blue-100' : 'text-slate-900 dark:text-slate-100'}`}>
                          {format.name}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
                {selectedFormat && (
                  <p className="text-sm text-slate-600 dark:text-slate-400 mt-2">
                    {selectedFormat.description}
                  </p>
                )}
              </div>

              {/* 크기 설정 */}
              <div>
                <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-4">
                  크기 및 해상도
                </h3>
                
                {/* 소셜 미디어 사전 설정 */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    사전 설정
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                    {SOCIAL_PRESETS.map(preset => (
                      <button
                        key={preset.id}
                        onClick={() => setExportOptions(prev => ({ ...prev, social_preset: preset.id }))}
                        className={`p-3 border rounded-lg flex items-center gap-2 text-left transition-colors ${
                          exportOptions.social_preset === preset.id
                            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                            : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                        }`}
                      >
                        <div className={exportOptions.social_preset === preset.id ? 'text-blue-600' : 'text-slate-600'}>
                          {preset.icon}
                        </div>
                        <div>
                          <div className={`text-sm font-medium ${exportOptions.social_preset === preset.id ? 'text-blue-900 dark:text-blue-100' : 'text-slate-900 dark:text-slate-100'}`}>
                            {preset.name}
                          </div>
                          <div className="text-xs text-slate-500">
                            {preset.dimensions[0] > 0 ? `${preset.dimensions[0]} × ${preset.dimensions[1]}` : '사용자 정의'}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* 커스텀 크기 입력 */}
                {exportOptions.social_preset === 'custom' && (
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        가로 (px)
                      </label>
                      <input
                        type="number"
                        value={exportOptions.custom_width || ''}
                        onChange={(e) => setExportOptions(prev => ({ ...prev, custom_width: parseInt(e.target.value) || undefined }))}
                        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-slate-700 dark:text-slate-100"
                        placeholder="1920"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        세로 (px)
                      </label>
                      <input
                        type="number"
                        value={exportOptions.custom_height || ''}
                        onChange={(e) => setExportOptions(prev => ({ ...prev, custom_height: parseInt(e.target.value) || undefined }))}
                        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-slate-700 dark:text-slate-100"
                        placeholder="1080"
                      />
                    </div>
                  </div>
                )}

                {/* 해상도 배수 */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                    해상도 배수
                  </label>
                  <div className="flex gap-2">
                    {['1x', '2x', '4x'].map(multiplier => (
                      <button
                        key={multiplier}
                        onClick={() => setExportOptions(prev => ({ ...prev, resolution_multiplier: multiplier as any }))}
                        className={`px-4 py-2 border rounded-lg font-medium transition-colors ${
                          exportOptions.resolution_multiplier === multiplier
                            ? 'border-blue-500 bg-blue-500 text-white'
                            : 'border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                        }`}
                      >
                        {multiplier}
                      </button>
                    ))}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    높은 배수일수록 더 선명하지만 파일 크기가 커집니다
                  </p>
                </div>
              </div>

              {/* 기본 옵션 */}
              <div>
                <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-4">
                  기본 옵션
                </h3>
                <div className="space-y-4">
                  
                  {/* 투명 배경 */}
                  {selectedFormat?.supports_transparency && (
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                          투명 배경
                        </label>
                        <p className="text-xs text-slate-500">
                          배경을 투명하게 내보냅니다
                        </p>
                      </div>
                      <button
                        onClick={() => setExportOptions(prev => ({ ...prev, transparent_background: !prev.transparent_background }))}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          exportOptions.transparent_background ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'
                        }`}
                      >
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          exportOptions.transparent_background ? 'translate-x-6' : 'translate-x-1'
                        }`} />
                      </button>
                    </div>
                  )}

                  {/* 워터마크 */}
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        워터마크 추가
                      </label>
                      <p className="text-xs text-slate-500">
                        이미지에 텍스트 워터마크를 추가합니다
                      </p>
                    </div>
                    <button
                      onClick={() => setExportOptions(prev => ({ ...prev, include_watermark: !prev.include_watermark }))}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        exportOptions.include_watermark ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'
                      }`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        exportOptions.include_watermark ? 'translate-x-6' : 'translate-x-1'
                      }`} />
                    </button>
                  </div>

                  {/* 워터마크 설정 */}
                  {exportOptions.include_watermark && (
                    <div className="ml-4 p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                          워터마크 텍스트
                        </label>
                        <input
                          type="text"
                          value={exportOptions.watermark_text}
                          onChange={(e) => setExportOptions(prev => ({ ...prev, watermark_text: e.target.value }))}
                          className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-slate-700 dark:text-slate-100"
                          placeholder="Created with AIPortal"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          위치
                        </label>
                        <div className="grid grid-cols-3 gap-2">
                          {[
                            { value: 'top-left', label: '좌상단' },
                            { value: 'top-right', label: '우상단' },
                            { value: 'center', label: '중앙' },
                            { value: 'bottom-left', label: '좌하단' },
                            { value: 'bottom-right', label: '우하단' }
                          ].map(position => (
                            <button
                              key={position.value}
                              onClick={() => setExportOptions(prev => ({ ...prev, watermark_position: position.value as any }))}
                              className={`px-3 py-2 text-sm border rounded-md transition-colors ${
                                exportOptions.watermark_position === position.value
                                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                                  : 'border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-700'
                              }`}
                            >
                              {position.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 고급 설정 탭 */}
          {activeTab === 'advanced' && (
            <div className="space-y-6">
              
              {/* 품질 설정 */}
              {selectedFormat?.quality_adjustable && (
                <div>
                  <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-4">
                    품질 설정
                  </h3>
                  
                  {exportOptions.format === 'jpeg' && (
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        JPEG 품질: {advancedOptions.jpeg_quality}%
                      </label>
                      <input
                        type="range"
                        min="10"
                        max="100"
                        value={advancedOptions.jpeg_quality}
                        onChange={(e) => setAdvancedOptions(prev => ({ ...prev, jpeg_quality: parseInt(e.target.value) }))}
                        className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                      />
                      <div className="flex justify-between text-xs text-slate-500 mt-1">
                        <span>작은 크기</span>
                        <span>고품질</span>
                      </div>
                    </div>
                  )}
                  
                  {exportOptions.format === 'webp' && (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          WebP 품질: {advancedOptions.webp_quality}%
                        </label>
                        <input
                          type="range"
                          min="10"
                          max="100"
                          value={advancedOptions.webp_quality}
                          onChange={(e) => setAdvancedOptions(prev => ({ ...prev, webp_quality: parseInt(e.target.value) }))}
                          className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                        />
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                            무손실 압축
                          </label>
                          <p className="text-xs text-slate-500">
                            품질 손실 없이 압축 (파일 크기 증가)
                          </p>
                        </div>
                        <button
                          onClick={() => setAdvancedOptions(prev => ({ ...prev, webp_lossless: !prev.webp_lossless }))}
                          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                            advancedOptions.webp_lossless ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'
                          }`}
                        >
                          <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            advancedOptions.webp_lossless ? 'translate-x-6' : 'translate-x-1'
                          }`} />
                        </button>
                      </div>
                    </div>
                  )}
                  
                  {exportOptions.format === 'png' && (
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        PNG 압축 레벨: {advancedOptions.png_compression}
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="9"
                        value={advancedOptions.png_compression}
                        onChange={(e) => setAdvancedOptions(prev => ({ ...prev, png_compression: parseInt(e.target.value) }))}
                        className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                      />
                      <div className="flex justify-between text-xs text-slate-500 mt-1">
                        <span>빠른 처리</span>
                        <span>최적 압축</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* PDF 설정 */}
              {exportOptions.format === 'pdf' && (
                <div>
                  <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-4">
                    PDF 설정
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        템플릿
                      </label>
                      <select
                        value={advancedOptions.pdf_template}
                        onChange={(e) => setAdvancedOptions(prev => ({ ...prev, pdf_template: e.target.value }))}
                        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-slate-700 dark:text-slate-100"
                      >
                        <option value="gallery">갤러리</option>
                        <option value="portfolio">포트폴리오</option>
                        <option value="presentation">프레젠테이션</option>
                        <option value="catalog">카탈로그</option>
                        <option value="document">문서</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        용지 크기
                      </label>
                      <select
                        value={advancedOptions.pdf_page_size}
                        onChange={(e) => setAdvancedOptions(prev => ({ ...prev, pdf_page_size: e.target.value }))}
                        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-slate-700 dark:text-slate-100"
                      >
                        <option value="A4">A4</option>
                        <option value="A3">A3</option>
                        <option value="A5">A5</option>
                        <option value="Letter">Letter</option>
                        <option value="Legal">Legal</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        방향
                      </label>
                      <div className="flex gap-2">
                        {[
                          { value: 'portrait', label: '세로' },
                          { value: 'landscape', label: '가로' }
                        ].map(orientation => (
                          <button
                            key={orientation.value}
                            onClick={() => setAdvancedOptions(prev => ({ ...prev, pdf_orientation: orientation.value }))}
                            className={`flex-1 px-3 py-2 border rounded-md font-medium transition-colors ${
                              advancedOptions.pdf_orientation === orientation.value
                                ? 'border-blue-500 bg-blue-500 text-white'
                                : 'border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                            }`}
                          >
                            {orientation.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                        여백 (mm): {advancedOptions.pdf_margin}
                      </label>
                      <input
                        type="range"
                        min="5"
                        max="50"
                        value={advancedOptions.pdf_margin}
                        onChange={(e) => setAdvancedOptions(prev => ({ ...prev, pdf_margin: parseInt(e.target.value) }))}
                        className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* 일괄 내보내기 설정 */}
              {isSeriesMode && (
                <div>
                  <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-4">
                    일괄 내보내기 설정
                  </h3>
                  
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                          하나의 PDF로 결합 (PDF 포맷 선택 시)
                        </label>
                        <p className="text-xs text-slate-500">
                          모든 Canvas를 하나의 다중 페이지 PDF로 생성합니다
                        </p>
                      </div>
                      <button
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          exportOptions.format === 'pdf' ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'
                        }`}
                        disabled={exportOptions.format !== 'pdf'}
                      >
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          exportOptions.format === 'pdf' ? 'translate-x-6' : 'translate-x-1'
                        }`} />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 클라우드 연동 탭 */}
          {activeTab === 'cloud' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100 mb-4">
                  클라우드 스토리지
                </h3>
                
                {/* 클라우드 제공업체 선택 */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
                  {[
                    { id: 'none', name: '저장 안함', icon: <X className="w-5 h-5" />, color: 'slate' },
                    { id: 'google_drive', name: 'Google Drive', icon: <Cloud className="w-5 h-5" />, color: 'blue' },
                    { id: 'dropbox', name: 'Dropbox', icon: <Package className="w-5 h-5" />, color: 'indigo' },
                    { id: 'aws_s3', name: 'AWS S3', icon: <Cloud className="w-5 h-5" />, color: 'orange' }
                  ].map(provider => (
                    <button
                      key={provider.id}
                      onClick={() => setCloudOptions(prev => ({ ...prev, provider: provider.id }))}
                      className={`p-4 border-2 rounded-lg transition-all ${
                        cloudOptions.provider === provider.id
                          ? `border-${provider.color}-500 bg-${provider.color}-50 dark:bg-${provider.color}-900/20`
                          : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex flex-col items-center gap-2">
                        <div className={cloudOptions.provider === provider.id ? `text-${provider.color}-600` : 'text-slate-600'}>
                          {provider.icon}
                        </div>
                        <span className={`text-sm font-medium ${cloudOptions.provider === provider.id ? `text-${provider.color}-900 dark:text-${provider.color}-100` : 'text-slate-900 dark:text-slate-100'}`}>
                          {provider.name}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>

                {/* 클라우드 설정 */}
                {cloudOptions.provider !== 'none' && (
                  <div className="space-y-4 p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    
                    {/* 폴더 경로 */}
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                        폴더 경로
                      </label>
                      <input
                        type="text"
                        value={cloudOptions.folder_path}
                        onChange={(e) => setCloudOptions(prev => ({ ...prev, folder_path: e.target.value }))}
                        className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-slate-700 dark:text-slate-100"
                        placeholder="/AIPortal Exports"
                      />
                    </div>

                    {/* 공유 링크 생성 */}
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                          공유 링크 생성
                        </label>
                        <p className="text-xs text-slate-500">
                          업로드 후 공유 가능한 링크를 생성합니다
                        </p>
                      </div>
                      <button
                        onClick={() => setCloudOptions(prev => ({ ...prev, generate_share_link: !prev.generate_share_link }))}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          cloudOptions.generate_share_link ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'
                        }`}
                      >
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          cloudOptions.generate_share_link ? 'translate-x-6' : 'translate-x-1'
                        }`} />
                      </button>
                    </div>

                    {/* 공유 권한 */}
                    {cloudOptions.generate_share_link && (
                      <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                          공유 권한
                        </label>
                        <div className="flex gap-2">
                          {[
                            { value: 'view', label: '보기 전용' },
                            { value: 'comment', label: '댓글 가능' },
                            { value: 'edit', label: '편집 가능' }
                          ].map(permission => (
                            <button
                              key={permission.value}
                              onClick={() => setCloudOptions(prev => ({ ...prev, share_permissions: permission.value }))}
                              className={`px-3 py-2 border rounded-md font-medium transition-colors ${
                                cloudOptions.share_permissions === permission.value
                                  ? 'border-blue-500 bg-blue-500 text-white'
                                  : 'border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
                              }`}
                            >
                              {permission.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 클라우드별 추가 설정 안내 */}
                    <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
                      <p className="text-sm text-blue-800 dark:text-blue-200">
                        {cloudOptions.provider === 'google_drive' && '💡 Google Drive 계정 연결이 필요합니다.'}
                        {cloudOptions.provider === 'dropbox' && '💡 Dropbox 계정 연결이 필요합니다.'}
                        {cloudOptions.provider === 'aws_s3' && '💡 AWS S3 자격 증명이 필요합니다.'}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* 푸터 */}
        <div className="flex items-center justify-between p-6 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
          <div className="text-sm text-slate-600 dark:text-slate-400">
            {isSeriesMode 
              ? `${canvasIds.length}개 Canvas를 ${exportOptions.format.toUpperCase()} 형식으로 내보내기`
              : `${canvasName}을 ${exportOptions.format.toUpperCase()} 형식으로 내보내기`
            }
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={onClose}
              disabled={isExporting}
              className="px-4 py-2 text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
            >
              취소
            </button>
            <button
              onClick={handleExport}
              disabled={isExporting || (exportOptions.social_preset === 'custom' && (!exportOptions.custom_width || !exportOptions.custom_height))}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {isExporting ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  내보내는 중...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  내보내기 시작
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};