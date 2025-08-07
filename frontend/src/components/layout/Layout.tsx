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
    <div className="min-h-screen bg-gradient-to-b from-neutral-25 to-neutral-50">
      <Header />
      <main className="flex-1 relative">
        {children}
      </main>
      <GlobalLoadingOverlay />
    </div>
  );
};