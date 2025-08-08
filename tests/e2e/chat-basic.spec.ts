import { test, expect } from '@playwright/test';

/**
 * 기본 채팅 플로우 E2E 테스트
 */
test.describe('기본 채팅 기능', () => {
  test.beforeEach(async ({ page }) => {
    // 애플리케이션 홈페이지로 이동
    await page.goto('/');
    
    // 페이지 로드 대기
    await page.waitForLoadState('networkidle');
  });

  test('페이지 로드 및 기본 UI 요소 확인', async ({ page }) => {
    // 페이지 제목 확인
    await expect(page).toHaveTitle(/AI Portal/);
    
    // 주요 UI 요소들이 표시되는지 확인
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('[data-testid="chat-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="model-selector"]')).toBeVisible();
    await expect(page.locator('[data-testid="agent-selector"]')).toBeVisible();
  });

  test('메시지 전송 및 응답 받기', async ({ page }) => {
    const testMessage = '안녕하세요. 테스트 메시지입니다.';
    
    // 채팅 입력 필드에 메시지 입력
    const chatInput = page.locator('[data-testid="chat-input"]');
    await chatInput.fill(testMessage);
    
    // 전송 버튼 클릭
    const sendButton = page.locator('[data-testid="send-button"]');
    await sendButton.click();
    
    // 메시지가 채팅 영역에 표시되는지 확인
    await expect(page.locator('[data-testid="user-message"]').last()).toContainText(testMessage);
    
    // AI 응답 대기 (최대 30초)
    await expect(page.locator('[data-testid="ai-message"]').last()).toBeVisible({ timeout: 30000 });
    
    // 채팅 입력 필드가 비워졌는지 확인
    await expect(chatInput).toHaveValue('');
  });

  test('모델 선택 기능', async ({ page }) => {
    // 모델 선택기 클릭
    const modelSelector = page.locator('[data-testid="model-selector"]');
    await modelSelector.click();
    
    // 모델 옵션들이 표시되는지 확인
    await expect(page.locator('[data-testid="model-option"]')).toHaveCount(8); // 8개 모델
    
    // Gemini 모델 선택
    await page.locator('[data-testid="model-option"][data-value="gemini-1.5-pro"]').click();
    
    // 선택된 모델이 표시되는지 확인
    await expect(modelSelector).toContainText('Gemini 1.5 Pro');
  });

  test('에이전트 선택 기능', async ({ page }) => {
    // 에이전트 선택기 클릭
    const agentSelector = page.locator('[data-testid="agent-selector"]');
    await agentSelector.click();
    
    // 에이전트 옵션들이 표시되는지 확인
    const agentOptions = [
      'none',           // 일반 채팅
      'web_search',     // 웹 검색
      'research',       // 리서치
      'canvas'          // Canvas
    ];
    
    for (const agent of agentOptions) {
      await expect(page.locator(`[data-testid="agent-option"][data-value="${agent}"]`)).toBeVisible();
    }
    
    // 웹 검색 에이전트 선택
    await page.locator('[data-testid="agent-option"][data-value="web_search"]').click();
    
    // 선택된 에이전트가 표시되는지 확인
    await expect(agentSelector).toContainText('웹 검색');
  });

  test('채팅 히스토리 사이드바', async ({ page }) => {
    // 사이드바가 기본으로 열려있는지 확인 (데스크톱)
    const sidebar = page.locator('[data-testid="sidebar"]');
    await expect(sidebar).toBeVisible();
    
    // 새 대화 버튼 확인
    const newChatButton = page.locator('[data-testid="new-chat-button"]');
    await expect(newChatButton).toBeVisible();
    
    // 새 대화 시작
    await newChatButton.click();
    
    // 채팅 영역이 비워졌는지 확인
    await expect(page.locator('[data-testid="chat-messages"]')).toBeEmpty();
  });

  test('반응형 디자인 - 모바일 뷰', async ({ page }) => {
    // 모바일 뷰포트로 변경
    await page.setViewportSize({ width: 375, height: 667 });
    
    // 모바일 헤더가 표시되는지 확인
    const mobileHeader = page.locator('[data-testid="mobile-header"]');
    await expect(mobileHeader).toBeVisible();
    
    // 사이드바가 숨겨져 있는지 확인
    const sidebar = page.locator('[data-testid="sidebar"]');
    await expect(sidebar).not.toBeVisible();
    
    // 메뉴 버튼 클릭하여 사이드바 열기
    const menuButton = page.locator('[data-testid="menu-button"]');
    await menuButton.click();
    
    // 사이드바 오버레이가 표시되는지 확인
    await expect(sidebar).toBeVisible();
    
    // 오버레이 클릭하여 사이드바 닫기
    const overlay = page.locator('[data-testid="sidebar-overlay"]');
    await overlay.click();
    
    // 사이드바가 다시 숨겨지는지 확인
    await expect(sidebar).not.toBeVisible();
  });

  test('로딩 상태 표시', async ({ page }) => {
    const testMessage = '테스트 메시지';
    
    // 메시지 전송
    await page.locator('[data-testid="chat-input"]').fill(testMessage);
    await page.locator('[data-testid="send-button"]').click();
    
    // 로딩 인디케이터가 표시되는지 확인
    await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible();
    
    // 응답 완료 후 로딩 인디케이터가 사라지는지 확인
    await expect(page.locator('[data-testid="ai-message"]').last()).toBeVisible({ timeout: 30000 });
    await expect(page.locator('[data-testid="typing-indicator"]')).not.toBeVisible();
  });

  test('에러 처리', async ({ page }) => {
    // 네트워크 요청을 실패하도록 설정
    await page.route('**/api/v1/chat/**', route => route.abort());
    
    // 메시지 전송
    await page.locator('[data-testid="chat-input"]').fill('테스트 메시지');
    await page.locator('[data-testid="send-button"]').click();
    
    // 에러 메시지가 표시되는지 확인
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible({ timeout: 10000 });
    
    // 에러 내용 확인
    await expect(page.locator('[data-testid="error-message"]')).toContainText('오류');
  });
});