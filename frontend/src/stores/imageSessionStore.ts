/**
 * 진화형 이미지 생성 세션 관리 Store
 * 하나의 대화 = 하나의 Canvas = 하나의 이미지 테마 + 순차적 버전 개선
 */

import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';

// UUID 충돌 방지 헬퍼 함수 (v4.5 추가)
function generateUniqueVersionId(existingVersions: ImageVersion[]): string {
  const existingIds = new Set(existingVersions.map(v => v.id));
  let attempts = 0;
  let newId: string;
  
  do {
    newId = uuidv4();
    attempts++;
    if (attempts > 10) {
      console.warn('⚠️ UUID 충돌 방지 - 10회 시도 후 강제 진행:', newId);
      break;
    }
  } while (existingIds.has(newId));
  
  return newId;
}
// import { promptEvolutionEngine } from '../services/promptEvolutionEngine';
import type { ImageVersion, ImageGenerationSession } from '../types/imageSession';
import { ImageSessionApiClient, ApiResponseConverter } from '../services/imageSessionApi';

interface ImageSessionState {
  // 세션 맵 (conversationId -> Session)
  sessions: Map<string, ImageGenerationSession>;
  
  // 삭제된 이미지 URL 추적 (conversationId -> Set<imageUrl>)
  deletedImageUrls: Map<string, Set<string>>;
  
  // DB 동기화 상태
  isLoading: Map<string, boolean>;
  loadError: string | null;
  
  // 동기화 완료 플래그 (conversationId -> 완료 시간)
  syncCompletedFlags: Map<string, number>;
  
  // 현재 사용자 ID (임시로 하드코딩, 추후 인증 시스템과 연동)
  currentUserId: string;
  
  // Canvas ID 기반 중복 방지 (v4.1) - conversationId -> Set<canvasId>
  processedCanvasIds: Map<string, Set<string>>;
  
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
  
  // 삭제된 이미지 URL 추적
  isImageDeleted: (conversationId: string, imageUrl: string) => boolean;
  clearDeletedImages: (conversationId: string) => void;
  
  // DB 동기화 메서드
  loadSessionFromDB: (conversationId: string, forceReload?: boolean) => Promise<ImageGenerationSession | null>;
  syncSessionToDB: (conversationId: string) => Promise<void>;
  syncVersionToDB: (conversationId: string, versionId: string) => Promise<void>;
  syncDeletedImageUrls: (conversationId: string) => Promise<void>;
  
  // 상태 관리
  setLoading: (conversationId: string, loading: boolean) => void;
  setError: (error: string | null) => void;
  isLoadingSession: (conversationId: string) => boolean;
  
  // 동기화 완료 플래그 관리
  markSyncCompleted: (conversationId: string) => void;
  isSyncCompleted: (conversationId: string, maxAgeMs?: number) => boolean;
  clearSyncFlag: (conversationId: string) => void;
  
  // 하이브리드 메서드 (메모리 + DB 동기화)
  createSessionHybrid: (conversationId: string, theme: string, initialPrompt: string) => Promise<ImageGenerationSession>;
  addVersionHybrid: (conversationId: string, version: Omit<ImageVersion, 'id' | 'createdAt' | 'versionNumber'>) => Promise<string>;
  deleteVersionHybrid: (conversationId: string, versionId: string) => Promise<void>;
  selectVersionHybrid: (conversationId: string, versionId: string) => Promise<void>;
  
  // Canvas ID 중복 방지 메서드 (v4.1)
  isCanvasIdProcessed: (conversationId: string, canvasId: string) => boolean;
  markCanvasIdAsProcessed: (conversationId: string, canvasId: string) => void;
  clearProcessedCanvasIds: (conversationId: string) => void;
}

