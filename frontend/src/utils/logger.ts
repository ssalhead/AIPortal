/**
 * 환경 기반 로깅 유틸리티
 * 개발/프로덕션 환경에 따라 로그 레벨을 제어합니다.
 */

export enum LogLevel {
  ERROR = 0,
  WARN = 1,
  INFO = 2,
  DEBUG = 3,
}

interface LogContext {
  component?: string;
  action?: string;
  userId?: string;
  sessionId?: string;
  [key: string]: unknown;
}

class Logger {
  private isDevelopment: boolean;
  private logLevel: LogLevel;

  constructor() {
    this.isDevelopment = import.meta.env.DEV;
    this.logLevel = this.isDevelopment ? LogLevel.DEBUG : LogLevel.WARN;
  }

  private shouldLog(level: LogLevel): boolean {
    return level <= this.logLevel;
  }

  private formatMessage(level: string, message: string, context?: LogContext): string {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level}]`;
    
    if (context) {
      const contextStr = Object.entries(context)
        .map(([key, value]) => `${key}=${value}`)
        .join(' ');
      return `${prefix} ${message} | ${contextStr}`;
    }
    
    return `${prefix} ${message}`;
  }

  error(message: string, error?: Error, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.ERROR)) return;

    const formattedMessage = this.formatMessage('ERROR', message, context);
    console.error(formattedMessage);
    
    if (error) {
      console.error('Error details:', error);
    }

    // 프로덕션에서는 에러 리포팅 서비스로 전송 (향후 확장)
    if (!this.isDevelopment) {
      this.reportError(message, error, context);
    }
  }

  warn(message: string, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.WARN)) return;
    const formattedMessage = this.formatMessage('WARN', message, context);
    console.warn(formattedMessage);
  }

  info(message: string, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.INFO)) return;
    const formattedMessage = this.formatMessage('INFO', message, context);
    console.info(formattedMessage);
  }

  debug(message: string, data?: unknown, context?: LogContext): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;
    
    const formattedMessage = this.formatMessage('DEBUG', message, context);
    console.log(formattedMessage);
    
    if (data !== undefined) {
      console.log('Debug data:', data);
    }
  }

  // 성능 크리티컬 영역용 조건부 디버깅
  debugPerformance(message: string, data?: unknown, context?: LogContext): void {
    // 성능 로깅은 더 엄격한 조건으로만 출력
    if (!this.isDevelopment || !import.meta.env.VITE_DEBUG_PERFORMANCE) {
      return;
    }
    this.debug(`[PERF] ${message}`, data, context);
  }

  // API 호출 전용 로깅
  apiCall(method: string, url: string, context?: LogContext): void {
    if (!this.isDevelopment || !import.meta.env.VITE_DEBUG_API) {
      return;
    }
    this.debug(`API ${method.toUpperCase()} ${url}`, undefined, {
      ...context,
      type: 'api_call'
    });
  }

  // 스트리밍 전용 로깅 (빈도 제어)
  streaming(message: string, data?: unknown, context?: LogContext): void {
    // 스트리밍 로그는 매우 제한적으로만 출력
    if (!this.isDevelopment || !import.meta.env.VITE_DEBUG_STREAMING) {
      return;
    }
    
    // 랜덤 샘플링으로 로그 빈도 50% 감소
    if (Math.random() > 0.5) {
      return;
    }
    
    this.debug(`[STREAM] ${message}`, data, context);
  }

  private reportError(message: string, error?: Error, context?: LogContext): void {
    // 향후 Sentry, LogRocket 등 에러 리포팅 서비스 연동
    // 현재는 localStorage에 에러 로그 저장
    try {
      const errorLog = {
        timestamp: new Date().toISOString(),
        message,
        error: error?.message,
        stack: error?.stack,
        context,
        url: window.location.href,
        userAgent: navigator.userAgent
      };

      const existingLogs = JSON.parse(localStorage.getItem('error_logs') || '[]');
      existingLogs.push(errorLog);
      
      // 최대 50개 에러 로그만 보관
      if (existingLogs.length > 50) {
        existingLogs.splice(0, existingLogs.length - 50);
      }
      
      localStorage.setItem('error_logs', JSON.stringify(existingLogs));
    } catch (e) {
      // localStorage 저장 실패 시 무시
    }
  }

  // 개발자 도구에서 에러 로그 조회용
  getErrorLogs(): Array<Record<string, unknown>> {
    try {
      return JSON.parse(localStorage.getItem('error_logs') || '[]');
    } catch {
      return [];
    }
  }

  clearErrorLogs(): void {
    localStorage.removeItem('error_logs');
  }
}

// 싱글톤 인스턴스 생성
export const logger = new Logger();

// 개발자 도구에서 접근 가능하도록 전역 등록
if (typeof window !== 'undefined') {
  (window as Record<string, unknown>).__logger = logger;
}

// 기존 console.log를 점진적으로 교체하기 위한 헬퍼 함수들
export const loggers = {
  // 에러 처리용
  error: (message: string, error?: Error, component?: string) => 
    logger.error(message, error, { component }),
  
  // 경고용
  warn: (message: string, component?: string) => 
    logger.warn(message, { component }),
  
  // 일반 정보용
  info: (message: string, component?: string) => 
    logger.info(message, { component }),
  
  // API 호출용
  api: (method: string, url: string, component?: string) => 
    logger.apiCall(method, url, { component }),
  
  // 스트리밍용 (빈도 제어됨)
  stream: (message: string, data?: unknown, component?: string) => 
    logger.streaming(message, data, { component }),
  
  // 성능 디버깅용
  perf: (message: string, data?: unknown, component?: string) => 
    logger.debugPerformance(message, data, { component }),
  
  // 개발 디버깅용
  debug: (message: string, data?: unknown, component?: string) => 
    logger.debug(message, data, { component })
};