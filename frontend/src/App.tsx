/**
 * AI 포탈 메인 애플리케이션
 */

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryProvider } from './contexts/QueryProvider';
import { AuthProvider } from './contexts/AuthContext';
import { LoadingProvider } from './contexts/LoadingContext';
import { Layout } from './components/layout/Layout';
import { ChatPage } from './pages/ChatPage';
import WorkspacePage from './pages/WorkspacePage';
import WorkspaceDetailPage from './pages/WorkspaceDetailPage';
import { SplitScreenLayout } from './components/layout/SplitScreenLayout';
import { ConversationHistoryPage } from './components/ConversationHistory/ConversationHistoryPage';

function App() {
  return (
    <QueryProvider>
      <AuthProvider>
        <LoadingProvider>
          <Router>
            <Layout>
              <Routes>
                <Route path="/" element={<ChatPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/workspace" element={<WorkspacePage />} />
                <Route path="/workspace/:workspaceId" element={<WorkspaceDetailPage />} />
                <Route path="/split" element={<SplitScreenLayout />} />
                <Route path="/split/:workspaceId" element={<SplitScreenLayout />} />
                <Route path="/history" element={<ConversationHistoryPage />} />
                {/* 추후 추가될 라우트들 */}
                {/* <Route path="/agents" element={<AgentsPage />} /> */}
              </Routes>
            </Layout>
          </Router>
        </LoadingProvider>
      </AuthProvider>
    </QueryProvider>
  );
}

export default App
