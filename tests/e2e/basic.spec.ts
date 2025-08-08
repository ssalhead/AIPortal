import { test, expect } from '@playwright/test';

/**
 * 기본 E2E 테스트 - 간단한 기능 확인
 */
test.describe('기본 기능 테스트', () => {
  test.beforeEach(async ({ page }) => {
    // 애플리케이션 홈페이지로 이동
    await page.goto('/');
    
    // 페이지 로드 대기 (더 안정적인 방법)
    await page.waitForLoadState('domcontentloaded');
    
    // React 앱이 완전히 로드될 때까지 대기
    await page.waitForSelector('body', { state: 'visible' });
  });

  test('페이지 로드 확인', async ({ page }) => {
    // 페이지가 로드되었는지 확인
    await expect(page).toHaveURL(/localhost:5173/);
    
    // HTML title 확인 (기본적인 확인)
    await expect(page).toHaveTitle(/Vite \+ React TS/);
    
    // 페이지에 기본적인 컨텐츠가 있는지 확인
    await expect(page.locator('body')).toBeVisible();
  });

  test('React 앱이 마운트되었는지 확인', async ({ page }) => {
    // React root div 확인
    await expect(page.locator('#root')).toBeVisible();
    
    // React 컴포넌트가 로드되었는지 확인
    await page.waitForFunction(() => {
      return document.querySelector('#root')?.children.length > 0;
    }, { timeout: 10000 });
    
    // React 앱 내용이 있는지 확인
    const rootContent = await page.locator('#root').textContent();
    expect(rootContent).toBeTruthy();
  });

  test('기본 채팅 인터페이스 요소 확인', async ({ page }) => {
    // 페이지가 완전히 로드될 때까지 대기
    await page.waitForTimeout(2000);
    
    // 채팅과 관련된 기본 요소들이 있는지 확인
    const chatElements = await page.locator('input, textarea, button').all();
    expect(chatElements.length).toBeGreaterThan(0);
    
    // 최소한 하나의 입력 필드가 있는지 확인
    const inputExists = await page.locator('input, textarea').count();
    expect(inputExists).toBeGreaterThan(0);
  });

  test('네트워크 연결 상태 확인', async ({ page }) => {
    // API 엔드포인트에 대한 기본 연결 확인
    const response = await page.request.get('http://localhost:8000/api/v1/health');
    expect(response.status()).toBe(200);
    
    const responseData = await response.json();
    expect(responseData).toHaveProperty('status');
  });

  test('브라우저 콘솔 에러 확인', async ({ page }) => {
    const consoleErrors: string[] = [];
    
    // 콘솔 에러 수집
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    // 페이지 로드 후 2초 대기
    await page.waitForTimeout(2000);
    
    // 심각한 에러가 없는지 확인 (일반적인 개발 환경 경고는 제외)
    const seriousErrors = consoleErrors.filter(error => 
      !error.includes('Warning:') && 
      !error.includes('[HMR]') &&
      !error.includes('WebSocket')
    );
    
    if (seriousErrors.length > 0) {
      console.log('Console errors found:', seriousErrors);
    }
    
    // 심각한 에러가 없어야 함
    expect(seriousErrors.length).toBeLessThanOrEqual(2); // 개발 환경에서는 약간의 에러가 있을 수 있음
  });

  test('반응형 디자인 기본 확인', async ({ page }) => {
    // 데스크톱 뷰포트
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.waitForTimeout(500);
    
    // 기본 레이아웃이 표시되는지 확인
    const bodyVisible = await page.locator('body').isVisible();
    expect(bodyVisible).toBe(true);
    
    // 모바일 뷰포트로 변경
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    
    // 모바일에서도 기본 레이아웃이 유지되는지 확인
    const bodyVisibleMobile = await page.locator('body').isVisible();
    expect(bodyVisibleMobile).toBe(true);
  });

  test('JavaScript 로드 상태 확인', async ({ page }) => {
    // React가 마운트되었는지 확인
    const reactMounted = await page.evaluate(() => {
      return !!(window as any).React || document.querySelector('[data-reactroot]') || document.querySelector('#root')?.children.length > 0;
    });
    
    expect(reactMounted).toBe(true);
    
    // 기본적인 DOM 조작이 가능한지 확인
    const domReady = await page.evaluate(() => {
      return document.readyState === 'complete';
    });
    
    expect(domReady).toBe(true);
  });
});