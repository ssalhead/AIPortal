import { test, expect } from '@playwright/test';

/**
 * 고급 채팅 기능 E2E 테스트
 */
test.describe('고급 채팅 기능', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('웹 검색 에이전트 기능', async ({ page }) => {
    // 웹 검색 에이전트 선택
    await page.locator('[data-testid="agent-selector"]').click();
    await page.locator('[data-testid="agent-option"][data-value="web_search"]').click();
    
    // 검색 쿼리 전송
    const searchQuery = '최신 AI 뉴스';
    await page.locator('[data-testid="chat-input"]').fill(searchQuery);
    await page.locator('[data-testid="send-button"]').click();
    
    // 검색 진행 상태 표시 확인
    await expect(page.locator('[data-testid="search-progress"]')).toBeVisible({ timeout: 5000 });
    
    // 검색 결과가 포함된 응답 확인
    const aiMessage = page.locator('[data-testid="ai-message"]').last();
    await expect(aiMessage).toBeVisible({ timeout: 60000 });
    
    // 인용(Citation) 정보 확인
    await expect(page.locator('[data-testid="citations"]')).toBeVisible();
    await expect(page.locator('[data-testid="citation-item"]')).toHaveCount.greaterThan(0);
  });

  test('Canvas 워크스페이스 기능', async ({ page }) => {
    // Canvas 에이전트 선택
    await page.locator('[data-testid="agent-selector"]').click();
    await page.locator('[data-testid="agent-option"][data-value="canvas"]').click();
    
    // Canvas 요청 메시지 전송
    const canvasRequest = '간단한 프로젝트 계획을 마인드맵으로 만들어 주세요';
    await page.locator('[data-testid="chat-input"]').fill(canvasRequest);
    await page.locator('[data-testid="send-button"]').click();
    
    // Canvas 워크스페이스가 열리는지 확인
    await expect(page.locator('[data-testid="canvas-workspace"]')).toBeVisible({ timeout: 30000 });
    
    // Canvas 도구들이 표시되는지 확인
    await expect(page.locator('[data-testid="canvas-tools"]')).toBeVisible();
    await expect(page.locator('[data-testid="text-note-tool"]')).toBeVisible();
    await expect(page.locator('[data-testid="image-tool"]')).toBeVisible();
    await expect(page.locator('[data-testid="mindmap-tool"]')).toBeVisible();
  });

  test('Canvas - 텍스트 노트 편집', async ({ page }) => {
    // Canvas 에이전트로 전환
    await page.locator('[data-testid="agent-selector"]').click();
    await page.locator('[data-testid="agent-option"][data-value="canvas"]').click();
    
    // 텍스트 노트 요청
    await page.locator('[data-testid="chat-input"]').fill('텍스트 노트를 만들어 주세요');
    await page.locator('[data-testid="send-button"]').click();
    
    // Canvas가 열릴 때까지 대기
    await expect(page.locator('[data-testid="canvas-workspace"]')).toBeVisible({ timeout: 30000 });
    
    // 텍스트 노트 도구 선택
    await page.locator('[data-testid="text-note-tool"]').click();
    
    // 텍스트 편집기가 활성화되는지 확인
    await expect(page.locator('[data-testid="text-editor"]')).toBeVisible();
    
    // 텍스트 입력 및 편집
    const testText = '# 테스트 제목\n\n이것은 테스트 내용입니다.';
    await page.locator('[data-testid="text-editor"] textarea').fill(testText);
    
    // 변경사항이 반영되는지 확인
    await expect(page.locator('[data-testid="text-preview"]')).toContainText('테스트 제목');
    await expect(page.locator('[data-testid="text-preview"]')).toContainText('테스트 내용');
  });

  test('Canvas - 이미지 생성', async ({ page }) => {
    // Canvas 활성화
    await page.locator('[data-testid="agent-selector"]').click();
    await page.locator('[data-testid="agent-option"][data-value="canvas"]').click();
    
    await page.locator('[data-testid="chat-input"]').fill('이미지를 생성해 주세요');
    await page.locator('[data-testid="send-button"]').click();
    
    await expect(page.locator('[data-testid="canvas-workspace"]')).toBeVisible({ timeout: 30000 });
    
    // 이미지 생성 도구 선택
    await page.locator('[data-testid="image-tool"]').click();
    
    // 이미지 생성 패널이 열리는지 확인
    await expect(page.locator('[data-testid="image-generator"]')).toBeVisible();
    
    // 프롬프트 입력
    const imagePrompt = '아름다운 일몰 풍경';
    await page.locator('[data-testid="image-prompt"]').fill(imagePrompt);
    
    // 스타일 선택
    await page.locator('[data-testid="style-selector"]').click();
    await page.locator('[data-testid="style-option"][data-value="realistic"]').click();
    
    // 이미지 생성 버튼 클릭
    await page.locator('[data-testid="generate-image-button"]').click();
    
    // 로딩 상태 확인
    await expect(page.locator('[data-testid="image-generation-loading"]')).toBeVisible();
    
    // 생성된 이미지 확인 (시간이 걸릴 수 있음)
    await expect(page.locator('[data-testid="generated-image"]')).toBeVisible({ timeout: 60000 });
  });

  test('Canvas - 마인드맵 편집', async ({ page }) => {
    // Canvas 활성화
    await page.locator('[data-testid="agent-selector"]').click();
    await page.locator('[data-testid="agent-option"][data-value="canvas"]').click();
    
    await page.locator('[data-testid="chat-input"]').fill('마인드맵을 만들어 주세요');
    await page.locator('[data-testid="send-button"]').click();
    
    await expect(page.locator('[data-testid="canvas-workspace"]')).toBeVisible({ timeout: 30000 });
    
    // 마인드맵 도구 선택
    await page.locator('[data-testid="mindmap-tool"]').click();
    
    // 마인드맵 편집기가 활성화되는지 확인
    await expect(page.locator('[data-testid="mindmap-editor"]')).toBeVisible();
    
    // 중앙 노드가 있는지 확인
    await expect(page.locator('[data-testid="mindmap-root-node"]')).toBeVisible();
    
    // 새 노드 추가 버튼 클릭
    await page.locator('[data-testid="add-node-button"]').click();
    
    // 새 노드가 생성되었는지 확인
    await expect(page.locator('[data-testid="mindmap-node"]')).toHaveCount.greaterThan(1);
    
    // 노드 텍스트 편집
    const newNode = page.locator('[data-testid="mindmap-node"]').last();
    await newNode.dblclick();
    
    // 편집 모드가 활성화되는지 확인
    await expect(page.locator('[data-testid="node-text-input"]')).toBeVisible();
    
    // 텍스트 입력
    await page.locator('[data-testid="node-text-input"]').fill('새 아이디어');
    await page.locator('[data-testid="node-text-input"]').press('Enter');
    
    // 노드 텍스트가 업데이트되었는지 확인
    await expect(newNode).toContainText('새 아이디어');
  });

  test('실시간 스트리밍 응답', async ({ page }) => {
    // 스트리밍 모드 활성화 (설정에서)
    const longQuery = '인공지능의 발전 역사와 미래 전망에 대해 자세히 설명해 주세요.';
    
    await page.locator('[data-testid="chat-input"]').fill(longQuery);
    await page.locator('[data-testid="send-button"]').click();
    
    // 타이핑 인디케이터 확인
    await expect(page.locator('[data-testid="typing-indicator"]')).toBeVisible();
    
    // 점진적으로 텍스트가 나타나는지 확인 (스트리밍)
    const aiMessage = page.locator('[data-testid="ai-message"]').last();
    await expect(aiMessage).toBeVisible({ timeout: 10000 });
    
    // 일정 시간 후 더 많은 내용이 추가되는지 확인
    await page.waitForTimeout(2000);
    const initialLength = await aiMessage.textContent();
    
    await page.waitForTimeout(3000);
    const updatedLength = await aiMessage.textContent();
    
    // 스트리밍으로 텍스트가 증가했는지 확인
    expect(updatedLength!.length).toBeGreaterThan(initialLength!.length);
  });

  test('인용 정보 상세보기', async ({ page }) => {
    // 웹 검색 에이전트로 검색 수행
    await page.locator('[data-testid="agent-selector"]').click();
    await page.locator('[data-testid="agent-option"][data-value="web_search"]').click();
    
    await page.locator('[data-testid="chat-input"]').fill('최신 기술 동향');
    await page.locator('[data-testid="send-button"]').click();
    
    // 응답 및 인용 정보 대기
    await expect(page.locator('[data-testid="citations"]')).toBeVisible({ timeout: 60000 });
    
    // 첫 번째 인용 클릭
    const firstCitation = page.locator('[data-testid="citation-item"]').first();
    await firstCitation.click();
    
    // 인용 상세 정보가 표시되는지 확인
    await expect(page.locator('[data-testid="citation-detail"]')).toBeVisible();
    await expect(page.locator('[data-testid="citation-source-url"]')).toBeVisible();
    await expect(page.locator('[data-testid="citation-snippet"]')).toBeVisible();
    
    // 출처 링크 클릭 (새 탭에서 열림)
    const [newPage] = await Promise.all([
      page.context().waitForEvent('page'),
      page.locator('[data-testid="citation-source-url"]').click()
    ]);
    
    // 새 탭이 열렸는지 확인
    expect(newPage.url()).toBeTruthy();
    await newPage.close();
  });

  test('다중 세션 관리', async ({ page }) => {
    // 첫 번째 메시지 전송
    await page.locator('[data-testid="chat-input"]').fill('첫 번째 질문입니다');
    await page.locator('[data-testid="send-button"]').click();
    await expect(page.locator('[data-testid="ai-message"]').last()).toBeVisible({ timeout: 30000 });
    
    // 새 대화 시작
    await page.locator('[data-testid="new-chat-button"]').click();
    
    // 채팅 영역이 비워졌는지 확인
    await expect(page.locator('[data-testid="chat-messages"]')).toBeEmpty();
    
    // 두 번째 메시지 전송
    await page.locator('[data-testid="chat-input"]').fill('두 번째 대화입니다');
    await page.locator('[data-testid="send-button"]').click();
    await expect(page.locator('[data-testid="ai-message"]').last()).toBeVisible({ timeout: 30000 });
    
    // 사이드바에 두 개의 대화 세션이 있는지 확인
    await expect(page.locator('[data-testid="conversation-item"]')).toHaveCount(2);
    
    // 첫 번째 대화로 돌아가기
    await page.locator('[data-testid="conversation-item"]').first().click();
    
    // 첫 번째 대화 내용이 복원되었는지 확인
    await expect(page.locator('[data-testid="user-message"]')).toContainText('첫 번째 질문');
  });

  test('피드백 시스템', async ({ page }) => {
    // 메시지 전송하고 응답 받기
    await page.locator('[data-testid="chat-input"]').fill('테스트 메시지');
    await page.locator('[data-testid="send-button"]').click();
    await expect(page.locator('[data-testid="ai-message"]').last()).toBeVisible({ timeout: 30000 });
    
    // 마지막 AI 메시지에 대한 피드백 버튼 확인
    const lastMessage = page.locator('[data-testid="ai-message"]').last();
    await expect(lastMessage.locator('[data-testid="thumbs-up"]')).toBeVisible();
    await expect(lastMessage.locator('[data-testid="thumbs-down"]')).toBeVisible();
    
    // 좋아요 클릭
    await lastMessage.locator('[data-testid="thumbs-up"]').click();
    
    // 피드백이 등록되었는지 확인 (버튼 상태 변경)
    await expect(lastMessage.locator('[data-testid="thumbs-up"]')).toHaveClass(/active/);
    
    // 상세 피드백 모달 열기
    await lastMessage.locator('[data-testid="feedback-detail"]').click();
    await expect(page.locator('[data-testid="feedback-modal"]')).toBeVisible();
    
    // 별점 평가
    await page.locator('[data-testid="rating-star-4"]').click();
    
    // 상세 피드백 입력
    await page.locator('[data-testid="feedback-text"]').fill('응답이 매우 도움이 되었습니다.');
    
    // 피드백 제출
    await page.locator('[data-testid="submit-feedback"]').click();
    
    // 모달이 닫히고 성공 메시지 표시
    await expect(page.locator('[data-testid="feedback-modal"]')).not.toBeVisible();
    await expect(page.locator('[data-testid="feedback-success"]')).toBeVisible();
  });
});