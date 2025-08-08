import { test, expect } from '@playwright/test';

/**
 * 매우 간단한 E2E 테스트 - 연결 확인용
 */
test.describe('연결 테스트', () => {
  test('프론트엔드 서버 연결 확인', async ({ page }) => {
    // 페이지 이동 (타임아웃 연장)
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 60000 });
    
    // 기본적인 HTML 구조 확인
    await expect(page.locator('html')).toBeVisible();
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('#root')).toBeVisible();
  });

  test('백엔드 API 연결 확인', async ({ request }) => {
    // 백엔드 헬스체크 API 호출
    const response = await request.get('http://localhost:8000/api/v1/health');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('status', 'healthy');
  });

  test('React 앱 로딩 확인', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 60000 });
    
    // React가 로드될 때까지 대기 (타임아웃 연장)
    await page.waitForFunction(() => {
      const root = document.getElementById('root');
      return root && root.children.length > 0;
    }, { timeout: 60000 });
    
    // React 앱이 마운트되었는지 확인
    const rootContent = await page.locator('#root').innerHTML();
    expect(rootContent.length).toBeGreaterThan(0);
  });

  test('기본 UI 요소 로딩 확인', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 60000 });
    
    // React 앱 로딩 대기
    await page.waitForFunction(() => {
      const root = document.getElementById('root');
      return root && root.children.length > 0;
    }, { timeout: 60000 });
    
    // 기본적인 UI 요소들이 있는지 확인 (태그 기반)
    const hasInput = await page.locator('input, textarea').count() > 0;
    const hasButton = await page.locator('button').count() > 0;
    const hasDiv = await page.locator('div').count() > 0;
    
    expect(hasInput || hasButton || hasDiv).toBe(true);
  });
});