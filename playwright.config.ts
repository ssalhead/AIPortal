import { defineConfig, devices } from '@playwright/test';

/**
 * E2E 테스트 설정
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',
  /* 병렬 실행 설정 */
  fullyParallel: false,
  /* CI에서 실패한 테스트 재시도 안함 */
  forbidOnly: !!process.env.CI,
  /* CI에서만 재시도 */
  retries: process.env.CI ? 2 : 0,
  /* 병렬 실행할 워커 수 */
  workers: 1,
  /* 리포터 설정 */
  reporter: 'line',
  /* 모든 테스트의 글로벌 설정 */
  use: {
    /* Base URL for e2e tests */
    baseURL: 'http://localhost:5173',
    
    /* 스크린샷 및 비디오 캡처 */
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
    /* 헤드리스 모드 */
    headless: true,
    
    /* 뷰포트 설정 */
    viewport: { width: 1280, height: 720 },
    
    /* 브라우저 컨텍스트 설정 */
    ignoreHTTPSErrors: true,
  },

  /* 수동으로 서버 실행 중이므로 webServer 설정 비활성화 */

  /* 테스트 타임아웃 설정 */
  timeout: 30 * 1000, // 30초
  expect: {
    timeout: 10 * 1000, // 10초
  },
});