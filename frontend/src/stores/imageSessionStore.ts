/**
 * 진화형 이미지 생성 세션 관리 Store
 * 하나의 대화 = 하나의 Canvas = 하나의 이미지 테마 + 순차적 버전 개선
 */

import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
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
  
  // 현재 사용자 ID (임시로 하드코딩, 추후 인증 시스템과 연동)
  currentUserId: string;
  
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
  loadSessionFromDB: (conversationId: string) => Promise<ImageGenerationSession | null>;
  syncSessionToDB: (conversationId: string) => Promise<void>;
  syncVersionToDB: (conversationId: string, versionId: string) => Promise<void>;
  syncDeletedImageUrls: (conversationId: string) => Promise<void>;
  
  // 상태 관리
  setLoading: (conversationId: string, loading: boolean) => void;
  setError: (error: string | null) => void;
  
  // 하이브리드 메서드 (메모리 + DB 동기화)
  createSessionHybrid: (conversationId: string, theme: string, initialPrompt: string) => Promise<ImageGenerationSession>;
  addVersionHybrid: (conversationId: string, version: Omit<ImageVersion, 'id' | 'createdAt' | 'versionNumber'>) => Promise<string>;
  deleteVersionHybrid: (conversationId: string, versionId: string) => Promise<void>;
  selectVersionHybrid: (conversationId: string, versionId: string) => Promise<void>;
}

export const useImageSessionStore = create<ImageSessionState>((set, get) => ({
  sessions: new Map(),
  deletedImageUrls: new Map(),
  isLoading: new Map(),
  loadError: null,
  currentUserId: 'ff8e410a-53a4-4541-a7d4-ce265678d66a', // Mock 사용자 ID (실제 UUID 형식)
  
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
  
  loadSessionFromDB: async (conversationId) => {
    console.log('📥 DB에서 세션 로드 시작:', conversationId);
    const state = get();
    
    try {
      state.setLoading(conversationId, true);
      state.setError(null);
      
      const apiSession = await ImageSessionApiClient.getSessionByConversation(conversationId, state.currentUserId);
      
      if (apiSession) {
        const storeSession = ApiResponseConverter.toStoreSession(apiSession);
        
        // 메모리에 세션 저장
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
    
    // 2. DB에 비동기 동기화
    try {
      const apiSession = await ImageSessionApiClient.getSessionByConversation(conversationId, state.currentUserId);
      if (apiSession) {
        await ImageSessionApiClient.selectVersion({
          user_id: state.currentUserId,
          session_id: apiSession.id,
          version_id: versionId,
        });
        console.log('✅ DB 버전 선택 동기화 완료:', versionId);
      } else {
        console.log('ℹ️ DB에 세션이 없어서 버전 선택 동기화 스킵:', conversationId);
        
        // 세션이 없으면 메모리 세션을 DB에 저장 (세션 생성)
        const session = state.getSession(conversationId);
        if (session) {
          console.log('🔄 메모리 세션을 DB에 동기화:', conversationId);
          await state.syncSessionToDB(conversationId);
        }
      }
    } catch (error) {
      console.error('❌ DB 버전 선택 동기화 실패:', error);
      // 메모리 상태는 유지 (사용자 경험 우선)
    }
  },
}));