import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Users, Calendar, Settings, Search, Filter, Split, Briefcase } from 'lucide-react';

// API 타입 정의
interface Workspace {
  id: string;
  name: string;
  description: string;
  type: string;
  is_public: boolean;
  permission_level: string;
  artifact_count: number;
  created_at: string;
  updated_at: string;
}

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

const WorkspacePage: React.FC = () => {
  const navigate = useNavigate();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<WorkspaceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWorkspace, setNewWorkspace] = useState({
    name: '',
    description: '',
    type: 'canvas',
    is_public: false
  });

  // 워크스페이스 목록 로드
  const loadWorkspaces = async () => {
    try {
      const response = await fetch('/api/v1/workspaces/', {
        headers: {
          'Authorization': 'Bearer test-token'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setWorkspaces(data);
      }
    } catch (error) {
      console.error('워크스페이스 목록 로드 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  // 워크스페이스 상세 정보 로드
  const loadWorkspaceDetail = async (workspaceId: string) => {
    try {
      const response = await fetch(`/api/v1/workspaces/${workspaceId}`, {
        headers: {
          'Authorization': 'Bearer test-token'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setSelectedWorkspace(data);
      }
    } catch (error) {
      console.error('워크스페이스 상세 정보 로드 실패:', error);
    }
  };

  // 새 워크스페이스 생성
  const createWorkspace = async () => {
    try {
      const response = await fetch('/api/v1/workspaces/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-token'
        },
        body: JSON.stringify(newWorkspace)
      });
      
      if (response.ok) {
        setShowCreateModal(false);
        setNewWorkspace({
          name: '',
          description: '',
          type: 'canvas',
          is_public: false
        });
        loadWorkspaces(); // 목록 새로고침
      }
    } catch (error) {
      console.error('워크스페이스 생성 실패:', error);
    }
  };

  useEffect(() => {
    loadWorkspaces();
  }, []);

  // 검색 및 필터링된 워크스페이스
  const filteredWorkspaces = workspaces.filter(ws => {
    const matchesSearch = ws.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         ws.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterType === 'all' || ws.type === filterType;
    return matchesSearch && matchesFilter;
  });

  const getPermissionBadgeColor = (level: string) => {
    switch (level) {
      case 'owner': return 'bg-purple-100 text-purple-800';
      case 'editor': return 'bg-blue-100 text-blue-800';
      case 'viewer': return 'bg-gray-100 text-gray-800';
      case 'commenter': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'canvas': return '🎨';
      case 'document': return '📄';
      case 'code': return '💻';
      case 'data': return '📊';
      case 'workflow': return '⚡';
      default: return '📋';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">워크스페이스를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">워크스페이스</h1>
              <span className="ml-2 text-sm text-gray-500">
                {workspaces.length}개의 워크스페이스
              </span>
            </div>
            
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              <Plus className="h-4 w-4 mr-2" />
              새 워크스페이스
            </button>
          </div>
        </div>
      </div>

      {/* 검색 및 필터 */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="워크스페이스 검색..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">모든 타입</option>
              <option value="canvas">Canvas</option>
              <option value="document">Document</option>
              <option value="code">Code</option>
              <option value="data">Data</option>
              <option value="workflow">Workflow</option>
            </select>
          </div>
        </div>

        {/* 워크스페이스 그리드 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredWorkspaces.map((workspace) => (
            <div
              key={workspace.id}
              onClick={() => navigate(`/workspace/${workspace.id}`)}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow relative group cursor-pointer"
            >
              {/* 워크스페이스 헤더 */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center">
                  <span className="text-2xl mr-3">{getTypeIcon(workspace.type)}</span>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 line-clamp-1">
                      {workspace.name}
                    </h3>
                    <p className="text-sm text-gray-500">
                      {workspace.type.charAt(0).toUpperCase() + workspace.type.slice(1)}
                    </p>
                  </div>
                </div>
                
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPermissionBadgeColor(workspace.permission_level)}`}>
                  {workspace.permission_level}
                </span>
              </div>

              {/* 설명 */}
              {workspace.description && (
                <p className="text-gray-600 text-sm mb-4 line-clamp-2">
                  {workspace.description}
                </p>
              )}

              {/* 메타 정보 */}
              <div className="flex items-center justify-between text-xs text-gray-500">
                <div className="flex items-center">
                  <Calendar className="h-3 w-3 mr-1" />
                  {new Date(workspace.updated_at).toLocaleDateString()}
                </div>
                
                <div className="flex items-center">
                  <span className="mr-3">📄 {workspace.artifact_count}</span>
                  {workspace.is_public && (
                    <span className="inline-flex items-center">
                      <Users className="h-3 w-3 mr-1" />
                      공개
                    </span>
                  )}
                </div>
              </div>
              
              {/* 빠른 액션 버튼 */}
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/workspace/${workspace.id}`);
                  }}
                  className="p-1.5 bg-white shadow-sm border border-gray-200 rounded hover:bg-gray-50"
                  title="워크스페이스 열기"
                >
                  <Briefcase className="w-3 h-3 text-gray-600" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/split/${workspace.id}`);
                  }}
                  className="p-1.5 bg-white shadow-sm border border-gray-200 rounded hover:bg-gray-50"
                  title="분할 화면으로 열기"
                >
                  <Split className="w-3 h-3 text-gray-600" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* 빈 상태 */}
        {filteredWorkspaces.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-6xl mb-4">🏗️</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              워크스페이스가 없습니다
            </h3>
            <p className="text-gray-500 mb-6">
              새 워크스페이스를 만들어 협업을 시작하세요.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              <Plus className="h-4 w-4 mr-2" />
              첫 번째 워크스페이스 만들기
            </button>
          </div>
        )}
      </div>

      {/* 워크스페이스 생성 모달 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold mb-4">새 워크스페이스 만들기</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  이름 *
                </label>
                <input
                  type="text"
                  value={newWorkspace.name}
                  onChange={(e) => setNewWorkspace({...newWorkspace, name: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  placeholder="워크스페이스 이름을 입력하세요"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  설명
                </label>
                <textarea
                  value={newWorkspace.description}
                  onChange={(e) => setNewWorkspace({...newWorkspace, description: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="워크스페이스에 대한 설명을 입력하세요"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  타입
                </label>
                <select
                  value={newWorkspace.type}
                  onChange={(e) => setNewWorkspace({...newWorkspace, type: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                >
                  <option value="canvas">🎨 Canvas</option>
                  <option value="document">📄 Document</option>
                  <option value="code">💻 Code</option>
                  <option value="data">📊 Data</option>
                  <option value="workflow">⚡ Workflow</option>
                </select>
              </div>
              
              <div className="flex items-center">
                <input
                  type="checkbox"
                  id="is_public"
                  checked={newWorkspace.is_public}
                  onChange={(e) => setNewWorkspace({...newWorkspace, is_public: e.target.checked})}
                  className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <label htmlFor="is_public" className="ml-2 text-sm text-gray-700">
                  공개 워크스페이스로 설정
                </label>
              </div>
            </div>
            
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
              >
                취소
              </button>
              <button
                onClick={createWorkspace}
                disabled={!newWorkspace.name.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-md"
              >
                생성
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 워크스페이스 상세 모달 */}
      {selectedWorkspace && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  {getTypeIcon(selectedWorkspace.type)} {selectedWorkspace.name}
                </h2>
                <p className="text-gray-600 mt-1">{selectedWorkspace.description}</p>
              </div>
              
              <div className="flex gap-2">
                <button className="p-2 text-gray-400 hover:text-gray-600">
                  <Settings className="h-5 w-5" />
                </button>
                <button
                  onClick={() => setSelectedWorkspace(null)}
                  className="p-2 text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* 협업자 정보 */}
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-3 flex items-center">
                <Users className="h-5 w-5 mr-2" />
                협업자 ({selectedWorkspace.collaborators.length}명)
              </h3>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {selectedWorkspace.collaborators.map((collaborator) => (
                  <div key={collaborator.user_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">{collaborator.name}</p>
                      <p className="text-sm text-gray-500">{collaborator.email}</p>
                    </div>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPermissionBadgeColor(collaborator.permission_level)}`}>
                      {collaborator.permission_level}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* 아티팩트 목록 */}
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-900 mb-3">
                아티팩트 ({selectedWorkspace.artifacts.length}개)
              </h3>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {selectedWorkspace.artifacts.map((artifact) => (
                  <div key={artifact.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow">
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium text-gray-900 line-clamp-1">{artifact.title}</h4>
                      {artifact.is_pinned && <span className="text-yellow-500">📌</span>}
                    </div>
                    
                    <p className="text-sm text-gray-500 mb-3">
                      {artifact.type} • v{artifact.version}
                    </p>
                    
                    <div className="text-xs text-gray-400">
                      위치: ({artifact.position.x}, {artifact.position.y})
                      <br />
                      크기: {artifact.size.width}×{artifact.size.height}
                    </div>
                  </div>
                ))}
              </div>
              
              {selectedWorkspace.artifacts.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  아직 아티팩트가 없습니다.
                </div>
              )}
            </div>

            {/* 액션 버튼 */}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  // 워크스페이스로 이동 (향후 구현)
                  console.log('워크스페이스 열기:', selectedWorkspace.id);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md"
              >
                워크스페이스 열기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkspacePage;