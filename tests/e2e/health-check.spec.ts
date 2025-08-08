import { test, expect } from '@playwright/test';

/**
 * 기본 헬스체크 테스트 - 가장 간단한 E2E 확인
 */
test.describe('헬스체크 테스트', () => {
  
  test('백엔드 API 헬스체크', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/health/');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('status', 'healthy');
    expect(data).toHaveProperty('timestamp');
    expect(data).toHaveProperty('version');
    expect(data).toHaveProperty('environment', 'development');
    expect(data).toHaveProperty('project', 'AI Portal');
    expect(data).toHaveProperty('mock_auth_enabled', true);
  });

  test('프론트엔드 서버 접근', async ({ request }) => {
    const response = await request.get('http://localhost:5173/');
    expect(response.status()).toBe(200);
    
    const html = await response.text();
    expect(html).toContain('<div id="root">');
    expect(html).toContain('Vite + React + TS');
  });

  test('CORS 헤더 확인', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/health/', {
      headers: {
        'Origin': 'http://localhost:5173'
      }
    });
    
    expect(response.status()).toBe(200);
    // CORS 헤더가 적절히 설정되어 있는지 확인
    const headers = response.headers();
    expect(headers['access-control-allow-origin']).toBeDefined();
  });
});