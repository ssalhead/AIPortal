/**
 * 레이아웃 관련 상수 정의
 */

export const SIDEBAR_WIDTHS = {
  EXPANDED: 256, // w-64 (16rem * 16px = 256px)
  COLLAPSED: 64, // w-16 (4rem * 16px = 64px)
} as const;

export const BREAKPOINTS = {
  MOBILE: 768, // md breakpoint
} as const;

export const CANVAS_SPLIT = {
  MIN_CHAT_WIDTH: 30, // 채팅 영역 최소 30%
  MAX_CHAT_WIDTH: 80, // 채팅 영역 최대 80%
  DEFAULT_CHAT_WIDTH: 70, // 기본 7:3 비율
} as const;