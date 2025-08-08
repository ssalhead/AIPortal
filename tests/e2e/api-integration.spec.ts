import { test, expect } from '@playwright/test';

/**
 * API 통합 테스트 - E2E 테스트의 기반
 */
test.describe('API 통합 테스트', () => {
  
  test('백엔드 헬스체크 API', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/health');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data).toHaveProperty('status', 'healthy');
    expect(data).toHaveProperty('timestamp');
  });

  test('채팅 API - 기본 메시지 전송', async ({ request }) => {
    // Mock 인증을 사용한 메시지 전송
    const chatResponse = await request.post('http://localhost:8000/api/v1/chat/', {
      headers: {
        'Content-Type': 'application/json',
      },
      data: {
        message: 'Hello, this is a test message',
        model: 'claude-4',
        agent_type: 'none',
      }
    });
    
    expect(chatResponse.status()).toBe(200);
    
    const chatData = await chatResponse.json();
    expect(chatData).toHaveProperty('response');
    expect(chatData).toHaveProperty('agent_used');
    expect(chatData).toHaveProperty('model_used');
    expect(chatData).toHaveProperty('timestamp');
    expect(chatData).toHaveProperty('user_id');
  });

  test('채팅 API - 웹 검색 에이전트', async ({ request }) => {
    const searchResponse = await request.post('http://localhost:8000/api/v1/chat/', {
      headers: {
        'Content-Type': 'application/json',
      },
      data: {
        message: '최신 AI 뉴스를 검색해주세요',
        model: 'claude-4',
        agent_type: 'web_search',
      }
    });
    
    expect(searchResponse.status()).toBe(200);
    
    const searchData = await searchResponse.json();
    expect(searchData).toHaveProperty('response');
    expect(searchData.agent_used).toBe('web_search');
    expect(searchData).toHaveProperty('citations');
    expect(searchData).toHaveProperty('sources');
  });

  test('대화 세션 생성', async ({ request }) => {
    const sessionResponse = await request.post('http://localhost:8000/api/v1/chat/sessions/new', {
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    expect(sessionResponse.status()).toBe(200);
    
    const sessionData = await sessionResponse.json();
    expect(sessionData).toHaveProperty('session_id');
    expect(sessionData).toHaveProperty('created_at');
    expect(sessionData).toHaveProperty('title');
  });

  test('대화 히스토리 조회', async ({ request }) => {
    const historyResponse = await request.get('http://localhost:8000/api/v1/chat/history');
    
    expect(historyResponse.status()).toBe(200);
    
    const historyData = await historyResponse.json();
    expect(Array.isArray(historyData)).toBe(true);
  });

  test('사용자 세션 목록 조회', async ({ request }) => {
    const sessionsResponse = await request.get('http://localhost:8000/api/v1/chat/sessions');
    
    expect(sessionsResponse.status()).toBe(200);
    
    const sessionsData = await sessionsResponse.json();
    expect(Array.isArray(sessionsData)).toBe(true);
  });

  test('피드백 시스템 - Thumbs 피드백', async ({ request }) => {
    const feedbackResponse = await request.post('http://localhost:8000/api/v1/feedback/', {
      headers: {
        'Content-Type': 'application/json',
      },
      data: {
        message_id: 'test-message-123',
        feedback_type: 'thumbs',
        is_positive: true,
        category: 'overall'
      }
    });
    
    expect(feedbackResponse.status()).toBe(200);
    
    const feedbackData = await feedbackResponse.json();
    expect(feedbackData).toHaveProperty('id');
    expect(feedbackData).toHaveProperty('status', 'success');
  });

  test('피드백 시스템 - 별점 피드백', async ({ request }) => {
    const ratingResponse = await request.post('http://localhost:8000/api/v1/feedback/', {
      headers: {
        'Content-Type': 'application/json',
      },
      data: {
        message_id: 'test-message-456',
        feedback_type: 'rating',
        rating: 4.5,
        category: 'accuracy'
      }
    });
    
    expect(ratingResponse.status()).toBe(200);
    
    const ratingData = await ratingResponse.json();
    expect(ratingData).toHaveProperty('id');
    expect(ratingData).toHaveProperty('status', 'success');
  });

  test('피드백 시스템 - 상세 피드백', async ({ request }) => {
    const detailedResponse = await request.post('http://localhost:8000/api/v1/feedback/', {
      headers: {
        'Content-Type': 'application/json',
      },
      data: {
        message_id: 'test-message-789',
        feedback_type: 'detailed',
        title: '개선 제안',
        content: '응답이 더 구체적이었으면 좋겠습니다.',
        suggestions: '예시를 추가해주세요.',
        category: 'completeness',
        rating: 3.0
      }
    });
    
    expect(detailedResponse.status()).toBe(200);
    
    const detailedData = await detailedResponse.json();
    expect(detailedData).toHaveProperty('id');
    expect(detailedData).toHaveProperty('status', 'success');
  });

  test('Canvas 워크스페이스 API', async ({ request }) => {
    const canvasResponse = await request.post('http://localhost:8000/api/v1/chat/', {
      headers: {
        'Content-Type': 'application/json',
      },
      data: {
        message: 'Canvas 워크스페이스를 생성해주세요',
        model: 'claude-4',
        agent_type: 'canvas',
      }
    });
    
    expect(canvasResponse.status()).toBe(200);
    
    const canvasData = await canvasResponse.json();
    expect(canvasData).toHaveProperty('response');
    expect(canvasData.agent_used).toBe('canvas');
  });

  test('성능 메트릭 조회', async ({ request }) => {
    const metricsResponse = await request.get('http://localhost:8000/api/v1/performance/metrics');
    
    expect(metricsResponse.status()).toBe(200);
    
    const metricsData = await metricsResponse.json();
    expect(metricsData).toHaveProperty('metrics');
    expect(Array.isArray(metricsData.metrics)).toBe(true);
  });

  test('에러 처리 - 잘못된 모델', async ({ request }) => {
    const errorResponse = await request.post('http://localhost:8000/api/v1/chat/', {
      headers: {
        'Content-Type': 'application/json',
      },
      data: {
        message: 'Test message',
        model: 'invalid-model',
        agent_type: 'none',
      }
    });
    
    // 에러 응답 확인 (400 또는 422 예상)
    expect([400, 422]).toContain(errorResponse.status());
  });

  test('E2E 워크플로우 - 전체 채팅 세션', async ({ request }) => {
    // 1. 새 세션 생성
    const sessionResponse = await request.post('http://localhost:8000/api/v1/chat/sessions/new');
    expect(sessionResponse.status()).toBe(200);
    const session = await sessionResponse.json();
    
    // 2. 메시지 전송
    const messageResponse = await request.post('http://localhost:8000/api/v1/chat/', {
      data: {
        message: 'E2E 테스트 메시지입니다',
        model: 'claude-4',
        agent_type: 'none',
        session_id: session.session_id
      }
    });
    expect(messageResponse.status()).toBe(200);
    const message = await messageResponse.json();
    
    // 3. 피드백 제출
    const feedbackResponse = await request.post('http://localhost:8000/api/v1/feedback/', {
      data: {
        message_id: message.session_id + '-msg-1', // 실제 메시지 ID 구조에 맞게 조정
        feedback_type: 'thumbs',
        is_positive: true,
        category: 'overall'
      }
    });
    expect(feedbackResponse.status()).toBe(200);
    
    // 4. 히스토리 확인
    const historyResponse = await request.get(`http://localhost:8000/api/v1/chat/history?session_id=${session.session_id}`);
    expect(historyResponse.status()).toBe(200);
    
    // 5. 세션 종료
    const endResponse = await request.delete(`http://localhost:8000/api/v1/chat/sessions/${session.session_id}`);
    expect(endResponse.status()).toBe(200);
  });
});