/**
 * AI 포탈 메인 애플리케이션
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryProvider } from './contexts/QueryProvider';
import { AuthProvider } from './contexts/AuthContext';
import { LoadingProvider } from './contexts/LoadingContext';
import { Layout } from './components/layout/Layout';
import { ChatPage } from './pages/ChatPage';

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
                {/* 추후 추가될 라우트들 */}
                {/* <Route path="/workspace" element={<WorkspacePage />} /> */}
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
