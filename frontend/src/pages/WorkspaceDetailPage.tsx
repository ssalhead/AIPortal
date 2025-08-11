/**
 * 개별 워크스페이스 상세 페이지
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Share2, 
  Settings, 
  Users, 
  Download, 
  MoreVertical,
  MessageSquare,
  Briefcase,
  Split
} from 'lucide-react';
import { WorkspaceCanvas } from '../components/workspace/WorkspaceCanvas';

interface WorkspaceDetail {
  id: string;
  name: string;
  description: string;
  type: string;
  is_public: boolean;
  config: Record<string, any>;
  layout: Record<string, any>;
  artifacts: Array<{
    id: string;
    title: string;
    type: string;
    content: string;
    version: number;
    is_pinned: boolean;
    position: { x: number; y: number };
    size: { width: number; height: number };
    created_at: string;
    updated_at: string;
  }>;
  collaborators: Array<{
    user_id: string;
    email: string;
    name: string;
    permission_level: string;
    joined_at: string;
  }>;
  created_at: string;
  updated_at: string;
}

const WorkspaceDetailPage: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const [workspace, setWorkspace] = useState<WorkspaceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSidebar, setShowSidebar] = useState(false);
  const [activeView, setActiveView] = useState<'canvas' | 'chat'>('canvas');

  // 현재 사용자 정보 (실제로는 인증 컨텍스트에서 가져와야 함)
  const currentUserId = "ff8e410a-53a4-4541-a7d4-ce265678d66a";

  // 워크스페이스 정보 로드
  const loadWorkspace = async () => {
    if (!workspaceId) return;
    
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/workspaces/${workspaceId}`, {
        headers: {
          'Authorization': 'Bearer test-token'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setWorkspace(data);
      } else {
        setError('워크스페이스를 불러올 수 없습니다');
      }
    } catch (err) {
      setError('네트워크 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  };

  // 아티팩트 업데이트
  const handleArtifactUpdate = async (artifactId: string, updates: Partial<any>) => {
    if (!workspace) return;
    
    // 로컬 상태 즉시 업데이트 (낙관적 업데이트)
    setWorkspace(prev => {
      if (!prev) return prev;
      
      return {
        ...prev,
        artifacts: prev.artifacts.map(artifact =>
          artifact.id === artifactId
            ? { ...artifact, ...updates }
            : artifact
        )
      };
    });
    
    // 서버에 업데이트 전송 (실제 API 호출)
    try {
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/artifacts/${artifactId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-token'
        },
        body: JSON.stringify(updates)
      });
      
      if (!response.ok) {
        // 실패 시 롤백 (실제로는 서버에서 최신 상태를 다시 가져와야 함)
        console.error('아티팩트 업데이트 실패');
        loadWorkspace();
      }
    } catch (error) {
      console.error('아티팩트 업데이트 오류:', error);
      loadWorkspace();
    }
  };

  // 새 아티팩트 생성
  const handleArtifactCreate = async (artifactData: any) => {
    if (!workspaceId) return;
    
    try {
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/artifacts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-token'
        },
        body: JSON.stringify(artifactData)
      });
      
      if (response.ok) {
        // 워크스페이스 새로고침
        loadWorkspace();
      } else {
        console.error('아티팩트 생성 실패');
      }
    } catch (error) {
      console.error('아티팩트 생성 오류:', error);
    }
  };

  // 아티팩트 삭제
  const handleArtifactDelete = async (artifactId: string) => {
    if (!confirm('이 아티팩트를 삭제하시겠습니까?')) return;
    
    try {
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/artifacts/${artifactId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': 'Bearer test-token'
        }
      });
      
      if (response.ok) {
        // 로컬 상태에서 즉시 제거
        setWorkspace(prev => {
          if (!prev) return prev;
          
          return {
            ...prev,
            artifacts: prev.artifacts.filter(artifact => artifact.id !== artifactId)
          };
        });
      } else {
        console.error('아티팩트 삭제 실패');
      }
    } catch (error) {
      console.error('아티팩트 삭제 오류:', error);
    }
  };

  useEffect(() => {
    loadWorkspace();
  }, [workspaceId]);

  // 사용자 권한 확인
  const currentUserPermission = workspace?.collaborators.find(
    c => c.user_id === currentUserId
  )?.permission_level || 'viewer';
  
  const isReadOnly = !['owner', 'editor'].includes(currentUserPermission);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">워크스페이스를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error || !workspace) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || '워크스페이스를 찾을 수 없습니다'}</p>
          <button
            onClick={() => navigate('/workspace')}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            워크스페이스 목록으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* 워크스페이스 헤더 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/workspace')}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            
            <div>
              <h1 className="text-xl font-bold text-gray-900">{workspace.name}</h1>
              <p className="text-sm text-gray-500">
                {workspace.description} • {workspace.type}
              </p>
            </div>
            
            {isReadOnly && (
              <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                읽기 전용
              </span>
            )}
          </div>

          {/* 뷰 토글 및 액션 */}
          <div className="flex items-center gap-3">
            {/* 뷰 토글 */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setActiveView('canvas')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  activeView === 'canvas'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <Briefcase className="w-4 h-4 mr-1 inline" />
                Canvas
              </button>
              <button
                onClick={() => setActiveView('chat')}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                  activeView === 'chat'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <MessageSquare className="w-4 h-4 mr-1 inline" />
                채팅
              </button>
            </div>

            {/* 액션 버튼 */}
            <button
              onClick={() => navigate(`/split/${workspaceId}`)}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              title="분할 화면으로 열기"
            >
              <Split className="w-5 h-5" />
            </button>
            
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
            >
              <Users className="w-5 h-5" />
            </button>
            
            <button className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
              <Share2 className="w-5 h-5" />
            </button>
            
            <button className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* 메인 컨텐츠 */}
      <div className="flex-1 flex overflow-hidden">
        {/* Canvas/채팅 영역 */}
        <div className="flex-1 relative">
          {activeView === 'canvas' ? (
            <WorkspaceCanvas
              workspaceId={workspace.id}
              artifacts={workspace.artifacts}
              onArtifactUpdate={handleArtifactUpdate}
              onArtifactCreate={handleArtifactCreate}
              onArtifactDelete={handleArtifactDelete}
              collaborators={workspace.collaborators}
              currentUserId={currentUserId}
              isReadOnly={isReadOnly}
            />
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center text-gray-500">
                <MessageSquare className="w-12 h-12 mx-auto mb-4" />
                <p>워크스페이스 채팅 기능 구현 예정</p>
              </div>
            </div>
          )}
        </div>

        {/* 사이드바 (협업자 정보) */}
        {showSidebar && (
          <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
            <div className="p-4 border-b border-gray-200">
              <h3 className="font-semibold text-gray-900">협업자</h3>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4">
              <div className="space-y-3">
                {workspace.collaborators.map((collaborator) => (
                  <div key={collaborator.user_id} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-bold">
                        {collaborator.name.charAt(0)}
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{collaborator.name}</p>
                        <p className="text-xs text-gray-500">{collaborator.email}</p>
                      </div>
                    </div>
                    
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      collaborator.permission_level === 'owner' 
                        ? 'bg-purple-100 text-purple-800'
                        : collaborator.permission_level === 'editor'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {collaborator.permission_level}
                    </span>
                  </div>
                ))}
              </div>
              
              {!isReadOnly && (
                <button className="w-full mt-4 px-4 py-2 border border-dashed border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50">
                  + 협업자 초대
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkspaceDetailPage;