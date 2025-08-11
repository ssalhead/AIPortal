/**
 * 워크스페이스 통합 Canvas 컴포넌트
 * 기존 Canvas 기능을 워크스페이스 아티팩트 시스템과 연동
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  FileText, 
  Image, 
  GitBranch, 
  Code, 
  BarChart3,
  Plus,
  Users,
  Eye,
  Edit3,
  Save,
  Download
} from 'lucide-react';

// 아티팩트 타입별 이름 정의
const TOOL_NAMES: Record<string, string> = {
  text: '텍스트 노트',
  image: '이미지 생성',
  mindmap: '마인드맵',
  code: '코드 편집기',
  chart: '차트'
};

// 기존 Canvas 컴포넌트들 재사용
import { TextNoteEditor } from '../canvas/TextNoteEditor';
import { WorkspaceImageGenerator } from './WorkspaceImageGenerator';
import { MindMapEditor } from '../canvas/MindMapEditor';

interface WorkspaceArtifact {
  id: string;
  title: string;
  type: string;
  content: string;
  position: { x: number; y: number };
  size: { width: number; height: number };
  version: number;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

interface WorkspaceCanvasProps {
  workspaceId: string;
  artifacts: WorkspaceArtifact[];
  onArtifactUpdate: (artifactId: string, updates: Partial<WorkspaceArtifact>) => void;
  onArtifactCreate: (artifact: Omit<WorkspaceArtifact, 'id' | 'version' | 'created_at' | 'updated_at'>) => void;
  onArtifactDelete: (artifactId: string) => void;
  collaborators: Array<{
    user_id: string;
    name: string;
    email: string;
    permission_level: string;
  }>;
  currentUserId: string;
  isReadOnly?: boolean;
}

export const WorkspaceCanvas: React.FC<WorkspaceCanvasProps> = ({
  workspaceId,
  artifacts,
  onArtifactUpdate,
  onArtifactCreate,
  onArtifactDelete,
  collaborators,
  currentUserId,
  isReadOnly = false
}) => {
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null);
  const [draggedItem, setDraggedItem] = useState<string | null>(null);
  const [showCreateMenu, setShowCreateMenu] = useState(false);
  const [activeEditors, setActiveEditors] = useState<Record<string, string>>({});
  const [onlineUsers, setOnlineUsers] = useState<string[]>([]);
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);

  // WebSocket 연결 관리
  useEffect(() => {
    const connectWebSocket = () => {
      const wsUrl = `ws://localhost:8000/ws/workspace/${workspaceId}?token=test-token`;
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('워크스페이스 WebSocket 연결됨');
        setWebsocket(ws);
      };
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error('WebSocket 메시지 파싱 오류:', error);
        }
      };
      
      ws.onclose = () => {
        console.log('워크스페이스 WebSocket 연결 해제');
        setWebsocket(null);
        // 재연결 시도 (3초 후)
        setTimeout(connectWebSocket, 3000);
      };
      
      ws.onerror = (error) => {
        console.error('워크스페이스 WebSocket 오류:', error);
      };
    };
    
    connectWebSocket();
    
    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, [workspaceId]);

  // WebSocket 메시지 처리
  const handleWebSocketMessage = useCallback((message: any) => {
    switch (message.type) {
      case 'user_joined':
        setOnlineUsers(message.data.active_users.map((u: any) => u.id));
        break;
      
      case 'user_left':
        setOnlineUsers(message.data.active_users.map((u: any) => u.id));
        // 편집 중이던 아티팩트 해제
        if (message.data.released_artifacts) {
          setActiveEditors(prev => {
            const updated = { ...prev };
            message.data.released_artifacts.forEach((artifactId: string) => {
              delete updated[artifactId];
            });
            return updated;
          });
        }
        break;
      
      case 'artifact_edit_start':
        setActiveEditors(prev => ({
          ...prev,
          [message.data.artifact_id]: message.data.editor.id
        }));
        break;
      
      case 'artifact_edit_stop':
        setActiveEditors(prev => {
          const updated = { ...prev };
          delete updated[message.data.artifact_id];
          return updated;
        });
        break;
      
      case 'artifact_content_change':
        // 실시간 내용 동기화 (여기서는 로그만)
        console.log('아티팩트 실시간 변경:', message.data);
        break;
    }
  }, []);

  // 아티팩트 편집 시작
  const startEditing = (artifactId: string) => {
    if (isReadOnly) return;
    
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.send(JSON.stringify({
        type: 'artifact_edit',
        data: {
          artifact_id: artifactId,
          action: 'start_editing'
        }
      }));
    }
    
    setSelectedArtifact(artifactId);
  };

  // 아티팩트 편집 종료
  const stopEditing = (artifactId: string) => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.send(JSON.stringify({
        type: 'artifact_edit',
        data: {
          artifact_id: artifactId,
          action: 'stop_editing'
        }
      }));
    }
    
    if (selectedArtifact === artifactId) {
      setSelectedArtifact(null);
    }
  };

  // 새 아티팩트 생성
  const createArtifact = (type: string) => {
    if (isReadOnly) return;
    
    const newArtifact = {
      title: `새 ${getArtifactTypeName(type)}`,
      type,
      content: getDefaultContent(type),
      position: { x: Math.random() * 300 + 100, y: Math.random() * 200 + 100 },
      size: getDefaultSize(type),
      is_pinned: false
    };
    
    onArtifactCreate(newArtifact);
    setShowCreateMenu(false);
  };

  // 아티팩트 위치 업데이트
  const updateArtifactPosition = (artifactId: string, position: { x: number; y: number }) => {
    onArtifactUpdate(artifactId, { position });
  };

  // 아티팩트 내용 업데이트
  const updateArtifactContent = (artifactId: string, content: string) => {
    onArtifactUpdate(artifactId, { content });
    
    // 실시간 동기화
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.send(JSON.stringify({
        type: 'artifact_edit',
        data: {
          artifact_id: artifactId,
          action: 'content_change',
          content
        }
      }));
    }
  };

  // 유틸리티 함수들
  const getArtifactTypeName = (type: string): string => {
    const names: Record<string, string> = {
      text: '텍스트 노트',
      image: '이미지',
      mindmap: '마인드맵',
      code: '코드',
      chart: '차트'
    };
    return names[type] || type;
  };

  const getDefaultContent = (type: string): string => {
    const defaults: Record<string, string> = {
      text: '새 텍스트 노트입니다.',
      image: '',
      mindmap: '{"nodes": [], "edges": []}',
      code: '// 새 코드 파일\nconsole.log("Hello, World!");',
      chart: '{"type": "bar", "data": {}}'
    };
    return defaults[type] || '';
  };

  const getDefaultSize = (type: string): { width: number; height: number } => {
    const sizes: Record<string, { width: number; height: number }> = {
      text: { width: 400, height: 300 },
      image: { width: 400, height: 400 },
      mindmap: { width: 600, height: 500 },
      code: { width: 500, height: 400 },
      chart: { width: 450, height: 350 }
    };
    return sizes[type] || { width: 400, height: 300 };
  };

  const getArtifactIcon = (type: string) => {
    const icons: Record<string, React.ReactNode> = {
      text: <FileText className="w-4 h-4" />,
      image: <Image className="w-4 h-4" />,
      mindmap: <GitBranch className="w-4 h-4" />,
      code: <Code className="w-4 h-4" />,
      chart: <BarChart3 className="w-4 h-4" />
    };
    return icons[type] || <FileText className="w-4 h-4" />;
  };

  // 편집 중인 사용자 표시
  const getEditorInfo = (artifactId: string) => {
    const editorId = activeEditors[artifactId];
    if (!editorId || editorId === currentUserId) return null;
    
    const editor = collaborators.find(c => c.user_id === editorId);
    return editor ? `${editor.name}이 편집 중` : '다른 사용자가 편집 중';
  };

  return (
    <div className="h-full bg-gray-50 relative overflow-hidden">
      {/* 툴바 */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
        {/* 생성 도구 */}
        <div className="relative">
          <button
            onClick={() => setShowCreateMenu(!showCreateMenu)}
            disabled={isReadOnly}
            className="flex items-center gap-2 px-3 py-2 bg-white rounded-lg shadow-sm border border-gray-200 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus className="w-4 h-4" />
            <span className="text-sm font-medium">아티팩트 추가</span>
          </button>
          
          {showCreateMenu && !isReadOnly && (
            <div className="absolute top-full left-0 mt-1 bg-white rounded-lg shadow-lg border border-gray-200 py-1 min-w-[150px]">
              {Object.entries(TOOL_NAMES).map(([type, name]) => (
                <button
                  key={type}
                  onClick={() => createArtifact(type)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50"
                >
                  {getArtifactIcon(type)}
                  {name}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 협업자 표시 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-2">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-gray-500" />
            <span className="text-xs font-medium text-gray-700">
              협업자 ({collaborators.length})
            </span>
          </div>
          
          <div className="flex -space-x-1">
            {collaborators.slice(0, 5).map((collaborator) => (
              <div
                key={collaborator.user_id}
                className={`relative w-6 h-6 rounded-full border-2 border-white flex items-center justify-center text-xs font-bold text-white ${
                  onlineUsers.includes(collaborator.user_id) 
                    ? 'bg-green-500' 
                    : 'bg-gray-400'
                }`}
                title={`${collaborator.name} (${collaborator.permission_level})`}
              >
                {collaborator.name.charAt(0)}
                {onlineUsers.includes(collaborator.user_id) && (
                  <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border border-white"></div>
                )}
              </div>
            ))}
            
            {collaborators.length > 5 && (
              <div className="w-6 h-6 rounded-full bg-gray-300 border-2 border-white flex items-center justify-center text-xs font-bold text-gray-600">
                +{collaborators.length - 5}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Canvas 영역 */}
      <div className="h-full w-full relative">
        {artifacts.map((artifact) => {
          const editorInfo = getEditorInfo(artifact.id);
          const isBeingEdited = activeEditors[artifact.id] && activeEditors[artifact.id] !== currentUserId;
          
          return (
            <div
              key={artifact.id}
              className={`absolute bg-white rounded-lg shadow-lg border-2 transition-all duration-200 ${
                isBeingEdited 
                  ? 'border-yellow-400 shadow-yellow-100' 
                  : selectedArtifact === artifact.id 
                    ? 'border-blue-400 shadow-blue-100' 
                    : 'border-gray-200'
              } ${artifact.is_pinned ? 'ring-2 ring-purple-200' : ''}`}
              style={{
                left: artifact.position.x,
                top: artifact.position.y,
                width: artifact.size.width,
                height: artifact.size.height,
                transform: draggedItem === artifact.id ? 'scale(1.02)' : 'scale(1)',
                zIndex: selectedArtifact === artifact.id ? 10 : 1
              }}
              onClick={() => !isBeingEdited && startEditing(artifact.id)}
            >
              {/* 아티팩트 헤더 */}
              <div className="flex items-center justify-between p-2 border-b border-gray-100 bg-gray-50 rounded-t-lg">
                <div className="flex items-center gap-2">
                  {getArtifactIcon(artifact.type)}
                  <span className="text-sm font-medium text-gray-700">
                    {artifact.title}
                  </span>
                  <span className="text-xs text-gray-500">v{artifact.version}</span>
                </div>
                
                <div className="flex items-center gap-1">
                  {isBeingEdited && (
                    <div className="flex items-center gap-1 text-xs text-yellow-600">
                      <Edit3 className="w-3 h-3" />
                      <span>{editorInfo}</span>
                    </div>
                  )}
                  
                  {artifact.is_pinned && (
                    <span className="text-purple-500">📌</span>
                  )}
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!isReadOnly) {
                        onArtifactDelete(artifact.id);
                      }
                    }}
                    disabled={isReadOnly || isBeingEdited}
                    className="p-1 text-gray-400 hover:text-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    ×
                  </button>
                </div>
              </div>

              {/* 아티팩트 콘텐츠 */}
              <div className="p-2 h-full overflow-hidden">
                {artifact.type === 'text' && (
                  <TextNoteEditor
                    content={artifact.content}
                    onChange={(content) => updateArtifactContent(artifact.id, content)}
                    readOnly={isReadOnly || isBeingEdited}
                  />
                )}
                
                {artifact.type === 'image' && (
                  <WorkspaceImageGenerator
                    onImageGenerated={(imageData) => updateArtifactContent(artifact.id, imageData)}
                    readOnly={isReadOnly || isBeingEdited}
                  />
                )}
                
                {artifact.type === 'mindmap' && (
                  <MindMapEditor
                    data={artifact.content}
                    onChange={(content) => updateArtifactContent(artifact.id, content)}
                    readOnly={isReadOnly || isBeingEdited}
                  />
                )}
                
                {artifact.type === 'code' && (
                  <div className="h-full">
                    <textarea
                      value={artifact.content}
                      onChange={(e) => updateArtifactContent(artifact.id, e.target.value)}
                      readOnly={isReadOnly || isBeingEdited}
                      className="w-full h-full resize-none border-none outline-none font-mono text-sm bg-gray-900 text-green-400 p-2 rounded"
                      placeholder="코드를 입력하세요..."
                    />
                  </div>
                )}
                
                {artifact.type === 'chart' && (
                  <div className="h-full flex items-center justify-center text-gray-500">
                    <div className="text-center">
                      <BarChart3 className="w-8 h-8 mx-auto mb-2" />
                      <p className="text-sm">차트 기능 구현 예정</p>
                    </div>
                  </div>
                )}
              </div>
              
              {/* 편집 상태 오버레이 */}
              {isBeingEdited && (
                <div className="absolute inset-0 bg-yellow-100/50 rounded-lg flex items-center justify-center">
                  <div className="bg-white px-3 py-1 rounded-full shadow-sm border text-sm text-yellow-700">
                    {editorInfo}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* 빈 상태 */}
        {artifacts.length === 0 && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="text-gray-300 text-8xl mb-4">🎨</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                비어있는 캔버스
              </h3>
              <p className="text-gray-500 mb-6">
                아티팩트를 추가하여 협업을 시작하세요.
              </p>
              {!isReadOnly && (
                <button
                  onClick={() => setShowCreateMenu(true)}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  첫 번째 아티팩트 만들기
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 하단 상태바 */}
      <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-sm border border-gray-200 px-3 py-2">
        <div className="flex items-center gap-4 text-xs text-gray-600">
          <span>아티팩트: {artifacts.length}개</span>
          <span>온라인: {onlineUsers.length}명</span>
          <span>편집 중: {Object.keys(activeEditors).length}개</span>
        </div>
      </div>
    </div>
  );

};