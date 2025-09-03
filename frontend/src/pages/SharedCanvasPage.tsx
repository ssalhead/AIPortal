/**
 * 공유 Canvas 페이지
 * URL: /shared/canvas/:shareToken
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Lock, AlertTriangle, Clock } from 'lucide-react';
import ShareCanvasViewer from '../components/canvas/ShareCanvasViewer';

interface ShareInfo {
  title: string;
  description: string;
  preview_image_url?: string;
  created_at: string;
  creator_id?: string;
}

const SharedCanvasPage: React.FC = () => {
  const { shareToken } = useParams<{ shareToken: string }>();
  const navigate = useNavigate();
  
  const [shareInfo, setShareInfo] = useState<ShareInfo | null>(null);
  const [needsPassword, setNeedsPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // 공유 정보 로드
  const loadShareInfo = async () => {
    if (!shareToken) return;

    try {
      const response = await fetch(`/api/v1/canvas/share/public/${shareToken}/info`);
      
      if (response.ok) {
        const data = await response.json();
        setShareInfo(data);
        
        // 페이지 제목 및 메타태그 업데이트
        document.title = `${data.title} - AI Portal`;
        
        // 기존 메타태그 제거 후 새로 추가
        updateMetaTags(data);
      } else if (response.status === 404) {
        setError('Share link not found or has been removed');
      } else {
        setError('Failed to load share information');
      }
    } catch (err) {
      console.error('Failed to load share info:', err);
      setError('Network error. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  // 메타태그 업데이트 (소셜 미디어 공유용)
  const updateMetaTags = (info: ShareInfo) => {
    // 기본 메타태그
    updateMetaTag('description', info.description || 'View this Canvas creation on AI Portal');
    
    // Open Graph
    updateMetaTag('property', 'og:title', info.title);
    updateMetaTag('property', 'og:description', info.description || 'View this Canvas creation on AI Portal');
    updateMetaTag('property', 'og:image', info.preview_image_url || '');
    updateMetaTag('property', 'og:url', window.location.href);
    updateMetaTag('property', 'og:type', 'website');
    
    // Twitter Card
    updateMetaTag('name', 'twitter:card', 'summary_large_image');
    updateMetaTag('name', 'twitter:title', info.title);
    updateMetaTag('name', 'twitter:description', info.description || 'View this Canvas creation on AI Portal');
    updateMetaTag('name', 'twitter:image', info.preview_image_url || '');
  };

  const updateMetaTag = (attribute: string, value: string, content?: string) => {
    const attr = content ? attribute : 'name';
    const val = content || value;
    const cont = content || '';
    
    let element = document.querySelector(`meta[${attr}="${val}"]`) as HTMLMetaElement;
    
    if (!element) {
      element = document.createElement('meta');
      element.setAttribute(attr, val);
      document.head.appendChild(element);
    }
    
    element.setAttribute('content', cont || content || '');
  };

  useEffect(() => {
    loadShareInfo();
  }, [shareToken]);

  // 비밀번호 제출
  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError('');
    // ShareCanvasViewer 컴포넌트가 비밀번호를 받아 처리
  };

  // 비밀번호 필요 처리
  const handlePasswordRequired = () => {
    setNeedsPassword(true);
  };

  // 접근 거부 처리
  const handleAccessDenied = (errorCode: string) => {
    switch (errorCode) {
      case 'SHARE_EXPIRED':
        setError('This share link has expired');
        break;
      case 'SHARE_VIEW_LIMIT_EXCEEDED':
        setError('This share link has reached its view limit');
        break;
      case 'SHARE_PERMISSION_DENIED':
        setError('You do not have permission to view this canvas');
        break;
      default:
        setError('Access denied');
    }
  };

  if (!shareToken) {
    navigate('/');
    return null;
  }

  // 로딩 상태
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading shared canvas...</p>
        </div>
      </div>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <AlertTriangle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Unable to Access Canvas</h1>
          <p className="text-gray-600 mb-6">{error}</p>
          
          <div className="space-y-3">
            <button
              onClick={() => window.location.reload()}
              className="w-full px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              Try Again
            </button>
            <button
              onClick={() => navigate('/')}
              className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
            >
              Go to Home
            </button>
          </div>
          
          {shareInfo && (
            <div className="mt-6 text-left bg-white p-4 rounded-lg border">
              <h3 className="font-semibold text-gray-900 mb-2">Canvas Information</h3>
              <div className="space-y-1 text-sm text-gray-600">
                <div><strong>Title:</strong> {shareInfo.title}</div>
                <div><strong>Created:</strong> {new Date(shareInfo.created_at).toLocaleDateString()}</div>
                {shareInfo.creator_id && (
                  <div><strong>Creator:</strong> {shareInfo.creator_id}</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // 비밀번호 입력 필요
  if (needsPassword && !password) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md mx-auto p-6">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="text-center mb-6">
              <Lock className="h-12 w-12 text-blue-500 mx-auto mb-4" />
              <h1 className="text-xl font-bold text-gray-900 mb-2">Password Required</h1>
              <p className="text-gray-600">This canvas is password protected.</p>
            </div>

            {shareInfo && (
              <div className="bg-gray-50 p-4 rounded-lg mb-6">
                <h3 className="font-semibold text-gray-900 mb-1">{shareInfo.title}</h3>
                {shareInfo.description && (
                  <p className="text-gray-600 text-sm">{shareInfo.description}</p>
                )}
                <div className="flex items-center text-xs text-gray-500 mt-2">
                  <Clock className="h-4 w-4 mr-1" />
                  Created {new Date(shareInfo.created_at).toLocaleDateString()}
                </div>
              </div>
            )}

            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Enter Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter the password..."
                  required
                />
                {passwordError && (
                  <p className="text-red-500 text-sm mt-1">{passwordError}</p>
                )}
              </div>

              <button
                type="submit"
                className="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 transition-colors"
              >
                Access Canvas
              </button>
            </form>

            <div className="text-center mt-4">
              <button
                onClick={() => navigate('/')}
                className="text-gray-500 hover:text-gray-700 text-sm"
              >
                Go back to home
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Canvas 뷰어 렌더링
  return (
    <ShareCanvasViewer
      shareToken={shareToken}
      password={password}
      onPasswordRequired={handlePasswordRequired}
      onAccessDenied={handleAccessDenied}
    />
  );
};

export default SharedCanvasPage;