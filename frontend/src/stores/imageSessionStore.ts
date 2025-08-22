/**
 * 진화형 이미지 생성 세션 관리 Store
 * 하나의 대화 = 하나의 Canvas = 하나의 이미지 테마 + 순차적 버전 개선
 */

import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
// import { promptEvolutionEngine } from '../services/promptEvolutionEngine';

// 이미지 버전 인터페이스
export interface ImageVersion {
  id: string;
  versionNumber: number;        // 1, 2, 3, 4...
  prompt: string;
  negativePrompt: string;
  style: string;
  size: string;
  imageUrl: string;
  parentVersionId?: string;     // 브랜치 추적용 (어떤 이미지를 기반으로 생성되었는지)
  createdAt: string;
  isSelected: boolean;          // 현재 선택된 베이스 이미지 여부
  status: 'generating' | 'completed' | 'failed';
}

// 이미지 생성 세션 인터페이스
export interface ImageGenerationSession {
  conversationId: string;
  theme: string;               // "강아지", "수영장" 등 추출된 주제
  versions: ImageVersion[];
  selectedVersionId: string;   // 현재 선택된 버전 ID
  basePrompt: string;          // 최초 프롬프트
  evolutionHistory: string[];  // 프롬프트 변화 히스토리
  createdAt: string;
  updatedAt: string;
}

interface ImageSessionState {
  // 세션 맵 (conversationId -> Session)
  sessions: Map<string, ImageGenerationSession>;
  
  // 세션 관리
  createSession: (conversationId: string, theme: string, initialPrompt: string) => ImageGenerationSession;
  getSession: (conversationId: string) => ImageGenerationSession | null;
  updateSession: (conversationId: string, updates: Partial<ImageGenerationSession>) => void;
  deleteSession: (conversationId: string) => void;
  
  // 버전 관리
  addVersion: (conversationId: string, version: Omit<ImageVersion, 'id' | 'createdAt' | 'versionNumber'>) => string;
  updateVersion: (conversationId: string, versionId: string, updates: Partial<ImageVersion>) => void;
  deleteVersion: (conversationId: string, versionId: string) => void;
  deleteAllVersions: (conversationId: string) => void;
  
  // 버전 선택
  selectVersion: (conversationId: string, versionId: string) => void;
  selectLatestVersion: (conversationId: string) => void;
  
  // 프롬프트 진화
  evolvePrompt: (conversationId: string, userInput: string) => string;
  extractTheme: (prompt: string) => string;
  
  // 상태 조회
  getSelectedVersion: (conversationId: string) => ImageVersion | null;
  getLatestVersion: (conversationId: string) => ImageVersion | null;
  hasAnyVersions: (conversationId: string) => boolean;
  getVersionCount: (conversationId: string) => number;
  getNextVersionNumber: (conversationId: string) => number;
  
  // 세션 존재 여부
  hasSession: (conversationId: string) => boolean;
  
  // 브랜치 관련
  getChildVersions: (conversationId: string, parentVersionId: string) => ImageVersion[];
  createBranch: (conversationId: string, parentVersionId: string, newPrompt: string) => string;
}

