/**
 * WebSocket 연결 및 실시간 채팅을 위한 커스텀 훅
 */

import { useState, useRef, useCallback, useEffect } from 'react';

export interface WebSocketMessage {
  type: 'chat' | 'ping' | 'connection' | 'error';
  content?: string;
  model?: string;
  agent_type?: string;
  metadata?: Record<string, any>;
}

export interface WebSocketResponse {
  type: 'connection' | 'message_received' | 'assistant_start' | 'assistant_chunk' | 
        'assistant_end' | 'pong' | 'error';
  content?: string;
  message_id?: string;
  conversation_id?: string;
  timestamp?: string;
  message?: string;
}

interface UseWebSocketOptions {
  conversationId?: string;
  userId?: string;
  onMessage?: (response: WebSocketResponse) => void;
  onError?: (error: Event) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  isConnecting: boolean;
  currentMessage: string;
  isTyping: boolean;
  connect: () => void;
  disconnect: () => void;
  sendMessage: (message: WebSocketMessage) => void;
  sendPing: () => void;
  error: string | null;
}

export const useWebSocket = (options: UseWebSocketOptions = {}): UseWebSocketReturn => {
  const {
    conversationId = `conv-${Date.now()}`,
    userId = 'default_user',
    onMessage,
    onError,
    onConnect,
    onDisconnect
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const wsUrl = `ws://localhost:8000/api/v1/ws/chat/${conversationId}?user_id=${userId}`;

  const connect = useCallback(() => {
    if (isConnecting || isConnected) return;

    setIsConnecting(true);
    setError(null);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket 연결 성공');
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
        reconnectAttempts.current = 0;
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const response: WebSocketResponse = JSON.parse(event.data);
          console.log('WebSocket 메시지 수신:', response);

          // 메시지 타입별 처리
          switch (response.type) {
            case 'connection':
              console.log(`연결 확인: ${response.conversation_id}`);
              break;

            case 'message_received':
              console.log(`메시지 수신 확인: ${response.message_id}`);
              break;

            case 'assistant_start':
              setIsTyping(true);
              setCurrentMessage('');
              break;

            case 'assistant_chunk':
              if (response.content) {
                setCurrentMessage(prev => prev + response.content);
              }
              break;

            case 'assistant_end':
              setIsTyping(false);
              console.log(`응답 완료: ${response.message_id}`);
              break;

            case 'pong':
              console.log('Pong 응답 수신');
              break;

            case 'error':
              console.error('서버 오류:', response.message);
              setError(response.message || '서버에서 오류가 발생했습니다.');
              break;
          }

          onMessage?.(response);
        } catch (err) {
          console.error('메시지 파싱 오류:', err);
          setError('메시지 파싱 중 오류가 발생했습니다.');
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket 오류:', error);
        setError('연결 중 오류가 발생했습니다.');
        setIsConnecting(false);
        onError?.(error);
      };

      ws.onclose = (event) => {
        console.log('WebSocket 연결 종료:', event.code, event.reason);
        setIsConnected(false);
        setIsConnecting(false);
        setIsTyping(false);
        wsRef.current = null;
        onDisconnect?.();

        // 자동 재연결 (정상 종료가 아닌 경우)
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.pow(2, reconnectAttempts.current) * 1000; // 지수 백오프
          console.log(`${delay}ms 후 재연결 시도... (${reconnectAttempts.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setError('연결을 복구할 수 없습니다. 페이지를 새로고침해주세요.');
        }
      };

    } catch (err) {
      console.error('WebSocket 생성 오류:', err);
      setError('WebSocket 연결을 생성할 수 없습니다.');
      setIsConnecting(false);
    }
  }, [wsUrl, isConnecting, isConnected, onConnect, onMessage, onError, onDisconnect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
    setIsTyping(false);
    setCurrentMessage('');
    setError(null);
    reconnectAttempts.current = 0;
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('WebSocket이 연결되지 않았습니다.');
      return;
    }

    try {
      wsRef.current.send(JSON.stringify(message));
      console.log('메시지 전송:', message);
    } catch (err) {
      console.error('메시지 전송 오류:', err);
      setError('메시지 전송 중 오류가 발생했습니다.');
    }
  }, []);

  const sendPing = useCallback(() => {
    sendMessage({ type: 'ping' });
  }, [sendMessage]);

  // 컴포넌트 언마운트 시 연결 해제
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // 페이지 가시성 변경 시 처리 (선택사항)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // 페이지가 숨겨짐 - 연결 유지하지만 핑 중단
        console.log('페이지 숨김 - 연결 유지');
      } else {
        // 페이지가 다시 보임 - 연결 상태 확인
        console.log('페이지 활성화 - 연결 상태 확인');
        if (!isConnected && !isConnecting) {
          connect();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isConnected, isConnecting, connect]);

  return {
    isConnected,
    isConnecting,
    currentMessage,
    isTyping,
    connect,
    disconnect,
    sendMessage,
    sendPing,
    error
  };
};