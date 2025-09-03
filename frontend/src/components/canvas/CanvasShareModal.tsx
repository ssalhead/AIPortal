/**
 * Canvas 공유 모달 컴포넌트
 */

import React, { useState, useEffect } from 'react';
import {
  X,
  Share,
  Copy,
  Eye,
  Download,
  Edit,
  Lock,
  Unlock,
  Clock,
  Users,
  Settings,
  ExternalLink,
  BarChart3,
  AlertTriangle
} from 'lucide-react';
import CanvasShareAnalytics from './CanvasShareAnalytics';

interface ShareLink {
  id: string;
  share_token: string;
  canvas_id: string;
  title?: string;
  description?: string;
  permission: 'read_only' | 'copy_enabled' | 'edit_enabled';
  visibility: 'public' | 'private' | 'password_protected' | 'user_limited';
  duration: '24_hours' | '7_days' | '30_days' | 'unlimited';
  view_count: number;
  download_count: number;
  is_active: boolean;
  expires_at?: string;
  share_url: string;
  created_at: string;
  can_access: boolean;
}

interface CanvasShareModalProps {
  canvasId: string;
  isOpen: boolean;
  onClose: () => void;
}

const CanvasShareModal: React.FC<CanvasShareModalProps> = ({
  canvasId,
  isOpen,
  onClose
}) => {
  const [shares, setShares] = useState<ShareLink[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedShare, setSelectedShare] = useState<ShareLink | null>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  
  // 새 공유 링크 폼 상태
  const [newShare, setNewShare] = useState({
    title: '',
    description: '',
    permission: 'read_only' as const,
    visibility: 'public' as const,
    duration: '7_days' as const,
    password: '',
    max_views: ''
  });

  // 공유 링크 목록 로드
  const loadShares = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/canvas/share/canvas/${canvasId}/shares`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setShares(data);
      }
    } catch (err) {
      console.error('Failed to load shares:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadShares();
    }
  }, [isOpen, canvasId]);

  // 새 공유 링크 생성
  const createShare = async () => {
    try {
      const response = await fetch('/api/v1/canvas/share/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          canvas_id: canvasId,
          title: newShare.title || undefined,
          description: newShare.description || undefined,
          permission: newShare.permission,
          visibility: newShare.visibility,
          duration: newShare.duration,
          password: newShare.password || undefined,
          max_views: newShare.max_views ? parseInt(newShare.max_views) : undefined
        })
      });

      if (response.ok) {
        await loadShares();
        setShowCreateForm(false);
        setNewShare({
          title: '',
          description: '',
          permission: 'read_only',
          visibility: 'public',
          duration: '7_days',
          password: '',
          max_views: ''
        });
      } else {
        alert('Failed to create share link');
      }
    } catch (err) {
      console.error('Failed to create share:', err);
      alert('Failed to create share link');
    }
  };

  // 공유 링크 삭제
  const deleteShare = async (shareToken: string) => {
    if (!confirm('Are you sure you want to delete this share link?')) return;

    try {
      const response = await fetch(`/api/v1/canvas/share/${shareToken}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        await loadShares();
      } else {
        alert('Failed to delete share link');
      }
    } catch (err) {
      console.error('Failed to delete share:', err);
      alert('Failed to delete share link');
    }
  };

  // URL 복사
  const copyUrl = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      alert('Link copied to clipboard!');
    } catch (err) {
      console.error('Failed to copy URL:', err);
      alert('Failed to copy link');
    }
  };

  // 권한 아이콘
  const getPermissionIcon = (permission: string) => {
    switch (permission) {
      case 'edit_enabled': return <Edit className="h-4 w-4" />;
      case 'copy_enabled': return <Download className="h-4 w-4" />;
      default: return <Eye className="h-4 w-4" />;
    }
  };

  // 가시성 아이콘
  const getVisibilityIcon = (visibility: string) => {
    switch (visibility) {
      case 'private': return <Lock className="h-4 w-4" />;
      case 'password_protected': return <Lock className="h-4 w-4" />;
      case 'user_limited': return <Users className="h-4 w-4" />;
      default: return <Unlock className="h-4 w-4" />;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-2">
            <Share className="h-6 w-6 text-blue-500" />
            <h2 className="text-xl font-semibold">Share Canvas</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-md"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 내용 */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* 새 공유 링크 생성 버튼 */}
          {!showCreateForm && (
            <div className="mb-6">
              <button
                onClick={() => setShowCreateForm(true)}
                className="w-full bg-blue-500 text-white py-3 px-4 rounded-md hover:bg-blue-600 flex items-center justify-center space-x-2"
              >
                <Share className="h-5 w-5" />
                <span>Create New Share Link</span>
              </button>
            </div>
          )}

          {/* 새 공유 링크 생성 폼 */}
          {showCreateForm && (
            <div className="mb-6 bg-gray-50 p-6 rounded-lg">
              <h3 className="text-lg font-semibold mb-4">Create New Share Link</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Title (optional)
                  </label>
                  <input
                    type="text"
                    value={newShare.title}
                    onChange={(e) => setNewShare({ ...newShare, title: e.target.value })}
                    className="w-full border rounded-md px-3 py-2"
                    placeholder="My Awesome Canvas"
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description (optional)
                  </label>
                  <textarea
                    value={newShare.description}
                    onChange={(e) => setNewShare({ ...newShare, description: e.target.value })}
                    className="w-full border rounded-md px-3 py-2"
                    rows={3}
                    placeholder="Description of your canvas..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Permission
                  </label>
                  <select
                    value={newShare.permission}
                    onChange={(e) => setNewShare({ ...newShare, permission: e.target.value as any })}
                    className="w-full border rounded-md px-3 py-2"
                  >
                    <option value="read_only">View Only</option>
                    <option value="copy_enabled">View + Copy</option>
                    <option value="edit_enabled">View + Copy + Edit</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Visibility
                  </label>
                  <select
                    value={newShare.visibility}
                    onChange={(e) => setNewShare({ ...newShare, visibility: e.target.value as any })}
                    className="w-full border rounded-md px-3 py-2"
                  >
                    <option value="public">Public</option>
                    <option value="password_protected">Password Protected</option>
                    <option value="private">Private</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Duration
                  </label>
                  <select
                    value={newShare.duration}
                    onChange={(e) => setNewShare({ ...newShare, duration: e.target.value as any })}
                    className="w-full border rounded-md px-3 py-2"
                  >
                    <option value="24_hours">24 Hours</option>
                    <option value="7_days">7 Days</option>
                    <option value="30_days">30 Days</option>
                    <option value="unlimited">Unlimited</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Views (optional)
                  </label>
                  <input
                    type="number"
                    value={newShare.max_views}
                    onChange={(e) => setNewShare({ ...newShare, max_views: e.target.value })}
                    className="w-full border rounded-md px-3 py-2"
                    placeholder="Unlimited"
                    min="1"
                  />
                </div>

                {newShare.visibility === 'password_protected' && (
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Password
                    </label>
                    <input
                      type="password"
                      value={newShare.password}
                      onChange={(e) => setNewShare({ ...newShare, password: e.target.value })}
                      className="w-full border rounded-md px-3 py-2"
                      placeholder="Enter password..."
                      required
                    />
                  </div>
                )}
              </div>

              <div className="flex justify-end space-x-2 mt-4">
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 text-gray-600 border rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={createShare}
                  className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                >
                  Create Share Link
                </button>
              </div>
            </div>
          )}

          {/* 기존 공유 링크 목록 */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Existing Share Links</h3>
            
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                <p className="text-gray-600 mt-2">Loading shares...</p>
              </div>
            ) : shares.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Share className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No share links created yet</p>
              </div>
            ) : (
              <div className="space-y-4">
                {shares.map((share) => (
                  <div
                    key={share.id}
                    className={`border rounded-lg p-4 ${
                      !share.can_access ? 'bg-red-50 border-red-200' : 'bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <h4 className="font-medium">
                            {share.title || 'Untitled Share'}
                          </h4>
                          <div className="flex items-center space-x-1">
                            {getPermissionIcon(share.permission)}
                            {getVisibilityIcon(share.visibility)}
                          </div>
                          {!share.can_access && (
                            <div className="flex items-center space-x-1 text-red-500">
                              <AlertTriangle className="h-4 w-4" />
                              <span className="text-sm">Expired</span>
                            </div>
                          )}
                        </div>
                        
                        {share.description && (
                          <p className="text-gray-600 text-sm mb-2">{share.description}</p>
                        )}
                        
                        <div className="flex items-center space-x-4 text-sm text-gray-500">
                          <div className="flex items-center space-x-1">
                            <Eye className="h-4 w-4" />
                            <span>{share.view_count} views</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Download className="h-4 w-4" />
                            <span>{share.download_count} downloads</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <Clock className="h-4 w-4" />
                            <span>Created {new Date(share.created_at).toLocaleDateString()}</span>
                          </div>
                          {share.expires_at && (
                            <div className="flex items-center space-x-1">
                              <span>Expires {new Date(share.expires_at).toLocaleDateString()}</span>
                            </div>
                          )}
                        </div>
                        
                        <div className="mt-3 flex items-center space-x-1 bg-gray-100 p-2 rounded text-sm font-mono">
                          <input
                            type="text"
                            value={share.share_url}
                            readOnly
                            className="flex-1 bg-transparent border-none outline-none"
                          />
                        </div>
                      </div>
                      
                      <div className="flex flex-col space-y-2 ml-4">
                        <button
                          onClick={() => copyUrl(share.share_url)}
                          className="p-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                          title="Copy link"
                        >
                          <Copy className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => window.open(share.share_url, '_blank')}
                          className="p-2 bg-green-500 text-white rounded-md hover:bg-green-600"
                          title="Open link"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => {
                            setSelectedShare(share);
                            setShowAnalytics(true);
                          }}
                          className="p-2 bg-gray-500 text-white rounded-md hover:bg-gray-600"
                          title="Analytics"
                        >
                          <BarChart3 className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => deleteShare(share.share_token)}
                          className="p-2 bg-red-500 text-white rounded-md hover:bg-red-600"
                          title="Delete"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 푸터 */}
        <div className="border-t p-6 bg-gray-50">
          <div className="text-sm text-gray-600">
            <p>
              Share links allow others to view your canvas. You can control permissions,
              set expiration dates, and track views.
            </p>
          </div>
        </div>
      </div>
      
      {/* 분석 모달 */}
      {selectedShare && (
        <CanvasShareAnalytics
          shareToken={selectedShare.share_token}
          shareTitle={selectedShare.title || 'Untitled Share'}
          isOpen={showAnalytics}
          onClose={() => {
            setShowAnalytics(false);
            setSelectedShare(null);
          }}
        />
      )}
    </div>
  );
};

export default CanvasShareModal;