/**
 * 메인 레이아웃 컴포넌트
 */

import React from 'react';
import { Header } from './Header';
import { GlobalLoadingOverlay } from '../ui/GlobalLoadingOverlay';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="h-screen flex flex-col bg-gradient-to-b from-neutral-25 to-neutral-50">
      <Header />
      <main className="flex-1 relative overflow-hidden min-h-0">
        {children}
      </main>
      <GlobalLoadingOverlay />
    </div>
  );
};