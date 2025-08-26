/**
 * Canvas 자동 저장 시스템 (v4.0)
 * 사용자 액션 기반 스마트 자동 저장
 */

import type { CanvasItem, CanvasToolType } from '../types/canvas';
import { CanvasShareStrategy } from './CanvasShareStrategy';

interface AutoSaveSession {
  canvasId: string;
  canvasType: CanvasToolType;
  conversationId: string;
  lastSaveTime: number;
  isDirty: boolean;
  saveIntervalId?: NodeJS.Timeout;
  debounceTimeoutId?: NodeJS.Timeout;
  changeCount: number;
}

export interface AutoSaveOptions {
  /** 자동 저장 간격 (밀리초) */
  autoSaveInterval: number;
  /** 변경 감지 debounce 시간 (밀리초) */
  debounceDelay: number;
  /** 강제 저장 주기 (밀리초) */
  forceSaveInterval: number;
  /** 최대 변경 횟수 (이 횟수에 도달하면 즉시 저장) */
  maxChangeCount: number;
}

export class CanvasAutoSave {
  private static sessions = new Map<string, AutoSaveSession>();
  
  private static readonly DEFAULT_OPTIONS: AutoSaveOptions = {
    autoSaveInterval: 3000,        // 3초
    debounceDelay: 1000,          // 1초
    forceSaveInterval: 30000,     // 30초
    maxChangeCount: 10            // 10회 변경
  };

  private static saveCallback: ((canvasId: string, canvasData: any) => Promise<void>) | null = null;

