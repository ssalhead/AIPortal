/**
 * 반응형 디자인을 위한 커스텀 훅
 */

import { useState, useEffect } from 'react';

export interface BreakpointConfig {
  sm: number;  // 640px
  md: number;  // 768px
  lg: number;  // 1024px
  xl: number;  // 1280px
  '2xl': number; // 1536px
}

const defaultBreakpoints: BreakpointConfig = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
};

export const useResponsive = (breakpoints: BreakpointConfig = defaultBreakpoints) => {
  const [windowSize, setWindowSize] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    height: typeof window !== 'undefined' ? window.innerHeight : 800,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleResize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const width = windowSize.width;

  return {
    // Window dimensions
    width: windowSize.width,
    height: windowSize.height,
    
    // Breakpoint checks
    isMobile: width < breakpoints.md,
    isTablet: width >= breakpoints.md && width < breakpoints.lg,
    isDesktop: width >= breakpoints.lg,
    isLargeScreen: width >= breakpoints.xl,
    
    // Specific breakpoint checks
    isSmall: width < breakpoints.sm,
    isMedium: width >= breakpoints.sm && width < breakpoints.md,
    isLarge: width >= breakpoints.md && width < breakpoints.lg,
    isExtraLarge: width >= breakpoints.lg && width < breakpoints.xl,
    is2XLarge: width >= breakpoints.xl && width < breakpoints['2xl'],
    is3XLarge: width >= breakpoints['2xl'],
    
    // Utility functions
    isAtLeast: (breakpoint: keyof BreakpointConfig) => width >= breakpoints[breakpoint],
    isAtMost: (breakpoint: keyof BreakpointConfig) => width <= breakpoints[breakpoint],
    isBetween: (min: keyof BreakpointConfig, max: keyof BreakpointConfig) => 
      width >= breakpoints[min] && width <= breakpoints[max],
  };
};

/**
 * 터치 디바이스 감지 훅
 */
export const useTouchDevice = () => {
  const [isTouchDevice, setIsTouchDevice] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const checkTouchDevice = () => {
      setIsTouchDevice(
        'ontouchstart' in window ||
        navigator.maxTouchPoints > 0 ||
        // @ts-ignore
        navigator.msMaxTouchPoints > 0
      );
    };

    checkTouchDevice();
  }, []);

  return isTouchDevice;
};

/**
 * CSS 미디어 쿼리 훅
 */
export const useMediaQuery = (query: string) => {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia(query);
    setMatches(mediaQuery.matches);

    const handler = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    // addEventListener가 지원되는 경우 사용, 아니면 addListener 사용
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handler);
      return () => mediaQuery.removeEventListener('change', handler);
    } else {
      // 구형 브라우저 지원
      mediaQuery.addListener(handler);
      return () => mediaQuery.removeListener(handler);
    }
  }, [query]);

  return matches;
};

/**
 * 다크 모드 감지 훅
 */
export const usePrefersDarkMode = () => {
  return useMediaQuery('(prefers-color-scheme: dark)');
};

/**
 * 사용자의 motion preference 확인
 */
export const usePrefersReducedMotion = () => {
  return useMediaQuery('(prefers-reduced-motion: reduce)');
};