export const useImageSessionStore = create<ImageSessionState>((set, get) => ({
  sessions: new Map(),
  
  // === 세션 관리 ===
  createSession: (conversationId, theme, initialPrompt) => {
    console.log('🎨 이미지 세션 생성:', { conversationId, theme, initialPrompt });
    
    const newSession: ImageGenerationSession = {
      conversationId,
      theme,
      versions: [],
      selectedVersionId: '',
      basePrompt: initialPrompt,
      evolutionHistory: [initialPrompt],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    
    set((state) => {
      const newSessions = new Map(state.sessions);
      newSessions.set(conversationId, newSession);
      return { sessions: newSessions };
    });
    
    return newSession;
  },
  
  getSession: (conversationId) => {
    return get().sessions.get(conversationId) || null;
  },
  
  updateSession: (conversationId, updates) => {
    set((state) => {
      const newSessions = new Map(state.sessions);
      const existingSession = newSessions.get(conversationId);
      
      if (existingSession) {
        const updatedSession = {
          ...existingSession,
          ...updates,
          updatedAt: new Date().toISOString(),
        };
        newSessions.set(conversationId, updatedSession);
      }
      
      return { sessions: newSessions };
    });
  },
  
  deleteSession: (conversationId) => {
    console.log('🗑️ 이미지 세션 삭제:', conversationId);
    
    set((state) => {
      const newSessions = new Map(state.sessions);
      newSessions.delete(conversationId);
      return { sessions: newSessions };
    });
  },
  
  // === 버전 관리 ===
  addVersion: (conversationId, versionData) => {
    console.log('🖼️ 새 이미지 버전 추가:', { conversationId, versionData });
    
    const versionId = uuidv4();
    const nextVersionNumber = get().getNextVersionNumber(conversationId);
    
    const newVersion: ImageVersion = {
      id: versionId,
      versionNumber: nextVersionNumber,
      createdAt: new Date().toISOString(),
      isSelected: false, // 기본값, 나중에 선택 처리
      ...versionData,
    };
    
    set((state) => {
      const newSessions = new Map(state.sessions);
      const session = newSessions.get(conversationId);
      
      if (session) {
        // 기존 선택 해제
        const updatedVersions = session.versions.map(v => ({ ...v, isSelected: false }));
        
        // 새 버전 추가 및 선택
        newVersion.isSelected = true;
        updatedVersions.push(newVersion);
        
        const updatedSession = {
          ...session,
          versions: updatedVersions,
          selectedVersionId: versionId,
          updatedAt: new Date().toISOString(),
        };
        
        newSessions.set(conversationId, updatedSession);
      }
      
      return { sessions: newSessions };
    });
    
    return versionId;
  },
  
  updateVersion: (conversationId, versionId, updates) => {
    console.log('📝 이미지 버전 업데이트:', { conversationId, versionId, updates });
    
    set((state) => {
      const newSessions = new Map(state.sessions);
      const session = newSessions.get(conversationId);
      
      if (session) {
        const updatedVersions = session.versions.map(version =>
          version.id === versionId
            ? { ...version, ...updates }
            : version
        );
        
        const updatedSession = {
          ...session,
          versions: updatedVersions,
          updatedAt: new Date().toISOString(),
        };
        
        newSessions.set(conversationId, updatedSession);
      }
      
      return { sessions: newSessions };
    });
  },
  
  deleteVersion: (conversationId, versionId) => {
    console.log('🗑️ 이미지 버전 삭제:', { conversationId, versionId });
    
    set((state) => {
      const newSessions = new Map(state.sessions);
      const session = newSessions.get(conversationId);
      
      if (session) {
        const filteredVersions = session.versions.filter(v => v.id !== versionId);
        let newSelectedVersionId = session.selectedVersionId;
        
        // 삭제된 버전이 선택되어 있었다면 가장 최신 버전으로 변경
        if (session.selectedVersionId === versionId && filteredVersions.length > 0) {
          const latestVersion = filteredVersions.reduce((latest, current) =>
            latest.versionNumber > current.versionNumber ? latest : current
          );
          
          newSelectedVersionId = latestVersion.id;
          
          // 선택 상태 업데이트
          filteredVersions.forEach(v => {
            v.isSelected = v.id === newSelectedVersionId;
          });
        }
        
        const updatedSession = {
          ...session,
          versions: filteredVersions,
          selectedVersionId: newSelectedVersionId,
          updatedAt: new Date().toISOString(),
        };
        
        newSessions.set(conversationId, updatedSession);
      }
      
      return { sessions: newSessions };
    });
  },
  
  deleteAllVersions: (conversationId) => {
    console.log('🗑️ 모든 이미지 버전 삭제:', conversationId);
    
    set((state) => {
      const newSessions = new Map(state.sessions);
      const session = newSessions.get(conversationId);
      
      if (session) {
        const updatedSession = {
          ...session,
          versions: [],
          selectedVersionId: '',
          updatedAt: new Date().toISOString(),
        };
        
        newSessions.set(conversationId, updatedSession);
      }
      
      return { sessions: newSessions };
    });
  },
  
  // === 버전 선택 ===
  selectVersion: (conversationId, versionId) => {
    console.log('🎯 이미지 버전 선택:', { conversationId, versionId });
    
    set((state) => {
      const newSessions = new Map(state.sessions);
      const session = newSessions.get(conversationId);
      
      if (session) {
        const updatedVersions = session.versions.map(version => ({
          ...version,
          isSelected: version.id === versionId,
        }));
        
        const updatedSession = {
          ...session,
          versions: updatedVersions,
          selectedVersionId: versionId,
          updatedAt: new Date().toISOString(),
        };
        
        newSessions.set(conversationId, updatedSession);
      }
      
      return { sessions: newSessions };
    });
  },
  
  selectLatestVersion: (conversationId) => {
    const session = get().getSession(conversationId);
    if (session && session.versions.length > 0) {
      const latestVersion = session.versions.reduce((latest, current) =>
        latest.versionNumber > current.versionNumber ? latest : current
      );
      get().selectVersion(conversationId, latestVersion.id);
    }
  },
  
  // === 프롬프트 진화 ===
  evolvePrompt: (conversationId, userInput) => {
    console.log('🧬 프롬프트 진화:', { conversationId, userInput });
    
    const session = get().getSession(conversationId);
    const selectedVersion = get().getSelectedVersion(conversationId);
    
    if (!session || !selectedVersion) {
      console.warn('⚠️ 세션 또는 선택된 버전이 없음');
      return userInput;
    }
    
    // PromptEvolutionEngine을 사용한 지능적 프롬프트 진화
    const basePrompt = selectedVersion.prompt;
    // const evolutionResult = promptEvolutionEngine.evolvePrompt(basePrompt, userInput);
    const evolutionResult = { newPrompt: userInput, confidence: 1.0 };
    
    // 진화 히스토리 업데이트
    const newHistory = [...session.evolutionHistory, userInput];
    get().updateSession(conversationId, {
      evolutionHistory: newHistory,
    });
    
    console.log('✨ 프롬프트 진화 완료:', {
      basePrompt,
      userInput,
      evolutionResult,
      confidence: evolutionResult.confidence,
    });
    
    return evolutionResult.newPrompt;
  },
  
  extractTheme: (prompt) => {
    // PromptEvolutionEngine의 주제 추출 로직 사용
    // return promptEvolutionEngine.extractTheme(prompt);
    return prompt.split(' ')[0] || 'unknown';
  },
  
  // === 상태 조회 ===
  getSelectedVersion: (conversationId) => {
    const session = get().getSession(conversationId);
    if (!session) return null;
    
    return session.versions.find(v => v.id === session.selectedVersionId) || null;
  },
  
  getLatestVersion: (conversationId) => {
    const session = get().getSession(conversationId);
    if (!session || session.versions.length === 0) return null;
    
    return session.versions.reduce((latest, current) =>
      latest.versionNumber > current.versionNumber ? latest : current
    );
  },
  
  hasAnyVersions: (conversationId) => {
    const session = get().getSession(conversationId);
    return session ? session.versions.length > 0 : false;
  },
  
  getVersionCount: (conversationId) => {
    const session = get().getSession(conversationId);
    return session ? session.versions.length : 0;
  },
  
  getNextVersionNumber: (conversationId) => {
    const session = get().getSession(conversationId);
    if (!session || session.versions.length === 0) return 1;
    
    const maxVersion = session.versions.reduce((max, current) =>
      current.versionNumber > max ? current.versionNumber : max, 0
    );
    
    return maxVersion + 1;
  },
  
  hasSession: (conversationId) => {
    return get().sessions.has(conversationId);
  },
  
  // === 브랜치 관련 ===
  getChildVersions: (conversationId, parentVersionId) => {
    const session = get().getSession(conversationId);
    if (!session) return [];
    
    return session.versions.filter(v => v.parentVersionId === parentVersionId);
  },
  
  createBranch: (conversationId, parentVersionId, newPrompt) => {
    console.log('🌿 브랜치 생성:', { conversationId, parentVersionId, newPrompt });
    
    const parentVersion = get().getSession(conversationId)?.versions.find(v => v.id === parentVersionId);
    if (!parentVersion) {
      console.warn('⚠️ 부모 버전을 찾을 수 없음');
      return '';
    }
    
    return get().addVersion(conversationId, {
      prompt: newPrompt,
      negativePrompt: parentVersion.negativePrompt,
      style: parentVersion.style,
      size: parentVersion.size,
      imageUrl: '', // 생성 대기 상태
      parentVersionId: parentVersionId,
      status: 'generating',
      isSelected: false,
    });
  },
}));

// 명시적 export 추가
export { type ImageVersion, type ImageGenerationSession };
export default useImageSessionStore;