  /**
   * 자동 저장 시스템 초기화
   */
  static initialize(saveCallback: (canvasId: string, canvasData: any) => Promise<void>): void {
    console.log('🔄 Canvas 자동 저장 시스템 초기화');
    this.saveCallback = saveCallback;
    
    // 브라우저 종료 시 모든 변경사항 저장
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', this.saveAllBeforeUnload.bind(this));
      
      // 페이지 숨김 시에도 저장
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
          this.saveAllImmediate();
        }
      });
    }
  }

  /**
   * Canvas 자동 저장 시작
   */
  static startAutoSave(
    canvasId: string,
    canvasType: CanvasToolType,
    conversationId: string,
    initialData?: any,
    options?: Partial<AutoSaveOptions>
  ): void {
    console.log('▶️ Canvas 자동 저장 시작:', { canvasId, canvasType });

    // 기존 세션이 있으면 정리
    this.stopAutoSave(canvasId);

    // 자동 저장 옵션 병합
    const finalOptions: AutoSaveOptions = {
      ...this.DEFAULT_OPTIONS,
      ...options
    };

    // 새 세션 생성
    const session: AutoSaveSession = {
      canvasId,
      canvasType,
      conversationId,
      lastSaveTime: Date.now(),
      isDirty: false,
      changeCount: 0
    };

    // 주기적 자동 저장 설정
    if (CanvasShareStrategy.shouldAutoSave(canvasType)) {
      session.saveIntervalId = setInterval(() => {
        this.performPeriodicSave(canvasId, finalOptions);
      }, finalOptions.autoSaveInterval);
    }

    this.sessions.set(canvasId, session);

    // 초기 데이터가 있으면 즉시 저장
    if (initialData) {
      this.saveImmediate(canvasId, initialData);
    }

    console.log('✅ Canvas 자동 저장 시작 완료:', canvasId);
  }

  /**
   * Canvas 변경 감지 및 저장 스케줄링
   */
  static notifyChange(
    canvasId: string,
    canvasData: any,
    options?: Partial<AutoSaveOptions>
  ): void {
    const session = this.sessions.get(canvasId);
    if (!session) {
      console.warn('⚠️ 자동 저장 세션을 찾을 수 없음:', canvasId);
      return;
    }

    const finalOptions: AutoSaveOptions = {
      ...this.DEFAULT_OPTIONS,
      ...options
    };

    // 변경 카운터 증가
    session.changeCount++;
    session.isDirty = true;

    console.log('🔔 Canvas 변경 감지:', {
      canvasId: canvasId.substring(0, 20),
      changeCount: session.changeCount,
      isDirty: session.isDirty
    });

    // 기존 debounce 타이머 취소
    if (session.debounceTimeoutId) {
      clearTimeout(session.debounceTimeoutId);
    }

    // 최대 변경 횟수에 도달하면 즉시 저장
    if (session.changeCount >= finalOptions.maxChangeCount) {
      console.log('⚡ 최대 변경 횟수 도달, 즉시 저장:', canvasId);
      this.saveImmediate(canvasId, canvasData);
      return;
    }

    // Debounced 저장 스케줄링
    session.debounceTimeoutId = setTimeout(() => {
      this.saveImmediate(canvasId, canvasData);
    }, finalOptions.debounceDelay);
  }

  /**
   * 즉시 저장
   */
  static async saveImmediate(canvasId: string, canvasData: any): Promise<void> {
    const session = this.sessions.get(canvasId);
    if (!session || !session.isDirty) {
      return;
    }

    try {
      console.log('💾 Canvas 즉시 저장 실행:', canvasId.substring(0, 20));

      if (this.saveCallback) {
        await this.saveCallback(canvasId, canvasData);
        
        // 저장 성공 후 상태 업데이트
        session.lastSaveTime = Date.now();
        session.isDirty = false;
        session.changeCount = 0;
        
        // debounce 타이머 정리
        if (session.debounceTimeoutId) {
          clearTimeout(session.debounceTimeoutId);
          session.debounceTimeoutId = undefined;
        }

        console.log('✅ Canvas 즉시 저장 완료:', canvasId.substring(0, 20));
      } else {
        console.warn('⚠️ 저장 콜백이 설정되지 않음');
      }

    } catch (error) {
      console.error('❌ Canvas 즉시 저장 실패:', canvasId, error);
      // 저장 실패 시 재시도 로직
      setTimeout(() => {
        this.saveImmediate(canvasId, canvasData);
      }, 5000); // 5초 후 재시도
    }
  }

  /**
   * 주기적 저장 수행
   */
  private static async performPeriodicSave(canvasId: string, options: AutoSaveOptions): Promise<void> {
    const session = this.sessions.get(canvasId);
    if (!session || !session.isDirty) {
      return;
    }

    const now = Date.now();
    const timeSinceLastSave = now - session.lastSaveTime;

    // 강제 저장 주기에 도달했거나 변경사항이 있으면 저장
    if (timeSinceLastSave >= options.forceSaveInterval) {
      console.log('⏰ 주기적 강제 저장 실행:', canvasId.substring(0, 20));
      
      try {
        // Canvas 데이터를 현재 상태에서 가져와야 함
        // 실제로는 Canvas Store에서 현재 데이터를 가져와야 함
        const currentCanvasData = await this.getCurrentCanvasData(canvasId);
        if (currentCanvasData) {
          await this.saveImmediate(canvasId, currentCanvasData);
        }
      } catch (error) {
        console.error('❌ 주기적 저장 실패:', error);
      }
    }
  }

  /**
   * Canvas 자동 저장 중지
   */
  static stopAutoSave(canvasId: string, saveBeforeStop: boolean = true): void {
    const session = this.sessions.get(canvasId);
    if (!session) {
      return;
    }

    console.log('⏹️ Canvas 자동 저장 중지:', canvasId.substring(0, 20));

    // 중지 전 마지막 저장
    if (saveBeforeStop && session.isDirty) {
      this.getCurrentCanvasData(canvasId)
        .then(canvasData => {
          if (canvasData) {
            this.saveImmediate(canvasId, canvasData);
          }
        })
        .catch(error => {
          console.error('❌ 중지 전 저장 실패:', error);
        });
    }

    // 타이머들 정리
    if (session.saveIntervalId) {
      clearInterval(session.saveIntervalId);
    }
    if (session.debounceTimeoutId) {
      clearTimeout(session.debounceTimeoutId);
    }

    // 세션 제거
    this.sessions.delete(canvasId);

    console.log('✅ Canvas 자동 저장 중지 완료:', canvasId.substring(0, 20));
  }

  /**
   * 모든 자동 저장 중지
   */
  static stopAllAutoSave(): void {
    console.log('⏹️ 모든 Canvas 자동 저장 중지');
    
    const canvasIds = Array.from(this.sessions.keys());
    canvasIds.forEach(canvasId => {
      this.stopAutoSave(canvasId, false); // 일괄 중지 시에는 개별 저장 안함
    });
  }

  /**
   * 모든 변경사항 즉시 저장 (브라우저 종료 전)
   */
  private static saveAllBeforeUnload(): void {
    console.log('🔄 브라우저 종료 전 모든 Canvas 저장');
    
    // 동기적으로 처리해야 함 (beforeunload)
    const dirtySessions = Array.from(this.sessions.entries())
      .filter(([_, session]) => session.isDirty);

    if (dirtySessions.length > 0) {
      console.log(`💾 저장할 Canvas 개수: ${dirtySessions.length}`);
      // 실제 저장은 navigator.sendBeacon 등을 사용해야 함
      this.saveAllImmediate();
    }
  }

  /**
   * 모든 변경사항 즉시 저장
   */
  private static async saveAllImmediate(): Promise<void> {
    console.log('💾 모든 Canvas 즉시 저장');
    
    const savePromises = Array.from(this.sessions.entries())
      .filter(([_, session]) => session.isDirty)
      .map(async ([canvasId, session]) => {
        try {
          const canvasData = await this.getCurrentCanvasData(canvasId);
          if (canvasData) {
            await this.saveImmediate(canvasId, canvasData);
          }
        } catch (error) {
          console.error(`❌ Canvas 저장 실패 (${canvasId}):`, error);
        }
      });

    await Promise.allSettled(savePromises);
  }

  /**
   * 현재 Canvas 데이터 가져오기
   * 실제로는 Canvas Store에서 가져와야 함
   */
  private static async getCurrentCanvasData(canvasId: string): Promise<any> {
    // TODO: Canvas Store 연동
    // 현재는 더미 데이터 반환
    return {
      canvasId,
      timestamp: Date.now(),
      // 실제로는 Canvas Store에서 현재 Canvas 상태를 가져와야 함
    };
  }

  /**
   * 자동 저장 상태 조회
   */
  static getAutoSaveStatus(canvasId: string): {
    isActive: boolean;
    isDirty: boolean;
    lastSaveTime: number;
    changeCount: number;
  } | null {
    const session = this.sessions.get(canvasId);
    if (!session) {
      return null;
    }

    return {
      isActive: true,
      isDirty: session.isDirty,
      lastSaveTime: session.lastSaveTime,
      changeCount: session.changeCount
    };
  }

  /**
   * 전체 자동 저장 통계
   */
  static getAutoSaveStatistics(): {
    activeSessions: number;
    dirtySessions: number;
    totalChanges: number;
  } {
    const sessions = Array.from(this.sessions.values());
    
    return {
      activeSessions: sessions.length,
      dirtySessions: sessions.filter(s => s.isDirty).length,
      totalChanges: sessions.reduce((sum, s) => sum + s.changeCount, 0)
    };
  }
}

export default CanvasAutoSave;