export const useImageSessionStore = create<ImageSessionState>((set, get) => ({
  sessions: new Map(),
  deletedImageUrls: new Map(),
  isLoading: new Map(),
  loadError: null,
  syncCompletedFlags: new Map(),
  currentUserId: 'ff8e410a-53a4-4541-a7d4-ce265678d66a', // Mock 사용자 ID (실제 UUID 형식)
  processedCanvasIds: new Map(), // Canvas ID 중복 방지 (v4.1)
  
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
    console.log('📊 ImageSession Store - 기존 세션 상태:', { 
      hasSession: get().hasSession(conversationId),
      currentVersions: get().getSession(conversationId)?.versions?.length || 0,
      versions: get().getSession(conversationId)?.versions?.map(v => ({ id: v.id, prompt: v.prompt.substring(0, 30) }))
    });
    
    // 🚫 버전 중복 생성 방지: 동일한 이미지URL + 프롬프트 조합 검증
    const session = get().getSession(conversationId);
    if (session && versionData.imageUrl) {
      const existingVersion = session.versions.find(v => 
        v.imageUrl === versionData.imageUrl && 
        v.prompt.trim() === (versionData.prompt || '').trim()
      );
      
      if (existingVersion) {
        console.log('🚫 ImageSession Store - 동일한 버전 이미 존재, 새 생성 스킵:', {
          existingVersionId: existingVersion.id,
          versionNumber: existingVersion.versionNumber,
          imageUrl: versionData.imageUrl.substring(0, 50) + '...',
          prompt: versionData.prompt?.substring(0, 30) + '...'
        });
        
        // 기존 버전 선택하고 ID 반환
        get().selectVersion(conversationId, existingVersion.id);
        return existingVersion.id;
      }
    }
    
    // 새 버전 추가 시 동기화 플래그 초기화 (새로운 동기화가 필요할 수 있음)
    get().clearSyncFlag(conversationId);
    
    // 🛡️ UUID 충돌 방지 - 기존 버전 ID와 중복되지 않도록 보장 (v4.5)
    const currentSession = get().getSession(conversationId);
    const existingVersions = currentSession?.versions || [];
    const versionId = generateUniqueVersionId(existingVersions);
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
      const newDeletedImageUrls = new Map(state.deletedImageUrls);
      const session = newSessions.get(conversationId);
      
      if (session) {
        // 삭제될 버전 찾기
        const versionToDelete = session.versions.find(v => v.id === versionId);
        
        if (versionToDelete && versionToDelete.imageUrl) {
          // 삭제된 이미지 URL 추적
          const deletedUrls = newDeletedImageUrls.get(conversationId) || new Set();
          deletedUrls.add(versionToDelete.imageUrl);
          newDeletedImageUrls.set(conversationId, deletedUrls);
          
          console.log('🗑️ 삭제된 이미지 URL 추가:', versionToDelete.imageUrl.slice(0, 50) + '...');
        }
        
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
      
      return { 
        sessions: newSessions,
        deletedImageUrls: newDeletedImageUrls
      };
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
  
  // === 삭제된 이미지 URL 추적 ===
  isImageDeleted: (conversationId, imageUrl) => {
    const deletedUrls = get().deletedImageUrls.get(conversationId);
    return deletedUrls ? deletedUrls.has(imageUrl) : false;
  },
  
  clearDeletedImages: (conversationId) => {
    const newDeletedImageUrls = new Map(get().deletedImageUrls);
    newDeletedImageUrls.delete(conversationId);
    
    set({ deletedImageUrls: newDeletedImageUrls });
    console.log('🗑️ 삭제된 이미지 URL 목록 정리:', conversationId);
  },
  
  // === DB 동기화 메서드 ===
  
  loadSessionFromDB: async (conversationId, forceReload = false) => {
    console.log('📥 DB에서 세션 로드 시작:', { conversationId, forceReload });
    const state = get();
    
    // 🚨 RACE CONDITION 방지 + 강제 로드 지원
    const existingSession = state.getSession(conversationId);
    if (!forceReload && existingSession && existingSession.versions.length > 0) {
      console.log('⏸️ 이미 메모리에 세션 존재 (버전 있음), DB 로드 생략:', {
        conversationId,
        versionsCount: existingSession.versions.length,
        forceReload
      });
      return existingSession;
    }
    
    if (forceReload && existingSession) {
      console.log('🔄 강제 재로드 모드 - 기존 메모리 세션 무시:', {
        conversationId,
        existingVersions: existingSession.versions.length
      });
    }
    
    try {
      state.setLoading(conversationId, true);
      state.setError(null);
      
      const apiSession = await ImageSessionApiClient.getSessionByConversation(conversationId, state.currentUserId);
      
      if (apiSession) {
        const storeSession = ApiResponseConverter.toStoreSession(apiSession);
        
        // 🛡️ 로드 직전에 다시 한번 체크 - 다른 컴포넌트가 먼저 생성했을 수 있음
        const currentSession = state.getSession(conversationId);
        if (currentSession && currentSession.versions.length > 0) {
          console.log('⚠️ 로드 중에 다른 컴포넌트가 세션 생성함, DB 로드 취소:', {
            conversationId,
            currentVersionsCount: currentSession.versions.length,
            dbVersionsCount: storeSession.versions.length
          });
          return currentSession; // 기존 메모리 세션 유지
        }
        
        // 메모리에 세션 저장 (DB 데이터가 우선)
        set((state) => {
          const newSessions = new Map(state.sessions);
          newSessions.set(conversationId, storeSession);
          return { sessions: newSessions };
        });
        
        // 삭제된 이미지 URL 동기화
        await state.syncDeletedImageUrls(conversationId);
        
        console.log('✅ DB에서 세션 로드 완료:', { conversationId, versionsCount: storeSession.versions.length });
        return storeSession;
      } else {
        console.log('ℹ️ DB에 세션이 없음:', conversationId);
        return null;
      }
    } catch (error) {
      console.error('❌ DB 세션 로드 실패:', error);
      state.setError(`세션 로드 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
      return null;
    } finally {
      state.setLoading(conversationId, false);
    }
  },
  
  syncSessionToDB: async (conversationId) => {
    console.log('📤 세션 DB 동기화 시작:', conversationId);
    const state = get();
    const session = state.getSession(conversationId);
    
    if (!session) {
      console.warn('⚠️ 동기화할 세션이 없음:', conversationId);
      return;
    }
    
    try {
      state.setLoading(conversationId, true);
      
      // DB에서 기존 세션 확인
      const existingSession = await ImageSessionApiClient.getSessionByConversation(conversationId, state.currentUserId);
      
      if (!existingSession) {
        // 새 세션 생성
        const apiSession = await ImageSessionApiClient.createSession({
          user_id: state.currentUserId,
          conversation_id: conversationId,
          theme: session.theme,
          base_prompt: session.basePrompt,
          evolution_history: session.evolutionHistory,
        });
        console.log('✅ 새 세션 DB 저장 완료:', apiSession.id);
      }
    } catch (error) {
      console.error('❌ 세션 DB 동기화 실패:', error);
      state.setError(`세션 동기화 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
    } finally {
      state.setLoading(conversationId, false);
    }
  },
  
  syncVersionToDB: async (conversationId, versionId) => {
    console.log('📤 버전 DB 동기화 시작:', { conversationId, versionId });
    const state = get();
    const session = state.getSession(conversationId);
    const version = session?.versions.find(v => v.id === versionId);
    
    if (!session || !version) {
      console.warn('⚠️ 동기화할 세션 또는 버전이 없음:', { conversationId, versionId });
      return;
    }
    
    try {
      // 먼저 세션이 DB에 있는지 확인
      const apiSession = await ImageSessionApiClient.getSessionByConversation(conversationId, state.currentUserId);
      if (!apiSession) {
        console.log('🔄 세션이 DB에 없어서 먼저 동기화');
        await state.syncSessionToDB(conversationId);
      }
      
      // 세션 ID 다시 조회
      const refreshedSession = await ImageSessionApiClient.getSessionByConversation(conversationId, state.currentUserId);
      if (!refreshedSession) {
        throw new Error('세션 동기화 후에도 세션을 찾을 수 없음');
      }
      
      // 버전 추가
      await ImageSessionApiClient.addVersion({
        user_id: state.currentUserId,
        session_id: refreshedSession.id,
        prompt: version.prompt,
        negative_prompt: version.negativePrompt,
        style: version.style,
        size: version.size,
        image_url: version.imageUrl,
        parent_version_id: version.parentVersionId,
        status: version.status,
      });
      
      console.log('✅ 버전 DB 동기화 완료:', versionId);
    } catch (error) {
      console.error('❌ 버전 DB 동기화 실패:', error);
      state.setError(`버전 동기화 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
    }
  },
  
  syncDeletedImageUrls: async (conversationId) => {
    console.log('📤 삭제된 이미지 URL DB 동기화 시작:', conversationId);
    const state = get();
    
    try {
      const deletedUrls = await ImageSessionApiClient.getDeletedImageUrls(conversationId, state.currentUserId);
      
      if (deletedUrls.length > 0) {
        set((state) => {
          const newDeletedImageUrls = new Map(state.deletedImageUrls);
          newDeletedImageUrls.set(conversationId, new Set(deletedUrls));
          return { deletedImageUrls: newDeletedImageUrls };
        });
        
        console.log('✅ 삭제된 이미지 URL 동기화 완료:', { conversationId, count: deletedUrls.length });
      }
    } catch (error) {
      console.error('❌ 삭제된 이미지 URL 동기화 실패:', error);
      // 이 부분은 크리티컬하지 않으므로 에러를 던지지 않음
    }
  },
  
  setLoading: (conversationId, loading) => {
    set((state) => {
      const newIsLoading = new Map(state.isLoading);
      newIsLoading.set(conversationId, loading);
      return { isLoading: newIsLoading };
    });
  },
  
  setError: (error) => {
    set({ loadError: error });
  },
  
  isLoadingSession: (conversationId) => {
    return get().isLoading.get(conversationId) || false;
  },
  
  // === 동기화 완료 플래그 관리 ===
  
  markSyncCompleted: (conversationId) => {
    console.log('🏁 동기화 완료 플래그 설정:', conversationId);
    set((state) => {
      const newFlags = new Map(state.syncCompletedFlags);
      newFlags.set(conversationId, Date.now());
      return { syncCompletedFlags: newFlags };
    });
  },
  
  isSyncCompleted: (conversationId, maxAgeMs = 30000) => {
    const completedTime = get().syncCompletedFlags.get(conversationId);
    if (!completedTime) return false;
    
    const age = Date.now() - completedTime;
    const isValid = age <= maxAgeMs;
    
    console.log('🔍 동기화 완료 플래그 확인:', {
      conversationId,
      completedTime,
      age,
      maxAgeMs,
      isValid
    });
    
    return isValid;
  },
  
  clearSyncFlag: (conversationId) => {
    console.log('🗑️ 동기화 완료 플래그 삭제:', conversationId);
    set((state) => {
      const newFlags = new Map(state.syncCompletedFlags);
      newFlags.delete(conversationId);
      return { syncCompletedFlags: newFlags };
    });
  },
  
  // === 하이브리드 메서드 (메모리 + DB 동기화) ===
  
  createSessionHybrid: async (conversationId, theme, initialPrompt) => {
    console.log('🎨 하이브리드 세션 생성:', { conversationId, theme, initialPrompt });
    const state = get();
    
    // 1. 먼저 DB에서 기존 세션 확인
    const existingSession = await state.loadSessionFromDB(conversationId);
    if (existingSession) {
      console.log('✅ 기존 DB 세션 반환:', conversationId);
      return existingSession;
    }
    
    // 2. 메모리에 새 세션 생성
    const memorySession = state.createSession(conversationId, theme, initialPrompt);
    
    // 3. DB에 비동기 저장
    state.syncSessionToDB(conversationId).catch(error => {
      console.error('❌ 세션 DB 저장 실패 (비동기):', error);
    });
    
    return memorySession;
  },
  
  addVersionHybrid: async (conversationId, versionData) => {
    console.log('🖼️ 하이브리드 버전 추가:', { conversationId, versionData });
    const state = get();
    
    // 1. 메모리에 버전 추가
    const versionId = state.addVersion(conversationId, versionData);
    
    // 2. DB에 비동기 저장
    state.syncVersionToDB(conversationId, versionId).catch(error => {
      console.error('❌ 버전 DB 저장 실패 (비동기):', error);
    });
    
    return versionId;
  },
  
  deleteVersionHybrid: async (conversationId, versionId) => {
    console.log('🗑️ 하이브리드 버전 삭제:', { conversationId, versionId });
    const state = get();
    
    try {
      // 1. DB에서 삭제
      const apiSession = await ImageSessionApiClient.getSessionByConversation(conversationId, state.currentUserId);
      if (apiSession) {
        const result = await ImageSessionApiClient.deleteVersion({
          user_id: state.currentUserId,
          session_id: apiSession.id,
          version_id: versionId,
        });
        
        console.log('✅ DB 버전 삭제 완료:', result);
        
        // 2. 메모리에서도 삭제 (DB 결과 반영)
        state.deleteVersion(conversationId, versionId);
        
        // 3. 새로 선택된 버전이 있다면 메모리 상태 업데이트
        if (result.new_selected_version) {
          const newSelectedVersion = ApiResponseConverter.toStoreVersion(result.new_selected_version);
          state.selectVersion(conversationId, newSelectedVersion.id);
        }
      } else {
        // DB에 세션이 없으면 메모리에서만 삭제
        state.deleteVersion(conversationId, versionId);
      }
    } catch (error) {
      console.error('❌ 버전 삭제 실패:', error);
      // 에러가 발생해도 메모리에서는 삭제
      state.deleteVersion(conversationId, versionId);
      state.setError(`버전 삭제 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
    }
  },
  
  selectVersionHybrid: async (conversationId, versionId) => {
    console.log('🎯 하이브리드 버전 선택:', { conversationId, versionId });
    const state = get();
    
    // 세션이 메모리에 없으면 Canvas 데이터로부터 자동 생성
    if (!state.hasSession(conversationId)) {
      console.log('🔄 메모리에 세션이 없어서 임시 세션 생성:', conversationId);
      
      // 기본 테마와 프롬프트로 빈 세션 생성
      state.createSession(conversationId, '이미지 생성', '사용자 요청');
    }
    
    // 1. 메모리에서 선택
    state.selectVersion(conversationId, versionId);
    
    // 2. DB에 비동기 동기화 (개선된 404 오류 방지)
    try {
      const apiSession = await ImageSessionApiClient.getSessionByConversation(conversationId, state.currentUserId);
      if (apiSession) {
        // DB 세션의 versions 배열에서 해당 버전 존재 여부 확인
        const versionExists = apiSession.versions.some((v: any) => v.id === versionId);
        
        if (versionExists) {
          // 🛡️ 버전 존재 확인됨 - 안전하게 선택 API 호출
          try {
            await ImageSessionApiClient.selectVersion({
              user_id: state.currentUserId,
              session_id: apiSession.id,
              version_id: versionId,
            });
            console.log('✅ DB 버전 선택 동기화 완료:', versionId);
          } catch (selectError) {
            console.warn('⚠️ 버전 선택 API 실패 (존재하는 버전인데도), 메모리에서만 처리:', selectError);
          }
        } else {
          console.warn('⚠️ DB에 해당 버전이 존재하지 않음, DB 동기화 후 재시도:', {
            conversationId,
            versionId,
            availableVersions: apiSession.versions.map((v: any) => ({ id: v.id, version_number: v.version_number }))
          });
          
          // DB에 없는 경우 메모리 버전을 DB에 동기화 시도
          const memorySession = state.getSession(conversationId);
          const memoryVersion = memorySession?.versions.find(v => v.id === versionId);
          
          if (memoryVersion) {
            console.log('🔄 메모리 버전을 DB에 동기화 시도:', versionId);
            try {
              await state.syncVersionToDB(conversationId, versionId);
              
              // 🔍 동기화 후 DB 세션 재조회로 버전 존재 재확인
              const refreshedSession = await ImageSessionApiClient.getSessionByConversation(conversationId, state.currentUserId);
              if (refreshedSession) {
                const versionExistsAfterSync = refreshedSession.versions.some((v: any) => v.id === versionId);
                
                if (versionExistsAfterSync) {
                  // 🎯 동기화 성공 - 이제 안전하게 선택 API 호출
                  try {
                    await ImageSessionApiClient.selectVersion({
                      user_id: state.currentUserId,
                      session_id: refreshedSession.id,
                      version_id: versionId,
                    });
                    console.log('✅ DB 동기화 후 버전 선택 완료:', versionId);
                  } catch (finalSelectError) {
                    console.warn('⚠️ 동기화 후에도 버전 선택 실패, 메모리에서만 처리:', finalSelectError);
                  }
                } else {
                  console.warn('⚠️ DB 동기화했지만 여전히 버전이 없음, 메모리에서만 처리');
                }
              }
            } catch (syncError) {
              console.warn('⚠️ DB 동기화 실패, 메모리에서만 처리:', syncError);
            }
          } else {
            console.warn('⚠️ 메모리에도 해당 버전이 없음, 동기화 불가');
          }
        }
      } else {
        console.log('ℹ️ DB에 세션이 없어서 버전 선택 동기화 스킵:', conversationId);
        
        // 세션이 없으면 메모리 세션을 DB에 저장 시도
        const session = state.getSession(conversationId);
        if (session) {
          console.log('🔄 메모리 세션을 DB에 동기화 (버전 포함):', conversationId);
          try {
            await state.syncSessionToDB(conversationId);
            
            // 🔄 세션과 모든 버전을 동기화
            for (const version of session.versions) {
              try {
                await state.syncVersionToDB(conversationId, version.id);
              } catch (versionSyncError) {
                console.warn(`⚠️ 버전 ${version.id} DB 동기화 실패:`, versionSyncError);
              }
            }
          } catch (sessionSyncError) {
            console.warn('⚠️ 세션 DB 동기화 실패:', sessionSyncError);
          }
        }
      }
    } catch (error) {
      console.error('❌ DB 버전 선택 동기화 실패:', error);
      
      // 🛡️ 404 및 기타 오류 처리 - 메모리 상태는 유지 (사용자 경험 우선)
      if (error instanceof Error) {
        if (error.message.includes('Not Found') || error.message.includes('404')) {
          console.log('🔄 404 오류: DB에서 리소스를 찾을 수 없음, 메모리에서만 처리');
        } else if (error.message.includes('Network') || error.message.includes('fetch')) {
          console.log('🔄 네트워크 오류: 연결 문제, 메모리에서만 처리');
        } else {
          console.log('🔄 기타 오류:', error.message, '메모리에서만 처리');
        }
      }
    }
  },

  // === Canvas ID 중복 방지 시스템 (v4.1) ===
  isCanvasIdProcessed: (conversationId, canvasId) => {
    const processedSet = get().processedCanvasIds.get(conversationId);
    return processedSet ? processedSet.has(canvasId) : false;
  },

  markCanvasIdAsProcessed: (conversationId, canvasId) => {
    const state = get();
    const currentSet = state.processedCanvasIds.get(conversationId) || new Set<string>();
    currentSet.add(canvasId);
    
    const newProcessedCanvasIds = new Map(state.processedCanvasIds);
    newProcessedCanvasIds.set(conversationId, currentSet);
    
    set({ processedCanvasIds: newProcessedCanvasIds });
    console.log(`✅ ImageSession Store - Canvas ID 처리 완료 표시: ${conversationId} / ${canvasId}`);
  },

  clearProcessedCanvasIds: (conversationId) => {
    const newProcessedCanvasIds = new Map(get().processedCanvasIds);
    newProcessedCanvasIds.delete(conversationId);
    
    set({ processedCanvasIds: newProcessedCanvasIds });
    console.log(`🗑️ ImageSession Store - 처리된 Canvas ID 초기화: ${conversationId}`);
  },
}));