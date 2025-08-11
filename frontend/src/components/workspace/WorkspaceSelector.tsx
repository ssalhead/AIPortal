/**
 * 워크스페이스 선택기 컴포넌트
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, Briefcase, Users, Calendar } from 'lucide-react';

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

interface WorkspaceSelectorProps {
  currentWorkspaceId?: string;
  onWorkspaceChange?: (workspaceId: string) => void;
  mode?: 'dropdown' | 'list';
}

export const WorkspaceSelector: React.FC<WorkspaceSelectorProps> = ({
  currentWorkspaceId,
  onWorkspaceChange,
  mode = 'dropdown'
}) => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDropdown, setShowDropdown] = useState(false);
  const navigate = useNavigate();

  const currentWorkspace = workspaces.find(w => w.id === currentWorkspaceId);

  useEffect(() => {
    loadWorkspaces();
  }, []);

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

  const handleWorkspaceSelect = (workspaceId: string) => {
    if (onWorkspaceChange) {
      onWorkspaceChange(workspaceId);
    } else {
      navigate(`/split/${workspaceId}`);
    }
    setShowDropdown(false);
  };

  const getTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      canvas: '🎨',
      document: '📄',
      code: '💻',
      data: '📊',
      workflow: '⚡'
    };
    return icons[type] || '📋';
  };

  if (loading) {
    return (
      <div className="animate-pulse bg-gray-200 h-8 w-48 rounded"></div>
    );
  }

  if (mode === 'list') {
    return (
      <div className="space-y-2">
        {workspaces.map((workspace) => (
          <div
            key={workspace.id}
            onClick={() => handleWorkspaceSelect(workspace.id)}
            className={`p-3 rounded-lg border cursor-pointer transition-colors ${
              currentWorkspaceId === workspace.id
                ? 'bg-blue-50 border-blue-200'
                : 'bg-white border-gray-200 hover:bg-gray-50'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg">{getTypeIcon(workspace.type)}</span>
                <div>
                  <h4 className="font-medium text-gray-900">{workspace.name}</h4>
                  <p className="text-sm text-gray-500">{workspace.description}</p>
                </div>
              </div>
              <div className="text-right text-xs text-gray-500">
                <div>📄 {workspace.artifact_count}</div>
                <div>{workspace.permission_level}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="w-full flex items-center justify-between px-3 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <div className="flex items-center gap-2 min-w-0">
          {currentWorkspace ? (
            <>
              <span className="text-sm">{getTypeIcon(currentWorkspace.type)}</span>
              <span className="font-medium text-gray-900 truncate">
                {currentWorkspace.name}
              </span>
            </>
          ) : (
            <>
              <Briefcase className="w-4 h-4 text-gray-400" />
              <span className="text-gray-500">워크스페이스 선택</span>
            </>
          )}
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showDropdown ? 'rotate-180' : ''}`} />
      </button>

      {showDropdown && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
          <div className="p-1">
            {workspaces.map((workspace) => (
              <button
                key={workspace.id}
                onClick={() => handleWorkspaceSelect(workspace.id)}
                className={`w-full text-left px-3 py-2 rounded hover:bg-gray-50 transition-colors ${
                  currentWorkspaceId === workspace.id ? 'bg-blue-50' : ''
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm">{getTypeIcon(workspace.type)}</span>
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-gray-900 truncate">
                      {workspace.name}
                    </div>
                    <div className="text-xs text-gray-500 truncate">
                      {workspace.description}
                    </div>
                  </div>
                  <div className="text-xs text-gray-400">
                    📄 {workspace.artifact_count}
                  </div>
                </div>
              </button>
            ))}
            
            {workspaces.length === 0 && (
              <div className="px-3 py-4 text-center text-gray-500 text-sm">
                워크스페이스가 없습니다
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};