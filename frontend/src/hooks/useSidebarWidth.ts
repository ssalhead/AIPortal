/**
 * 사이드바 너비 계산 유틸리티 훅
 */

import { useCallback } from 'react';
import { SIDEBAR_WIDTHS } from '../constants/layout';

export const useSidebarWidth = () => {
  const getSidebarWidth = useCallback((isOpen: boolean, isMobile: boolean) => {
    if (isMobile) return 0;
    return isOpen ? SIDEBAR_WIDTHS.EXPANDED : SIDEBAR_WIDTHS.COLLAPSED;
  }, []);

  const getMainContentMargin = useCallback((isOpen: boolean, isMobile: boolean) => {
    const sidebarWidth = getSidebarWidth(isOpen, isMobile);
    return isMobile ? 0 : sidebarWidth;
  }, [getSidebarWidth]);

  const getContainerWidth = useCallback((
    containerRef: React.RefObject<HTMLDivElement | null>, 
    isOpen: boolean, 
    isMobile: boolean
  ) => {
    if (!containerRef.current) return 800; // 기본값
    // absolute 포지셔닝으로 사이드바가 변경되어 전체 너비 사용 가능
    return containerRef.current.offsetWidth;
  }, []);

  return {
    getSidebarWidth,
    getMainContentMargin,
    getContainerWidth,
  };
};