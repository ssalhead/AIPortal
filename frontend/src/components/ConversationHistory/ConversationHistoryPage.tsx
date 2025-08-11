/**
 * 대화 이력 메인 페이지 컴포넌트
 */

import React, { useState, useEffect } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { History, TrendingUp } from 'lucide-react';
import { ConversationList } from './ConversationList';
import { ConversationDetailView } from './ConversationDetailView';
import type { ConversationSummary } from '../../services/conversationHistoryService';
import { conversationHistoryService } from '../../services/conversationHistoryService';
import { useToast } from '../ui/Toast';

interface ConversationHistoryPageProps {
  className?: string;
}

export const ConversationHistoryPage: React.FC<ConversationHistoryPageProps> = ({
  className = ''
}) => {
  const [selectedConversationId, setSelectedConversationId] = useState<string | undefined>();
  const [showStatistics, setShowStatistics] = useState(false);
  const [statistics, setStatistics] = useState<any>(null);
  const { showSuccess, showError } = useToast();

  // 통계 로드
  useEffect(() => {
    if (showStatistics) {
      loadStatistics();
    }
  }, [showStatistics]);

  const loadStatistics = async () => {
    try {
      const stats = await conversationHistoryService.getStatistics(30);
      setStatistics(stats);
    } catch (error) {
      showError('통계를 불러오는데 실패했습니다.');
    }
  };

  const handleSelectConversation = (conversation: ConversationSummary) => {
    setSelectedConversationId(conversation.id);
  };

  const handleCreateNewConversation = async () => {
    try {
      const now = new Date();
      const defaultTitle = `새 대화 ${now.toLocaleDateString('ko-KR')} ${now.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })}`;

      const newConversation = await conversationHistoryService.createConversation({
        title: defaultTitle,
        description: '새로 생성된 대화입니다.'
      });

      setSelectedConversationId(newConversation.id);
      showSuccess('새 대화가 생성되었습니다.');
    } catch (error) {
      showError('새 대화 생성에 실패했습니다.');
    }
  };

  return (
    <div className={`h-screen flex flex-col bg-gray-50 dark:bg-gray-900 ${className}`}>
      {/* 헤더 */}
      <div className="h-16 px-6 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <History className="w-6 h-6 text-blue-600 dark:text-blue-400" />
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            대화 이력 관리
          </h1>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowStatistics(!showStatistics)}
            className={`
              flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors
              ${showStatistics 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }
            `}
          >
            <TrendingUp className="w-4 h-4 mr-2" />
            통계
          </button>
        </div>
      </div>

      {/* 통계 패널 */}
      {showStatistics && statistics && (
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {statistics.conversation_count}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">총 대화</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {statistics.message_count}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">총 메시지</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {statistics.active_days}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">활성 일수</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                {Math.round(statistics.avg_input_tokens).toLocaleString()}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">평균 입력 토큰</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                {Math.round(statistics.avg_output_tokens).toLocaleString()}
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">평균 출력 토큰</div>
            </div>
            
            <div className="text-center">
              <div className="text-2xl font-bold text-teal-600 dark:text-teal-400">
                {Math.round(statistics.avg_latency_ms)}ms
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">평균 응답시간</div>
            </div>
          </div>
          
          <div className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
            최근 {statistics.period_days}일간의 통계입니다
          </div>
        </div>
      )}

      {/* 메인 컨텐츠 영역 */}
      <div className="flex-1 min-h-0">
        <PanelGroup direction="horizontal">
          {/* 대화 목록 패널 */}
          <Panel 
            defaultSize={35} 
            minSize={25} 
            maxSize={50}
            className="border-r border-gray-200 dark:border-gray-700"
          >
            <ConversationList
              selectedConversationId={selectedConversationId}
              onSelectConversation={handleSelectConversation}
              onCreateNew={handleCreateNewConversation}
              className="h-full"
            />
          </Panel>

          {/* 리사이저 */}
          <PanelResizeHandle className="w-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors">
            <div className="w-full h-full flex items-center justify-center">
              <div className="w-0.5 h-8 bg-gray-400 dark:bg-gray-500 rounded-full"></div>
            </div>
          </PanelResizeHandle>

          {/* 대화 상세 패널 */}
          <Panel defaultSize={65} minSize={50}>
            {selectedConversationId ? (
              <ConversationDetailView
                conversationId={selectedConversationId}
                className="h-full"
              />
            ) : (
              <div className="h-full flex items-center justify-center bg-white dark:bg-gray-900">
                <div className="text-center text-gray-500 dark:text-gray-400">
                  <History className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <h3 className="text-lg font-medium mb-2">대화 이력을 확인하세요</h3>
                  <p className="text-sm">
                    왼쪽에서 대화를 선택하면 상세 내용을 볼 수 있습니다.
                  </p>
                  <button
                    onClick={handleCreateNewConversation}
                    className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                  >
                    새 대화 시작하기
                  </button>
                </div>
              </div>
            )}
          </Panel>
        </PanelGroup>
      </div>
    </div>
  );
};