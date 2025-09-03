/**
 * 공유 Canvas 뷰어 컴포넌트
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Share,
  Download,
  Copy,
  ZoomIn,
  ZoomOut,
  Maximize,
  Eye,
  EyeOff,
  Info,
  AlertTriangle,
  Lock,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

interface CanvasImage {
  id: string;
  version: number;
  url: string;
  prompt: string;
  style: string;
  size: string;
  created_at: string;
  edit_mode: string;
}

interface ShareAccessResponse {
  canvas_id: string;
  canvas_data: {
    canvas_id: string;
    images: CanvasImage[];
    metadata: {
      total_versions: number;
      created_at: string;
      last_updated: string;
    };
  };
  permission: 'read_only' | 'copy_enabled' | 'edit_enabled';
  title?: string;
  description?: string;
  created_at: string;
  creator_info?: {
    creator_id: string;
    created_at: string;
  };
  preview_image_url?: string;
  layers_count: number;
  elements_count: number;
}

interface ShareCanvasViewerProps {
  shareToken: string;
  password?: string;
  onPasswordRequired?: () => void;
  onAccessDenied?: (error: string) => void;
}

const ShareCanvasViewer: React.FC<ShareCanvasViewerProps> = ({
  shareToken,
  password,
  onPasswordRequired,
  onAccessDenied
}) => {
  const [shareData, setShareData] = useState<ShareAccessResponse | null>(null);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [showMetadata, setShowMetadata] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showReport, setShowReport] = useState(false);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // Canvas 데이터 로드
  const loadCanvasData = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`/api/v1/canvas/share/access/${shareToken}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          password: password || undefined
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        
        if (response.status === 401 && errorData.detail?.error_code === 'SHARE_PASSWORD_REQUIRED') {
          onPasswordRequired?.();
          return;
        }
        
        if (response.status === 401 && errorData.detail?.error_code === 'SHARE_PASSWORD_INCORRECT') {
          setError('Incorrect password');
          onPasswordRequired?.();
          return;
        }
        
        if (response.status === 410) {
          setError('This share link has expired');
          return;
        }
        
        if (response.status === 429) {
          setError('View limit exceeded for this share link');
          return;
        }
        
        setError(errorData.detail?.message || 'Failed to load canvas');
        onAccessDenied?.(errorData.detail?.error_code || 'ACCESS_DENIED');
        return;
      }

      const data: ShareAccessResponse = await response.json();
      setShareData(data);
      
    } catch (err) {
      setError('Network error. Please try again.');
      console.error('Failed to load canvas data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCanvasData();
  }, [shareToken, password]);

  // 다운로드 추적
  const trackDownload = async () => {
    try {
      await fetch(`/api/v1/canvas/share/${shareToken}/download`, {
        method: 'POST'
      });
    } catch (err) {
      console.error('Failed to track download:', err);
    }
  };

  // 이미지 다운로드
  const downloadImage = async (imageUrl: string, filename: string) => {
    if (!shareData || shareData.permission === 'read_only') {
      alert('Download not allowed for this share');
      return;
    }

    try {
      await trackDownload();
      
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
      alert('Download failed. Please try again.');
    }
  };

  // 클립보드에 이미지 복사
  const copyToClipboard = async (imageUrl: string) => {
    if (!shareData || shareData.permission === 'read_only') {
      alert('Copy not allowed for this share');
      return;
    }

    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      
      await navigator.clipboard.write([
        new ClipboardItem({ [blob.type]: blob })
      ]);
      
      alert('Image copied to clipboard!');
    } catch (err) {
      console.error('Copy failed:', err);
      alert('Copy failed. Please try again.');
    }
  };

  // 풀스크린 토글
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  // 줌 조작
  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.25, 3));
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.25, 0.25));
  const handleZoomReset = () => setZoom(1);

  // 신고 모달
  const ReportModal: React.FC<{ onClose: () => void }> = ({ onClose }) => {
    const [reason, setReason] = useState('inappropriate');
    const [description, setDescription] = useState('');
    const [email, setEmail] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const submitReport = async () => {
      setSubmitting(true);
      try {
        await fetch(`/api/v1/canvas/share/${shareToken}/report`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ reason, description, reporter_email: email })
        });
        alert('Report submitted successfully');
        onClose();
      } catch (err) {
        alert('Failed to submit report');
      } finally {
        setSubmitting(false);
      }
    };

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
          <h3 className="text-lg font-semibold mb-4">Report Content</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Reason</label>
              <select 
                value={reason} 
                onChange={(e) => setReason(e.target.value)}
                className="w-full border rounded-md px-3 py-2"
              >
                <option value="inappropriate">Inappropriate content</option>
                <option value="copyright">Copyright violation</option>
                <option value="spam">Spam</option>
                <option value="harassment">Harassment</option>
                <option value="violence">Violence</option>
                <option value="illegal">Illegal content</option>
                <option value="misinformation">Misinformation</option>
                <option value="other">Other</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Description (optional)</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full border rounded-md px-3 py-2"
                rows={3}
                placeholder="Additional details..."
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Email (optional)</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full border rounded-md px-3 py-2"
                placeholder="your@email.com"
              />
            </div>
          </div>
          
          <div className="flex justify-end space-x-2 mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 border rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={submitReport}
              disabled={submitting}
              className="px-4 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Submit Report'}
            </button>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading canvas...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center p-8">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Unable to Load Canvas</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={loadCanvasData}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!shareData) return null;

  const currentImage = shareData.canvas_data.images[currentImageIndex];
  const hasMultipleImages = shareData.canvas_data.images.length > 1;
  const canDownload = shareData.permission !== 'read_only';

  return (
    <div ref={containerRef} className="min-h-screen bg-gray-900 text-white relative">
      {/* 헤더 */}
      <div className="bg-black bg-opacity-50 p-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div>
            <h1 className="text-xl font-semibold">
              {shareData.title || 'Untitled Canvas'}
            </h1>
            {shareData.description && (
              <p className="text-gray-300 text-sm mt-1">{shareData.description}</p>
            )}
          </div>
          {shareData.permission !== 'read_only' && (
            <div className="flex items-center space-x-1 text-xs bg-green-600 px-2 py-1 rounded">
              <Lock className="h-3 w-3" />
              <span>{shareData.permission.replace('_', ' ')}</span>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {/* 메타데이터 토글 */}
          <button
            onClick={() => setShowMetadata(!showMetadata)}
            className="p-2 bg-gray-700 rounded-md hover:bg-gray-600"
            title={showMetadata ? 'Hide info' : 'Show info'}
          >
            {showMetadata ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
          </button>

          {/* 줌 컨트롤 */}
          <div className="flex items-center space-x-1 bg-gray-700 rounded-md">
            <button
              onClick={handleZoomOut}
              className="p-2 hover:bg-gray-600 rounded-l-md"
              title="Zoom out"
            >
              <ZoomOut className="h-4 w-4" />
            </button>
            <button
              onClick={handleZoomReset}
              className="px-3 py-2 text-sm font-mono hover:bg-gray-600"
              title="Reset zoom"
            >
              {Math.round(zoom * 100)}%
            </button>
            <button
              onClick={handleZoomIn}
              className="p-2 hover:bg-gray-600 rounded-r-md"
              title="Zoom in"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
          </div>

          {/* 액션 버튼들 */}
          {canDownload && (
            <>
              <button
                onClick={() => copyToClipboard(currentImage.url)}
                className="p-2 bg-gray-700 rounded-md hover:bg-gray-600"
                title="Copy to clipboard"
              >
                <Copy className="h-5 w-5" />
              </button>
              <button
                onClick={() => downloadImage(currentImage.url, `canvas-${currentImage.id}.png`)}
                className="p-2 bg-gray-700 rounded-md hover:bg-gray-600"
                title="Download image"
              >
                <Download className="h-5 w-5" />
              </button>
            </>
          )}

          {/* 공유 버튼 */}
          <button
            onClick={() => navigator.share?.({ url: window.location.href, title: shareData.title })}
            className="p-2 bg-gray-700 rounded-md hover:bg-gray-600"
            title="Share"
          >
            <Share className="h-5 w-5" />
          </button>

          {/* 풀스크린 */}
          <button
            onClick={toggleFullscreen}
            className="p-2 bg-gray-700 rounded-md hover:bg-gray-600"
            title="Fullscreen"
          >
            <Maximize className="h-5 w-5" />
          </button>

          {/* 신고 버튼 */}
          <button
            onClick={() => setShowReport(true)}
            className="p-2 bg-red-600 rounded-md hover:bg-red-700"
            title="Report"
          >
            <AlertTriangle className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="flex flex-1">
        {/* 이미지 뷰어 */}
        <div className="flex-1 flex items-center justify-center p-4 relative">
          {hasMultipleImages && (
            <button
              onClick={() => setCurrentImageIndex(Math.max(0, currentImageIndex - 1))}
              disabled={currentImageIndex === 0}
              className="absolute left-4 top-1/2 transform -translate-y-1/2 p-2 bg-black bg-opacity-50 rounded-full disabled:opacity-50"
            >
              <ChevronLeft className="h-6 w-6" />
            </button>
          )}

          <div className="max-w-full max-h-full overflow-hidden">
            <img
              ref={imageRef}
              src={currentImage.url}
              alt={currentImage.prompt}
              style={{ transform: `scale(${zoom})`, maxWidth: '100%', maxHeight: '80vh' }}
              className="object-contain transition-transform duration-200"
            />
          </div>

          {hasMultipleImages && (
            <button
              onClick={() => setCurrentImageIndex(Math.min(shareData.canvas_data.images.length - 1, currentImageIndex + 1))}
              disabled={currentImageIndex === shareData.canvas_data.images.length - 1}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 p-2 bg-black bg-opacity-50 rounded-full disabled:opacity-50"
            >
              <ChevronRight className="h-6 w-6" />
            </button>
          )}

          {/* 이미지 인덱스 표시 */}
          {hasMultipleImages && (
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black bg-opacity-50 px-3 py-1 rounded-full text-sm">
              {currentImageIndex + 1} / {shareData.canvas_data.images.length}
            </div>
          )}
        </div>

        {/* 메타데이터 패널 */}
        {showMetadata && (
          <div className="w-80 bg-gray-800 p-4 overflow-y-auto">
            <div className="space-y-4">
              {/* Canvas 정보 */}
              <div>
                <h3 className="text-lg font-semibold mb-2">Canvas Info</h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-gray-400">Created:</span>
                    <span className="ml-2">{new Date(shareData.created_at).toLocaleDateString()}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Versions:</span>
                    <span className="ml-2">{shareData.canvas_data.metadata.total_versions}</span>
                  </div>
                  {shareData.creator_info && (
                    <div>
                      <span className="text-gray-400">Creator:</span>
                      <span className="ml-2">{shareData.creator_info.creator_id}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* 현재 이미지 정보 */}
              <div>
                <h3 className="text-lg font-semibold mb-2">Current Image</h3>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-gray-400">Version:</span>
                    <span className="ml-2">{currentImage.version}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Style:</span>
                    <span className="ml-2">{currentImage.style}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Size:</span>
                    <span className="ml-2">{currentImage.size}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Mode:</span>
                    <span className="ml-2">{currentImage.edit_mode}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Created:</span>
                    <span className="ml-2">{new Date(currentImage.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              {/* 프롬프트 */}
              <div>
                <h3 className="text-lg font-semibold mb-2">Prompt</h3>
                <p className="text-sm text-gray-300 bg-gray-900 p-3 rounded border overflow-wrap break-words">
                  {currentImage.prompt}
                </p>
              </div>

              {/* 이미지 목록 */}
              {hasMultipleImages && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">All Versions</h3>
                  <div className="space-y-2">
                    {shareData.canvas_data.images.map((image, index) => (
                      <button
                        key={image.id}
                        onClick={() => setCurrentImageIndex(index)}
                        className={`w-full text-left p-2 rounded text-sm ${
                          index === currentImageIndex ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
                        }`}
                      >
                        <div className="flex items-center space-x-2">
                          <img src={image.url} alt="" className="w-8 h-8 object-cover rounded" />
                          <div>
                            <div className="font-medium">Version {image.version}</div>
                            <div className="text-gray-300 truncate">{image.style} • {image.size}</div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 신고 모달 */}
      {showReport && <ReportModal onClose={() => setShowReport(false)} />}
    </div>
  );
};

export default ShareCanvasViewer;