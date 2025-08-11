/**
 * 분할 화면 레이아웃 - 간단한 버전
 */

import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MessageSquare, Briefcase, Split } from 'lucide-react';

export const SplitScreenLayout: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();

  return (
    <div className="h-full flex flex-col bg-white">
      {/* 상단 헤더 */}
      <div className="bg-gradient-to-r from-blue-50 to-green-50 px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Split className="w-6 h-6 text-purple-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-900">분할 화면 모드</h1>
              <p className="text-sm text-gray-600">
                채팅과 워크스페이스를 동시에 사용하세요
              </p>
            </div>
          </div>
          <div className="text-sm text-gray-500">
            {workspaceId ? `워크스페이스: ${workspaceId.slice(0, 8)}...` : '워크스페이스 미선택'}
          </div>
        </div>
      </div>

      {/* 분할된 콘텐츠 영역 */}
      <div className="flex-1 flex">
        {/* 왼쪽: 채팅 영역 */}
        <div className="w-1/2 border-r-2 border-gray-200 flex flex-col bg-blue-50/30">
          <div className="bg-blue-100 px-4 py-3 border-b border-blue-200">
            <h3 className="font-medium text-blue-800 flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              AI 채팅
            </h3>
          </div>
          <div className="flex-1 p-4">
            <div className="h-full bg-white rounded-lg border border-blue-200 flex items-center justify-center">
              <div className="text-center text-blue-600">
                <MessageSquare className="w-12 h-12 mx-auto mb-4" />
                <p className="font-medium">채팅 기능</p>
                <p className="text-sm text-gray-500 mt-2">여기에 ChatPage 컴포넌트가 들어갑니다</p>
                <button
                  onClick={() => navigate('/chat')}
                  className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  전체 채팅으로 이동
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 오른쪽: 워크스페이스 영역 */}
        <div className="w-1/2 flex flex-col bg-green-50/30">
          <div className="bg-green-100 px-4 py-3 border-b border-green-200">
            <h3 className="font-medium text-green-800 flex items-center gap-2">
              <Briefcase className="w-4 h-4" />
              워크스페이스
            </h3>
          </div>
          <div className="flex-1 p-4">
            {workspaceId ? (
              <div className="h-full bg-white rounded-lg border border-green-200 flex items-center justify-center">
                <div className="text-center text-green-600">
                  <Briefcase className="w-12 h-12 mx-auto mb-4" />
                  <p className="font-medium">워크스페이스: {workspaceId.slice(0, 8)}...</p>
                  <p className="text-sm text-gray-500 mt-2">여기에 WorkspaceDetailPage 컴포넌트가 들어갑니다</p>
                  <button
                    onClick={() => navigate(`/workspace/${workspaceId}`)}
                    className="mt-4 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                  >
                    전체 워크스페이스로 이동
                  </button>
                </div>
              </div>
            ) : (
              <div className="h-full bg-white rounded-lg border border-gray-200 flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <Briefcase className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p className="font-medium mb-4">워크스페이스를 선택해주세요</p>
                  <button
                    onClick={() => navigate('/workspace')}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                  >
                    워크스페이스 목록
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};