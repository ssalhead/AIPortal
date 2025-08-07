/**
 * 로딩 상태 관리 컨텍스트
 */

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface LoadingState {
  /** 전역 로딩 상태 */
  isLoading: boolean;
  /** 로딩 메시지 */
  loadingMessage: string;
  /** 개별 작업별 로딩 상태 */
  taskLoadings: Record<string, boolean>;
  /** 타이핑 인디케이터 상태 */
  isTyping: boolean;
  /** 타이핑 메시지 */
  typingMessage: string;
  /** 사용중인 AI 모델 */
  currentModel?: string;
}

interface LoadingActions {
  /** 전역 로딩 시작 */
  startLoading: (message?: string) => void;
  /** 전역 로딩 종료 */
  stopLoading: () => void;
  /** 작업별 로딩 시작 */
  startTaskLoading: (taskId: string) => void;
  /** 작업별 로딩 종료 */
  stopTaskLoading: (taskId: string) => void;
  /** 모든 작업 로딩 상태 확인 */
  isTaskLoading: (taskId: string) => boolean;
  /** 타이핑 인디케이터 시작 */
  startTyping: (message?: string, model?: string) => void;
  /** 타이핑 인디케이터 종료 */
  stopTyping: () => void;
  /** 모든 로딩 상태 초기화 */
  clearAllLoadings: () => void;
}

type LoadingContextType = LoadingState & LoadingActions;

const LoadingContext = createContext<LoadingContextType | undefined>(undefined);

const initialState: LoadingState = {
  isLoading: false,
  loadingMessage: '',
  taskLoadings: {},
  isTyping: false,
  typingMessage: 'AI가 응답을 작성 중입니다...',
  currentModel: undefined,
};

interface LoadingProviderProps {
  children: ReactNode;
}

export const LoadingProvider: React.FC<LoadingProviderProps> = ({ children }) => {
  const [state, setState] = useState<LoadingState>(initialState);

  const startLoading = (message = '처리 중입니다...') => {
    setState(prev => ({
      ...prev,
      isLoading: true,
      loadingMessage: message,
    }));
  };

  const stopLoading = () => {
    setState(prev => ({
      ...prev,
      isLoading: false,
      loadingMessage: '',
    }));
  };

  const startTaskLoading = (taskId: string) => {
    setState(prev => ({
      ...prev,
      taskLoadings: {
        ...prev.taskLoadings,
        [taskId]: true,
      },
    }));
  };

  const stopTaskLoading = (taskId: string) => {
    setState(prev => {
      const newTaskLoadings = { ...prev.taskLoadings };
      delete newTaskLoadings[taskId];
      return {
        ...prev,
        taskLoadings: newTaskLoadings,
      };
    });
  };

  const isTaskLoading = (taskId: string): boolean => {
    return !!state.taskLoadings[taskId];
  };

  const startTyping = (message = 'AI가 응답을 작성 중입니다...', model?: string) => {
    setState(prev => ({
      ...prev,
      isTyping: true,
      typingMessage: message,
      currentModel: model,
    }));
  };

  const stopTyping = () => {
    setState(prev => ({
      ...prev,
      isTyping: false,
      typingMessage: 'AI가 응답을 작성 중입니다...',
      currentModel: undefined,
    }));
  };

  const clearAllLoadings = () => {
    setState(initialState);
  };

  const contextValue: LoadingContextType = {
    ...state,
    startLoading,
    stopLoading,
    startTaskLoading,
    stopTaskLoading,
    isTaskLoading,
    startTyping,
    stopTyping,
    clearAllLoadings,
  };

  return (
    <LoadingContext.Provider value={contextValue}>
      {children}
    </LoadingContext.Provider>
  );
};

export const useLoading = (): LoadingContextType => {
  const context = useContext(LoadingContext);
  if (!context) {
    throw new Error('useLoading must be used within a LoadingProvider');
  }
  return context;
};

/**
 * 개별 작업 로딩 상태를 관리하는 커스텀 훅
 */
export const useTaskLoading = (taskId: string) => {
  const { isTaskLoading, startTaskLoading, stopTaskLoading } = useLoading();

  return {
    isLoading: isTaskLoading(taskId),
    startLoading: () => startTaskLoading(taskId),
    stopLoading: () => stopTaskLoading(taskId),
  };
};

/**
 * 비동기 작업에 대한 로딩 상태를 자동으로 관리하는 훅
 */
export const useAsyncLoading = <T extends any[], R>(
  asyncFunction: (...args: T) => Promise<R>,
  taskId?: string
) => {
  const { startLoading, stopLoading, startTaskLoading, stopTaskLoading } = useLoading();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = async (...args: T): Promise<R | null> => {
    try {
      setIsLoading(true);
      setError(null);
      
      if (taskId) {
        startTaskLoading(taskId);
      } else {
        startLoading();
      }

      const result = await asyncFunction(...args);
      return result;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      return null;
    } finally {
      setIsLoading(false);
      
      if (taskId) {
        stopTaskLoading(taskId);
      } else {
        stopLoading();
      }
    }
  };

  return {
    execute,
    isLoading,
    error,
  };
};

/**
 * 타이핑 인디케이터를 쉽게 사용할 수 있는 훅
 */
export const useTyping = () => {
  const { isTyping, startTyping, stopTyping, typingMessage, currentModel } = useLoading();

  return {
    isTyping,
    startTyping,
    stopTyping,
    typingMessage,
    currentModel,
  };
};