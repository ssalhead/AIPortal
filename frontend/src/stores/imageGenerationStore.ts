/**
 * 글로벌 이미지 생성 상태 관리 Store
 * Canvas 열기/닫기와 독립적으로 이미지 생성 작업을 추적
 */

import { create } from 'zustand';

// 이미지 생성 작업 인터페이스
interface ImageGenerationJob {
  jobId: string;
  artifactId: string; // Canvas 아이템 ID
  status: 'generating' | 'completed' | 'failed';
  progress: number; // 0-100
  prompt: string;
  style: string;
  size: string;
  imageUrl?: string;
  error?: string;
  startTime: number;
  endTime?: number;
}

interface ImageGenerationState {
  // 활성 작업들 (jobId -> Job 매핑)
  activeJobs: Map<string, ImageGenerationJob>;
  
  // 완료된 작업들 (최근 10개 유지)
  completedJobs: ImageGenerationJob[];
  
  // Actions
  startGeneration: (jobId: string, artifactId: string, prompt: string, style: string, size: string) => void;
  updateProgress: (jobId: string, progress: number, step?: string) => void;
  completeGeneration: (jobId: string, imageUrl: string) => void;
  failGeneration: (jobId: string, error: string) => void;
  
  // Getters
  getJobStatus: (jobId: string) => ImageGenerationJob | null;
  getJobByArtifactId: (artifactId: string) => ImageGenerationJob | null;
  isGenerating: (artifactId?: string) => boolean;
  getActiveJobsCount: () => number;
  
  // Cleanup
  clearCompletedJobs: () => void;
  removeJob: (jobId: string) => void;
}

export const useImageGenerationStore = create<ImageGenerationState>((set, get) => ({
  activeJobs: new Map(),
  completedJobs: [],
  
  startGeneration: (jobId, artifactId, prompt, style, size) => {
    console.log('🎨 이미지 생성 작업 시작:', { jobId, artifactId, prompt });
    
    const newJob: ImageGenerationJob = {
      jobId,
      artifactId,
      status: 'generating',
      progress: 0,
      prompt,
      style,
      size,
      startTime: Date.now()
    };
    
    set((state) => {
      const newActiveJobs = new Map(state.activeJobs);
      newActiveJobs.set(jobId, newJob);
      return { activeJobs: newActiveJobs };
    });
  },
  
  updateProgress: (jobId, progress, step) => {
    console.log('🎨 이미지 생성 진행률 업데이트:', { jobId, progress, step });
    
    set((state) => {
      const newActiveJobs = new Map(state.activeJobs);
      const job = newActiveJobs.get(jobId);
      
      if (job) {
        job.progress = Math.min(Math.max(progress, 0), 100); // 0-100 범위 제한
        newActiveJobs.set(jobId, job);
      }
      
      return { activeJobs: newActiveJobs };
    });
  },
  
  completeGeneration: (jobId, imageUrl) => {
    console.log('🎨 이미지 생성 완료:', { jobId, imageUrl });
    
    set((state) => {
      const newActiveJobs = new Map(state.activeJobs);
      const job = newActiveJobs.get(jobId);
      
      if (job) {
        // 작업 완료로 상태 변경
        job.status = 'completed';
        job.progress = 100;
        job.imageUrl = imageUrl;
        job.endTime = Date.now();
        
        // 완료된 작업 리스트에 추가 (최근 10개만 유지)
        const newCompletedJobs = [job, ...state.completedJobs.slice(0, 9)];
        
        // 활성 작업에서 제거
        newActiveJobs.delete(jobId);
        
        return {
          activeJobs: newActiveJobs,
          completedJobs: newCompletedJobs
        };
      }
      
      return { activeJobs: newActiveJobs };
    });
  },
  
  failGeneration: (jobId, error) => {
    console.log('🎨 이미지 생성 실패:', { jobId, error });
    
    set((state) => {
      const newActiveJobs = new Map(state.activeJobs);
      const job = newActiveJobs.get(jobId);
      
      if (job) {
        // 작업 실패로 상태 변경
        job.status = 'failed';
        job.error = error;
        job.endTime = Date.now();
        
        // 실패한 작업도 완료된 작업 리스트에 추가 (디버깅용)
        const newCompletedJobs = [job, ...state.completedJobs.slice(0, 9)];
        
        // 활성 작업에서 제거
        newActiveJobs.delete(jobId);
        
        return {
          activeJobs: newActiveJobs,
          completedJobs: newCompletedJobs
        };
      }
      
      return { activeJobs: newActiveJobs };
    });
  },
  
  getJobStatus: (jobId) => {
    const state = get();
    
    // 활성 작업에서 먼저 찾기
    const activeJob = state.activeJobs.get(jobId);
    if (activeJob) return activeJob;
    
    // 완료된 작업에서 찾기
    return state.completedJobs.find(job => job.jobId === jobId) || null;
  },
  
  getJobByArtifactId: (artifactId) => {
    const state = get();
    
    // 활성 작업에서 먼저 찾기
    for (const job of state.activeJobs.values()) {
      if (job.artifactId === artifactId) return job;
    }
    
    // 완료된 작업에서 찾기
    return state.completedJobs.find(job => job.artifactId === artifactId) || null;
  },
  
  isGenerating: (artifactId) => {
    const state = get();
    
    if (artifactId) {
      // 특정 Artifact의 생성 상태 확인
      for (const job of state.activeJobs.values()) {
        if (job.artifactId === artifactId && job.status === 'generating') {
          return true;
        }
      }
      return false;
    } else {
      // 전체 생성 작업 중인지 확인
      for (const job of state.activeJobs.values()) {
        if (job.status === 'generating') return true;
      }
      return false;
    }
  },
  
  getActiveJobsCount: () => {
    return get().activeJobs.size;
  },
  
  clearCompletedJobs: () => {
    set({ completedJobs: [] });
  },
  
  removeJob: (jobId) => {
    set((state) => {
      const newActiveJobs = new Map(state.activeJobs);
      newActiveJobs.delete(jobId);
      
      const newCompletedJobs = state.completedJobs.filter(job => job.jobId !== jobId);
      
      return {
        activeJobs: newActiveJobs,
        completedJobs: newCompletedJobs
      };
    });
  }
}));

export default useImageGenerationStore;